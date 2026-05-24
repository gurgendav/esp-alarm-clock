#!/usr/bin/env python3
"""On-demand Yandex Maps route duration service for AlarmV1.

Runs a tiny local HTTP server around headless Chromium scraping. Home Assistant can
call `/route` via `rest_command` when the alarm is dismissed; no polling sensor is
needed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

DEFAULT_ROUTE_URL = ""


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data.replace("\xa0", " ")).strip()
        if text:
            self.parts.append(text)


def chromium_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("Chromium executable not found")


def render_dom(url: str, chrome: str, timeout: int, budget_ms: int, debug_html: str | None = None) -> str:
    user_data_dir = tempfile.mkdtemp(prefix="alarmv1-yandex-route-chrome-")
    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--disable-extensions",
        "--disable-sync",
        "--disable-default-apps",
        "--no-first-run",
        "--window-size=1280,900",
        f"--user-data-dir={user_data_dir}",
        f"--virtual-time-budget={budget_ms}",
        "--dump-dom",
        url,
    ]
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Chromium timed out after {timeout}s") from exc
    finally:
        shutil.rmtree(user_data_dir, ignore_errors=True)

    if debug_html:
        with open(debug_html, "w", encoding="utf-8") as f:
            f.write(proc.stdout or "")

    if proc.returncode not in (0, 124):
        err = (proc.stderr or "").strip().splitlines()[-5:]
        raise RuntimeError(f"Chromium exited {proc.returncode}: {' | '.join(err)}")
    if not proc.stdout or len(proc.stdout) < 1000:
        err = (proc.stderr or "").strip().splitlines()[-5:]
        raise RuntimeError(f"Chromium produced no useful DOM. stderr: {' | '.join(err)}")
    return proc.stdout


def rendered_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    parts: list[str] = []
    for part in parser.parts:
        if not parts or parts[-1] != part:
            parts.append(part)
    return " | ".join(parts)


def duration_to_minutes(text: str) -> int | None:
    h = re.search(r"(\d+)\s*h", text)
    m = re.search(r"(\d+)\s*min", text)
    if not h and not m:
        return None
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def parse_visible_routes(text: str) -> list[dict[str, Any]]:
    duration = r"(?P<duration>(?:\d+\s*h(?:\s*\d+\s*min)?|\d+\s*min))"
    arrival = r"Arrive at\s*(?P<arrival>[0-2]?\d:\d{2})"
    distance = r"(?P<distance>\d+(?:\.\d+)?\s*(?:km|m))"
    pattern = re.compile(duration + r"\s*\|\s*" + arrival + r"\s*\|\s*" + distance, re.I)

    routes: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for match in pattern.finditer(text):
        item: dict[str, Any] = {key: re.sub(r"\s+", " ", value.strip()) for key, value in match.groupdict().items() if value}
        key = (item["duration"], item["arrival"], item["distance"])
        if key in seen:
            continue
        seen.add(key)
        item["duration_minutes"] = duration_to_minutes(item["duration"])
        routes.append(item)
    return routes


def scrape_route(url: str, chrome: str, timeout: int, budget_ms: int, debug_html: str | None = None) -> dict[str, Any]:
    start = time.time()
    html = render_dom(url, chrome, timeout, budget_ms, debug_html)
    text = rendered_text(html)
    routes = parse_visible_routes(text)
    result: dict[str, Any] = {
        "ok": bool(routes),
        "source": "yandex_maps_headless_chromium",
        "url": url,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_seconds": round(time.time() - start, 2),
        "routes": routes,
    }
    if routes:
        result["best"] = routes[0]
    else:
        idx = max(text.lower().find("depart now"), text.lower().find("routes"), 0)
        result["error"] = "No route snippets matched rendered Yandex text"
        result["text_sample"] = text[idx : idx + 800]
    return result


def route_response(scrape_result: dict[str, Any]) -> dict[str, Any]:
    best = scrape_result.get("best") or {}
    return {
        "ok": bool(scrape_result.get("ok")),
        "provider": "yandex_maps_scraper",
        "duration_minutes": best.get("duration_minutes"),
        "duration": best.get("duration"),
        "arrival": best.get("arrival"),
        "distance": best.get("distance"),
        "routes": scrape_result.get("routes", []),
        "fetched_at": scrape_result.get("fetched_at"),
        "elapsed_seconds": scrape_result.get("elapsed_seconds"),
        "url": scrape_result.get("url"),
        "error": scrape_result.get("error"),
    }


ScrapeFn = Callable[[str, str, int, int, str | None], dict[str, Any]]


def handle_route_request(
    query: dict[str, list[str]],
    scrape_fn: ScrapeFn,
    default_url: str,
    chrome: str,
    timeout: int,
    budget_ms: int,
) -> tuple[str, int]:
    url = query.get("url", [default_url])[0]
    if not url:
        return json.dumps({"ok": False, "error": "Missing route URL"}, ensure_ascii=False), 400
    try:
        response = route_response(scrape_fn(url, chrome, timeout, budget_ms, None))
    except Exception as exc:
        response = {"ok": False, "provider": "yandex_maps_scraper", "error": str(exc)}
        return json.dumps(response, ensure_ascii=False), 502
    return json.dumps(response, ensure_ascii=False), 200 if response.get("ok") else 502


class RouteRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._write_json({"ok": True, "service": "alarmv1_yandex_route"}, 200)
            return
        if parsed.path != "/route":
            self._write_json({"ok": False, "error": "Not found"}, 404)
            return
        body, status = handle_route_request(
            urllib.parse.parse_qs(parsed.query),
            scrape_route,
            self.server.default_url,  # type: ignore[attr-defined]
            self.server.chrome,  # type: ignore[attr-defined]
            self.server.scrape_timeout,  # type: ignore[attr-defined]
            self.server.budget_ms,  # type: ignore[attr-defined]
        )
        self._write(body, status)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.log_date_time_string()} {self.address_string()} {format % args}")

    def _write_json(self, data: dict[str, Any], status: int) -> None:
        self._write(json.dumps(data, ensure_ascii=False), status)

    def _write(self, body: str, status: int) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class RouteServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler], *, default_url: str, chrome: str, scrape_timeout: int, budget_ms: int) -> None:
        super().__init__(server_address, handler_cls)
        self.default_url = default_url
        self.chrome = chrome
        self.scrape_timeout = scrape_timeout
        self.budget_ms = budget_ms


def main() -> int:
    parser = argparse.ArgumentParser(description="AlarmV1 on-demand Yandex route HTTP service")
    parser.add_argument("--host", default=os.environ.get("ALARMV1_ROUTE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ALARMV1_ROUTE_PORT", "8765")))
    parser.add_argument(
        "--route-url",
        default=os.environ.get("ALARMV1_YANDEX_ROUTE_URL", DEFAULT_ROUTE_URL),
        help="Yandex Maps route URL. Prefer ALARMV1_YANDEX_ROUTE_URL so private coordinates stay out of git.",
    )
    parser.add_argument("--chromium", default=os.environ.get("CHROMIUM_PATH"))
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("ALARMV1_ROUTE_TIMEOUT", "60")))
    parser.add_argument("--budget-ms", type=int, default=int(os.environ.get("ALARMV1_ROUTE_BUDGET_MS", "30000")))
    parser.add_argument("--once", action="store_true", help="Scrape once, print JSON, and exit")
    args = parser.parse_args()

    chrome = chromium_path(args.chromium)
    if not args.route_url:
        parser.error("--route-url or ALARMV1_YANDEX_ROUTE_URL is required")
    if args.once:
        print(json.dumps(route_response(scrape_route(args.route_url, chrome, args.timeout, args.budget_ms)), ensure_ascii=False, indent=2))
        return 0

    server = RouteServer(
        (args.host, args.port),
        RouteRequestHandler,
        default_url=args.route_url,
        chrome=chrome,
        scrape_timeout=args.timeout,
        budget_ms=args.budget_ms,
    )
    print(f"AlarmV1 Yandex route service listening on http://{args.host}:{args.port}")
    print(f"Default route URL: {args.route_url}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

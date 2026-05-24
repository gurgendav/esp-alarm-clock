import importlib.util
import json
import pathlib
import sys
import urllib.parse

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "home-assistant" / "scripts" / "yandex_route_service.py"
spec = importlib.util.spec_from_file_location("yandex_route_service", MODULE_PATH)
assert spec is not None
assert spec.loader is not None
yandex_route_service = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = yandex_route_service
spec.loader.exec_module(yandex_route_service)


def test_parse_visible_routes_extracts_unique_visible_route_snippets():
    text = (
        "Routes | All | Depart now | 8 min | Arrive at 09:18 | 2.27 km | Details | Report | "
        "8 min | Arrive at 09:18 | 2.27 km | Details | "
        "12 min | Arrive at 09:22 | 3.4 km | Details"
    )

    routes = yandex_route_service.parse_visible_routes(text)

    assert routes == [
        {
            "duration": "8 min",
            "arrival": "09:18",
            "distance": "2.27 km",
            "duration_minutes": 8,
        },
        {
            "duration": "12 min",
            "arrival": "09:22",
            "distance": "3.4 km",
            "duration_minutes": 12,
        },
    ]


def test_parse_visible_routes_supports_hour_and_minute_durations():
    text = "Depart now | 1 h 5 min | Arrive at 10:15 | 42 km | Details"

    routes = yandex_route_service.parse_visible_routes(text)

    assert routes[0]["duration_minutes"] == 65
    assert routes[0]["duration"] == "1 h 5 min"


def test_route_response_flattens_best_route_for_home_assistant():
    scrape_result = {
        "ok": True,
        "best": {
            "duration": "8 min",
            "arrival": "09:18",
            "distance": "2.27 km",
            "duration_minutes": 8,
        },
        "routes": [{"duration": "8 min"}],
        "elapsed_seconds": 6.2,
    }

    response = yandex_route_service.route_response(scrape_result)

    assert response["ok"] is True
    assert response["duration_minutes"] == 8
    assert response["duration"] == "8 min"
    assert response["arrival"] == "09:18"
    assert response["distance"] == "2.27 km"
    assert response["provider"] == "yandex_maps_scraper"


def test_route_request_handler_uses_default_url_when_no_url_query_is_passed():
    captured = {}

    def fake_scrape(url, chrome, timeout, budget_ms, debug_html=None):
        captured["url"] = url
        return {
            "ok": True,
            "best": {"duration": "9 min", "arrival": "09:19", "distance": "2.5 km", "duration_minutes": 9},
            "routes": [],
            "elapsed_seconds": 0.1,
        }

    body, status = yandex_route_service.handle_route_request(
        urllib.parse.parse_qs(""),
        fake_scrape,
        default_url="https://yandex.com/maps/?rtext=a~b&rtt=auto",
        chrome="/usr/bin/chromium",
        timeout=1,
        budget_ms=1,
    )

    data = json.loads(body)
    assert status == 200
    assert data["ok"] is True
    assert data["duration_minutes"] == 9
    assert captured["url"] == "https://yandex.com/maps/?rtext=a~b&rtt=auto"

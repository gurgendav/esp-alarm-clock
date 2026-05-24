# AlarmV1 Morning Briefing Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** On deliberate AlarmV1 alarm stop/dismiss, Home Assistant speaks a useful morning briefing with detailed weather and one-time commute duration lookup.

**Architecture:** ESPHome remains only the trigger: `dismiss_alarm` calls `script.alarmv1_morning_briefing`. Home Assistant owns orchestration, weather forecast parsing, commute gating, TTS, and dedupe. Yandex commute lookup is an on-demand local HTTP service wrapping headless Chromium; HA calls it with `rest_command` only while the briefing script runs, not via a polling sensor.

**Tech Stack:** ESPHome YAML, Home Assistant package YAML, Python 3 stdlib HTTP service, system Chromium, pytest for scraper/service parsing tests.

---

## Task 1: Add testable Yandex route service module

**Objective:** Provide a local HTTP API (`/route`) that returns the first Yandex Maps route snippet as JSON and can be tested without launching Chromium.

**Files:**
- Create: `home-assistant/scripts/yandex_route_service.py`
- Create: `tests/test_yandex_route_service.py`

**Steps:**
1. Write tests for `parse_visible_routes()` using rendered text like `Depart now | 8 min | Arrive at 09:18 | 2.27 km`.
2. Write tests for HTTP JSON shaping using a fake scrape function.
3. Run the tests and confirm they fail because the module does not exist.
4. Implement the module by adapting the proven `/config/scripts/yandex_route_scraper.py` parser/Chromium runner plus a small `http.server` wrapper.
5. Run tests and confirm pass.

## Task 2: Replace the old Waze package example with on-demand detailed weather + Yandex route

**Objective:** Make the HA package reflect the approved architecture: detailed weather, no polling sensor, route only on alarm-dismiss path.

**Files:**
- Modify: `home-assistant/packages/alarmv1_morning_briefing.yaml.example`

**Steps:**
1. Add `input_datetime.alarmv1_morning_briefing_last_run` for dedupe.
2. Add `rest_command.alarmv1_yandex_route_home_to_work` targeting the reachable route-service URL. For the Hermes Agent Home Assistant add-on, bind the service to `0.0.0.0` and call `http://0a6523c6-hermes-agent.local.hass.io:8765/route` from Home Assistant.
3. In `script.alarmv1_morning_briefing`, call `weather.get_forecasts` twice (`daily` and `hourly`).
4. Compute current temperature/condition from `weather.kievyan_pogoda` attributes/state.
5. Compute today high/low from daily forecast fields.
6. Compute first likely rain window from hourly forecast precipitation/precipitation_probability.
7. Gate commute to weekday morning while `person.gurgen` is `home`, then call the Yandex route rest_command.
8. Speak concise but detailed text via `tts.speak`.

## Task 3: Verify existing ESPHome hook remains correct

**Objective:** Confirm the already-present `dismiss_alarm -> play_morning_briefing_on_ha` hook only fires on deliberate stop, not snooze/timeout.

**Files:**
- Inspect: `clock.yaml`

**Steps:**
1. Verify `button Stop Alarm` uses `dismiss_alarm`.
2. Verify `dismiss_alarm` clears snooze, stops alarm, and calls `play_morning_briefing_on_ha`.
3. Verify snooze paths do not call `play_morning_briefing_on_ha`.
4. Run `esphome config clock.yaml`.

## Task 4: Validate and document operation

**Objective:** Ensure the Python service and ESPHome config pass local checks and document how to run the service.

**Files:**
- Modify: `readme.md` if needed.

**Steps:**
1. Run `python3 -m pytest tests/ -q`.
2. Run a live one-shot route scrape against a Yandex route URL.
3. Run `esphome config clock.yaml`.
4. Commit changes on `wip/alarm-clock`.

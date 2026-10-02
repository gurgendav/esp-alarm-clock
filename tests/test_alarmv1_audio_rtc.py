"""Host-execute production audio lambdas/actions; never build or contact firmware."""
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ESPHomeLoader(yaml.SafeLoader):
    pass


ESPHomeLoader.add_multi_constructor(
    "!", lambda loader, tag, node: loader.construct_scalar(node)
)


def clock():
    return yaml.load((ROOT / "clock.yaml").read_text(), Loader=ESPHomeLoader)


def actions_cpp(actions):
    """Execute the relevant synchronous ESPHome action subset with host stubs.

    Delays are advanced by the caller (watchdog runs at its deadline). Telemetry
    is inert; script calls are recorded, not recursively run. Unknown actions
    fail rather than silently claiming behavioral coverage.
    """
    result = []
    for action in actions:
        for key, value in action.items():
            if key == "lambda":
                result.append(f"[&]() {{ {value} }}();")
            elif key == "if":
                condition = value["condition"]["lambda"]
                result.append(f"if ([&]() {{ {condition} }}()) {{")
                result.append(actions_cpp(value["then"]))
                result.append("} else {")
                result.append(actions_cpp(value.get("else", [])))
                result.append("}")
            elif key == "script.execute":
                name = value if isinstance(value, str) else value["id"]
                result.append(f"{name}.execute();")
            elif key == "script.stop":
                result.append(f"{value}.stop();")
            elif key == "output.turn_off":
                assert value == "buzzer"
                result.append("local_audio = false;")
            elif key == "delay":
                pass
            else:
                raise AssertionError(f"Unimplemented host action: {key}")
    return "\n".join(result)


@pytest.fixture(scope="module")
def audio_harness(tmp_path_factory):
    compiler = shutil.which("g++")
    assert compiler, "g++ required to execute production audio behavior"
    config = clock()
    scripts = {item["id"]: item for item in config["script"]}
    listener = next(item for item in config["text_sensor"] if item.get("id") == "alarm_audio_player_state")
    request = scripts["request_alarm_media_on_ha"]["then"][1]["homeassistant.action"]
    code = r'''
#include <cassert>
#include <cstdint>
#include <string>
#define id(x) x
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
bool local_audio = true, alarm_ringing = true, alarm_session_active = true;
bool alarm_external_audio_retry_needed = false;
uint32_t alarm_external_audio_playing_started_ms = 0;
int alarm_external_audio_retry_count = 0, alarm_external_audio_session_retry_count = 0;
int alarm_audio_event_code = 0;
uint32_t alarm_session_id = 7, alarm_audio_attempt_generation = 3;
uint32_t request_session_id = 7, request_generation = 3, now_ms = 1000;
uint32_t millis() { return now_ms; }
struct Player {
  bool present = true;
  std::string state = "idle";
  bool has_state() { return present; }
} alarm_audio_player_state;
struct Script {
  int calls = 0;
  bool local = false;
  void execute() { ++calls; if (local) local_audio = true; }
  void stop() { if (local) local_audio = false; }
  bool is_running() { return local && local_audio; }
};
Script alarm_loop{0, true}, start_alarm_media_on_ha, publish_wake_event, stop_alarm_media_on_ha;
'''
    code += "\nvoid observe() {\n" + actions_cpp(listener["on_value"]["then"]) + "\n}\n"
    code += "void accepted() {\n" + actions_cpp(request["on_success"]) + "\n}\n"
    code += "void watchdog() {\n" + actions_cpp(scripts["alarm_external_audio_watchdog"]["then"]) + "\n}\n"
    code += r'''
void playing() { alarm_audio_player_state.present = true; alarm_audio_player_state.state = "playing"; observe(); }
int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string scenario = argv[1];
  if (scenario == "accepted_without_playback") {
    accepted(); assert(local_audio);
    now_ms = 46000; watchdog(); assert(local_audio);
    assert(start_alarm_media_on_ha.calls == 1);
    accepted(); assert(local_audio);
    now_ms += 45000; watchdog(); assert(local_audio);
    assert(start_alarm_media_on_ha.calls == 2);
    accepted(); assert(local_audio);
    now_ms += 45000; watchdog(); assert(local_audio);
    assert(start_alarm_media_on_ha.calls == 2);
  } else if (scenario == "playing_handoff") {
    playing(); assert(!local_audio);
    assert(alarm_external_audio_playing_started_ms == 1000);
    accepted(); assert(!local_audio);
  } else if (scenario == "early_drop" || scenario == "late_drop" ||
             scenario == "budget_exhausted" || scenario == "unavailable_drop" ||
             scenario == "unknown_drop" || scenario == "missing_state_drop") {
    playing();
    // Represent the local handoff even on the buggy baseline to isolate drop behavior.
    local_audio = false;
    if (scenario == "budget_exhausted") alarm_external_audio_retry_count = 2;
    now_ms = scenario == "late_drop" ? 61000 : 2000;
    alarm_audio_player_state.state = scenario == "unavailable_drop" ? "unavailable" :
                                     scenario == "unknown_drop" ? "unknown" : "idle";
    if (scenario == "missing_state_drop") alarm_audio_player_state.present = false;
    observe(); assert(local_audio);
    assert(alarm_external_audio_playing_started_ms == 0);
    const bool should_retry = scenario != "late_drop" && scenario != "budget_exhausted";
    assert(start_alarm_media_on_ha.calls == (should_retry ? 1 : 0));
    assert(alarm_external_audio_session_retry_count == (should_retry ? 1 : 0));
    accepted(); assert(local_audio);
    playing(); assert(!local_audio);
  } else if (scenario == "stopped_no_resurrection") {
    alarm_ringing = false; alarm_session_active = false; local_audio = false;
    playing(); accepted(); watchdog();
    alarm_audio_player_state.state = "idle"; observe();
    assert(!local_audio); assert(alarm_loop.calls == 0);
    assert(start_alarm_media_on_ha.calls == 0);
    assert(stop_alarm_media_on_ha.calls == 1);
  } else if (scenario == "superseded_callback") {
    request_generation = 2; accepted(); assert(local_audio);
    assert(stop_alarm_media_on_ha.calls == 0);
    request_generation = 3; request_session_id = 6; accepted(); assert(local_audio);
    assert(stop_alarm_media_on_ha.calls == 0);
  } else { assert(false); }
}
'''
    directory = tmp_path_factory.mktemp("alarm-audio-host")
    source = directory / "audio.cpp"
    source.write_text(code)
    executable = directory / "audio"
    subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(executable)], check=True, capture_output=True, text=True)
    return executable


@pytest.mark.parametrize("scenario", [
    "accepted_without_playback", "playing_handoff", "early_drop", "late_drop",
    "budget_exhausted", "unavailable_drop", "unknown_drop", "missing_state_drop",
    "stopped_no_resurrection", "superseded_callback",
])
def test_production_audio_transitions(audio_harness, scenario):
    result = subprocess.run([str(audio_harness), scenario], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_rtc_restore_precedes_boot_scheduling_and_offline_reboots_are_disabled():
    config = clock()
    boot = config["esphome"]["on_boot"]
    assert boot["priority"] < 0  # after RTC/component setup, before the main loop
    actions = boot["then"]
    read_index = next((i for i, action in enumerate(actions) if "pcf8563.read_time" in action), None)
    assert read_index is not None, "update_interval: never requires explicit hardware RTC restoration"
    assert actions[read_index]["pcf8563.read_time"] == {"id": "rtctime"}
    for i, action in enumerate(actions):
        if isinstance(action, dict) and action.get("script.execute") in {"update_minutes_hand", "sync_alarm_day_state"}:
            assert read_index < i
    assert read_index == 0  # no boot delay may allow scheduling before restoration
    assert config["wifi"]["reboot_timeout"] == "0s"
    assert config["api"]["reboot_timeout"] == "0s"
    assert config["preferences"]["flash_write_interval"] == "10s"


def test_stop_cancels_pending_audio_work():
    scripts = {item["id"]: item for item in clock()["script"]}
    actions = scripts["stop_alarm"]["then"]
    assert {"script.stop": "alarm_external_audio_watchdog"} in actions
    assert {"script.stop": "alarm_loop"} in actions
    assert {"output.turn_off": "buzzer"} in actions
    assert any("id(alarm_ringing) = false;" in item.get("lambda", "") for item in actions)

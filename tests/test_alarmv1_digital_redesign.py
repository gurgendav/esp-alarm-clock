from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / "clock.yaml"


def read_clock() -> str:
    return CLOCK.read_text(encoding="utf-8")


def test_v2_digital_clock_replaces_analog_meter():
    text = read_clock()
    assert "id: clock_time_label" in text
    assert "id: clock_status_pill" in text
    assert "id: clock_next_label" in text
    assert "id: clock_countdown_label" in text
    assert "id: minute_hand" not in text
    assert "id: hour_hand" not in text
    assert "id: secs_hand" not in text


def test_v2_design_font_assets_and_labels_are_present():
    text = read_clock()
    assert "assets/HankenGrotesk-Bold.ttf" in text
    assert "id: clock_time_font_82" in text
    assert "TAP TO RESUME" in text
    assert "AWAY" in text
    assert "ON" in text
    assert "ONE-TIME" in text
    assert "SNOOZING" in text
    assert "SKIPPED" in text
    assert "Start Music" in text
    assert "Open Music" in text
    assert "Start music" not in text
    assert "Open music" not in text


def test_v2_skip_resume_layout_stays_inside_round_screen():
    text = read_clock()
    assert "id: clock_time_label\n            width: 220\n            align: CENTER\n            y: -40" in text
    assert "id: clock_divider\n            width: 142\n            height: 2\n            align: CENTER\n            y: 0" in text
    assert "id: clock_resume_button\n            hidden: true\n            width: 140\n            height: 28" in text
    assert "radius: 14\n            bg_opa: TRANSP" in text
    assert "shadow_width: 0\n            pad_all: 0" in text


def test_v2_omits_bottom_nav_and_album_art_runtime_paths():
    text = read_clock()
    forbidden = [
        "bottom_nav",
        "online_image:",
        "runtime_image",
        "entity_picture",
        "alarm_nav",
        "timer_nav",
        "nightlight_nav",
    ]
    for token in forbidden:
        assert token not in text


def test_v2_media_screen_uses_large_touch_targets_without_album_art():
    text = read_clock()
    assert "id: media_text_font_18" in text
    assert "id: media_play_pause_button\n                  width: 68\n                  height: 68" in text
    assert "id: media_play_pause_icon_label\n                        align: CENTER\n                        x: 2\n                        y: 1" in text
    assert "id: media_stop_button\n                  width: 54\n                  height: 54" in text
    assert "id: media_next_button\n                  width: 54\n                  height: 54" in text
    assert "arc_width: 8" in text


def test_v2_away_and_alarm_state_pill_colors_are_distinct():
    text = read_clock()
    assert "return \"AWAY\";" in text
    assert "return \"ON\";" in text
    assert "return lv_color_hex(0xB6F7FF);" in text  # away pill
    assert "return lv_color_hex(0x17351F);" in text  # normal alarm-on pill
    assert "return lv_color_hex(0xFFD166);" in text  # skipped alarm accent
    assert "return lv_color_hex(0xFFB59C);" in text  # one-time override accent
    assert "return lv_color_hex(0x4DD9E4);" in text  # snoozing accent
    assert "return lv_color_hex(0x003E44);" in text  # full-screen away teal


def test_v2_snooze_screen_shows_until_time_and_countdown():
    text = read_clock()
    assert "Active snooze adjusted clockwise" in text
    assert "Active snooze adjusted anticlockwise" in text
    assert "snprintf(next_buf, sizeof(next_buf), \"Snoozed until\");" in text
    assert "auto snooze_until = ESPTime::from_epoch_local(id(next_alarm_epoch));" in text
    assert "snprintf(countdown_buf, sizeof(countdown_buf), \"%d min left\", minutes_left);" in text


def test_v2_post_dismiss_briefing_choices_replace_auto_immediate_start():
    text = read_clock()
    assert "id: briefing_prompt_label" in text
    assert "text: \"Briefing\"" in text
    assert "text: \"Brief+Music\"" in text
    assert "text: \"Dismiss\"" in text
    assert "id(morning_briefing_auto_start_ms) = now_ms + 15000;" in text
    assert "snprintf(briefing_buf, sizeof(briefing_buf), \"Briefing in %us\"" in text
    assert "id: play_morning_briefing_with_music_on_ha" in text
    dismiss_block = text.split("  - id: dismiss_alarm", 1)[1].split("\n\n  - id:", 1)[0]
    assert "play_morning_briefing_on_ha" not in dismiss_block


def test_v2_rotary_does_not_create_override_while_next_ring_is_skipped():
    text = read_clock()
    assert text.count("Ignoring encoder turn while next ring is skipped") == 2
    clockwise_block = text.split("on_clockwise:", 1)[1].split("on_anticlockwise:", 1)[0]
    anticlockwise_block = text.split("on_anticlockwise:", 1)[1].split("time:", 1)[0]
    for block in (clockwise_block, anticlockwise_block):
        skip_guard = block.split("if (id(skip_next_ring))", 1)[1].split("auto now = id(sntp_time).now();", 1)[0]
        assert "return;" in skip_guard


def test_v2_stop_music_cancels_pending_morning_music_start():
    text = read_clock()
    assert "script.stop: play_morning_music_on_ha" in text
    assert "action: script.turn_off\n          data:\n            entity_id: ${morning_briefing_action}" in text
    assert "id(morning_music_start_pending) = true;" in text
    assert "id(morning_music_start_pending) = false;" in text
    assert "lambda: \"return id(morning_music_start_pending);\"" in text

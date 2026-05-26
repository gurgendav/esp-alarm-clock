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
    assert "ONE-TIME" in text
    assert "SNOOZING" in text
    assert "SKIPPED" in text
    assert "Start Music" in text
    assert "Open Music" in text
    assert "Start music" not in text
    assert "Open music" not in text


def test_v2_skip_resume_layout_stays_inside_round_screen():
    text = read_clock()
    assert "id: clock_time_label\n            width: 220\n            align: CENTER\n            y: -48" in text
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
    assert "id: media_stop_button\n                  width: 54\n                  height: 54" in text
    assert "id: media_next_button\n                  width: 54\n                  height: 54" in text
    assert "arc_width: 8" in text

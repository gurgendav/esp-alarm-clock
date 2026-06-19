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
    assert "Resume Music" in text
    assert "Starting..." in text
    assert "Start music" not in text
    assert "Open music" not in text


def test_v2_skip_resume_layout_stays_inside_round_screen():
    text = read_clock()
    assert "id: clock_time_label\n            width: 220\n            align: CENTER\n            y: -35" in text
    assert "id: clock_divider\n            width: 142\n            height: 2\n            align: CENTER\n            y: 0" in text
    assert "id: clock_resume_button\n            hidden: true\n            width: 140\n            height: 28" in text
    assert "radius: 14\n            bg_opa: TRANSP" in text
    assert "shadow_width: 0\n            pad_all: 0" in text


def test_v2_main_ring_copy_prioritizes_visible_countdown_and_short_date():
    text = read_clock()
    assert 'text: "Ring: --:--"' in text
    assert "text_font: clock_body_font_18" in text
    assert "return lv_color_hex(0x4DD9E4);" in text  # visible normal ring countdown accent
    assert 'snprintf(next_buf, sizeof(next_buf), "Ring in %dh %dm", hours, minutes);' in text
    assert 'snprintf(next_buf, sizeof(next_buf), "Ring: %s %02d:%02d", day_text, next_alarm.hour, next_alarm.minute);' in text
    assert 'snprintf(countdown_buf, sizeof(countdown_buf), "%s %02d:%02d", day_text, next_alarm.hour, next_alarm.minute);' in text
    assert "Next Ring:" not in text


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


def test_v2_media_screen_uses_clean_controls_without_album_art():
    text = read_clock()
    assert "id: media_text_font_18" in text
    assert "id: media_text_font_20" in text
    assert "media_icon_font_28" not in text
    assert "id: media_status_label" in text
    assert "id: media_sleep_label" in text
    assert "text: \"READY\"" in text
    assert "return \"NOW PLAYING\";" in text
    assert "return \"STARTING\";" in text
    assert "return \"Starting music\";" in text
    assert "return \"Tap stop to cancel\";" in text
    assert "return \"Ready to play\";" in text
    assert "id: media_status_label\n                  width: 150\n                  align: CENTER\n                  y: -92" in text
    assert "id: media_title_label\n                  width: 204\n                  align: CENTER\n                  y: -50" in text
    assert "text_font: media_text_font_20" in text
    assert "id: media_artist_label\n                  width: 196\n                  align: CENTER\n                  y: -16" in text
    assert "id: media_sleep_label\n                  width: 176\n                  align: CENTER\n                  y: 4" in text
    assert "id: media_progress_bar\n                  width: 176\n                  height: 4" in text
    assert "id: media_progress_bar\n                  width: 176\n                  height: 4\n                  align: CENTER\n                  y: 12" in text
    assert "id: media_control_dock\n                  width: 168\n                  height: 72\n                  align: CENTER\n                  y: 64" in text
    assert "id: media_stop_button\n                        width: 52\n                        height: 64\n                        x: -54\n                        y: 0" in text
    assert "id: media_play_pause_button\n                        width: 52\n                        height: 52\n                        x: 0\n                        y: 0" in text
    assert "id: media_next_button\n                        width: 52\n                        height: 64\n                        x: 54\n                        y: 0" in text
    assert "id: media_stop_icon\n                              width: 14\n                              height: 14" in text
    assert "id: media_pause_icon_group\n                              width: 30\n                              height: 24" in text
    assert "id: media_play_icon\n                              hidden: true\n                              width: 24\n                              height: 24" in text
    assert "id: media_next_icon_group\n                              width: 30\n                              height: 22" in text
    assert 'points: ["4,3", "4,21", "20,12", "4,3"]' in text
    assert 'points: ["2,3", "12,11", "2,19"]' in text
    assert 'text: "Stop"' not in text
    assert 'text: "Next"' not in text
    assert "media_play_pause_icon_label" not in text


def test_v2_media_uses_top_volume_arc_overlay_horizontal_progress_and_rotating_title():
    text = read_clock()
    assert "id: media_track_position" in text
    assert "attribute: media_position" in text
    assert "id: media_track_duration" in text
    assert "attribute: media_duration" in text
    assert "id: media_progress_bar" in text
    assert "lvgl.bar.update:\n          id: media_progress_bar" in text
    assert "id: media_volume_arc\n                  hidden: true\n                  width: 214\n                  height: 214\n                  align: CENTER\n                  y: -4" in text
    assert "start_angle: 220" in text
    assert "end_angle: 320" in text
    assert "arc_width: 6" in text
    assert "arc_rounded: true" in text
    assert "arc_color: 0x18383B" in text
    assert "indicator:\n                    arc_width: 6\n                    arc_color: 0x4DD9E4" in text
    assert "knob:\n                    bg_opa: TRANSP" in text
    assert "media_volume_label" not in text
    assert "VOL" not in text
    assert "lvgl.widget.show: media_volume_arc" in text
    assert "lvgl.widget.hide: media_volume_arc" in text
    assert "long_mode: scroll_circular" in text
    assert "id(media_position_updated_ms) = millis();" in text
    assert "return lv_color_hex(0x4DD9E4);" in text  # volume/progress color
    assert "bg_color: 0x4DD9E4" in text  # progress/status color
    assert "bg_color: 0x243030" in text  # inactive progress bar


def test_v2_media_starting_state_is_cancel_focused():
    text = read_clock()
    assert "id: media_starting_stop_button" in text
    assert "id: media_starting_stop_button\n                  hidden: true\n                  width: 118\n                  height: 44\n                  align: CENTER\n                  y: 76" in text
    assert "lvgl.widget.hide: [media_control_dock, media_progress_bar]" in text
    assert "lvgl.widget.show: media_starting_stop_button" in text
    assert "lvgl.widget.show: [media_control_dock, media_progress_bar]" in text
    assert "lvgl.widget.hide: media_starting_stop_button" in text


def test_v2_media_metadata_skips_unsupported_glyphs_before_display():
    text = read_clock()
    header_path = ROOT / "alarmv1_media_text.h"
    assert "    - alarmv1_media_text.h" in text
    assert header_path.exists()
    header = header_path.read_text(encoding="utf-8")

    assert "sanitize_media_text" in header
    assert "is_supported_media_codepoint" in header
    assert "codepoint >= 0x0410 && codepoint <= 0x044F" in header
    assert "codepoint == 0x0401 || codepoint == 0x0451" in header
    assert "return false;" in header
    assert "alarmv1::media_text::sanitize(id(media_track_title).state, media_title_buf)" in text
    assert "alarmv1::media_text::sanitize(id(media_track_artist).state, media_artist_buf)" in text
    assert "alarmv1::media_text::sanitize(id(media_track_album).state, media_artist_buf)" in text


def test_v2_media_sleep_timer_and_next_double_tap():
    text = read_clock()
    assert "id: cycle_media_sleep_timer" in text
    assert "Media sleep timer set for %d minutes" in text
    assert "Sleep timer %dm" in text
    assert "Media sleep timer expired; stopping music" in text
    assert "id: handle_media_next_button_click" in text
    assert "id: media_next_single_tap_delay" in text
    assert "Double tap Next: skipping morning music playlist" in text
    assert "skip_playlist: \"true\"" in text


def test_v2_front_button_controls_media_screen():
    text = read_clock()
    front_button_block = text.split("id: front_button", 1)[1].split("spi:", 1)[0]
    assert "return id(media_screen_visible);" in front_button_block
    assert "script.execute: media_play_pause_on_ha" in front_button_block
    assert "script.execute: stop_morning_music_on_ha" in front_button_block
    assert "script.execute: close_media_screen" in front_button_block
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
    assert "Turn knob for snooze" in text
    assert "Rotate = snooze time" not in text


def test_v2_post_dismiss_briefing_choices_replace_auto_immediate_start():
    text = read_clock()
    assert "id: briefing_prompt_panel\n            hidden: true\n            width: 210\n            height: 210" in text
    assert "id: briefing_prompt_label" in text
    assert "text: \"Morning\"" in text
    assert "text: \"Briefing\"" in text
    assert "text: \"Brief+Music\"" in text
    assert "text: \"Dismiss\"" in text
    assert "id: briefing_start_button\n                  width: 168\n                  height: 42" in text
    assert "id: briefing_music_button\n                  width: 168\n                  height: 42" in text
    assert "id: briefing_dismiss_button\n                  width: 128\n                  height: 34" in text
    assert "id(morning_briefing_auto_start_ms) = now_ms + 15000;" in text
    assert "snprintf(briefing_buf, sizeof(briefing_buf), \"Briefing in %us\"" in text
    assert "id: play_morning_briefing_with_music_on_ha" in text
    music_button_block = text.split("id: briefing_music_button", 1)[1].split("widgets:", 1)[0]
    assert "script.execute: open_media_screen" in music_button_block
    assert music_button_block.index("open_media_screen") < music_button_block.index("play_morning_briefing_with_music_on_ha")
    assert "id(morning_music_start_pending_until_ms) = millis() + 180000;" in text
    assert "lvgl.widget.show: [briefing_prompt_panel]" in text
    assert "lvgl.widget.show: [briefing_prompt_label, briefing_start_button" not in text
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


def test_v2_skip_on_one_time_override_removes_override_before_main_alarm_skip():
    text = read_clock()
    assert "skip_next_ring_targets_override" not in text

    toggle_block = text.split("  - id: toggle_skip_next_ring", 1)[1].split("\n\n  - id:", 1)[0]
    assert "Skip one-time override removed; restored regular next ring" in toggle_block
    assert "id(next_ring_override_active) = false;" in toggle_block
    assert "id(next_ring_override_epoch) = 0;" in toggle_block

    override_clear = toggle_block.index("Skip one-time override removed; restored regular next ring")
    normal_skip = toggle_block.index("id(skip_next_ring) = true;")
    assert override_clear < normal_skip


def test_v2_anticlockwise_rotary_starts_quick_override_when_regular_alarm_is_far_away():
    text = read_clock()
    assert "smart_quick_override_threshold_minutes" in text
    assert "smart_quick_override_start_minutes" in text
    assert "const uint32_t smart_quick_override_threshold_minutes = 180;" in text
    assert "const uint32_t smart_quick_override_start_minutes = 30;" in text
    assert text.count("Smart quick override started at +%u minutes") == 1

    clockwise_block = text.split("on_clockwise:", 1)[1].split("on_anticlockwise:", 1)[0]
    anticlockwise_block = text.split("on_anticlockwise:", 1)[1].split("time:", 1)[0]

    assert "smart_quick_override_threshold_minutes" not in clockwise_block
    assert "smart_quick_override_start_minutes" not in clockwise_block
    assert "Smart quick override started" not in clockwise_block

    assert "!id(next_ring_override_active)" in anticlockwise_block
    assert "minutes_until_next_alarm > smart_quick_override_threshold_minutes" in anticlockwise_block
    smart_start = anticlockwise_block.index("now.timestamp + (smart_quick_override_start_minutes * 60)")
    normal_adjust = anticlockwise_block.index("Next ring override adjusted")
    assert smart_start < normal_adjust


def test_v2_exposes_ha_one_time_alarm_datetime_and_clear_button():
    text = read_clock()

    assert "id: one_time_alarm_time" in text
    assert 'name: "One-Time Alarm"' in text
    assert "type: datetime" in text
    assert "restore_value: false" in text
    assert "on_value:" in text
    assert "set_one_time_alarm_from_epoch" in text

    assert 'name: "Clear One-Time Alarm"' in text
    clear_button_block = text.split('name: "Clear One-Time Alarm"', 1)[1].split("\n\n", 1)[0]
    assert "script.execute: clear_one_time_alarm" in clear_button_block


def test_v2_one_time_alarm_api_actions_are_exposed_for_automations():
    text = read_clock()
    api_block = text.split("api:", 1)[1].split("\nweb_server:", 1)[0]

    assert "actions:" in api_block
    assert "action: set_one_time_alarm" in api_block
    assert "target_epoch: int" in api_block
    assert "set_one_time_alarm_from_epoch" in api_block
    assert "action: clear_one_time_alarm" in api_block
    assert "script.execute: clear_one_time_alarm" in api_block


def test_v2_one_time_alarm_rejects_read_only_and_past_targets():
    text = read_clock()
    set_block = text.split("  - id: set_one_time_alarm_from_epoch", 1)[1].split("\n\n  - id:", 1)[0]

    assert "Parents Home Mode blocks one-time alarm setup" in set_block
    assert "id(read_only_mode)" in set_block
    assert "Ignoring one-time alarm in the past" in set_block
    assert "target_epoch <= uint32_t(now.timestamp)" in set_block
    assert "id(skip_next_ring) = false;" in set_block
    assert "id(next_ring_override_active) = true;" in set_block
    assert "id(next_ring_override_epoch) = target_epoch;" in set_block


def test_v2_one_time_alarm_auto_clears_after_ring_or_expiry():
    text = read_clock()
    sync_block = text.split("  - id: sync_next_alarm_state", 1)[1].split("\n\n  - id:", 1)[0]

    assert "if (id(next_ring_override_active))" in sync_block
    assert "id(last_alarm_minute_key) != int(override_minute)" in sync_block
    assert "id(next_ring_override_active) = false;" in sync_block
    assert "id(next_ring_override_epoch) = 0;" in sync_block


def test_v2_missed_alarm_catches_up_after_power_or_connection_recovery():
    text = read_clock()
    last_key_block = text.split("id: last_alarm_minute_key", 1)[1].split("  - id:", 1)[0]
    assert "restore_value: yes" in last_key_block
    assert "const uint32_t missed_alarm_catch_up_minutes = 120;" in text
    assert "Missed one-time override catch-up" in text
    assert "Missed scheduled alarm catch-up" in text
    assert "now_minute > target_minute + missed_alarm_catch_up_minutes" in text
    assert "id(last_alarm_minute_key) != int(candidate_minute)" in text
    assert "skipped_minute + missed_alarm_catch_up_minutes < now_minute" in text


def test_v2_exposes_alarm_ringing_state_to_home_assistant():
    text = read_clock()
    assert "id: alarm_ringing_sensor" in text
    assert "name: \"Alarm Ringing\"" in text
    assert "icon: \"mdi:alarm-light\"" in text
    assert "return id(alarm_ringing);" in text


def test_v2_real_screenshot_endpoint_is_registered():
    text = read_clock()
    assert "includes:\n    - alarmv1_screenshot.h" in text
    assert "CONFIG_LV_USE_SNAPSHOT: y" in text
    assert "- -DLV_USE_SNAPSHOT=1" in text
    assert "id: alarmv1_lvgl" in text
    assert "alarmv1::screenshot::register_alarmv1_screenshot_endpoint(" in text
    assert "id(open_media_screen).execute();" in text
    assert "id(close_media_screen).execute();" in text


def test_v2_screenshot_endpoint_can_navigate_to_media_or_clock():
    header = (ROOT / "alarmv1_screenshot.h").read_text(encoding="utf-8")
    assert "constexpr const char *OPEN_MEDIA_PATH = \"/alarmv1/open-media\";" in header
    assert "constexpr const char *OPEN_CLOCK_PATH = \"/alarmv1/open-clock\";" in header
    assert "request->url_to(url_buffer) == OPEN_MEDIA_PATH" in header
    assert "request->url_to(url_buffer) == OPEN_CLOCK_PATH" in header
    assert "handle_navigation_request_(request, \"open-media\", this->open_media_)" in header
    assert "handle_navigation_request_(request, \"open-clock\", this->open_clock_)" in header
    assert "AlarmV1 navigation executed" in header


def test_v2_real_screenshot_endpoint_streams_lvgl_bmp():
    header = (ROOT / "alarmv1_screenshot.h").read_text(encoding="utf-8")
    assert "constexpr const char *SCREENSHOT_PATH = \"/alarmv1/screenshot.bmp\";" in header
    assert "constexpr uint16_t ALARMV1_SCREENSHOT_BAND_ROWS" in header
    assert "lv_draw_buf_create(width, ALARMV1_SCREENSHOT_BAND_ROWS, LV_COLOR_FORMAT_RGB565" in header
    assert "lv_obj_redraw(&layer, screen);" in header
    assert "LV_COLOR_FORMAT_RGB565" in header
    assert "image/bmp" in header
    assert "httpd_resp_send_chunk" in header
    assert "BITMAPINFOHEADER" in header
    assert "std::vector<uint8_t> rgb565" not in header


def test_v2_touch_stop_requires_hold_progress():
    text = read_clock()
    stop_block = text.split("id: stop_button", 1)[1].split("widgets:", 1)[0]
    assert "on_click:" not in stop_block
    assert "on_press:" in stop_block
    assert "script.execute: begin_alarm_stop_hold_touch" in stop_block
    assert "on_release:" in stop_block
    assert "script.execute: cancel_alarm_stop_hold" in stop_block

    assert "id: stop_hold_bar" in text
    assert "lvgl.bar.update:" in text
    assert "id(alarm_stop_hold_started_ms)" in text
    assert "id: finish_alarm_stop_hold" in text
    assert '"HOLD %u%%"' not in text
    assert '"HOLD %u"' in text


def test_v2_physical_button_shows_same_hold_to_stop_progress():
    text = read_clock()
    front_button_block = text.split("id: front_button", 1)[1].split("spi:", 1)[0]
    assert "on_press:" in front_button_block
    assert "script.execute: begin_alarm_stop_hold_front" in front_button_block
    assert "on_release:" in front_button_block
    assert "script.execute: cancel_alarm_stop_hold" in front_button_block
    assert "id(front_button_stop_consumed)" in front_button_block
    assert "script.execute: home_all_lights_off" in front_button_block


def test_v2_home_music_button_is_state_aware():
    text = read_clock()
    button_block = text.split("id: menu_music_play_button", 1)[1].split("widgets:", 1)[0]
    assert "id(morning_music_start_pending)" in button_block
    assert "id(media_player_state).state == \"playing\"" in button_block
    assert "id(media_player_state).state == \"paused\"" in button_block
    assert "script.execute: media_play_on_ha" in button_block
    assert "script.execute: play_morning_music_on_ha" in button_block


def test_v2_stop_music_cancels_pending_morning_music_start():
    text = read_clock()
    assert "script.stop: play_morning_music_on_ha" in text
    assert "action: script.turn_off\n          data:\n            entity_id: ${morning_briefing_action}" in text
    assert "id(morning_music_start_pending) = true;" in text
    assert "id(morning_music_start_pending_until_ms) = millis() + 30000;" in text
    assert "id(morning_music_start_pending) = false;" in text
    assert "id(morning_music_start_pending_until_ms) = 0;" in text
    assert "Morning music playback detected; clearing start pending state" in text
    assert "Morning music start pending state timed out" in text
    assert "lambda: \"return id(morning_music_start_pending);\"" in text


def test_v2_night_dim_first_touch_only_wakes_display():
    text = read_clock()
    assert "id: wake_only_touch_until_ms" in text
    touch_block = text.split("touchscreen:", 1)[1].split("light:", 1)[0]
    assert "id(screen_dimmed) && night_dim_mode" in touch_block
    assert "now.hour >= 23 || now.hour < 7" in touch_block
    assert "id(wake_only_touch_until_ms) = now_ms + 1200;" in touch_block
    assert "Night dim tap wakes screen only" in touch_block

    center_short_block = text.split("id: center_tap_button", 1)[1].split("on_long_press:", 1)[0]
    assert center_short_block.index("wake_only_touch_until_ms") < center_short_block.index("toggle_skip_next_ring")
    assert "Center tap ignored after night dim wake" in center_short_block

    center_long_block = text.split("on_long_press:", 1)[1].split("id: home_menu_panel", 1)[0]
    assert center_long_block.index("wake_only_touch_until_ms") < center_long_block.index("open_home_menu")
    assert "Long press ignored after night dim wake" in center_long_block

    resume_block = text.split("id: clock_resume_button", 1)[1].split("widgets:", 1)[0]
    assert resume_block.index("wake_only_touch_until_ms") < resume_block.index("enable_alarm")
    assert resume_block.index("wake_only_touch_until_ms") < resume_block.index("toggle_skip_next_ring")
    assert "Resume tap ignored after night dim wake" in resume_block


def test_v2_alarm_external_audio_retries_when_playback_drops_quickly():
    text = read_clock()
    assert "id: alarm_audio_player_state" in text
    assert "entity_id: ${alarm_audio_player_entity}" in text
    assert "id: alarm_external_audio_playing_started_ms" in text
    assert "id: alarm_external_audio_retry_count" in text
    assert "id: alarm_external_audio_retry_needed" in text
    assert "const uint32_t minimum_external_audio_ms = 45000;" in text
    assert "External alarm audio stopped after %ums; retrying alarm audio" in text
    assert "External alarm audio did not reach playing within 45s; retrying alarm audio" in text
    assert "id(alarm_external_audio_retry_count) < 2" in text
    assert "id: alarm_external_audio_watchdog" in text
    assert "delay: 45s" in text

    retry_block = text.split("id: alarm_audio_player_state", 1)[1].split("id: media_track_title", 1)[0]
    assert "id(alarm_ringing)" in retry_block
    assert "state == \"playing\"" in retry_block
    assert "script.execute: alarm_loop" in retry_block
    assert "script.execute: start_alarm_media_on_ha" in retry_block

    start_block = text.split("\n  - id: start_alarm\n", 1)[1].split("\n\n  - id: stop_alarm", 1)[0]
    assert "id(alarm_external_audio_playing_started_ms) = 0;" in start_block
    assert "id(alarm_external_audio_retry_count) = 0;" in start_block

    stop_block = text.split("  - id: stop_alarm", 1)[1].split("\n\n  - id: alarm_loop", 1)[0]
    assert "id(alarm_external_audio_playing_started_ms) = 0;" in stop_block
    assert "id(alarm_external_audio_retry_needed) = false;" in stop_block


def test_v2_parents_home_mode_is_persistent_and_locks_scheduling_controls():
    text = read_clock()
    assert "id: read_only_mode" in text
    assert "restore_value: yes" in text.split("id: read_only_mode", 1)[1].split("  - id:", 1)[0]
    assert "id: parents_home_mode_switch" not in text
    assert "id: parents_home_mode_state" in text
    assert "entity_id: input_boolean.parents_home_mode" in text
    parents_state_block = text.split("id: parents_home_mode_state", 1)[1].split("  - platform:", 1)[0]
    assert "id(read_only_mode) = enabled;" in parents_state_block
    assert "Parents Home Mode enabled from Home Assistant" in parents_state_block
    assert "Parents Home Mode disabled from Home Assistant" in parents_state_block

    center_short_block = text.split("id: center_tap_button", 1)[1].split("on_long_press:", 1)[0]
    assert center_short_block.index("id(read_only_mode)") < center_short_block.index("toggle_skip_next_ring")

    center_long_block = text.split("on_long_press:", 1)[1].split("id: home_menu_panel", 1)[0]
    assert "!id(read_only_mode)" in center_long_block
    assert center_long_block.index("!id(read_only_mode)") < center_long_block.index("open_home_menu")

    toggle_block = text.split("  - id: toggle_skip_next_ring", 1)[1].split("\n\n  - id:", 1)[0]
    readonly_guard = toggle_block.split("Parents Home Mode blocks skip next ring", 1)[0]
    assert "if (id(read_only_mode))" in readonly_guard
    assert "id(skip_next_ring) = false;" in readonly_guard
    assert "id(next_ring_override_active) = false;" in readonly_guard
    assert readonly_guard.index("if (id(read_only_mode))") < toggle_block.index("id(skip_next_ring) = true;")

    sync_block = text.split("  - id: sync_next_alarm_state", 1)[1].split("\n\n  - id:", 1)[0]
    assert "Parents Home Mode cleared persisted skip/override state" in sync_block
    assert sync_block.index("if (id(read_only_mode))") < sync_block.index("if (id(skip_next_ring))")


def test_v2_parents_home_mode_blocks_one_time_override_and_auto_briefing():
    text = read_clock()
    clockwise_block = text.split("on_clockwise:", 1)[1].split("on_anticlockwise:", 1)[0]
    anticlockwise_block = text.split("on_anticlockwise:", 1)[1].split("time:", 1)[0]
    for block in (clockwise_block, anticlockwise_block):
        assert "id(read_only_mode)" in block
        assert block.index("id(read_only_mode)") < block.index("id(next_ring_override_active) = true;")

    dismiss_block = text.split("  - id: dismiss_alarm", 1)[1].split("\n\n  - id:", 1)[0]
    assert "if (id(read_only_mode))" in dismiss_block
    assert "Parents Home Mode dismisses morning briefing/music prompt" in dismiss_block
    readonly_dismiss = dismiss_block.split("if (id(read_only_mode))", 1)[1].split("} else {", 1)[0]
    assert "id(morning_music_prompt_until_ms) = 0;" in readonly_dismiss
    assert "id(morning_briefing_auto_start_ms) = 0;" in readonly_dismiss
    assert "now_ms + 60000" not in readonly_dismiss
    assert "now_ms + 15000" not in readonly_dismiss

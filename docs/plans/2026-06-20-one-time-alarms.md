# AlarmV1 One-Time Alarms Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a first-class, Home Assistant controllable one-time alarm for AlarmV1 so users can set a single next ring (for example, tomorrow at 09:00) without changing weekday/weekend schedules.

**Architecture:** Reuse the existing restored `next_ring_override_active` + `next_ring_override_epoch` state, because the firmware already prioritizes one-time overrides above recurring alarms, catches up after reboot, shows the override as the next alarm, and clears it after it has rung or expired. Add a Home Assistant `datetime` entity for setting the one-time alarm, plus a clear button/native API action for cancellation. Keep recurring weekday/weekend alarm entities unchanged.

**Tech Stack:** ESPHome 2026.x YAML, Home Assistant native API actions, ESPHome template `datetime`, existing Python structural tests in `tests/test_alarmv1_digital_redesign.py`, AlarmV1 `/config/work/esp-alarm-clock/clock.yaml`.

---

## Current behavior discovered

- `clock.yaml` already has persisted globals:
  - `next_ring_override_active`
  - `next_ring_override_epoch`
- `sync_next_alarm_state` already checks override before snooze and recurring alarms.
- Override is already exposed indirectly as `sensor.alarmv1_next_alarm_time`.
- Rotary already creates/adjusts one-time overrides:
  - clockwise adjusts from current next alarm
  - anticlockwise can start a smart quick override at now + 30 minutes
- No Home Assistant entity currently exists for directly setting an arbitrary one-time datetime.
- Today’s manual workaround changed `time.alarmv1_weekend_alarm_time`; this is exactly what this feature should avoid.

---

## Design alternatives

### Option A — Firmware-owned one-time `datetime` entity (recommended)

Add:

- `datetime.alarmv1_one_time_alarm` exposed by ESPHome
- `button.alarmv1_clear_one_time_alarm`
- native API action `esphome.esphome_web_56058c_set_one_time_alarm` with an epoch integer, mainly for automations/scripts
- native API action `esphome.esphome_web_56058c_clear_one_time_alarm`

**Pros**

- Survives Home Assistant restarts because the actual ring target remains in ESPHome restored globals.
- Keeps AlarmV1 independent enough to ring even if HA is unavailable after the target is set.
- Easy for Hermes/Telegram to set through HA services later.
- Does not mutate recurring weekday/weekend alarms.
- Reuses existing tested override/catch-up/ring logic.

**Cons**

- Requires firmware flash.
- The HA entity list changes; automations/dashboards may need entity refresh after ESPHome reconnects.

### Option B — Home Assistant helper + automation only

Create an HA `input_datetime` and automation that presses/updates AlarmV1 at the chosen time.

**Pros**

- No firmware flash if only HA helpers are added.
- Faster to prototype in HA UI.

**Cons**

- Alarm depends on HA automation firing at the exact time.
- Does not use AlarmV1’s local missed-alarm catch-up and local ringing logic as cleanly.
- More fragile during HA restart/network outage.

### Option C — Full on-device date/time picker

Add a dedicated AlarmV1 UI panel for picking date and time directly on the 240×240 device.

**Pros**

- Can be used without phone/HA UI.

**Cons**

- Much more UI complexity on a small round screen.
- Higher risk of accidental alarm changes.
- Not necessary because rotary quick override already covers on-device short-term overrides.

**Recommendation:** Implement Option A now. Keep Option C as a future polish item only if the HA/Telegram flow feels insufficient.

---

## Acceptance criteria

- [ ] User can set a one-time alarm from Home Assistant without changing `time.alarmv1_weekday_alarm_time` or `time.alarmv1_weekend_alarm_time`.
- [ ] User can clear a one-time alarm from Home Assistant.
- [ ] `sensor.alarmv1_next_alarm_time` reports the one-time target after it is set.
- [ ] One-time alarm is blocked in Parents Home / read-only mode, consistent with current scheduling-control rules.
- [ ] Setting an invalid past target is rejected/ignored and does not overwrite the next alarm.
- [ ] One-time alarm persists across AlarmV1 reboot until it rings, is cleared, is skipped, or expires beyond catch-up.
- [ ] Existing rotary quick override behavior remains unchanged, especially anticlockwise-only smart quick override.
- [ ] Tests, `esphome config`, and `esphome compile` pass before any flash.

---

## Task 1: Add tests for HA-exposed one-time alarm controls

**Objective:** Lock the desired HA surface before editing firmware.

**Files:**

- Modify: `tests/test_alarmv1_digital_redesign.py`
- Read: `clock.yaml`

**Step 1: Add failing structural tests**

Add tests near the existing override tests:

```python
def test_v2_exposes_ha_one_time_alarm_datetime_and_clear_button():
    text = read_clock()

    assert 'id: one_time_alarm_time' in text
    assert 'name: "One-Time Alarm"' in text
    assert 'type: datetime' in text
    assert 'set_one_time_alarm_from_epoch' in text

    assert 'name: "Clear One-Time Alarm"' in text
    clear_button_block = text.split('name: "Clear One-Time Alarm"', 1)[1].split('\n  - platform:', 1)[0]
    assert 'script.execute: clear_one_time_alarm' in clear_button_block


def test_v2_one_time_alarm_api_actions_are_exposed_for_automations():
    text = read_clock()
    api_block = text.split('api:', 1)[1].split('\nweb_server:', 1)[0]

    assert 'actions:' in api_block
    assert 'action: set_one_time_alarm' in api_block
    assert 'target_epoch: int' in api_block
    assert 'script.execute:' in api_block
    assert 'action: clear_one_time_alarm' in api_block


def test_v2_one_time_alarm_rejects_read_only_and_past_targets():
    text = read_clock()
    set_block = text.split('  - id: set_one_time_alarm_from_epoch', 1)[1].split('\n\n  - id:', 1)[0]

    assert 'Parents Home Mode blocks one-time alarm setup' in set_block
    assert 'id(read_only_mode)' in set_block
    assert 'Ignoring one-time alarm in the past' in set_block
    assert 'target_epoch <= uint32_t(now.timestamp)' in set_block
    assert 'id(next_ring_override_active) = true;' in set_block
    assert 'id(next_ring_override_epoch) = target_epoch;' in set_block
```

**Step 2: Run the tests to verify failure**

Run:

```bash
pytest -q tests/test_alarmv1_digital_redesign.py \
  -k 'one_time_alarm or override'
```

Expected: FAIL because the new datetime, actions, and scripts do not exist yet.

---

## Task 2: Add the native API actions

**Objective:** Allow HA automations and Hermes to set/clear a one-time alarm by epoch without touching recurring schedule entities.

**Files:**

- Modify: `clock.yaml:65-67`

**Step 1: Replace the current `api` block**

Current:

```yaml
api:
  reboot_timeout: 0s
```

Change to:

```yaml
api:
  reboot_timeout: 0s
  actions:
    - action: set_one_time_alarm
      variables:
        target_epoch: int
      then:
        - script.execute:
            id: set_one_time_alarm_from_epoch
            target_epoch: !lambda 'return uint32_t(target_epoch);'
    - action: clear_one_time_alarm
      then:
        - script.execute: clear_one_time_alarm
```

**Step 2: Run focused tests**

Run:

```bash
pytest -q tests/test_alarmv1_digital_redesign.py::test_v2_one_time_alarm_api_actions_are_exposed_for_automations
```

Expected: PASS after scripts are added in Task 4; may still FAIL at this task if the test also requires script IDs.

---

## Task 3: Add HA datetime and clear button entities

**Objective:** Expose user-friendly HA controls for setting and cancelling one-time alarms.

**Files:**

- Modify: `clock.yaml:595-617` (`datetime:` section)
- Modify: `clock.yaml:309-323` (`button:` section)

**Step 1: Add a template datetime after weekend alarm time**

```yaml
  - platform: template
    id: one_time_alarm_time
    name: "One-Time Alarm"
    type: datetime
    icon: "mdi:alarm-plus"
    optimistic: yes
    restore_value: false
    initial_value: "2026-01-01 09:00:00"
    on_value:
      then:
        - script.execute:
            id: set_one_time_alarm_from_epoch
            target_epoch: !lambda 'return uint32_t(x.timestamp);'
```

Notes:

- `on_value` is used because the ESPHome template datetime reliably publishes the new value when HA updates it.
- `restore_value: false` prevents an old UI value from re-arming itself on boot; the actual active target remains in restored globals (`next_ring_override_active` / `next_ring_override_epoch`).

**Step 2: Add a clear button after `Test Alarm`**

```yaml
  - platform: template
    name: "Clear One-Time Alarm"
    icon: "mdi:alarm-off"
    on_press:
      - script.execute: clear_one_time_alarm
      - script.execute: reset_idle_timer
```

**Step 3: Run focused test**

Run:

```bash
pytest -q tests/test_alarmv1_digital_redesign.py::test_v2_exposes_ha_one_time_alarm_datetime_and_clear_button
```

Expected: PASS after Task 4 adds the script IDs.

---

## Task 4: Add set/clear scripts for one-time alarms

**Objective:** Centralize validation, read-only blocking, state updates, and UI refresh for one-time alarms.

**Files:**

- Modify: `clock.yaml` in the `script:` section, near `sync_next_alarm_state`

**Step 1: Add parameterized set script before `sync_next_alarm_state`**

```yaml
  - id: set_one_time_alarm_from_epoch
    parameters:
      target_epoch: uint32_t
    then:
      - lambda: |-
          if (id(read_only_mode)) {
            ESP_LOGI("alarm", "Parents Home Mode blocks one-time alarm setup");
            return;
          }
          auto now = id(sntp_time).now();
          if (!now.is_valid()) {
            now = id(rtctime).now();
          }
          if (!now.is_valid()) {
            ESP_LOGW("alarm", "Ignoring one-time alarm setup because time is unavailable");
            return;
          }
          if (target_epoch <= uint32_t(now.timestamp)) {
            ESP_LOGW("alarm", "Ignoring one-time alarm in the past: target epoch %u", target_epoch);
            return;
          }
          id(skip_next_ring) = false;
          id(skip_next_ring_epoch) = 0;
          id(next_ring_override_active) = true;
          id(next_ring_override_epoch) = target_epoch;
          auto target = ESPTime::from_epoch_local(target_epoch);
          ESP_LOGI("alarm", "One-time alarm set for %04d-%02d-%02d %02d:%02d", target.year, target.month, target.day_of_month, target.hour, target.minute);
      - script.execute: sync_next_alarm_state
      - script.execute: update_minutes_hand
      - script.execute: update_alarm_status_ui
      - script.execute: reset_idle_timer
```

**Step 2: Add clear script immediately after it**

```yaml
  - id: clear_one_time_alarm
    then:
      - lambda: |-
          if (id(next_ring_override_active)) {
            ESP_LOGI("alarm", "One-time alarm cleared");
          }
          id(next_ring_override_active) = false;
          id(next_ring_override_epoch) = 0;
          if (id(skip_next_ring)) {
            id(skip_next_ring) = false;
            id(skip_next_ring_epoch) = 0;
          }
      - script.execute: sync_next_alarm_state
      - script.execute: update_minutes_hand
      - script.execute: update_alarm_status_ui
      - script.execute: reset_idle_timer
```

**Step 3: Run focused tests**

Run:

```bash
pytest -q tests/test_alarmv1_digital_redesign.py \
  -k 'one_time_alarm or override or read_only'
```

Expected: PASS.

---

## Task 5: Ensure dismiss/expiry semantics remain one-time

**Objective:** Verify the override clears after ring/expiry and does not turn into a recurring schedule.

**Files:**

- Read/possibly modify: `clock.yaml:1988-2006`
- Modify: `tests/test_alarmv1_digital_redesign.py`

**Step 1: Add a regression test for existing auto-clear behavior**

```python
def test_v2_one_time_alarm_auto_clears_after_ring_or_expiry():
    text = read_clock()
    sync_block = text.split('  - id: sync_next_alarm_state', 1)[1].split('\n\n  - id:', 1)[0]

    assert 'if (id(next_ring_override_active))' in sync_block
    assert 'id(last_alarm_minute_key) != int(override_minute)' in sync_block
    assert 'id(next_ring_override_active) = false;' in sync_block
    assert 'id(next_ring_override_epoch) = 0;' in sync_block
```

**Step 2: Run test**

Run:

```bash
pytest -q tests/test_alarmv1_digital_redesign.py::test_v2_one_time_alarm_auto_clears_after_ring_or_expiry
```

Expected: PASS with current logic, or minimal code changes if the existing block has drifted.

---

## Task 6: Full validation before flash

**Objective:** Prove firmware config/build is valid before deploying to the device.

**Files:**

- Generated private files under `/tmp/alarmv1-flash-files/`

**Step 1: Run full Python test suite**

```bash
pytest -q
```

Expected: all tests pass.

**Step 2: Prepare private flashing files**

```bash
python /config/.hermes/scripts/prepare_alarmv1_flash_files.py
```

Expected: `/tmp/alarmv1-flash-files/clock.yaml` exists and includes local substitutions/secrets without committing them.

**Step 3: Validate ESPHome config**

```bash
esphome config /tmp/alarmv1-flash-files/clock.yaml
```

Expected: config validates successfully.

**Step 4: Compile firmware**

```bash
esphome compile /tmp/alarmv1-flash-files/clock.yaml
```

Expected: compile succeeds.

---

## Task 7: Commit, push, and prepare flash handoff

**Objective:** Save a reviewable unit of work before OTA flashing.

**Files:**

- `clock.yaml`
- `tests/test_alarmv1_digital_redesign.py`
- optionally this plan file if not already committed

**Step 1: Review diff for private data**

```bash
git diff -- clock.yaml tests/test_alarmv1_digital_redesign.py docs/plans/2026-06-20-one-time-alarms.md
```

Expected: no private entity IDs, hostnames, addresses, Wi-Fi values, tokens, or local-only secrets introduced.

**Step 2: Commit**

```bash
git add clock.yaml tests/test_alarmv1_digital_redesign.py docs/plans/2026-06-20-one-time-alarms.md
git commit -m "feat: expose one-time alarm controls"
```

**Step 3: Push**

```bash
git push origin wip/alarm-clock
```

---

## Task 8: Flash and verify after user approval

**Objective:** Deploy only after validation and explicit flash confirmation.

**Step 1: Present flash confirmation**

Message must include:

- Target: AlarmV1 / `esphome-web-56058c.local`
- Change: exposes one-time alarm HA controls and native actions; recurring alarms unchanged
- Validation: pytest, `esphome config`, `esphome compile` results
- Risk: device will reboot; if OTA/network fails, physical/USB recovery may be needed
- Ask: `Flash now?`

**Step 2: OTA upload if approved**

```bash
esphome upload /tmp/alarmv1-flash-files/clock.yaml --device esphome-web-56058c.local
```

**Step 3: Verify HA entities**

After device reconnects, check:

- `datetime.alarmv1_one_time_alarm`
- `button.alarmv1_clear_one_time_alarm`
- `sensor.alarmv1_next_alarm_time`
- existing recurring entities unchanged:
  - `time.alarmv1_weekday_alarm_time`
  - `time.alarmv1_weekend_alarm_time`

**Step 4: Test a safe future one-time alarm**

Use a target at least 10 minutes in the future, then immediately clear it after verifying `sensor.alarmv1_next_alarm_time` updates.

Example HA call shape after the entity exists:

```yaml
action: datetime.set_value
target:
  entity_id: datetime.alarmv1_one_time_alarm
data:
  datetime: "2026-06-20 09:00:00"
```

Then clear:

```yaml
action: button.press
target:
  entity_id: button.alarmv1_clear_one_time_alarm
```

Expected:

- One-time alarm appears as next alarm after set.
- Recurring weekday/weekend alarm times remain unchanged.
- Clear restores the next recurring alarm.

---

## Future polish, not part of first implementation

- Add a Home Assistant dashboard row/card with `datetime.alarmv1_one_time_alarm`, clear button, and next alarm sensor.
- Add Telegram helper command/wrapper in Hermes after firmware is live: “set one-time alarm tomorrow 09:00”.
- Consider a simple on-device “+30m / +60m / clear” panel only if HA/Telegram is not enough.

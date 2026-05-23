#pragma once

#include "esphome/core/time.h"

namespace alarm_clock {

template<typename PrimaryClock, typename FallbackClock>
esphome::ESPTime current_time(PrimaryClock *primary, FallbackClock *fallback) {
  auto now = primary->now();
  if (!now.is_valid()) {
    now = fallback->now();
  }
  return now;
}

inline esphome::ESPTime add_minutes(esphome::ESPTime now, int minutes) {
  return esphome::ESPTime::from_epoch_local(now.timestamp + (minutes * 60));
}

}  // namespace alarm_clock

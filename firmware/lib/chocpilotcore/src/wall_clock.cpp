#include "wall_clock.h"

namespace chocpilot {

namespace {
constexpr uint32_t kSecondsPerDay = 24UL * 60 * 60;
}

void WallClock::set(uint8_t hour, uint8_t minute, uint8_t second, uint32_t nowMs) {
  secondsAtSync_ = (hour % 24) * 3600UL + (minute % 60) * 60UL + (second % 60);
  syncMs_ = nowMs;
  valid_ = true;
}

bool WallClock::now(uint32_t nowMs, uint8_t& hour, uint8_t& minute) const {
  if (!valid_) return false;
  // Różnica bez znaku działa też po przepełnieniu millis() (49 dni).
  const uint32_t seconds = (secondsAtSync_ + (nowMs - syncMs_) / 1000) % kSecondsPerDay;
  hour = static_cast<uint8_t>(seconds / 3600);
  minute = static_cast<uint8_t>(seconds / 60 % 60);
  return true;
}

}  // namespace chocpilot

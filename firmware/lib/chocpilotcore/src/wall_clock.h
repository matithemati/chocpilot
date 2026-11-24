// Zegar ścienny z czasu podanego przez aplikację (komenda time) – płytka nie ma RTC z baterią.
// Po ustawieniu liczy dalej z millis() (HSI48 strojony przez USB – dokładny przy podłączeniu).
#pragma once

#include <stdint.h>

namespace chocpilot {

class WallClock {
 public:
  void set(uint8_t hour, uint8_t minute, uint8_t second, uint32_t nowMs);
  bool valid() const { return valid_; }
  // Godzina i minuta teraz; false, dopóki aplikacja nie podała czasu.
  bool now(uint32_t nowMs, uint8_t& hour, uint8_t& minute) const;

 private:
  bool valid_ = false;
  uint32_t syncMs_ = 0;
  uint32_t secondsAtSync_ = 0;  // sekunda doby w chwili syncMs_
};

}  // namespace chocpilot

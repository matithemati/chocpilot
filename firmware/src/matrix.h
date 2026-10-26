// Skan matrycy 2 × 4 (COL2ROW, przełączniki Kailh Choc z diodami) z debounce per klawisz.
#pragma once

#include <stdint.h>

#include "debouncer.h"
#include "device_config.h"

namespace chocpilot {

class Matrix {
 public:
  using KeyCallback = void (*)(uint8_t key, bool down);

  void begin();
  // Pełny skan (wywoływany co ~1 ms). Zmiany po debounce trafiają do callbacku.
  void scan(uint32_t nowMs, uint8_t debounceMs, KeyCallback onChange);
  // key: 1..8
  bool pressed(uint8_t key) const;

 private:
  Debouncer keys_[kTotalKeys];
};

}  // namespace chocpilot

// Stan wejść pokazywany na ekranie w trybie testu sprzętu.
#pragma once

#include <stdint.h>

#include "device_config.h"

namespace chocpilot {

struct TestSnapshot {
  bool keys[kTotalKeys] = {false};
  // Tylko płytki z pokrętłami i suwakiem: suma obrotów, przyciski, suwak 0–100.
  int16_t encoders[2] = {0, 0};
  bool encoderKeys[2] = {false, false};
  uint8_t slider = 0;
};

}  // namespace chocpilot

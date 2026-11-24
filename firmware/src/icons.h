// Ikony klawiszy (ChocPilot v0): 8 obrazów 32 × 32 (paleta 16 kolorów + 4 bity na piksel) w RAM,
// wysyłane przez aplikację komendą icon w kawałkach. Rysowane w siatce LCD zamiast etykiet.
#pragma once

#include <stdint.h>

#include "device_config.h"

namespace chocpilot {

class IconStore {
 public:
  void clear(uint8_t key);
  // Zapis kawałka; kawałki muszą przychodzić po kolei (offset 0 zaczyna nową ikonę).
  // Zwraca true, gdy ikona jest kompletna.
  bool write(uint8_t key, uint16_t offset, const uint8_t* data, uint8_t len);
  bool has(uint8_t key) const;
  const uint8_t* data(uint8_t key) const { return buf_[key - 1]; }

 private:
  uint8_t buf_[kTotalKeys][kIconBytes] = {{0}};
  uint16_t filled_[kTotalKeys] = {0};
};

// Rysuje ikonę (32 × 32 w skali `scale`) z lewym górnym rogiem w (x, y) – w całości na ekranie.
void drawIcon(int x, int y, const uint8_t* icon, uint8_t scale);

}  // namespace chocpilot

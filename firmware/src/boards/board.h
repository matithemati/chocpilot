// Mapa pinów ChocPilot: Arduino Pro Micro (ATmega32U4) na płytce ChocPilot (docs/schematic.png).
// Numery to piny Arduino (Dn); w komentarzu nóżka modułu i port.
#pragma once

#include <stdint.h>

#include "device_config.h"

namespace chocpilot {
namespace board {

constexpr const char* kBoardId = "promicro";
constexpr const char* kBoardName = "Pro Micro";

// Matryca COL2ROW: wiersz = wyjście LOW, kolumna = wejście z pull-upem.
constexpr uint8_t kRowPins[kRows] = {
    4,  // Row 0 – nóżka 7, PD4
    9,  // Row 1 – nóżka 12, PB5
};
constexpr uint8_t kColPins[kCols] = {
    8,  // Column 0 – nóżka 11, PB4
    7,  // Column 1 – nóżka 10, PE6
    6,  // Column 2 – nóżka 9, PD7
    5,  // Column 3 – nóżka 8, PC6
};

// OLED 2,42" (SSD1309) na sprzętowym I²C ATmega32U4 (TWI): SDA = 2/PD1, SCL = 3/PD0.
constexpr uint8_t kSda = 2;  // nóżka 5
constexpr uint8_t kScl = 3;  // nóżka 6

}  // namespace board
}  // namespace chocpilot

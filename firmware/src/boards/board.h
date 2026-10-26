// Wybór mapy pinów płytki na podstawie flagi budowania (platformio.ini).
// Każdy plik board_*.h definiuje w przestrzeni nazw chocpilot::board te same stałe:
//   kBoardId, kBoardName, kRowPins[3], kColPins[3], kEncA, kEncB, kEncSw, kSda, kScl,
//   kOledSoftI2c (true = ekran przez programowe I²C na pinach kSda/kScl)
// oraz makro CHOCPILOT_ISR_ATTR (atrybut funkcji obsługi przerwań).
#pragma once

#if defined(CHOCPILOT_BOARD_KB2040)
#include "board_kb2040.h"
#elif defined(CHOCPILOT_BOARD_XIAO_ESP32S3)
#include "board_xiao_esp32s3.h"
#elif defined(CHOCPILOT_BOARD_PROMICRO)
#include "board_promicro.h"
#else
#error "Nie wybrano płytki: zdefiniuj CHOCPILOT_BOARD_KB2040, CHOCPILOT_BOARD_XIAO_ESP32S3 lub CHOCPILOT_BOARD_PROMICRO"
#endif

// Mapa pinów: Arduino / SparkFun Pro Micro (ATmega32U4). Patrz docs/WIRING.md.
// Pro Micro i KB2040 mają ten sam rozkład wyprowadzeń – PCB MacroPad_Y7 pasuje do obu.
// Numery to piny Arduino (Dn) płytki Pro Micro w tym samym miejscu co piny KB2040.
#pragma once

#include <stdint.h>

#define CHOCPILOT_ISR_ATTR

namespace chocpilot {
namespace board {

constexpr const char* kBoardId = "promicro";
constexpr const char* kBoardName = "Pro Micro";

constexpr uint8_t kRowPins[3] = {9, 8, 7};  // D9 (PB5), D8 (PB4), D7 (PE6)
constexpr uint8_t kColPins[3] = {6, 5, 4};  // D6 (PD7), D5 (PC6), D4 (PD4)

// Piny w miejscu MOSI/MISO/SCK KB2040. Nie mają INTx – enkoder używa przerwania
// pin change PCINT0 (PB1–PB3), patrz hal_promicro.cpp.
constexpr uint8_t kEncA = 16;   // MOSI (PB2, PCINT2)
constexpr uint8_t kEncB = 14;   // MISO (PB3, PCINT3)
constexpr uint8_t kEncSw = 15;  // SCK (PB1)

// Ścieżka OLED_SDA biegnie do pinu „D3” KB2040, a OLED_SCL do „D2”. Na Pro Micro to D3 = PD0
// (sprzętowe SCL układu TWI) i D2 = PD1 (sprzętowe SDA) – odwrotnie, a TWI ma piny na stałe,
// dlatego ekran obsługuje programowe I²C (jak na KB2040).
constexpr uint8_t kSda = 3;  // D3 (PD0)
constexpr uint8_t kScl = 2;  // D2 (PD1)
constexpr bool kOledSoftI2c = true;

}  // namespace board
}  // namespace chocpilot

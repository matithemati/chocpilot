// Mapa pinów ChocPilot v0: własna płytka ze STM32F072CBT6 (pcb/chocpilot-v0, docs/PINOUT.md).
// Numery pinów rdzenia STM32duino (PA0…PC15); w komentarzu nóżka LQFP-48 i sieć ze schematu.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "device_config.h"

namespace chocpilot {
namespace board {

constexpr const char* kBoardId = "chocpilot_v0";
constexpr const char* kBoardName = "ChocPilot v0";
constexpr bool kHasEncoders = true;

// Matryca 2×4 COL2ROW (dioda przy każdym klawiszu): wiersz = wyjście LOW, kolumna = wejście
// z pull-upem. Kolumna = para sąsiednich klawiszy w jednym rzędzie, wiersz 0 = klawisze
// wewnętrzne, wiersz 1 = zewnętrzne (krótsze ścieżki na płytce).
constexpr uint8_t kRowPins[kRows] = {
    PB0,   // ROW0 – nóżka 18: K2, K3, K6, K7
    PB11,  // ROW1 – nóżka 22: K1, K4, K5, K8
};
constexpr uint8_t kColPins[kCols] = {
    PB9,  // COL0 – nóżka 46: K1/K2
    PB7,  // COL1 – nóżka 43: K3/K4
    PA4,  // COL2 – nóżka 14: K5/K6
    PB2,  // COL3 – nóżka 20: K7/K8
};
// Numer klawisza Kn w punkcie matrycy (wiersz, kolumna) – pcb/…/tools/design.py: MATRIX_KEYS.
constexpr uint8_t kKeyMap[kRows][kCols] = {{2, 3, 6, 7}, {1, 4, 5, 8}};

// Ekran LCD 2" ST7789V 240×320 (Waveshare WSH-17344) na SPI1, złącze J2.
constexpr uint8_t kLcdSck = PB3;   // nóżka 39, SPI1_SCK (AF0)
constexpr uint8_t kLcdMosi = PB5;  // nóżka 41, SPI1_MOSI (AF0)
constexpr uint8_t kLcdCs = PA10;   // nóżka 31
constexpr uint8_t kLcdDc = PA9;    // nóżka 30
constexpr uint8_t kLcdRst = PB14;  // nóżka 27
constexpr uint8_t kLcdBl = PA8;    // nóżka 29, TIM1_CH1 – PWM podświetlenia

// Pokrętła EC11 (15 impulsów / 30 zatrzasków): A/B na wejściach timerów w trybie enkodera.
constexpr uint8_t kEnc1A = PA0;   // nóżka 10, TIM2_CH1 (AF2)
constexpr uint8_t kEnc1B = PA1;   // nóżka 11, TIM2_CH2 (AF2)
constexpr uint8_t kEnc1Sw = PA2;  // nóżka 12
constexpr uint8_t kEnc2A = PA6;   // nóżka 16, TIM3_CH1 (AF1)
constexpr uint8_t kEnc2B = PA7;   // nóżka 17, TIM3_CH2 (AF1)
constexpr uint8_t kEnc2Sw = PA3;  // nóżka 13
// Kierunek liczenia: +1 = obrót w prawo daje dodatnią deltę. Zmień na −1, jeśli jest odwrotnie.
constexpr int8_t kEncoderDir = 1;
// Zliczenia timera (tryb x4) na jeden zatrzask EC11E15244G1: 15 impulsów × 4 / 30 zatrzasków.
constexpr uint8_t kEncoderCountsPerDetent = 2;

// Suwak ALPS RS45111 10 kΩ: dzielnik 3,3 V → ADC (pin 1 = GND na dole, pin 3 = 3,3 V u góry).
constexpr uint8_t kSlider = PB1;  // nóżka 19, ADC_IN9

// 12 × WS2812B-V6 na spodzie: dane PB15 (SPI2_MOSI, AF0) → 74AHCT1G125 → L1 … L12.
constexpr uint8_t kLedData = PB15;  // nóżka 28
constexpr uint8_t kLedCount = 12;
// Dioda przy klawiszu (błysk po naciśnięciu): łańcuch L1 … L12 = indeksy 0 … 11. Górny rząd
// K1–K4 nad diodami L9–L12, dolny K5–K8 pod L6, L5, L4, L3 (pcb/…/tools/design.py: LED).
constexpr uint8_t kKeyLed[kRows * kCols] = {8, 9, 10, 11, 5, 4, 3, 2};

}  // namespace board
}  // namespace chocpilot

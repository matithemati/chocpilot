// Efekty podświetlenia LED (ChocPilot v0) – czysta logika bez Arduino, testowana w native.
#pragma once

#include <stdint.h>

#include "device_config.h"

namespace chocpilot {

struct Rgb {
  uint8_t r, g, b;
};

// Jasność 255 w ustawieniach = kLedMaxLevel/255 pełnej mocy diody: 12 × WS2812B przy pełnej
// bieli to ok. 720 mA, po ograniczeniu ok. 230 mA – razem z LCD i MCU mieści się w 500 mA USB.
constexpr uint8_t kLedMaxLevel = 80;
constexpr uint32_t kLedReactMs = 400;  // czas wygaszania błysku po naciśnięciu klawisza

struct LedFrame {
  uint32_t now = 0;
  bool online = false;
  bool sleeping = false;  // wygaszacz ekranu – diody też gasną
  bool test = false;      // tryb testu: kolejno czerwony, zielony, niebieski, biały
  // Błysk klawiszy: bit k = klawisz k+1 wciśnięty niedawno, keyDownAt[k] = czas naciśnięcia.
  uint8_t reactMask = 0;
  const uint32_t* keyDownAt = nullptr;
  // Numer diody (0…count−1) przy klawiszu k+1; 0xFF = brak diody przy klawiszu.
  const uint8_t* keyLed = nullptr;
};

// Kolor w odcieniu hue (0–255 = pełne koło), pełne nasycenie i jasność.
Rgb hueToRgb(uint8_t hue);

// Wylicza kolory `count` diod dla ustawień i stanu. Zwraca maskę klawiszy, których błysk
// jeszcze trwa (do zapisania z powrotem w reactMask).
uint8_t renderLeds(const LedSettings& s, const LedFrame& f, Rgb* out, uint8_t count);

}  // namespace chocpilot

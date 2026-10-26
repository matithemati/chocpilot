// Napisy stałe w pamięci programu. Na AVR (ATmega32U4, 2,5 KB RAM) literały trafiałyby do RAM,
// więc tabele i komunikaty leżą w PROGMEM i są czytane przez pgm_read_*. Na pozostałych
// platformach (RP2040, ESP32, testy native) to zwykłe wskaźniki – makra niczego nie zmieniają.
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#if defined(__AVR__)
#include <avr/pgmspace.h>

class __FlashStringHelper;

namespace chocpilot {
// Komunikat w pamięci programu (zgodny z F() z Arduino).
using FlashText = const __FlashStringHelper*;
}  // namespace chocpilot

#define CHOCPILOT_PROGMEM PROGMEM
// Literał w pamięci programu jako const char* (do funkcji *_P / pgmByte).
#define CHOCPILOT_P(s) PSTR(s)
// Literał w pamięci programu jako FlashText.
#define CHOCPILOT_F(s) (reinterpret_cast<::chocpilot::FlashText>(PSTR(s)))

#else

namespace chocpilot {
using FlashText = const char*;
}  // namespace chocpilot

#define CHOCPILOT_PROGMEM
#define CHOCPILOT_P(s) (s)
#define CHOCPILOT_F(s) (s)

#endif

namespace chocpilot {

inline uint8_t pgmByte(const void* p) {
#if defined(__AVR__)
  return pgm_read_byte(p);
#else
  return *static_cast<const uint8_t*>(p);
#endif
}

inline uint16_t pgmWord(const void* p) {
#if defined(__AVR__)
  return pgm_read_word(p);
#else
  return *static_cast<const uint16_t*>(p);
#endif
}

inline const char* flashChars(FlashText s) { return reinterpret_cast<const char*>(s); }

// Czy `len` bajtów z RAM równa się napisowi z pamięci programu (zakończonemu \0)?
inline bool equalsP(const char* ram, size_t len, const char* pgm) {
  for (size_t i = 0; i < len; ++i) {
    if (pgmByte(pgm + i) != static_cast<uint8_t>(ram[i])) return false;
  }
  return pgmByte(pgm + len) == 0;
}

}  // namespace chocpilot

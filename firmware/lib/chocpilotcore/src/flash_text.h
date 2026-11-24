// Napisy stałe. STM32 (i testy native) czytają stałe wprost z flash, więc FlashText to zwykły
// const char*, a makra CHOCPILOT_P / CHOCPILOT_F niczego nie zmieniają – zostały jako jedno
// miejsce na ewentualną platformę z osobną przestrzenią adresową pamięci programu.
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace chocpilot {
using FlashText = const char*;
}  // namespace chocpilot

#define CHOCPILOT_PROGMEM
#define CHOCPILOT_P(s) (s)
#define CHOCPILOT_F(s) (s)


namespace chocpilot {

inline uint8_t pgmByte(const void* p) {
  return *static_cast<const uint8_t*>(p);
}

inline uint16_t pgmWord(const void* p) {
  return *static_cast<const uint16_t*>(p);
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

// Krój 5×7 ASCII i dekodowanie UTF-8 z transliteracją polskich liter – wspólne dla ekranów.
#pragma once

#include <stdint.h>

namespace chocpilot {

constexpr uint8_t kGlyphW = 5;
constexpr uint8_t kGlyphH = 7;

// Znaki ASCII 32–126 w pamięci programu (pgmByte): 5 kolumn na znak, bit 0 = górny wiersz.
extern const uint8_t kFont5x7[];

// Kolejny znak napisu UTF-8 jako znak ASCII do narysowania (ą → a, Ł → L, inne spoza ASCII → ?);
// 0 = koniec napisu.
char nextChar(const char*& s);

}  // namespace chocpilot

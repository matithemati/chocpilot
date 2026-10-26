// Minimalna grafika ChocPilot: podzbiór API U8G2 używany przez display.cpp. Ekran 2,42"
// (SSD1309 128×64) jest rysowany pasami po 8 wierszy (bufor 128 B na stosie, jak tryb
// stronicowy U8g2) i wysyłany przez sterownik U8x8. Biblioteka U8g2 z czcionkami nie mieści się
// w 28 KB flash ATmega32U4.
//
// I²C: sprzętowy TWI (własna obsługa rejestrów, bez biblioteki Wire i jej buforów w RAM). Gdy
// ekran odpowiada dopiero po zamianie linii – programowe I²C U8x8 na zamienionych pinach.
//
// Jeden krój 5×7 (ASCII) w pamięci programu; „czcionki” to sposoby jego rysowania: skala 1×–3×
// i pogrubienie. Polskie litery są zamieniane na łacińskie odpowiedniki (ą → a, Ł → L, ...).
#pragma once

#include <U8x8lib.h>
#include <stdint.h>

namespace chocpilot {

// Opis „czcionki”: {skala X, skala Y, pogrubienie (0/1)}.
extern const uint8_t kMiniFont1x[];
extern const uint8_t kMiniFontBold[];
extern const uint8_t kMiniFont2x[];
extern const uint8_t kMiniFont3x[];

class MiniGfx {
 public:
  static constexpr uint8_t kWidth = 128;
  static constexpr uint8_t kHeight = 64;
  static constexpr uint8_t kPages = kHeight / 8;
  static constexpr uint8_t kNoPin = 0xFF;

  // Sprzętowy TWI: włączenie (z podciąganiem linii), wyłączenie i test adresu (7-bit).
  static void twiBegin(uint8_t sdaPin, uint8_t sclPin);
  static void twiEnd();
  static bool twiProbe(uint8_t address);

  // Start ekranu pod adresem 7-bitowym. softSda/softScl != kNoPin → programowe I²C na tych
  // pinach zamiast TWI.
  bool begin(uint8_t address, uint8_t softSda = kNoPin, uint8_t softScl = kNoPin);
  void setPowerSave(uint8_t enable) { u8x8_SetPowerSave(&u8x8_, enable); }
  void setContrast(uint8_t value) { u8x8_SetContrast(&u8x8_, value); }
  void setFlip(bool flip) { u8x8_SetFlipMode(&u8x8_, flip ? 1 : 0); }

  // Rysowanie: firstPage(bufor kWidth bajtów), potem te same polecenia dla każdego pasa,
  // dopóki nextPage() zwraca true.
  void firstPage(uint8_t* buf);
  bool nextPage();

  void setFont(const uint8_t* font) { font_ = font; }
  void setDrawColor(uint8_t color) { color_ = color; }

  // Napisy UTF-8; maxChars ogranicza liczbę znaków (dzielenie etykiet na wiersze).
  int getUTF8Width(const char* text, uint8_t maxChars = 0xFF) const;
  // y = linia bazowa (jak w U8g2): znak zajmuje wiersze y − 7·skalaY … y − 1.
  void drawUTF8(int x, int y, const char* text, uint8_t maxChars = 0xFF);
  static uint8_t charCount(const char* text);
  // Wskaźnik za n-tym znakiem napisu (albo na \0).
  static const char* skipChars(const char* text, uint8_t n);

  void drawBox(int x, int y, int w, int h);
  void drawFrame(int x, int y, int w, int h);
  void drawVLine(int x, int y, int h) { drawBox(x, y, 1, h); }
  void drawHLine(int x, int y, int w) { drawBox(x, y, w, 1); }
  void drawDisc(int x, int y, int r);
  void drawCircle(int x, int y, int r);

 private:
  int advance() const;
  void drawGlyph(int x, int top, char c);

  u8x8_t u8x8_;
  uint8_t* buf_ = nullptr;
  uint8_t page_ = 0;
  const uint8_t* font_ = kMiniFont1x;
  uint8_t color_ = 1;
};

}  // namespace chocpilot

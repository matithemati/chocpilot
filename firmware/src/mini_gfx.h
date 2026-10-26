// Minimalna grafika dla CHOCPILOT_COMPACT (ATmega32U4): podzbiór API U8G2 używany przez display.cpp.
// Ekran jest rysowany pasami po 8 wierszy (bufor 128 B na stosie, jak tryb stronicowy U8g2)
// i wysyłany przez U8x8 (sterownik SSD1306 + programowe I²C). Biblioteka U8g2 z czcionkami
// zajmowała ok. 8 KB flash – za dużo na 28 KB.
//
// Jeden krój 5×7 (ASCII) w pamięci programu; „czcionki” to sposoby jego rysowania: skala 1×/2×
// i pogrubienie. Polskie litery są zamieniane na łacińskie odpowiedniki (ą → a, Ł → L, ...).
#pragma once

#if defined(CHOCPILOT_COMPACT)

#include <U8x8lib.h>
#include <stdint.h>

namespace chocpilot {

// Opis „czcionki”: {skala X, skala Y, pogrubienie (0/1)}.
extern const uint8_t kMiniFont1x[];
extern const uint8_t kMiniFontBold[];
extern const uint8_t kMiniFont2x[];

class MiniGfx {
 public:
  static constexpr uint8_t kWidth = 128;
  static constexpr uint8_t kPages = 4;  // 32 wiersze = 4 pasy po 8

  MiniGfx(uint8_t clock, uint8_t data) : oled_(clock, data, U8X8_PIN_NONE) {}

  u8x8_t* getU8x8() { return oled_.getU8x8(); }
  void setI2CAddress(uint8_t address) { oled_.setI2CAddress(address); }
  bool begin() { return oled_.begin(); }
  void setPowerSave(uint8_t enable) { oled_.setPowerSave(enable); }
  void setContrast(uint8_t value) { oled_.setContrast(value); }
  void setFlip(bool flip) { oled_.setFlipMode(flip ? 1 : 0); }
  void enableUTF8Print() {}

  // Rysowanie: firstPage(bufor kWidth bajtów), potem te same polecenia dla każdego pasa,
  // dopóki nextPage() zwraca true.
  void firstPage(uint8_t* buf);
  bool nextPage();

  void setFont(const uint8_t* font) { font_ = font; }
  void setFontMode(uint8_t) {}
  void setDrawColor(uint8_t color) { color_ = color; }

  int getUTF8Width(const char* text) const;
  // y = linia bazowa (jak w U8g2): znak zajmuje wiersze y − 7·skalaY … y − 1.
  void drawUTF8(int x, int y, const char* text);

  void drawBox(int x, int y, int w, int h);
  void drawFrame(int x, int y, int w, int h);
  void drawVLine(int x, int y, int h) { drawBox(x, y, 1, h); }
  void drawDisc(int x, int y, int r);
  void drawCircle(int x, int y, int r);

 private:
  int advance() const;
  void drawGlyph(int x, int top, char c);

  U8X8_SSD1306_128X32_UNIVISION_SW_I2C oled_;
  uint8_t* buf_ = nullptr;
  uint8_t page_ = 0;
  const uint8_t* font_ = kMiniFont1x;
  uint8_t color_ = 1;
};

}  // namespace chocpilot

#endif  // CHOCPILOT_COMPACT

// Sterownik LCD ST7789V 240×320 (Waveshare 2inch LCD Module) na SPI1, w poziomie 320×240.
// Bez bufora ramki (16 KB RAM): prostokąty i znaki są wysyłane od razu do pamięci ekranu.
#pragma once

#include <stdint.h>

namespace chocpilot {
namespace tft {

constexpr int kWidth = 320;
constexpr int kHeight = 240;

// Kolor RGB565.
constexpr uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) {
  return static_cast<uint16_t>((r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3);
}

void begin();
// flip = obrót o 180° (ustawienie „flip” z aplikacji).
void setFlip(bool flip);
// Jasność podświetlenia 0–255 (0 = wyłączone).
void setBacklight(uint8_t level);
// Uśpienie panelu (wygaszacz) – z podświetleniem wyłączanym osobno.
void setSleep(bool sleep);

void fillRect(int x, int y, int w, int h, uint16_t color);
// Strumień pikseli do prostokąta (w pełni na ekranie): beginPixels, potem dokładnie w × h
// wywołań pushPixel, wiersz po wierszu.
void beginPixels(int x, int y, int w, int h);
void pushPixel(uint16_t color);
void fillScreen(uint16_t color);
// Ramka o grubości t.
void drawFrame(int x, int y, int w, int h, int t, uint16_t color);

// Napis UTF-8 krojem 5×7 w skali `scale` (znak 6·scale × 7·scale px z odstępem), lewy górny róg
// w (x, y). Tło komórek znaków malowane kolorem bg. maxChars ogranicza liczbę znaków.
void drawText(int x, int y, const char* text, uint8_t scale, uint16_t fg, uint16_t bg,
              uint8_t maxChars = 0xFF);
int textWidth(const char* text, uint8_t scale, uint8_t maxChars = 0xFF);
constexpr int textHeight(uint8_t scale) { return 7 * scale; }

}  // namespace tft
}  // namespace chocpilot

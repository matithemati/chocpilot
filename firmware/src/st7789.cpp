#include "st7789.h"

#include <Arduino.h>

#include "boards/board.h"
#include "flash_text.h"
#include "font5x7.h"

namespace chocpilot {
namespace tft {

namespace {

// Polecenia ST7789V (datasheet, rozdz. 9).
enum : uint8_t {
  kSwReset = 0x01,
  kSleepIn = 0x10,
  kSleepOut = 0x11,
  kNormalOn = 0x13,
  kInvOn = 0x21,
  kDispOn = 0x29,
  kCaSet = 0x2A,
  kRaSet = 0x2B,
  kRamWr = 0x2C,
  kMadCtl = 0x36,
  kColMod = 0x3A,
};

// MADCTL: poziomo (MV) – panel 240×320 ma natywnie orientację pionową.
constexpr uint8_t kMadLandscape = 0x60;         // MX | MV
constexpr uint8_t kMadLandscapeFlipped = 0xA0;  // MY | MV

// Szybkie sterowanie pinami DC / CS (BSRR zamiast digitalWrite w pętlach rysowania).
GPIO_TypeDef* gDcPort;
uint32_t gDcMask;

inline void spiWrite(uint8_t b) {
  while (!(SPI1->SR & SPI_SR_TXE)) {
  }
  *reinterpret_cast<volatile uint8_t*>(&SPI1->DR) = b;
}

inline void spiWait() {
  while (SPI1->SR & SPI_SR_BSY) {
  }
}

inline void dcCommand() {
  spiWait();
  gDcPort->BRR = gDcMask;
}

inline void dcData() {
  spiWait();
  gDcPort->BSRR = gDcMask;
}

void command(uint8_t cmd) {
  dcCommand();
  spiWrite(cmd);
  dcData();
}

void command(uint8_t cmd, const uint8_t* data, uint8_t len) {
  command(cmd);
  for (uint8_t i = 0; i < len; ++i) spiWrite(data[i]);
}

void setWindow(int x0, int y0, int x1, int y1) {
  const uint8_t ca[4] = {static_cast<uint8_t>(x0 >> 8), static_cast<uint8_t>(x0),
                         static_cast<uint8_t>(x1 >> 8), static_cast<uint8_t>(x1)};
  const uint8_t ra[4] = {static_cast<uint8_t>(y0 >> 8), static_cast<uint8_t>(y0),
                         static_cast<uint8_t>(y1 >> 8), static_cast<uint8_t>(y1)};
  command(kCaSet, ca, 4);
  command(kRaSet, ra, 4);
  command(kRamWr);
}

inline void pushColor(uint16_t c) {
  spiWrite(static_cast<uint8_t>(c >> 8));
  spiWrite(static_cast<uint8_t>(c));
}

// SPI1 nadawczy (BIDIMODE + BIDIOE), master, 8 bitów, tryb 3 (CPOL = CPHA = 1) jak w przykładach
// Waveshare – ST7789V próbkuje na zboczu narastającym, a bezczynny SCK w stanie wysokim nie
// daje fałszywego zbocza przy stale aktywnym CS. Zegar fPCLK/4 = 12 MHz: ST7789V dopuszcza
// zapis z cyklem ≥ 66 ns (ok. 15 MHz), a moduł jest podłączony kablem PH2.0 – 24 MHz byłoby
// poza specyfikacją. Pełna klatka 320×240 ok. 0,1 s, ale rysowane są tylko zmienione pasy.
void spiInit() {
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_SPI1_CLK_ENABLE();
  GPIO_InitTypeDef io = {};
  io.Pin = digitalPinToBitMask(board::kLcdSck) | digitalPinToBitMask(board::kLcdMosi);
  io.Mode = GPIO_MODE_AF_PP;
  io.Pull = GPIO_NOPULL;
  io.Speed = GPIO_SPEED_FREQ_HIGH;
  io.Alternate = GPIO_AF0_SPI1;
  HAL_GPIO_Init(GPIOB, &io);

  SPI1->CR1 = 0;
  SPI1->CR2 = SPI_CR2_DS_2 | SPI_CR2_DS_1 | SPI_CR2_DS_0 | SPI_CR2_FRXTH;  // 8 bitów
  SPI1->CR1 = SPI_CR1_BIDIMODE | SPI_CR1_BIDIOE | SPI_CR1_MSTR | SPI_CR1_SSM | SPI_CR1_SSI |
              SPI_CR1_CPOL | SPI_CR1_CPHA | SPI_CR1_BR_0;
  SPI1->CR1 |= SPI_CR1_SPE;
}

}  // namespace

void begin() {
  pinMode(board::kLcdCs, OUTPUT);
  pinMode(board::kLcdDc, OUTPUT);
  pinMode(board::kLcdRst, OUTPUT);
  digitalWrite(board::kLcdCs, HIGH);  // nieaktywny, dopóki SCK nie ma stanu spoczynku trybu 3
  digitalWrite(board::kLcdDc, HIGH);
  gDcPort = digitalPinToPort(board::kLcdDc);
  gDcMask = digitalPinToBitMask(board::kLcdDc);
  setBacklight(0);
  spiInit();
  digitalWrite(board::kLcdCs, LOW);  // jedyne urządzenie na SPI1 – CS na stałe aktywny

  digitalWrite(board::kLcdRst, HIGH);
  delay(5);
  digitalWrite(board::kLcdRst, LOW);
  delay(20);
  digitalWrite(board::kLcdRst, HIGH);
  delay(120);

  command(kSwReset);
  delay(150);
  command(kSleepOut);
  delay(120);
  static const uint8_t kColor16[] = {0x55};  // RGB565
  command(kColMod, kColor16, 1);
  // Ustawienia zasilania i gammy jak w przykładach Waveshare dla 2inch LCD Module.
  static const uint8_t kPorch[] = {0x0C, 0x0C, 0x00, 0x33, 0x33};
  command(0xB2, kPorch, sizeof(kPorch));
  static const uint8_t kGate[] = {0x35};
  command(0xB7, kGate, 1);
  static const uint8_t kVcom[] = {0x1F};
  command(0xBB, kVcom, 1);
  static const uint8_t kLcm[] = {0x2C};
  command(0xC0, kLcm, 1);
  static const uint8_t kVdvVrhEn[] = {0x01};
  command(0xC2, kVdvVrhEn, 1);
  static const uint8_t kVrh[] = {0x12};
  command(0xC3, kVrh, 1);
  static const uint8_t kVdv[] = {0x20};
  command(0xC4, kVdv, 1);
  static const uint8_t kFrameRate[] = {0x0F};
  command(0xC6, kFrameRate, 1);
  static const uint8_t kPower[] = {0xA4, 0xA1};
  command(0xD0, kPower, sizeof(kPower));
  static const uint8_t kGammaPos[] = {0xD0, 0x08, 0x11, 0x08, 0x0C, 0x15, 0x39,
                                      0x33, 0x50, 0x36, 0x13, 0x14, 0x29, 0x2D};
  command(0xE0, kGammaPos, sizeof(kGammaPos));
  static const uint8_t kGammaNeg[] = {0xD0, 0x08, 0x10, 0x08, 0x06, 0x06, 0x39,
                                      0x44, 0x51, 0x0B, 0x16, 0x14, 0x2F, 0x31};
  command(0xE1, kGammaNeg, sizeof(kGammaNeg));
  command(kInvOn);  // panel IPS Waveshare wymaga inwersji dla poprawnych kolorów
  setFlip(false);
  command(kNormalOn);
  fillScreen(0);
  command(kDispOn);
  delay(20);
}

void setFlip(bool flip) {
  const uint8_t mad = flip ? kMadLandscapeFlipped : kMadLandscape;
  command(kMadCtl, &mad, 1);
}

void setBacklight(uint8_t level) { analogWrite(board::kLcdBl, level); }

void setSleep(bool sleep) {
  command(sleep ? kSleepIn : kSleepOut);
  delay(sleep ? 5 : 120);
}

void fillRect(int x, int y, int w, int h, uint16_t color) {
  if (x < 0) {
    w += x;
    x = 0;
  }
  if (y < 0) {
    h += y;
    y = 0;
  }
  if (x + w > kWidth) w = kWidth - x;
  if (y + h > kHeight) h = kHeight - y;
  if (w <= 0 || h <= 0) return;
  setWindow(x, y, x + w - 1, y + h - 1);
  const uint8_t hi = static_cast<uint8_t>(color >> 8);
  const uint8_t lo = static_cast<uint8_t>(color);
  for (uint32_t n = static_cast<uint32_t>(w) * static_cast<uint32_t>(h); n > 0; --n) {
    spiWrite(hi);
    spiWrite(lo);
  }
}

void fillScreen(uint16_t color) { fillRect(0, 0, kWidth, kHeight, color); }

void beginPixels(int x, int y, int w, int h) { setWindow(x, y, x + w - 1, y + h - 1); }

void pushPixel(uint16_t color) { pushColor(color); }

void drawFrame(int x, int y, int w, int h, int t, uint16_t color) {
  fillRect(x, y, w, t, color);
  fillRect(x, y + h - t, w, t, color);
  fillRect(x, y + t, t, h - 2 * t, color);
  fillRect(x + w - t, y + t, t, h - 2 * t, color);
}

int textWidth(const char* text, uint8_t scale, uint8_t maxChars) {
  uint8_t n = 0;
  while (n < maxChars && nextChar(text) != 0) ++n;
  return n == 0 ? 0 : n * 6 * scale - scale;
}

void drawText(int x, int y, const char* text, uint8_t scale, uint16_t fg, uint16_t bg,
              uint8_t maxChars) {
  const int cellW = 6 * scale;
  const int cellH = 7 * scale;
  if (y < 0 || y + cellH > kHeight) return;
  for (char c; maxChars > 0 && (c = nextChar(text)) != 0; --maxChars, x += cellW) {
    if (x < 0) continue;
    if (x + cellW > kWidth) break;
    if (c < 32 || c > 126) c = '?';
    const uint8_t* glyph = kFont5x7 + (c - 32) * kGlyphW;
    setWindow(x, y, x + cellW - 1, y + cellH - 1);
    for (int row = 0; row < cellH; ++row) {
      const uint8_t bit = static_cast<uint8_t>(1u << (row / scale));
      for (int col = 0; col < cellW; ++col) {
        const int gc = col / scale;
        const bool on = gc < kGlyphW && (pgmByte(glyph + gc) & bit);
        pushColor(on ? fg : bg);
      }
    }
  }
}

}  // namespace tft
}  // namespace chocpilot

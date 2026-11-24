#include "mini_gfx.h"

#include <Arduino.h>
#include <string.h>

#include "flash_text.h"
#include "font5x7.h"

namespace chocpilot {

const uint8_t kMiniFont1x[] CHOCPILOT_PROGMEM = {1, 1, 0, 1};
const uint8_t kMiniFontCondensed[] CHOCPILOT_PROGMEM = {1, 1, 0, 0};
const uint8_t kMiniFontBold[] CHOCPILOT_PROGMEM = {1, 1, 1, 1};
const uint8_t kMiniFont2x[] CHOCPILOT_PROGMEM = {2, 2, 0, 1};
const uint8_t kMiniFont3x[] CHOCPILOT_PROGMEM = {3, 3, 0, 1};

namespace {

// --- sprzętowy TWI (ATmega32U4) ---

constexpr uint32_t kTwiHz = 400000;
constexpr uint16_t kTwiTimeout = 4000;  // pętle oczekiwania (ok. 1–2 ms)

bool gSoftI2c = false;
bool gTwiOk = true;  // false po błędzie – reszta transmisji jest pomijana

bool twiWait() {
  for (uint16_t i = 0; i < kTwiTimeout; ++i) {
    if (TWCR & _BV(TWINT)) return true;
  }
  return false;
}

uint8_t twiStatus() { return TWSR & 0xF8; }

// START + adres z bitem zapisu (adres 8-bitowy, jak w U8x8). true = urządzenie potwierdziło.
bool twiStart(uint8_t address8) {
  TWCR = _BV(TWINT) | _BV(TWSTA) | _BV(TWEN);
  if (!twiWait() || (twiStatus() != 0x08 && twiStatus() != 0x10)) return false;
  TWDR = address8;
  TWCR = _BV(TWINT) | _BV(TWEN);
  return twiWait() && twiStatus() == 0x18;  // SLA+W, ACK
}

bool twiWrite(uint8_t value) {
  TWDR = value;
  TWCR = _BV(TWINT) | _BV(TWEN);
  return twiWait() && twiStatus() == 0x28;  // dane, ACK
}

void twiStop() {
  TWCR = _BV(TWINT) | _BV(TWSTO) | _BV(TWEN);
  for (uint16_t i = 0; i < kTwiTimeout && (TWCR & _BV(TWSTO)); ++i) {
  }
}

// Callback bajtów U8x8: TWI albo programowe I²C z biblioteki.
extern "C" uint8_t chocpilotByteCb(u8x8_t* u8x8, uint8_t msg, uint8_t argInt, void* argPtr) {
  if (gSoftI2c) return u8x8_byte_sw_i2c(u8x8, msg, argInt, argPtr);
  switch (msg) {
    case U8X8_MSG_BYTE_START_TRANSFER:
      gTwiOk = twiStart(u8x8_GetI2CAddress(u8x8));
      break;
    case U8X8_MSG_BYTE_SEND: {
      const uint8_t* data = static_cast<const uint8_t*>(argPtr);
      for (; argInt > 0 && gTwiOk; --argInt) gTwiOk = twiWrite(*data++);
      break;
    }
    case U8X8_MSG_BYTE_END_TRANSFER:
      twiStop();
      break;
    default:  // INIT (TWI włącza twiBegin), SET_DC – nieużywane przy I²C
      break;
  }
  return 1;
}

}  // namespace

void MiniGfx::twiBegin(uint8_t sdaPin, uint8_t sclPin) {
  pinMode(sdaPin, INPUT_PULLUP);  // słabe podciąganie obok rezystorów modułu
  pinMode(sclPin, INPUT_PULLUP);
  uint32_t twbr = (F_CPU / kTwiHz - 16) / 2;
  if (twbr < 10) twbr = 10;  // 8 MHz: ok. 220 kHz
  TWSR = 0;
  TWBR = static_cast<uint8_t>(twbr);
  TWCR = _BV(TWEN);
}

void MiniGfx::twiEnd() { TWCR = 0; }

bool MiniGfx::twiProbe(uint8_t address) {
  const bool ack = twiStart(static_cast<uint8_t>(address << 1));
  twiStop();
  return ack;
}

bool MiniGfx::begin(uint8_t address, uint8_t softSda, uint8_t softScl) {
  u8x8_Setup(&u8x8_, u8x8_d_ssd1309_128x64_noname2, u8x8_cad_ssd13xx_fast_i2c, chocpilotByteCb,
             u8x8_gpio_and_delay_arduino);
  gSoftI2c = softSda != kNoPin;
  if (gSoftI2c) {
    u8x8_SetPin(&u8x8_, U8X8_PIN_I2C_DATA, softSda);
    u8x8_SetPin(&u8x8_, U8X8_PIN_I2C_CLOCK, softScl);
  }
  u8x8_SetI2CAddress(&u8x8_, static_cast<uint8_t>(address << 1));
  gTwiOk = true;
  u8x8_InitDisplay(&u8x8_);
  u8x8_ClearDisplay(&u8x8_);
  u8x8_SetPowerSave(&u8x8_, 0);
  return gSoftI2c || gTwiOk;
}

void MiniGfx::firstPage(uint8_t* buf) {
  buf_ = buf;
  page_ = 0;
  memset(buf_, 0, kWidth);
}

bool MiniGfx::nextPage() {
  u8x8_DrawTile(&u8x8_, 0, page_, kWidth / 8, buf_);
  if (++page_ >= kPages) return false;
  memset(buf_, 0, kWidth);
  return true;
}

int MiniGfx::advance() const {
  return (kGlyphW + pgmByte(font_ + 3)) * pgmByte(font_) + pgmByte(font_ + 2);
}

uint8_t MiniGfx::charCount(const char* text) {
  uint8_t n = 0;
  while (nextChar(text) != 0) ++n;
  return n;
}

const char* MiniGfx::skipChars(const char* text, uint8_t n) {
  for (; n > 0 && *text != '\0'; --n) nextChar(text);
  return text;
}

int MiniGfx::getUTF8Width(const char* text, uint8_t maxChars) const {
  uint8_t n = 0;
  while (n < maxChars && nextChar(text) != 0) ++n;
  return n == 0 ? 0 : n * advance() - pgmByte(font_ + 3) * pgmByte(font_);
}

void MiniGfx::drawUTF8(int x, int y, const char* text, uint8_t maxChars) {
  const uint8_t sy = pgmByte(font_ + 1);
  const int top = y - kGlyphH * sy;
  // Napis poza bieżącym pasem – nic do rysowania.
  if (top >= (page_ + 1) * 8 || y <= page_ * 8) return;
  const int step = advance();
  for (char c; maxChars > 0 && (c = nextChar(text)) != 0 && x < kWidth; x += step, --maxChars) {
    drawGlyph(x, top, c);
  }
}

void MiniGfx::drawGlyph(int x, int top, char c) {
  if (c < 32 || c > 126) c = '?';
  const uint8_t* glyph = kFont5x7 + (c - 32) * kGlyphW;
  const uint8_t sx = pgmByte(font_);
  const uint8_t sy = pgmByte(font_ + 1);
  const uint8_t bold = pgmByte(font_ + 2);
  for (uint8_t col = 0; col < kGlyphW; ++col) {
    const uint8_t bits = pgmByte(glyph + col);
    for (uint8_t row = 0; row < kGlyphH; ++row) {
      if (bits & (1 << row)) drawBox(x + col * sx, top + row * sy, sx + bold, sy);
    }
  }
}

void MiniGfx::drawBox(int x, int y, int w, int h) {
  const int top = page_ * 8;
  const int y0 = y < top ? top : y;
  const int y1 = y + h > top + 8 ? top + 8 : y + h;  // bez y1
  if (y0 >= y1) return;
  const uint8_t mask = static_cast<uint8_t>((0xFF << (y0 - top)) & (0xFF >> (top + 8 - y1)));
  const int x0 = x < 0 ? 0 : x;
  const int x1 = x + w > kWidth ? kWidth : x + w;
  for (int i = x0; i < x1; ++i) {
    buf_[i] = color_ ? static_cast<uint8_t>(buf_[i] | mask) : static_cast<uint8_t>(buf_[i] & ~mask);
  }
}

void MiniGfx::drawFrame(int x, int y, int w, int h) {
  drawBox(x, y, w, 1);
  drawBox(x, y + h - 1, w, 1);
  drawBox(x, y, 1, h);
  drawBox(x + w - 1, y, 1, h);
}

void MiniGfx::drawDisc(int x, int y, int r) {
  for (int dy = -r; dy <= r; ++dy) {
    int dx = 0;
    while ((dx + 1) * (dx + 1) + dy * dy <= r * r) ++dx;
    drawBox(x - dx, y + dy, 2 * dx + 1, 1);
  }
}

void MiniGfx::drawCircle(int x, int y, int r) {
  // Okrąg = koło minus mniejsze koło w kolorze tła.
  drawDisc(x, y, r);
  color_ ^= 1;
  drawDisc(x, y, r - 1);
  color_ ^= 1;
}

}  // namespace chocpilot

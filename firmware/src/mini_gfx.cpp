#include "mini_gfx.h"

#include <Arduino.h>
#include <string.h>

#include "flash_text.h"

namespace chocpilot {

const uint8_t kMiniFont1x[] CHOCPILOT_PROGMEM = {1, 1, 0, 1};
const uint8_t kMiniFontCondensed[] CHOCPILOT_PROGMEM = {1, 1, 0, 0};
const uint8_t kMiniFontBold[] CHOCPILOT_PROGMEM = {1, 1, 1, 1};
const uint8_t kMiniFont2x[] CHOCPILOT_PROGMEM = {2, 2, 0, 1};
const uint8_t kMiniFont3x[] CHOCPILOT_PROGMEM = {3, 3, 0, 1};

namespace {

constexpr uint8_t kGlyphW = 5;
constexpr uint8_t kGlyphH = 7;

// Krój 5×7, znaki ASCII 32–126: 5 kolumn na znak, bit 0 = górny wiersz.
const uint8_t kFont5x7[] CHOCPILOT_PROGMEM = {
    0x00, 0x00, 0x00, 0x00, 0x00,  // ' '
    0x00, 0x00, 0x5F, 0x00, 0x00,  // !
    0x00, 0x07, 0x00, 0x07, 0x00,  // "
    0x14, 0x7F, 0x14, 0x7F, 0x14,  // #
    0x24, 0x2A, 0x7F, 0x2A, 0x12,  // $
    0x23, 0x13, 0x08, 0x64, 0x62,  // %
    0x36, 0x49, 0x55, 0x22, 0x50,  // &
    0x00, 0x05, 0x03, 0x00, 0x00,  // '
    0x00, 0x1C, 0x22, 0x41, 0x00,  // (
    0x00, 0x41, 0x22, 0x1C, 0x00,  // )
    0x08, 0x2A, 0x1C, 0x2A, 0x08,  // *
    0x08, 0x08, 0x3E, 0x08, 0x08,  // +
    0x00, 0x50, 0x30, 0x00, 0x00,  // ,
    0x08, 0x08, 0x08, 0x08, 0x08,  // -
    0x00, 0x60, 0x60, 0x00, 0x00,  // .
    0x20, 0x10, 0x08, 0x04, 0x02,  // /
    0x3E, 0x51, 0x49, 0x45, 0x3E,  // 0
    0x00, 0x42, 0x7F, 0x40, 0x00,  // 1
    0x42, 0x61, 0x51, 0x49, 0x46,  // 2
    0x21, 0x41, 0x45, 0x4B, 0x31,  // 3
    0x18, 0x14, 0x12, 0x7F, 0x10,  // 4
    0x27, 0x45, 0x45, 0x45, 0x39,  // 5
    0x3C, 0x4A, 0x49, 0x49, 0x30,  // 6
    0x01, 0x71, 0x09, 0x05, 0x03,  // 7
    0x36, 0x49, 0x49, 0x49, 0x36,  // 8
    0x06, 0x49, 0x49, 0x29, 0x1E,  // 9
    0x00, 0x36, 0x36, 0x00, 0x00,  // :
    0x00, 0x56, 0x36, 0x00, 0x00,  // ;
    0x08, 0x14, 0x22, 0x41, 0x00,  // <
    0x14, 0x14, 0x14, 0x14, 0x14,  // =
    0x00, 0x41, 0x22, 0x14, 0x08,  // >
    0x02, 0x01, 0x51, 0x09, 0x06,  // ?
    0x32, 0x49, 0x79, 0x41, 0x3E,  // @
    0x7E, 0x11, 0x11, 0x11, 0x7E,  // A
    0x7F, 0x49, 0x49, 0x49, 0x36,  // B
    0x3E, 0x41, 0x41, 0x41, 0x22,  // C
    0x7F, 0x41, 0x41, 0x22, 0x1C,  // D
    0x7F, 0x49, 0x49, 0x49, 0x41,  // E
    0x7F, 0x09, 0x09, 0x09, 0x01,  // F
    0x3E, 0x41, 0x49, 0x49, 0x7A,  // G
    0x7F, 0x08, 0x08, 0x08, 0x7F,  // H
    0x00, 0x41, 0x7F, 0x41, 0x00,  // I
    0x20, 0x40, 0x41, 0x3F, 0x01,  // J
    0x7F, 0x08, 0x14, 0x22, 0x41,  // K
    0x7F, 0x40, 0x40, 0x40, 0x40,  // L
    0x7F, 0x02, 0x0C, 0x02, 0x7F,  // M
    0x7F, 0x04, 0x08, 0x10, 0x7F,  // N
    0x3E, 0x41, 0x41, 0x41, 0x3E,  // O
    0x7F, 0x09, 0x09, 0x09, 0x06,  // P
    0x3E, 0x41, 0x51, 0x21, 0x5E,  // Q
    0x7F, 0x09, 0x19, 0x29, 0x46,  // R
    0x46, 0x49, 0x49, 0x49, 0x31,  // S
    0x01, 0x01, 0x7F, 0x01, 0x01,  // T
    0x3F, 0x40, 0x40, 0x40, 0x3F,  // U
    0x1F, 0x20, 0x40, 0x20, 0x1F,  // V
    0x3F, 0x40, 0x38, 0x40, 0x3F,  // W
    0x63, 0x14, 0x08, 0x14, 0x63,  // X
    0x07, 0x08, 0x70, 0x08, 0x07,  // Y
    0x61, 0x51, 0x49, 0x45, 0x43,  // Z
    0x00, 0x7F, 0x41, 0x41, 0x00,  // [
    0x02, 0x04, 0x08, 0x10, 0x20,  // backslash
    0x00, 0x41, 0x41, 0x7F, 0x00,  // ]
    0x04, 0x02, 0x01, 0x02, 0x04,  // ^
    0x40, 0x40, 0x40, 0x40, 0x40,  // _
    0x00, 0x01, 0x02, 0x04, 0x00,  // `
    0x20, 0x54, 0x54, 0x54, 0x78,  // a
    0x7F, 0x48, 0x44, 0x44, 0x38,  // b
    0x38, 0x44, 0x44, 0x44, 0x20,  // c
    0x38, 0x44, 0x44, 0x48, 0x7F,  // d
    0x38, 0x54, 0x54, 0x54, 0x18,  // e
    0x08, 0x7E, 0x09, 0x01, 0x02,  // f
    0x08, 0x54, 0x54, 0x54, 0x3C,  // g
    0x7F, 0x08, 0x04, 0x04, 0x78,  // h
    0x00, 0x44, 0x7D, 0x40, 0x00,  // i
    0x20, 0x40, 0x44, 0x3D, 0x00,  // j
    0x7F, 0x10, 0x28, 0x44, 0x00,  // k
    0x00, 0x41, 0x7F, 0x40, 0x00,  // l
    0x7C, 0x04, 0x18, 0x04, 0x78,  // m
    0x7C, 0x08, 0x04, 0x04, 0x78,  // n
    0x38, 0x44, 0x44, 0x44, 0x38,  // o
    0x7C, 0x14, 0x14, 0x14, 0x08,  // p
    0x08, 0x14, 0x14, 0x18, 0x7C,  // q
    0x7C, 0x08, 0x04, 0x04, 0x08,  // r
    0x48, 0x54, 0x54, 0x54, 0x20,  // s
    0x04, 0x3F, 0x44, 0x40, 0x20,  // t
    0x3C, 0x40, 0x40, 0x20, 0x7C,  // u
    0x1C, 0x20, 0x40, 0x20, 0x1C,  // v
    0x3C, 0x40, 0x30, 0x40, 0x3C,  // w
    0x44, 0x28, 0x10, 0x28, 0x44,  // x
    0x0C, 0x50, 0x50, 0x50, 0x3C,  // y
    0x44, 0x64, 0x54, 0x4C, 0x44,  // z
    0x00, 0x08, 0x36, 0x41, 0x00,  // {
    0x00, 0x00, 0x7F, 0x00, 0x00,  // |
    0x00, 0x41, 0x36, 0x08, 0x00,  // }
    0x08, 0x04, 0x08, 0x10, 0x08,  // ~
};

// Polskie litery → odpowiedniki bez znaków diakrytycznych.
struct Transliteration {
  uint16_t codepoint;
  char ascii;
};

const Transliteration kPolish[] CHOCPILOT_PROGMEM = {
    {0x0104, 'A'}, {0x0105, 'a'}, {0x0106, 'C'}, {0x0107, 'c'}, {0x0118, 'E'}, {0x0119, 'e'},
    {0x0141, 'L'}, {0x0142, 'l'}, {0x0143, 'N'}, {0x0144, 'n'}, {0x00D3, 'O'}, {0x00F3, 'o'},
    {0x015A, 'S'}, {0x015B, 's'}, {0x0179, 'Z'}, {0x017A, 'z'}, {0x017B, 'Z'}, {0x017C, 'z'},
};

// Kolejny znak napisu UTF-8 jako znak ASCII do narysowania; 0 = koniec napisu.
char nextChar(const char*& s) {
  const uint8_t lead = static_cast<uint8_t>(*s);
  if (lead == 0) return 0;
  ++s;
  if (lead < 0x80) return static_cast<char>(lead);
  uint8_t extra = 0;
  uint16_t codepoint = 0;
  if ((lead & 0xE0) == 0xC0) {
    extra = 1;
    codepoint = lead & 0x1F;
  } else if ((lead & 0xF0) == 0xE0) {
    extra = 2;
    codepoint = lead & 0x0F;
  } else if ((lead & 0xF8) == 0xF0) {
    extra = 3;
    codepoint = 0xFFFF;  // poza zakresem tabeli
  }
  for (; extra > 0 && (static_cast<uint8_t>(*s) & 0xC0) == 0x80; --extra, ++s) {
    if (codepoint != 0xFFFF) codepoint = static_cast<uint16_t>(codepoint << 6 | (*s & 0x3F));
  }
  for (const Transliteration& t : kPolish) {
    if (pgmWord(&t.codepoint) == codepoint) return static_cast<char>(pgmByte(&t.ascii));
  }
  return '?';
}


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

#include "display.h"

#include <Arduino.h>
#include <string.h>

#include "boards/board.h"
#include "config.h"
#include "mini_gfx.h"
#include "time_util.h"

namespace chocpilot {

namespace {

// Minimalna grafika (mini_gfx.h): jeden krój 5×7 w kilku skalach zamiast czcionek U8g2.
MiniGfx u8g2;

const uint8_t* const kFontSmall = kMiniFont1x;
const uint8_t* const kFontMedium = kMiniFontBold;
const uint8_t* const kFontLarge = kMiniFont2x;
const uint8_t* const kFontHuge = kMiniFont3x;

constexpr int kWidth = MiniGfx::kWidth;
constexpr int kHeight = MiniGfx::kHeight;
constexpr uint32_t kSplashMs = 1500;
constexpr uint32_t kTestRedrawMs = 50;

// Siatka 2 × 4 pod paskiem tytułu: komórki 32 × 27 px, etykieta w 1 albo 2 wierszach po 5 znaków.
constexpr int kTitleBarH = 10;
constexpr int kCellW = kWidth / kCols;
constexpr int kCellTop = kTitleBarH + 1;
constexpr int kCellH = 27;
constexpr uint8_t kCellLineChars = 5;

// Rysuje napis wyśrodkowany w poziomie, wybierając największą czcionkę, która się mieści.
void drawCenteredFit(const char* text, int baseline, const uint8_t* const* fonts, int count) {
  for (int i = 0; i < count; ++i) {
    u8g2.setFont(fonts[i]);
    const int w = u8g2.getUTF8Width(text);
    if (w <= kWidth - 2 || i == count - 1) {
      u8g2.drawUTF8((kWidth - w) / 2, baseline, text);
      return;
    }
  }
}

void drawCentered(const char* text, int cx, int baseline, uint8_t maxChars = 0xFF) {
  const int w = u8g2.getUTF8Width(text, maxChars);
  u8g2.drawUTF8(cx - w / 2, baseline, text, maxChars);
}

// Etykieta klawisza w komórce siatki: do 5 znaków w jednym wierszu, dłuższa w dwóch
// (podział na spacji, jeśli wypada w pierwszych 5 znakach).
void drawCellLabel(const char* label, int cx, int top) {
  if (MiniGfx::charCount(label) <= kCellLineChars) {
    drawCentered(label, cx, top + 17);
    return;
  }
  uint8_t first = kCellLineChars;
  const char* rest = MiniGfx::skipChars(label, kCellLineChars);
  for (uint8_t i = kCellLineChars; i > 0; --i) {
    const char* p = MiniGfx::skipChars(label, i);
    if (*p == ' ') {
      first = i;
      rest = p + 1;
      break;
    }
  }
  drawCentered(label, cx, top + 12, first);
  drawCentered(rest, cx, top + 22, kCellLineChars);
}

// --- programowe sprawdzenie adresu I²C (linie open-drain emulowane przez INPUT_PULLUP);
// używane tylko, gdy sprzętowy TWI nic nie znajdzie – do wykrycia zamienionych SDA/SCL.
constexpr uint32_t kSoftHalfUs = 5;  // ok. 100 kHz

void lineLow(uint8_t pin) {
  digitalWrite(pin, LOW);
  pinMode(pin, OUTPUT);
}

void lineRelease(uint8_t pin) { pinMode(pin, INPUT_PULLUP); }

bool softProbe(uint8_t sda, uint8_t scl, uint8_t addr) {
  lineRelease(sda);
  lineRelease(scl);
  delayMicroseconds(kSoftHalfUs);
  if (digitalRead(sda) == LOW || digitalRead(scl) == LOW) return false;  // zwarcie
  // START
  lineLow(sda);
  delayMicroseconds(kSoftHalfUs);
  lineLow(scl);
  delayMicroseconds(kSoftHalfUs);
  // adres + bit zapisu
  const uint8_t byte = static_cast<uint8_t>(addr << 1);
  for (int8_t bit = 7; bit >= 0; --bit) {
    if (byte & (1 << bit)) {
      lineRelease(sda);
    } else {
      lineLow(sda);
    }
    delayMicroseconds(kSoftHalfUs);
    lineRelease(scl);
    delayMicroseconds(kSoftHalfUs);
    lineLow(scl);
  }
  // ACK od urządzenia
  lineRelease(sda);
  delayMicroseconds(kSoftHalfUs);
  lineRelease(scl);
  delayMicroseconds(kSoftHalfUs);
  const bool ack = digitalRead(sda) == LOW;
  lineLow(scl);
  delayMicroseconds(kSoftHalfUs);
  // STOP
  lineLow(sda);
  delayMicroseconds(kSoftHalfUs);
  lineRelease(scl);
  delayMicroseconds(kSoftHalfUs);
  lineRelease(sda);
  delayMicroseconds(kSoftHalfUs);
  return ack;
}

// swapped = false → sprzętowy TWI na pinach płytki, true → programowo na zamienionych liniach.
bool probe(uint8_t addr, bool swapped) {
  return swapped ? softProbe(board::kScl, board::kSda, addr) : MiniGfx::twiProbe(addr);
}

void scanBus(I2cDiag& diag, bool swapped) {
  diag.count = 0;
  for (uint8_t addr = 0x08; addr <= 0x77; ++addr) {
    if (probe(addr, swapped) && diag.count < sizeof(diag.devices)) {
      diag.devices[diag.count++] = addr;
    }
  }
}

// Dopisuje liczbę dziesiętną na końcu napisu (zamiast snprintf – na AVR to ok. 1,5 KB flash).
void appendNumber(char* dst, size_t cap, long value) {
  char digits[12];
  uint8_t n = 0;
  unsigned long u = value < 0 ? 0UL - static_cast<unsigned long>(value) : value;
  do {
    digits[n++] = static_cast<char>('0' + u % 10);
    u /= 10;
  } while (u != 0);
  if (value < 0) digits[n++] = '-';
  size_t len = strlen(dst);
  while (n > 0 && len + 1 < cap) dst[len++] = digits[--n];
  dst[len] = '\0';
}

void appendText(char* dst, size_t cap, const char* text) {
  size_t len = strlen(dst);
  while (*text != '\0' && len + 1 < cap) dst[len++] = *text++;
  dst[len] = '\0';
}

}  // namespace

bool Display::begin(const Settings& settings) {
  // Stan linii bez wewnętrznego pull-upu: wysoki tylko, gdy moduł jest zasilony i ma rezystory.
  diag_ = I2cDiag();
  pinMode(board::kSda, INPUT);
  pinMode(board::kScl, INPUT);
  delay(2);
  diag_.sdaLevel = digitalRead(board::kSda) == HIGH ? 1 : 0;
  diag_.sclLevel = digitalRead(board::kScl) == HIGH ? 1 : 0;

  // Skan magistrali: diagnostyka i automatyczny wybór adresu (0x3C / 0x3D).
  MiniGfx::twiBegin(board::kSda, board::kScl);
  bool swapped = false;
  scanBus(diag_, false);
  if (diag_.count == 0) {
    // Nic nie odpowiada – może SDA i SCL są zamienione na płytce lub module (moduły 2,42"
    // często mają kolejność GND, VCC, SCL, SDA). TWI ma piny na stałe, więc programowo.
    MiniGfx::twiEnd();
    scanBus(diag_, true);
    swapped = diag_.count > 0;
    diag_.swapped = swapped;
    if (!swapped) MiniGfx::twiBegin(board::kSda, board::kScl);
  }
  uint8_t addr = settings.oledAddr;
  if (!probe(addr, swapped)) {
    if (probe(0x3C, swapped)) {
      addr = 0x3C;
    } else if (probe(0x3D, swapped)) {
      addr = 0x3D;
    } else {
      addr = 0;
    }
  }
  diag_.oledAddr = addr;

  const uint8_t useAddr = addr != 0 ? addr : settings.oledAddr;
  ready_ = swapped ? u8g2.begin(useAddr, board::kScl, board::kSda) : u8g2.begin(useAddr);
  applySettings(settings);
  splashUntil_ = millis() + kSplashMs;
  lastActivity_ = millis();
  dirty_ = true;
  return ready_;
}

void Display::applySettings(const Settings& settings) {
  screensaverS_ = settings.screensaverS;
  if (!ready_) return;
  u8g2.setContrast(settings.brightness);
  u8g2.setFlip(settings.flip);
  dirty_ = true;
}

void Display::setOnline(bool online) {
  if (online_ == online) return;
  online_ = online;
  dirty_ = true;
}

void Display::restore(const DisplayState& state) {
  base_ = DisplayCommand();
  base_.mode = state.mode;
  memcpy(base_.title, state.title, sizeof(base_.title));
  memcpy(base_.labels, state.labels, sizeof(base_.labels));
  dirty_ = true;
}

void Display::apply(const DisplayCommand& cmd, uint32_t nowMs) {
  const bool transient =
      (cmd.mode == DisplayMode::Text || cmd.mode == DisplayMode::Bar) && cmd.ms > 0;
  if (transient) {
    overlay_ = cmd;
    overlayUntil_ = nowMs + cmd.ms;
    overlayActive_ = true;
  } else {
    base_ = cmd;
    overlayActive_ = false;
  }
  dirty_ = true;
}

void Display::flash(uint8_t key, const char* text, uint32_t ms, uint32_t nowMs) {
  flash_.key = key;
  copyUtf8(flash_.text, sizeof(flash_.text), text, kTitleChars);
  flash_.ms = ms;
  flashUntil_ = nowMs + ms;
  flashActive_ = true;
  activity(nowMs);
  dirty_ = true;
}

void Display::setTestMode(bool active) {
  testMode_ = active;
  dirty_ = true;
}

void Display::setTestSnapshot(const TestSnapshot& snapshot) {
  if (memcmp(&snapshot, &test_, sizeof(test_)) != 0) {
    test_ = snapshot;
    if (testMode_) dirty_ = true;
  }
}

void Display::activity(uint32_t nowMs) {
  lastActivity_ = nowMs;
  if (sleeping_) {
    sleeping_ = false;
    if (ready_) u8g2.setPowerSave(0);
    dirty_ = true;
  }
}

void Display::update(uint32_t nowMs) {
  if (!ready_) return;

  if (splashUntil_ != 0 && static_cast<int32_t>(nowMs - splashUntil_) >= 0) {
    splashUntil_ = 0;
    dirty_ = true;
  }
  if (overlayActive_ && static_cast<int32_t>(nowMs - overlayUntil_) >= 0) {
    overlayActive_ = false;
    dirty_ = true;
  }
  if (flashActive_ && static_cast<int32_t>(nowMs - flashUntil_) >= 0) {
    flashActive_ = false;
    dirty_ = true;
  }

  // Wygaszacz (nie w trybie testu).
  if (!sleeping_ && !testMode_ && screensaverS_ > 0 &&
      elapsed(nowMs, lastActivity_, static_cast<uint32_t>(screensaverS_) * 1000UL)) {
    sleeping_ = true;
    u8g2.setPowerSave(1);
    return;
  }
  if (sleeping_ || !dirty_) return;
  if (testMode_ && nowMs - lastDraw_ < kTestRedrawMs) return;

  dirty_ = false;
  lastDraw_ = nowMs;
  draw(nowMs);
}

void Display::draw(uint32_t nowMs) {
  (void)nowMs;
  // Ta sama zawartość rysowana kolejno dla każdego z 8 pasów ekranu (bufor pasa na stosie).
  uint8_t page[MiniGfx::kWidth];
  u8g2.firstPage(page);
  do {
    u8g2.setDrawColor(1);
    if (splashUntil_ != 0) {
      drawSplash();
    } else if (testMode_) {
      drawTest();
    } else if (flashActive_) {
      drawFlash();
    } else if (!online_) {
      drawOffline();
    } else if (overlayActive_) {
      drawCommand(overlay_);
    } else {
      drawBase();
    }
  } while (u8g2.nextPage());
}

void Display::drawStatusMarker(int x, int y, bool inverted) {
  u8g2.setDrawColor(inverted ? 0 : 1);
  if (online_) {
    u8g2.drawDisc(x, y, 2);
  } else {
    u8g2.drawCircle(x, y, 2);
  }
  u8g2.setDrawColor(1);
}

void Display::drawSplash() {
  u8g2.setFont(kFontLarge);
  drawCentered("ChocPilot", kWidth / 2, 30);
  u8g2.setFont(kFontSmall);
  char line[40] = "fw ";
  appendText(line, sizeof(line), CHOCPILOT_FW_VERSION);
  appendText(line, sizeof(line), "  ");
  appendText(line, sizeof(line), board::kBoardName);
  drawCentered(line, kWidth / 2, 50);
}

void Display::drawOffline() {
  u8g2.setFont(kFontLarge);
  drawCentered("Offline", kWidth / 2, 28);
  u8g2.setFont(kFontSmall);
  drawCentered("Czekam na aplikację", kWidth / 2, 48);
  drawStatusMarker(kWidth - 4, 3, false);
}

void Display::drawBase() {
  if (base_.mode == DisplayMode::None) {
    u8g2.setFont(kFontLarge);
    drawCentered("ChocPilot", kWidth / 2, 38);
    drawStatusMarker(kWidth - 4, 3, false);
    return;
  }
  drawCommand(base_);
}

void Display::drawCommand(const DisplayCommand& cmd) {
  switch (cmd.mode) {
    case DisplayMode::Profile: {
      static const uint8_t* const fonts[] = {kFontHuge, kFontLarge, kFontMedium, kFontSmall};
      drawCenteredFit(cmd.title, 40, fonts, 4);
      drawStatusMarker(kWidth - 4, 3, false);
      break;
    }
    case DisplayMode::Grid: {
      // Pasek tytułu (odwrócony) + siatka 2 × 4 ułożona jak klawisze.
      u8g2.drawBox(0, 0, kWidth, kTitleBarH);
      u8g2.setFont(kFontSmall);
      u8g2.setDrawColor(0);
      u8g2.drawUTF8(2, 8, cmd.title);
      u8g2.setDrawColor(1);
      drawStatusMarker(kWidth - 5, 4, true);
      for (int r = 0; r < kRows; ++r) {
        for (int c = 0; c < kCols; ++c) {
          drawCellLabel(cmd.labels[r * kCols + c], c * kCellW + kCellW / 2 - 1,
                        kCellTop + r * kCellH);
        }
      }
      for (int c = 1; c < kCols; ++c) u8g2.drawVLine(c * kCellW - 1, kCellTop, kHeight - kCellTop);
      u8g2.drawHLine(0, kCellTop + kCellH - 1, kWidth);
      break;
    }
    case DisplayMode::Text: {
      if (cmd.line2[0] == '\0') {
        static const uint8_t* const big[] = {kFontHuge, kFontLarge, kFontMedium, kFontSmall};
        drawCenteredFit(cmd.line1, 40, big, 4);
      } else {
        static const uint8_t* const fonts1[] = {kFontLarge, kFontMedium, kFontSmall};
        static const uint8_t* const fonts2[] = {kFontMedium, kFontSmall};
        drawCenteredFit(cmd.line1, 26, fonts1, 3);
        drawCenteredFit(cmd.line2, 50, fonts2, 2);
      }
      break;
    }
    case DisplayMode::Bar: {
      u8g2.setFont(kFontMedium);
      u8g2.drawUTF8(0, 14, cmd.title);
      char pct[8] = "";
      appendNumber(pct, sizeof(pct), cmd.value);
      appendText(pct, sizeof(pct), "%");
      u8g2.drawUTF8(kWidth - u8g2.getUTF8Width(pct), 14, pct);
      u8g2.drawFrame(0, 26, kWidth, 24);
      const int fill = (kWidth - 4) * cmd.value / 100;
      if (fill > 0) u8g2.drawBox(2, 28, fill, 20);
      break;
    }
    case DisplayMode::None:
      break;
  }
}

void Display::drawFlash() {
  static const uint8_t* const fonts[] = {kFontHuge, kFontLarge, kFontMedium, kFontSmall};
  drawCenteredFit(flash_.text, 42, fonts, 4);
  if (flash_.key != 0) {
    char tag[6] = "K";
    appendNumber(tag, sizeof(tag), flash_.key);
    u8g2.setFont(kFontSmall);
    u8g2.drawUTF8(0, 8, tag);
  }
}

void Display::drawTest() {
  // Test sprzętu: 8 pól ułożonych jak klawisze, wciśnięty = wypełniony.
  u8g2.setFont(kFontSmall);
  u8g2.drawUTF8(0, 8, "TEST");
  u8g2.drawUTF8(kWidth - u8g2.getUTF8Width("K1+K4 3s: koniec"), 8, "K1+K4 3s: koniec");
  for (int r = 0; r < kRows; ++r) {
    for (int c = 0; c < kCols; ++c) {
      const int key = r * kCols + c;
      const int x = c * kCellW + 1;
      const int y = kCellTop + 1 + r * kCellH;
      const int w = kCellW - 3;
      const int h = kCellH - 4;
      char number[4] = "";
      appendNumber(number, sizeof(number), key + 1);
      if (test_.keys[key]) {
        u8g2.drawBox(x, y, w, h);
        u8g2.setDrawColor(0);
      } else {
        u8g2.drawFrame(x, y, w, h);
      }
      drawCentered(number, x + w / 2, y + 15);
      u8g2.setDrawColor(1);
    }
  }
}

}  // namespace chocpilot

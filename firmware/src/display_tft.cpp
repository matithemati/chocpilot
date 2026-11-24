#include "display_tft.h"

#include <Arduino.h>
#include <stdio.h>
#include <string.h>

#include "boards/board.h"
#include "config.h"
#include "font5x7.h"
#include "st7789.h"
#include "time_util.h"

namespace chocpilot {

namespace {

using tft::rgb;

constexpr int kW = tft::kWidth;
constexpr int kH = tft::kHeight;
constexpr uint32_t kSplashMs = 1500;
constexpr uint32_t kTestRedrawMs = 50;
constexpr uint32_t kSettleMs = 30;    // cisza po ostatniej zmianie przed rysowaniem
constexpr uint32_t kMaxWaitMs = 250;  // najdłuższe opóźnienie przy ciągłych zmianach

// Paleta (RGB565).
constexpr uint16_t kBg = rgb(12, 16, 28);
constexpr uint16_t kPanel = rgb(32, 40, 62);
constexpr uint16_t kAccent = rgb(0, 170, 200);
constexpr uint16_t kWarn = rgb(255, 170, 40);
constexpr uint16_t kText = rgb(235, 240, 245);
constexpr uint16_t kMuted = rgb(130, 140, 165);
constexpr uint16_t kOnline = rgb(60, 220, 110);
constexpr uint16_t kPressed = rgb(255, 120, 60);

// Siatka 2 × 4 pod paskiem tytułu, ułożona jak klawisze (K1–K4 u góry).
constexpr int kTitleBarH = 32;
constexpr int kCellW = kW / kCols;
constexpr int kCellTop = kTitleBarH + 2;
constexpr int kCellH = (kH - kCellTop) / kRows;
constexpr int kTileInset = 3;
constexpr uint8_t kCellLineChars = 6;  // skala 2: 6 znaków = 70 px w komórce 74 px

// Czyści pas (0, y, kW, h) i rysuje w nim napis wyśrodkowany największą skalą, która się mieści.
void centeredFit(const char* text, int y, int h, uint8_t maxScale, uint8_t minScale, uint16_t fg,
                 uint16_t bg) {
  tft::fillRect(0, y, kW, h, bg);
  uint8_t scale = maxScale;
  while (scale > minScale &&
         (tft::textWidth(text, scale) > kW - 16 || tft::textHeight(scale) > h)) {
    --scale;
  }
  const int w = tft::textWidth(text, scale);
  tft::drawText((kW - w) / 2, y + (h - tft::textHeight(scale)) / 2, text, scale, fg, bg);
}

void centeredAt(const char* text, int cx, int y, uint8_t scale, uint16_t fg, uint16_t bg,
                uint8_t maxChars = 0xFF) {
  const int w = tft::textWidth(text, scale, maxChars);
  tft::drawText(cx - w / 2, y, text, scale, fg, bg, maxChars);
}

uint8_t charCount(const char* text) {
  uint8_t n = 0;
  while (nextChar(text) != 0) ++n;
  return n;
}

const char* skipChars(const char* text, uint8_t n) {
  for (; n > 0 && *text != '\0'; --n) nextChar(text);
  return text;
}

// Etykieta klawisza w kafelku: do 6 znaków w jednym wierszu, dłuższa w dwóch
// (podział na spacji, jeśli wypada w pierwszych 6 znakach) – jak w podglądzie aplikacji.
void drawCellLabel(const char* label, int cx, int cy, uint16_t fg, uint16_t bg) {
  const int lineH = tft::textHeight(2);
  if (charCount(label) <= kCellLineChars) {
    centeredAt(label, cx, cy - lineH / 2, 2, fg, bg, kCellLineChars);
    return;
  }
  uint8_t first = kCellLineChars;
  const char* rest = skipChars(label, kCellLineChars);
  for (uint8_t i = kCellLineChars; i > 0; --i) {
    const char* p = skipChars(label, i);
    if (*p == ' ') {
      first = i;
      rest = p + 1;
      break;
    }
  }
  centeredAt(label, cx, cy - lineH - 3, 2, fg, bg, first);
  centeredAt(rest, cx, cy + 3, 2, fg, bg, kCellLineChars);
}

}  // namespace

void Display::markDirty() {
  const uint32_t now = millis();
  if (!dirty_) dirtySince_ = now;
  changedAt_ = now;
  dirty_ = true;
}

bool Display::begin(const Settings& settings) {
  tft::begin();
  ready_ = true;
  applySettings(settings);
  splashUntil_ = millis() + kSplashMs;
  lastActivity_ = millis();
  markDirty();
  return ready_;
}

void Display::applySettings(const Settings& settings) {
  screensaverS_ = settings.screensaverS;
  brightness_ = settings.brightness;
  if (!ready_) return;
  if (settings.flip != flip_) {
    flip_ = settings.flip;
    tft::setFlip(flip_);
    drawn_ = Screen::None;  // po obrocie cały ekran od nowa
  }
  if (!sleeping_) tft::setBacklight(brightness_);
  markDirty();
}

void Display::setSaver(const char* name) {
  saver_ = findSaver(name);
  if (saving_ && saver_ == nullptr) {
    saving_ = false;  // animację wyłączono w trakcie – wraca zwykły ekran do najbliższej aktywności
    drawn_ = Screen::None;
    markDirty();
  }
}

void Display::setOnline(bool online) {
  if (online_ == online) return;
  online_ = online;
  markDirty();
}

void Display::restore(const DisplayState& state) {
  base_ = DisplayCommand();
  base_.mode = state.mode;
  memcpy(base_.title, state.title, sizeof(base_.title));
  memcpy(base_.labels, state.labels, sizeof(base_.labels));
  markDirty();
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
  markDirty();
}

void Display::flash(uint8_t key, const char* text, uint32_t ms, uint32_t nowMs) {
  flash_.key = key;
  copyUtf8(flash_.text, sizeof(flash_.text), text, kTitleChars);
  flash_.ms = ms;
  flashUntil_ = nowMs + ms;
  flashActive_ = true;
  activity(nowMs);
  markDirty();
}

void Display::setTestMode(bool active) {
  testMode_ = active;
  markDirty();
}

void Display::setTestSnapshot(const TestSnapshot& snapshot) {
  if (memcmp(&snapshot, &test_, sizeof(test_)) != 0) {
    test_ = snapshot;
    if (testMode_) markDirty();
  }
}

void Display::activity(uint32_t nowMs) {
  lastActivity_ = nowMs;
  if (saving_) {
    saving_ = false;
    drawn_ = Screen::None;
    markDirty();
  }
  if (sleeping_) {
    sleeping_ = false;
    if (ready_) {
      tft::setSleep(false);
      tft::setBacklight(brightness_);
    }
    drawn_ = Screen::None;
    markDirty();
  }
}

void Display::update(uint32_t nowMs) {
  if (!ready_) return;

  if (splashUntil_ != 0 && static_cast<int32_t>(nowMs - splashUntil_) >= 0) {
    splashUntil_ = 0;
    markDirty();
  }
  if (overlayActive_ && static_cast<int32_t>(nowMs - overlayUntil_) >= 0) {
    overlayActive_ = false;
    markDirty();
  }
  if (flashActive_ && static_cast<int32_t>(nowMs - flashUntil_) >= 0) {
    flashActive_ = false;
    markDirty();
  }

  // Wygaszacz (nie w trybie testu): animacja z settings.saver albo wygaszony ekran
  // (podświetlenie wyłączone, panel uśpiony).
  if (!sleeping_ && !saving_ && !testMode_ && screensaverS_ > 0 &&
      elapsed(nowMs, lastActivity_, static_cast<uint32_t>(screensaverS_) * 1000UL)) {
    if (saver_ != nullptr) {
      saving_ = true;
      saverPlayer_.start(saver_, nowMs, clock_);
    } else {
      sleeping_ = true;
      tft::setBacklight(0);
      tft::setSleep(true);
    }
    return;
  }
  if (saving_) {
    if (testMode_) {
      saving_ = false;  // tryb testu przerywa wygaszacz
      drawn_ = Screen::None;
      markDirty();
    } else {
      saverPlayer_.update(nowMs);
      return;
    }
  }
  if (sleeping_ || !dirty_) return;
  // Zmiany przychodzą seriami (przełączenie profilu: siatka, ikony w kawałkach, LED, skróty).
  // Rysujemy po ustaniu serii – kSettleMs bez nowych zmian, najpóźniej kMaxWaitMs od pierwszej –
  // zamiast pełnego przerysowania (ok. 0,13 s) po każdej ikonie, które blokowało odbiór danych.
  if (!testMode_ && static_cast<int32_t>(nowMs - changedAt_) < static_cast<int32_t>(kSettleMs) &&
      static_cast<int32_t>(nowMs - dirtySince_) < static_cast<int32_t>(kMaxWaitMs)) {
    return;
  }
  if (testMode_ && nowMs - lastDraw_ < kTestRedrawMs) return;

  dirty_ = false;
  lastDraw_ = nowMs;
  draw();
}

Display::Screen Display::currentScreen() const {
  if (splashUntil_ != 0) return Screen::Splash;
  if (testMode_) return Screen::Test;
  if (flashActive_) return Screen::Flash;
  if (!online_) return Screen::Offline;
  const DisplayCommand& cmd = overlayActive_ ? overlay_ : base_;
  switch (cmd.mode) {
    case DisplayMode::Profile:
      return Screen::Profile;
    case DisplayMode::Grid:
      return Screen::Grid;
    case DisplayMode::Text:
      return Screen::Text;
    case DisplayMode::Bar:
      return Screen::Bar;
    case DisplayMode::None:
      break;
  }
  return Screen::Idle;
}

void Display::draw() {
  const Screen screen = currentScreen();
  if (screen != drawn_) {
    tft::fillScreen(screen == Screen::Flash ? kAccent : kBg);
    drawn_ = screen;
  }
  switch (screen) {
    case Screen::Splash:
      drawSplash();
      break;
    case Screen::Test:
      drawTest();
      break;
    case Screen::Flash:
      drawFlash();
      break;
    case Screen::Offline:
      drawOffline();
      break;
    case Screen::Idle:
      drawIdle();
      break;
    case Screen::None:
      break;
    default:
      drawCommand(overlayActive_ ? overlay_ : base_);
      break;
  }
}

void Display::drawStatusMarker(uint16_t bg) {
  const int x = kW - 18;
  const int y = 8;
  tft::fillRect(x, y, 12, 12, bg);
  if (online_) {
    tft::fillRect(x, y, 12, 12, kOnline);
  } else {
    tft::drawFrame(x, y, 12, 12, 2, kMuted);
  }
}

void Display::drawSplash() {
  centeredFit("ChocPilot", 60, 60, 5, 3, kAccent, kBg);
  char line[48];
  snprintf(line, sizeof(line), "fw %s  %s", CHOCPILOT_FW_VERSION, board::kBoardName);
  centeredFit(line, 140, 30, 2, 1, kMuted, kBg);
}

void Display::drawOffline() {
  centeredFit("Offline", 60, 60, 6, 3, kWarn, kBg);
  centeredFit("Czekam na aplikację", 140, 30, 2, 1, kText, kBg);
  drawStatusMarker(kBg);
}

void Display::drawIdle() {
  centeredFit("ChocPilot", 80, 60, 5, 3, kAccent, kBg);
  drawStatusMarker(kBg);
}

void Display::drawCommand(const DisplayCommand& cmd) {
  switch (cmd.mode) {
    case DisplayMode::Profile:
      drawProfile(cmd);
      break;
    case DisplayMode::Grid:
      drawGrid(cmd);
      break;
    case DisplayMode::Text:
      drawText(cmd);
      break;
    case DisplayMode::Bar:
      drawBar(cmd);
      break;
    case DisplayMode::None:
      break;
  }
}

void Display::drawProfile(const DisplayCommand& cmd) {
  centeredFit("PROFIL", 36, 20, 2, 2, kMuted, kBg);
  centeredFit(cmd.title, 80, 90, 6, 2, kText, kBg);
  drawStatusMarker(kBg);
}

void Display::drawGrid(const DisplayCommand& cmd) {
  // Pasek tytułu w kolorze akcentu + kafelki 2 × 4 ułożone jak klawisze.
  tft::fillRect(0, 0, kW, kTitleBarH, kAccent);
  tft::drawText(8, (kTitleBarH - tft::textHeight(2)) / 2, cmd.title, 2, kBg, kAccent);
  drawStatusMarker(kAccent);
  for (int r = 0; r < kRows; ++r) {
    for (int c = 0; c < kCols; ++c) {
      const int key = r * kCols + c + 1;
      const int x = c * kCellW + kTileInset;
      const int y = kCellTop + r * kCellH + kTileInset;
      const int w = kCellW - 2 * kTileInset;
      const int h = kCellH - 2 * kTileInset;
      tft::fillRect(x, y, w, h, kPanel);
      char tag[4];
      snprintf(tag, sizeof(tag), "K%d", key);
      tft::drawText(x + 5, y + 5, tag, 1, kMuted, kPanel);
      if (icons_ != nullptr && icons_->has(static_cast<uint8_t>(key))) {
        // Ikona 32 × 32 w skali 2 (64 × 64) na środku kafelka, pod znacznikiem Kn.
        const int size = kIconSize * 2;
        drawIcon(x + (w - size) / 2, y + (h - size) / 2 + 4, icons_->data(static_cast<uint8_t>(key)),
                 2);
      } else {
        drawCellLabel(cmd.labels[key - 1], x + w / 2, y + h / 2 + 4, kText, kPanel);
      }
    }
  }
}

void Display::drawText(const DisplayCommand& cmd) {
  // Pasy poza napisami też są czyszczone – poprzedni tekst mógł mieć inny układ (1 ↔ 2 wiersze).
  if (cmd.line2[0] == '\0') {
    tft::fillRect(0, 0, kW, 40, kBg);
    centeredFit(cmd.line1, 40, 160, 6, 2, kText, kBg);
    tft::fillRect(0, 200, kW, kH - 200, kBg);
  } else {
    tft::fillRect(0, 0, kW, 30, kBg);
    centeredFit(cmd.line1, 30, 100, 5, 2, kText, kBg);
    tft::fillRect(0, 130, kW, 10, kBg);
    centeredFit(cmd.line2, 140, 70, 3, 1, kMuted, kBg);
    tft::fillRect(0, 210, kW, kH - 210, kBg);
  }
  drawStatusMarker(kBg);
}

void Display::drawBar(const DisplayCommand& cmd) {
  centeredFit(cmd.title, 20, 36, 3, 2, kText, kBg);
  char pct[8];
  snprintf(pct, sizeof(pct), "%u%%", static_cast<unsigned>(cmd.value));
  centeredFit(pct, 66, 60, 6, 4, kAccent, kBg);
  // Pasek: ramka + wypełnienie; malowane w całości przy każdej zmianie wartości.
  const int x = 20;
  const int y = 150;
  const int w = kW - 40;
  const int h = 50;
  tft::drawFrame(x, y, w, h, 3, kText);
  const int inner = w - 8;
  const int fill = inner * cmd.value / 100;
  tft::fillRect(x + 4, y + 4, fill, h - 8, kAccent);
  tft::fillRect(x + 4 + fill, y + 4, inner - fill, h - 8, kPanel);
  drawStatusMarker(kBg);
}

void Display::drawFlash() {
  centeredFit(flash_.text, 60, 120, 6, 2, kBg, kAccent);
  tft::fillRect(8, 8, 80, tft::textHeight(3), kAccent);
  if (flash_.key != 0) {
    char tag[6];
    snprintf(tag, sizeof(tag), "K%u", static_cast<unsigned>(flash_.key));
    tft::drawText(10, 8, tag, 3, kBg, kAccent);
  }
}

void Display::drawTest() {
  // Test sprzętu: 8 kafelków jak klawisze (wciśnięty = pomarańczowy), pokrętła i suwak.
  tft::drawText(6, 6, "TEST", 2, kWarn, kBg);
  const char* hint = "K1+K4 3s: koniec";
  tft::drawText(kW - tft::textWidth(hint, 1) - 6, 10, hint, 1, kMuted, kBg);
  constexpr int kTop = 28;
  constexpr int kTileH = 60;
  for (int r = 0; r < kRows; ++r) {
    for (int c = 0; c < kCols; ++c) {
      const int key = r * kCols + c;
      const int x = c * kCellW + kTileInset;
      const int y = kTop + r * kTileH + kTileInset;
      const int w = kCellW - 2 * kTileInset;
      const int h = kTileH - 2 * kTileInset;
      const uint16_t bg = test_.keys[key] ? kPressed : kPanel;
      tft::fillRect(x, y, w, h, bg);
      char number[4];
      snprintf(number, sizeof(number), "%d", key + 1);
      centeredAt(number, x + w / 2, y + (h - tft::textHeight(3)) / 2, 3, kText, bg);
    }
  }
  // Pokrętła: suma obrotów od wejścia w tryb testu, tło pomarańczowe = przycisk wciśnięty.
  constexpr int kEncTop = kTop + kRows * kTileH + 4;
  for (int i = 0; i < 2; ++i) {
    const int x = i * (kW / 2) + kTileInset;
    const int w = kW / 2 - 2 * kTileInset;
    const uint16_t bg = test_.encoderKeys[i] ? kPressed : kPanel;
    tft::fillRect(x, kEncTop, w, 36, bg);
    char line[16];
    snprintf(line, sizeof(line), "E%d %+d", i + 1, test_.encoders[i]);
    tft::drawText(x + 8, kEncTop + 11, line, 2, kText, bg);
  }
  // Suwak 0–100.
  constexpr int kSliderTop = kEncTop + 42;
  const int barX = 70;
  const int barW = kW - barX - kTileInset;
  char value[8];
  snprintf(value, sizeof(value), "%3u", static_cast<unsigned>(test_.slider));
  tft::fillRect(0, kSliderTop, barX, 28, kBg);
  tft::drawText(kTileInset + 4, kSliderTop + 7, value, 2, kText, kBg);
  const int fill = barW * test_.slider / 100;
  tft::fillRect(barX, kSliderTop, fill, 28, kAccent);
  tft::fillRect(barX + fill, kSliderTop, barW - fill, 28, kPanel);
}

}  // namespace chocpilot

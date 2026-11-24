// Ekran Waveshare 2" IPS LCD (ST7789V, 240×320, używany poziomo 320×240):
// tryby z komend display/flash, ekran offline, tryb testu i wygaszacz.
#pragma once

#include <stdint.h>

#include "device_config.h"
#include "protocol_codec.h"
#include "icons.h"
#include "saver.h"
#include "test_snapshot.h"

namespace chocpilot {

class Display {
 public:
  bool begin(const Settings& settings);
  void applySettings(const Settings& settings);
  // Animacja wygaszacza (nazwa z settings.saver; nieznana / pusta = wygaszony ekran).
  void setSaver(const char* name);
  // Zegar z aplikacji pokazywany na wygaszaczu z animacją.
  void setClock(const WallClock* clock) { clock_ = clock; }
  // Ikony klawiszy w siatce (zamiast etykiet); iconsChanged() po zmianie ikony.
  void setIcons(const IconStore* icons) { icons_ = icons; }
  void iconsChanged() { markDirty(); }

  void setOnline(bool online);
  // Tryb bazowy z pamięci (profile / grid).
  void restore(const DisplayState& state);
  // Komenda display: profile/grid oraz text/bar bez ms ustawiają tryb bazowy,
  // text/bar z ms – nakładkę chwilową.
  void apply(const DisplayCommand& cmd, uint32_t nowMs);
  void flash(uint8_t key, const char* text, uint32_t ms, uint32_t nowMs);

  void setTestMode(bool active);
  void setTestSnapshot(const TestSnapshot& snapshot);

  // Aktywność użytkownika – wybudza z wygaszacza.
  void activity(uint32_t nowMs);
  void update(uint32_t nowMs);

  // Wygaszacz aktywny (wygaszony ekran albo animacja) – diody LED też gasną.
  bool sleeping() const { return sleeping_ || saving_; }

 private:
  // Rodzaj ekranu – przy zmianie całe tło jest czyszczone, w obrębie jednego rodzaju
  // przerysowywane są tylko pasy z treścią (bez migania przy zmianie wartości).
  enum class Screen : uint8_t { None, Splash, Test, Flash, Offline, Idle, Profile, Grid, Text, Bar };

  void draw();
  Screen currentScreen() const;
  void drawSplash();
  void drawOffline();
  void drawIdle();
  void drawCommand(const DisplayCommand& cmd);
  void drawProfile(const DisplayCommand& cmd);
  void drawGrid(const DisplayCommand& cmd);
  void drawText(const DisplayCommand& cmd);
  void drawBar(const DisplayCommand& cmd);
  void drawFlash();
  void drawTest();
  void drawStatusMarker(uint16_t bg);

  bool ready_ = false;
  bool dirty_ = true;
  uint32_t dirtySince_ = 0;  // pierwsza zmiana od ostatniego rysowania
  uint32_t changedAt_ = 0;   // ostatnia zmiana
  void markDirty();
  bool online_ = false;
  bool testMode_ = false;
  bool sleeping_ = false;
  bool saving_ = false;  // wygaszacz z animacją (podświetlenie włączone)
  const SaverAnimation* saver_ = nullptr;
  SaverPlayer saverPlayer_;
  const WallClock* clock_ = nullptr;
  const IconStore* icons_ = nullptr;
  bool flip_ = false;
  uint8_t brightness_ = 128;
  uint16_t screensaverS_ = 0;
  uint32_t lastActivity_ = 0;
  uint32_t splashUntil_ = 0;
  uint32_t lastDraw_ = 0;
  Screen drawn_ = Screen::None;

  DisplayCommand base_;
  DisplayCommand overlay_;
  uint32_t overlayUntil_ = 0;
  bool overlayActive_ = false;

  FlashCommand flash_;
  uint32_t flashUntil_ = 0;
  bool flashActive_ = false;

  TestSnapshot test_;
};

}  // namespace chocpilot

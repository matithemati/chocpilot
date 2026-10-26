// Model danych zapisywanych w pamięci urządzenia i jego zapis binarny.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace chocpilot {

// Matryca 2 × 4 (Kailh Choc): klawisze 1–4 w wierszu 0, 5–8 w wierszu 1.
constexpr int kRows = 2;
constexpr int kCols = 4;
constexpr int kTotalKeys = kRows * kCols;

// Limity napisów (w znakach Unicode) i rozmiary buforów (w bajtach UTF-8, z \0).
constexpr size_t kTitleChars = 21;
constexpr size_t kLabelChars = 10;  // na ekranie 1–2 wiersze po 6 znaków w komórce 32 px
// Mało RAM (ATmega32U4): bufory na tekst ASCII – dłuższy UTF-8 jest obcinany wcześniej.
constexpr size_t kTitleBuf = 22;
constexpr size_t kLabelBuf = 12;

struct Settings {
  uint8_t brightness = 128;
  uint16_t screensaverS = 300;
  bool flip = false;
  uint8_t debounceMs = 8;
  uint8_t oledAddr = 0x3C;
};

// Skrót trybu awaryjnego: kombinacja klawiatury (mods + code) albo klawisz multimedialny.
struct FallbackBinding {
  uint8_t mods = 0;
  uint8_t code = 0;
  uint16_t media = 0;
  bool empty() const { return mods == 0 && code == 0 && media == 0; }
};

// Sloty 0..7 = klawisze 1..8.
constexpr int kFallbackSlots = kTotalKeys;

enum class DisplayMode : uint8_t { None = 0, Profile, Grid, Text, Bar };

// Trwały stan ekranu (tylko tryby profile / grid).
struct DisplayState {
  DisplayMode mode = DisplayMode::None;
  char title[kTitleBuf] = {0};  // tytuł siatki albo nazwa profilu
  char labels[kTotalKeys][kLabelBuf] = {{0}};
};

struct DeviceConfig {
  Settings settings;
  FallbackBinding fallback[kFallbackSlots];
  DisplayState display;

  void setDefaults();
  static void defaultFallback(FallbackBinding (&slots)[kFallbackSlots]);
};

// Zapis binarny: wersja + struktura. Zwraca liczbę zapisanych bajtów (0 przy braku miejsca).
size_t encodeConfig(const DeviceConfig& cfg, char* buf, size_t cap);
// Zwraca false, jeśli dane są uszkodzone (wtedy cfg ma wartości domyślne).
bool decodeConfig(const char* data, size_t len, DeviceConfig& cfg);

// Kopiuje UTF-8 obcinając do maxChars znaków i rozmiaru bufora, bez łamania sekwencji.
void copyUtf8(char* dst, size_t dstSize, const char* src, size_t maxChars);

}  // namespace chocpilot

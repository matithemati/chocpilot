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

// Podświetlenie LED (ChocPilot v0: 12 × WS2812B na spodzie). Status = kolor połączenia
// (online turkus, offline bursztyn); pozostałe tryby używają koloru r/g/b.
enum class LedMode : uint8_t { Off = 0, Status, Static, Breathe, Rainbow };
constexpr uint8_t kLedSpeedMin = 1;
constexpr uint8_t kLedSpeedMax = 10;

struct LedSettings {
  LedMode mode = LedMode::Status;
  uint8_t r = 0;
  uint8_t g = 160;
  uint8_t b = 192;
  uint8_t brightness = 128;  // 0–255, w firmware ograniczona do ok. 1/3 pełnej (prąd USB)
  uint8_t speed = 5;         // 1–10: tempo oddychania i tęczy
  bool react = true;         // błysk diody przy naciśniętym klawiszu
};

// Animacja wygaszacza ekranu (ChocPilot v0): nazwa wbudowanej animacji, np. "rabbit"; pusta =
// wygaszony ekran. Nazwa zamiast numeru – kolejność i liczba animacji mogą się zmieniać.
constexpr size_t kSaverNameBuf = 12;  // do 11 znaków [a-z0-9_]

struct SaverSettings {
  char name[kSaverNameBuf] = {0};
};

// Ikony klawiszy na LCD (ChocPilot v0): 32 × 32 px, paleta 16 kolorów RGB565 (32 B) + piksele
// 4 bity (512 B) – rysowane w skali 2 w kafelkach siatki zamiast etykiet. Tylko w RAM: aplikacja
// wysyła je po połączeniu (komenda icon w kawałkach), po restarcie bez aplikacji – etykiety.
constexpr uint8_t kIconSize = 32;
constexpr uint16_t kIconPaletteBytes = 16 * 2;
constexpr uint16_t kIconBytes = kIconPaletteBytes + kIconSize * kIconSize / 2;  // 544
constexpr uint8_t kIconChunkMax = 128;  // bajtów obrazu w jednej komendzie (base64 ≈ 172 znaki)

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
  LedSettings leds;    // od wersji 2 zapisu
  SaverSettings saver;  // od wersji 3; nowe pola zawsze na końcu (starszy zapis = prefiks)

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

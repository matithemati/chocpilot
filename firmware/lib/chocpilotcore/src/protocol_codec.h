// Kodowanie i dekodowanie wiadomości protokołu ChocPilot (JSON Lines), patrz docs/PROTOCOL.md.
// Czysta logika – bez Arduino, testowana w środowisku native. Parser bez alokacji (2,5 KB RAM).
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "device_config.h"
#include "flash_text.h"

namespace chocpilot {

// Bufor odbioru. Limit trafia do hello (max_line), aplikacja dzieli dłuższe komendy.
constexpr size_t kMaxLineLength = 272;

enum class CommandType : uint8_t {
  Unknown = 0,
  Hello,
  Ping,
  GetInfo,
  Display,
  Flash,
  Settings,
  SetFallback,
  Reboot,
  TestMode,
  Debug,
  Leds,
  Time,
  Icon,
};

// Czas lokalny z aplikacji (zegar na wygaszaczu LCD).
// Kawałek ikony klawisza (komenda icon): data[0..len) zapisywane od offset; clear = usuń ikonę.
struct IconChunk {
  uint8_t key = 0;  // 1–8
  bool clear = false;
  uint16_t offset = 0;
  uint8_t len = 0;
  uint8_t data[kIconChunkMax] = {0};
};

struct TimeOfDay {
  uint8_t hour = 0;
  uint8_t minute = 0;
  uint8_t second = 0;
};

struct DisplayCommand {
  DisplayMode mode = DisplayMode::None;
  char title[kTitleBuf] = {0};  // grid/bar: tytuł, profile: nazwa
  // Mało RAM: etykiety (tylko grid) i wiersze tekstu (tylko text) dzielą pamięć.
  union {
    char labels[kTotalKeys][kLabelBuf] = {{0}};
    struct {
      char line1[kTitleBuf];
      char line2[kTitleBuf];
    };
  };
  uint8_t value = 0;
  uint32_t ms = 0;
};

struct FlashCommand {
  uint8_t key = 0;  // 0 = brak
  char text[kTitleBuf] = {0};
  uint32_t ms = 1000;
};

// Częściowa aktualizacja ustawień: bit w `mask` oznacza obecność pola.
struct SettingsPatch {
  enum Field : uint16_t {
    kBrightness = 1 << 0,
    kScreensaver = 1 << 1,
    kFlip = 1 << 2,
    kDebounce = 1 << 3,
    kSaver = 1 << 5,
  };
  uint16_t mask = 0;
  Settings values;
  char saver[kSaverNameBuf] = {0};  // kSaver: animacja wygaszacza ("" / "off" = wygaszony ekran)

  void applyTo(Settings& s) const;
};

// Częściowa zmiana podświetlenia (komenda leds). save = false: tylko do restartu / rozłączenia
// (np. kolor profilu), bez zapisu do pamięci.
struct LedPatch {
  enum Field : uint8_t {
    kMode = 1 << 0,
    kColor = 1 << 1,
    kBrightness = 1 << 2,
    kSpeed = 1 << 3,
    kReact = 1 << 4,
  };
  uint8_t mask = 0;
  bool save = true;
  LedSettings values;

  void applyTo(LedSettings& s) const;
};

struct FallbackPatch {
  bool replace = false;
  uint8_t count = 0;
  uint8_t slots[kFallbackSlots] = {0};
  FallbackBinding bindings[kFallbackSlots];

  void applyTo(FallbackBinding (&target)[kFallbackSlots]) const;
};

struct Command {
  CommandType type = CommandType::Unknown;
  bool hasId = false;
  int32_t id = 0;
  DisplayCommand display;
  FlashCommand flash;
  SettingsPatch settings;
  FallbackPatch fallback;
  LedPatch leds;
  TimeOfDay time;
  IconChunk icon;
  bool flag = false;  // reboot.bootloader / test_mode.enable / debug.enable
};

enum class ParseStatus : uint8_t {
  Ok,          // poprawna komenda
  Ignored,     // nieznany typ – ignorować
  BadJson,     // niepoprawny JSON / brak type – odpowiedź error bez id
  Invalid,     // błąd walidacji – odpowiedź error z id (jeśli jest)
};

struct ParseResult {
  ParseStatus status = ParseStatus::Ok;
  FlashText error = nullptr;  // statyczny opis błędu
};

ParseResult parseCommand(const char* line, size_t len, Command& out);

// Budowanie wiadomości wychodzących. Zwracają długość (bez \0, bez \n) lub 0 przy braku miejsca.
// encoder: płytka ma pokrętła.
// leds: liczba diod podświetlenia (0 = brak, pole leds pominięte). savers: nazwy animacji
// wygaszacza (pole savers tylko, gdy saverCount > 0).
size_t buildHello(char* buf, size_t cap, const char* board, const char* fw, bool online,
                  bool encoder = false, uint8_t leds = 0,
                  const char* const* savers = nullptr, uint8_t saverCount = 0,
                  uint8_t iconSize = 0);

// Dekoduje base64 (bez białych znaków) z src[0..srcLen) do dst; zwraca liczbę bajtów albo −1
// przy błędzie / braku miejsca.
int decodeBase64(const char* src, size_t srcLen, uint8_t* dst, size_t cap);
size_t buildKey(char* buf, size_t cap, uint8_t key, bool down, uint32_t t);
// Pokrętło `index` (1, 2) obrócone o `delta` zatrzasków (+ w prawo).
size_t buildEncoder(char* buf, size_t cap, uint8_t index, int16_t delta, uint32_t t);
// Przycisk pokrętła `index` wciśnięty / zwolniony (po debounce).
size_t buildEncoderKey(char* buf, size_t cap, uint8_t index, bool down, uint32_t t);
// Położenie suwaka 0–100 (dół – góra).
size_t buildSlider(char* buf, size_t cap, uint8_t value, uint32_t t);
size_t buildAck(char* buf, size_t cap, int32_t id);
size_t buildError(char* buf, size_t cap, bool hasId, int32_t id, FlashText msg);
size_t buildLog(char* buf, size_t cap, FlashText level, FlashText msg);
size_t buildTest(char* buf, size_t cap, bool active);

}  // namespace chocpilot

#include "hid_codes.h"

#include <stdlib.h>
#include <string.h>

#include "flash_text.h"

namespace chocpilot {

namespace {

// Tabele w pamięci programu (na AVR nie zajmują RAM): nazwy jako jeden napis „nazwa\0nazwa\0…”
// zakończony pustą nazwą, wartości w osobnej tablicy o tej samej kolejności.
const char kKeyNames[] CHOCPILOT_PROGMEM =
    "enter\0return\0esc\0escape\0backspace\0tab\0space\0minus\0"
    "equal\0lbracket\0rbracket\0backslash\0semicolon\0quote\0grave\0comma\0"
    "period\0slash\0capslock\0printscreen\0scrolllock\0pause\0insert\0home\0"
    "pageup\0delete\0end\0pagedown\0right\0left\0down\0up\0"
    "numlock\0kp_divide\0kp_multiply\0kp_minus\0kp_plus\0kp_enter\0kp_period\0menu\0"
    "-\0=\0[\0]\0\\\0;\0'\0`\0,\0.\0/\0";
const uint8_t kKeyCodes[] CHOCPILOT_PROGMEM = {
    0x28, 0x28, 0x29, 0x29, 0x2A, 0x2B, 0x2C, 0x2D,
    0x2E, 0x2F, 0x30, 0x31, 0x33, 0x34, 0x35, 0x36,
    0x37, 0x38, 0x39, 0x46, 0x47, 0x48, 0x49, 0x4A,
    0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52,
    0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x63, 0x65,
    0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
};

const char kModNames[] CHOCPILOT_PROGMEM =
    "ctrl\0control\0shift\0alt\0win\0gui\0meta\0cmd\0"
    "lctrl\0lshift\0lalt\0lwin\0rctrl\0rshift\0ralt\0altgr\0rwin\0rgui\0";
const uint8_t kModBits[] CHOCPILOT_PROGMEM = {
    kModLCtrl, kModLCtrl,  kModLShift, kModLAlt,  kModLGui,  kModLGui, kModLGui, kModLGui,
    kModLCtrl, kModLShift, kModLAlt,   kModLGui,  kModRCtrl, kModRShift, kModRAlt, kModRAlt,
    kModRGui,  kModRGui,
};

const char kConsumerNames[] CHOCPILOT_PROGMEM =
    "play_pause\0next\0prev\0stop\0vol_up\0vol_down\0mute\0";
const uint16_t kConsumerUsages[] CHOCPILOT_PROGMEM = {
    kConsumerPlayPause, kConsumerNext,    kConsumerPrev, kConsumerStop,
    kConsumerVolUp,     kConsumerVolDown, kConsumerMute,
};

// Porównanie bez rozróżniania wielkości liter (tylko ASCII); `b` w pamięci programu.
bool equalsIgnoreCase(const char* a, const char* b) {
  while (*a && pgmByte(b)) {
    char ca = *a, cb = static_cast<char>(pgmByte(b));
    if (ca >= 'A' && ca <= 'Z') ca = static_cast<char>(ca - 'A' + 'a');
    if (cb >= 'A' && cb <= 'Z') cb = static_cast<char>(cb - 'A' + 'a');
    if (ca != cb) return false;
    ++a;
    ++b;
  }
  return *a == '\0' && pgmByte(b) == 0;
}

// Indeks nazwy na liście „nazwa\0nazwa\0…\0” albo −1.
int findName(const char* name, const char* names) {
  for (int i = 0; pgmByte(names) != 0; ++i) {
    if (equalsIgnoreCase(name, names)) return i;
    while (pgmByte(names++) != 0) {
    }
  }
  return -1;
}

// Parsuje liczbę dziesiętną z całego napisu; zwraca −1 przy błędzie.
int parseNumber(const char* s) {
  if (*s == '\0') return -1;
  int value = 0;
  for (; *s; ++s) {
    if (*s < '0' || *s > '9') return -1;
    value = value * 10 + (*s - '0');
    if (value > 1000) return -1;
  }
  return value;
}

}  // namespace

uint8_t hidKeyFromName(const char* name) {
  if (name == nullptr || *name == '\0') return 0;
  const size_t len = strlen(name);

  if (len == 1) {
    char c = name[0];
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    if (c >= 'a' && c <= 'z') return static_cast<uint8_t>(0x04 + (c - 'a'));
    if (c >= '1' && c <= '9') return static_cast<uint8_t>(0x1E + (c - '1'));
    if (c == '0') return 0x27;
  }

  // f1..f24
  if ((name[0] == 'f' || name[0] == 'F') && len >= 2 && len <= 3) {
    const int n = parseNumber(name + 1);
    if (n >= 1 && n <= 12) return static_cast<uint8_t>(0x3A + (n - 1));
    if (n >= 13 && n <= 24) return static_cast<uint8_t>(0x68 + (n - 13));
  }

  // kp_0..kp_9
  if (len == 4 && (strncmp(name, "kp_", 3) == 0 || strncmp(name, "KP_", 3) == 0)) {
    const char d = name[3];
    if (d == '0') return 0x62;
    if (d >= '1' && d <= '9') return static_cast<uint8_t>(0x59 + (d - '1'));
  }

  const int i = findName(name, kKeyNames);
  return i < 0 ? 0 : pgmByte(&kKeyCodes[i]);
}

uint8_t hidModFromName(const char* name) {
  if (name == nullptr) return 0;
  const int i = findName(name, kModNames);
  return i < 0 ? 0 : pgmByte(&kModBits[i]);
}

uint16_t consumerFromName(const char* name) {
  if (name == nullptr) return 0;
  const int i = findName(name, kConsumerNames);
  return i < 0 ? 0 : pgmWord(&kConsumerUsages[i]);
}

}  // namespace chocpilot

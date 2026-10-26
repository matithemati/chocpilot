#include "device_config.h"

#include <string.h>

#include "hid_codes.h"

namespace chocpilot {

void copyUtf8(char* dst, size_t dstSize, const char* src, size_t maxChars) {
  if (dstSize == 0) return;
  size_t out = 0;
  size_t chars = 0;
  if (src != nullptr) {
    while (*src && chars < maxChars) {
      const uint8_t lead = static_cast<uint8_t>(*src);
      size_t seqLen = 1;
      if ((lead & 0xE0) == 0xC0) {
        seqLen = 2;
      } else if ((lead & 0xF0) == 0xE0) {
        seqLen = 3;
      } else if ((lead & 0xF8) == 0xF0) {
        seqLen = 4;
      }
      // Sprawdzenie, czy cała sekwencja istnieje i zmieści się w buforze.
      size_t i = 1;
      while (i < seqLen && src[i] != '\0') ++i;
      if (i < seqLen) break;
      if (out + seqLen >= dstSize) break;
      memcpy(dst + out, src, seqLen);
      out += seqLen;
      src += seqLen;
      ++chars;
    }
  }
  dst[out] = '\0';
}

void DeviceConfig::defaultFallback(FallbackBinding (&slots)[kFallbackSlots]) {
  for (FallbackBinding& b : slots) b = FallbackBinding();
  // Dolny rząd bez aplikacji: ciszej, głośniej, odtwarzaj/pauza, wycisz.
  slots[4].media = kConsumerVolDown;
  slots[5].media = kConsumerVolUp;
  slots[6].media = kConsumerPlayPause;
  slots[7].media = kConsumerMute;
}

void DeviceConfig::setDefaults() {
  settings = Settings();
  defaultFallback(fallback);
  display = DisplayState();
}


// Zapis binarny: [wersja][DeviceConfig]. Zmiana układu struktury wymaga nowej wersji (zwykle
// zmienia też rozmiar) – stary zapis zostaje wtedy odrzucony i obowiązują wartości domyślne.
namespace {
constexpr uint8_t kBinaryConfigVersion = 1;
}

size_t encodeConfig(const DeviceConfig& cfg, char* buf, size_t cap) {
  const size_t n = 1 + sizeof(DeviceConfig);
  if (n > cap) return 0;
  buf[0] = static_cast<char>(kBinaryConfigVersion);
  memcpy(buf + 1, &cfg, sizeof(DeviceConfig));
  return n;
}

bool decodeConfig(const char* data, size_t len, DeviceConfig& cfg) {
  cfg.setDefaults();
  if (len != 1 + sizeof(DeviceConfig) || static_cast<uint8_t>(data[0]) != kBinaryConfigVersion) {
    return false;
  }
  memcpy(static_cast<void*>(&cfg), data + 1, sizeof(DeviceConfig));

  Settings& st = cfg.settings;
  if (st.debounceMs < 1 || st.debounceMs > 50) st.debounceMs = 8;
  if (cfg.display.mode != DisplayMode::Profile && cfg.display.mode != DisplayMode::Grid) {
    cfg.display = DisplayState();
  }
  cfg.display.title[kTitleBuf - 1] = '\0';
  for (auto& label : cfg.display.labels) label[kLabelBuf - 1] = '\0';
  return true;
}


}  // namespace chocpilot

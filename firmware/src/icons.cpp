#include "icons.h"

#include <string.h>

#include "st7789.h"

namespace chocpilot {

void IconStore::clear(uint8_t key) {
  if (key < 1 || key > kTotalKeys) return;
  filled_[key - 1] = 0;
}

bool IconStore::write(uint8_t key, uint16_t offset, const uint8_t* data, uint8_t len) {
  if (key < 1 || key > kTotalKeys) return false;
  uint16_t& filled = filled_[key - 1];
  if (offset == 0) filled = 0;     // nowa ikona – do czasu skompletowania etykieta
  if (offset != filled) return false;  // zgubiony kawałek – czekamy na offset 0
  if (offset + len > kIconBytes) return false;
  memcpy(buf_[key - 1] + offset, data, len);
  filled = static_cast<uint16_t>(offset + len);
  return filled == kIconBytes;
}

bool IconStore::has(uint8_t key) const {
  return key >= 1 && key <= kTotalKeys && filled_[key - 1] == kIconBytes;
}

void drawIcon(int x, int y, const uint8_t* icon, uint8_t scale) {
  uint16_t palette[16];
  for (uint8_t i = 0; i < 16; ++i) {
    palette[i] = static_cast<uint16_t>(icon[2 * i] << 8 | icon[2 * i + 1]);  // big-endian
  }
  const uint8_t* pixels = icon + kIconPaletteBytes;
  const int size = kIconSize * scale;
  tft::beginPixels(x, y, size, size);
  for (uint8_t row = 0; row < kIconSize; ++row) {
    const uint8_t* line = pixels + row * (kIconSize / 2);
    for (uint8_t repeat = 0; repeat < scale; ++repeat) {
      for (uint8_t col = 0; col < kIconSize; ++col) {
        const uint8_t b = line[col >> 1];
        const uint16_t c = palette[(col & 1) ? (b & 0x0F) : (b >> 4)];
        for (uint8_t s = 0; s < scale; ++s) tft::pushPixel(c);
      }
    }
  }
}

}  // namespace chocpilot

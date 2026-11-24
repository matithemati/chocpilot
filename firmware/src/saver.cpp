#include "saver.h"

#include <stdio.h>
#include <string.h>

#include "saver_data.h"
#include "st7789.h"

namespace chocpilot {

using saver_data::kClockColor;
using saver_data::kClockScale;
using saver_data::kClockY;
using saver_data::kGround;
using saver_data::kGroundLine;
using saver_data::kGroundLineH;
using saver_data::kGroundY;
using saver_data::kSaverCount;
using saver_data::kSavers;
using saver_data::kSky;

const SaverAnimation* findSaver(const char* name) {
  if (name == nullptr || name[0] == '\0') return nullptr;
  for (const SaverAnimation& a : kSavers) {
    if (strcmp(a.name, name) == 0) return &a;
  }
  return nullptr;
}

const char* const* saverNames() {
  static const char* names[kSaverCount];
  for (uint8_t i = 0; i < kSaverCount; ++i) names[i] = kSavers[i].name;
  return names;
}

uint8_t saverCount() { return kSaverCount; }

void SaverPlayer::start(const SaverAnimation* anim, uint32_t nowMs, const WallClock* clock) {
  anim_ = anim;
  clock_ = clock;
  shownMinutes_ = -1;
  startMs_ = nowMs;
  lastStep_ = 0xFFFFFFFF;
  prevW_ = 0;
  tft::fillRect(0, 0, tft::kWidth, kGroundY, kSky);
  tft::fillRect(0, kGroundY, tft::kWidth, kGroundLineH, kGroundLine);
  tft::fillRect(0, kGroundY + kGroundLineH, tft::kWidth, tft::kHeight - kGroundY - kGroundLineH,
                kGround);
  update(nowMs);
}

void SaverPlayer::update(uint32_t nowMs) {
  if (anim_ == nullptr) return;
  drawClock(nowMs);
  const uint32_t step = (nowMs - startMs_) / anim_->frameMs;
  if (step == lastStep_) return;
  lastStep_ = step;
  drawStep(step);
}

// Godzina HH:MM u góry na środku – przerysowywana tylko przy zmianie minuty. Postać nigdy nie
// wchodzi tak wysoko (najwyższy skok kończy się niżej), więc napis nie jest zamalowywany.
void SaverPlayer::drawClock(uint32_t nowMs) {
  uint8_t hour = 0;
  uint8_t minute = 0;
  if (clock_ == nullptr || !clock_->now(nowMs, hour, minute)) return;
  const int16_t minutes = static_cast<int16_t>(hour * 60 + minute);
  if (minutes == shownMinutes_) return;
  shownMinutes_ = minutes;
  char text[8];
  snprintf(text, sizeof(text), "%02u:%02u", static_cast<unsigned>(hour),
           static_cast<unsigned>(minute));
  const int w = tft::textWidth(text, kClockScale);
  tft::drawText((tft::kWidth - w) / 2, kClockY, text, kClockScale, kClockColor, kSky);
}

namespace {

inline int imin(int a, int b) { return a < b ? a : b; }
inline int imax(int a, int b) { return a > b ? a : b; }

}  // namespace

// Ta sama arytmetyka co saver_pose() w app/chocpilot/core/savers.py.
void SaverPlayer::drawStep(uint32_t step) {
  const SaverAnimation& a = *anim_;
  const uint32_t cycles = step / a.stepCount;
  const uint8_t index = static_cast<uint8_t>(step - cycles * a.stepCount);
  uint32_t pos = cycles * a.cycleDx;
  for (uint8_t i = 0; i <= index; ++i) pos += a.steps[i].dx;
  const int w = a.w * a.scale;
  const int h = a.h * a.scale;
  const int x = static_cast<int>(pos % static_cast<uint32_t>(tft::kWidth + w)) - w;
  const int y = kGroundY - h - a.steps[index].dy;
  const uint8_t frame = a.steps[index].frame;

  // Obszar do przerysowania: poprzedni i nowy prostokąt postaci. Gdy postać przeskoczyła
  // z prawej krawędzi na lewą (prostokąty rozłączne), stary zamalowujemy osobno.
  int x0 = x, y0 = y, x1 = x + w, y1 = y + h;
  if (prevW_ > 0) {
    const bool overlap = prevX_ < x1 && x < prevX_ + prevW_;
    if (overlap) {
      x0 = imin(x0, prevX_);
      y0 = imin(y0, prevY_);
      x1 = imax(x1, prevX_ + prevW_);
      y1 = imax(y1, prevY_ + prevH_);
    } else {
      tft::fillRect(prevX_, prevY_, prevW_, prevH_, kSky);
    }
  }
  prevX_ = x;
  prevY_ = y;
  prevW_ = w;
  prevH_ = h;

  x0 = imax(x0, 0);
  y0 = imax(y0, 0);
  x1 = imin(x1, tft::kWidth);
  y1 = imin(y1, kGroundY);
  if (x0 >= x1 || y0 >= y1) return;

  const int bytesPerRow = (a.w + 1) / 2;
  const uint8_t* frameData = a.pixels + static_cast<uint32_t>(frame) * a.h * bytesPerRow;
  tft::beginPixels(x0, y0, x1 - x0, y1 - y0);
  for (int sy = y0; sy < y1; ++sy) {
    int sx = x0;
    if (sy >= y && sy < y + h) {
      const uint8_t* row = frameData + ((sy - y) / a.scale) * bytesPerRow;
      for (; sx < x1 && sx < x; ++sx) tft::pushPixel(kSky);
      // Licznik zamiast dzielenia przy każdym pikselu (Cortex-M0 nie ma sprzętowego dzielenia).
      int px = (sx - x) / a.scale;
      int sub = (sx - x) - px * a.scale;
      const int end = imin(x1, x + w);
      for (; sx < end; ++sx) {
        const uint8_t b = row[px >> 1];
        const uint8_t v = (px & 1) ? (b & 0x0F) : (b >> 4);
        tft::pushPixel(v ? a.palette[v] : kSky);
        if (++sub == a.scale) {
          sub = 0;
          ++px;
        }
      }
    }
    for (; sx < x1; ++sx) tft::pushPixel(kSky);
  }
}

}  // namespace chocpilot

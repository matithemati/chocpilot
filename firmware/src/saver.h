// Animowany wygaszacz LCD: postać z pixel-artu (paleta ≤ 16 kolorów, 4 bity na
// piksel) idzie po ekranie nad pasem ziemi. Dane animacji: saver_data.h (generowane z aplikacji,
// app/chocpilot/core/savers.py – ta sama oś czasu co podgląd w aplikacji).
#pragma once

#include <stdint.h>

#include "wall_clock.h"

namespace chocpilot {

struct SaverStep {
  uint8_t frame;  // numer ramki
  uint8_t dx;     // przesunięcie w prawo w tym kroku [px ekranu]
  uint8_t dy;     // wysokość nad ziemią [px ekranu]
};

struct SaverAnimation {
  const char* name;  // identyfikator w protokole (settings.saver)
  uint8_t w, h;      // rozmiar ramki [px sprite]
  uint8_t scale;     // powiększenie na ekranie
  uint16_t frameMs;  // czas kroku
  uint8_t stepCount;
  uint16_t cycleDx;  // suma dx kroków
  const SaverStep* steps;
  const uint16_t* palette;  // RGB565, [0] = tło (przezroczysty)
  const uint8_t* pixels;    // ramki × h × ceil(w/2) bajtów, starszy półbajt = lewy piksel
};

// Wbudowana animacja o nazwie `name` (nullptr = brak – wygaszacz gasi ekran).
const SaverAnimation* findSaver(const char* name);
// Nazwy wbudowanych animacji (do hello).
const char* const* saverNames();
uint8_t saverCount();

// Odtwarzanie: start() rysuje tło, update() przerysowuje tylko obszar postaci przy zmianie kroku.
class SaverPlayer {
 public:
  // clock: zegar z aplikacji – godzina u góry na środku (nullptr / nieustawiony = bez zegara).
  void start(const SaverAnimation* anim, uint32_t nowMs, const WallClock* clock = nullptr);
  void update(uint32_t nowMs);

 private:
  void drawStep(uint32_t step);
  void drawClock(uint32_t nowMs);

  const WallClock* clock_ = nullptr;
  int16_t shownMinutes_ = -1;  // godzina × 60 + minuta na ekranie (−1 = nic)

  const SaverAnimation* anim_ = nullptr;
  uint32_t startMs_ = 0;
  uint32_t lastStep_ = 0xFFFFFFFF;
  // Prostokąt postaci narysowany ostatnio (do zamalowania tłem po przesunięciu).
  int prevX_ = 0, prevY_ = 0, prevW_ = 0, prevH_ = 0;
};

}  // namespace chocpilot

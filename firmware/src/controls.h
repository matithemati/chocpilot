// Pokrętła EC11 (TIM2 / TIM3 w trybie enkodera), ich przyciski i suwak ADC – ChocPilot.
#pragma once

#include <stdint.h>

#include "debouncer.h"

namespace chocpilot {

class Controls {
 public:
  static constexpr uint8_t kEncoders = 2;

  using EncoderCallback = void (*)(uint8_t index, int16_t delta);  // index 1..2, delta w zatrzaskach
  using EncoderKeyCallback = void (*)(uint8_t index, bool down);
  using SliderCallback = void (*)(uint8_t value);  // 0–100

  void begin();
  // Wołane co ~1 ms (razem ze skanem matrycy).
  void update(uint32_t nowMs, uint8_t debounceMs, EncoderCallback onEncoder,
              EncoderKeyCallback onEncoderKey, SliderCallback onSlider);

  uint8_t slider() const { return sliderValue_; }

 private:
  void updateSlider(uint32_t nowMs, SliderCallback onSlider);

  uint16_t lastCount_[kEncoders] = {0, 0};
  int16_t pending_[kEncoders] = {0, 0};  // zliczenia timera jeszcze nie złożone w zatrzask
  Debouncer keys_[kEncoders];

  uint32_t lastSampleMs_ = 0;
  uint32_t lastSentMs_ = 0;
  int32_t filtered_ = -1;  // ADC × 16 (filtr wykładniczy), −1 = jeszcze bez próbki
  uint8_t sliderValue_ = 0;
  bool sliderSent_ = false;
};

}  // namespace chocpilot

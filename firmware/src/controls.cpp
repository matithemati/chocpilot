#include "controls.h"

#include <Arduino.h>

#include "boards/board.h"

namespace chocpilot {

namespace {

constexpr uint32_t kSliderSampleMs = 5;
constexpr uint32_t kSliderMinIntervalMs = 20;  // nie częściej niż 50 wiadomości/s
// Zakres ADC (12 bit) z martwymi strefami na końcach skoku – 0 i 100 osiągalne mimo tolerancji.
constexpr int32_t kAdcMin = 40;
constexpr int32_t kAdcMax = 4055;
// Histereza w 1/16 punktu procentowego: zmiana o mniej niż ~0,7 % nie jest zgłaszana.
constexpr int32_t kSliderHysteresis = 11;

TIM_TypeDef* const kTimers[Controls::kEncoders] = {TIM2, TIM3};

// Timer w trybie enkodera x4 (zliczanie na obu zboczach A i B) z filtrem wejść
// (fDTS/32, N = 8 przy CKD = /4 → ok. 20 µs) – drgania styków EC11 nie dają fałszywych kroków.
void encoderTimerInit(TIM_TypeDef* tim, uint8_t pinA, uint8_t pinB, uint32_t alternate) {
  GPIO_InitTypeDef io = {};
  io.Pin = digitalPinToBitMask(pinA) | digitalPinToBitMask(pinB);
  io.Mode = GPIO_MODE_AF_PP;
  io.Pull = GPIO_PULLUP;  // EC11: styki zwierają do C = GND
  io.Speed = GPIO_SPEED_FREQ_LOW;
  io.Alternate = alternate;
  HAL_GPIO_Init(digitalPinToPort(pinA), &io);

  tim->CR1 = TIM_CR1_CKD_1;  // tDTS = 4 × tCK_INT
  tim->SMCR = TIM_SMCR_SMS_1 | TIM_SMCR_SMS_0;  // tryb enkodera 3: oba kanały
  tim->CCMR1 = TIM_CCMR1_CC1S_0 | TIM_CCMR1_CC2S_0 | (0xFu << TIM_CCMR1_IC1F_Pos) |
               (0xFu << TIM_CCMR1_IC2F_Pos);
  tim->CCER = 0;  // bez odwracania polaryzacji
  tim->ARR = 0xFFFF;
  tim->CNT = 0;
  tim->CR1 |= TIM_CR1_CEN;
}

}  // namespace

void Controls::begin() {
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_TIM2_CLK_ENABLE();
  __HAL_RCC_TIM3_CLK_ENABLE();
  encoderTimerInit(TIM2, board::kEnc1A, board::kEnc1B, GPIO_AF2_TIM2);
  encoderTimerInit(TIM3, board::kEnc2A, board::kEnc2B, GPIO_AF1_TIM3);
  for (uint8_t i = 0; i < kEncoders; ++i) lastCount_[i] = static_cast<uint16_t>(kTimers[i]->CNT);

  pinMode(board::kEnc1Sw, INPUT_PULLUP);
  pinMode(board::kEnc2Sw, INPUT_PULLUP);
  const uint32_t now = millis();
  for (Debouncer& d : keys_) d.reset(false, now);

  analogReadResolution(12);
  pinMode(board::kSlider, INPUT_ANALOG);
}

void Controls::update(uint32_t nowMs, uint8_t debounceMs, EncoderCallback onEncoder,
                      EncoderKeyCallback onEncoderKey, SliderCallback onSlider) {
  for (uint8_t i = 0; i < kEncoders; ++i) {
    // 16-bitowa różnica licznika (TIM2 jest 32-bitowy, ale ARR = 0xFFFF) – odporna na przepełnienie.
    const uint16_t count = static_cast<uint16_t>(kTimers[i]->CNT);
    const int16_t diff = static_cast<int16_t>(count - lastCount_[i]);
    lastCount_[i] = count;
    pending_[i] = static_cast<int16_t>(pending_[i] + diff * board::kEncoderDir);
    const int16_t detents = pending_[i] / board::kEncoderCountsPerDetent;
    if (detents != 0) {
      pending_[i] = static_cast<int16_t>(pending_[i] - detents * board::kEncoderCountsPerDetent);
      if (onEncoder != nullptr) onEncoder(static_cast<uint8_t>(i + 1), detents);
    }
  }

  static const uint8_t kSwitchPins[kEncoders] = {board::kEnc1Sw, board::kEnc2Sw};
  for (uint8_t i = 0; i < kEncoders; ++i) {
    const bool raw = digitalRead(kSwitchPins[i]) == LOW;
    if (keys_[i].update(raw, nowMs, debounceMs) && onEncoderKey != nullptr) {
      onEncoderKey(static_cast<uint8_t>(i + 1), keys_[i].pressed());
    }
  }

  updateSlider(nowMs, onSlider);
}

void Controls::updateSlider(uint32_t nowMs, SliderCallback onSlider) {
  if (nowMs - lastSampleMs_ < kSliderSampleMs) return;
  lastSampleMs_ = nowMs;
  const int32_t raw = analogRead(board::kSlider) * 16;
  filtered_ = filtered_ < 0 ? raw : filtered_ + (raw - filtered_) / 8;

  // Położenie w 1/16 %: ograniczone do martwych stref, potem histereza względem ostatniej wartości.
  int32_t adc = filtered_ / 16;
  if (adc < kAdcMin) adc = kAdcMin;
  if (adc > kAdcMax) adc = kAdcMax;
  const int32_t pos16 = (adc - kAdcMin) * 100 * 16 / (kAdcMax - kAdcMin);
  const int32_t current16 = static_cast<int32_t>(sliderValue_) * 16;
  const int32_t delta = pos16 - current16;
  if (sliderSent_ && delta > -kSliderHysteresis && delta < kSliderHysteresis) return;
  const uint8_t value = static_cast<uint8_t>((pos16 + 8) / 16);
  if (sliderSent_ && value == sliderValue_) return;
  if (sliderSent_ && nowMs - lastSentMs_ < kSliderMinIntervalMs) return;
  sliderValue_ = value;
  sliderSent_ = true;
  lastSentMs_ = nowMs;
  if (onSlider != nullptr) onSlider(value);
}

}  // namespace chocpilot

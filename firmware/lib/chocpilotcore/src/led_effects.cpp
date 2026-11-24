#include "led_effects.h"

namespace chocpilot {

namespace {

constexpr Rgb kOnline = {0, 150, 180};
constexpr Rgb kOffline = {255, 110, 0};

uint8_t scale8(uint8_t value, uint8_t level) {
  return static_cast<uint8_t>(static_cast<uint16_t>(value) * level / 255);
}

Rgb scaled(Rgb c, uint8_t level) { return {scale8(c.r, level), scale8(c.g, level), scale8(c.b, level)}; }

// Okres oddychania: tempo 1 = 6 s … 10 = ok. 1 s.
uint32_t breathePeriodMs(uint8_t speed) { return 6000UL - (speed - 1) * 550UL; }
// Pełny obrót tęczy: tempo 1 = 12 s … 10 = ok. 1,7 s.
uint32_t rainbowPeriodMs(uint8_t speed) { return 12000UL - (speed - 1) * 1150UL; }

uint8_t clampSpeed(uint8_t speed) {
  if (speed < kLedSpeedMin) return kLedSpeedMin;
  return speed > kLedSpeedMax ? kLedSpeedMax : speed;
}

}  // namespace

Rgb hueToRgb(uint8_t hue) {
  // 6 odcinków po ok. 43 kroki: czerwony → żółty → zielony → turkus → niebieski → fiolet.
  const uint8_t region = hue / 43;
  const uint8_t rem = static_cast<uint8_t>((hue - region * 43) * 6);
  const uint8_t up = rem;
  const uint8_t down = static_cast<uint8_t>(255 - rem);
  switch (region) {
    case 0:
      return {255, up, 0};
    case 1:
      return {down, 255, 0};
    case 2:
      return {0, 255, up};
    case 3:
      return {0, down, 255};
    case 4:
      return {up, 0, 255};
    default:
      return {255, 0, down};
  }
}

uint8_t renderLeds(const LedSettings& s, const LedFrame& f, Rgb* out, uint8_t count) {
  const uint8_t level = scale8(s.brightness, kLedMaxLevel);
  if (f.sleeping || (s.mode == LedMode::Off && !f.test)) {
    for (uint8_t i = 0; i < count; ++i) out[i] = {0, 0, 0};
    return 0;
  }
  if (f.test) {
    static constexpr Rgb kCycle[] = {{255, 0, 0}, {0, 255, 0}, {0, 0, 255}, {255, 255, 255}};
    // W teście co najmniej połowa jasności, żeby było widać każdą diodę.
    const uint8_t testLevel = level > kLedMaxLevel / 2 ? level : kLedMaxLevel / 2;
    const Rgb c = scaled(kCycle[(f.now / 500) % 4], testLevel);
    for (uint8_t i = 0; i < count; ++i) out[i] = c;
    return 0;
  }

  const Rgb color = {s.r, s.g, s.b};
  const uint8_t speed = clampSpeed(s.speed);
  switch (s.mode) {
    case LedMode::Status:
      for (uint8_t i = 0; i < count; ++i) out[i] = f.online ? kOnline : kOffline;
      break;
    case LedMode::Static:
      for (uint8_t i = 0; i < count; ++i) out[i] = color;
      break;
    case LedMode::Breathe: {
      // Trójkąt podniesiony do kwadratu – łagodne wygaszanie, minimum ok. 12 %.
      const uint32_t period = breathePeriodMs(speed);
      const uint32_t phase = (f.now % period) * 512 / period;  // 0…511
      const uint32_t tri = phase < 256 ? phase : 511 - phase;  // 0…255
      const uint8_t k = static_cast<uint8_t>(30 + tri * tri * 225 / 65025);
      const Rgb c = scaled(color, k);
      for (uint8_t i = 0; i < count; ++i) out[i] = c;
      break;
    }
    case LedMode::Rainbow: {
      const uint32_t period = rainbowPeriodMs(speed);
      const uint8_t base = static_cast<uint8_t>((f.now % period) * 256 / period);
      for (uint8_t i = 0; i < count; ++i) {
        out[i] = hueToRgb(static_cast<uint8_t>(base + i * 256 / count));
      }
      break;
    }
    case LedMode::Off:
      break;
  }

  // Błysk: dioda przy klawiszu rozjaśnia się do bieli i wraca do efektu w kLedReactMs.
  uint8_t stillActive = 0;
  if (s.react && f.keyDownAt != nullptr && f.keyLed != nullptr) {
    for (uint8_t k = 0; k < kTotalKeys; ++k) {
      if (!(f.reactMask & (1u << k))) continue;
      const uint32_t age = f.now - f.keyDownAt[k];
      if (age >= kLedReactMs) continue;
      stillActive = static_cast<uint8_t>(stillActive | (1u << k));
      const uint8_t led = f.keyLed[k];
      if (led >= count) continue;
      const uint8_t mix = static_cast<uint8_t>((kLedReactMs - age) * 255 / kLedReactMs);
      Rgb& c = out[led];
      c.r = static_cast<uint8_t>(c.r + scale8(static_cast<uint8_t>(255 - c.r), mix));
      c.g = static_cast<uint8_t>(c.g + scale8(static_cast<uint8_t>(255 - c.g), mix));
      c.b = static_cast<uint8_t>(c.b + scale8(static_cast<uint8_t>(255 - c.b), mix));
    }
  }

  for (uint8_t i = 0; i < count; ++i) out[i] = scaled(out[i], level);
  return stillActive;
}

}  // namespace chocpilot

// 12 × WS2812B-V6 na spodzie płytki – dane z SPI2 MOSI przez 74AHCT1G125.
#pragma once

#include <stdint.h>

#include "led_effects.h"

namespace chocpilot {
namespace leds {

using Color = Rgb;

void begin();
// Wysyła kolory wszystkich diod (kolejność łańcucha L1 → L12). Blokuje ok. 0,4 ms.
void show(const Color* colors, uint8_t count);
// Wszystkie diody w jednym kolorze.
void fill(Color color);

}  // namespace leds
}  // namespace chocpilot

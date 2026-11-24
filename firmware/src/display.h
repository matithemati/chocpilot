// Wybór ekranu: kolorowy LCD ST7789 (ChocPilot v0) albo OLED SSD1309 (Pro Micro).
#pragma once

#if defined(CHOCPILOT_BOARD_V0)
#include "display_tft.h"
#else
#include "display_oled.h"
#endif

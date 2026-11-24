// Wybór płytki: CHOCPILOT_BOARD_V0 (środowisko chocpilot_v0) albo Arduino Pro Micro.
#pragma once

#if defined(CHOCPILOT_BOARD_V0)
#include "board_v0.h"
#else
#include "board_promicro.h"
#endif

// Stałe kompilacji firmware ChocPilot.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "device_config.h"

#ifndef CHOCPILOT_FW_VERSION
#define CHOCPILOT_FW_VERSION "1.0.0"
#endif

// Domyślny adres I²C wyświetlacza (nadpisywany ustawieniem oled_addr).
#ifndef CHOCPILOT_OLED_ADDR
#define CHOCPILOT_OLED_ADDR 0x3C
#endif

namespace chocpilot {

constexpr uint32_t kScanIntervalUs = 1000;      // skan matrycy co 1 ms
constexpr uint32_t kRowSettleUs = 5;            // ustalenie po przełączeniu wiersza
constexpr uint32_t kHeartbeatTimeoutMs = 3000;  // brak ping → offline
constexpr uint32_t kTestComboHoldMs = 3000;     // K1+K4 → tryb testu
constexpr uint32_t kTestComboBootWindowMs = 500;  // kombinacja musi być wciśnięta od startu
constexpr uint32_t kConfigSaveDelayMs = 3000;   // opóźniony zapis (oszczędzanie flash)
constexpr size_t kConfigBufSize = 1 + sizeof(DeviceConfig);  // zapis binarny (device_config.cpp)

}  // namespace chocpilot

// Warstwa sprzętowa (HAL): USB, EEPROM, restart. Implementacja: hal_promicro.cpp.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace chocpilot {
namespace hal {

// --- board ---
// Wczesna inicjalizacja USB (nazwa produktu, HID) – przed Serial.
void usbBegin();
// Restart; bootloader=true → bootloader Caterina (wgrywanie firmware).
[[noreturn]] void reboot(bool bootloader);

// --- storage ---
// Jeden blob z konfiguracją urządzenia (dane binarne w EEPROM).
bool storageBegin();
// Zwraca liczbę wczytanych bajtów (0 = brak danych). Bufor zakończony \0, jeśli jest miejsce.
size_t storageLoad(char* buf, size_t cap);
bool storageSave(const char* data, size_t len);

// --- usb_hid ---
bool hidReady();
// Raport klawiatury: modyfikatory + do 6 kodów (0 = brak).
void hidKeyboardReport(uint8_t mods, const uint8_t keys[6]);
// Consumer control: usage != 0 → wciśnięty, 0 → zwolniony.
void hidConsumerReport(uint16_t usage);


}  // namespace hal
}  // namespace chocpilot

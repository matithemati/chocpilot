// Warstwa sprzętowa (HAL): USB (CDC + HID), pamięć nieulotna, restart.
// Implementacje: hal_promicro.cpp (ATmega32U4), hal_stm32.cpp (ChocPilot v0, STM32F072).
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace chocpilot {
namespace hal {

// --- board ---
// Wczesna inicjalizacja USB (nazwa produktu, HID) – przed serialBegin().
void usbBegin();
// Obsługa stosu USB – wołane w każdym obiegu pętli (na AVR robi to rdzeń Arduino).
void poll();
// Restart; bootloader=true → bootloader (Pro Micro: Caterina, STM32: DFU w ROM).
[[noreturn]] void reboot(bool bootloader);

// --- usb_cdc (łącze z aplikacją) ---
void serialBegin();
int serialAvailable();
// Kolejny bajt albo −1.
int serialRead();
// Czy port jest otwarty po stronie PC (DTR) – bez tego wiadomości są pomijane.
bool serialConnected();
void serialWrite(const uint8_t* data, size_t len);
void serialFlush();

// --- storage ---
// Jeden blob z konfiguracją urządzenia (dane binarne w EEPROM / emulacji EEPROM we flash).
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

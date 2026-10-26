// Warstwa sprzętowa (HAL). Jedyne miejsce z kodem zależnym od płytki to implementacje
// hal_kb2040.cpp, hal_xiao_esp32s3.cpp i hal_promicro.cpp (kompilowane warunkowo w całości).
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace chocpilot {
namespace hal {

// --- board ---
// Wczesna inicjalizacja USB (nazwa produktu, HID) – przed Serial.
void usbBegin();
// Uruchomienie magistrali I²C na pinach z mapy płytki.
void i2cBegin();
// Restart; bootloader=true → tryb wgrywania (UF2 / ROM download / Caterina).
[[noreturn]] void reboot(bool bootloader);

// --- storage ---
// Jeden blob z konfiguracją urządzenia: tekst JSON, a przy CHOCPILOT_COMPACT – dane binarne.
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

#if defined(CHOCPILOT_BOARD_PROMICRO)
// --- encoder ---
// ATmega32U4: piny enkodera nie mają INTx – przerwanie pin change (PCINT0) woła `isr`.
void encoderIrqBegin(void (*isr)());
#endif

// --- status_led ---
enum class LedState : uint8_t { Offline, Online, Test };
void statusLedBegin();
void statusLedSet(LedState state);
// Krótki sygnał zdarzenia (naciśnięcie / obrót).
void statusLedPulse();
// Wywoływane w pętli – animacje (miganie, wygaszanie błysku).
void statusLedUpdate(uint32_t nowMs);

}  // namespace hal
}  // namespace chocpilot

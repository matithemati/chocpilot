// HAL: Arduino / SparkFun Pro Micro (ATmega32U4, rdzeń Arduino AVR, PluggableUSB HID, EEPROM).
#if defined(CHOCPILOT_BOARD_PROMICRO)

#include <Arduino.h>
#include <EEPROM.h>
#include <HID.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <string.h>
#include <util/crc16.h>

#include "../boards/board.h"
#include "hal.h"

namespace chocpilot {
namespace hal {

namespace {

enum : uint8_t { kRidKeyboard = 1, kRidConsumer = 2 };

// Klawiatura (modyfikatory + 6 kodów) i consumer control (jeden 16-bitowy usage).
const uint8_t kHidReportDesc[] PROGMEM = {
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, kRidKeyboard,  // Generic Desktop / Keyboard
    0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x02,                      // 8 bitów modyfikatorów
    0x95, 0x01, 0x75, 0x08, 0x81, 0x03,                      // bajt zarezerwowany
    0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x26, 0xFF, 0x00,
    0x05, 0x07, 0x19, 0x00, 0x2A, 0xFF, 0x00, 0x81, 0x00,    // 6 kodów klawiszy
    0xC0,
    0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, kRidConsumer,  // Consumer Control
    0x15, 0x00, 0x26, 0xFF, 0x03, 0x19, 0x00, 0x2A, 0xFF, 0x03,
    0x75, 0x10, 0x95, 0x01, 0x81, 0x00,
    0xC0,
};

// Rdzeń AVR podłącza USB przed setup(), więc deskryptor HID musi być dodany już przy
// inicjalizacji obiektów statycznych (tak robi też biblioteka Keyboard).
struct HidRegistration {
  HIDSubDescriptor node{kHidReportDesc, sizeof(kHidReportDesc)};
  HidRegistration() { HID().AppendDescriptor(&node); }
};
HidRegistration hidRegistration;

// EEPROM (1 KB): nagłówek [znacznik 2 B][długość 2 B][CRC-8 1 B] + dane.
constexpr uint16_t kMagic = 0x5433;  // „T3”
constexpr int kHeaderSize = 5;

uint8_t crcOf(const uint8_t* data, size_t len) {
  uint8_t crc = 0;
  for (size_t i = 0; i < len; ++i) crc = _crc_ibutton_update(crc, data[i]);
  return crc;
}

void (*encoderIsr)() = nullptr;

}  // namespace

// --- board ---

void usbBegin() {
  // USB CDC + HID uruchamia rdzeń Arduino (main.cpp → USBDevice.attach()).
}

void i2cBegin() {
  // Ekran tylko przez programowe I²C (U8g2 SW_I2C) – sprzętowy TWI nie jest używany.
}

void reboot(bool bootloader) {
  delay(50);  // czas na wysłanie ack
  // Caterina po resecie watchdogiem sprawdza „magiczny klucz” 0x7777: stary bootloader
  // pod adresem 0x0800, nowy (LUFA) w RAMEND-1. Zapis w oba miejsca obsługuje oba warianty.
  // Bez klucza bootloader od razu uruchamia program, więc ten sam reset służy do zwykłego restartu.
  cli();
  const uint16_t key = bootloader ? 0x7777 : 0;
  *reinterpret_cast<volatile uint16_t*>(0x0800) = key;
  *reinterpret_cast<volatile uint16_t*>(RAMEND - 1) = key;
  wdt_enable(WDTO_15MS);
  while (true) {
  }
}

// --- storage ---

bool storageBegin() { return true; }

size_t storageLoad(char* buf, size_t cap) {
  uint8_t header[kHeaderSize];
  for (int i = 0; i < kHeaderSize; ++i) header[i] = EEPROM.read(i);
  const uint16_t magic = static_cast<uint16_t>(header[0] << 8 | header[1]);
  const size_t len = static_cast<size_t>(header[2] << 8 | header[3]);
  if (magic != kMagic || len == 0 || len > cap ||
      len > static_cast<size_t>(EEPROM.length() - kHeaderSize)) {
    return 0;
  }
  uint8_t* out = reinterpret_cast<uint8_t*>(buf);
  for (size_t i = 0; i < len; ++i) out[i] = EEPROM.read(static_cast<int>(kHeaderSize + i));
  if (crcOf(out, len) != header[4]) return 0;
  if (len < cap) buf[len] = '\0';
  return len;
}

bool storageSave(const char* data, size_t len) {
  if (len == 0 || len > static_cast<size_t>(EEPROM.length() - kHeaderSize)) return false;
  const uint8_t* in = reinterpret_cast<const uint8_t*>(data);
  // update() zapisuje tylko zmienione bajty (oszczędza EEPROM). Zapis nie jest atomowy:
  // przerwany przez odłączenie zasilania kończy się złym CRC i wartościami domyślnymi.
  EEPROM.update(0, static_cast<uint8_t>(kMagic >> 8));
  EEPROM.update(1, static_cast<uint8_t>(kMagic & 0xFF));
  EEPROM.update(2, static_cast<uint8_t>(len >> 8));
  EEPROM.update(3, static_cast<uint8_t>(len & 0xFF));
  EEPROM.update(4, crcOf(in, len));
  for (size_t i = 0; i < len; ++i) EEPROM.update(static_cast<int>(kHeaderSize + i), in[i]);
  return true;
}

// --- usb_hid ---

bool hidReady() { return USBDevice.configured(); }

void hidKeyboardReport(uint8_t mods, const uint8_t keys[6]) {
  uint8_t report[8];
  report[0] = mods;
  report[1] = 0;
  memcpy(report + 2, keys, 6);
  HID().SendReport(kRidKeyboard, report, sizeof(report));
}

void hidConsumerReport(uint16_t usage) {
  HID().SendReport(kRidConsumer, &usage, sizeof(usage));  // little-endian jak w HID
}

// --- encoder ---

void encoderIrqBegin(void (*isr)()) {
  encoderIsr = isr;
  *digitalPinToPCMSK(board::kEncA) |= _BV(digitalPinToPCMSKbit(board::kEncA));
  *digitalPinToPCMSK(board::kEncB) |= _BV(digitalPinToPCMSKbit(board::kEncB));
  PCIFR = _BV(PCIF0);
  PCICR |= _BV(PCIE0);
}

// --- status_led ---
// Diody RX/TX Pro Micro steruje rdzeń USB (miganie przy transmisji), a innej diody płytka
// nie ma – stan pokazuje tylko ekran.

void statusLedBegin() {}

void statusLedSet(LedState state) { (void)state; }

void statusLedPulse() {}

void statusLedUpdate(uint32_t nowMs) { (void)nowMs; }

}  // namespace hal
}  // namespace chocpilot

ISR(PCINT0_vect) {
  if (chocpilot::hal::encoderIsr != nullptr) chocpilot::hal::encoderIsr();
}

#endif  // CHOCPILOT_BOARD_PROMICRO

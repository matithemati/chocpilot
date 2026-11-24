// HAL: ChocPilot v0 (STM32F072CBT6, rdzeń STM32duino). USB CDC + HID przez TinyUSB,
// konfiguracja w emulacji EEPROM rdzenia (ostatnia strona flash), bootloader DFU w ROM.

#include <Arduino.h>
#include <utility/stm32_eeprom.h>  // emulacja EEPROM rdzenia (biblioteka EEPROM): API z buforem
#include <string.h>

#include "hal.h"
#include "tusb.h"
#include "usb_ids.h"

namespace chocpilot {
namespace hal {

namespace {

// Emulacja EEPROM: nagłówek [znacznik 2 B][długość 2 B][CRC-8 1 B] + dane (jak na Pro Micro).
constexpr uint16_t kMagic = 0x5433;  // „T3”
constexpr uint32_t kHeaderSize = 5;
constexpr uint32_t kEepromSize = E2END + 1;

// Bootloader systemowy STM32F07x (AN2606): pamięć systemowa od 0x1FFFC800.
constexpr uint32_t kSystemMemory = 0x1FFFC800;

constexpr uint32_t kWriteTimeoutMs = 50;

// Znacznik „wejdź do bootloadera” – słowo 1 KB poniżej końca RAM: poza .data/.bss (firmware
// zajmuje ok. 6,5 z 16 KB), a stos przy starcie (przed enterBootloader) jest płytszy niż 1 KB.
// Reset nie czyści RAM, a kod startowy zeruje tylko .bss.
constexpr uint32_t kBootMagic = 0xB007D0F1;
}  // namespace
}  // namespace hal
}  // namespace chocpilot

extern "C" uint32_t _estack;  // koniec RAM (skrypt linkera)

namespace chocpilot {
namespace hal {
namespace {

inline volatile uint32_t& bootFlag() {
  return *reinterpret_cast<volatile uint32_t*>(reinterpret_cast<uintptr_t>(&_estack) - 1024);
}

// CRC-8 Dallas/Maxim (wielomian 0x31 odbity = 0x8C) – ten sam co _crc_ibutton_update na AVR.
uint8_t crcOf(const uint8_t* data, size_t len) {
  uint8_t crc = 0;
  for (size_t i = 0; i < len; ++i) {
    crc ^= data[i];
    for (uint8_t bit = 0; bit < 8; ++bit) crc = (crc & 1) ? (crc >> 1) ^ 0x8C : crc >> 1;
  }
  return crc;
}

// Skok do bootloadera DFU w ROM. Z działającego firmware (zegar 48 MHz, USB, timery, przerwania)
// bootloader F072 nie startuje poprawnie, więc: znacznik w RAM → reset → skok w enterBootloader()
// zaraz po resecie, zanim STM32duino skonfiguruje zegar i peryferia.
[[noreturn]] void jumpToBootloader() {
  // Odłączenie od hosta (pull-up D+), żeby Windows zauważył nowe urządzenie DFU.
  tud_disconnect();
  delay(100);
  __disable_irq();
  bootFlag() = kBootMagic;
  NVIC_SystemReset();
  while (true) {
  }
}

}  // namespace

// --- board ---

void usbBegin() {
  __HAL_RCC_USB_CLK_ENABLE();
  tud_init(0);
}

void poll() { tud_task(); }

void reboot(bool bootloader) {
  delay(50);  // czas na wysłanie ack
  if (bootloader) jumpToBootloader();
  tud_disconnect();
  delay(20);
  NVIC_SystemReset();
  while (true) {
  }
}

// --- usb_cdc ---

void serialBegin() {}

int serialAvailable() { return static_cast<int>(tud_cdc_available()); }

int serialRead() { return tud_cdc_read_char(); }

bool serialConnected() { return tud_cdc_connected(); }

void serialWrite(const uint8_t* data, size_t len) {
  // Bufor TX (512 B) zwykle mieści całą wiadomość; gdy jest pełny – obsługa USB i krótkie
  // czekanie, a po kWriteTimeoutMs reszta jest pomijana (port zamknięty / host nie czyta).
  const uint32_t start = millis();
  size_t off = 0;
  while (off < len && tud_cdc_connected()) {
    const uint32_t n = tud_cdc_write(data + off, static_cast<uint32_t>(len - off));
    off += n;
    if (n == 0) {
      tud_cdc_write_flush();
      tud_task();
      if (millis() - start > kWriteTimeoutMs) return;
    }
  }
  tud_cdc_write_flush();
}

void serialFlush() {
  const uint32_t start = millis();
  tud_cdc_write_flush();
  while (tud_cdc_connected() && tud_cdc_write_available() < CFG_TUD_CDC_TX_BUFSIZE &&
         millis() - start < kWriteTimeoutMs) {
    tud_task();
    tud_cdc_write_flush();
  }
}

// --- storage ---

bool storageBegin() {
  eeprom_buffer_fill();  // kopia strony flash w RAM; odczyty i zapisy idą przez bufor
  return true;
}

size_t storageLoad(char* buf, size_t cap) {
  uint8_t header[kHeaderSize];
  for (uint32_t i = 0; i < kHeaderSize; ++i) header[i] = eeprom_buffered_read_byte(i);
  const uint16_t magic = static_cast<uint16_t>(header[0] << 8 | header[1]);
  const size_t len = static_cast<size_t>(header[2] << 8 | header[3]);
  if (magic != kMagic || len == 0 || len > cap || len > kEepromSize - kHeaderSize) return 0;
  uint8_t* out = reinterpret_cast<uint8_t*>(buf);
  for (size_t i = 0; i < len; ++i) out[i] = eeprom_buffered_read_byte(kHeaderSize + i);
  if (crcOf(out, len) != header[4]) return 0;
  if (len < cap) buf[len] = '\0';
  return len;
}

bool storageSave(const char* data, size_t len) {
  if (len == 0 || len > kEepromSize - kHeaderSize) return false;
  const uint8_t* in = reinterpret_cast<const uint8_t*>(data);
  const uint8_t header[kHeaderSize] = {
      static_cast<uint8_t>(kMagic >> 8), static_cast<uint8_t>(kMagic & 0xFF),
      static_cast<uint8_t>(len >> 8), static_cast<uint8_t>(len & 0xFF), crcOf(in, len)};
  // Strona flash jest kasowana i zapisywana w całości – tylko gdy dane się zmieniły.
  bool changed = false;
  for (uint32_t i = 0; i < kHeaderSize; ++i) {
    if (eeprom_buffered_read_byte(i) != header[i]) {
      eeprom_buffered_write_byte(i, header[i]);
      changed = true;
    }
  }
  for (size_t i = 0; i < len; ++i) {
    if (eeprom_buffered_read_byte(kHeaderSize + i) != in[i]) {
      eeprom_buffered_write_byte(kHeaderSize + i, in[i]);
      changed = true;
    }
  }
  if (changed) eeprom_buffer_flush();
  return true;
}

// --- usb_hid ---

bool hidReady() { return tud_hid_ready(); }

void hidKeyboardReport(uint8_t mods, const uint8_t keys[6]) {
  uint8_t codes[6];
  memcpy(codes, keys, sizeof(codes));
  tud_hid_keyboard_report(usb::kReportKeyboard, mods, codes);
}

void hidConsumerReport(uint16_t usage) {
  tud_hid_report(usb::kReportConsumer, &usage, sizeof(usage));  // little-endian jak w HID
}

}  // namespace hal
}  // namespace chocpilot

extern "C" {

// Zegar: SYSCLK = HSI48 (48 MHz, bez kwarcu), USB z HSI48 dostrajanego przez CRS do ramek SOF
// hosta (RM0091 §7.2.3). Zastępuje słabą definicję z wariantu STM32duino.
void SystemClock_Config(void) {
  RCC_OscInitTypeDef osc = {};
  osc.OscillatorType = RCC_OSCILLATORTYPE_HSI48;
  osc.HSI48State = RCC_HSI48_ON;
  osc.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&osc) != HAL_OK) Error_Handler();

  RCC_ClkInitTypeDef clk = {};
  clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1;
  clk.SYSCLKSource = RCC_SYSCLKSOURCE_HSI48;
  clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
  clk.APB1CLKDivider = RCC_HCLK_DIV1;
  if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_1) != HAL_OK) Error_Handler();

  RCC_PeriphCLKInitTypeDef periph = {};
  periph.PeriphClockSelection = RCC_PERIPHCLK_USB;
  periph.UsbClockSelection = RCC_USBCLKSOURCE_HSI48;
  if (HAL_RCCEx_PeriphCLKConfig(&periph) != HAL_OK) Error_Handler();

  __HAL_RCC_CRS_CLK_ENABLE();
  RCC_CRSInitTypeDef crs = {};
  crs.Prescaler = RCC_CRS_SYNC_DIV1;
  crs.Source = RCC_CRS_SYNC_SOURCE_USB;
  crs.Polarity = RCC_CRS_SYNC_POLARITY_RISING;
  crs.ReloadValue = __HAL_RCC_CRS_RELOADVALUE_CALCULATE(48000000, 1000);
  crs.ErrorLimitValue = RCC_CRS_ERRORLIMIT_DEFAULT;
  crs.HSI48CalibrationValue = RCC_CRS_HSI48CALIBRATION_DEFAULT;
  HAL_RCCEx_CRSConfig(&crs);
}

void USB_IRQHandler(void) { tud_int_handler(0); }

uint32_t tusb_time_millis_api(void) { return millis(); }

}  // extern "C"

// Po resecie z jumpToBootloader(): skok do pamięci systemowej, zanim premain() (konstruktor
// o priorytecie 101 w rdzeniu STM32duino) uruchomi HAL i zegar 48 MHz.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wprio-ctor-dtor"
__attribute__((constructor(100))) static void enterBootloader() {
  using chocpilot::hal::bootFlag;
  if (bootFlag() != chocpilot::hal::kBootMagic) return;
  bootFlag() = 0;  // następny reset (np. RESET po wgraniu) – znów firmware
  __HAL_RCC_SYSCFG_CLK_ENABLE();
  __HAL_SYSCFG_REMAPMEMORY_SYSTEMFLASH();  // wektory pod adresem 0 = pamięć systemowa
  const uint32_t stack = *reinterpret_cast<volatile uint32_t*>(chocpilot::hal::kSystemMemory);
  const uint32_t entry = *reinterpret_cast<volatile uint32_t*>(chocpilot::hal::kSystemMemory + 4);
  __set_MSP(stack);
  reinterpret_cast<void (*)()>(entry)();
  while (true) {
  }
}
#pragma GCC diagnostic pop

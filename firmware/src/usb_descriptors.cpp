// Deskryptory USB ChocPilot (TinyUSB): urządzenie złożone CDC + HID.
// Aplikacja szuka portu po nazwie „ChocPilot” (iProduct / iInterface CDC).
#include <Arduino.h>
#include <string.h>

#include "tusb.h"
#include "usb_ids.h"

namespace {

// VID 0x1209 (pid.codes), PID 0x0001 = testowy PID pid.codes – na własny użytek.
constexpr uint16_t kVid = 0x1209;
constexpr uint16_t kPid = 0x0001;
constexpr uint16_t kBcdDevice = 0x0110;

enum : uint8_t { kItfCdc = 0, kItfCdcData, kItfHid, kItfTotal };
enum : uint8_t { kEpCdcNotif = 0x81, kEpCdcOut = 0x02, kEpCdcIn = 0x82, kEpHid = 0x83 };
enum : uint8_t { kStrLang = 0, kStrManufacturer, kStrProduct, kStrSerial, kStrCdc, kStrHid };

const tusb_desc_device_t kDeviceDesc = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    // IAD: klasa „Miscellaneous / Common / Interface Association” dla złożonego CDC + HID
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = kVid,
    .idProduct = kPid,
    .bcdDevice = kBcdDevice,
    .iManufacturer = kStrManufacturer,
    .iProduct = kStrProduct,
    .iSerialNumber = kStrSerial,
    .bNumConfigurations = 1,
};

// Klawiatura (modyfikatory + 6 kodów) i consumer control (raporty jak w standardowej klawiaturze Arduino).
const uint8_t kHidReportDesc[] = {
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, chocpilot::usb::kReportKeyboard,  // Keyboard
    0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x02,                      // 8 bitów modyfikatorów
    0x95, 0x01, 0x75, 0x08, 0x81, 0x03,                      // bajt zarezerwowany
    0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x26, 0xFF, 0x00,
    0x05, 0x07, 0x19, 0x00, 0x2A, 0xFF, 0x00, 0x81, 0x00,    // 6 kodów klawiszy
    0xC0,
    0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, chocpilot::usb::kReportConsumer,  // Consumer
    0x15, 0x00, 0x26, 0xFF, 0x03, 0x19, 0x00, 0x2A, 0xFF, 0x03,
    0x75, 0x10, 0x95, 0x01, 0x81, 0x00,
    0xC0,
};

constexpr uint16_t kConfigLen = TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN + TUD_HID_DESC_LEN;

const uint8_t kConfigDesc[] = {
    // płytka z 12 LED może pobierać więcej niż 100 mA – deklarowane 500 mA
    TUD_CONFIG_DESCRIPTOR(1, kItfTotal, 0, kConfigLen, 0x00, 500),
    TUD_CDC_DESCRIPTOR(kItfCdc, kStrCdc, kEpCdcNotif, 8, kEpCdcOut, kEpCdcIn, 64),
    TUD_HID_DESCRIPTOR(kItfHid, kStrHid, HID_ITF_PROTOCOL_NONE, sizeof(kHidReportDesc), kEpHid,
                       CFG_TUD_HID_EP_BUFSIZE, 10),
};

const char* const kStrings[] = {
    nullptr,          // język – osobno
    "ChocPilot",      // producent
    "ChocPilot",      // produkt
    nullptr,          // numer seryjny – z UID układu
    "ChocPilot",      // interfejs CDC (Windows pokazuje go jako opis portu COM)
    "ChocPilot HID",  // interfejs HID
};

uint16_t gStrBuf[32];

// Numer seryjny: 96-bitowy UID STM32F072 (RM0091 §33.1) jako 24 cyfry szesnastkowe.
uint8_t serialString(uint16_t* out, uint8_t cap) {
  const uint8_t* uid = reinterpret_cast<const uint8_t*>(UID_BASE);
  static const char kHex[] = "0123456789ABCDEF";
  uint8_t n = 0;
  for (uint8_t i = 0; i < 12 && n + 2 <= cap; ++i) {
    out[n++] = static_cast<uint16_t>(kHex[uid[i] >> 4]);
    out[n++] = static_cast<uint16_t>(kHex[uid[i] & 0x0F]);
  }
  return n;
}

}  // namespace

extern "C" {

uint8_t const* tud_descriptor_device_cb(void) {
  return reinterpret_cast<uint8_t const*>(&kDeviceDesc);
}

uint8_t const* tud_descriptor_configuration_cb(uint8_t index) {
  (void)index;
  return kConfigDesc;
}

uint8_t const* tud_hid_descriptor_report_cb(uint8_t instance) {
  (void)instance;
  return kHidReportDesc;
}

uint16_t const* tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
  (void)langid;
  constexpr uint8_t kMaxChars = sizeof(gStrBuf) / sizeof(gStrBuf[0]) - 1;
  uint8_t count = 0;
  if (index == kStrLang) {
    gStrBuf[1] = 0x0409;  // angielski (USA)
    count = 1;
  } else if (index == kStrSerial) {
    count = serialString(gStrBuf + 1, kMaxChars);
  } else if (index < sizeof(kStrings) / sizeof(kStrings[0]) && kStrings[index] != nullptr) {
    const char* s = kStrings[index];
    while (s[count] != '\0' && count < kMaxChars) {
      gStrBuf[1 + count] = static_cast<uint16_t>(s[count]);
      ++count;
    }
  } else {
    return nullptr;
  }
  gStrBuf[0] = static_cast<uint16_t>((TUSB_DESC_STRING << 8) | (2 * count + 2));
  return gStrBuf;
}

// Raporty HID na żądanie hosta (GET_REPORT / SET_REPORT, np. diody LED klawiatury) – nieużywane.
uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type,
                               uint8_t* buffer, uint16_t reqlen) {
  (void)instance;
  (void)report_id;
  (void)report_type;
  (void)buffer;
  (void)reqlen;
  return 0;
}

void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id, hid_report_type_t report_type,
                           uint8_t const* buffer, uint16_t bufsize) {
  (void)instance;
  (void)report_id;
  (void)report_type;
  (void)buffer;
  (void)bufsize;
}

}  // extern "C"

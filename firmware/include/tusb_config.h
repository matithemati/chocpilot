// TinyUSB – konfiguracja dla ChocPilot (STM32F072, USB FS bez kwarcu).
// Urządzenie złożone: CDC (łącze z aplikacją, JSON Lines) + HID (klawiatura i multimedia
// w trybie awaryjnym). Deskryptory: src/usb_descriptors.cpp.
#pragma once

#ifndef CFG_TUSB_MCU
#define CFG_TUSB_MCU OPT_MCU_STM32F0
#endif

#define CFG_TUSB_OS OPT_OS_NONE
#define CFG_TUSB_DEBUG 0

#define CFG_TUD_ENABLED 1
#define CFG_TUD_MAX_SPEED OPT_MODE_FULL_SPEED
#define CFG_TUSB_RHPORT0_MODE (OPT_MODE_DEVICE | OPT_MODE_FULL_SPEED)

#define CFG_TUD_ENDPOINT0_SIZE 64

#define CFG_TUD_CDC 1
#define CFG_TUD_HID 1
#define CFG_TUD_MSC 0
#define CFG_TUD_MIDI 0
#define CFG_TUD_VENDOR 0

// Bufory CDC: hello z diagnostyką ma ok. 220 B, komendy od PC do 272 B (max_line).
#define CFG_TUD_CDC_RX_BUFSIZE 512
#define CFG_TUD_CDC_TX_BUFSIZE 512
#define CFG_TUD_CDC_EP_BUFSIZE 64

// Raport klawiatury: ID + modyfikatory + bajt zarezerwowany + 6 kodów.
#define CFG_TUD_HID_EP_BUFSIZE 16

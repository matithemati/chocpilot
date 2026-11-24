#include "protocol.h"

#include "boards/board.h"
#include "config.h"
#include "hal/hal.h"

namespace chocpilot {

void Link::begin() { hal::serialBegin(); }

void Link::poll(LineHandler handler) {
#if defined(CHOCPILOT_BOARD_V0)
  // Seria komend (np. ikony przy zmianie profilu, ok. 8 KB): gdy bufor CDC się opróżni, od razu
  // obsługujemy USB (następny pakiet 64 B może już czekać) zamiast wracać do pętli. Odbiór i tak
  // ogranicza tempo pakietów USB (ok. 1 na ramkę 1 ms) – ważniejsze jest, że ekran nie jest
  // przerysowywany w trakcie serii (Display: kSettleMs).
  int budget = 4096;
#else
  int budget = 512;  // Pro Micro: ogranicz pracę w jednym obiegu pętli (skan klawiszy)
#endif
  while (budget-- > 0) {
    if (hal::serialAvailable() <= 0) {
#if defined(CHOCPILOT_BOARD_V0)
      hal::poll();
      if (hal::serialAvailable() <= 0) break;
#else
      break;
#endif
    }
    const int c = hal::serialRead();
    if (c < 0) break;
    if (c == '\r') continue;
    if (c == '\n') {
      if (overflow_) {
        overflow_ = false;
        sendError(false, 0, CHOCPILOT_F("line too long"));
      } else if (rxLen_ > 0) {
        rx_[rxLen_] = '\0';
        handler(rx_, rxLen_);
      }
      rxLen_ = 0;
      continue;
    }
    if (overflow_) continue;
    if (rxLen_ >= sizeof(rx_) - 1) {
      overflow_ = true;
      rxLen_ = 0;
      continue;
    }
    rx_[rxLen_++] = static_cast<char>(c);
  }
}

void Link::sendRaw(size_t len) {
  if (len == 0) return;
  // Bez otwartego portu (DTR) wiadomość jest pomijana.
  if (!hal::serialConnected()) return;
  tx_[len] = '\n';  // builder dostaje bufor o 1 bajt krótszy – jest miejsce na koniec linii
  hal::serialWrite(reinterpret_cast<const uint8_t*>(tx_), len + 1);
}

void Link::sendHello(bool online) {
  sendRaw(buildHello(tx_, kTxCap, board::kBoardId, CHOCPILOT_FW_VERSION, online, diag,
                     board::kHasEncoders, board::kLedCount, savers, saverCount, iconSize));
}

void Link::sendKey(uint8_t key, bool down, uint32_t t) {
  sendRaw(buildKey(tx_, kTxCap, key, down, t));
}

void Link::sendAck(int32_t id) { sendRaw(buildAck(tx_, kTxCap, id)); }

void Link::sendError(bool hasId, int32_t id, FlashText msg) {
  sendRaw(buildError(tx_, kTxCap, hasId, id, msg));
}

void Link::sendLog(FlashText level, FlashText msg) {
  if (!debug) return;
  sendRaw(buildLog(tx_, kTxCap, level, msg));
}

void Link::sendTest(bool active) { sendRaw(buildTest(tx_, kTxCap, active)); }

void Link::sendEncoder(uint8_t index, int16_t delta, uint32_t t) {
  sendRaw(buildEncoder(tx_, kTxCap, index, delta, t));
}

void Link::sendEncoderKey(uint8_t index, bool down, uint32_t t) {
  sendRaw(buildEncoderKey(tx_, kTxCap, index, down, t));
}

void Link::sendSlider(uint8_t value, uint32_t t) {
  sendRaw(buildSlider(tx_, kTxCap, value, t));
}

}  // namespace chocpilot

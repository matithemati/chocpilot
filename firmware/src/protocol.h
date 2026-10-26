// Łącze z aplikacją: odczyt linii JSON z USB CDC i nieblokujące wysyłanie wiadomości.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "protocol_codec.h"

namespace chocpilot {

class Link {
 public:
  using LineHandler = void (*)(const char* line, size_t len);

  void begin();
  // Czyta dostępne bajty; dla każdej pełnej linii woła handler.
  void poll(LineHandler handler);

  void sendHello(bool online);
  void sendKey(uint8_t key, bool down, uint32_t t);
  void sendEnc(int32_t steps, uint32_t t);
  void sendAck(int32_t id);
  void sendError(bool hasId, int32_t id, FlashText msg);
  void sendLog(FlashText level, FlashText msg);
  void sendTest(bool active);

  bool debug = false;
  const I2cDiag* diag = nullptr;  // dołączane do hello

 private:
  void sendRaw(size_t len);

  char rx_[kMaxLineLength];
  size_t rxLen_ = 0;
  bool overflow_ = false;
#if defined(CHOCPILOT_COMPACT)
  char tx_[216];  // najdłuższa wiadomość: hello z diagnostyką I²C (do 214 znaków)
#else
  char tx_[256];
#endif
};

}  // namespace chocpilot

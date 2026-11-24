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
  void sendAck(int32_t id);
  void sendError(bool hasId, int32_t id, FlashText msg);
  void sendLog(FlashText level, FlashText msg);
  void sendTest(bool active);
  // Pokrętła i suwak – aplikacja bez ich obsługi ignoruje te wiadomości.
  void sendEncoder(uint8_t index, int16_t delta, uint32_t t);
  void sendEncoderKey(uint8_t index, bool down, uint32_t t);
  void sendSlider(uint8_t value, uint32_t t);

  bool debug = false;
  const char* const* savers = nullptr;  // animacje wygaszacza (hello: savers)
  uint8_t saverCount = 0;
  uint8_t iconSize = 0;  // hello: icon (rozmiar ikon klawiszy; 0 = bez ikon)

 private:
  void sendRaw(size_t len);

  char rx_[kMaxLineLength];
  size_t rxLen_ = 0;
  bool overflow_ = false;
  // Najdłuższa wiadomość: hello z diagnostyką I²C (do 214 znaków) + znak końca linii.
  static constexpr size_t kTxCap = 216;
  char tx_[kTxCap + 1];
};

}  // namespace chocpilot

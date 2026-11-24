#include "leds.h"

#include <Arduino.h>

#include "boards/board.h"

namespace chocpilot {
namespace leds {

namespace {

// Bit WS2812 = 3 bity SPI przy 3 MHz (333 ns): 0 → 100 (333 ns stanu wysokiego),
// 1 → 110 (667 ns) – mieści się w tolerancjach WS2812B-V6 (T0H 220–380 ns, T1H 580–1000 ns).
// Linia między ramkami zostaje w stanie niskim (każdy kod kończy się zerem) = reset.
inline void spiWrite(uint8_t b) {
  while (!(SPI2->SR & SPI_SR_TXE)) {
  }
  *reinterpret_cast<volatile uint8_t*>(&SPI2->DR) = b;
}

// Jeden bajt koloru (MSB pierwszy) → 24 bity SPI.
void sendByte(uint8_t value) {
  uint32_t bits = 0;
  for (int8_t i = 7; i >= 0; --i) bits = (bits << 3) | ((value >> i) & 1 ? 0b110 : 0b100);
  spiWrite(static_cast<uint8_t>(bits >> 16));
  spiWrite(static_cast<uint8_t>(bits >> 8));
  spiWrite(static_cast<uint8_t>(bits));
}

}  // namespace

void begin() {
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_SPI2_CLK_ENABLE();
  GPIO_InitTypeDef io = {};
  io.Pin = digitalPinToBitMask(board::kLedData);
  io.Mode = GPIO_MODE_AF_PP;
  io.Pull = GPIO_PULLDOWN;
  io.Speed = GPIO_SPEED_FREQ_HIGH;
  io.Alternate = GPIO_AF0_SPI2;
  HAL_GPIO_Init(GPIOB, &io);

  // SPI2 nadawczy, master, tryb 0, 8 bitów, fPCLK/16 = 3 MHz.
  SPI2->CR1 = 0;
  SPI2->CR2 = SPI_CR2_DS_2 | SPI_CR2_DS_1 | SPI_CR2_DS_0 | SPI_CR2_FRXTH;
  SPI2->CR1 = SPI_CR1_BIDIMODE | SPI_CR1_BIDIOE | SPI_CR1_MSTR | SPI_CR1_SSM | SPI_CR1_SSI |
              SPI_CR1_BR_1 | SPI_CR1_BR_0;
  SPI2->CR1 |= SPI_CR1_SPE;
  fill({0, 0, 0});
}

void show(const Color* colors, uint8_t count) {
  // Przerwania (USB, SysTick) mogą wydłużyć przerwę między bitami – WS2812B-V6 toleruje to
  // aż do czasu resetu (≥ 280 µs), więc transmisja nie musi blokować przerwań.
  for (uint8_t i = 0; i < count; ++i) {
    sendByte(colors[i].g);  // kolejność GRB
    sendByte(colors[i].r);
    sendByte(colors[i].b);
  }
  while (SPI2->SR & SPI_SR_BSY) {
  }
}

void fill(Color color) {
  Color all[board::kLedCount];
  for (Color& c : all) c = color;
  show(all, board::kLedCount);
}

}  // namespace leds
}  // namespace chocpilot

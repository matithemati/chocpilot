# Okablowanie ChocPilot

## Matryca 3×3 (COL2ROW)

Każdy przełącznik MX ma szeregowo diodę **1N4148**. Układ **COL2ROW**: prąd płynie od
kolumny przez przełącznik i diodę do wiersza – **katoda diody (pasek) w stronę wiersza**.

```
           COL1 (in, pull-up)   COL2               COL3
             │                   │                  │
ROW1 ──┬─────┼──────────┬────────┼─────────┬────────┼──
 (out) │     │          │        │         │        │
       ▼ D1  └─[K1]─┐   ▼ D2     └─[K2]─┐  ▼ D3     └─[K3]─┐
       └────────────┘   └───────────────┘  └───────────────┘
   (analogicznie ROW2: K4 K5 K6, ROW3: K7 K8 K9)
```

Schemat pojedynczego klawisza:

```
COLn ───[ przełącznik ]───|>|─── ROWm
                          A  K   (katoda/pasek → wiersz)
```

Skanowanie: aktywny wiersz = wyjście **LOW**, pozostałe wiersze = wejście (wysoka impedancja).
Kolumny = wejścia z **INPUT_PULLUP**. Wciśnięty klawisz w aktywnym wierszu ściąga kolumnę do LOW.
Dzięki diodom możliwe jest pełne NKRO (dowolna kombinacja klawiszy bez „duchów”).

Numeracja: `Kn`, n = (wiersz − 1)·3 + kolumna.

| | COL1 | COL2 | COL3 |
|---|---|---|---|
| **ROW1** | K1 | K2 | K3 |
| **ROW2** | K4 | K5 | K6 |
| **ROW3** | K7 | K8 | K9 |

Przycisk enkodera = **klawisz 10** (poza matrycą).

## Enkoder EC11 z przyciskiem

```
EC11 (widok od strony nóżek)
  A ─── GPIO enc A (INPUT_PULLUP)
  C ─── GND
  B ─── GPIO enc B (INPUT_PULLUP)
  SW1 ── GPIO enc SW (INPUT_PULLUP)
  SW2 ── GND
```
Opcjonalnie: kondensatory 10 nF z A i B do GND poprawiają odporność na drgania
(firmware i tak filtruje je tablicą stanów kodu Graya).

## OLED 0.91" SSD1306 128×32 (I²C)

| OLED | Połączenie |
|---|---|
| GND | GND |
| VCC | **3,3 V** (Pro Micro: pin VCC – 5 V w wersji 5 V, patrz uwagi) |
| SCL | SCL płytki |
| SDA | SDA płytki |

Adres domyślny **0x3C** (zmiana: `CHOCPILOT_OLED_ADDR` w `firmware/src/config.h` lub ustawienie `oled_addr`).
Moduły OLED mają zwykle własne rezystory podciągające 4,7–10 kΩ.

## Mapa pinów

| Sygnał | KB2040 (GPIO) | Pro Micro (pin Arduino / port) | XIAO ESP32-S3 (pin / GPIO) |
|---|---|---|---|
| Wiersz 1 | 9 (D9) | 9 / PB5 | D8 / 7 |
| Wiersz 2 | 8 (D8) | 8 / PB4 | D9 / 8 |
| Wiersz 3 | 7 (D7) | 7 / PE6 | D10 / 9 |
| Kolumna 1 | 6 (D6) | 6 / PD7 | D2 / 3 (strapping) |
| Kolumna 2 | 5 (D5) | 5 / PC6 | D6 / 43 (UART0 TX) |
| Kolumna 3 | 4 (D4) | 4 / PD4 | D7 / 44 (UART0 RX) |
| Enkoder A | 19 (MOSI) | 16 (MOSI) / PB2, PCINT2 | D0 / 1 |
| Enkoder B | 20 (MISO) | 14 (MISO) / PB3, PCINT3 | D1 / 2 |
| Enkoder SW | 18 (SCK) | 15 (SCK) / PB1 | D3 / 4 |
| OLED SDA | 3 (D3, programowe I²C) | 3 / PD0 (programowe I²C) | D4 / 5 |
| OLED SCL | 2 (D2, programowe I²C) | 2 / PD1 (programowe I²C) | D5 / 6 |
| Dioda statusu | NeoPixel GPIO17 (wbudowany) | brak | LED użytkownika GPIO21 (wbudowana, aktywna stanem niskim) |

Plik źródłowy prawdy: `firmware/src/boards/board_kb2040.h`, `board_promicro.h` i
`board_xiao_esp32s3.h`.

KB2040 i Pro Micro mają ten sam rozkład wyprowadzeń, więc płytka PCB (MacroPad_Y7, footprint
Pro Micro) pasuje do obu. Kolumna „Pro Micro” to piny w **tych samych miejscach** co piny KB2040:

```
           KB2040 / Pro Micro (widok od góry, USB u góry)
 TX  GPIO0 / D1 (TXO)  ●   ● RAW
 RX  GPIO1 / D0 (RXI)  ●   ● GND
               GND     ●   ● RST
               GND     ●   ● 3V / VCC
 D2  GPIO2 / 2  (SDA)  ●   ● A3
 D3  GPIO3 / 3  (SCL)  ●   ● A2
 D4  GPIO4 / 4         ●   ● A1
 D5  GPIO5 / 5         ●   ● A0
 D6  GPIO6 / 6         ●   ● SCK  GPIO18 / 15
 D7  GPIO7 / 7         ●   ● MISO GPIO20 / 14
 D8  GPIO8 / 8         ●   ● MOSI GPIO19 / 16
 D9  GPIO9 / 9         ●   ● D10  GPIO10 / 10
```

### Uwagi – KB2040

- OLED: SDA = GPIO3, SCL = GPIO2 – tak poprowadzono ścieżki na PCB. Sprzętowe I2C1 RP2040 ma te piny
  odwrotnie (GPIO2 = SDA, GPIO3 = SCL), więc firmware obsługuje ekran **programowym I²C** (U8g2 SW_I2C,
  `kOledSoftI2c` w `board_kb2040.h`). Przy nowej płytce z SDA na GPIO2 i SCL na GPIO3 można wrócić do
  sprzętowego I²C (`kOledSoftI2c = false`).
- GPIO0/1 (D0/D1, UART0) są wolne.
- NeoPixel na GPIO17 jest wbudowany na płytce. Jasność ograniczona programowo.
- Złącze STEMMA QT (GPIO12/13) nie jest używane.

### Uwagi – Pro Micro (ATmega32U4)

- **OLED – programowe I²C.** Ścieżka OLED_SDA biegnie do pinu, który na KB2040 jest GPIO3, a
  OLED_SCL do GPIO2. Na Pro Micro w tych miejscach są **3 (PD0)** i **2 (PD1)**. Sprzętowy TWI
  ATmega32U4 ma piny na stałe: **SDA = 2 (PD1), SCL = 3 (PD0)** – czyli dokładnie odwrotnie niż
  na PCB (ta sama sytuacja co na RP2040), a TWI nie da się przemapować. Dlatego firmware obsługuje
  ekran programowym I²C (`kOledSoftI2c = true` w `board_promicro.h`, wersja kompaktowa nie ma
  w ogóle kodu sprzętowego I²C). Przy starcie firmware sam sprawdza też wariant z zamienionymi
  liniami (`swapped` w `hello`). Na nowej płytce z SDA na pinie 2 i SCL na 3 sprzętowy TWI
  zadziałałby, ale nie jest potrzebny (ekran 128×32 i tak mieści się w czasie).
- **Enkoder – przerwanie pin change.** Piny 14/16 (PB3/PB2) nie mają przerwań INTx
  (`attachInterrupt()` na nich nic nie robi), więc firmware używa przerwania **PCINT0**
  (`hal::encoderIrqBegin` w `hal_promicro.cpp`).
- **5 V czy 3,3 V.** Pro Micro 5 V/16 MHz ma logikę **5 V**, a pin VCC (w miejscu „3V” KB2040)
  podaje **5 V** – OLED dostaje wtedy 5 V zasilania i 5 V na liniach I²C (podciąganie
  wewnętrzne do 5 V + rezystory modułu do jego VCC). Typowe moduły 0.91" mają własny stabilizator
  i działają z 5 V, ale sam SSD1306 jest układem 3,3 V – jeśli moduł nie ma stabilizatora albo
  chcesz trzymać się specyfikacji, użyj **Pro Micro 3,3 V/8 MHz** (`pio run -e promicro_3v3`).
  Matryca i enkoder są pasywne – działają z oboma wersjami.
- **Dioda statusu**: brak osobnej diody; RX/TX LED na płytce steruje rdzeń USB (miganie przy
  transmisji). Stan online/offline pokazuje ekran.
- Wolne piny: 0/1 (UART), A0–A3, 10.

### Uwagi – XIAO ESP32-S3

- Zajęte są wszystkie 11 pinów D0–D10.
- **GPIO3 (D2)** to pin strapping (wybór źródła JTAG) – wejście z pull-upem jest bezpieczne.
- **GPIO43/44 (D6/D7)** to domyślnie UART0. Firmware nie inicjalizuje `Serial0`; po starcie są
  zwykłymi wejściami kolumn. Bootloader ROM wypisuje komunikaty na GPIO43 przy starcie – diody
  matrycy i wysoka impedancja wierszy sprawiają, że jest to nieszkodliwe.
- Wbudowana pomarańczowa dioda LED użytkownika na GPIO21 świeci przy stanie **niskim**.
- Komunikacja z PC i HID idą przez natywne USB (TinyUSB, `ARDUINO_USB_MODE=0`).

## Zasilanie

Całość zasilana z USB-C płytki. OLED wyłącznie z 3,3 V. Nie podłączaj 5 V do żadnego GPIO.

Wyjątek: Pro Micro 5 V – jego GPIO i pin VCC pracują z 5 V (patrz uwagi wyżej). Moduł OLED
musi wtedy tolerować 5 V albo użyj wersji 3,3 V/8 MHz.

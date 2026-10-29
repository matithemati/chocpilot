# ChocPilot v2 – mapa pinów

Źródło prawdy: `tools/design.py` (schemat i płytka są z niego generowane). Współrzędne
w mm od lewego górnego rogu płytki (widok od góry).

## MCU STM32F072CBT6 (U1, LQFP-48)

| Pin | Port | Sieć | Funkcja / uwagi |
|---|---|---|---|
| 1 | VBAT | +3V3 | C8 100 nF |
| 2–4 | PC13–PC15 | – | wolne |
| 5 | PF0 | OSC_IN | kwarc Y1 8 MHz (opcja) |
| 6 | PF1 | OSC_OUT | kwarc Y1 |
| 7 | NRST | NRST | SW1 RESET, C12 100 nF, J3.4 |
| 8 / 9 | VSSA / VDDA | GND / +3V3 | C10 100 nF + C11 1 µF |
| 10 | PA0 | ENC1_A | TIM2_CH1 (AF2) – tryb enkodera |
| 11 | PA1 | ENC1_B | TIM2_CH2 (AF2) |
| 12 | PA2 | ENC1_SW | przycisk enkodera 1 |
| 13 | PA3 | ENC2_SW | przycisk enkodera 2 |
| 14 | PA4 | K5 | klawisz S5 |
| 15 | PA5 | K6 | klawisz S6 |
| 16 | PA6 | ENC2_A | TIM3_CH1 (AF1) – tryb enkodera |
| 17 | PA7 | ENC2_B | TIM3_CH2 (AF1) |
| 18 | PB0 | – | wolne (ADC_IN8) |
| 19 | PB1 | SLIDER | ADC_IN9, filtr C16 100 nF |
| 20 | PB2 | K7 | klawisz S7 |
| 21 | PB10 | K8 | klawisz S8 |
| 22 | PB11 | – | wolne |
| 23 / 24 | VSS / VDD | GND / +3V3 | C6 100 nF |
| 25–27 | PB12–PB14 | – | wolne |
| 28 | PB15 | LED_DATA_3V3 | SPI2_MOSI (AF0) lub TIM15_CH2 (AF1) → U4 → L1 |
| 29–31 | PA8–PA10 | – | wolne (PA9/PA10 = USART1, używany też przez bootloader) |
| 32 | PA11 | USB_DN | USB D− (przez U3) |
| 33 | PA12 | USB_DP | USB D+ (przez U3); podciąganie 1,5 k wewnątrz MCU |
| 34 | PA13 | SWDIO | J3.2 |
| 35 / 36 | VSS / VDDIO2 | GND / +3V3 | C7 100 nF |
| 37 | PA14 | SWCLK | J3.3 |
| 38, 39 | PA15, PB3 | – | wolne |
| 40 | PB4 | K4 | klawisz S4 |
| 41 | PB5 | K3 | klawisz S3 |
| 42 | PB6 | OLED_SCL | I2C1_SCL (AF1), R4 4,7 k → 3V3 |
| 43 | PB7 | OLED_SDA | I2C1_SDA (AF1), R5 4,7 k → 3V3 |
| 44 | BOOT0 | BOOT0 | R3 10 k → GND, SW2 BOOT0 → 3V3 |
| 45 | PB8 | K2 | klawisz S2 |
| 46 | PB9 | K1 | klawisz S1 |
| 47 / 48 | VSS / VDD | GND / +3V3 | C5 100 nF, C9 4,7 µF |

Wszystkie wejścia klawiszy, enkoderów i przycisków: **aktywne niskim, z wewnętrznym
podciąganiem** (INPUT_PULLUP). Brak matrycy i diod – każdy klawisz ma własny pin.
PB6/PB7 są tolerancyjne na 5 V (FT), więc moduł OLED może podciągać I²C do swojego VCC.

## Klawisze (Kailh Choc V2, gniazda hotswap)

| Klawisz | Oznaczenie | Pin MCU | Środek (x, y) |
|---|---|---|---|
| K1 | S1 | PB9 | 26,43; 12,5 |
| K2 | S2 | PB8 | 45,48; 12,5 |
| K3 | S3 | PB5 | 64,53; 12,5 |
| K4 | S4 | PB4 | 83,58; 12,5 |
| K5 | S5 | PA4 | 26,43; 80,5 |
| K6 | S6 | PA5 | 45,48; 80,5 |
| K7 | S7 | PB2 | 64,53; 80,5 |
| K8 | S8 | PB10 | 83,58; 80,5 |

Raster 19,05 mm, rzędy 68 mm od siebie, ekran dokładnie pośrodku (55; 46,5). Numeracja
`Kn` jak w v1 (firmware, protokół, aplikacja). Pad 1 gniazda = sygnał, pad 2 = GND.

## Złącza

**J1 – USB-C (GCT USB4105-GF-A)**, górna krawędź, oś x = 103,5. CC1/CC2 → 5,1 kΩ do GND
(urządzenie, do 500 mA z dowolnego hosta USB-C). VBUS → bezpiecznik F1 0,5 A → +5V.

**J2 – moduł OLED 2,42" I²C** (gniazdo 1×4 2,54 mm, pin 1 z lewej, środek złącza
x = 55, y = 24,45 – pod pinami u góry modułu):

| J2 | Sygnał | Uwagi |
|---|---|---|
| 1 | GND | |
| 2 | OLED_VCC | zworka JP1: 1–2 = 3,3 V (fabrycznie), 2–3 = 5 V |
| 3 | OLED_SCL | PB6 |
| 4 | OLED_SDA | PB7 |

Kolejność GND, VCC, SCL, SDA odpowiada typowemu nadrukowi modułów 2,42" – **sprawdź swój
moduł**. Jeśli ma inną kolejność lub raster, połącz go przewodami (jak w v1).

**J3 – SWD (opcjonalne, 1×5 2,54 mm):** 1 = +3V3, 2 = SWDIO, 3 = SWCLK, 4 = NRST, 5 = GND
(opisane na sitodruku). Do ST-Link / programatora SWD; zwykłe wgrywanie idzie przez USB DFU.

## Enkodery i suwak

| Element | Piny | Połączenie |
|---|---|---|
| ENC1 (oś 12,5; 34,5) | A, B, C | PA0, PA1, GND |
| | S1, S2 | PA2, GND |
| ENC2 (oś 12,5; 58,5) | A, B, C | PA6, PA7, GND |
| | S1, S2 | PA3, GND |
| RV1 suwak (oś x = 97,25, środek skoku y = 46,5) | 1 (dół) | GND |
| | 2 (suwak) | PB1 (ADC) |
| | 3 (góra) | +3V3 – suwak w górę = większa wartość |

Uchwyty enkoderów i suwaka (MP) są na GND.

## LED WS2812B (L1–L12, spód płytki, świecą w blat)

Dane: PB15 → U4 (74AHCT1G125, 3,3 → 5 V) → R6 330 Ω → L1 DIN → … → L12 DOUT (wolny).
Kolejność w łańcuchu (widok od góry):

| LED | Położenie | LED | Położenie |
|---|---|---|---|
| L1 | prawy bok, góra (104,5; 28) | L7 | lewy bok, dół (6; 72) |
| L2 | prawy bok, dół (104,5; 65) | L8 | lewy bok, góra (6; 21) |
| L3–L6 | dolna krawędź, od prawej (pod K8…K5) | L9–L12 | górna krawędź, od lewej (nad K1…K4) |

Zasilanie +5V (z USB po bezpieczniku), 100 nF przy każdej diodzie, C18 10 µF na wejściu
łańcucha.

## Przyciski (spód płytki)

| Przycisk | Położenie | Działanie |
|---|---|---|
| SW1 RESET | (46; 60) | NRST → GND |
| SW2 BOOT0 | (58; 60) | BOOT0 → 3,3 V; trzymaj i naciśnij RESET → bootloader USB DFU |

# Okablowanie ChocPilot

Źródło prawdy: schemat płytki [schematic.png](schematic.png) i mapa pinów
`firmware/src/boards/board.h`.

## Matryca 2×4 (COL2ROW, Kailh Choc)

Każdy przełącznik Kailh Choc (S1–S8) ma szeregowo diodę **1N4148** (D1–D8). Układ **COL2ROW**:
prąd płynie od kolumny przez przełącznik i diodę do wiersza – **katoda diody (pasek) w stronę
wiersza**.

```
          Column 0      Column 1      Column 2      Column 3
             │             │             │             │
             ├─[S1]─|>|─┐  ├─[S2]─|>|─┐  ├─[S3]─|>|─┐  ├─[S4]─|>|─┐
Row 0 ───────┼──────────┴──┼──────────┴──┼──────────┴──┼──────────┴──
             │             │             │             │
             └─[S5]─|>|─┐  └─[S6]─|>|─┐  └─[S7]─|>|─┐  └─[S8]─|>|─┐
Row 1 ──────────────────┴─────────────┴─────────────┴─────────────┴──
```

Skanowanie: aktywny wiersz = wyjście **LOW**, drugi wiersz = wejście (wysoka impedancja).
Kolumny = wejścia z **INPUT_PULLUP**. Wciśnięty klawisz w aktywnym wierszu ściąga kolumnę do LOW.
Dzięki diodom możliwe jest pełne NKRO (dowolna kombinacja klawiszy bez „duchów”).

Numeracja klawiszy (tak samo w firmware, protokole i aplikacji): `Kn`, n = wiersz·4 + kolumna + 1.

| | Column 0 | Column 1 | Column 2 | Column 3 |
|---|---|---|---|---|
| **Row 0** | K1 (S1) | K2 (S2) | K3 (S3) | K4 (S4) |
| **Row 1** | K5 (S5) | K6 (S6) | K7 (S7) | K8 (S8) |

Tryb testu sprzętu: **K1 + K4** (skrajne klawisze górnego rzędu) trzymane 3 s zaraz po
podłączeniu.

## Mapa pinów (Arduino Pro Micro, U1)

| Sygnał | Nóżka U1 | Pin Arduino | Port | Uwagi |
|---|---|---|---|---|
| OLED_SDA | 5 | 2 | PD1 | sprzętowe SDA (TWI) |
| OLED_SCL | 6 | 3 | PD0 | sprzętowe SCL (TWI) |
| Row 0 | 7 | 4 | PD4 | wyjście LOW / wejście |
| Column 3 | 8 | 5 | PC6 | INPUT_PULLUP |
| Column 2 | 9 | 6 | PD7 | INPUT_PULLUP |
| Column 1 | 10 | 7 | PE6 | INPUT_PULLUP |
| Column 0 | 11 | 8 | PB4 | INPUT_PULLUP |
| Row 1 | 12 | 9 | PB5 | wyjście LOW / wejście |
| GND | 23 | – | – | GND OLED |
| VCC | 21 | – | – | +5 V dla OLED (wersja 5 V) |

Wolne: 0/1 (UART TX/RX), A0–A3, 10, 14, 15, 16.

## OLED 2,42" SSD1309 128×64 (I²C), złącze J1

| J1 | Sygnał | Pro Micro |
|---|---|---|
| 1 | GND | GND |
| 2 | +5 V | VCC (nóżka 21) |
| 3 | OLED_SDA | 2 (PD1) |
| 4 | OLED_SCL | 3 (PD0) |

- Adres domyślny **0x3C** (zmiana: `CHOCPILOT_OLED_ADDR` w `firmware/src/config.h` lub ustawienie
  `oled_addr`); firmware przy starcie sam wybiera 0x3C albo 0x3D.
- **Kolejność wyprowadzeń modułu.** Moduły 2,42" mają często kolejność **GND, VCC, SCL, SDA** –
  wtedy na J1 linie byłyby zamienione. Firmware to wykryje: gdy sprzętowy TWI nic nie znajdzie,
  sprawdza magistralę programowo z zamienionymi liniami i działa dalej w programowym I²C
  (`swapped` w `hello`, ostrzeżenie w dzienniku aplikacji). Działa, ale wolniej – lepiej
  dopasować kolejność na płytce.
- **I²C zamiast SPI.** Wiele modułów 2,42" (7 pinów) jest fabrycznie ustawionych na SPI;
  tryb I²C wybiera się zworkami/rezystorami na odwrocie – według opisu nadrukowanego na
  module lub karty sprzedawcy (RES trzeba wtedy podciągnąć do VCC). Moduł 4-pinowy jest od razu
  w I²C.
- **Sterownik.** Firmware używa `u8x8_d_ssd1309_128x64_noname2` (najczęstsze moduły 2,42").
  Jeśli obraz jest przesunięty o 2 kolumny albo pojawiają się śmieci przy krawędzi, zmień na
  `noname0` w `firmware/src/mini_gfx.cpp`.
- **Podciąganie.** Moduły mają zwykle własne rezystory 4,7–10 kΩ; firmware dodatkowo włącza
  słabe wewnętrzne podciąganie na SDA/SCL.

## Zasilanie: Pro Micro 5 V czy 3,3 V

Całość zasilana z USB płytki Pro Micro. Na schemacie OLED dostaje **+5 V** z pinu VCC.

- **Pro Micro 5 V/16 MHz** (`pio run -e promicro`): GPIO pracują z logiką **5 V**, a linie I²C
  są podciągnięte do 5 V. Moduły 2,42" mają zwykle stabilizator 3,3 V i akceptują 5 V na
  zasilaniu i liniach – sprawdź opis modułu. SSD1309 sam w sobie jest układem 3,3 V.
- **Pro Micro 3,3 V/8 MHz** (`pio run -e promicro_3v3`): VCC = 3,3 V, wszystko w specyfikacji
  SSD1309; I²C działa z ok. 220 kHz zamiast 400 kHz.

Matryca jest pasywna – działa z oboma wersjami.

## Pro Micro – pozostałe uwagi

- Dioda statusu: brak osobnej diody; RX/TX LED na płytce steruje rdzeń USB (miganie przy
  transmisji). Stan online/offline pokazuje ekran.
- Wgrywanie firmware: bootloader Caterina – patrz README („Wgrywanie”).

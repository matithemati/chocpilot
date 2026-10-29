# ChocPilot v2 – notatki projektowe

## Układ płytki

- 110 × 93 mm, narożniki R2, 2 warstwy, wylewki GND na obu (trasy GND poprowadzone także
  ścieżkami – wylewka nie jest jedynym połączeniem).
- Oś symetrii x = 55: klawisze w rastrze 19,05 mm, rzędy y = 12,5 i 80,5 (68 mm od siebie),
  ekran 70,10 × 48,10 mm wyśrodkowany w (55; 46,5) – ten sam odstęp od obu rzędów.
- Lewa kolumna: enkodery (osie (12,5; 34,5) i (12,5; 58,5)). Prawa: suwak PTA4543, oś dźwigni
  x ≈ 97,25, skok 45 mm wokół y = 46,5. Korpusy enkoderów i suwaka nie wchodzą pod moduł OLED.
- Gniazda hotswap zawsze od strony ekranu (górny rząd obrócony o 180°), dzięki temu przy
  krawędziach zostało miejsce na diody LED.
- Elektronika (MCU, LDO, kondensatory) jest na wierzchu **pod modułem OLED**. Najwyższe
  elementy pod modułem: kwarc 1,3 mm, gniazdo J2. Listwa J3 (SWD) nie jest lutowana na stałe.
- Spód: diody LED na obrzeżu, gniazda hotswap, przyciski RESET/BOOT0 (otwory w dnie obudowy).
- Otwory M3: (6,5; 7), (106,5; 21), (6; 86,5), (104,5; 86,5).

## Zasilanie

| Szyna | Źródło | Odbiorcy | Uwagi |
|---|---|---|---|
| VBUS | USB-C | F1, U3 | ESD USBLC6 odnosi się do VBUS |
| +5V | po F1 (PTC 0,5 A / zadziałanie 1 A) | U2, U4, 12 × LED, JP1 | ścieżki 0,6 mm |
| +3V3 | TPS73633 (400 mA) | MCU, OLED (JP1 1–2), suwak, pull-upy | |

Budżet: MCU ~25 mA, OLED 2,42" ~20–80 mA (zależnie od zapalonych pikseli), LED WS2812B do
~36 mA każda przy pełnej bieli → 12 × 36 ≈ 430 mA. Razem ponad 500 mA dostępne z portu USB 2.0.
**Firmware musi ograniczać jasność LED** (np. suma ≤ 300 mA, ok. 70 % bieli) – bezpiecznik
F1 i tak zadziała przy przeciążeniu, ale port może się wcześniej wyłączyć.

## Sygnały

- **USB:** D+/D− przez USBLC6 (U3), ~55 mm od złącza do MCU, bez dopasowania długości – przy 12 Mb/s
  zbędne. F072 ma wewnętrzny pull-up 1,5 kΩ na D+. CC1/CC2: 5,1 kΩ do GND.
- **Klawisze, enkodery:** bezpośrednio do pinów, wewnętrzne podciąganie. Brak matrycy i diod –
  pełne NKRO bez skanowania. Brak sprzętowego filtrowania – debouncing w firmware
  (timery w trybie enkodera mają filtr wejściowy ICxF).
- **Suwak:** dzielnik 3,3 V → ADC PB1, filtr 100 nF. TME ma Bourns PTA45 tylko w charakterystyce
  logarytmicznej (A, ~15 % w połowie skoku) – firmware powinien ją linearyzować tablicą.
  Wersja liniowa PTA4543-2015DPB103 pasuje do tego samego footprintu.
- **LED:** 3,3 V z MCU nie spełnia V_IH WS2812B przy 5 V (0,7 × VDD = 3,5 V), stąd
  74AHCT1G125 (wejście TTL) zasilany z +5V i 330 Ω szeregowo przy źródle.
- **OLED:** I²C1 (PB6/PB7), pull-upy 4,7 kΩ do 3,3 V na płytce. Moduł zasilany 3,3 V (JP1);
  jeśli wymaga 5 V – przełącz JP1 na 2–3 (PB6/PB7 tolerują 5 V).
- **Programowanie:** bootloader DFU w ROM (BOOT0 + RESET), zapasowo SWD (J3).

## Elementy THT (nie ma ich w SMD)

| Element | Dlaczego THT | Wybór |
|---|---|---|
| Przełączniki Choc V2 | piny przełącznika | gniazda hotswap Kailh **SMD** od spodu – przełącznik wciskany |
| EC11 | tylko THT | Alps EC11E15244G1 (z przyciskiem) |
| Suwak | tylko THT | Bourns PTA4543 (45 mm), footprint KiCad |
| J2 OLED | złącze modułu z listwą THT, obciążenie mechaniczne | gniazdo 1×4 2,54 mm |
| J3 SWD | opcja serwisowa | pady pod listwę 1×5 |

USB-C (USB4105) jest SMD z kołkami THT obudowy – najtrudniejszy element do lutowania
(raster 0,5 mm), ale jedyny rząd padów, bez drugiego rzędu pod spodem złącza.

## Footprint Kailh Choc V1/V2 hotswap

`chocpilot.pretty/SW_Kailh_Choc_V1V2_Hotswap_1u` – geometria wg biblioteki kiswitch
(`SW_Hotswap_Kailh_Choc_V1V2_1.00u`, zgodna z footprintem ergogen): otwór środkowy Ø5,05
(Choc V2; V1 Ø3,45 też wchodzi), kołki V1 Ø1,9 na ±5,5 mm, kołek V2 Ø1,6 w (−5; 5,15),
piny przełącznika Ø3,05 w (0; −5,9) i (5; −3,8), pady gniazda 2,55 × 2,5 mm w (−3,5; −6)
i (8,5; −3,8) na B.Cu. Choc V2 ma piny w tych samych miejscach co V1, więc pasuje to samo
gniazdo CPG135001S30. Pasują keycapy MX (trzpień V2).

## Do sprawdzenia przed zamówieniem

1. **Gniazdo Choc:** wydrukuj `img/pcb_bottom.png` lub warstwę B.Cu 1:1 i przyłóż gniazdo
   oraz przełącznik V2 (otwory, pady). Geometria pochodzi z biblioteki, nie z pomiaru.
2. **Moduł OLED:** położenie i raster pinów (zakładam 4 piny 2,54 mm, środek górnej krawędzi,
   ~2 mm od niej, kolejność GND, VCC, SCL, SDA). Przy innym module – przewody do J2.
3. **Wysokości w obudowie:** moduł na gnieździe J2 stoi ok. 8–11 mm nad płytką; enkoder
   EC11 H20 i suwak (6,5 mm korpusu + dźwignia) – dobierz do nich obudowę.
4. **Nakładka suwaka:** dźwignia PTA porusza się w y ≈ 24–69; nakładka szersza niż ok. 8 mm
   na końcach skoku zbliża się do keycapów K4/K8.
5. Numery TME oznaczone w BOM „do potwierdzenia” (zwykłe 0805).

## Co będzie potrzebne w firmware i aplikacji (port – osobny krok)

- **Platforma:** STM32F072CB (PlatformIO `ststm32`, Arduino STM32duino – wariant generic F072CB,
  USB CDC z `USBD_USE_CDC`) albo QMK/ChibiOS. Wgrywanie: `dfu-util -a 0 -s 0x08000000:leave`.
  Dobrze dodać komendę protokołu „skok do bootloadera”, żeby nie trzeba było przycisków.
- **Klawisze:** odczyt bezpośredni 8 pinów (zamiast matrycy 2×4 z `matrix.cpp`), ta sama
  numeracja K1–K8; kombinacja testu K1 + K4 bez zmian.
- **Enkodery:** TIM2 (PA0/PA1) i TIM3 (PA6/PA7) w trybie enkodera lub przerwania; przyciski
  PA2, PA3. Nowe zdarzenia w protokole (obrót ±n, wciśnięcie).
- **Suwak:** ADC PB1, uśrednianie + histereza, linearyzacja charakterystyki A, zdarzenie
  „wartość 0–100 %” wysyłane przy zmianie.
- **LED:** 12 × WS2812B na PB15 – SPI2 MOSI z kodowaniem bitów (~2,4–3 MHz) lub TIM15_CH2 + DMA;
  limit jasności; efekty sterowane z aplikacji.
- **OLED:** ten sam SSD1309 128×64 na I2C1 (u8g2 działa na STM32), 400 kHz.
- **Protokół / aplikacja:** `hello` powinno raportować nowe możliwości (enkodery, suwak, LED),
  aplikacja – akcje dla obrotu/wciśnięcia enkoderów, suwaka (np. głośność) i ustawienia LED.
  `docs/PROTOCOL.md` do rozszerzenia.
- **Obudowa (`case/`):** nowy obrys 110 × 93 mm i otwory M3 jak wyżej, otwory na osie enkoderów,
  szczelina suwaka, USB-C w prawym górnym rogu górnej krawędzi, dwa otwory w dnie na RESET/BOOT0,
  przezroczysty / otwarty dolny obrzeże dla podświetlenia.

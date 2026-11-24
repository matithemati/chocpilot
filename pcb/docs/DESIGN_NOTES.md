# ChocPilot – notatki projektowe

## Układ płytki

- 114 × 93 mm, narożniki R2, 2 warstwy, wylewki GND na obu (trasy GND poprowadzone także
  ścieżkami – wylewka nie jest jedynym połączeniem).
- Oś klawiszy i ekranu x = 55: klawisze w rastrze 19,05 mm, rzędy y = 12,5 i 80,5 (68 mm od
  siebie), ekran wyśrodkowany w (55; 46,5) – ten sam odstęp od obu rzędów. Płytka jest 4 mm
  szersza w prawo niż oś × 2, żeby keycapy K4/K8 (do x ≈ 92,6) miały ok. 4,7 mm odstępu od
  suwaka i jego nakładki (od x ≈ 97,25).
- Lewa kolumna: enkodery (osie (12,5; 34,5) i (12,5; 58,5)). Prawa: suwak ALPS RS45111, oś dźwigni
  x ≈ 101,25, skok 45 mm wokół y = 46,5. Korpusy enkoderów i suwaka nie wchodzą pod ekran.
- Piny przełączników zawsze od strony ekranu (górny rząd obrócony o 180°), dzięki temu przy
  krawędziach zostało miejsce na diody LED.
- Elektronika (MCU, LDO, kondensatory) jest na wierzchu **pod ekranem** (ekran 2" przykręcony do obudowy nad płytką). Najwyższe
  elementy pod ekranem: kwarc 1,3 mm, listwa J2. Listwa J3 (SWD) nie jest lutowana na stałe.
- Spód: diody LED na obrzeżu, diody matrycy, przyciski RESET/BOOT0 (otwory w dnie obudowy).
- Otwory M3: (6,5; 7), (110,5; 21), (6; 86,5), (108,5; 86,5).

## Zasilanie

| Szyna | Źródło | Odbiorcy | Uwagi |
|---|---|---|---|
| VBUS | USB-C | F1, U3 | ESD USBLC6 odnosi się do VBUS |
| +5V | po F1 (PTC 0,5 A / zadziałanie 1 A) | U2, U4, 12 × LED | ścieżki 0,6 mm |
| +3V3 | TPS73633 (400 mA) | MCU, ekran LCD, suwak | |

Budżet: MCU ~25 mA, ekran LCD 2" ~40–60 mA (podświetlenie, regulowane PWM), LED WS2812B do
~36 mA każda przy pełnej bieli → 12 × 36 ≈ 430 mA. Razem ponad 500 mA dostępne z portu USB 2.0.
Firmware ogranicza jasność LED do ok. 1/3 pełnej mocy (ok. 230 mA przy bieli, `leds.cpp`) –
bezpiecznik F1 i tak zadziała przy przeciążeniu, ale port mógłby się wcześniej wyłączyć.

## Sygnały

- **USB:** D+/D− przez USBLC6 (U3), ~55 mm od złącza do MCU, bez dopasowania długości – przy 12 Mb/s
  zbędne. F072 ma wewnętrzny pull-up 1,5 kΩ na D+. CC1/CC2: 5,1 kΩ do GND.
- **Klawisze:** matryca 2×4 COL2ROW z diodą 1N4148W przy każdym klawiszu (jak v1, NKRO).
  Kolumny = pary sąsiednich klawiszy w rzędzie (PB9, PB7, PA4, PB2), wiersze = klawisze
  wewnętrzne (PB0) i zewnętrzne (PB11) – przez środek płytki idą tylko 2 sieci, a piny
  wierszy są z boku MCU, żeby nie zasłaniały wyprowadzeń. Mapa klawiszy: PINOUT.md.
- **Enkodery:** bezpośrednio do pinów, wewnętrzne podciąganie. Brak sprzętowego filtrowania –
  debouncing w firmware (timery w trybie enkodera mają filtr wejściowy ICxF).
- **Suwak:** ALPS RS45111A900F (45 mm, 10 kΩ liniowy), dzielnik 3,3 V → ADC PB1, filtr 100 nF.
  Footprint własny (`chocpilot.pretty/Potentiometer_Alps_RS45111_Slide_45mm`) wg rysunku ALPS.
- **LED:** 3,3 V z MCU nie spełnia V_IH WS2812B przy 5 V (0,7 × VDD = 3,5 V), stąd
  74AHCT1G125 (wejście TTL) zasilany z +5V i 330 Ω szeregowo przy źródle.
- **Ekran:** Waveshare 2inch LCD Module (TME WSH-17344: ST7789V, 240×320 IPS, 58 × 35 mm)
  przykręcony do obudowy, dołączonym kablem PH2.0 do J2 (1:1). Ten sam układ 8 pinów mają
  inne moduły Waveshare (np. 2,4" WSH-18366), więc pasują bez zmian płytki.
  SPI1 (PB3 SCK, PB5 MOSI), tryb 3, 12 MHz (ST7789V: zapis do ok. 15 MHz; kabel PH2.0),
  pełna klatka ok. 0,1 s, więc rysowanie tylko zmienionych fragmentów
  (16 KB RAM nie mieści bufora klatki). Sterowanie CS/DC/RST na PA10/PA9/PB14, podświetlenie
  PWM na PA8 (TIM1_CH1). Zasilanie i logika 3,3 V (moduł przy 5 V miałby logikę 5 V).
- **Programowanie:** bootloader DFU w ROM (BOOT0 + RESET), zapasowo SWD (J3).

## Elementy THT (nie ma ich w SMD)

| Element | Dlaczego THT | Wybór |
|---|---|---|
| Przełączniki Choc V1 | piny przełącznika | lutowane bezpośrednio w płytkę (bez gniazd hotswap) |
| EC11 | tylko THT | Alps EC11E15244G1 (z przyciskiem) |
| Suwak | tylko THT | ALPS RS45111A900F (45 mm, liniowy), footprint własny |
| J2 ekran | kabel PH2.0 z modułu kończy się żeńskimi wtykami 2,54 mm | listwa 1×8 2,54 mm |
| J3 SWD | opcja serwisowa | pady pod listwę 1×5 |

USB-C (USB4105) jest SMD z kołkami THT obudowy – najtrudniejszy element do lutowania
(raster 0,5 mm), ale jedyny rząd padów, bez drugiego rzędu pod spodem złącza.

## Footprint Kailh Choc V1/V2

`chocpilot.pretty/SW_Kailh_Choc_V1V2_1u` – przełącznik lutowany bezpośrednio, geometria wg
biblioteki kiswitch (`SW_Kailh_Choc_V1V2_1.00u`): otwór środkowy Ø5,05 (Choc V2; V1 też
wchodzi), kołki V1 Ø1,9 na ±5,5 mm, kołek V2 Ø1,6 w (−5; 5,15), piny przełącznika – pady THT
Ø2,2 / otwór 1,2 mm w (0; −5,9) (pin 1 = kolumna) i (5; −3,8) (pin 2 = anoda diody). Choc V2
ma piny w tych samych miejscach co V1. Projekt używa Choc V1 z drukowanymi keycapami
(`case/chocpilot_keycap.stl`); z Choc V2 trzeba keycapów MX. Stary footprint
z gniazdem hotswap (`SW_Kailh_Choc_V1V2_Hotswap_1u`) został w bibliotece, nieużywany.

## Do sprawdzenia przed zamówieniem

1. **Footprint Choc:** wydrukuj warstwę F.Cu 1:1 i przyłóż przełącznik Choc V1 (piny, kołki).
   Geometria pochodzi z biblioteki, nie z pomiaru.
2. **Ekran:** mocowanie modułu 58 × 35 mm w obudowie (otwory w rogach płytki modułu – wymiary
   z rysunku Waveshare lub pomiaru) i długość kabla PH2.0 do J2.
3. **Wysokości w obudowie:** ekran w obudowie nad płytką (najwyższe elementy pod nim: kwarc 1,3 mm, listwa J2); enkoder
   EC11 H20 i suwak (6,5 mm korpusu + dźwignia) – dobierz do nich obudowę.
4. **Nakładka suwaka:** dźwignia (4 × 1,2 mm) porusza się w y ≈ 24–69; nakładka szersza niż ok. 8 mm
   na końcach skoku zbliża się do keycapów K4/K8.
5. **Footprint suwaka ALPS:** wydrukuj 1:1 i przyłóż RS45111 (piny 1–3, kołki ustalające) – rysunek
   ALPS jest „widokiem od strony montażu”; przy lustrzanym odbiciu pin 2 trafi na drugą stronę.

## Firmware i aplikacja

Firmware: `firmware/` (środowisko PlatformIO `chocpilot`, opis w głównym README):
STM32duino + TinyUSB (CDC + HID), matryca z mapą klawiszy z tej płytki (`src/boards/board.h`),
LCD ST7789V na SPI1, pokrętła na TIM2/TIM3, suwak na ADC PB1, LED przez SPI2, ustawienia
w emulacji EEPROM, skok do bootloadera DFU komendą `reboot` (`bootloader: true`).
Protokół rozszerzony o `encoder`, `encoder_key`, `slider` (docs/PROTOCOL.md); w aplikacji każdy
profil ma akcje dla obu pokręteł (obrót w prawo / w lewo / naciśnięcie) i działanie suwaka
(głośność systemu albo programu).

## Obudowa

Model w `case/` (SolidCraft, opis w [case/README.md](../../case/README.md)): obrys pod płytkę
114 × 93 mm i otwory M3 jak wyżej, okno ekranu z 4 tulejami M2 na moduł, otwory na osie
enkoderów, szczelina suwaka, otwór USB-C dopasowany do gniazda (oś x = 107,5), dwa otwory w dnie
na RESET/BOOT0; dno z półprzezroczystego filamentu rozprasza światło diod.

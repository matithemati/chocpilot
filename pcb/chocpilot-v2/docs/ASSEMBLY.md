# ChocPilot v2 – montaż i uruchomienie

Wszystko lutowane ręcznie. Przyda się: grot ścięty 1–2 mm, topnik w żelu (no-clean), cyna
0,5 mm, plecionka, pęseta, lupa / mikroskop, multimetr. Gorące powietrze nie jest konieczne.

Zasada: **najpierw najdrobniejsze i najniższe elementy, potem coraz wyższe**, i najpierw strona,
na której jest najwięcej drobnicy (wierzch), dopóki płytka leży płasko.

## Kolejność

### 1. J1 – USB-C (GCT USB4105, wierzch)
1. Wciśnij kołki ustalające w otwory – złącze samo trafia w pady.
2. Pady sygnałowe (rząd 0,5 mm): topnik, kropla cyny na grocie, przeciągnięcie wzdłuż rzędu,
   mostki zbierz plecionką.
3. Na końcu 4 zaczepy obudowy (THT) – dużo cyny, to one trzymają złącze mechanicznie.
4. Sprawdź multimetrem brak zwarć VBUS–GND i CC1/CC2 z sąsiednimi padami.

### 2. Zasilanie i ochrona USB (wierzch)
F1, R1, R2, U3 (USBLC6, kropka = pin 1), C1, U2 (TPS73633) z C2, C3, C4.

**Test 1:** podłącz USB (najlepiej przez miernik prądu / zasilacz z ograniczeniem).
Pobór kilka mA. Zmierz **+5V ≈ 4,8–5,1 V** (C1) i **+3V3 = 3,3 V** (C3).

### 3. U1 – STM32F072 (LQFP-48, wierzch) i jego otoczenie
1. Topnik na pady, ustaw układ (kropka = pin 1 w lewym górnym rogu, jak trójkąt na sitodruku).
2. Przylutuj dwa przeciwległe narożne piny, sprawdź pod lupą, że wszystkie 4 rzędy leżą
   centralnie na padach.
3. Lutowanie „drag”: dużo topnika, kropla cyny na grocie, przeciągnij wzdłuż każdego boku.
4. Mostki zbierz plecionką z topnikiem. Sprawdź brak zwarć sąsiednich pinów, zwłaszcza par
   zasilania 23–24, 35–36, 47–48 (VSS/VDD) i 8–9 (VSSA/VDDA).
5. Od razu odsprzęganie: C5–C12, C9, oraz R3 (BOOT0 → GND).
6. Od spodu SW1 (RESET) i SW2 (BOOT0) – płaskie, nie przeszkadzają w dalszym lutowaniu.

**Test 2 – bootloader:** trzymaj **BOOT0**, naciśnij i puść **RESET**, puść BOOT0.
Komputer powinien zobaczyć urządzenie DFU `0483:df11` („STM32 BOOTLOADER”):

```bash
dfu-util -l
```

Wgraj firmware testowe (np. echo przez USB CDC), zanim przylutujesz resztę.

### 4. Reszta wierzchu (SMD)
- Y1 + C13, C14 (opcjonalne – można pominąć).
- R4, R5 (I²C), C15, C16.
- U4 (74AHCT1G125), C17, R6.
- **JP1** (zasilanie OLED) jest fabrycznie zmostkowana 1–2 = 3,3 V. Dla modułu 5 V przetnij
  mostek 1–2 i zlutuj 2–3.

### 5. Spód: kondensator łańcucha LED
C18 (10 µF).

### 6. Spód: diody WS2812B (L1–L12) i C19–C30
- **Orientacja:** pad 1 = VDD (+5V), pad 3 = GND, pad 4 = DIN, pad 2 = DOUT. Znacznik pinu
  na obudowie diody różni się między partiami – sprawdź w karcie katalogowej swojej partii
  (WS2812B-V5) i dopasuj do znacznika „1” na sitodruku. Pad GND dzwoni się z masą płytki.
  Łańcuch idzie L1 → L12 (patrz [PINOUT.md](PINOUT.md)).
- WS2812B nie lubi długiego grzania: grot ≤ 320 °C, krótko, najpierw jeden pad, potem pozostałe.
- Kondensator 100 nF przy każdej diodzie przylutuj od razu z diodą.

**Test 3:** firmware z prostym efektem na 12 diod, jasność ≤ 30 %. Jeśli świeci tylko
część łańcucha – sprawdź lut DOUT ostatniej świecącej i DIN następnej.

### 7. Spód: gniazda hotswap S1–S8
Gniazda Kailh Choc (CPG135001S30) od spodu, na pady 1 i 2: najpierw cyna na jeden pad,
dociśnij gniazdo pęsetą, przylutuj, potem drugi pad. Gniazdo musi leżeć płasko – inaczej
przełącznik nie wejdzie do końca.

### 8. THT na końcu
- **J2** – gniazdo 1×4 2,54 mm dla modułu OLED (wierzch). Moduł z listwą kołkową wtyka się
  od góry; przy innym rastrze / kolejności pinów modułu połącz go przewodami.
- **J3** (SWD) – opcjonalnie, zwykle bez listwy (do programatora wystarczy wcisnąć kołki).
- **ENC1, ENC2** – najpierw dwa zaczepy (MP, dużo cyny), potem 5 pinów.
- **RV1** – 4 zaczepy + 3 piny.
- Piny THT od spodu przytnij jak najkrócej (obudowa / blat).

### 9. Złożenie
Moduł OLED na J2 (i w obudowie), przełączniki Choc V2 wciśnięte w gniazda (płyta montażowa
w obudowie trzyma je w osi), keycapy MX, gałki enkoderów, nakładka suwaka.

## Najczęstsze problemy

| Objaw | Sprawdź |
|---|---|
| Brak DFU | 5,1 kΩ na CC1/CC2 (R1, R2), luty D+/D− przy J1 i U3, BOOT0 = 3,3 V w chwili resetu |
| Komputer zgłasza błąd USB | mostki na J1 (raster 0,5 mm), zamienione D+/D− = zły lut U3 |
| Ekran nie działa | kolejność pinów modułu vs J2 (GND, VCC, SCL, SDA), JP1, adres 0x3C/0x3D |
| LED: pierwsza miga losowo | lut R6 / U4, zasilanie U4 (+5V na pinie 5) |
| Klawisz nie reaguje | lut gniazda hotswap (oba pady), przełącznik wciśnięty do końca |

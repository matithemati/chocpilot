# ChocPilot

ChocPilot to przewodowy macropad z 9 klawiszami MX (matryca 3×3), pokrętłem EC11 z przyciskiem i
ekranem OLED 0.91" (128×32), oparty na **Adafruit KB2040** (RP2040), **Seeed XIAO ESP32-S3**
albo **Arduino / SparkFun Pro Micro** (ATmega32U4), oraz aplikacja na Windows, w której ustawiasz, co robi każdy klawisz i pokrętło.

Firmware jest „cienki”: skanuje klawisze i pokrętło, rysuje ekran i przechowuje kilka ustawień.
Całą logikę (gesty, akcje, profile) wykonuje aplikacja na PC. Komunikują się przez USB CDC
protokołem JSON Lines ([docs/PROTOCOL.md](docs/PROTOCOL.md)). Gdy aplikacja nie działa,
urządzenie samo wysyła zapisane skróty przez USB HID (tryb awaryjny).

```
firmware/   PlatformIO: środowiska kb2040, xiao_esp32s3, promicro(_3v3), native(_compact) (testy)
app/        aplikacja Python 3.12+ (PySide6): rdzeń, GUI, symulator, testy
case/       parametryczna obudowa OpenSCAD
docs/       PROTOCOL.md, WIRING.md
```

## Funkcje

- **Gesty**: naciśnięcie, przytrzymanie (próg 500 ms), podwójne naciśnięcie (okno 300 ms);
  pokrętło: obrót w prawo/lewo i obrót z wciśniętym przyciskiem, opcjonalne przyspieszenie.
- **Akcje**: uruchom program (albo przełącz na jego okno; przy kilku oknach kolejne naciśnięcia
  przechodzą między nimi), otwórz plik/folder, adres WWW,
  skrót klawiszowy (także Win, F13–F24), wpisz tekst (Unicode), multimedia, głośność
  systemu i pojedynczego programu, przewijanie, polecenie cmd/PowerShell, makro, zmiana
  profilu, warstwa (profil na czas trzymania klawisza), blokada komputera, wyłączenie ekranu.
- **Profile** z automatycznym przełączaniem według aktywnego okna (np. `obs64.exe` → „Stream”),
  import/eksport do JSON.
- **Ekran**: siatka etykiet 3×3 albo duża nazwa profilu, pasek głośności, etykieta po akcji,
  wygaszacz, znacznik online/offline, tryb testu sprzętu.
- **Tryb awaryjny HID**: po 3 s bez sygnału z aplikacji pokrętło zmienia głośność, przycisk
  wycisza, klawisze wysyłają skróty wyliczone z profilu (akcje „skrót” i „multimedia”).

## Wybór płytki

| | Adafruit KB2040 | Seeed XIAO ESP32-S3 | Pro Micro |
|---|---|---|---|
| Mikrokontroler | RP2040 | ESP32-S3 | ATmega32U4 (5 V/16 MHz lub 3,3 V/8 MHz) |
| Rozmiar | ok. 33 × 18 mm | 21 × 17,8 mm | ok. 33 × 18 mm (ten sam rozkład pinów co KB2040) |
| Wolne GPIO po podłączeniu | kilka (np. STEMMA QT) | 0 (wszystkie 11 zajęte) | kilka (A0–A3, D10) |
| Dioda statusu | NeoPixel (kolory) | jedna LED (świeci/miga) | brak (RX/TX LED steruje rdzeń USB) |
| Wgrywanie | dysk RPI-RP2 (UF2) | port USB (esptool) | bootloader Caterina (avrdude, „1200 bps touch”) |
| Pamięć ustawień | LittleFS | NVS (Preferences) | EEPROM (binarnie) |
| Ekran | pełny (czcionki U8g2, polskie znaki) | pełny | uproszczony (jeden krój 5×7, bez ogonków) |

Wszystkie działają tak samo z aplikacją – rozpoznaje je po nazwie produktu USB „ChocPilot”.
KB2040 jest prostszy w uruchomieniu (UF2, NeoPixel), XIAO – mniejszy. Pro Micro to najtańszy
zamiennik KB2040 na tej samej PCB, ale ma tylko 2,5 KB RAM i 28 KB flash – patrz
[Firmware – Pro Micro](#pro-micro-atmega32u4).

## Części

- 1× Adafruit KB2040 **albo** Seeed XIAO ESP32-S3 **albo** Pro Micro (ATmega32U4)
- 9× przełącznik MX (+ nasadki), 9× dioda 1N4148
- 1× enkoder EC11 z przyciskiem (tuleja M7) + gałka
- 1× OLED 0.91" SSD1306 128×32 I²C (adres 0x3C)
- przewody, obudowa (wydruk 3D z `case/`), 4 wkręty M2 (lub M3)

## Montaż

Pełny opis i tabele pinów: **[docs/WIRING.md](docs/WIRING.md)**. Najważniejsze:

1. Matryca **COL2ROW**: przy każdym przełączniku dioda 1N4148, **pasek (katoda) w stronę wiersza**.
   Wiersze R1–R3 i kolumny C1–C3 podłącz według tabeli dla wybranej płytki.
2. Enkoder: A, B, SW na GPIO; wspólny pin C i druga nóżka przycisku do GND.
3. OLED: VCC → **3,3 V**, GND, SDA, SCL.
4. Uruchom tryb testu sprzętu (przytrzymaj **K1 + K3** zaraz po podłączeniu, przez 3 s) i sprawdź
   każdy klawisz, przycisk i kierunek pokrętła.

## Firmware

Wymagania: [PlatformIO](https://platformio.org/) (VS Code + rozszerzenie albo `pip install platformio`).

```bash
cd firmware
pio run -e kb2040
```

```bash
pio run -e xiao_esp32s3
```

```bash
pio run -e promicro
```

(`promicro` – Pro Micro 5 V/16 MHz, `promicro_3v3` – wersja 3,3 V/8 MHz.)

Wersje (sprawdzone 2026-10): U8g2 2.36.18, ArduinoJson 7.4.3, Adafruit NeoPixel 1.15.5.

- **KB2040**: platforma `maxgerhardt/platform-raspberrypi` (rdzeń arduino-pico Earle Philhowera),
  płytka `adafruit_kb2040`, stos Adafruit TinyUSB (`-DUSE_TINYUSB`): CDC + HID (klawiatura i
  consumer control). Nazwa USB ustawiona przez `board_build.arduino.earlephilhower.usb_product`.
- **XIAO ESP32-S3**: oficjalna platforma `espressif32` w PlatformIO nadal dostarcza Arduino-ESP32 2.x,
  dlatego używamy **pioarduino** `53.03.13` (Arduino-ESP32 **3.1.3**), płytka `seeed_xiao_esp32s3`.
  Definicja płytki domyślnie ustawia `ARDUINO_USB_MODE=1` (sprzętowy CDC/JTAG – bez HID), więc
  `platformio.ini` nadpisuje `board_build.extra_flags` na `ARDUINO_USB_MODE=0` +
  `ARDUINO_USB_CDC_ON_BOOT=1` (TinyUSB: CDC + HID). Nazwa USB przez `-DUSB_PRODUCT="ChocPilot"`.
  Uwaga: wariant XIAO ma **własny VID Seeed 0x2886** (nie Espressif 0x303A) – aplikacja szuka
  wszystkich trzech VID (0x303A, 0x239A, 0x2886) i zawsze potwierdza urządzenie wiadomością `hello`.
- `lib_ldf_mode = chain+` – wykrywanie bibliotek respektuje `#if`, dzięki czemu HAL jednej płytki
  nie wciąga bibliotek drugiej.

### Pro Micro (ATmega32U4)

Platforma `atmelavr`, płytka `sparkfun_promicro16` (albo `sparkfun_promicro8`), rdzeń Arduino AVR:
USB CDC + HID (PluggableUSB, klawiatura i consumer control). Nazwa USB „ChocPilot”, VID/PID z definicji
płytki SparkFun: **1B4F:9206** (5 V) / **1B4F:9204** (3,3 V). Aplikacja szuka tych par oraz
klonów z bootloaderem Leonardo/Micro (2341:8036 / 8037) – nigdy PID-ów bootloadera.

ATmega32U4 ma **2,5 KB RAM i 28 KB flash** (z bootloaderem Caterina), więc środowisko buduje
wersję kompaktową (`-DCHOCPILOT_COMPACT`). Zużycie (sprawdzone 2026-10, `pio run -e promicro`):
**flash 27 632 B / 28 672 B (96,4 %)**, **RAM statycznie 2 083 B / 2 560 B (81,4 %)** – reszta
to stos (bufor pasa ekranu, parser). Co zmieniono względem KB2040 / XIAO:

- **Ekran**: zamiast grafiki U8g2 z sześcioma czcionkami (ok. 8 KB) – własny mini-renderer
  (`firmware/src/mini_gfx.cpp`) na sterowniku U8x8: jeden krój **5×7 ASCII**, powiększany 2× i
  pogrubiany. Układ ekranów bez zmian (siatka 3×3 z 7-znakowymi etykietami, profil, tekst, pasek,
  błysk, test), ale napisy są prostsze, a **polskie litery tracą ogonki** (ą → a, Ł → L).
- **Protokół**: kodek bez ArduinoJson (`protocol_codec_compact.cpp`, czyta linię w miejscu, bez
  alokacji). Maksymalna linia do urządzenia to **272 B** (zgłaszane w `hello` jako `max_line`);
  aplikacja sama dzieli dłuższe `set_fallback` na kilka wiadomości.
- **Bufory**: tytuł do 21 znaków ASCII (22 B), etykieta do 7 znaków (10 B) – wielobajtowe UTF-8
  skraca się wcześniej; kolejka raportów HID trybu awaryjnego 12 zamiast 32 (szybki obrót
  pokrętła offline wysyła najwyżej kilka kroków naraz).
- **Ustawienia** w EEPROM jako blok binarny z CRC (nie JSON). Zapis nie jest atomowy: przerwany
  odłączeniem zasilania kończy się wartościami domyślnymi.
- **Brak diody statusu** (stan widać na ekranie).
- Ekran tylko przez **programowe I²C** (jak na KB2040 – patrz [docs/WIRING.md](docs/WIRING.md)).

### Wgrywanie – KB2040

1. Przytrzymaj **BOOT**, naciśnij i puść **RESET**, puść BOOT → pojawi się dysk **RPI-RP2**.
2. Skopiuj `firmware/.pio/build/kb2040/firmware.uf2` na ten dysk (płytka sama się zrestartuje).

Albo bezpośrednio: `pio run -e kb2040 -t upload` (działa też z działającym firmware ChocPilot – reset
przez „1200 bps touch”). Z aplikacji: menu **Urządzenie → Tryb wgrywania firmware**.

### Wgrywanie – XIAO ESP32-S3

1. Trzymając przycisk **BOOT** (B), podłącz kabel USB-C (albo: trzymaj BOOT i naciśnij RESET).
2. `pio run -e xiao_esp32s3 -t upload`
3. Po wgraniu naciśnij **RESET** (w trybie pobierania płytka nie uruchamia się sama).

Przy kolejnych aktualizacjach można użyć menu aplikacji **Urządzenie → Tryb wgrywania firmware**.

### Wgrywanie – Pro Micro

```bash
pio run -e promicro -t upload
```

Najpierw zamknij aplikację ChocPilot (trzyma port COM). PlatformIO otwiera port z prędkością
1200 bps („1200 bps touch”), płytka restartuje się do bootloadera **Caterina** (osobny port COM
na ok. 8 s, potem wraca do programu) i avrdude wgrywa firmware. Menu aplikacji
**Urządzenie → Tryb wgrywania firmware** też przełącza do Caterina (firmware wpisuje „magiczny
klucz” i restartuje się watchdogiem) – przydatne przy wgrywaniu ręcznym avrdude w ciągu tych 8 s.
Gdy firmware nie działa: zewrzyj dwa razy szybko **RST** z **GND** i od razu wgrywaj.

### Testy firmware (na PC)

Parser protokołu, dekoder enkodera (sekwencje A/B z drganiami), debounce, kody HID i zapis
konfiguracji mają testy jednostkowe w środowisku `native`. Potrzebny jest kompilator gcc/g++
w PATH (Windows: MSYS2/MinGW-w64; najprościej `pio pkg install -g -t platformio/toolchain-gccmingw32`
i dodanie `%USERPROFILE%\.platformio\packages\toolchain-gccmingw32\bin` do PATH).

```bash
pio test -e native -e native_compact
```

`native_compact` uruchamia te same testy dla wersji kompaktowej (Pro Micro): kodek bez
ArduinoJson i binarny zapis konfiguracji.

## Aplikacja

Wymagania: Windows 10/11, Python **3.12+** (sprawdzone na 3.14).

```bash
cd app
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m chocpilot
```

Opcje:

| Opcja | Działanie |
|---|---|
| `--simulate` | zamiast urządzenia uruchamia **symulator** (okno z 9 klawiszami, pokrętłem – kółko myszy – i podglądem OLED) |
| `--board xiao_esp32s3` / `--board promicro` | płytka zgłaszana przez symulator (`promicro`: limit linii 272 B jak w firmware) |
| `--minimized` | start w zasobniku |
| `--config PLIK` | inny plik konfiguracji |
| `--verbose` | dziennik na konsoli |

Konfiguracja: `%APPDATA%\ChocPilot\config.json` (zapis atomowy, poprzednia wersja w `config.json.bak`,
dziennik w `chocpilot.log`). Uszkodzony plik jest odkładany jako `config.broken.json`, a aplikacja
wczytuje kopię zapasową.

Obsługa:

- Lista profili po lewej (dwuklik = aktywuj). Kliknij klawisz albo pokrętło na podglądzie, aby
  edytować; przyciski **Testuj** wykonują akcję od razu. Fizyczne naciśnięcia podświetlają elementy.
- **Plik → Ustawienia**: port (auto/ręczny), jasność, wygaszacz, tryb ekranu, obrót, progi gestów,
  pokrętło (odwrócenie, impulsy na ząbek, przyspieszenie), debounce, skróty trybu awaryjnego,
  autostart z Windows, start zminimalizowany, motyw.
- Zamknięcie okna chowa aplikację do zasobnika (kolor ikony = stan połączenia). Z zasobnika:
  zmiana profilu, **Wstrzymaj akcje**, wyjście. Uruchamia się tylko jedna instancja.

### Testy i jakość

```bash
cd app
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check chocpilot tests
.venv\Scripts\python -m ruff format --check chocpilot tests
.venv\Scripts\python -m mypy chocpilot
```

Testy nie wymagają urządzenia (atrapy portu szeregowego, platformy i symulator). Testy GUI
działają w trybie `offscreen` (pytest-qt).

### Budowanie ChocPilot.exe

```powershell
cd app
.\build_exe.ps1
```

Skrypt instaluje zależności, generuje ikonę (`scripts/make_icon.py`) i uruchamia PyInstaller
(`chocpilot.spec`, jeden plik, bez konsoli). Wynik: `app\dist\ChocPilot.exe`.

### Architektura aplikacji

```
chocpilot/core/protocol.py    kodowanie/dekodowanie JSON Lines, walidacja, transliteracja (OLED = ASCII)
chocpilot/core/transport.py   interfejs + port szeregowy (wątek, wykrywanie, ponowne łączenie)
chocpilot/core/simulator.py   symulator urządzenia (ta sama logika co firmware) + transport w procesie
chocpilot/core/gestures.py    tap / hold / double_tap / obroty (czysta logika, czas z zewnątrz)
chocpilot/core/actions/       rejestr typów akcji, wbudowane akcje, wykonawca (pula wątków)
chocpilot/core/config.py      modele pydantic, migracje schema_version, zapis atomowy, import/eksport
chocpilot/core/profiles.py    aktywny profil, warstwy, automatyczne przełączanie
chocpilot/core/engine.py      kontroler: zdarzenia → gesty → akcje; profil → display + set_fallback
chocpilot/platform/           kod zależny od systemu (windows.py; base.py = interfejs dla Linux/macOS)
chocpilot/gui/                PySide6: okno główne, edytory, ustawienia, zasobnik, symulator
```

Nowy typ akcji: klasa dziedzicząca po `ActionBase` z polem `type: Literal["nazwa"]`, metodą
`run(ctx)` i dekoratorem `@register_action("nazwa", "Etykieta")`. Formularz w GUI tworzy się
automatycznie z pól modelu.

## Obudowa (OpenSCAD)

`case/chocpilot_case.scad` – parametry na początku pliku (płytka, otwór MX 14,0 mm, rozstaw 19,05 mm,
płyta 1,5 mm, okno OLED, otwór 7,2 mm na EC11, śruby M2/M3, pochylenie `tilt_deg`).

```bash
openscad -D part=\"top\" -D board=\"kb2040\" -o chocpilot_top.stl case/chocpilot_case.scad
```

```bash
openscad -D part=\"bottom\" -D board=\"kb2040\" -D tilt_deg=6 -o chocpilot_bottom.stl case/chocpilot_case.scad
```

Górę drukuj płytą do stołu (plik jest już obrócony), dół – bez podpór. Moduł OLED wkleja się
w ramkę prowadzącą od spodu, enkoder przykręca nakrętką M7, płytka wsuwa się w uchwyt przy tylnej
ściance (USB-C w wycięciu).

### Obudowa dla płytki PCB (MacroPad_Y7)

`case/chocpilot_pcb_case.scad` – obudowa dla drukowanej płytki 62,55 × 80,05 mm (wymiary i pozycje
elementów wzięte z gerberów): skorupa ze „studnią” na keycapy, oknem OLED i otworem na EC11,
dno ze słupkami pod 4 otwory M2 płytki, wycięcie USB-C w prawej ściance i gałka na wałek D 6 mm.
KB2040 jest domyślnie wlutowany od spodu płytki (`mcu_side`), a OLED leży 4,5 mm nad PCB
(`oled_top`); przy innym montażu zmień te parametry.

```bash
openscad -D part=\"shell\" -o chocpilot_pcb_shell.stl case/chocpilot_pcb_case.scad
```

```bash
openscad -D part=\"bottom\" -o chocpilot_pcb_bottom.stl case/chocpilot_pcb_case.scad
```

Części: `shell`, `bottom`, `knob`; podgląd: `assembly`, `exploded`. Montaż: płytka do dna
4 wkrętami M2×6 od góry (przed założeniem keycapów), skorupa do dna 4 wkrętami M2×8 od spodu.

## Rozwiązywanie problemów

| Objaw | Co sprawdzić |
|---|---|
| Aplikacja „szuka ChocPilot…” | Kabel z transmisją danych (nie tylko ładowanie). Zamknij monitor portu PlatformIO/Arduino IDE (port może być zajęty). W Ustawieniach wybierz port ręcznie. Dziennik pokazuje próby. |
| XIAO nie pojawia się jako klawiatura / brak portu | Firmware musi być zbudowany z `ARDUINO_USB_MODE=0` (środowisko `xiao_esp32s3`). Po wgraniu naciśnij RESET. |
| Nie da się wgrać na XIAO | Wejdź w tryb pobierania: BOOT + podłączenie kabla. |
| KB2040 nie widać jako dysku | BOOT trzymany podczas RESET; inny kabel/port. |
| Pro Micro: wgrywanie kończy się błędem / brak portu | Dwa razy szybko zewrzyj RST z GND i od razu uruchom `pio run -e promicro -t upload`. Klon z bootloaderem Leonardo ma VID 2341 – aplikacja też go znajdzie (PID 8036/8037). |
| Pro Micro: dziwne znaki na ekranie | To nie błąd: wersja kompaktowa ma tylko krój ASCII, polskie litery są wyświetlane bez ogonków. |
| Pusty ekran | Spójrz na pasek stanu aplikacji: **OLED: 0x3C/0x3D** = ekran odpowiada (adres wybierany automatycznie), **OLED: brak** = nic nie odpowiada na I²C – sprawdź zasilanie 3,3 V, GND, zamienione SDA/SCL i lutowanie. Lista znalezionych urządzeń jest w zakładce Dziennik. |
| Pokrętło liczy podwójnie / co drugi ząbek | Ustawienia → Pokrętło → **Impulsy na ząbek** (EC11 zwykle 4, niektóre 2). |
| Pokrętło kręci odwrotnie | Ustawienia → Pokrętło → **Odwróć kierunek**. |
| Kilka klawiszy reaguje naraz | Odwrócona dioda albo brak diody; sprawdź w trybie testu sprzętu. |
| Klawisz „drga” | Zwiększ debounce (Ustawienia → Urządzenie). |
| Przełączanie na okno programu nie działa | Windows czasem blokuje przejęcie fokusu; program i tak jest uruchamiany, gdy nie ma okna. |
| Głośność programu „nie gra” | Program musi mieć aktywną sesję audio (widoczną w mikserze głośności). |
| SmartScreen / antywirus ostrzega o ChocPilot.exe | Plik nie jest podpisany; pynput (symulacja klawiatury) bywa oznaczany heurystycznie. Można uruchamiać z Pythona. |
| Akcje wykonują się podwójnie | Nie powinno: gdy aplikacja jest połączona, HID urządzenia jest wyłączony. Sprawdź, czy nie działają dwie kopie aplikacji (np. exe i python). |

## Licencja

MIT.

# ChocPilot

ChocPilot to przewodowy macropad na własnej płytce ze **STM32F072** i aplikacja na **Windows
i macOS**, w której ustawiasz, co robi każdy element:

- **8 klawiszy Kailh Choc V1** (matryca 2×4) z drukowanymi keycapami,
- kolorowy ekran **[Waveshare 2" IPS LCD 240×320](https://www.tme.eu/pl/details/wsh-17344/wyswietlacze-lcd-graficzne/waveshare/17344/)**
  (ST7789V, SPI; TME WSH-17344) pomiędzy rzędami klawiszy – etykiety albo ikony klawiszy,
  nazwa profilu, nastawy, wygaszacz z animacją i zegarem,
- **2 pokrętła EC11** z przyciskiem i **suwak 45 mm**,
- **12 diod WS2812B** na spodzie (podświetlenie blatu),
- USB-C (USB CDC + HID, bez sterowników).

Firmware jest „cienki”: skanuje klawisze, pokrętła i suwak, rysuje ekran, steruje diodami
i przechowuje kilka ustawień. Całą logikę (gesty, akcje, profile, tryb Klipper) wykonuje
aplikacja. Komunikują się przez USB CDC protokołem JSON Lines ([docs/PROTOCOL.md](docs/PROTOCOL.md)).
Gdy aplikacja nie działa, urządzenie samo wysyła zapisane skróty przez USB HID (tryb awaryjny).

```
firmware/   PlatformIO: chocpilot (STM32F072, STM32duino + TinyUSB), native (testy na PC)
app/        aplikacja Python 3.12+ (PySide6): rdzeń, GUI, symulator, testy, budowanie exe / .app
pcb/        płytka KiCad 10: schemat, PCB, BOM (TME), Gerbery, montaż, mapa pinów
case/       SolidCraft: obudowa, keycapy, gałki, nakładka suwaka, podstawka (STEP / 3MF / STL)
docs/       PROTOCOL.md – protokół urządzenie ↔ aplikacja
```

## Funkcje

- **Gesty**: naciśnięcie, przytrzymanie (próg 500 ms), podwójne naciśnięcie (okno 300 ms).
- **Akcje**: uruchom program (albo przełącz na jego okno; przy kilku oknach kolejne naciśnięcia
  przechodzą między nimi), otwórz plik/folder, adres WWW, skrót klawiszowy (także Win/Cmd,
  F13–F24), wpisz tekst (Unicode), multimedia, głośność systemu i pojedynczego programu
  (Windows), przewijanie, polecenie powłoki, makro, zmiana profilu, warstwa (profil na czas
  trzymania klawisza), tryb Klipper, blokada komputera, wyłączenie ekranu.
- **Profile** z automatycznym przełączaniem według aktywnego programu (np. `obs64.exe` / `OBS`
  → „Stream”), import/eksport do JSON, własny kolor diod dla profilu.
- **Pokrętła i suwak**: każde pokrętło ma akcje dla obrotu w prawo, w lewo i naciśnięcia (te same
  typy akcji co klawisze; głośność i przewijanie mnożą krok przez liczbę zatrzasków). Suwak
  ustawia głośność systemu albo wybranego programu (0–100 %). Domyślnie pokrętło 1 = głośność /
  wycisz, pokrętło 2 = przewijanie / odtwarzaj-pauza.
- **Ekran 320×240**: siatka 2×4 z etykietami albo [ikonami](#ikony-klawiszy) klawiszy, duża
  nazwa profilu, pasek głośności, napis po akcji, znacznik online/offline, tryb testu sprzętu,
  [wygaszacz](#wygaszacz-ekranu) z animacją i godziną. Podgląd w aplikacji rysuje te same piksele.
- **Podświetlenie LED**: stan połączenia, stały kolor, oddychanie, tęcza, wyłączone; błysk diody
  przy naciśniętym klawiszu. Ustawienia zapisane w urządzeniu działają też bez aplikacji.
- **[Tryb Klipper](#tryb-klipper-drukarki-3d)**: sterowanie drukarkami 3D przez Moonraker.
- **Tryb awaryjny HID**: po 3 s bez sygnału z aplikacji klawisze wysyłają skróty wyliczone
  z profilu (akcje „skrót” i „multimedia”), pokrętło 1 zmienia głośność; domyślnie dolny rząd:
  ciszej, głośniej, odtwarzaj/pauza, wycisz.

## Sprzęt

Wszystko o płytce jest w [pcb/README.md](pcb/README.md):

- lista części z numerami TME: [pcb/bom/BOM.md](pcb/bom/BOM.md) (wszystko poza przełącznikami
  Kailh jest w TME, łącznie z ekranem),
- kolejność lutowania i uruchomienie: [pcb/docs/ASSEMBLY.md](pcb/docs/ASSEMBLY.md),
- mapa pinów MCU i złączy: [pcb/docs/PINOUT.md](pcb/docs/PINOUT.md),
- decyzje projektowe, zasilanie, sygnały: [pcb/docs/DESIGN_NOTES.md](pcb/docs/DESIGN_NOTES.md),
- Gerbery do zamówienia płytek: `pcb/fab/gerbers/` (2 warstwy, 1,6 mm – standard JLCPCB / PCBWay).

Obudowa, keycapy, gałki pokręteł, nakładka suwaka i podstawka pod kątem 20°:
[case/README.md](case/README.md) (gotowe pliki STL / 3MF do druku).

Ekran Waveshare 2" przykręca się 4 wkrętami M2 do obudowy i łączy dołączonym kablem PH2.0
ze złączem J2 płytki (1:1, zasilanie 3,3 V).

## Firmware

Wymagania: [PlatformIO](https://platformio.org/) (VS Code + rozszerzenie albo `pip install platformio`).

```bash
cd firmware
pio run
```

- **Rdzeń**: Arduino STM32duino (platforma `ststm32`, płytka `boards/chocpilot.json` = wariant
  generic F072CB), zegar 48 MHz z HSI48 bez kwarcu, dostrajany przez CRS do ramek USB.
- **USB**: [TinyUSB](https://github.com/hathach/tinyusb) 0.18 – urządzenie złożone CDC + HID
  (klawiatura i consumer control), nazwa „ChocPilot”, VID:PID **1209:0001** (pid.codes).
  Aplikacja znajduje port po nazwie, zapasowo po tej parze.
- **Ekran** (`src/display_tft.cpp`, `src/st7789.cpp`): SPI1 12 MHz, tryb 3, bez bufora ramki –
  rysowane są tylko zmienione fragmenty, a po serii komend (np. ikony przy zmianie profilu)
  ekran odświeża się raz, gdy zmiany ustaną. Jasność = PWM podświetlenia, `flip` = obrót o 180°.
  Krój 5×7 ASCII w kilku skalach – polskie litery tracą ogonki (ą → a).
- **Matryca** 2×4 COL2ROW z mapą klawiszy z płytki (`src/boards/board.h`).
- **Pokrętła i suwak** (`src/controls.cpp`): TIM2/TIM3 w trybie enkodera, suwak przez ADC
  z filtrem i histerezą. **Offline** pokrętło 1 zmienia głośność, jego przycisk wycisza.
- **LED** (`src/leds.cpp`, SPI2 3 MHz; efekty `lib/chocpilotcore/src/led_effects.cpp`): jasność
  ograniczona do ok. 1/3 (prąd z USB), przy wygaszaczu wyłączone, w trybie testu kolejno R / G / B / biały.
- **Wygaszacz** (`src/saver.cpp`): animacje z `app/chocpilot/core/savers.py` (jedno źródło dla
  firmware i podglądu) – `python firmware/tools/gen_savers.py` generuje z nich `src/saver_data.h`.
- **Ikony klawiszy** (`src/icons.cpp`): 32×32 px, 16 kolorów, tylko w RAM (aplikacja wysyła je
  po połączeniu).
- **Ustawienia** w emulacji EEPROM rdzenia (ostatnia strona flash) jako blok binarny z CRC
  i numerem wersji – nowsze wersje firmware czytają zapisy starszych.
- **Zużycie** (2026-11, `pio run`): **flash 56 500 B / 128 KB (43 %)**, **RAM 11 228 B / 16 KB (69 %)**.

### Wgrywanie (bootloader DFU w ROM)

Windows:

```powershell
cd firmware
.\flash.ps1
```

Skrypt kompiluje firmware, przełącza działającą płytkę w bootloader (komenda `reboot`) i wgrywa
program przez dfu-util. Opcje: `-BuildOnly` (tylko kompilacja), `-CloseApp` (najpierw zamyka
aplikację ChocPilot, która trzyma port). Bez skryptu (Windows i macOS):

1. Wejście do bootloadera: w aplikacji **Urządzenie → Tryb wgrywania firmware** albo przyciski
   na spodzie płytki (dostęp przez otwory w dnie): trzymaj **BOOT0**, naciśnij i puść **RESET**,
   puść BOOT0. System widzi wtedy „STM32 BOOTLOADER” (0483:DF11).
2. `pio run -t upload` – po wgraniu płytka sama uruchamia program.

Windows za pierwszym razem: przypisz urządzeniu „STM32 BOOTLOADER” sterownik **WinUSB**
programem [Zadig](https://zadig.akeo.ie/) (albo wgraj `.pio\build\chocpilot\firmware.bin` od
adresu 0x08000000 w STM32CubeProgrammer). macOS nie potrzebuje sterownika.

### Testy firmware (na PC)

Parser protokołu, debounce, kody HID, zapis konfiguracji i efekty LED mają testy jednostkowe
w środowisku `native`. Potrzebny jest kompilator gcc/g++ w PATH (Windows: MinGW-w64 –
`pio pkg install -g -t platformio/toolchain-gccmingw32` i dodanie
`%USERPROFILE%\.platformio\packages\toolchain-gccmingw32\bin` do PATH; macOS: Xcode Command Line Tools).

```bash
pio test -e native
```

## Aplikacja

Wymagania: Windows 10/11 albo macOS 12+, Python **3.12+** (sprawdzone na 3.14).

Windows:

```powershell
cd app
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m chocpilot
```

macOS:

```bash
cd app
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m chocpilot
```

| Opcja | Działanie |
|---|---|
| `--minimized` | start w zasobniku (macOS: pasek menu) |
| `--config PLIK` | inny plik konfiguracji |
| `--verbose` | dziennik na konsoli |
| `--simulate` | tryb deweloperski: okno symulatora płytki (klawisze, pokrętła, suwak, LED, podgląd LCD) zamiast urządzenia |
| `--version` | wersja aplikacji |

Konfiguracja i dziennik:

| System | Katalog |
|---|---|
| Windows | `%APPDATA%\ChocPilot` |
| macOS | `~/Library/Application Support/ChocPilot` |

`config.json` (zapis atomowy, poprzednia wersja w `config.json.bak`), `chocpilot.log`
(rotacja 3 × 512 KB), `icons/` (własne ikony). Uszkodzony plik konfiguracji jest odkładany
jako `config.broken.json`, a aplikacja wczytuje kopię zapasową. Nieobsłużone błędy trafiają do
dziennika z pełnym śladem i pokazują jedno okno z informacją – aplikacja działa dalej.

Obsługa:

- Lista profili po lewej (dwuklik = aktywuj). Kliknij klawisz, pokrętło albo suwak na podglądzie,
  aby edytować; przyciski **Testuj** wykonują akcję od razu. Fizyczne naciśnięcia podświetlają
  elementy podglądu.
- **Plik → Ustawienia**: port (auto/ręczny), jasność, wygaszacz i jego animacja, tryb ekranu,
  obrót, podświetlenie LED (podgląd na żywo), progi gestów, debounce, skróty trybu awaryjnego,
  autostart, start zminimalizowany, motyw, język (PL/EN).
- Zamknięcie okna chowa aplikację do zasobnika (kolor ikony = stan połączenia). Z zasobnika:
  zmiana profilu, **Wstrzymaj akcje**, wyjście. Uruchamia się tylko jedna instancja.

### macOS – uprawnienia i ograniczenia

- **Dostępność** (Ustawienia systemowe → Prywatność i ochrona → Dostępność): wymagana do skrótów,
  wpisywania tekstu, przewijania, blokady ekranu i przełączania okien. Przy pierwszym starcie
  macOS sam pokazuje prośbę, a aplikacja wyjaśnia, co włączyć; po włączeniu uruchom ją ponownie.
- **Automatyzacja**: przy pierwszym poleceniu powłoki uruchamianym w widocznym oknie macOS pyta
  o zgodę na sterowanie Terminalem (AppleScript) – zezwól.
- Głośność **pojedynczego programu** nie jest dostępna (macOS nie ma do tego publicznego API);
  głośność systemu działa.
- Autostart = LaunchAgent `~/Library/LaunchAgents/com.chocpilot.app.plist` (włączany w Ustawieniach).

### Testy i jakość

```bash
cd app
.venv/Scripts/python -m pytest          # macOS: .venv/bin/python
.venv/Scripts/python -m ruff check chocpilot tests
.venv/Scripts/python -m ruff format --check chocpilot tests
.venv/Scripts/python -m mypy chocpilot
```

Testy nie wymagają urządzenia (atrapy portu szeregowego, platformy i symulator). Testy GUI
działają w trybie `offscreen` (pytest-qt).

### Budowanie – Windows (ChocPilot.exe)

```powershell
cd app
.\build_exe.ps1
```

Skrypt instaluje zależności, generuje ikony (`scripts/make_icon.py`) i uruchamia PyInstaller
(`chocpilot.spec`): jeden plik bez konsoli, z ikoną i metadanymi wersji (Właściwości pliku).
Wynik: `app\dist\ChocPilot.exe`. Działającą kopię z `dist` skrypt zamyka przed budowaniem
i uruchamia ponownie (`-NoRestart` – bez ponownego uruchomienia).

### Budowanie – macOS (ChocPilot.app)

```bash
cd app
./build_macos.sh
```

Skrypt (na Macu, z Pythonem 3.12+ z python.org albo Homebrew i Xcode Command Line Tools)
tworzy `.venv`, uruchamia testy, generuje ikonę `.icns`, buduje **`dist/ChocPilot.app`**
(PyInstaller, architektura Pythona – na Apple Silicon `arm64`), podpisuje ją ad-hoc i pakuje
do **`dist/ChocPilot-<wersja>-macOS-<arch>.dmg`** (przeciągnij do Aplikacji). Opcje:
`--skip-tests`, `--no-dmg`.

- Pierwsze uruchomienie aplikacji podpisanej ad-hoc: Finder → prawy klik → **Otwórz** (albo
  `xattr -dr com.apple.quarantine /Applications/ChocPilot.app`), bo Gatekeeper nie zna autora.
- Do dystrybucji innym osobom: `CODESIGN_IDENTITY="Developer ID Application: …" ./build_macos.sh`
  podpisuje certyfikatem Apple (hardened runtime); potem notaryzacja:
  `xcrun notarytool submit dist/ChocPilot-*.dmg --keychain-profile <profil> --wait`
  i `xcrun stapler staple dist/ChocPilot-*.dmg`.
- Po każdej przebudowie podpisanej ad-hoc macOS może zapomnieć uprawnienie Dostępność – wyłącz
  i włącz ChocPilot na liście (albo usuń i dodaj ponownie).

### Wersje

Jedno źródło wersji aplikacji: `app/chocpilot/__init__.py` (`__version__`) – używają go pakiet
Pythona, okno „O programie”, metadane exe i `Info.plist`. Wersja firmware: `CHOCPILOT_FW_VERSION`
w `firmware/platformio.ini`; aplikacja pokazuje ją na pasku stanu.

### Architektura aplikacji

```
chocpilot/core/protocol.py    kodowanie/dekodowanie JSON Lines, walidacja, transliteracja (krój ASCII)
chocpilot/core/transport.py   interfejs + port szeregowy (wątek, wykrywanie, ponowne łączenie)
chocpilot/core/simulator.py   symulator urządzenia (ta sama logika co firmware) + transport w procesie
chocpilot/core/gestures.py    tap / hold / double_tap (czysta logika, czas z zewnątrz)
chocpilot/core/actions/       rejestr typów akcji, wbudowane akcje, wykonawca (pula wątków)
chocpilot/core/config.py      modele pydantic, migracje schema_version, zapis atomowy, import/eksport
chocpilot/core/profiles.py    aktywny profil, warstwy, automatyczne przełączanie
chocpilot/core/engine.py      kontroler: zdarzenia → gesty → akcje; profil → ekran, ikony, LED, skróty HID
chocpilot/core/klipper.py     tryb Klipper (moonraker.py – klient HTTP Moonrakera)
chocpilot/core/leds.py        efekty LED (jak firmware – podgląd), savers.py – animacje wygaszacza
chocpilot/platform/           kod zależny od systemu: windows.py, macos.py (base.py = interfejs)
chocpilot/gui/                PySide6: okno główne, edytory, ustawienia, zasobnik, symulator
chocpilot/gui/lcd.py          podgląd ekranu LCD 320×240 – ten sam krój i układ co firmware
chocpilot/gui/icon_*.py       biblioteka i wybór ikon klawiszy
```

Nowy typ akcji: klasa dziedzicząca po `ActionBase` z polem `type: Literal["nazwa"]`, metodą
`run(ctx)` i dekoratorem `@register_action("nazwa", "Etykieta")`. Formularz w GUI tworzy się
automatycznie z pól modelu.

## Ikony klawiszy

Każdy klawisz może mieć na ekranie ikonę zamiast etykiety: edytor klawisza → **Ikona na
ekranie** → *Wybierz ikonę…*. Okno wyboru ma wyszukiwarkę i kategorie:

- **wbudowane** – ok. 120 ikon liniowych (multimedia, edycja, programy, system, streaming, druk 3D,
  symbole), zdefiniowane w `app/chocpilot/gui/icon_set.py`; nowa ikona = jeden wiersz SVG,
- **emoji** – wszystkie emoji czcionki systemu (Windows: Segoe UI Emoji, macOS: Apple Color
  Emoji), wyszukiwane po angielskiej nazwie Unicode,
- **własne** – pliki PNG / SVG / JPG z folderu `icons` w katalogu konfiguracji (przycisk *Folder
  własnych ikon*, potem *Odśwież*).

Aplikacja zamienia ikonę na 32 × 32 px w 16 kolorach na tle kafelka i wysyła ją do urządzenia
(komenda `icon`), które rysuje ją w skali 2. Przy zmianie profilu ikony idą przed siatką, więc
nowy ekran pojawia się od razu z kompletem ikon. Etykieta zostaje – pokazuje się w podglądzie
po naciśnięciu i po restarcie płytki bez aplikacji.

## Wygaszacz ekranu

Po czasie `screensaver_s` (Ustawienia → Urządzenie) ekran gaśnie albo pokazuje animację –
po trawie skacze królik albo kłusuje corgi, a u góry na środku jest godzina HH:MM (czas podaje
aplikacja, płytka liczy dalej sama). Wybór: **Ustawienia → Urządzenie → Animacja wygaszacza**.
Dowolny klawisz / pokrętło budzi ekran, diody LED w tym czasie są zgaszone. Nowa animacja =
wpis w `SAVERS` (`app/chocpilot/core/savers.py`, ramki jako tekst) + `firmware/tools/gen_savers.py`.

## Tryb Klipper (drukarki 3D)

ChocPilot może sterować drukarkami 3D z [Klipperem](https://www.klipper3d.org/) przez API
[Moonrakera](https://moonraker.readthedocs.io/) (to samo, którego używają Mainsail i Fluidd).
Konfiguracja: strona **Klipper** w aplikacji.

- **Drukarki:** nazwa, adres Moonrakera (np. `http://voron.local` albo `192.168.1.20:7125`),
  opcjonalny klucz API; przycisk *Testuj połączenie* pokazuje stan drukarki.
- **Włączanie trybu:** przytrzymaj przycisk pokrętła E2 (domyślnie 0,8 s; do wyboru E1 albo tylko
  akcja). Krótkie naciśnięcie tego pokrętła działa jak zwykle (wykonuje się po puszczeniu).
  Akcję **Tryb Klipper** (włącz / wyłącz / przełącz) można też przypisać do dowolnego klawisza.
- **W trybie Klipper:**
  - klawisze K1–K8 – polecenia z ustawień (każde z ikoną): G-code / makro, pauza / wznowienie,
    anuluj wydruk, awaryjne zatrzymanie, restart firmware, następna drukarka, wyjście. Domyślnie:
    Home, Pauza, PLA (stół 60 °C, dysza 200 °C), Stygnij, Silniki, Anuluj (przytrzymanie),
    Drukarka, STOP (przytrzymanie);
  - pokrętło E1 – ruch osi (naciśnięcie: X → Y → Z, krok i prędkość w ustawieniach; wymaga
    bazowania osi); w trakcie wydruku – Z offset w locie (`SET_GCODE_OFFSET Z_ADJUST`);
  - pokrętło E2 – temperatura dyszy / stołu, prędkość (M220), przepływ (M221), wentylator;
    naciśnięcie zmienia parametr;
  - suwak – wentylator chłodzenia albo prędkość wydruku 50–150 %;
  - ekran – w tytule nazwa drukarki, stan (postęp wydruku) i temperatury, w siatce ikony
    poleceń; nastawy pokazują się na chwilę na ekranie.
- Szybkie kręcenie pokrętłem wysyła tylko najnowszą nastawę (bez kolejki starych poleceń).
  Klucz API jest zapisywany w pliku konfiguracji aplikacji.

## Rozwiązywanie problemów

| Objaw | Co sprawdzić |
|---|---|
| Aplikacja „szuka ChocPilot…” | Kabel z transmisją danych (nie tylko ładowanie). Zamknij monitor portu PlatformIO (port może być zajęty). W Ustawieniach wybierz port ręcznie (Windows: `COMx`, macOS: `/dev/cu.usbmodem…`). Dziennik pokazuje próby. |
| Płytka nie pojawia się w systemie | Sprawdź **+5V** i **+3V3** (pcb/docs/ASSEMBLY.md, test 1) i lut USB-C. Płytka bez firmware zgłasza się tylko jako „STM32 BOOTLOADER” – wgraj firmware. |
| `flash.ps1` / `pio run -t upload`: brak urządzenia DFU | Windows: sterownik WinUSB dla „STM32 BOOTLOADER” (Zadig). Wejdź do bootloadera ręcznie: BOOT0 + RESET. |
| Pusty / biały ekran | Kabel PH2.0 do J2 (VCC na pin 1, kolejność 1:1), lut J2. W trybie testu (K1 + K4 przez 3 s po podłączeniu) ekran pokazuje stan klawiszy. |
| Obraz do góry nogami | Ustawienia → Urządzenie → **Obróć ekran o 180°**. |
| Polskie litery bez ogonków | To nie błąd: krój ekranu ma tylko ASCII. |
| Kilka klawiszy reaguje naraz | Odwrócona dioda albo brak diody; sprawdź w trybie testu sprzętu. |
| Klawisz „drga” | Zwiększ debounce (Ustawienia → Urządzenie). |
| Pokrętło działa odwrotnie | Kierunek w firmware: `kEncoderDir` w `firmware/src/boards/board.h`. |
| Przełączanie na okno programu nie działa | Windows czasem blokuje przejęcie fokusu (program i tak jest uruchamiany, gdy nie ma okna); macOS – uprawnienie Dostępność. |
| Skróty i tekst nic nie robią (macOS) | Uprawnienie **Dostępność** dla ChocPilot (po przebudowie aplikacji wyłącz i włącz je ponownie). |
| Głośność programu „nie gra” | Windows: program musi mieć aktywną sesję audio (widoczną w mikserze głośności). macOS: funkcja niedostępna. |
| SmartScreen / antywirus ostrzega o ChocPilot.exe | Plik nie jest podpisany; pynput (symulacja klawiatury) bywa oznaczany heurystycznie. Można uruchamiać z Pythona. |
| Akcje wykonują się podwójnie | Nie powinno: gdy aplikacja jest połączona, HID urządzenia jest wyłączony. Sprawdź, czy nie działają dwie kopie aplikacji (np. zbudowana i z Pythona). |
| Coś innego | Zakładka **Dziennik** w aplikacji albo `chocpilot.log` w katalogu konfiguracji. |

## Licencja

MIT.

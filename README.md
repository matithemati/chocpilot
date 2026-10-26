# ChocPilot

ChocPilot to przewodowy macropad z **8 niskoprofilowymi klawiszami Kailh Choc** (matryca 2×4)
i **ekranem OLED 2,42" (SSD1309, 128×64)** na **Arduino Pro Micro** (ATmega32U4), oraz aplikacja
na Windows, w której ustawiasz, co robi każdy klawisz.

Firmware jest „cienki”: skanuje klawisze, rysuje ekran i przechowuje kilka ustawień. Całą logikę
(gesty, akcje, profile) wykonuje aplikacja na PC. Komunikują się przez USB CDC protokołem
JSON Lines ([docs/PROTOCOL.md](docs/PROTOCOL.md)). Gdy aplikacja nie działa, urządzenie samo
wysyła zapisane skróty przez USB HID (tryb awaryjny).

Projekt powstał z kodu macropada Tap32 (3×3 MX + enkoder) – ChocPilot nie ma pokrętła.

```
firmware/   PlatformIO: środowiska promicro (5 V), promicro_3v3, native (testy)
app/        aplikacja Python 3.12+ (PySide6): rdzeń, GUI, symulator, testy
docs/       PROTOCOL.md, WIRING.md, schematic.png (schemat płytki)
```

## Funkcje

- **Gesty**: naciśnięcie, przytrzymanie (próg 500 ms), podwójne naciśnięcie (okno 300 ms).
- **Akcje**: uruchom program (albo przełącz na jego okno; przy kilku oknach kolejne naciśnięcia
  przechodzą między nimi), otwórz plik/folder, adres WWW,
  skrót klawiszowy (także Win, F13–F24), wpisz tekst (Unicode), multimedia, głośność
  systemu i pojedynczego programu, przewijanie, polecenie cmd/PowerShell, makro, zmiana
  profilu, warstwa (profil na czas trzymania klawisza), blokada komputera, wyłączenie ekranu.
- **Profile** z automatycznym przełączaniem według aktywnego okna (np. `obs64.exe` → „Stream”),
  import/eksport do JSON.
- **Ekran 128×64**: siatka etykiet 2×4 (jak klawisze) albo duża nazwa profilu, pasek głośności,
  etykieta po akcji, wygaszacz, znacznik online/offline, tryb testu sprzętu.
- **Tryb awaryjny HID**: po 3 s bez sygnału z aplikacji klawisze wysyłają skróty wyliczone
  z profilu (akcje „skrót” i „multimedia”); domyślnie dolny rząd: ciszej, głośniej,
  odtwarzaj/pauza, wycisz.

## Części

- 1× Arduino / SparkFun **Pro Micro** (ATmega32U4), 5 V/16 MHz albo 3,3 V/8 MHz
- 8× przełącznik **Kailh Choc** (low profile) + nasadki Choc, 8× dioda 1N4148
- 1× OLED **2,42" SSD1309 128×64 I²C** – moduł ShengYang, wersja **4-pinowa I²C**
  (70,10 × 48,10 mm, używana w projekcie); wersja 7-pinowa (72 × 43 mm) też pasuje do obudowy
  (`oled_variant`), ale wymaga przełożenia rezystorów z SPI na I²C.
  Szczegóły i karta sprzedawcy: [docs/WIRING.md](docs/WIRING.md#oled-242-ssd1309-12864-ic-złącze-j1)
- płytka ChocPilot (schemat: [docs/schematic.png](docs/schematic.png))

## Montaż

Pełny opis i tabela pinów: **[docs/WIRING.md](docs/WIRING.md)**. Najważniejsze:

1. Matryca **COL2ROW** 2×4: przy każdym przełączniku dioda 1N4148, **pasek (katoda) w stronę
   wiersza**. S1–S4 = klawisze K1–K4 (Row 0), S5–S8 = K5–K8 (Row 1).
2. OLED na złączu J1: GND, **+5 V**, SDA (pin 2 Pro Micro), SCL (pin 3). Sprawdź kolejność
   wyprowadzeń modułu – jeśli SDA i SCL są zamienione, firmware sam to wykryje (programowe I²C).
3. Uruchom tryb testu sprzętu (przytrzymaj **K1 + K4** zaraz po podłączeniu, przez 3 s) i sprawdź
   każdy klawisz.

## Firmware

Wymagania: [PlatformIO](https://platformio.org/) (VS Code + rozszerzenie albo `pip install platformio`).

```bash
cd firmware
pio run -e promicro
```

(`promicro` – Pro Micro 5 V/16 MHz, `promicro_3v3` – wersja 3,3 V/8 MHz.)

Platforma `atmelavr`, płytka `sparkfun_promicro16` (albo `sparkfun_promicro8`), rdzeń Arduino AVR:
USB CDC + HID (PluggableUSB, klawiatura i consumer control). Nazwa USB „ChocPilot”, VID/PID
z definicji płytki SparkFun: **1B4F:9206** (5 V) / **1B4F:9204** (3,3 V). Aplikacja szuka nazwy
„ChocPilot”, a zapasowo tych par oraz klonów z bootloaderem Leonardo/Micro (2341:8036 / 8037) –
nigdy PID-ów bootloadera Caterina (bajty `hello` byłyby dla niego komendami).

ATmega32U4 ma **2,5 KB RAM i 28 KB flash** (z bootloaderem Caterina). Zużycie (sprawdzone
2026-10, `pio run -e promicro`): **flash 25 974 B / 28 672 B (90,6 %)**, **RAM statycznie
1 958 B / 2 560 B (76,5 %)** – reszta to stos (bufor pasa ekranu, parser). Dlatego:

- **Ekran**: zamiast grafiki U8g2 z czcionkami – mini-renderer (`firmware/src/mini_gfx.cpp`)
  na sterowniku U8x8 (SSD1309 `noname2`): jeden krój **5×7 ASCII** w skali 1×–3×, pogrubiony
  i wąski (6 znaków w komórce siatki). **Polskie litery tracą ogonki** (ą → a, Ł → L).
  Podgląd w aplikacji rysuje dokładnie te same piksele.
- **I²C**: sprzętowy TWI 400 kHz (własna obsługa rejestrów, bez biblioteki Wire); gdy ekran
  odpowiada dopiero po zamianie SDA/SCL – programowe I²C na zamienionych pinach.
- **Protokół**: kodek bez bibliotek JSON (czyta linię w miejscu, bez alokacji). Maksymalna linia
  do urządzenia to **272 B** (`max_line` w `hello`); aplikacja sama dzieli dłuższe `set_fallback`.
- **Bufory**: tytuł do 21 znaków ASCII (22 B), etykieta do 10 znaków (12 B) – wielobajtowe UTF-8
  skraca się wcześniej.
- **Ustawienia** w EEPROM jako blok binarny z CRC. Zapis nie jest atomowy: przerwany odłączeniem
  zasilania kończy się wartościami domyślnymi.
- **Brak diody statusu** (RX/TX LED steruje rdzeń USB; stan widać na ekranie).

### Wgrywanie

Skrypt `firmware\flash.ps1` znajduje PlatformIO (PATH, `%USERPROFILE%\.platformio`, a w razie
potrzeby instaluje go przez pip), sprawdza, czy aplikacja nie trzyma portu, kompiluje i wgrywa:

```powershell
cd firmware
.\flash.ps1
```

Opcje: `-Board 3v3` (Pro Micro 3,3 V/8 MHz), `-Port COM7` (konkretny port), `-BuildOnly`
(tylko kompilacja, wynik w `.pio\build\promicro\firmware.hex`), `-CloseApp` (zamyka działającą
aplikację ChocPilot). Bez skryptu: `pio run -e promicro -t upload`.

Najpierw zamknij aplikację ChocPilot (trzyma port COM). PlatformIO otwiera port z prędkością
1200 bps („1200 bps touch”), płytka restartuje się do bootloadera **Caterina** (osobny port COM
na ok. 8 s, potem wraca do programu) i avrdude wgrywa firmware. Menu aplikacji
**Urządzenie → Tryb wgrywania firmware** też przełącza do Caterina (firmware wpisuje „magiczny
klucz” i restartuje się watchdogiem) – przydatne przy wgrywaniu ręcznym avrdude w ciągu tych 8 s.
Gdy firmware nie działa: zewrzyj dwa razy szybko **RST** z **GND** i od razu wgrywaj.

### Testy firmware (na PC)

Parser protokołu, debounce, kody HID i zapis konfiguracji mają testy jednostkowe w środowisku
`native`. Potrzebny jest kompilator gcc/g++ w PATH (Windows: MSYS2/MinGW-w64; najprościej
`pio pkg install -g -t platformio/toolchain-gccmingw32` i dodanie
`%USERPROFILE%\.platformio\packages\toolchain-gccmingw32\bin` do PATH).

```bash
pio test -e native
```

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
| `--simulate` | zamiast urządzenia uruchamia **symulator** (okno z 8 klawiszami 2×4 i podglądem OLED 128×64) |
| `--minimized` | start w zasobniku |
| `--config PLIK` | inny plik konfiguracji |
| `--verbose` | dziennik na konsoli |

Konfiguracja: `%APPDATA%\ChocPilot\config.json` (zapis atomowy, poprzednia wersja
w `config.json.bak`, dziennik w `chocpilot.log`). Uszkodzony plik jest odkładany jako
`config.broken.json`, a aplikacja wczytuje kopię zapasową.

Obsługa:

- Lista profili po lewej (dwuklik = aktywuj). Kliknij klawisz na podglądzie, aby edytować;
  przyciski **Testuj** wykonują akcję od razu. Fizyczne naciśnięcia podświetlają klawisze.
- **Plik → Ustawienia**: port (auto/ręczny), jasność, wygaszacz, tryb ekranu, obrót, progi gestów,
  debounce, skróty trybu awaryjnego, autostart z Windows, start zminimalizowany, motyw.
- Zamknięcie okna chowa aplikację do zasobnika (kolor ikony = stan połączenia). Z zasobnika:
  zmiana profilu, **Wstrzymaj akcje**, wyjście. Uruchamia się tylko jedna instancja.

### Testy i jakość

```bash
cd app
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check chocpilot tests
.venv\Scripts\python -m ruff format --check chocpilot tests
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
chocpilot/core/gestures.py    tap / hold / double_tap (czysta logika, czas z zewnątrz)
chocpilot/core/actions/       rejestr typów akcji, wbudowane akcje, wykonawca (pula wątków)
chocpilot/core/config.py      modele pydantic, migracje schema_version, zapis atomowy, import/eksport
chocpilot/core/profiles.py    aktywny profil, warstwy, automatyczne przełączanie
chocpilot/core/engine.py      kontroler: zdarzenia → gesty → akcje; profil → display + set_fallback
chocpilot/platform/           kod zależny od systemu (windows.py; base.py = interfejs dla Linux/macOS)
chocpilot/gui/                PySide6: okno główne, edytory, ustawienia, zasobnik, symulator
chocpilot/gui/oled.py         podgląd OLED 128×64 – ten sam krój i układ co firmware
```

Nowy typ akcji: klasa dziedzicząca po `ActionBase` z polem `type: Literal["nazwa"]`, metodą
`run(ctx)` i dekoratorem `@register_action("nazwa", "Etykieta")`. Formularz w GUI tworzy się
automatycznie z pól modelu.

## Obudowa (OpenSCAD)

`case/chocpilot_case.scad` – obudowa **93,5 × 99,6 × 20 mm** z płaską górą, symetryczna względem klawiszy i ekranu (lewa ścianka grubsza o tyle, o ile PCB wystaje w prawo pod Pro Micro), dopasowana do
kompaktowej płytki z KiCad (`esp_macropad/pcb/tap32/tap32.kicad_pcb`, podgląd:
[docs/img/pcb_compact.png](docs/img/pcb_compact.png)): obrys 79,5 × 88,75 mm, rzędy klawiszy
67 mm od siebie, ekran 2,42" poziomo dokładnie pośrodku (ten sam odstęp od obu rzędów).
Moduł OLED wisi 2 mm nad płytką, przykręcony od spodu do płyty obudowy (4× M2,5×4); szkło leży
w otworze 0,4 mm poniżej powierzchni – nic nie wystaje. Płytka leży na 5 słupkach dna (M3),
Pro Micro od spodu (wystaje 1,9 mm poza PCB – kieszeń w prawej ściance), USB wychodzi prawą
ścianką. Skorupa drukuje się górą w dół bez podpór.

Pod modułem musi być płasko (2 mm wolnego miejsca):

- wkręty płytki **M3 z niskim łbem** (ISO 7380 / „button head”, łeb 1,65 mm) – wszystkie
  otwory H1–H5 leżą pod modułem,
- piny Pro Micro od góry płytki **przycięte równo z lutem**,
- moduł połączony **przewodami** (cienkie, np. AWG 28–30) z polami J1 – bez złącza XH;
  złącze na dolnej krawędzi modułu 4-pinowego (od spodu) zdejmij, jeśli jest wyższe niż 2 mm.

```bash
openscad -D part=\"shell\" -o chocpilot_shell.stl case/chocpilot_case.scad
```

```bash
openscad -D part=\"bottom\" -o chocpilot_bottom.stl case/chocpilot_case.scad
```

Części: `shell`, `bottom`; podgląd: `assembly`, `exploded`.

**Moduł OLED:** ShengYang 2,42", wersja wybierana parametrem `oled_variant` – `i2c_4pin`
(domyślnie, 70,10 × 48,10 mm) albo `spi_7pin` (72 × 43 mm). Wymiary płytek są z karty
sprzedawcy, ale rozstaw otworów (ok. 3 mm od krawędzi) i położenie szkła są oszacowane –
**zmierz moduł przed drukiem**. Plik sprawdza asercjami przy renderowaniu, że szkło nie
wystaje, moduł nie nachodzi na przełączniki i że wokół wkrętów modułu zostaje materiał płyty
(1,6 mm do otworów na klawisze, 1,2 mm do otworu na szkło). Zakładany jest też
montaż Pro Micro od spodu płytki (elementy w dół) – przy montażu od góry trzeba zmienić
`standoff_h`, wycięcie USB i miejsce pod modułem.

## Rozwiązywanie problemów

| Objaw | Co sprawdzić |
|---|---|
| Aplikacja „szuka ChocPilot…” | Kabel z transmisją danych (nie tylko ładowanie). Zamknij monitor portu PlatformIO/Arduino IDE (port może być zajęty). W Ustawieniach wybierz port ręcznie. Dziennik pokazuje próby. |
| Wgrywanie kończy się błędem / brak portu | Dwa razy szybko zewrzyj RST z GND i od razu uruchom `pio run -e promicro -t upload`. Klon z bootloaderem Leonardo ma VID 2341 – aplikacja też go znajdzie (PID 8036/8037). |
| Pusty ekran | Spójrz na pasek stanu aplikacji: **OLED: 0x3C/0x3D** = ekran odpowiada (adres wybierany automatycznie), **OLED: brak** = nic nie odpowiada na I²C – sprawdź zasilanie +5 V, GND, czy moduł 2,42" jest ustawiony na I²C (nie SPI) i lutowanie. Lista znalezionych urządzeń jest w zakładce Dziennik. |
| Ekran odpowiada, ale obraz jest przesunięty / śmieci | Niektóre moduły SSD1309 potrzebują innego wariantu sterownika: w `firmware/src/mini_gfx.cpp` zamień `u8x8_d_ssd1309_128x64_noname2` na `..._noname0`. |
| Polskie litery bez ogonków | To nie błąd: firmware ma tylko krój ASCII (brak miejsca na czcionki). |
| Kilka klawiszy reaguje naraz | Odwrócona dioda albo brak diody; sprawdź w trybie testu sprzętu. |
| Klawisz „drga” | Zwiększ debounce (Ustawienia → Urządzenie). |
| Przełączanie na okno programu nie działa | Windows czasem blokuje przejęcie fokusu; program i tak jest uruchamiany, gdy nie ma okna. |
| Głośność programu „nie gra” | Program musi mieć aktywną sesję audio (widoczną w mikserze głośności). |
| SmartScreen / antywirus ostrzega o ChocPilot.exe | Plik nie jest podpisany; pynput (symulacja klawiatury) bywa oznaczany heurystycznie. Można uruchamiać z Pythona. |
| Akcje wykonują się podwójnie | Nie powinno: gdy aplikacja jest połączona, HID urządzenia jest wyłączony. Sprawdź, czy nie działają dwie kopie aplikacji (np. exe i python). |

## Licencja

MIT.

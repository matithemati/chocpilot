# Protokół ChocPilot (wersja 1)

Urządzenie ChocPilot i aplikacja na PC komunikują się przez **USB CDC** (wirtualny port
szeregowy, prędkość bez znaczenia – transmisja jest natywna USB). Format: **JSON Lines** –
każda wiadomość to jeden obiekt JSON zakończony znakiem `\n` (`\r` przed `\n` jest
ignorowany). Kodowanie: UTF-8.

Wspólne zasady:

- Każda wiadomość ma pole `type` (string).
- Nieznane pola są **ignorowane** (kompatybilność wsteczna). Nieznane typy wiadomości
  również są ignorowane (bez odpowiedzi, nawet jeśli mają `id`).
- Maksymalna długość linii wysyłanej do urządzenia: wartość `max_line` z `hello` – w ChocPilot
  **272 bajty** (łącznie z `\n`; brak pola = 1024). Dłuższa linia jest odrzucana w całości,
  urządzenie odpowiada `{"type":"error","msg":"line too long"}` bez `id`.
- Niepoprawny JSON (lub brak `type`) → `{"type":"error","msg":"..."}` (bez `id`);
  urządzenie nie zawiesza się i czeka na kolejną linię.
- Czasy `t` to milisekundy od startu urządzenia (`millis()`, uint32, przepełnia się po ~49 dniach).

## Urządzenie → PC

### `hello`
```json
{"type":"hello","device":"chocpilot","fw":"1.2.0","board":"chocpilot","keys":8,"encoder":true,"hid":true,"online":false,"leds":12,"icon":32,"savers":["rabbit","corgi"],"max_line":272}
```
- `board`: `"chocpilot"` – płytka ChocPilot (STM32F072, LCD 2" IPS, 2 pokrętła, suwak, 12 LED).
  Firmware sprzed porządków (≤ 1.1.0) wysyłał `"chocpilot_v0"` – aplikacja używa tego pola tylko
  do wyświetlenia nazwy, możliwości płytki odczytuje z pól poniżej.
- `keys`: liczba klawiszy – 8 (matryca 2×4). `encoder`: `true` – płytka wysyła też `encoder`,
  `encoder_key` i `slider`.
- `hid`: urządzenie ma interfejs HID (tryb awaryjny).
- `leds`: liczba diod podświetlenia (`12`); brak pola = bez LED – aplikacja nie wysyła wtedy `leds`.
- `icon`: rozmiar ikon klawiszy (`32`); brak pola = tylko etykiety.
- `savers`: nazwy animacji wygaszacza wbudowanych w firmware (`["rabbit","corgi"]`);
  brak pola = tylko wygaszony ekran. Aplikacja buduje z tej listy wybór w ustawieniach, więc nowe
  animacje w firmware nie wymagają zmian aplikacji.
- `online` (informacyjnie): czy urządzenie uważa aplikację za połączoną.
- `max_line`: maksymalna długość linii do urządzenia w bajtach, łącznie z `\n` (ChocPilot: 272).
  Aplikacja dzieli dłuższe `set_fallback` na kilka wiadomości (pierwsza z `replace: true`, kolejne
  z `replace: false`). Tytuły i etykiety są w urządzeniu skracane do 21 / 11 bajtów UTF-8, a ekran
  pokazuje tylko ASCII (polskie litery bez ogonków).

Wysyłane: po starcie, w odpowiedzi na `hello` od PC i na `get_info`.

### `key`
```json
{"type":"key","key":3,"action":"down","t":123456}
```
- `key`: 1–8 (K1…K4 – górny rząd, K5…K8 – dolny).
- `action`: `"down"` | `"up"` (po debounce).

### `encoder`, `encoder_key`, `slider`
```json
{"type":"encoder","index":1,"delta":-2,"t":123456}
{"type":"encoder_key","index":1,"action":"down","t":123460}
{"type":"slider","value":42,"t":123500}
```
- `encoder`: pokrętło `index` (1 – górne, 2 – dolne) obrócone o `delta` zatrzasków
  (dodatnie = w prawo). Szybki obrót może dać |delta| > 1.
- `encoder_key`: przycisk pokrętła, `action` `"down"` | `"up"` (po debounce).
- `slider`: położenie suwaka 0–100 (0 = dół). Wysyłane przy zmianie (histereza ok. 0,7 %,
  nie częściej niż co 20 ms) i raz po starcie.

Wysyłane zawsze, także offline. Aplikacja ChocPilot wykonuje dla nich akcje z profilu
(pokrętło: `cw` / `ccw` × |delta|, `press` przy `down`; suwak: głośność systemu / programu);
starsza wersja aplikacji ignoruje je jako nieznane typy.
**Offline** (tryb awaryjny HID) pokrętło 1 wysyła głośniej / ciszej, a jego przycisk – wycisz.

### `ack` / `error`
```json
{"type":"ack","id":7}
{"type":"error","id":7,"msg":"value out of range"}
{"type":"error","msg":"invalid json"}
```
Odpowiedź na wiadomość z polem `id` (liczba całkowita). `error` bez `id` – błąd parsowania.

### `log`
```json
{"type":"log","level":"info","msg":"settings saved"}
```
Tylko w trybie debug (`{"type":"debug","enable":true}`). `level`: `debug` | `info` | `warn` | `error`.

### `test`
```json
{"type":"test","active":true}
```
Informuje o wejściu/wyjściu z trybu testu sprzętu.

## PC → urządzenie

Pole `id` jest opcjonalne w każdej wiadomości. Jeśli występuje, urządzenie odpowiada
`ack` (sukces) albo `error` (błąd walidacji).

### `hello`
```json
{"type":"hello","app":"1.2.0"}
```
Urządzenie odpowiada `hello` i przechodzi w stan **online**.

### `ping`
```json
{"type":"ping"}
```
Wysyłany przez aplikację **co 1 s**. Każda poprawna wiadomość od PC odświeża licznik
heartbeat, ale aplikacja musi wysyłać `ping`, gdy nie ma nic innego do wysłania.
**Brak wiadomości przez 3 s → urządzenie przechodzi w tryb offline** (patrz niżej).

### `get_info`
```json
{"type":"get_info"}
```
Urządzenie odpowiada `hello`.

### `display`
Ustawia główny tryb ekranu. Tryby `profile` i `grid` są trwałe (zapamiętywane w pamięci
urządzenia). Tryby z polem `ms` (`text`, `bar`) są chwilowe – po `ms` ekran wraca do
poprzedniego trybu trwałego.

```json
{"type":"display","mode":"profile","name":"Stream"}
{"type":"display","mode":"grid","title":"Domyślny","labels":["Kalk","Notes","Kopiuj","Wklej","Głos -","Głos +","Play","Wycisz"]}
{"type":"display","mode":"text","line1":"Hello","line2":"world","ms":2000}
{"type":"display","mode":"bar","title":"Głośność","value":42,"ms":1500}
```
| Pole | Tryb | Limit |
|---|---|---|
| `name` | profile | 21 znaków |
| `title` | grid, bar | 21 znaków |
| `labels` | grid | 8 napisów (K1–K8), każdy do **10 znaków**; brakujące = puste. Na ekranie: do 6 znaków w wierszu, dłuższe w 2 wierszach (podział na spacji) |
| `line1`, `line2` | text | po 21 znaków |
| `value` | bar | 0–100 (przycinane) |
| `ms` | text, bar | 0 = bez limitu (tryb staje się trwały, ale nie jest zapisywany) |

Dłuższe napisy są obcinane. Krój urządzenia obsługuje ASCII; znaki spoza ASCII
aplikacja **transliteruje** (ą→a, ł→l, …) przed wysłaniem (firmware robi to samo dla polskich liter).

### `flash`
```json
{"type":"flash","key":3,"text":"Spotify","ms":1200}
```
Chwilowy duży napis (np. po wykonaniu akcji). `key` (opcjonalny) wyświetlany jest małym
znacznikiem `K3`. `ms` domyślnie 1000, maks. 10000.

### `settings`
Częściowa aktualizacja ustawień (podaj tylko zmieniane pola). Ustawienia są zapisywane
w pamięci nieulotnej.

```json
{"type":"settings","id":3,"brightness":128,"screensaver_s":300,"flip":false,"debounce_ms":8}
```
| Pole | Typ | Zakres | Domyślnie |
|---|---|---|---|
| `brightness` | int | 0–255 – podświetlenie LCD (PWM); jasność diod ustawia `leds` | 128 |
| `screensaver_s` | int | 0–65535, 0 = wyłączony | 300 |
| `flip` | bool | obrót ekranu o 180° | false |
| `debounce_ms` | int | 1–50 | 8 |
| `saver` | string | animacja wygaszacza z listy `savers` w `hello`, `"off"` = wygaszony ekran (nazwa: a–z, 0–9, `_`, do 11 znaków; nieznana = wygaszony ekran) | `"off"` |

Wartość poza zakresem lub złego typu → `error`, żadne pole z tej wiadomości nie jest zapisywane.

### `leds`
Podświetlenie LED. Wszystkie pola opcjonalne – zmieniane są tylko podane. Ustawienia są zapisywane
w pamięci nieulotnej i działają też bez aplikacji (tryb offline).

```json
{"type":"leds","id":4,"mode":"breathe","color":"#00a0c0","brightness":128,"speed":5,"react":true}
{"type":"leds","color":"#ff1744","save":false}
```
| Pole | Typ | Zakres | Domyślnie |
|---|---|---|---|
| `mode` | string | `off`, `status` (online turkus / offline bursztyn), `static`, `breathe`, `rainbow` | `status` |
| `color` | string | `#RRGGBB` – kolor trybów `static` i `breathe` | `#00a0c0` |
| `brightness` | int | 0–255; 255 = ok. 1/3 pełnej mocy diod (ok. 230 mA przy bieli – limit USB) | 128 |
| `speed` | int | 1–10 – tempo oddychania (6 s … 1 s) i tęczy (12 s … 1,7 s) | 5 |
| `react` | bool | dioda przy naciśniętym klawiszu rozbłyska bielą i gaśnie w 0,4 s | true |
| `save` | bool | `false` = tylko do rozłączenia / restartu, bez zapisu (kolor profilu, podgląd) | true |

- Wygaszacz ekranu gasi też diody; tryb testu pokazuje kolejno czerwony, zielony, niebieski, biały.
- Po przejściu w tryb offline urządzenie wraca do zapisanych ustawień (bez zmian z `save:false`).
- Aplikacja po połączeniu wysyła pełne ustawienia, a potem kolor aktywnego profilu z `save:false`
  – przełączanie profili nie zużywa pamięci flash.

### `icon`
Ikona klawisza na ekranie LCD zamiast etykiety: 32 × 32 px, 544 B = paleta 16 kolorów RGB565
big-endian (32 B) + piksele po 4 bity (512 B, starszy półbajt = lewy piksel). Urządzenie rysuje ją
w skali 2 w kafelku siatki. Wysyłana w kawałkach po kolei (offset 0, 128, 256, 384, 512), dane
w base64 (≤ 128 B na komendę – mieści się w `max_line`). Ikony są tylko w RAM – po restarcie
urządzenia wracają etykiety, aż aplikacja wyśle ikony ponownie.

```json
{"type":"icon","key":3,"offset":0,"data":"CIMIgwiD..."}
{"type":"icon","key":3,"clear":true}
```
Kawałek z `offset` 0 zaczyna nową ikonę; zgubiony kawałek (offset ≠ dotychczas zapisanym bajtom)
jest pomijany, a ikona czeka na ponowne wysłanie od początku.

### `time`
Czas lokalny dla zegara HH:MM na wygaszaczu z animacją. Płytka nie ma zegara z baterią – po
`time` liczy dalej sama (do restartu). Aplikacja wysyła `time` po połączeniu i co 5 minut
(zmiana czasu letniego, dryf). Bez `time` wygaszacz pokazuje samą animację.

```json
{"type":"time","hour":14,"minute":5,"second":30}
```
`hour` 0–23, `minute` 0–59 (wymagane), `second` 0–59 (opcjonalne).

### `set_fallback`
Skróty HID dla trybu awaryjnego (offline). Można wysłać pojedyncze przypisanie albo listę:

```json
{"type":"set_fallback","key":1,"mods":["ctrl","shift"],"code":"c"}
{"type":"set_fallback","key":8,"media":"mute"}
{"type":"set_fallback","replace":true,"bindings":[
  {"key":5,"media":"vol_down"},
  {"key":6,"media":"vol_up"},
  {"key":8,"media":"mute"},
  {"key":2,"mods":["ctrl"],"code":"v"}
]}
```
- `key`: 1–8.
- `mods`: lista z `ctrl`, `shift`, `alt`, `win` (alias `gui`, `meta`), opcjonalnie z prefiksem
  `r` dla prawego (`rctrl`, `rshift`, `ralt`, `rwin`).
- `code`: nazwa klawisza (patrz niżej) albo liczba – surowy kod HID Usage (Keyboard page 0x07).
- `media`: `play_pause`, `next`, `prev`, `stop`, `vol_up`, `vol_down`, `mute`.
- Przypisanie bez `code` i `media` (oraz bez `mods`) usuwa skrót klawisza.
- `replace: true` czyści wszystkie przypisania przed zastosowaniem listy.

Nazwy klawiszy (`code`): `a`–`z`, `0`–`9`, `f1`–`f24`, `enter`, `esc`, `backspace`, `tab`,
`space`, `minus`, `equal`, `lbracket`, `rbracket`, `backslash`, `semicolon`, `quote`,
`grave`, `comma`, `period`, `slash`, `capslock`, `printscreen`, `scrolllock`, `pause`,
`insert`, `home`, `pageup`, `delete`, `end`, `pagedown`, `right`, `left`, `down`, `up`,
`numlock`, `kp_0`–`kp_9`, `kp_plus`, `kp_minus`, `kp_multiply`, `kp_divide`, `kp_enter`,
`kp_period`, `menu`. Pojedyncze znaki `-` `=` `[` `]` `\` `;` `'` `` ` `` `,` `.` `/` też są akceptowane.

Domyślne przypisania (gdy nic nie zapisano): K5 = `vol_down`, K6 = `vol_up`,
K7 = `play_pause`, K8 = `mute`, klawisze 1–4 bez przypisania.

### `reboot`
```json
{"type":"reboot"}
{"type":"reboot","bootloader":true}
```
`bootloader: true`: skok do bootloadera USB DFU w ROM STM32 (urządzenie „STM32 BOOTLOADER”
0483:DF11; wgrywanie `firmware/flash.ps1` albo `pio run -t upload`, po wgraniu płytka sama
uruchamia program). Urządzenie wysyła `ack` (jeśli było `id`) przed restartem.

### `test_mode`
```json
{"type":"test_mode","enable":true}
```
Włącza/wyłącza tryb testu sprzętu (ekran na żywo pokazuje stan 8 klawiszy, obroty i przyciski
pokręteł oraz położenie suwaka; diody LED świecą kolejno R, G, B, biały).
Tryb można też włączyć, trzymając **K1 + K4 przez 3 s zaraz po starcie**; wyłączyć – komendą
albo ponownym przytrzymaniem K1 + K4 przez 3 s.

### `debug`
```json
{"type":"debug","enable":true}
```
Włącza wysyłanie wiadomości `log`.

## Tryb online / offline (heartbeat)

| Stan | Warunek | Zachowanie |
|---|---|---|
| offline (start) | brak `hello`/`ping` od startu | ekran „Offline / Czekam na aplikację…”, HID aktywny |
| online | odebrano poprawną wiadomość w ciągu ostatnich 3 s | HID **wyłączony**, ekran wg `display` |
| offline | brak wiadomości przez 3 s | HID wysyła skróty `set_fallback`, ekran „Offline” |

Zdarzenia `key` są wysyłane **zawsze**, także offline. Przy przejściu offline → online
urządzenie zwalnia wszystkie wciśnięte klawisze HID (brak „zawieszonych” klawiszy i zdublowanych akcji).

## Przykładowa sesja

```
PC  → {"type":"hello","app":"1.2.0"}
DEV → {"type":"hello","device":"chocpilot","fw":"1.2.0","board":"chocpilot","keys":8,"encoder":true,"hid":true,"online":true,"leds":12,"icon":32,"savers":["rabbit","corgi"],"max_line":272}
PC  → {"type":"settings","id":1,"brightness":200}
DEV → {"type":"ack","id":1}
PC  → {"type":"display","mode":"grid","title":"Domyslny","labels":["Kalk","Notes","Kopiuj","Wklej","Glos -","Glos +","Play","Wycisz"]}
DEV → {"type":"key","key":1,"action":"down","t":5021}
DEV → {"type":"key","key":1,"action":"up","t":5130}
PC  → {"type":"flash","key":1,"text":"Kalk","ms":800}
DEV → {"type":"key","key":6,"action":"down","t":6000}
DEV → {"type":"key","key":6,"action":"up","t":6090}
PC  → {"type":"display","mode":"bar","title":"Glosnosc","value":54,"ms":1500}
PC  → {"type":"ping"}
```

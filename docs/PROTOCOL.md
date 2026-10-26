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
{"type":"hello","device":"chocpilot","fw":"1.0.0","board":"promicro","keys":8,"encoder":false,"hid":true,"online":false,"max_line":272}
```
- `board`: `"promicro"` (Arduino Pro Micro, ATmega32U4).
- `keys`: liczba klawiszy – 8 (matryca 2×4). `encoder`: zawsze `false` (ChocPilot nie ma pokrętła).
- `hid`: urządzenie ma interfejs HID (tryb awaryjny).
- `online` (informacyjnie): czy urządzenie uważa aplikację za połączoną.
- `oled`: adres I²C, pod którym odpowiada ekran (np. `60` = 0x3C), albo `null`, gdy ekran nie
  odpowiada. Firmware przy starcie sam wybiera 0x3C lub 0x3D, jeśli ustawiony adres nie odpowiada.
- `i2c`: lista adresów wszystkich urządzeń znalezionych na magistrali I²C (maks. 8).
- `lines`: `{"sda":0|1,"scl":0|1}` – stan linii zmierzony przy starcie bez wewnętrznego
  podciągania (1 = moduł zasilony i ma pull-upy).
- `swapped`: `true`, gdy ekran odpowiedział dopiero po zamianie SDA i SCL (firmware obsługuje go
  wtedy programowym I²C na zamienionych pinach).
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
{"type":"hello","app":"1.0.0"}
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
| `brightness` | int | 0–255 (kontrast OLED) | 128 |
| `screensaver_s` | int | 0–65535, 0 = wyłączony | 300 |
| `flip` | bool | obrót ekranu o 180° | false |
| `debounce_ms` | int | 1–50 | 8 |
| `oled_addr` | int | adres I²C OLED (0x3C / 0x3D), działa po restarcie | 0x3C |

Wartość poza zakresem lub złego typu → `error`, żadne pole z tej wiadomości nie jest zapisywane.

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
`bootloader: true`: restart do bootloadera Caterina na ok. 8 s (nowy port COM, wgrywanie
avrdude / `pio run -e promicro -t upload`). Urządzenie wysyła `ack` (jeśli było `id`) przed
restartem.

### `test_mode`
```json
{"type":"test_mode","enable":true}
```
Włącza/wyłącza tryb testu sprzętu (ekran na żywo pokazuje stan 8 klawiszy).
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
PC  → {"type":"hello","app":"1.0.0"}
DEV → {"type":"hello","device":"chocpilot","fw":"1.0.0","board":"promicro","keys":8,"encoder":false,"hid":true,"online":true,"max_line":272}
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

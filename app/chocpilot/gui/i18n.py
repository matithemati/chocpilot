# ruff: noqa: E501
"""Tłumaczenie interfejsu PL → EN.

Teksty w kodzie są po polsku; tr() zwraca angielski odpowiednik, gdy wybrano język „en”.
Brak wpisu w słowniku = tekst bez zmian (np. nazwy własne).
"""

from __future__ import annotations

from ..core.actions import ActionBase, format_hotkey, parse_hotkey
from ..core.osinfo import current_os

_language = "pl"

EN: dict[str, str] = {
    # nawigacja i okno główne
    "Konfiguracja": "Configuration",
    "Dziennik": "Log",
    "Ustawienia": "Settings",
    "Ustawienia…": "Settings…",
    "Profile": "Profiles",
    "Profil": "Profile",
    "Nowy profil": "New profile",
    "Importuj profil…": "Import profile…",
    "Eksportuj profil…": "Export profile…",
    "Importuj profil": "Import profile",
    "Eksportuj profil": "Export profile",
    "Zamknij okno (działa w tle)": "Close window (keep running in background)",
    "O programie": "About",
    "Zakończ": "Quit",
    "Menu aplikacji": "App menu",
    "Menu urządzenia": "Device menu",
    "Język": "Language",
    "Połączono": "Connected",
    "Rozłączono": "Disconnected",
    "Szukam ChocPilot…": "Looking for ChocPilot…",
    "Płytka": "Board",
    "Aktywny profil": "Active profile",
    "Tryb testu sprzętu": "Hardware test mode",
    "Wyślij ponownie ekran i ustawienia": "Resend display and settings",
    "Restart urządzenia": "Restart device",
    "Tryb wgrywania firmware…": "Firmware upload mode…",
    "Tryb wgrywania firmware": "Firmware upload mode",
    "domyślny": "default",
    "Aktywny": "Active",
    "Domyślny": "Default",
    "Ustaw jako aktywny": "Set as active",
    "Właściwości profilu": "Profile properties",
    "Więcej akcji profilu": "More profile actions",
    "Dodaj": "Add",
    "Duplikuj": "Duplicate",
    "Zmień nazwę": "Rename",
    "Eksportuj…": "Export…",
    "Usuń": "Delete",
    "Akcje włączone": "Actions on",
    "Akcje wstrzymane": "Actions paused",
    "Akcje wstrzymane.": "Actions paused.",
    "Naciśnięcia klawiszy nie wykonują akcji.": "Key presses do not run any actions.",
    "Wznów": "Resume",
    "Naciśnięcia tylko podświetlają elementy na podglądzie.": "Presses only highlight items in the preview.",
    "Wyłącz": "Turn off",
    "Kliknij klawisz, aby edytować akcje. Fizyczne naciśnięcia podświetlają elementy na żywo.": "Click a key to edit its actions. Physical presses highlight items live.",
    "Automatycznie dla:": "Automatic for:",
    "Nazwa profilu:": "Profile name:",
    "Nowa nazwa:": "New name:",
    "Profil „{name}” już istnieje.": "Profile “{name}” already exists.",
    "Musi zostać co najmniej jeden profil.": "At least one profile must remain.",
    "Usunąć profil „{name}”?": "Delete profile “{name}”?",
    "Profil ChocPilot (*.json)": "ChocPilot profile (*.json)",
    "Nie udało się zaimportować profilu:": "Could not import the profile:",
    "Nie udało się zapisać:": "Could not save:",
    "Przełączyć urządzenie w tryb wgrywania firmware?\nPłytka odłączy się od aplikacji i uruchomi bootloader USB DFU (STM32 BOOTLOADER). Wgraj firmware (firmware/flash.ps1 albo pio run -t upload) – po wgraniu płytka sama wróci do pracy.": "Switch the device to firmware upload mode?\nThe board disconnects from the app and starts the USB DFU bootloader (STM32 BOOTLOADER). Upload the firmware (firmware/flash.ps1 or pio run -t upload) – the board restarts on its own afterwards.",
    'Macropad 2×4 (Kailh Choc) z ekranem LCD 2" IPS, pokrętłami i suwakiem.': '2×4 macropad (Kailh Choc) with a 2" IPS LCD, encoders and a slider.',
    "Błąd": "Error",
    # podgląd urządzenia
    "Wybierz ikonę": "Choose an icon",
    "Szukaj (np. play, folder, kot, music)…": "Search (e.g. play, folder, cat, music)…",
    "Wszystkie": "All",
    "Folder własnych ikon": "Custom icons folder",
    "Odśwież": "Refresh",
    "Bez ikony": "No icon",
    "Wybierz": "Choose",
    "ikon": "icons",
    "Nie wybrano ikony": "No icon selected",
    "Dodaj pliki PNG/SVG do tego folderu, a potem kliknij Odśwież – pojawią się jako Własne.": "Add PNG/SVG files to this folder, then click Refresh – they appear under Custom.",
    "Ikona na ekranie (zamiast etykiety)": "Icon on screen (instead of the label)",
    "Wybierz ikonę…": "Choose icon…",
    "Usuń ikonę": "Remove icon",
    "Brak – na ekranie etykieta": "None – the label is shown",
    "Edycja": "Editing",
    "Programy": "Apps",
    "Streaming": "Streaming",
    "Druk 3D": "3D printing",
    "Symbole": "Symbols",
    "Emoji": "Emoji",
    "Własne": "Custom",
    "Tryb Klipper": "Klipper mode",
    "Klawisze, pokrętła i suwak sterują drukarką 3D.": "Keys, knobs and the slider control the 3D printer.",
    "Sterowanie drukarkami 3D z Klipperem (przez Moonraker) z klawiszy, pokręteł i suwaka ChocPilot.": "Control Klipper 3D printers (through Moonraker) with ChocPilot's keys, knobs and slider.",
    "Włącz tryb Klipper": "Turn on Klipper mode",
    "Wyłącz tryb Klipper": "Turn off Klipper mode",
    "Drukarki": "Printers",
    "Adres Moonrakera, np. http://voron.local albo 192.168.1.20:7125. Klucz API tylko, jeśli Moonraker go wymaga (Mainsail/Fluidd: Ustawienia → Klucz API).": "Moonraker address, e.g. http://voron.local or 192.168.1.20:7125. API key only if Moonraker requires one (Mainsail/Fluidd: Settings → API key).",
    "(opcjonalny)": "(optional)",
    "Klucz API": "API key",
    "Dodaj drukarkę": "Add printer",
    "Testuj połączenie": "Test connection",
    "Łączenie…": "Connecting…",
    "Brak danych – włącz tryb Klipper albo przetestuj połączenie.": "No data – turn on Klipper mode or test the connection.",
    "Brak połączenia": "No connection",
    "Przełączanie trybu": "Switching modes",
    "Przytrzymaj wybrany przycisk pokrętła, żeby wejść w tryb Klipper albo z niego wyjść – krótkie naciśnięcie działa jak zwykle. Akcję „Tryb Klipper” można też przypisać do dowolnego klawisza w profilu.": 'Hold the selected knob button to enter or leave Klipper mode – a short press works as usual. The "Klipper mode" action can also be assigned to any key in a profile.',
    "Przytrzymanie przycisku pokrętła E2": "Hold knob E2 button",
    "Przytrzymanie przycisku pokrętła E1": "Hold knob E1 button",
    "Tylko akcja „Tryb Klipper” na klawiszu": 'Only the "Klipper mode" action on a key',
    "Czas przytrzymania": "Hold time",
    "Klawisze w trybie Klipper": "Keys in Klipper mode",
    "Etykiety pojawiają się na ekranie urządzenia. „Przytrzymanie” chroni przed przypadkowym anulowaniem wydruku albo zatrzymaniem awaryjnym.": 'Labels appear on the device screen. "Hold" protects against cancelling a print or an emergency stop by accident.',
    "G-code / makro": "G-code / macro",
    "Czas przytrzymania klawisza": "Key hold time",
    "E1 – ruch osi (naciśnięcie: X → Y → Z); podczas wydruku zmienia Z offset. E2 – nastawy (naciśnięcie: kolejny parametr z listy poniżej).": "E1 – jog axes (press: X → Y → Z); while printing it changes the Z offset. E2 – adjustments (press: next parameter from the list below).",
    "Krok X/Y na zatrzask": "X/Y step per detent",
    "Krok Z na zatrzask": "Z step per detent",
    "Prędkość ruchu": "Jog speed",
    "Z offset na zatrzask (wydruk)": "Z offset per detent (printing)",
    "Krok temperatury": "Temperature step",
    "Odświeżanie stanu": "Status refresh",
    "Parametry pokrętła E2": "Knob E2 parameters",
    "Wentylator chłodzenia 0–100 %": "Part cooling fan 0–100 %",
    "Prędkość wydruku 50–150 %": "Print speed 50–150 %",
    "Pauza / wznowienie": "Pause / resume",
    "Anuluj wydruk": "Cancel print",
    "Awaryjne zatrzymanie": "Emergency stop",
    "Restart firmware": "Firmware restart",
    "Następna drukarka": "Next printer",
    "Wyjście z trybu Klipper": "Leave Klipper mode",
    "Temperatura dyszy": "Nozzle temperature",
    "Temperatura stołu": "Bed temperature",
    "Prędkość (M220)": "Speed (M220)",
    "Przepływ (M221)": "Flow (M221)",
    "Wentylator": "Fan",
    "Drukarka": "Printer",
    "(bez nazwy)": "(unnamed)",
    "drukuje": "printing",
    "wstrzymana": "paused",
    "wydruk zakończony": "print complete",
    "wydruk anulowany": "print cancelled",
    "gotowa": "ready",
    "błąd": "error",
    "zatrzymana (shutdown)": "stopped (shutdown)",
    "uruchamianie": "starting",
    "brak połączenia": "no connection",
    "dysza": "nozzle",
    "stół": "bed",
    "prędkość": "speed",
    "przepływ": "flow",
    "wentylator": "fan",
    "Animacja wygaszacza": "Screensaver animation",
    "Co pokazuje ekran LCD, gdy włączy się wygaszacz": "What the LCD shows when the screensaver starts",
    "Wygaszony ekran": "Blank screen",
    "Królik": "Rabbit",
    "Corgi": "Corgi",
    "Podświetlenie": "Lighting",
    "Podświetlenie LED": "LED lighting",
    "Stan połączenia (turkus / bursztyn)": "Connection status (teal / amber)",
    "Stały kolor": "Solid color",
    "Oddychanie": "Breathing",
    "Tęcza": "Rainbow",
    "Wyłączone": "Off",
    "Efekt": "Effect",
    "Działa też bez aplikacji (zapisany w urządzeniu)": "Also works without the app (stored on the device)",
    "Tryby stały i oddychanie; profil może mieć własny": "Solid and breathing modes; a profile can have its own",
    "Jasność LED": "LED brightness",
    "0–255; ograniczona w urządzeniu do bezpiecznego prądu USB": "0–255; the device caps it to a safe USB current",
    "Tempo": "Speed",
    "Oddychanie i tęcza: 1 = wolno, 10 = szybko": "Breathing and rainbow: 1 = slow, 10 = fast",
    "Błysk diody przy naciśniętym klawiszu": "Flash the LED next to a pressed key",
    "Kolor LED": "LED color",
    "Własny kolor podświetlenia w tym profilu": "Custom lighting color for this profile",
    "Kolor diod, gdy ten profil jest aktywny (tryby stały i oddychanie). Bez zaznaczenia – kolor z ustawień urządzenia.": "LED color while this profile is active (solid and breathing modes). Unchecked: the color from the device settings.",
    'Ekran LCD 2"': '2" LCD display',
    "Wystąpił nieoczekiwany błąd. Aplikacja działa dalej, szczegóły są w dzienniku:": "An unexpected error occurred. The app keeps running; details are in the log:",
    "ChocPilot potrzebuje uprawnienia „Dostępność”, żeby wysyłać skróty klawiszowe, wpisywać tekst i przełączać okna.\n\nUstawienia systemowe → Prywatność i ochrona → Dostępność → włącz ChocPilot, a potem uruchom aplikację ponownie.": "ChocPilot needs the Accessibility permission to send keyboard shortcuts, type text and switch windows.\n\nSystem Settings → Privacy & Security → Accessibility → turn on ChocPilot, then restart the app.",
    "Siatka etykiet 2×4": "2×4 label grid",
    "Duża nazwa profilu": "Large profile name",
    "Klawisz": "Key",
    # edytory
    "Zamknij": "Close",
    "Etykieta": "Label",
    "np. Spotify": "e.g. Spotify",
    "Na ekranie:": "On screen:",
    "Kolor": "Color",
    "Własny…": "Custom…",
    "Kolor klawisza": "Key color",
    # pokrętła i suwak
    "Pokrętło": "Knob",
    "Suwak": "Slider",
    "Suwak 45 mm": "45 mm slider",
    "Pokrętła i suwak": "Knobs and slider",
    "W prawo": "Clockwise",
    "W lewo": "Counter-clockwise",
    "Wyłączony": "Off",
    "Głośność": "Volume",
    "np. Głośność": "e.g. Volume",
    "Odśwież listę programów odtwarzających dźwięk": "Refresh the list of programs playing audio",
    "Obrót o kilka zatrzasków naraz: głośność i przewijanie mnożą krok, pozostałe akcje wykonują się raz na każdy zatrzask.": "Turning several detents at once: volume and scrolling multiply their step, other actions run once per detent.",
    "Dół suwaka = 0 %, góra = 100 %. Przy zmianie położenia ekran urządzenia pokazuje pasek głośności.": "Slider bottom = 0 %, top = 100 %. Moving it shows a volume bar on the device screen.",
    "Naciśnięcie": "Tap",
    "Przytrzymanie": "Hold",
    "Podwójne": "Double tap",
    "Przycisk": "Button",
    "Szybkie presety": "Quick presets",
    "proces, np. {name}": "process, e.g. {name}",
    "Zastosuj": "Apply",
    "Głośność systemu": "System volume",
    "Głośność programu…": "App volume…",
    "Przewijanie pionowe": "Vertical scroll",
    "Przewijanie poziome": "Horizontal scroll",
    "Utwory (następny/poprzedni)": "Tracks (next/previous)",
    "Zmiana profilu": "Switch profile",
    "Nazwa": "Name",
    "Profil domyślny (start aplikacji)": "Default profile (on app start)",
    "Automatyczne przełączanie": "Automatic switching",
    "Profil włącza się, gdy aktywne jest okno jednego z tych procesów.": "This profile turns on when a window of one of these processes is active.",
    "np. {name}": "e.g. {name}",
    "Odśwież listę uruchomionych procesów": "Refresh running processes",
    # edytor akcji
    "(brak akcji)": "(no action)",
    "nieznany": "unknown",
    "Typ akcji": "Action type",
    "Testuj": "Test",
    "Wykonaj akcję teraz": "Run the action now",
    "Nagraj skrót": "Record shortcut",
    "Anuluj": "Cancel",
    "np. ctrl+shift+c, win+e, f13": "e.g. ctrl+shift+c, win+e, f13",
    "Naciśnij kombinację klawiszy…": "Press a key combination…",
    "Plik…": "File…",
    "Folder…": "Folder…",
    "Programy (*.exe *.bat *.cmd *.lnk);;Wszystkie pliki (*)": "Programs (*.exe *.bat *.cmd *.lnk);;All files (*)",
    "Wszystkie pliki (*)": "All files (*)",
    "Aplikacje (*.app);;Wszystkie pliki (*)": "Applications (*.app);;All files (*)",
    "Wybierz plik": "Choose file",
    "Wybierz folder": "Choose folder",
    "Edytuj": "Edit",
    "W górę": "Move up",
    "W dół": "Move down",
    "Krok makra": "Macro step",
    "Opóźnienie po kroku:": "Delay after step:",
    # typy akcji (core/actions)
    "Uruchom program": "Launch program",
    "Uruchamia program lub przełącza na jego okno": "Launches a program or switches to its window",
    "Otwórz plik/folder": "Open file/folder",
    "Otwórz adres WWW": "Open web address",
    "Skrót klawiszowy": "Keyboard shortcut",
    "Kombinacja klawiszy, np. Ctrl+Shift+C, Win+E, F13": "Key combination, e.g. Ctrl+Shift+C, Win+E, F13",
    "Wpisz tekst": "Type text",
    "Wpisuje tekst (Unicode, także polskie znaki)": "Types text (Unicode, including accented characters)",
    "Multimedia": "Media",
    "Odtwarzanie i głośność systemu": "Playback and system volume",
    "Głośność programu": "App volume",
    "Głośność wybranego procesu (mikser Windows)": "Volume of a chosen process (Windows mixer)",
    "Przewijanie": "Scroll",
    "Polecenie": "Command",
    "Polecenie powłoki systemowej (cmd, PowerShell, zsh…)": "System shell command (cmd, PowerShell, zsh…)",
    "Makro": "Macro",
    "Lista kroków wykonywanych po kolei": "A list of steps run one after another",
    "Zmień profil": "Switch profile",
    "Warstwa (profil na czas trzymania)": "Layer (profile while held)",
    "Profil aktywny tylko podczas trzymania klawisza": "Profile active only while the key is held",
    "System": "System",
    "Nieznana akcja": "Unknown action",
    # pola akcji
    "Program": "Program",
    "Argumenty": "Arguments",
    "Katalog roboczy": "Working directory",
    "Jeśli już działa, przełącz na jego okno": "If already running, switch to its window",
    "Kolejne naciśnięcia przełączają między oknami programu": "Repeated presses cycle through the program's windows",
    "Plik lub folder": "File or folder",
    "Adres": "Address",
    "Przeglądarka (puste = domyślna)": "Browser (empty = default)",
    "Skrót": "Shortcut",
    "Tekst": "Text",
    "Krok głośności (%)": "Volume step (%)",
    "Proces": "Process",
    "Działanie": "Action",
    "Głośniej": "Volume up",
    "Ciszej": "Volume down",
    "Wycisz/włącz": "Mute/unmute",
    "Krok (%)": "Step (%)",
    "Kierunek": "Direction",
    "Linii na krok": "Lines per step",
    "Powłoka": "Shell",
    "Ukryte okno": "Hidden window",
    "Limit czasu (s)": "Timeout (s)",
    "Kroki": "Steps",
    "Opóźnienie po kroku (ms)": "Delay after step (ms)",
    "Przełącz na profil": "Switch to profile",
    "Następny": "Next",
    "Poprzedni": "Previous",
    "Zablokuj komputer": "Lock computer",
    "Wyłącz ekran": "Turn off display",
    "Odtwórz/Pauza": "Play/Pause",
    "Następny utwór": "Next track",
    "Poprzedni utwór": "Previous track",
    "Stop": "Stop",
    "Wycisz": "Mute",
    "Następny profil": "Next profile",
    "Poprzedni profil": "Previous profile",
    "Warstwa": "Layer",
    "kroków": "steps",
    # dziennik
    "Ostatnie zdarzenia i błędy.": "Recent events and errors.",
    "Pokaż": "Show",
    "Wszystko": "All",
    "Ostrzeżenia i błędy": "Warnings and errors",
    "Tylko błędy": "Errors only",
    "Wyczyść": "Clear",
    # ustawienia
    "Ustawienia – ChocPilot": "Settings – ChocPilot",
    "Urządzenie, gesty, tryb awaryjny i aplikacja.": "Device, gestures, fallback mode and application.",
    "Urządzenie": "Device",
    "Gesty": "Gestures",
    "Tryb awaryjny": "Fallback mode",
    "Aplikacja": "Application",
    "Zapisz": "Save",
    "Port": "Port",
    "Port szeregowy ChocPilot": "ChocPilot serial port",
    "Automatycznie (wykryj ChocPilot)": "Automatic (detect ChocPilot)",
    "Jasność ekranu": "Display brightness",
    "Wygaszacz po": "Screen saver after",
    "0 = wyłączony": "0 = off",
    "wyłączony": "off",
    "Tryb ekranu": "Display mode",
    "Obróć ekran o 180°": "Rotate display 180°",
    "Debounce klawiszy": "Key debounce",
    "Akcje urządzenia": "Device actions",
    "Próg przytrzymania": "Hold threshold",
    "Okno podwójnego naciśnięcia": "Double-tap window",
    "Wykonuj „przytrzymanie” od razu po przekroczeniu progu": "Run “hold” as soon as the threshold is passed",
    "Jeśli klawisz nie ma akcji „podwójne”, zwykłe naciśnięcie wykonuje się od razu po puszczeniu. W przeciwnym razie czeka na upływ okna.": "If a key has no “double tap” action, a tap runs immediately on release. Otherwise it waits for the window to pass.",
    "Gdy aplikacja nie działa (brak sygnału przez 3 s), ChocPilot sam wysyła skróty klawiaturowe/multimedialne przez USB HID. Domyślnie są wyliczane z aktywnego profilu (akcje typu skrót i multimedia), a poniższe wpisy je nadpisują.": "When the app is not running (no signal for 3 s), ChocPilot sends keyboard/media shortcuts itself over USB HID. By default they are derived from the active profile (shortcut and media actions); the entries below override them.",
    "Wyliczaj skróty z aktywnego profilu": "Derive shortcuts from the active profile",
    "Element": "Item",
    "Skrót (np. ctrl+c)": "Shortcut (e.g. ctrl+c)",
    "(z profilu)": "(from profile)",
    "tylko jeden klawisz poza modyfikatorami": "only one key besides modifiers",
    "Język interfejsu aplikacji": "Application interface language",
    "Motyw": "Theme",
    "Według systemu": "Follow system",
    "Jasny": "Light",
    "Ciemny": "Dark",
    "Uruchamiaj z systemem Windows": "Start with Windows",
    "Uruchamiaj po zalogowaniu": "Start at login",
    "Startuj zminimalizowana do zasobnika": "Start minimized to the tray",
    "Pokazuj etykietę na ekranie po wykonaniu akcji": "Show the label on the display after an action runs",
    "Automatycznie przełączaj profile według aktywnego okna": "Switch profiles automatically by active window",
    # zasobnik
    "Otwórz ChocPilot": "Open ChocPilot",
    "Wstrzymaj akcje": "Pause actions",
    "ChocPilot – połączono": "ChocPilot – connected",
    "ChocPilot – rozłączono": "ChocPilot – disconnected",
}


def set_language(language: str) -> None:
    global _language
    _language = "en" if language == "en" else "pl"


def language() -> str:
    return _language


def tr(text: str) -> str:
    if _language == "pl" or not text:
        return text
    return EN.get(text, text)


def action_summary(action: ActionBase | None) -> str:
    """Krótki opis akcji na kafelku/w edytorze, w bieżącym języku."""
    if action is None:
        return ""
    kind = action.type
    data = action.model_dump()
    if kind in ("launch", "open"):
        path = str(data.get("path") or "").replace("/", "\\")
        return path.rsplit("\\", 1)[-1] or tr(action.label)
    if kind == "url":
        url = str(data.get("url") or "")
        for prefix in ("https://", "http://"):
            url = url.removeprefix(prefix)
        return url.removeprefix("www.").rstrip("/") or tr(action.label)
    if kind == "hotkey":
        keys = str(data.get("keys") or "")
        try:
            if not keys:
                return tr("Skrót")
            text = format_hotkey(parse_hotkey(keys))
            # na macOS klawisz „win” to Cmd, a „alt” to Option
            return (
                text.replace("Win", "Cmd").replace("Alt", "Option")
                if current_os() == "macos"
                else text
            )
        except ValueError:
            return keys
    if kind == "type_text":
        short = str(data.get("text") or "").replace("\n", " ")[:20]
        return f"„{short}”"
    if kind == "media":
        from ..core.actions.builtin import MEDIA_LABELS

        return tr(str(MEDIA_LABELS.get(str(data.get("key")), data.get("key"))))
    if kind == "app_volume":
        modes = {"up": "Głośniej", "down": "Ciszej", "mute": "Wycisz/włącz"}
        return f"{data.get('process') or '?'} · {tr(modes.get(str(data.get('mode')), ''))}"
    if kind == "scroll":
        dirs = {"up": "W górę", "down": "W dół", "left": "W lewo", "right": "W prawo"}
        return f"{tr('Przewijanie')} · {tr(dirs.get(str(data.get('direction')), ''))}"
    if kind == "macro":
        return f"{tr('Makro')} ({len(data.get('steps') or [])} {tr('kroków')})"
    if kind == "profile":
        mode = data.get("mode")
        if mode == "next":
            return tr("Następny profil")
        if mode == "prev":
            return tr("Poprzedni profil")
        return f"{tr('Profil')}: {data.get('profile') or '—'}"
    if kind == "layer":
        return f"{tr('Warstwa')}: {data.get('profile') or '—'}"
    if kind == "system":
        cmds = {"lock": "Zablokuj komputer", "screen_off": "Wyłącz ekran"}
        return tr(cmds.get(str(data.get("command")), tr("System")))
    if kind == "shell":
        return f"{data.get('shell')}: {str(data.get('command') or '')[:24]}"
    return tr(action.label) if action.label else action.type

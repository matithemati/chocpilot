"""Wbudowane ikony liniowe (24 × 24, obrys 2 px) do klawiszy i interfejsu.

Każda pozycja: (nazwa, etykieta, kategoria, słowa kluczowe, treść SVG). Treść to elementy SVG
rysowane obrysem w kolorze podanym przy renderowaniu (bez wypełnienia). Nowa ikona = nowy wiersz
w ICONS (nazwa unikalna, a–z, 0–9, „-”). Własne ikony użytkownika (PNG/SVG) trafiają do folderu
ikon w katalogu konfiguracji – patrz icon_library.py.
"""

from __future__ import annotations

_SEARCH = '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>'
_SPEAKER = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
_MIC = (
    '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/>'
    '<path d="M12 18v4M8 22h8"/>'
)
_FILE = (
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>'
)
_EYE = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'
_LOCK_BODY = '<rect x="4" y="11" width="16" height="11" rx="2"/>'

# (nazwa, etykieta, kategoria, słowa kluczowe, SVG)
ICONS: tuple[tuple[str, str, str, str, str], ...] = (
    # --- multimedia
    ("play", "Odtwarzaj", "Multimedia", "play start", '<polygon points="7 4 20 12 7 20 7 4"/>'),
    (
        "pause",
        "Pauza",
        "Multimedia",
        "pause",
        '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    ),
    (
        "play-pause",
        "Odtwarzaj/pauza",
        "Multimedia",
        "play pause toggle",
        '<polygon points="3 5 11 12 3 19 3 5"/><path d="M15 5v14M20 5v14"/>',
    ),
    ("stop", "Stop", "Multimedia", "stop", '<rect x="5" y="5" width="14" height="14" rx="2"/>'),
    (
        "next",
        "Następny",
        "Multimedia",
        "next skip forward",
        '<polygon points="5 4 15 12 5 20 5 4"/><path d="M19 5v14"/>',
    ),
    (
        "prev",
        "Poprzedni",
        "Multimedia",
        "previous back rewind",
        '<polygon points="19 20 9 12 19 4 19 20"/><path d="M5 19V5"/>',
    ),
    (
        "record",
        "Nagrywanie",
        "Multimedia",
        "record rec",
        '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>',
    ),
    (
        "volume-up",
        "Głośniej",
        "Multimedia",
        "volume up louder",
        _SPEAKER + '<path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>',
    ),
    (
        "volume-down",
        "Ciszej",
        "Multimedia",
        "volume down quieter",
        _SPEAKER + '<path d="M15.5 8.5a5 5 0 0 1 0 7"/>',
    ),
    ("mute", "Wycisz", "Multimedia", "mute silent", _SPEAKER + '<path d="M22 9l-6 6M16 9l6 6"/>'),
    ("mic", "Mikrofon", "Multimedia", "microphone mic", _MIC),
    (
        "mic-off",
        "Mikrofon wył.",
        "Multimedia",
        "microphone mute off",
        _MIC + '<path d="M3 3l18 18"/>',
    ),
    (
        "headphones",
        "Słuchawki",
        "Multimedia",
        "headphones audio",
        '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><rect x="2" y="14" width="5" height="7" rx="2"/>'
        '<rect x="17" y="14" width="5" height="7" rx="2"/>',
    ),
    (
        "music",
        "Muzyka",
        "Multimedia",
        "music song note",
        '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    ),
    (
        "video",
        "Wideo",
        "Multimedia",
        "video camera film",
        '<rect x="2" y="6" width="14" height="12" rx="2"/><polygon points="22 8 16 12 22 16 22 8"/>',
    ),
    (
        "camera",
        "Aparat",
        "Multimedia",
        "camera photo",
        '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>'
        '<circle cx="12" cy="13" r="4"/>',
    ),
    (
        "shuffle",
        "Losowo",
        "Multimedia",
        "shuffle random",
        '<path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>',
    ),
    (
        "repeat",
        "Powtarzaj",
        "Multimedia",
        "repeat loop",
        '<path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/>'
        '<path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
    ),
    # --- edycja
    (
        "copy",
        "Kopiuj",
        "Edycja",
        "copy duplicate",
        '<rect x="9" y="9" width="13" height="13" rx="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    ),
    (
        "paste",
        "Wklej",
        "Edycja",
        "paste clipboard",
        '<rect x="5" y="4" width="14" height="18" rx="2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
    ),
    (
        "cut",
        "Wytnij",
        "Edycja",
        "cut scissors",
        '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/>'
        '<path d="M20 4L8.1 15.9M14.5 14.5L20 20M8.1 8.1L12 12"/>',
    ),
    (
        "undo",
        "Cofnij",
        "Edycja",
        "undo back",
        '<path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-15-6.7L3 13"/>',
    ),
    (
        "redo",
        "Ponów",
        "Edycja",
        "redo",
        '<path d="M21 7v6h-6"/><path d="M3 17a9 9 0 0 1 15-6.7L21 13"/>',
    ),
    (
        "save",
        "Zapisz",
        "Edycja",
        "save disk",
        '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
        '<path d="M17 21v-8H7v8M7 3v5h8"/>',
    ),
    ("search", "Szukaj", "Edycja", "search find", _SEARCH),
    ("zoom-in", "Powiększ", "Edycja", "zoom in plus", _SEARCH + '<path d="M11 8v6M8 11h6"/>'),
    ("zoom-out", "Pomniejsz", "Edycja", "zoom out minus", _SEARCH + '<path d="M8 11h6"/>'),
    (
        "pencil",
        "Edytuj",
        "Edycja",
        "edit pencil write",
        '<path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/>',
    ),
    (
        "trash",
        "Usuń",
        "Edycja",
        "delete trash bin",
        '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    ),
    (
        "hash",
        "Krzyżyk",
        "Edycja",
        "hash number tag",
        '<path d="M4 9h16M4 15h16M10 3L8 21M16 3l-2 18"/>',
    ),
    (
        "at",
        "Małpa",
        "Edycja",
        "at email mention",
        '<circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-3.9 7.9"/>',
    ),
    # --- pliki i programy
    (
        "folder",
        "Folder",
        "Programy",
        "folder directory",
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    ),
    ("file", "Plik", "Programy", "file document", _FILE),
    (
        "file-text",
        "Dokument",
        "Programy",
        "document text",
        _FILE + '<path d="M16 13H8M16 17H8M10 9H8"/>',
    ),
    (
        "terminal",
        "Terminal",
        "Programy",
        "terminal console shell",
        '<polyline points="4 17 10 11 4 5"/><path d="M12 19h8"/>',
    ),
    (
        "code",
        "Kod",
        "Programy",
        "code dev",
        '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    ),
    (
        "globe",
        "Przeglądarka",
        "Programy",
        "browser web internet globe",
        '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/>'
        '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    ),
    (
        "mail",
        "Poczta",
        "Programy",
        "mail email",
        '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 6l-10 7L2 6"/>',
    ),
    (
        "calendar",
        "Kalendarz",
        "Programy",
        "calendar date",
        '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    ),
    (
        "calculator",
        "Kalkulator",
        "Programy",
        "calculator",
        '<rect x="4" y="2" width="16" height="20" rx="2"/><rect x="8" y="6" width="8" height="4"/>'
        '<path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/>',
    ),
    (
        "image",
        "Obraz",
        "Programy",
        "image picture photo",
        '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>'
        '<path d="M21 15l-5-5L5 21"/>',
    ),
    (
        "chat",
        "Czat",
        "Programy",
        "chat message",
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    ),
    (
        "book",
        "Książka",
        "Programy",
        "book read docs",
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5z"/>'
        '<path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/>',
    ),
    (
        "clock",
        "Zegar",
        "Programy",
        "clock time",
        '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    ),
    (
        "timer",
        "Minutnik",
        "Programy",
        "timer stopwatch",
        '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M9 2h6"/>',
    ),
    (
        "gamepad",
        "Gry",
        "Programy",
        "game gamepad controller",
        '<rect x="2" y="7" width="20" height="10" rx="5"/><path d="M6 12h4M8 10v4"/>'
        '<path d="M15 11h.01M18 13h.01"/>',
    ),
    (
        "coffee",
        "Kawa",
        "Programy",
        "coffee break",
        '<path d="M17 8h1a4 4 0 0 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4z"/>'
        '<path d="M6 2v2M10 2v2M14 2v2"/>',
    ),
    (
        "cart",
        "Koszyk",
        "Programy",
        "cart shop",
        '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>'
        '<path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>',
    ),
    (
        "briefcase",
        "Praca",
        "Programy",
        "work briefcase",
        '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    ),
    (
        "map",
        "Mapa",
        "Programy",
        "map navigation",
        '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><path d="M8 2v16M16 6v16"/>',
    ),
    # --- system
    (
        "lock",
        "Zablokuj",
        "System",
        "lock secure",
        _LOCK_BODY + '<path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    ),
    (
        "unlock",
        "Odblokuj",
        "System",
        "unlock open",
        _LOCK_BODY + '<path d="M8 11V7a4 4 0 0 1 7.9-1"/>',
    ),
    (
        "power",
        "Zasilanie",
        "System",
        "power shutdown off",
        '<path d="M18.4 6.6a9 9 0 1 1-12.8 0"/><path d="M12 2v10"/>',
    ),
    (
        "settings",
        "Ustawienia",
        "System",
        "settings gear config",
        '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/>'
        '<path d="M12 1v3M12 20v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M1 12h3M20 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    ),
    (
        "home",
        "Start",
        "System",
        "home house",
        '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    ),
    (
        "refresh",
        "Odśwież",
        "System",
        "refresh reload",
        '<path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15"/>',
    ),
    (
        "sun",
        "Jasność",
        "System",
        "brightness sun light day",
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    ),
    (
        "moon",
        "Noc",
        "System",
        "moon night dark sleep",
        '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    ),
    (
        "wifi",
        "Wi-Fi",
        "System",
        "wifi network wireless",
        '<path d="M5 12.6a10 10 0 0 1 14 0M8.5 16.1a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 20 0"/><path d="M12 20h.01"/>',
    ),
    (
        "bluetooth",
        "Bluetooth",
        "System",
        "bluetooth",
        '<polyline points="7 7 17 17 12 22 12 2 17 7 7 17"/>',
    ),
    (
        "battery",
        "Bateria",
        "System",
        "battery power",
        '<rect x="2" y="7" width="18" height="10" rx="2"/><path d="M23 11v2"/>',
    ),
    (
        "keyboard",
        "Klawiatura",
        "System",
        "keyboard keys",
        '<rect x="2" y="5" width="20" height="14" rx="2"/>'
        '<path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 13h.01M18 13h.01M8 16h8M10 13h4"/>',
    ),
    (
        "mouse",
        "Mysz",
        "System",
        "mouse pointer",
        '<rect x="6" y="2" width="12" height="20" rx="6"/><path d="M12 6v4"/>',
    ),
    (
        "monitor",
        "Monitor",
        "System",
        "monitor display screen",
        '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    ),
    (
        "laptop",
        "Laptop",
        "System",
        "laptop computer",
        '<rect x="4" y="4" width="16" height="11" rx="2"/><path d="M2 20h20"/>',
    ),
    (
        "phone",
        "Telefon",
        "System",
        "phone smartphone mobile",
        '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M12 18h.01"/>',
    ),
    (
        "window",
        "Okno",
        "System",
        "window app",
        '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/>',
    ),
    (
        "maximize",
        "Maksymalizuj",
        "System",
        "maximize fullscreen",
        '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
    ),
    (
        "minimize",
        "Minimalizuj",
        "System",
        "minimize exit fullscreen",
        '<path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"/>',
    ),
    (
        "screenshot",
        "Zrzut ekranu",
        "System",
        "screenshot capture",
        '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>'
        '<circle cx="12" cy="12" r="3"/>',
    ),
    (
        "cpu",
        "Procesor",
        "System",
        "cpu chip processor",
        '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>'
        '<path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
    ),
    (
        "download",
        "Pobierz",
        "System",
        "download",
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><path d="M12 15V3"/>',
    ),
    (
        "upload",
        "Wyślij",
        "System",
        "upload",
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><path d="M12 3v12"/>',
    ),
    (
        "cloud",
        "Chmura",
        "System",
        "cloud",
        '<path d="M18 10h-1.3A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
    ),
    (
        "toggle-on",
        "Włączone",
        "System",
        "toggle switch on",
        '<rect x="1" y="6" width="22" height="12" rx="6"/><circle cx="16" cy="12" r="3"/>',
    ),
    (
        "toggle-off",
        "Wyłączone",
        "System",
        "toggle switch off",
        '<rect x="1" y="6" width="22" height="12" rx="6"/><circle cx="8" cy="12" r="3"/>',
    ),
    (
        "shield",
        "Ochrona",
        "System",
        "shield security",
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    ),
    (
        "key",
        "Klucz",
        "System",
        "key password",
        '<circle cx="7.5" cy="15.5" r="5.5"/><path d="M21 2l-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>',
    ),
    # --- streaming
    ("eye", "Widoczne", "Streaming", "eye show visible", _EYE),
    ("eye-off", "Ukryte", "Streaming", "eye hide hidden", _EYE + '<path d="M3 3l18 18"/>'),
    (
        "layers",
        "Sceny",
        "Streaming",
        "layers scenes",
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>'
        '<polyline points="2 12 12 17 22 12"/>',
    ),
    (
        "broadcast",
        "Na żywo",
        "Streaming",
        "broadcast live stream radio",
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="M16.2 7.8a6 6 0 0 1 0 8.5M7.8 16.2a6 6 0 0 1 0-8.5M19.1 4.9a10 10 0 0 1 0 14.2M4.9 19.1a10 10 0 0 1 0-14.2"/>',
    ),
    (
        "film",
        "Film",
        "Streaming",
        "film movie clip",
        '<rect x="2" y="2" width="20" height="20" rx="2.2"/>'
        '<path d="M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5"/>',
    ),
    (
        "send",
        "Wyślij wiad.",
        "Streaming",
        "send message",
        '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>',
    ),
    (
        "share",
        "Udostępnij",
        "Streaming",
        "share",
        '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
        '<path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
    ),
    # --- druk 3D
    (
        "printer",
        "Drukarka",
        "Druk 3D",
        "printer print",
        '<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
        '<rect x="6" y="14" width="12" height="8"/>',
    ),
    (
        "move",
        "Ruch osi",
        "Druk 3D",
        "move jog axis arrows",
        '<path d="M5 9l-3 3 3 3M9 5l3-3 3 3M15 19l-3 3-3-3M19 9l3 3-3 3M2 12h20M12 2v20"/>',
    ),
    (
        "crosshair",
        "Bazowanie",
        "Druk 3D",
        "home axes crosshair target",
        '<circle cx="12" cy="12" r="10"/><path d="M22 12h-4M6 12H2M12 6V2M12 22v-4"/>',
    ),
    (
        "thermometer",
        "Temperatura",
        "Druk 3D",
        "temperature heat thermometer",
        '<path d="M14 14.8V3.5a2.5 2.5 0 0 0-5 0v11.3a4.5 4.5 0 1 0 5 0z"/>',
    ),
    (
        "fan",
        "Wentylator",
        "Druk 3D",
        "fan cooling",
        '<circle cx="12" cy="12" r="2"/>'
        '<path d="M12 10c0-4 1-8 4-8s2 5-2 8M14 12c4 0 8 1 8 4s-5 2-8-2M12 14c0 4-1 8-4 8s-2-5 2-8M10 12c-4 0-8-1-8-4s5-2 8 2"/>',
    ),
    (
        "package",
        "Model",
        "Druk 3D",
        "box package cube model",
        '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7z"/>'
        '<path d="M3.3 7L12 12l8.7-5M12 22V12"/>',
    ),
    (
        "droplet",
        "Kropla",
        "Druk 3D",
        "droplet filament flow water",
        '<path d="M12 2.7l5.7 5.6a8 8 0 1 1-11.3 0z"/>',
    ),
    (
        "fire",
        "Grzanie",
        "Druk 3D",
        "fire heat flame hot",
        '<path d="M12 22c4 0 7-3 7-7 0-4-3-6-4-9-1 3-3 4-3 4s-1-3-3-5c0 4-4 6-4 10 0 4 3 7 7 7z"/>',
    ),
    # --- symbole
    (
        "star",
        "Gwiazdka",
        "Symbole",
        "star favorite",
        '<polygon points="12 2 15.1 8.3 22 9.3 17 14.1 18.2 21 12 17.8 5.8 21 7 14.1 2 9.3 8.9 8.3 12 2"/>',
    ),
    (
        "heart",
        "Serce",
        "Symbole",
        "heart love like",
        '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
    ),
    (
        "bell",
        "Dzwonek",
        "Symbole",
        "bell notification alert",
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    ),
    (
        "bolt",
        "Błyskawica",
        "Symbole",
        "bolt flash lightning zap",
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    ),
    ("check", "OK", "Symbole", "check ok done yes", '<polyline points="20 6 9 17 4 12"/>'),
    ("x", "Zamknij", "Symbole", "close x cancel no", '<path d="M18 6L6 18M6 6l12 12"/>'),
    ("plus", "Plus", "Symbole", "plus add new", '<path d="M12 5v14M5 12h14"/>'),
    ("minus", "Minus", "Symbole", "minus remove", '<path d="M5 12h14"/>'),
    ("arrow-up", "W górę", "Symbole", "arrow up", '<path d="M12 19V5M5 12l7-7 7 7"/>'),
    ("arrow-down", "W dół", "Symbole", "arrow down", '<path d="M12 5v14M19 12l-7 7-7-7"/>'),
    ("arrow-left", "W lewo", "Symbole", "arrow left", '<path d="M19 12H5M12 19l-7-7 7-7"/>'),
    ("arrow-right", "W prawo", "Symbole", "arrow right", '<path d="M5 12h14M12 5l7 7-7 7"/>'),
    (
        "link",
        "Link",
        "Symbole",
        "link url chain",
        '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
        '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    ),
    (
        "pin",
        "Lokalizacja",
        "Symbole",
        "pin location place",
        '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    ),
    (
        "flag",
        "Flaga",
        "Symbole",
        "flag",
        '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    ),
    (
        "tag",
        "Etykieta",
        "Symbole",
        "tag label",
        '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z"/><path d="M7 7h.01"/>',
    ),
    (
        "bookmark",
        "Zakładka",
        "Symbole",
        "bookmark save",
        '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    ),
    (
        "user",
        "Osoba",
        "Symbole",
        "user person profile",
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    ),
    (
        "users",
        "Grupa",
        "Symbole",
        "users people group team",
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
        '<path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    ),
    (
        "rocket",
        "Rakieta",
        "Symbole",
        "rocket launch",
        '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.2 2.2 0 0 0-2.9-.1z"/>'
        '<path d="M12 15l-3-3a22 22 0 0 1 2-3.9A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22.4 22.4 0 0 1-4 2z"/>'
        '<path d="M9 12H4s.6-3 2-4c1.6-1.1 5 0 5 0M12 15v5s3-.6 4-2c1.1-1.6 0-5 0-5"/>',
    ),
    (
        "gift",
        "Prezent",
        "Symbole",
        "gift present",
        '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/>'
        '<path d="M7.5 8a2.5 2.5 0 0 1 0-5C11 3 12 8 12 8s1-5 4.5-5a2.5 2.5 0 0 1 0 5"/>',
    ),
    (
        "thumbs-up",
        "Kciuk",
        "Symbole",
        "thumbs up like",
        '<path d="M7 10v12M15 5.9L14 10h5.8a2 2 0 0 1 1.9 2.6l-2.3 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.8a2 2 0 0 0 1.8-1.1L12 2a3.1 3.1 0 0 1 3 3.9z"/>',
    ),
    (
        "smile",
        "Uśmiech",
        "Symbole",
        "smile happy face",
        '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>',
    ),
    (
        "info",
        "Informacja",
        "Symbole",
        "info information",
        '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    ),
    (
        "help",
        "Pomoc",
        "Symbole",
        "help question",
        '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
    ),
    (
        "warning",
        "Uwaga",
        "Symbole",
        "warning alert caution",
        '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h16.9a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
        '<path d="M12 9v4M12 17h.01"/>',
    ),
    (
        "palette",
        "Paleta",
        "Symbole",
        "palette color art paint",
        '<circle cx="13.5" cy="6.5" r="1"/><circle cx="17.5" cy="10.5" r="1"/><circle cx="8.5" cy="7.5" r="1"/>'
        '<circle cx="6.5" cy="12.5" r="1"/>'
        '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.6-.7 1.6-1.7 0-.4-.2-.8-.4-1.1-.3-.3-.4-.7-.4-1.1 '
        '0-.9.7-1.7 1.7-1.7H16c3.1 0 5.6-2.5 5.6-5.6C21.9 6 17.5 2 12 2z"/>',
    ),
)

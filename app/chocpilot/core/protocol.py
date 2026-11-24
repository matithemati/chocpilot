"""Protokół ChocPilot (JSON Lines) – kodowanie, dekodowanie i walidacja wiadomości.

Pełny opis: docs/PROTOCOL.md. Moduł nie zależy od transportu ani od GUI.
"""

from __future__ import annotations

import base64
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

PROTOCOL_VERSION = 1
MAX_LINE_LENGTH = 1024
PING_INTERVAL_S = 1.0
HEARTBEAT_TIMEOUT_S = 3.0

TITLE_CHARS = 21
LABEL_CHARS = 10  # na ekranie 1–2 wiersze po 6 znaków w komórce siatki
# Matryca 2 × 4 (Kailh Choc): klawisze 1–4 w górnym rzędzie, 5–8 w dolnym.
KEY_ROWS = 2
KEY_COLS = 4
KEY_COUNT = KEY_ROWS * KEY_COLS
# ChocPilot v0: dwa pokrętła EC11 z przyciskami (1 – górne, 2 – dolne) i suwak 0–100.
ENCODER_COUNT = 2
SLIDER_MAX = 100

BOARD_NAMES = {"promicro": "Pro Micro", "chocpilot_v0": "ChocPilot v0 (STM32F072)"}
# Rodzaj ekranu płytki: "oled" = SSD1309 128×64 (I²C), "lcd" = kolorowy ST7789V 320×240 (SPI).
BOARD_SCREENS = {"chocpilot_v0": "lcd"}
# Płytki z małą pamięcią zgłaszają w hello krótszy limit linii (max_line), np. Pro Micro: 272 B.
MIN_LINE_LENGTH = 128

MEDIA_KEYS = ("play_pause", "next", "prev", "stop", "vol_up", "vol_down", "mute")
HID_MODIFIERS = ("ctrl", "shift", "alt", "win", "rctrl", "rshift", "ralt", "rwin")


class ProtocolError(ValueError):
    """Niepoprawna wiadomość."""


# --------------------------------------------------------------------------- kodowanie


def encode(message: dict[str, Any]) -> bytes:
    """Zamienia wiadomość na linię JSON zakończoną \\n (UTF-8)."""
    if "type" not in message:
        raise ProtocolError("message without type")
    line = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    data = (line + "\n").encode("utf-8")
    if len(data) > MAX_LINE_LENGTH:
        raise ProtocolError(f"message too long ({len(data)} bytes)")
    return data


def decode(line: bytes | str) -> dict[str, Any]:
    """Dekoduje jedną linię. Rzuca ProtocolError dla niepoprawnych danych."""
    if isinstance(line, bytes):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("invalid utf-8") from exc
    line = line.strip()
    if not line:
        raise ProtocolError("empty line")
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid json: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ProtocolError("object expected")
    if not isinstance(data.get("type"), str):
        raise ProtocolError("missing type")
    return data


# --------------------------------------------------------------------------- transliteracja

_POLISH = str.maketrans(
    {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
        "–": "-", "—": "-", "…": "...", "„": '"', "”": '"', "“": '"', "’": "'", "‘": "'",
        "×": "x", "→": ">", "←": "<", "▶": ">", "⏸": "||", "⏭": ">>", "⏮": "<<",
    }
)  # fmt: skip


def transliterate(text: str) -> str:
    """Zamienia tekst na ASCII (czcionki OLED nie mają polskich znaków)."""
    text = text.translate(_POLISH)
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if ord(c) < 128 and not unicodedata.combining(c))
    return "".join(c if c.isprintable() else " " for c in ascii_text)


def fit(text: str, max_chars: int) -> str:
    """Transliteracja + obcięcie do limitu znaków."""
    return transliterate(text)[:max_chars]


# --------------------------------------------------------------------------- PC → urządzenie


def msg_hello(app_version: str) -> dict[str, Any]:
    return {"type": "hello", "app": app_version}


def msg_ping() -> dict[str, Any]:
    return {"type": "ping"}


def msg_get_info() -> dict[str, Any]:
    return {"type": "get_info"}


def msg_display_profile(name: str) -> dict[str, Any]:
    return {"type": "display", "mode": "profile", "name": fit(name, TITLE_CHARS)}


def msg_display_grid(title: str, labels: list[str]) -> dict[str, Any]:
    padded = [fit(label, LABEL_CHARS) for label in labels[:KEY_COUNT]]
    padded += [""] * (KEY_COUNT - len(padded))
    return {"type": "display", "mode": "grid", "title": fit(title, TITLE_CHARS), "labels": padded}


def msg_display_text(line1: str, line2: str = "", ms: int = 0) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "type": "display",
        "mode": "text",
        "line1": fit(line1, TITLE_CHARS),
        "line2": fit(line2, TITLE_CHARS),
    }
    if ms:
        msg["ms"] = int(ms)
    return msg


def msg_display_bar(title: str, value: float, ms: int = 1500) -> dict[str, Any]:
    clamped = max(0, min(100, round(value)))
    msg: dict[str, Any] = {
        "type": "display",
        "mode": "bar",
        "title": fit(title, TITLE_CHARS),
        "value": clamped,
    }
    if ms:
        msg["ms"] = int(ms)
    return msg


def msg_flash(text: str, key: int | None = None, ms: int = 1000) -> dict[str, Any]:
    msg: dict[str, Any] = {"type": "flash", "text": fit(text, TITLE_CHARS), "ms": int(ms)}
    if key is not None:
        msg["key"] = int(key)
    return msg


# Podświetlenie LED (ChocPilot v0): tryby i zakresy komendy leds (jak firmware).
LED_MODES = ("off", "status", "static", "breathe", "rainbow")
LED_SPEED_MIN, LED_SPEED_MAX = 1, 10
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex_color(value: object) -> bool:
    return isinstance(value, str) and _HEX_COLOR.match(value) is not None


def msg_leds(
    *,
    mode: str | None = None,
    color: str | None = None,
    brightness: int | None = None,
    speed: int | None = None,
    react: bool | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Komenda leds (pola opcjonalne). save=False: bez zapisu w pamięci urządzenia."""
    msg: dict[str, Any] = {"type": "leds"}
    if mode is not None:
        if mode not in LED_MODES:
            raise ProtocolError(f"unknown led mode {mode}")
        msg["mode"] = mode
    if color is not None:
        if not is_hex_color(color):
            raise ProtocolError("color must be #RRGGBB")
        msg["color"] = color.lower()
    if brightness is not None:
        if isinstance(brightness, bool) or not 0 <= int(brightness) <= 255:
            raise ProtocolError("brightness: out of range 0..255")
        msg["brightness"] = int(brightness)
    if speed is not None:
        if isinstance(speed, bool) or not LED_SPEED_MIN <= int(speed) <= LED_SPEED_MAX:
            raise ProtocolError(f"speed: out of range {LED_SPEED_MIN}..{LED_SPEED_MAX}")
        msg["speed"] = int(speed)
    if react is not None:
        msg["react"] = bool(react)
    if not save:
        msg["save"] = False
    return msg


# Ikony klawiszy (płytki z `icon` w hello): 32 × 32, paleta 16 × RGB565 + 4 bity na piksel.
ICON_BYTES = 16 * 2 + 32 * 32 // 2  # 544
ICON_CHUNK = 128  # bajtów na komendę (base64 172 znaki – mieści się w max_line 272)


def msgs_icon(key: int, payload: bytes, chunk: int = ICON_CHUNK) -> list[dict[str, Any]]:
    """Ikona klawisza w kawałkach (po kolei od offset 0 – urządzenie składa je w RAM)."""
    if not 1 <= key <= KEY_COUNT or len(payload) != ICON_BYTES:
        raise ProtocolError("bad icon")
    return [
        {
            "type": "icon",
            "key": key,
            "offset": off,
            "data": base64.b64encode(payload[off : off + chunk]).decode("ascii"),
        }
        for off in range(0, len(payload), chunk)
    ]


def msg_icon_clear(key: int) -> dict[str, Any]:
    return {"type": "icon", "key": key, "clear": True}


# Czas lokalny dla zegara na wygaszaczu LCD (płytki z `savers` w hello).
TIME_SYNC_INTERVAL_S = 300.0


def msg_time(hour: int, minute: int, second: int = 0) -> dict[str, Any]:
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise ProtocolError("time out of range")
    return {"type": "time", "hour": int(hour), "minute": int(minute), "second": int(second)}


SETTINGS_FIELDS = {
    "brightness": (int, 0, 255),
    "screensaver_s": (int, 0, 65535),
    "flip": (bool, None, None),
    "debounce_ms": (int, 1, 50),
    "oled_addr": (int, 0x08, 0x77),
    "saver": (str, None, None),  # animacja wygaszacza ("off" = wygaszony ekran), tylko LCD
}
SAVER_OFF = "off"
_SAVER_NAME = re.compile(r"^[a-z0-9_]{1,11}$")


def is_saver_name(value: object) -> bool:
    return isinstance(value, str) and _SAVER_NAME.match(value) is not None


def msg_settings(**values: Any) -> dict[str, Any]:
    """Wiadomość settings z walidacją zakresów (zgodnie z firmware)."""
    msg: dict[str, Any] = {"type": "settings"}
    for key, value in values.items():
        if key not in SETTINGS_FIELDS:
            raise ProtocolError(f"unknown setting {key}")
        kind, lo, hi = SETTINGS_FIELDS[key]
        if kind is str:
            if not is_saver_name(value):
                raise ProtocolError(f"{key}: name expected (a-z, 0-9, _, max 11)")
        elif kind is bool:
            if not isinstance(value, bool):
                raise ProtocolError(f"{key}: bool expected")
        else:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ProtocolError(f"{key}: int expected")
            assert lo is not None and hi is not None
            if not lo <= value <= hi:
                raise ProtocolError(f"{key}: out of range {lo}..{hi}")
        msg[key] = value
    return msg


@dataclass(frozen=True)
class FallbackBinding:
    """Skrót HID trybu awaryjnego. slot: klawisz 1..8."""

    slot: int
    mods: tuple[str, ...] = ()
    code: str | None = None
    media: str | None = None

    def to_message(self) -> dict[str, Any]:
        item: dict[str, Any] = {"key": self.slot}
        if self.media:
            item["media"] = self.media
        else:
            if self.mods:
                item["mods"] = list(self.mods)
            if self.code:
                item["code"] = self.code
        return item


def msg_set_fallback(bindings: list[FallbackBinding], replace: bool = True) -> dict[str, Any]:
    return {
        "type": "set_fallback",
        "replace": replace,
        "bindings": [b.to_message() for b in bindings[:12]],
    }


# Zapas na pole "id" dodawane przy wysyłaniu (,"id":2147483647).
_ID_RESERVE = 16


def msgs_set_fallback(
    bindings: list[FallbackBinding], max_line: int = MAX_LINE_LENGTH
) -> list[dict[str, Any]]:
    """set_fallback podzielone na linie mieszczące się w limicie urządzenia (max_line z hello).

    Pierwsza wiadomość ma replace=True (czyści wszystkie sloty), kolejne dopisują przypisania.
    """
    limit = max(max_line, MIN_LINE_LENGTH) - _ID_RESERVE
    messages: list[dict[str, Any]] = []
    chunk: list[FallbackBinding] = []
    for binding in bindings[:12]:
        candidate = msg_set_fallback([*chunk, binding], replace=not messages)
        if chunk and len(encode(candidate)) > limit:
            messages.append(msg_set_fallback(chunk, replace=not messages))
            chunk = [binding]
        else:
            chunk.append(binding)
    if chunk or not messages:
        messages.append(msg_set_fallback(chunk, replace=not messages))
    return messages


def msg_reboot(bootloader: bool = False) -> dict[str, Any]:
    return {"type": "reboot", "bootloader": bootloader}


def msg_test_mode(enable: bool) -> dict[str, Any]:
    return {"type": "test_mode", "enable": enable}


# --------------------------------------------------------------------------- urządzenie → PC


@dataclass(frozen=True)
class DeviceInfo:
    device: str
    fw: str
    board: str
    keys: int = KEY_COUNT
    encoder: bool = False
    leds: int = 0  # liczba diod podświetlenia (0 = brak, np. Pro Micro)
    savers: tuple[str, ...] = ()  # animacje wygaszacza w urządzeniu (pusto = tylko wygaszony ekran)
    icon_size: int = 0  # ikony klawiszy na ekranie (0 = tylko etykiety, np. OLED)
    hid: bool = True
    # Diagnostyka I²C (firmware ≥ 1.0.1): has_diag=False – starszy firmware bez tych pól.
    has_diag: bool = False
    oled_addr: int | None = None  # None = ekran nie odpowiada
    i2c_devices: tuple[int, ...] = ()
    # Stan linii bez wewnętrznego pull-upu (1 = wysoki, 0 = niski, None = nie mierzono)
    sda_level: int | None = None
    scl_level: int | None = None
    swapped: bool = False  # ekran znaleziony po zamianie SDA/SCL
    # Maksymalna długość linii do urządzenia (z \n); pole max_line tylko na małych płytkach.
    max_line: int = MAX_LINE_LENGTH

    @property
    def board_name(self) -> str:
        return BOARD_NAMES.get(self.board, self.board)

    @property
    def screen(self) -> str:
        """Rodzaj ekranu: "lcd" (Waveshare 2" ST7789V) albo "oled" (SSD1309)."""
        return BOARD_SCREENS.get(self.board, "oled")

    @property
    def oled_status(self) -> str:
        if not self.has_diag:
            return "?"
        return f"0x{self.oled_addr:02X}" if self.oled_addr is not None else "brak"


@dataclass(frozen=True)
class KeyEvent:
    key: int
    down: bool
    t: int


@dataclass(frozen=True)
class AckEvent:
    id: int


@dataclass(frozen=True)
class ErrorEvent:
    id: int | None
    msg: str


@dataclass(frozen=True)
class LogEvent:
    level: str
    msg: str


@dataclass(frozen=True)
class TestModeEvent:
    active: bool


@dataclass(frozen=True)
class EncoderEvent:
    index: int  # 1..ENCODER_COUNT
    delta: int  # zatrzaski, dodatnie = w prawo
    t: int


@dataclass(frozen=True)
class EncoderKeyEvent:
    index: int
    down: bool
    t: int


@dataclass(frozen=True)
class SliderEvent:
    value: int  # 0..SLIDER_MAX (0 = dół)
    t: int


DeviceMessage = (
    DeviceInfo
    | KeyEvent
    | AckEvent
    | ErrorEvent
    | LogEvent
    | TestModeEvent
    | EncoderEvent
    | EncoderKeyEvent
    | SliderEvent
)


def _int(data: dict[str, Any], key: str, default: int | None = None) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(f"{key}: int expected")
    return value


def _level(data: dict[str, Any], line: str) -> int | None:
    lines = data.get("lines")
    value = lines.get(line) if isinstance(lines, dict) else None
    return value if value in (0, 1) and not isinstance(value, bool) else None


def _saver_names(data: dict[str, Any]) -> tuple[str, ...]:
    value = data.get("savers")
    if not isinstance(value, list):
        return ()
    return tuple(v for v in value if is_saver_name(v) and v != SAVER_OFF)


def _led_count(data: dict[str, Any]) -> int:
    value = data.get("leds")
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return min(max(value, 0), 64)


def _max_line(data: dict[str, Any]) -> int:
    value = data.get("max_line")
    if isinstance(value, bool) or not isinstance(value, int):
        return MAX_LINE_LENGTH
    return min(max(value, MIN_LINE_LENGTH), MAX_LINE_LENGTH)


def parse_device_message(data: dict[str, Any]) -> DeviceMessage | None:
    """Zamienia słownik od urządzenia na obiekt. Nieznany typ → None (ignorujemy)."""
    kind = data.get("type")
    if kind == "hello":
        device = data.get("device")
        if device != "chocpilot":
            raise ProtocolError("not a chocpilot device")
        return DeviceInfo(
            device=device,
            fw=str(data.get("fw", "?")),
            board=str(data.get("board", "?")),
            keys=_int(data, "keys", KEY_COUNT),
            encoder=bool(data.get("encoder", False)),
            leds=_led_count(data),
            savers=_saver_names(data),
            icon_size=data["icon"] if data.get("icon") == 32 else 0,
            hid=bool(data.get("hid", True)),
            has_diag="oled" in data,
            oled_addr=oled if isinstance(oled := data.get("oled"), int) else None,
            i2c_devices=tuple(
                a for a in data.get("i2c", []) or [] if isinstance(a, int) and 0 <= a < 128
            ),
            sda_level=_level(data, "sda"),
            scl_level=_level(data, "scl"),
            swapped=data.get("swapped") is True,
            max_line=_max_line(data),
        )
    if kind == "key":
        key = _int(data, "key")
        if not 1 <= key <= KEY_COUNT:
            raise ProtocolError("key out of range")
        action = data.get("action")
        if action not in ("down", "up"):
            raise ProtocolError("bad key action")
        return KeyEvent(key=key, down=action == "down", t=_int(data, "t", 0))
    if kind == "ack":
        return AckEvent(id=_int(data, "id"))
    if kind == "error":
        raw_id = data.get("id")
        return ErrorEvent(
            id=raw_id if isinstance(raw_id, int) else None, msg=str(data.get("msg", ""))
        )
    if kind == "log":
        return LogEvent(level=str(data.get("level", "info")), msg=str(data.get("msg", "")))
    if kind == "test":
        return TestModeEvent(active=bool(data.get("active", False)))
    if kind == "encoder":
        index = _encoder_index(data)
        delta = _int(data, "delta")
        if delta == 0:
            raise ProtocolError("encoder delta is zero")
        return EncoderEvent(index=index, delta=delta, t=_int(data, "t", 0))
    if kind == "encoder_key":
        index = _encoder_index(data)
        action = data.get("action")
        if action not in ("down", "up"):
            raise ProtocolError("bad encoder_key action")
        return EncoderKeyEvent(index=index, down=action == "down", t=_int(data, "t", 0))
    if kind == "slider":
        value = _int(data, "value")
        if not 0 <= value <= SLIDER_MAX:
            raise ProtocolError("slider value out of range")
        return SliderEvent(value=value, t=_int(data, "t", 0))
    return None


def _encoder_index(data: dict[str, Any]) -> int:
    index = _int(data, "index")
    if not 1 <= index <= ENCODER_COUNT:
        raise ProtocolError("encoder index out of range")
    return index

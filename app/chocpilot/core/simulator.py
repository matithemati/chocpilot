"""Symulator urządzenia ChocPilot – ta sama logika protokołu co firmware, bez sprzętu.

`SimulatedDevice` jest czysty (bez Qt); okno symulatora (gui/simulator_window.py) tylko go
wyświetla i przekazuje kliknięcia. `SimulatorTransport` łączy go z kontrolerem w procesie,
z pełnym kodowaniem/dekodowaniem JSON (testuje też protokół).
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from . import leds, protocol, savers
from .protocol import ProtocolError
from .transport import ConnectionState, Transport

log = logging.getLogger("chocpilot.simulator")

FW_VERSION = "1.0.0-sim"
# Płytki z krótszym buforem odbioru (firmware CHOCPILOT_COMPACT) – limit zgłaszany w hello.
BOARD_MAX_LINE = {"promicro": 272, "chocpilot_v0": 272}
# Płytki z pokrętłami i suwakiem (encoder: true w hello).
BOARDS_WITH_CONTROLS = {"chocpilot_v0"}
# Liczba diod podświetlenia (leds w hello).
BOARD_LEDS = {"chocpilot_v0": leds.LED_COUNT}
# Płytki z ikonami klawiszy (icon w hello) – LCD.
BOARD_ICONS = {"chocpilot_v0": 32}
# Animacje wygaszacza (savers w hello) – płytki z LCD.
BOARD_SAVERS = {"chocpilot_v0": savers.NAMES}


@dataclass(frozen=True)
class Screen:
    """Co jest na ekranie urządzenia (do narysowania przez GUI: OLED albo LCD)."""

    kind: str  # splash | offline | idle | profile | grid | text | bar | flash | test | off
    title: str = ""
    labels: tuple[str, ...] = ()
    line1: str = ""
    line2: str = ""
    value: int = 0
    key: int | None = None
    online: bool = False
    test_keys: tuple[bool, ...] = ()
    # Tryb testu na LCD (ChocPilot v0): suma obrotów pokręteł, przyciski pokręteł, suwak 0–100.
    saver: str = ""  # kind="saver": nazwa animacji wygaszacza
    saver_ms: int = 0  # czas od startu animacji
    clock: str = ""  # kind="saver": godzina HH:MM z aplikacji (pusto = zegar nieustawiony)
    icons: tuple[bytes | None, ...] = ()  # kind="grid": kompletne ikony klawiszy (544 B) albo None
    test_encoders: tuple[int, ...] = ()
    test_encoder_keys: tuple[bool, ...] = ()
    test_slider: int = 0
    flip: bool = False
    brightness: int = 128


@dataclass
class SimulatedDevice:
    board: str = "promicro"
    clock: Callable[[], float] = time.monotonic
    emit: Callable[[dict[str, Any]], None] = lambda message: None
    settings: dict[str, Any] = field(
        default_factory=lambda: {
            "brightness": 128,
            "screensaver_s": 300,
            "flip": False,
            "debounce_ms": 8,
            "oled_addr": 0x3C,
            "saver": "off",
        }
    )
    fallback: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "5": {"media": "vol_down"},
            "6": {"media": "vol_up"},
            "7": {"media": "play_pause"},
            "8": {"media": "mute"},
        }
    )

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._start = self.clock()
        self._last_rx: float | None = None
        self._base = Screen(kind="idle")
        self._overlay: Screen | None = None
        self._overlay_until = 0.0
        self._flash: Screen | None = None
        self._flash_until = 0.0
        self._last_activity = self._start
        self._pressed = [False] * protocol.KEY_COUNT
        self._test_mode = False
        self._test_encoders = [0] * protocol.ENCODER_COUNT
        self._encoder_down = [False] * protocol.ENCODER_COUNT
        self._slider = 0
        # Podświetlenie: zapisane (jak w EEPROM) i stosowane teraz (z kolorem profilu save:false).
        self.leds_saved = leds.LedState()
        self.leds_live = leds.LedState()
        self._key_down_ms: dict[int, int] = {}
        # Zegar z komendy time: (sekunda doby, czas symulatora w chwili ustawienia).
        self._wall_clock: tuple[int, float] | None = None
        # Ikony jak IconStore w firmware: bufor i liczba bajtów zapisanych po kolei.
        self._icon_buf = [bytearray(protocol.ICON_BYTES) for _ in range(protocol.KEY_COUNT)]
        self._icon_filled = [0] * protocol.KEY_COUNT
        self.debug = False
        self.hid_log: list[str] = []  # co zostałoby wysłane przez HID w trybie offline

    # ------------------------------------------------------------------ czas i stan

    def _ms(self) -> int:
        return int((self.clock() - self._start) * 1000)

    @property
    def online(self) -> bool:
        with self._lock:
            return (
                self._last_rx is not None
                and self.clock() - self._last_rx < protocol.HEARTBEAT_TIMEOUT_S
            )

    def screen(self) -> Screen:
        """Aktualny obraz ekranu (uwzględnia wygaszacz, nakładki i tryb offline)."""
        with self._lock:
            now = self.clock()
            flip = bool(self.settings["flip"])
            brightness = int(self.settings["brightness"])
            if now - self._start < 1.5:
                return Screen(kind="splash", flip=flip, brightness=brightness)
            saver_s = int(self.settings["screensaver_s"])
            idle = now - self._last_activity
            if saver_s and not self._test_mode and idle >= saver_s:
                name = str(self.settings.get("saver", "off"))
                if name in BOARD_SAVERS.get(self.board, ()):
                    return Screen(
                        kind="saver",
                        saver=name,
                        saver_ms=int((idle - saver_s) * 1000),
                        clock=self._clock_text(now),
                        flip=flip,
                        brightness=brightness,
                    )
                return Screen(kind="off")
            if self._test_mode:
                return Screen(
                    kind="test",
                    test_keys=tuple(self._pressed),
                    test_encoders=tuple(self._test_encoders),
                    test_encoder_keys=tuple(self._encoder_down),
                    test_slider=self._slider,
                    flip=flip,
                    brightness=brightness,
                )
            online = self.online
            if self._flash is not None and now < self._flash_until:
                return replace(self._flash, online=online, flip=flip, brightness=brightness)
            if not online:
                return Screen(kind="offline", flip=flip, brightness=brightness)
            if self._overlay is not None and now < self._overlay_until:
                return replace(self._overlay, online=online, flip=flip, brightness=brightness)
            base = self._base
            if base.kind == "grid" and self.board in BOARD_ICONS:
                base = replace(base, icons=self.icons())
            return replace(base, online=online, flip=flip, brightness=brightness)

    # ------------------------------------------------------------------ wejścia (UI)

    def press(self, key: int) -> None:
        self._key(key, True)

    def release(self, key: int) -> None:
        self._key(key, False)

    def _key(self, key: int, down: bool) -> None:
        with self._lock:
            if self._pressed[key - 1] == down:
                return
            self._pressed[key - 1] = down
            self._last_activity = self.clock()
            if down:
                self._key_down_ms[key] = self._ms()
            offline = not self.online
        self.emit({"type": "key", "key": key, "action": "down" if down else "up", "t": self._ms()})
        if offline and down:
            self._hid(str(key))

    # Pokrętła i suwak (tylko płytki z BOARDS_WITH_CONTROLS, jak ChocPilot v0).

    @property
    def has_controls(self) -> bool:
        return self.board in BOARDS_WITH_CONTROLS

    def turn(self, index: int, delta: int) -> None:
        if not self.has_controls or delta == 0:
            return
        self._activity()
        with self._lock:
            if self._test_mode:
                self._test_encoders[index - 1] += delta
        self.emit({"type": "encoder", "index": index, "delta": delta, "t": self._ms()})

    def press_encoder(self, index: int) -> None:
        self._encoder_key(index, True)

    def release_encoder(self, index: int) -> None:
        self._encoder_key(index, False)

    def _encoder_key(self, index: int, down: bool) -> None:
        if not self.has_controls:
            return
        self._activity()
        with self._lock:
            self._encoder_down[index - 1] = down
        self.emit(
            {
                "type": "encoder_key",
                "index": index,
                "action": "down" if down else "up",
                "t": self._ms(),
            }
        )

    def move_slider(self, value: int) -> None:
        if not self.has_controls:
            return
        self._activity()
        value = max(0, min(protocol.SLIDER_MAX, int(value)))
        with self._lock:
            self._slider = value
        self.emit({"type": "slider", "value": value, "t": self._ms()})

    def _activity(self) -> None:
        with self._lock:
            self._last_activity = self.clock()

    def _hid(self, slot: str) -> None:
        binding = self.fallback.get(slot)
        if binding:
            self.hid_log.append(f"{slot}: {binding}")
            log.info("[symulator HID] %s → %s", slot, binding)

    # ------------------------------------------------------------------ protokół

    @property
    def max_line(self) -> int:
        return BOARD_MAX_LINE.get(self.board, protocol.MAX_LINE_LENGTH)

    def handle_line(self, line: bytes) -> None:
        if len(line.rstrip(b"\r\n")) >= self.max_line:
            self.emit({"type": "error", "msg": "line too long"})  # jak firmware
            return
        try:
            message = protocol.decode(line)
        except ProtocolError as exc:
            self.emit({"type": "error", "msg": str(exc)})
            return
        self.handle(message)

    def handle(self, message: dict[str, Any]) -> None:
        msg_id = message.get("id")
        has_id = isinstance(msg_id, int) and not isinstance(msg_id, bool)
        try:
            known = self._dispatch(message)
        except ProtocolError as exc:
            reply: dict[str, Any] = {"type": "error", "msg": str(exc)}
            if has_id:
                reply["id"] = msg_id
            self.emit(reply)
            return
        if known and has_id and message.get("type") != "reboot":
            self.emit({"type": "ack", "id": msg_id})

    def _hello(self) -> dict[str, Any]:
        hello = {
            "type": "hello",
            "device": "chocpilot",
            "fw": FW_VERSION,
            "board": self.board,
            "keys": protocol.KEY_COUNT,
            "encoder": self.has_controls,
            "hid": True,
            "online": self.online,
        }
        if self.led_count:
            hello["leds"] = self.led_count
        if self.board in BOARD_SAVERS:
            hello["savers"] = list(BOARD_SAVERS[self.board])
        if self.board in BOARD_ICONS:
            hello["icon"] = BOARD_ICONS[self.board]
        if not self.has_controls:  # LCD ChocPilot v0 nie ma diagnostyki I²C
            hello["oled"] = 0x3C
            hello["i2c"] = [0x3C]
        if self.board in BOARD_MAX_LINE:
            hello["max_line"] = self.max_line
        return hello

    def _dispatch(self, message: dict[str, Any]) -> bool:
        kind = message["type"]
        with self._lock:
            self._last_rx = self.clock()
        if kind == "hello" or kind == "get_info":
            self.emit(self._hello())
        elif kind == "ping":
            pass
        elif kind == "display":
            self._display(message)
        elif kind == "flash":
            text = message.get("text")
            if not isinstance(text, str):
                raise ProtocolError("missing text")
            ms = int(message.get("ms", 1000))
            with self._lock:
                self._flash = Screen(kind="flash", line1=text[:21], key=message.get("key"))
                self._flash_until = self.clock() + ms / 1000
                self._last_activity = self.clock()
        elif kind == "settings":
            updates = {k: v for k, v in message.items() if k in protocol.SETTINGS_FIELDS}
            protocol.msg_settings(**updates)  # ta sama walidacja co firmware
            with self._lock:
                self.settings.update(updates)
        elif kind == "set_fallback":
            self._set_fallback(message)
        elif kind == "reboot":
            msg_id = message.get("id")
            if isinstance(msg_id, int):
                self.emit({"type": "ack", "id": msg_id})
            with self._lock:
                self._last_rx = None
                self._start = self.clock()
            self.emit(self._hello())
        elif kind == "test_mode":
            with self._lock:
                self._test_mode = bool(message.get("enable", True))
                self._test_encoders = [0] * protocol.ENCODER_COUNT  # suma od wejścia w test
            self.emit({"type": "test", "active": self._test_mode})
        elif kind == "debug":
            self.debug = bool(message.get("enable", True))
        elif kind == "leds":
            self._leds(message)
        elif kind == "icon":
            self._icon(message)
        elif kind == "time":
            values = [message.get(k, 0) for k in ("hour", "minute", "second")]
            if not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
                raise ProtocolError("integer expected")
            protocol.msg_time(*values)  # ta sama walidacja co firmware
            with self._lock:
                self._wall_clock = (values[0] * 3600 + values[1] * 60 + values[2], self.clock())
        else:
            return False
        return True

    # ------------------------------------------------------------------ podświetlenie

    @property
    def led_count(self) -> int:
        return BOARD_LEDS.get(self.board, 0)

    def _leds(self, message: dict[str, Any]) -> None:
        fields = ("mode", "color", "brightness", "speed", "react")
        values = {k: message[k] for k in fields if k in message}
        save = message.get("save", True)
        if not isinstance(save, bool):
            raise ProtocolError("save: bool expected")
        protocol.msg_leds(**values, save=save)  # ta sama walidacja co firmware
        if "color" in values:
            values["color"] = values["color"].lower()
        if not self.led_count:
            return  # płytka bez diod (Pro Micro) – komenda bez efektu, jak w firmware
        with self._lock:
            self.leds_live = replace(self.leds_live, **values)
            if save:
                self.leds_saved = replace(self.leds_saved, **values)

    def _icon(self, message: dict[str, Any]) -> None:
        key = message.get("key")
        if not isinstance(key, int) or isinstance(key, bool) or not 1 <= key <= protocol.KEY_COUNT:
            raise ProtocolError("value out of range")
        if self.board not in BOARD_ICONS:
            return  # bez LCD – komenda ignorowana, jak w firmware
        slot = key - 1
        if message.get("clear") is True:
            with self._lock:
                self._icon_filled[slot] = 0
            return
        offset = message.get("offset", 0)
        try:
            data = base64.b64decode(str(message.get("data", "")), validate=True)
        except ValueError as exc:
            raise ProtocolError("bad icon data") from exc
        if not isinstance(offset, int) or not data or offset + len(data) > protocol.ICON_BYTES:
            raise ProtocolError("bad icon data")
        with self._lock:
            if offset == 0:
                self._icon_filled[slot] = 0
            if offset != self._icon_filled[slot]:
                return  # zgubiony kawałek – czekamy na offset 0
            self._icon_buf[slot][offset : offset + len(data)] = data
            self._icon_filled[slot] = offset + len(data)

    def icons(self) -> tuple[bytes | None, ...]:
        with self._lock:
            return tuple(
                bytes(buf) if filled == protocol.ICON_BYTES else None
                for buf, filled in zip(self._icon_buf, self._icon_filled, strict=True)
            )

    def _clock_text(self, now: float) -> str:
        """HH:MM jak WallClock w firmware (liczy dalej od ostatniej komendy time)."""
        if self._wall_clock is None:
            return ""
        seconds_at_sync, synced = self._wall_clock
        seconds = (seconds_at_sync + int(now - synced)) % 86400
        return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}"

    def led_colors(self) -> list[leds.Rgb]:
        """Kolory diod teraz (jak firmware: wygaszacz, tryb testu, błysk klawiszy)."""
        if not self.led_count:
            return []
        screen = self.screen()
        with self._lock:
            state = self.leds_live if self.online else self.leds_saved
            return leds.render(
                state,
                self._ms(),
                online=self.online,
                sleeping=screen.kind in ("off", "saver"),
                test=self._test_mode,
                key_down_at=dict(self._key_down_ms),
                count=self.led_count,
            )

    def _display(self, message: dict[str, Any]) -> None:
        mode = message.get("mode")
        ms = int(message.get("ms", 0) or 0)
        if mode == "profile":
            screen = Screen(kind="profile", title=str(message.get("name", ""))[:21])
        elif mode == "grid":
            labels = message.get("labels", [])
            count = protocol.KEY_COUNT
            if not isinstance(labels, list) or len(labels) > count:
                raise ProtocolError("labels must be an array")
            padded = [str(x or "")[: protocol.LABEL_CHARS] for x in labels]
            padded += [""] * (count - len(labels))
            screen = Screen(
                kind="grid", title=str(message.get("title", ""))[:21], labels=tuple(padded)
            )
        elif mode == "text":
            screen = Screen(
                kind="text",
                line1=str(message.get("line1", ""))[:21],
                line2=str(message.get("line2", ""))[:21],
            )
        elif mode == "bar":
            value = max(0, min(100, int(message.get("value", 0))))
            screen = Screen(kind="bar", title=str(message.get("title", ""))[:21], value=value)
        else:
            raise ProtocolError("unknown display mode")
        with self._lock:
            if mode in ("text", "bar") and ms > 0:
                self._overlay = screen
                self._overlay_until = self.clock() + ms / 1000
            else:
                self._base = screen
                self._overlay = None

    def _set_fallback(self, message: dict[str, Any]) -> None:
        bindings = message.get("bindings")
        if bindings is None and "key" in message:
            bindings = [message]
        if not isinstance(bindings, list):
            if message.get("replace"):
                bindings = []
            else:
                raise ProtocolError("missing key or bindings")
        parsed: dict[str, dict[str, Any]] = {}
        for item in bindings:
            slot = str(item.get("key"))
            if slot not in {str(i) for i in range(1, protocol.KEY_COUNT + 1)}:
                raise ProtocolError("unknown key")
            if item.get("media") and item.get("code"):
                raise ProtocolError("use either code or media")
            parsed[slot] = {k: v for k, v in item.items() if k in ("mods", "code", "media")}
        with self._lock:
            if message.get("replace"):
                self.fallback = {}
            self.fallback.update(parsed)


class SimulatorTransport(Transport):
    """Transport w procesie: kontroler ↔ SimulatedDevice (przez kodowanie JSON)."""

    def __init__(self, device: SimulatedDevice) -> None:
        super().__init__()
        self.device = device
        device.emit = self._from_device
        self._started = False

    def start(self) -> None:
        self._started = True
        # Jak prawdziwy transport: handshake hello.
        self._set_state(ConnectionState.CONNECTING)
        self.device.handle_line(protocol.encode(protocol.msg_hello("sim")))

    def stop(self) -> None:
        self._started = False
        self._set_state(ConnectionState.DISCONNECTED)

    def send(self, message: dict[str, Any]) -> bool:
        if not self._started:
            return False
        self.device.handle_line(protocol.encode(message))
        self._notify_sent(message)
        return True

    def _from_device(self, message: dict[str, Any]) -> None:
        data = protocol.decode(protocol.encode(message))
        if data["type"] == "hello" and self.state != ConnectionState.CONNECTED:
            info = protocol.parse_device_message(data)
            if isinstance(info, protocol.DeviceInfo):
                self._set_state(ConnectionState.CONNECTED, info, "symulator")
        self.on_message(data)

"""Wspólna obsługa klawiatury i myszy przez pynput (Windows, macOS)."""

from __future__ import annotations

import threading
import time
from typing import Any

from .base import PlatformError

# Nazwa klawisza ChocPilot → atrybut pynput.keyboard.Key. Część klawiszy nie istnieje na
# każdym systemie (np. insert/printscreen na macOS) – wtedy PlatformError przy użyciu.
SPECIAL_KEYS = {
    "ctrl": "ctrl", "shift": "shift", "alt": "alt", "win": "cmd",
    "enter": "enter", "esc": "esc", "tab": "tab", "space": "space",
    "backspace": "backspace", "delete": "delete", "insert": "insert",
    "home": "home", "end": "end", "pageup": "page_up", "pagedown": "page_down",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "capslock": "caps_lock", "printscreen": "print_screen",
    "scrolllock": "scroll_lock", "pause": "pause", "menu": "menu",
    "numlock": "num_lock",
    "media_play_pause": "media_play_pause", "media_next": "media_next",
    "media_prev": "media_previous", "media_stop": "media_stop",
    "media_vol_up": "media_volume_up", "media_vol_down": "media_volume_down",
    "media_mute": "media_volume_mute",
}  # fmt: skip

MEDIA_TO_KEY = {
    "play_pause": "media_play_pause",
    "next": "media_next",
    "prev": "media_prev",
    "stop": "media_stop",
    "vol_up": "media_vol_up",
    "vol_down": "media_vol_down",
    "mute": "media_mute",
}


def pynput_key(name: str) -> Any:
    from pynput.keyboard import Key, KeyCode

    attr = SPECIAL_KEYS.get(name)
    if attr is None and name.startswith("f") and name[1:].isdigit():
        attr = name
    if attr is not None:
        key = getattr(Key, attr, None)
        if key is None:
            raise PlatformError(f"klawisz {name} nie jest dostępny w tym systemie")
        return key
    if name == "plus":
        return KeyCode.from_char("+")
    if len(name) == 1:
        return KeyCode.from_char(name)
    raise PlatformError(f"nieznany klawisz {name}")


class PynputInput:
    """Klawiatura i mysz: skróty, wpisywanie tekstu, klawisze multimedialne, przewijanie."""

    def __init__(self) -> None:
        self._kb_lock = threading.Lock()
        self._keyboard: Any = None
        self._mouse: Any = None

    def _kb(self) -> Any:
        if self._keyboard is None:
            from pynput.keyboard import Controller

            self._keyboard = Controller()
        return self._keyboard

    def send_hotkey(self, keys: list[str]) -> None:
        resolved = [pynput_key(k) for k in keys]
        kb = self._kb()
        with self._kb_lock:
            pressed = []
            try:
                for key in resolved:
                    kb.press(key)
                    pressed.append(key)
                time.sleep(0.01)
            finally:
                for key in reversed(pressed):
                    kb.release(key)

    def type_text(self, text: str) -> None:
        with self._kb_lock:
            self._kb().type(text)

    def media_key(self, name: str) -> None:
        key = pynput_key(MEDIA_TO_KEY[name])
        with self._kb_lock:
            self._kb().press(key)
            self._kb().release(key)

    def scroll(self, dx: int, dy: int) -> None:
        if self._mouse is None:
            from pynput.mouse import Controller

            self._mouse = Controller()
        self._mouse.scroll(dx, dy)

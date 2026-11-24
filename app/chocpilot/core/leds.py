"""Efekty podświetlenia LED – ten sam algorytm co firmware/lib/chocpilotcore/src/led_effects.cpp.

Używane przez symulator (podgląd diod) i testy; prawdziwa płytka liczy kolory sama.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .protocol import KEY_COUNT

LED_COUNT = 12
MAX_LEVEL = 80  # jasność 255 = 80/255 pełnej mocy diody (prąd USB)
REACT_MS = 400
# Dioda przy klawiszu K1…K8 (indeksy łańcucha L1…L12 od 0) – firmware/src/boards/board.h.
KEY_LED = (8, 9, 10, 11, 5, 4, 3, 2)

Rgb = tuple[int, int, int]

_ONLINE: Rgb = (0, 150, 180)
_OFFLINE: Rgb = (255, 110, 0)
_TEST: tuple[Rgb, ...] = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255))


@dataclass(frozen=True)
class LedState:
    """Ustawienia diod tak, jak trzyma je firmware (po komendach leds)."""

    mode: str = "status"
    color: str = "#00a0c0"
    brightness: int = 128
    speed: int = 5
    react: bool = True


def hex_to_rgb(color: str) -> Rgb:
    value = int(color.lstrip("#"), 16)
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF


def _scale8(value: int, level: int) -> int:
    return value * level // 255


def _scaled(c: Rgb, level: int) -> Rgb:
    return _scale8(c[0], level), _scale8(c[1], level), _scale8(c[2], level)


def hue_to_rgb(hue: int) -> Rgb:
    hue &= 0xFF
    region = hue // 43
    rem = ((hue - region * 43) * 6) & 0xFF
    up, down = rem, 255 - rem
    return (
        (255, up, 0),
        (down, 255, 0),
        (0, 255, up),
        (0, down, 255),
        (up, 0, 255),
        (255, 0, down),
    )[min(region, 5)]


def render(
    state: LedState,
    now_ms: int,
    *,
    online: bool = True,
    sleeping: bool = False,
    test: bool = False,
    key_down_at: Mapping[int, int] | None = None,
    count: int = LED_COUNT,
    key_led: Sequence[int] = KEY_LED,
) -> list[Rgb]:
    """Kolory `count` diod w chwili now_ms. key_down_at: klawisz (1–8) → czas naciśnięcia [ms]."""
    level = _scale8(state.brightness, MAX_LEVEL)
    if sleeping or (state.mode == "off" and not test):  # wygaszacz (także animowany) gasi diody
        return [(0, 0, 0)] * count
    if test:
        test_level = max(level, MAX_LEVEL // 2)
        return [_scaled(_TEST[(now_ms // 500) % 4], test_level)] * count

    color = hex_to_rgb(state.color)
    speed = min(max(state.speed, 1), 10)
    out: list[Rgb]
    if state.mode == "status":
        out = [_ONLINE if online else _OFFLINE] * count
    elif state.mode == "static":
        out = [color] * count
    elif state.mode == "breathe":
        period = 6000 - (speed - 1) * 550
        phase = (now_ms % period) * 512 // period
        tri = phase if phase < 256 else 511 - phase
        k = 30 + tri * tri * 225 // 65025
        out = [_scaled(color, k)] * count
    else:  # rainbow
        period = 12000 - (speed - 1) * 1150
        base = (now_ms % period) * 256 // period
        out = [hue_to_rgb(base + i * 256 // count) for i in range(count)]

    if state.react and key_down_at:
        for key, down_at in key_down_at.items():
            age = now_ms - down_at
            if not 1 <= key <= KEY_COUNT or not 0 <= age < REACT_MS:
                continue
            led = key_led[key - 1]
            if led >= count:
                continue
            mix = (REACT_MS - age) * 255 // REACT_MS
            r, g, b = out[led]
            out[led] = (
                r + _scale8(255 - r, mix),
                g + _scale8(255 - g, mix),
                b + _scale8(255 - b, mix),
            )

    return [_scaled(c, level) for c in out]

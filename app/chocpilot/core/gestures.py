"""Rozpoznawanie gestów (tap, hold, double tap) z surowych zdarzeń down/up klawiszy.

Logika jest czysta (czas podawany z zewnątrz), więc łatwo ją testować. Silnik wywołuje
`tick(now)` cyklicznie; `next_deadline()` mówi, kiedy najpóźniej trzeba to zrobić.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from .protocol import KEY_COUNT


class Gesture(StrEnum):
    TAP = "tap"
    HOLD = "hold"
    DOUBLE_TAP = "double_tap"


KEY_GESTURES = (Gesture.TAP, Gesture.HOLD, Gesture.DOUBLE_TAP)


@dataclass(frozen=True)
class GestureEvent:
    key: int  # 1..8
    gesture: Gesture
    steps: int = 1  # liczba powtórzeń akcji
    t: float = 0.0


@dataclass
class GestureConfig:
    hold_ms: int = 500
    double_tap_ms: int = 300
    hold_on_threshold: bool = False  # hold w chwili przekroczenia progu (a nie po puszczeniu)


@dataclass
class _KeyState:
    pressed: bool = False
    down_at: float = 0.0
    hold_fired: bool = False
    consumed: bool = False  # naciśnięcie zużyte (double_tap) – puszczenie nic nie robi
    pending_tap_at: float | None = None  # puszczenie czekające na ewentualny double_tap


HasGesture = Callable[[int, Gesture], bool]
Emit = Callable[[GestureEvent], None]


@dataclass
class GestureEngine:
    config: GestureConfig
    emit: Emit
    has_gesture: HasGesture
    _keys: dict[int, _KeyState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._keys = {k: _KeyState() for k in range(1, KEY_COUNT + 1)}

    def is_pressed(self, key: int) -> bool:
        state = self._keys.get(key)
        return bool(state and state.pressed)

    # ------------------------------------------------------------------ wejścia

    def key_down(self, key: int, now_ms: float) -> None:
        state = self._keys.get(key)
        if state is None or state.pressed:
            return
        if state.pending_tap_at is not None:
            if now_ms - state.pending_tap_at <= self.config.double_tap_ms:
                state.pending_tap_at = None
                self._start_press(state, now_ms)
                state.consumed = True
                self.emit(GestureEvent(key, Gesture.DOUBLE_TAP, 1, now_ms))
                return
            # Okno minęło, a tick jeszcze nie przyszedł – najpierw zaległy tap.
            state.pending_tap_at = None
            self.emit(GestureEvent(key, Gesture.TAP, 1, now_ms))
        self._start_press(state, now_ms)

    def key_up(self, key: int, now_ms: float) -> None:
        state = self._keys.get(key)
        if state is None or not state.pressed:
            return
        state.pressed = False
        if state.consumed or state.hold_fired:
            return
        duration = now_ms - state.down_at
        if duration >= self.config.hold_ms and self.has_gesture(key, Gesture.HOLD):
            self.emit(GestureEvent(key, Gesture.HOLD, 1, now_ms))
            return
        if self.has_gesture(key, Gesture.DOUBLE_TAP):
            state.pending_tap_at = now_ms
            return
        self.emit(GestureEvent(key, Gesture.TAP, 1, now_ms))

    def tick(self, now_ms: float) -> None:
        for key, state in self._keys.items():
            if (
                state.pressed
                and self.config.hold_on_threshold
                and not (state.hold_fired or state.consumed)
                and now_ms - state.down_at >= self.config.hold_ms
                and self.has_gesture(key, Gesture.HOLD)
            ):
                state.hold_fired = True
                self.emit(GestureEvent(key, Gesture.HOLD, 1, now_ms))
            if (
                state.pending_tap_at is not None
                and now_ms - state.pending_tap_at > self.config.double_tap_ms
            ):
                state.pending_tap_at = None
                self.emit(GestureEvent(key, Gesture.TAP, 1, now_ms))

    def next_deadline(self) -> float | None:
        """Najbliższa chwila (ms), w której tick() może coś wyemitować."""
        deadlines: list[float] = []
        for state in self._keys.values():
            if state.pending_tap_at is not None:
                deadlines.append(state.pending_tap_at + self.config.double_tap_ms + 1)
            if (
                state.pressed
                and self.config.hold_on_threshold
                and not (state.hold_fired or state.consumed)
            ):
                deadlines.append(state.down_at + self.config.hold_ms)
        return min(deadlines) if deadlines else None

    # ------------------------------------------------------------------ pomocnicze

    @staticmethod
    def _start_press(state: _KeyState, now_ms: float) -> None:
        state.pressed = True
        state.down_at = now_ms
        state.hold_fired = False
        state.consumed = False

"""Przekazywanie zdarzeń kontrolera (z wątków roboczych) do wątku GUI przez sygnały Qt."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..core.actions import ActionBase
from ..core.config import Profile
from ..core.engine import ControllerListener
from ..core.gestures import GestureEvent
from ..core.logbuffer import LogEntry
from ..core.protocol import DeviceInfo


class QtBridge(QObject, ControllerListener):
    connectionChanged = Signal(bool, object, object)  # connected, DeviceInfo|None, port|None
    rawInput = Signal(int, bool)  # klawisz, wciśnięty  # key|None, down, steps
    encoderInput = Signal(int, int)  # pokrętło 1–2, delta (zatrzaski)
    encoderKeyInput = Signal(int, bool)  # pokrętło 1–2, przycisk wciśnięty
    sliderInput = Signal(int)  # położenie suwaka 0–100
    gestureFired = Signal(object, object)  # GestureEvent, ActionBase|None
    profileChanged = Signal(object, str)  # Profile, reason
    actionFinished = Signal(str, object)  # summary, error|None
    testModeChanged = Signal(bool)
    klipperChanged = Signal(bool, str, object)  # aktywny, drukarka, PrinterStatus|None
    logEntry = Signal(object)  # LogEntry

    # Metody ControllerListener – emitują sygnały (połączenia kolejkowane do wątku GUI)
    def connection_changed(
        self, connected: bool, info: DeviceInfo | None, port: str | None
    ) -> None:
        self.connectionChanged.emit(connected, info, port)

    def raw_input(self, key: int, down: bool) -> None:
        self.rawInput.emit(key, down)

    def encoder_input(self, index: int, delta: int) -> None:
        self.encoderInput.emit(index, delta)

    def encoder_key_input(self, index: int, down: bool) -> None:
        self.encoderKeyInput.emit(index, down)

    def slider_input(self, value: int) -> None:
        self.sliderInput.emit(value)

    def gesture(self, event: GestureEvent, action: ActionBase | None) -> None:
        self.gestureFired.emit(event, action)

    def profile_changed(self, profile: Profile, reason: str) -> None:
        self.profileChanged.emit(profile, reason)

    def action_finished(self, summary: str, error: BaseException | None) -> None:
        self.actionFinished.emit(summary, error)

    def test_mode_changed(self, active: bool) -> None:
        self.testModeChanged.emit(active)

    def klipper_changed(self, active: bool, printer: str, status: object) -> None:
        self.klipperChanged.emit(active, printer, status)

    def on_log(self, entry: LogEntry) -> None:
        self.logEntry.emit(entry)

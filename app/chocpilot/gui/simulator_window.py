"""Okno symulatora ChocPilot: 8 klawiszy w układzie 2×4 i podgląd OLED 128×64."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.protocol import KEY_COLS, KEY_COUNT
from ..core.simulator import SimulatedDevice
from .icons import app_icon
from .oled import OledView


class SimulatorWindow(QWidget):
    def __init__(self, device: SimulatedDevice, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.device = device
        self.setWindowTitle("ChocPilot – symulator urządzenia")
        self.setWindowIcon(app_icon("connected"))
        self.oled = OledView(scale=3)

        grid = QGridLayout()
        for k in range(1, KEY_COUNT + 1):
            button = QPushButton(f"K{k}")
            button.setMinimumSize(80, 64)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            button.pressed.connect(lambda k=k: device.press(k))
            button.released.connect(lambda k=k: device.release(k))
            grid.addWidget(button, (k - 1) // KEY_COLS, (k - 1) % KEY_COLS)

        self.status = QLabel()
        self.hid = QPlainTextEdit()
        self.hid.setReadOnly(True)
        self.hid.setMaximumHeight(80)
        self.hid.setPlaceholderText("Tryb awaryjny HID (offline): wysłane skróty pojawią się tutaj")

        layout = QVBoxLayout(self)
        layout.addWidget(self.oled, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(grid, 1)
        layout.addWidget(self.status)
        layout.addWidget(self.hid)
        self.resize(440, 520)

        self._hid_count = 0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    def _refresh(self) -> None:
        self.oled.show_screen(self.device.screen())
        self.status.setText(
            f"Płytka: {self.device.board} • {'online' if self.device.online else 'OFFLINE (HID)'}"
        )
        if len(self.device.hid_log) != self._hid_count:
            for line in self.device.hid_log[self._hid_count :]:
                self.hid.appendPlainText(line)
            self._hid_count = len(self.device.hid_log)

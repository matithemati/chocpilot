"""Okno symulatora ChocPilot: 8 klawiszy 2×4 i podgląd ekranu (OLED 128×64 albo LCD 320×240)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.protocol import BOARD_SCREENS, ENCODER_COUNT, KEY_COLS, KEY_COUNT, SLIDER_MAX
from ..core.simulator import SimulatedDevice
from .icons import app_icon
from .oled import OledView


class LedStrip(QWidget):
    """Podgląd 12 diod podświetlenia (kolory jak z firmware, rozjaśnione do oglądania)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.colors: list[tuple[int, int, int]] = []
        self.setFixedHeight(22)
        self.setToolTip("Podświetlenie LED L1–L12")

    def set_colors(self, colors: list[tuple[int, int, int]]) -> None:
        if colors != self.colors:
            self.colors = colors
            self.update()

    def paintEvent(self, event) -> None:
        if not self.colors:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self.colors)
        step = self.width() / n
        d = min(step - 4, self.height() - 4)
        for i, (r, g, b) in enumerate(self.colors):
            # Firmware ogranicza jasność do ok. 1/3 – w podglądzie skala z powrotem do 0–255.
            peak = max(r, g, b, 1)
            k = min(255 / peak, 3.2) if peak > 2 else 0
            color = QColor(min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))
            p.setPen(QColor("#222"))
            p.setBrush(color if peak > 2 else QColor("#111"))
            x = i * step + (step - d) / 2
            p.drawEllipse(QRectF(x, (self.height() - d) / 2, d, d))
        p.end()


class SimulatorWindow(QWidget):
    def __init__(self, device: SimulatedDevice, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.device = device
        self.setWindowTitle("ChocPilot – symulator urządzenia")
        self.setWindowIcon(app_icon("connected"))
        self.oled = OledView(scale=3, screen_type=BOARD_SCREENS.get(device.board, "oled"))

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
        self.led_strip = LedStrip()
        self.led_strip.setVisible(bool(device.led_count))
        layout.addWidget(self.led_strip)
        if device.has_controls:
            layout.addLayout(self._controls(device))
        layout.addWidget(self.status)
        layout.addWidget(self.hid)
        self.resize(440, 520)

        self._hid_count = 0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

    @staticmethod
    def _controls(device: SimulatedDevice) -> QHBoxLayout:
        """Pokrętła (↺ / naciśnięcie / ↻) i suwak – ChocPilot v0."""
        row = QHBoxLayout()
        for i in range(1, ENCODER_COUNT + 1):
            for text, delta in ((f"E{i} ↺", -1), (f"E{i} ●", 0), (f"E{i} ↻", 1)):
                button = QPushButton(text)
                if delta == 0:
                    button.pressed.connect(lambda i=i: device.press_encoder(i))
                    button.released.connect(lambda i=i: device.release_encoder(i))
                else:
                    button.clicked.connect(lambda _=False, i=i, d=delta: device.turn(i, d))
                row.addWidget(button)
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setRange(0, SLIDER_MAX)
        slider.setToolTip("Suwak 0–100 %")
        slider.valueChanged.connect(device.move_slider)
        row.addWidget(slider)
        return row

    def _refresh(self) -> None:
        self.oled.show_screen(self.device.screen())
        if self.device.led_count:
            self.led_strip.set_colors(self.device.led_colors())
        self.status.setText(
            f"Płytka: {self.device.board} • {'online' if self.device.online else 'OFFLINE (HID)'}"
        )
        if len(self.device.hid_log) != self._hid_count:
            for line in self.device.hid_log[self._hid_count :]:
                self.hid.appendPlainText(line)
            self._hid_count = len(self.device.hid_log)

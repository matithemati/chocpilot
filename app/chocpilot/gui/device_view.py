"""Wizualny ChocPilot: ekran LCD nad siatką 2×4, pod nią pokrętła i suwak.
Podświetla fizyczne naciśnięcia, obroty i położenie suwaka na żywo."""

from __future__ import annotations

import math
from typing import ClassVar

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.actions import ActionBase
from ..core.config import EncoderBinding, Profile, SliderBinding
from ..core.protocol import ENCODER_COUNT, KEY_COLS, KEY_COUNT
from . import theme
from .i18n import action_summary, tr
from .lcd import LcdView
from .widgets import frame, label


def _font(base: QFont, size: float, bold: bool = False) -> QFont:
    f = QFont(base)
    f.setPointSizeF(theme.pt(size))
    f.setBold(bold)
    return f


class KeyTile(QWidget):
    clicked = Signal(int)

    def __init__(self, key: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self.label = ""
        self.summary = ""
        self.color = QColor("#455A64")
        self.gestures: list[str] = []
        self.icon = ""  # ikona zamiast etykiety (jak na ekranie LCD)
        self.selected = False
        self.hovered = False
        self.pressed_flash = 0.0
        self.setMinimumSize(120, 96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{tr('Klawisz')} K{key}")

    def set_binding(
        self, label: str, color: str, gestures: list[str], summary: str = "", icon: str = ""
    ) -> None:
        self.label = label
        self.icon = icon
        self.color = QColor(color) if QColor(color).isValid() else QColor("#455A64")
        self.gestures = gestures
        self.summary = summary
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)

    def enterEvent(self, event: object) -> None:
        self.hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hovered = False
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        surface = theme.color("surface")
        tint = QColor(self.color)
        tint.setAlpha(46 if theme.is_dark() else 22)
        # podświetlenie fizycznego naciśnięcia
        if self.pressed_flash > 0:
            glow = theme.color("accent")
            glow.setAlpha(int(70 * self.pressed_flash))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 17, 17)
        p.setPen(QPen(theme.color("border"), 1))
        p.setBrush(surface)
        p.drawRoundedRect(rect, 14, 14)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tint)
        p.drawRoundedRect(rect, 14, 14)
        if self.hovered and not self.selected:
            p.setPen(QPen(theme.color("faint"), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 14, 14)
        if self.selected or self.pressed_flash > 0:
            ring = theme.color("accent") if self.pressed_flash > 0 else theme.color("text")
            p.setPen(QPen(ring, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 13, 13)

        pad = 12
        inner = rect.adjusted(pad, 10, -pad, -10)
        # kropka koloru + numer
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.color)
        p.drawRoundedRect(QRectF(inner.left(), inner.top() + 4, 8, 8), 3, 3)
        small = _font(self.font(), 8, bold=True)
        p.setFont(small)
        p.setPen(theme.color("sub"))
        p.drawText(
            QRectF(inner.left() + 14, inner.top(), 60, 16),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            f"K{self.key}",
        )
        # znaczniki gestów
        badges = {"tap": "T", "hold": "H", "double_tap": "2×"}
        x = inner.right()
        for g in reversed(["tap", "hold", "double_tap"]):
            if g not in self.gestures:
                continue
            text = badges[g]
            w = 20 + 5 * (len(text) - 1)
            badge = QRectF(x - w, inner.top(), w, 17)
            p.setPen(QPen(theme.color("border"), 1))
            p.setBrush(theme.color("surface"))
            p.drawRoundedRect(badge, 5, 5)
            p.setPen(theme.color("sub"))
            p.setFont(_font(self.font(), 7.5, bold=True))
            p.drawText(badge, Qt.AlignmentFlag.AlignCenter, text)
            x -= w + 4
        # etykieta i opis akcji
        label_font = _font(self.font(), 12.5, bold=True)
        sum_font = _font(self.font(), 8.5)
        sum_h = 16 if self.summary else 0
        icon_drawn = False
        if self.icon:
            from .icon_library import library

            lib = library()
            if lib.entry(self.icon) is not None:
                size = 30
                image = lib.render(self.icon, size * 2, theme.tokens()["text"])
                target = QRectF(inner.left(), inner.bottom() - sum_h - size - 2, size, size)
                p.drawImage(target, image)
                icon_drawn = True
        if not icon_drawn:
            p.setFont(label_font)
            p.setPen(theme.color("text"))
            p.drawText(
                QRectF(inner.left(), inner.bottom() - sum_h - 26, inner.width(), 26),
                int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft),
                self.label or "—",
            )
        if self.summary:
            p.setFont(sum_font)
            p.setPen(theme.color("sub"))
            text = p.fontMetrics().elidedText(
                self.summary, Qt.TextElideMode.ElideRight, int(inner.width())
            )
            p.drawText(
                QRectF(inner.left(), inner.bottom() - sum_h, inner.width(), sum_h),
                int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft),
                text,
            )


class _ControlTile(QWidget):
    """Wspólne tło, obramowanie, zaznaczenie i podświetlenie kafelka pokrętła / suwaka."""

    clicked = Signal(str)

    FRAME_INSET = 4  # odstęp ramki od krawędzi (miejsce na poświatę)
    PAD_X, PAD_Y = 12, 10  # wnętrze ramki
    MAX_LINES = 3  # obrót w prawo, w lewo, naciśnięcie

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.label = ""
        self.selected = False
        self.hovered = False
        self.pressed_flash = 0.0
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # Wysokości wierszy z metryk czcionek – kafelek mieści wszystkie wiersze przy każdym DPI
    # i rozmiarze czcionki systemu (wcześniej stałe 92 px ucinały trzeci wiersz).
    def tag_height(self) -> float:
        return QFontMetricsF(_font(self.font(), 8, bold=True)).height() + 2

    def label_height(self) -> float:
        return QFontMetricsF(_font(self.font(), 11, bold=True)).height() + 4

    def line_height(self) -> float:
        return QFontMetricsF(_font(self.font(), 8)).height() + 2

    def header_height(self) -> float:
        return self.tag_height() + self.label_height()

    def sizeHint(self) -> QSize:
        content = self.header_height() + 4 + self.MAX_LINES * self.line_height()
        height = content + 2 * (self.FRAME_INSET + self.PAD_Y)
        return QSize(180, math.ceil(height))

    def minimumSizeHint(self) -> QSize:
        return QSize(150, self.sizeHint().height())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)

    def enterEvent(self, event: object) -> None:
        self.hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hovered = False
        self.update()

    def paint_frame(self, p: QPainter) -> QRectF:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        if self.pressed_flash > 0:
            glow = theme.color("accent")
            glow.setAlpha(int(70 * self.pressed_flash))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 17, 17)
        p.setPen(QPen(theme.color("border"), 1))
        p.setBrush(theme.color("surface"))
        p.drawRoundedRect(rect, 14, 14)
        if self.hovered and not self.selected:
            p.setPen(QPen(theme.color("faint"), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 14, 14)
        if self.selected or self.pressed_flash > 0:
            ring = theme.color("accent") if self.pressed_flash > 0 else theme.color("text")
            p.setPen(QPen(ring, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 13, 13)
        return rect.adjusted(self.PAD_X, self.PAD_Y, -self.PAD_X, -self.PAD_Y)

    def paint_texts(
        self,
        p: QPainter,
        area: QRectF,
        tag: str,
        lines: list[str],
        header_width: float | None = None,
    ) -> None:
        """Znacznik i nazwa (w szerokości header_width, np. obok pokrętła), pod nimi wiersze
        akcji na całą szerokość. Za długie teksty kończą się wielokropkiem."""
        head_w = area.width() if header_width is None else header_width
        left = int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        y = area.top()
        p.setFont(_font(self.font(), 8, bold=True))
        p.setPen(theme.color("sub"))
        p.drawText(QRectF(area.left(), y, head_w, self.tag_height()), left, tag)
        y += self.tag_height()
        p.setFont(_font(self.font(), 11, bold=True))
        p.setPen(theme.color("text"))
        name = p.fontMetrics().elidedText(
            self.label or "—", Qt.TextElideMode.ElideRight, int(head_w)
        )
        p.drawText(QRectF(area.left(), y, head_w, self.label_height()), left, name)
        y += self.label_height() + 4
        p.setFont(_font(self.font(), 8))
        p.setPen(theme.color("sub"))
        lh = self.line_height()
        for line in lines[: self.MAX_LINES]:
            text = p.fontMetrics().elidedText(line, Qt.TextElideMode.ElideRight, int(area.width()))
            p.drawText(QRectF(area.left(), y, area.width(), lh), left, text)
            y += lh


class EncoderTile(_ControlTile):
    """Pokrętło: wskaźnik obraca się przy fizycznym obrocie, kafelek świeci przy naciśnięciu."""

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(f"e{index}", parent)
        self.index = index
        self.lines: list[str] = []
        self.angle = 0.0
        self.setToolTip(f"{tr('Pokrętło')} E{index}")

    def set_binding(self, binding: EncoderBinding) -> None:
        self.label = binding.label
        arrows = (("cw", "↻"), ("ccw", "↺"), ("press", "●"))
        self.lines = [
            f"{mark} {action_summary(binding.action_for(g))}"
            for g, mark in arrows
            if binding.action_for(g) is not None
        ]
        self.update()

    def turn(self, delta: int) -> None:
        self.angle = (self.angle + 15 * delta) % 360  # 24 zatrzaski na pełny obrót rysunku
        self.pressed_flash = max(self.pressed_flash, 0.8)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        area = self.paint_frame(p)
        # Pokrętło w prawym górnym rogu obok nazwy; wiersze akcji pod nim na całą szerokość.
        knob = max(28.0, self.header_height() - 2)
        center = QPointF(area.right() - knob / 2, area.top() + knob / 2)
        p.setPen(QPen(theme.color("border"), 2))
        p.setBrush(theme.color("bg") if theme.is_dark() else theme.color("surface"))
        p.drawEllipse(center, knob / 2, knob / 2)
        rad = math.radians(self.angle - 90)
        tip = QPointF(
            center.x() + math.cos(rad) * knob * 0.36, center.y() + math.sin(rad) * knob * 0.36
        )
        p.setPen(QPen(theme.color("accent"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(
            QPointF(
                center.x() + math.cos(rad) * knob * 0.12, center.y() + math.sin(rad) * knob * 0.12
            ),
            tip,
        )
        self.paint_texts(
            p, area, f"E{self.index}", self.lines, header_width=area.width() - knob - 8
        )


class SliderTile(_ControlTile):
    """Suwak: uchwyt w położeniu z urządzenia (0 = lewa strona = dół suwaka)."""

    TARGETS: ClassVar[dict[str, str]] = {
        "off": "Wyłączony",
        "system_volume": "Głośność systemu",
        "app_volume": "Głośność",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("slider", parent)
        self.value: int | None = None
        self.summary = ""
        self.setToolTip(tr("Suwak"))

    def set_binding(self, binding: SliderBinding) -> None:
        self.label = binding.label
        summary = tr(self.TARGETS[binding.target])
        if binding.target == "app_volume":
            summary = f"{summary}: {binding.process or '?'}"
        self.summary = summary
        self.update()

    def set_value(self, value: int) -> None:
        self.value = value
        self.pressed_flash = max(self.pressed_flash, 0.5)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        area = self.paint_frame(p)
        value_text = f"{self.value}%" if self.value is not None else ""
        value_w = 40.0
        self.paint_texts(p, area, "S", [], header_width=area.width() - value_w)
        p.setFont(_font(self.font(), 8))
        p.setPen(theme.color("sub"))
        p.drawText(
            QRectF(
                area.left(), area.top() + self.header_height() + 4, area.width(), self.line_height()
            ),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            p.fontMetrics().elidedText(
                self.summary, Qt.TextElideMode.ElideRight, int(area.width())
            ),
        )
        p.drawText(
            QRectF(area.right() - value_w, area.top(), value_w, self.tag_height()),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
            value_text,
        )
        track = QRectF(area.left(), area.bottom() - 10, area.width(), 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.color("border"))
        p.drawRoundedRect(track, 3, 3)
        if self.value is not None:
            filled = QRectF(
                track.left(), track.top(), track.width() * self.value / 100, track.height()
            )
            p.setBrush(theme.color("accent"))
            p.drawRoundedRect(filled, 3, 3)
            p.drawEllipse(QPointF(filled.right(), track.center().y()), 7, 7)


class DeviceView(QWidget):
    keySelected = Signal(int)  # 1..8
    controlSelected = Signal(str)  # "e1", "e2", "slider"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.lcd = LcdView()
        self.lcd.setStyleSheet("background: transparent; border: none;")

        self.mode_chip = label("", "chip")
        lcd_head = QHBoxLayout()
        lcd_head.setSpacing(8)
        self.screen_label = label(tr('Ekran LCD 2"'), "lbl")
        lcd_head.addWidget(self.screen_label)
        lcd_head.addWidget(self.mode_chip)
        lcd_head.addStretch(1)
        lcd_frame = frame("lcd")
        of = QHBoxLayout(lcd_frame)
        of.setContentsMargins(10, 10, 10, 10)
        of.addWidget(self.lcd, 0, Qt.AlignmentFlag.AlignCenter)
        top = QVBoxLayout()
        top.setSpacing(8)
        top.addLayout(lcd_head)
        top.addWidget(lcd_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # Siatka 2 × 4 jak na płytce: K1–K4 u góry, K5–K8 na dole.
        grid = QGridLayout()
        grid.setSpacing(8)
        self.tiles: dict[int, KeyTile] = {}
        for k in range(1, KEY_COUNT + 1):
            tile = KeyTile(k)
            tile.clicked.connect(self._select_key)
            self.tiles[k] = tile
            grid.addWidget(tile, (k - 1) // KEY_COLS, (k - 1) % KEY_COLS)

        # Pokrętła i suwak – widoczne po podłączeniu płytki z pokrętłami.
        self.encoder_tiles: dict[int, EncoderTile] = {}
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        for i in range(1, ENCODER_COUNT + 1):
            enc = EncoderTile(i)
            enc.clicked.connect(self._select_control)
            self.encoder_tiles[i] = enc
            controls_row.addWidget(enc, 1)
        self.slider_tile = SliderTile()
        self.slider_tile.clicked.connect(self._select_control)
        controls_row.addWidget(self.slider_tile, 1)
        self.controls = QWidget()
        cl = QVBoxLayout(self.controls)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        cl.addWidget(label(tr("Pokrętła i suwak"), "lbl"))
        cl.addLayout(controls_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addLayout(top)
        layout.addLayout(grid, 1)
        layout.addWidget(self.controls)
        self.setStyleSheet("DeviceView { background: transparent; }")

        self._fade = QTimer(self)
        self._fade.setInterval(30)
        self._fade.timeout.connect(self._fade_step)
        self._selected: int | None = None

    # ------------------------------------------------------------------ dane

    def set_display_mode(self, mode: str) -> None:
        self.mode_chip.setText(
            tr("Siatka etykiet 2×4") if mode == "grid" else tr("Duża nazwa profilu")
        )

    def set_profile(self, profile: Profile) -> None:
        for k, tile in self.tiles.items():
            binding = profile.keys[k]
            gestures = [g for g in ("tap", "hold", "double_tap") if binding.action_for(g)]
            first: ActionBase | None = next(
                (
                    binding.action_for(g)
                    for g in ("tap", "hold", "double_tap")
                    if binding.action_for(g)
                ),
                None,
            )
            tile.set_binding(
                binding.label,
                binding.color,
                gestures,
                action_summary(first) if first else "",
                binding.icon,
            )
        for i, enc in self.encoder_tiles.items():
            enc.set_binding(profile.encoders[i])
        self.slider_tile.set_binding(profile.slider)

    def select(self, key: int | None) -> None:
        """key 1..8 albo None (zdejmuje też zaznaczenie pokrętła / suwaka)."""
        self._selected = key
        for k, tile in self.tiles.items():
            tile.selected = k == key
            tile.update()
        self._mark_control(None)

    def select_control(self, name: str | None) -> None:
        """name: "e1", "e2", "slider" albo None."""
        for tile in self.tiles.values():
            tile.selected = False
            tile.update()
        self._selected = None
        self._mark_control(name)

    def _mark_control(self, name: str | None) -> None:
        for tile in self._control_tiles():
            tile.selected = tile.name == name
            tile.update()

    def _control_tiles(self) -> list[_ControlTile]:
        return [*self.encoder_tiles.values(), self.slider_tile]

    def _select_key(self, key: int) -> None:
        self.select(key)
        self.keySelected.emit(key)

    def _select_control(self, name: str) -> None:
        self.select_control(name)
        self.controlSelected.emit(name)

    # ------------------------------------------------------------------ podświetlanie na żywo

    def highlight_key(self, key: int, down: bool) -> None:
        tile = self.tiles.get(key)
        if tile is None:
            return
        tile.pressed_flash = 1.0 if down else max(tile.pressed_flash, 0.6)
        tile.update()
        if not down:
            self._fade.start()

    def highlight_encoder(self, index: int, delta: int) -> None:
        tile = self.encoder_tiles.get(index)
        if tile is not None:
            tile.turn(delta)
            self._fade.start()

    def highlight_encoder_key(self, index: int, down: bool) -> None:
        tile = self.encoder_tiles.get(index)
        if tile is None:
            return
        tile.pressed_flash = 1.0 if down else max(tile.pressed_flash, 0.6)
        tile.update()
        if not down:
            self._fade.start()

    def show_slider(self, value: int) -> None:
        self.slider_tile.set_value(value)
        self._fade.start()

    def _fade_step(self) -> None:
        active = False
        tiles: list[KeyTile | _ControlTile] = [*self.tiles.values(), *self._control_tiles()]
        for tile in tiles:
            if tile.pressed_flash > 0:
                tile.pressed_flash = max(0.0, tile.pressed_flash - 0.08)
                tile.update()
                active = active or tile.pressed_flash > 0
        if not active:
            self._fade.stop()

"""Wizualny ChocPilot: ekran OLED nad siatką 2×4. Podświetla fizyczne naciśnięcia na żywo."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.actions import ActionBase
from ..core.config import Profile
from ..core.protocol import KEY_COLS, KEY_COUNT
from . import theme
from .i18n import action_summary, tr
from .oled import OledView
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
        self.selected = False
        self.hovered = False
        self.pressed_flash = 0.0
        self.setMinimumSize(120, 96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{tr('Klawisz')} K{key}")

    def set_binding(self, label: str, color: str, gestures: list[str], summary: str = "") -> None:
        self.label = label
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


class DeviceView(QWidget):
    keySelected = Signal(int)  # 1..8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.oled = OledView(scale=2)
        self.oled.setStyleSheet("background: transparent; border: none;")

        self.mode_chip = label("", "chip")
        oled_head = QHBoxLayout()
        oled_head.setSpacing(8)
        oled_head.addWidget(label(tr("Ekran OLED"), "lbl"))
        oled_head.addWidget(self.mode_chip)
        oled_head.addStretch(1)
        oled_frame = frame("oled")
        of = QHBoxLayout(oled_frame)
        of.setContentsMargins(10, 10, 10, 10)
        of.addWidget(self.oled, 0, Qt.AlignmentFlag.AlignCenter)
        top = QVBoxLayout()
        top.setSpacing(8)
        top.addLayout(oled_head)
        top.addWidget(oled_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # Siatka 2 × 4 jak na płytce: K1–K4 u góry, K5–K8 na dole.
        grid = QGridLayout()
        grid.setSpacing(8)
        self.tiles: dict[int, KeyTile] = {}
        for k in range(1, KEY_COUNT + 1):
            tile = KeyTile(k)
            tile.clicked.connect(self._select_key)
            self.tiles[k] = tile
            grid.addWidget(tile, (k - 1) // KEY_COLS, (k - 1) % KEY_COLS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addLayout(top)
        layout.addLayout(grid, 1)
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
                binding.label, binding.color, gestures, action_summary(first) if first else ""
            )

    def select(self, key: int | None) -> None:
        """key 1..8 albo None."""
        self._selected = key
        for k, tile in self.tiles.items():
            tile.selected = k == key
            tile.update()

    def _select_key(self, key: int) -> None:
        self.select(key)
        self.keySelected.emit(key)

    # ------------------------------------------------------------------ podświetlanie na żywo

    def highlight_key(self, key: int, down: bool) -> None:
        tile = self.tiles.get(key)
        if tile is None:
            return
        tile.pressed_flash = 1.0 if down else max(tile.pressed_flash, 0.6)
        tile.update()
        if not down:
            self._fade.start()

    def _fade_step(self) -> None:
        active = False
        for tile in self.tiles.values():
            if tile.pressed_flash > 0:
                tile.pressed_flash = max(0.0, tile.pressed_flash - 0.08)
                tile.update()
                active = active or tile.pressed_flash > 0
        if not active:
            self._fade.stop()

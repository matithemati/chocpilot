"""Podgląd kolorowego ekranu LCD 2" (Waveshare, ST7789V 240×320, w poziomie 320×240).

Te same układy, kolory i krój 5×7 co firmware/src/display_tft.cpp, więc podgląd
w aplikacji wygląda jak ekran urządzenia.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from ..core import savers
from ..core.protocol import ENCODER_COUNT, KEY_COLS, KEY_ROWS
from ..core.simulator import Screen

WIDTH, HEIGHT = 320, 240

# Krój 5×7 z firmware (znaki ASCII 32–126, 5 kolumn na znak, bit 0 = górny wiersz).
_FONT_5X7 = bytes.fromhex(
    "000000000000005f00000007000700147f147f14242a7f2a12231308646236495522500005030000001c224100"
    "0041221c00082a1c2a0808083e080800503000000808080808006060000020100804023e5149453e00427f4000"
    "42615149462141454b311814127f1027454545393c4a49493001710905033649494936064949291e0036360000"
    "00563600000814224100141414141400412214080201510906324979413e7e1111117e7f494949363e41414122"
    "7f4141221c7f494949417f090909013e4149497a7f0808087f00417f41002040413f017f081422417f40404040"
    "7f020c027f7f0408107f3e4141413e7f090909063e4151215e7f09192946464949493101017f01013f4040403f"
    "1f2040201f3f4038403f631408146307087008076151494543007f41410002040810200041417f000402010204"
    "4040404040000102040020545454787f484444383844444420384444487f3854545418087e090102085454543c"
    "7f0804047800447d40002040443d007f1028440000417f40007c041804787c0804047838444444387c14141408"
    "081414187c7c080404084854545420043f4440203c4040207c1c2040201c3c4030403c44281028440c5050503c"
    "4464544c44000836410000007f000000413608000804081008"
)
_POLISH = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def _ascii(text: str) -> str:
    return "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in text.translate(_POLISH))


def _rgb565(r: int, g: int, b: int) -> QColor:
    """Kolor tak, jak go pokaże panel RGB565 (obcięte młodsze bity)."""
    return QColor(r & 0xF8, g & 0xFC, b & 0xF8)


# Paleta z display_tft.cpp.
BG = _rgb565(12, 16, 28)
PANEL = _rgb565(32, 40, 62)
ACCENT = _rgb565(0, 170, 200)
WARN = _rgb565(255, 170, 40)
TEXT = _rgb565(235, 240, 245)
MUTED = _rgb565(130, 140, 165)
ONLINE = _rgb565(60, 220, 110)
PRESSED = _rgb565(255, 120, 60)

_TITLE_BAR_H = 32
_CELL_W = WIDTH // KEY_COLS
_CELL_TOP = _TITLE_BAR_H + 2
_CELL_H = (HEIGHT - _CELL_TOP) // KEY_ROWS
_TILE_INSET = 3
_CELL_LINE_CHARS = 6


def _cdiv(a: int, b: int) -> int:
    """Dzielenie całkowite jak w C (obcięcie do zera)."""
    return int(a / b)


class _Lcd:
    """Odpowiednik st7789.cpp: prostokąty i napisy z tłem komórek znaków."""

    def __init__(self, image: QImage) -> None:
        self.p = QPainter(image)

    def end(self) -> None:
        self.p.end()

    def fill(self, x: int, y: int, w: int, h: int, color: QColor) -> None:
        rect = QRect(x, y, w, h).intersected(QRect(0, 0, WIDTH, HEIGHT))
        if not rect.isEmpty():
            self.p.fillRect(rect, color)

    def frame(self, x: int, y: int, w: int, h: int, t: int, color: QColor) -> None:
        self.fill(x, y, w, t, color)
        self.fill(x, y + h - t, w, t, color)
        self.fill(x, y + t, t, h - 2 * t, color)
        self.fill(x + w - t, y + t, t, h - 2 * t, color)

    @staticmethod
    def width(text: str, scale: int, max_chars: int = 255) -> int:
        n = min(len(_ascii(text)), max_chars)
        return 0 if n == 0 else n * 6 * scale - scale

    def text(
        self,
        x: int,
        y: int,
        text: str,
        scale: int,
        fg: QColor,
        bg: QColor,
        max_chars: int = 255,
    ) -> None:
        cell_w, cell_h = 6 * scale, 7 * scale
        if y < 0 or y + cell_h > HEIGHT:
            return
        for ch in _ascii(text)[:max_chars]:
            if x >= 0:
                if x + cell_w > WIDTH:
                    break
                self.p.fillRect(x, y, cell_w, cell_h, bg)
                base = (ord(ch) - 32) * 5
                for col in range(5):
                    bits = _FONT_5X7[base + col]
                    for row in range(7):
                        if bits >> row & 1:
                            self.p.fillRect(x + col * scale, y + row * scale, scale, scale, fg)
            x += cell_w

    def centered_fit(
        self,
        text: str,
        y: int,
        h: int,
        max_scale: int,
        min_scale: int,
        fg: QColor,
        bg: QColor,
    ) -> None:
        self.fill(0, y, WIDTH, h, bg)
        scale = max_scale
        while scale > min_scale and (self.width(text, scale) > WIDTH - 16 or 7 * scale > h):
            scale -= 1
        w = self.width(text, scale)
        self.text(_cdiv(WIDTH - w, 2), y + _cdiv(h - 7 * scale, 2), text, scale, fg, bg)

    def centered_at(
        self,
        text: str,
        cx: int,
        y: int,
        scale: int,
        fg: QColor,
        bg: QColor,
        max_chars: int = 255,
    ) -> None:
        w = self.width(text, scale, max_chars)
        self.text(cx - _cdiv(w, 2), y, text, scale, fg, bg, max_chars)

    def cell_label(self, label: str, cx: int, cy: int, fg: QColor, bg: QColor) -> None:
        text = _ascii(label)
        line_h = 14
        if len(text) <= _CELL_LINE_CHARS:
            self.centered_at(text, cx, cy - line_h // 2, 2, fg, bg, _CELL_LINE_CHARS)
            return
        first, rest = _CELL_LINE_CHARS, text[_CELL_LINE_CHARS:]
        for i in range(_CELL_LINE_CHARS, 0, -1):
            if text[i] == " ":
                first, rest = i, text[i + 1 :]
                break
        self.centered_at(text, cx, cy - line_h - 3, 2, fg, bg, first)
        self.centered_at(rest, cx, cy + 3, 2, fg, bg, _CELL_LINE_CHARS)

    def icon(self, x: int, y: int, data: bytes, scale: int) -> None:
        """Ikona w formacie urządzenia: paleta 16 × RGB565 big-endian + piksele po 4 bity."""
        palette = []
        for i in range(16):
            v = data[2 * i] << 8 | data[2 * i + 1]
            palette.append(QColor((v >> 8) & 0xF8, (v >> 3) & 0xFC, (v << 3) & 0xF8))
        pixels = data[32:]
        for row in range(32):
            for col in range(32):
                b = pixels[row * 16 + col // 2]
                color = palette[b & 0x0F if col & 1 else b >> 4]
                self.p.fillRect(x + col * scale, y + row * scale, scale, scale, color)

    def marker(self, online: bool, bg: QColor) -> None:
        x, y = WIDTH - 18, 8
        self.fill(x, y, 12, 12, bg)
        if online:
            self.fill(x, y, 12, 12, ONLINE)
        else:
            self.frame(x, y, 12, 12, 2, MUTED)


def _draw(d: _Lcd, s: Screen) -> None:
    kind = s.kind
    if kind == "splash":
        d.centered_fit("ChocPilot", 60, 60, 5, 3, ACCENT, BG)
        d.centered_fit("fw sym.  ChocPilot", 140, 30, 2, 1, MUTED, BG)
    elif kind == "offline":
        d.centered_fit("Offline", 60, 60, 6, 3, WARN, BG)
        d.centered_fit("Czekam na aplikację", 140, 30, 2, 1, TEXT, BG)
        d.marker(False, BG)
    elif kind == "idle":
        d.centered_fit("ChocPilot", 80, 60, 5, 3, ACCENT, BG)
        d.marker(s.online, BG)
    elif kind == "profile":
        d.centered_fit("PROFIL", 36, 20, 2, 2, MUTED, BG)
        d.centered_fit(s.title, 80, 90, 6, 2, TEXT, BG)
        d.marker(s.online, BG)
    elif kind == "grid":
        d.fill(0, 0, WIDTH, _TITLE_BAR_H, ACCENT)
        d.text(8, (_TITLE_BAR_H - 14) // 2, s.title, 2, BG, ACCENT)
        d.marker(s.online, ACCENT)
        for r in range(KEY_ROWS):
            for c in range(KEY_COLS):
                key = r * KEY_COLS + c + 1
                x = c * _CELL_W + _TILE_INSET
                y = _CELL_TOP + r * _CELL_H + _TILE_INSET
                w = _CELL_W - 2 * _TILE_INSET
                h = _CELL_H - 2 * _TILE_INSET
                d.fill(x, y, w, h, PANEL)
                d.text(x + 5, y + 5, f"K{key}", 1, MUTED, PANEL)
                icon = s.icons[key - 1] if key - 1 < len(s.icons) else None
                if icon is not None:
                    size = 64  # ikona 32 × 32 w skali 2, jak drawIcon() w firmware
                    d.icon(x + (w - size) // 2, y + (h - size) // 2 + 4, icon, 2)
                else:
                    label = s.labels[key - 1] if key - 1 < len(s.labels) else ""
                    d.cell_label(label, x + w // 2, y + h // 2 + 4, TEXT, PANEL)
    elif kind == "text":
        if not s.line2:
            d.centered_fit(s.line1, 40, 160, 6, 2, TEXT, BG)
        else:
            d.centered_fit(s.line1, 30, 100, 5, 2, TEXT, BG)
            d.centered_fit(s.line2, 140, 70, 3, 1, MUTED, BG)
        d.marker(s.online, BG)
    elif kind == "bar":
        value = max(0, min(100, s.value))
        d.centered_fit(s.title, 20, 36, 3, 2, TEXT, BG)
        d.centered_fit(f"{value}%", 66, 60, 6, 4, ACCENT, BG)
        x, y, w, h = 20, 150, WIDTH - 40, 50
        d.frame(x, y, w, h, 3, TEXT)
        inner = w - 8
        fill = inner * value // 100
        d.fill(x + 4, y + 4, fill, h - 8, ACCENT)
        d.fill(x + 4 + fill, y + 4, inner - fill, h - 8, PANEL)
        d.marker(s.online, BG)
    elif kind == "flash":
        d.centered_fit(s.line1, 60, 120, 6, 2, BG, ACCENT)
        d.fill(8, 8, 80, 21, ACCENT)
        if s.key:
            d.text(10, 8, f"K{s.key}", 3, BG, ACCENT)
    elif kind == "test":
        _draw_test(d, s)


def _draw_test(d: _Lcd, s: Screen) -> None:
    d.text(6, 6, "TEST", 2, WARN, BG)
    hint = "K1+K4 3s: koniec"
    d.text(WIDTH - d.width(hint, 1) - 6, 10, hint, 1, MUTED, BG)
    top, tile_h = 28, 60
    for r in range(KEY_ROWS):
        for c in range(KEY_COLS):
            key = r * KEY_COLS + c
            x = c * _CELL_W + _TILE_INSET
            y = top + r * tile_h + _TILE_INSET
            w = _CELL_W - 2 * _TILE_INSET
            h = tile_h - 2 * _TILE_INSET
            pressed = key < len(s.test_keys) and s.test_keys[key]
            bg = PRESSED if pressed else PANEL
            d.fill(x, y, w, h, bg)
            d.centered_at(str(key + 1), x + w // 2, y + (h - 21) // 2, 3, TEXT, bg)
    enc_top = top + KEY_ROWS * tile_h + 4
    for i in range(ENCODER_COUNT):
        x = i * (WIDTH // 2) + _TILE_INSET
        w = WIDTH // 2 - 2 * _TILE_INSET
        down = i < len(s.test_encoder_keys) and s.test_encoder_keys[i]
        bg = PRESSED if down else PANEL
        d.fill(x, enc_top, w, 36, bg)
        turns = s.test_encoders[i] if i < len(s.test_encoders) else 0
        d.text(x + 8, enc_top + 11, f"E{i + 1} {turns:+d}", 2, TEXT, bg)
    slider_top = enc_top + 42
    bar_x = 70
    bar_w = WIDTH - bar_x - _TILE_INSET
    d.fill(0, slider_top, bar_x, 28, BG)
    d.text(_TILE_INSET + 4, slider_top + 7, f"{s.test_slider:3d}", 2, TEXT, BG)
    fill = bar_w * s.test_slider // 100
    d.fill(bar_x, slider_top, fill, 28, ACCENT)
    d.fill(bar_x + fill, slider_top, bar_w - fill, 28, PANEL)


def _draw_saver(d: _Lcd, s: Screen) -> None:
    """Animowany wygaszacz – ta sama oś czasu i kolory co firmware/src/saver.cpp."""
    anim = savers.saver(s.saver)
    sky = _rgb565(*savers.SKY)
    d.fill(0, 0, WIDTH, savers.GROUND_Y, sky)
    d.fill(0, savers.GROUND_Y, WIDTH, savers.GROUND_LINE_H, _rgb565(*savers.GROUND_LINE))
    ground_top = savers.GROUND_Y + savers.GROUND_LINE_H
    d.fill(0, ground_top, WIDTH, HEIGHT - ground_top, _rgb565(*savers.GROUND))
    if s.clock:
        w = d.width(s.clock, savers.CLOCK_SCALE)
        clock_color = _rgb565(*savers.CLOCK_COLOR)
        d.text(_cdiv(WIDTH - w, 2), savers.CLOCK_Y, s.clock, savers.CLOCK_SCALE, clock_color, sky)
    if anim is None:
        return
    pose = savers.saver_pose(anim, s.saver_ms)
    k = anim.scale
    colors = {c: _rgb565(*rgb) for c, rgb in anim.palette.items()}
    for row, line in enumerate(anim.frames[pose.frame]):
        y = pose.y + row * k
        for col, ch in enumerate(line):
            if ch != ".":
                x = pose.x + col * k
                # Firmware rysuje postać tylko nad ziemią i w granicach ekranu.
                h = min(k, savers.GROUND_Y - y)
                if h > 0:
                    d.fill(x, y, k, h, colors[ch])


def render(screen: Screen) -> QImage:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGB32)
    if screen.kind == "off":  # wygaszacz: podświetlenie wyłączone
        image.fill(QColor("#000000"))
        return image
    image.fill(ACCENT if screen.kind == "flash" else BG)
    lcd = _Lcd(image)
    try:
        if screen.kind == "saver":
            _draw_saver(lcd, screen)
        else:
            _draw(lcd, screen)
    finally:
        lcd.end()
    if screen.flip:
        image = image.transformed(QTransform().rotate(180))  # flip = obrót o 180°
    return image


class LcdView(QLabel):
    """Podgląd ekranu urządzenia (piksele skalowane bez wygładzania)."""

    def __init__(self, scale: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = scale
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:#000; border:2px solid #222; border-radius:4px;")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(QSize(WIDTH * scale + 8, HEIGHT * scale + 8))
        self._last: Screen | None = None
        self.show_screen(Screen(kind="offline"))

    def show_screen(self, screen: Screen) -> None:
        if screen == self._last:
            return
        self._last = screen
        image = render(screen)
        if screen.kind != "off":
            # podświetlenie (jasność) → przyciemnienie podglądu
            level = 0.45 + 0.55 * (screen.brightness / 255)
            if level < 0.99:
                painter = QPainter(image)
                painter.fillRect(image.rect(), QColor(0, 0, 0, int(255 * (1 - level))))
                painter.end()
        if self._scale != 1:
            image = image.scaled(
                WIDTH * self._scale,
                HEIGHT * self._scale,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        self.setPixmap(QPixmap.fromImage(image))

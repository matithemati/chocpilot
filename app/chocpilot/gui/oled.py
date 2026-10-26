"""Podgląd ekranu OLED 2,42" (SSD1309 128×64) – piksel w piksel jak firmware.

Rysuje tym samym krojem 5×7 (skala 1×–3×, pogrubienie) i tymi samymi układami co
firmware/src/display.cpp i mini_gfx.cpp, łącznie z zamianą polskich liter na łacińskie.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from ..core.protocol import KEY_COLS, KEY_ROWS
from ..core.simulator import Screen

WIDTH, HEIGHT = 128, 64
ON = QColor("#7fd8ff")
OFF = QColor("#05080b")

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

# „Czcionki” jak w firmware: (skala X, skala Y, pogrubienie, odstęp między znakami).
SMALL = (1, 1, 0, 1)
CONDENSED = (1, 1, 0, 0)  # 6 znaków w komórce siatki
MEDIUM = (1, 1, 1, 1)
LARGE = (2, 2, 0, 1)
HUGE = (3, 3, 0, 1)

# Siatka 2 × 4 (display.cpp): pasek tytułu 10 px, komórki 32 × 27 px.
_TITLE_BAR_H = 10
_CELL_W = WIDTH // KEY_COLS
_CELL_TOP = _TITLE_BAR_H + 1
_CELL_H = 27
_CELL_LINE_CHARS = 6


def _ascii(text: str) -> str:
    return "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in text.translate(_POLISH))


class _Canvas:
    """Odpowiednik MiniGfx: piksele 1-bitowe, kolor 1 = świeci, 0 = gaszenie."""

    def __init__(self) -> None:
        self.px = [[0] * WIDTH for _ in range(HEIGHT)]
        self.color = 1
        self.font = SMALL

    def box(self, x: int, y: int, w: int, h: int) -> None:
        for yy in range(max(0, y), min(HEIGHT, y + h)):
            row = self.px[yy]
            for xx in range(max(0, x), min(WIDTH, x + w)):
                row[xx] = self.color

    def frame(self, x: int, y: int, w: int, h: int) -> None:
        self.box(x, y, w, 1)
        self.box(x, y + h - 1, w, 1)
        self.box(x, y, 1, h)
        self.box(x + w - 1, y, 1, h)

    def disc(self, x: int, y: int, r: int) -> None:
        for dy in range(-r, r + 1):
            dx = 0
            while (dx + 1) ** 2 + dy * dy <= r * r:
                dx += 1
            self.box(x - dx, y + dy, 2 * dx + 1, 1)

    def circle(self, x: int, y: int, r: int) -> None:
        self.disc(x, y, r)
        self.color ^= 1
        self.disc(x, y, r - 1)
        self.color ^= 1

    def advance(self) -> int:
        return (5 + self.font[3]) * self.font[0] + self.font[2]

    def width(self, text: str, max_chars: int = 255) -> int:
        n = min(len(_ascii(text)), max_chars)
        return 0 if n == 0 else n * self.advance() - self.font[3] * self.font[0]

    def text(self, x: int, y: int, text: str, max_chars: int = 255) -> None:
        sx, sy, bold, _gap = self.font
        top = y - 7 * sy
        for ch in _ascii(text)[:max_chars]:
            if x >= WIDTH:
                break
            base = (ord(ch) - 32) * 5
            for col in range(5):
                bits = _FONT_5X7[base + col]
                for row in range(7):
                    if bits >> row & 1:
                        self.box(x + col * sx, top + row * sy, sx + bold, sy)
            x += self.advance()

    def centered(self, text: str, cx: int, baseline: int, max_chars: int = 255) -> None:
        self.text(cx - self.width(text, max_chars) // 2, baseline, text, max_chars)

    def centered_fit(
        self, text: str, baseline: int, fonts: list[tuple[int, int, int, int]]
    ) -> None:
        for i, font in enumerate(fonts):
            self.font = font
            w = self.width(text)
            if w <= WIDTH - 2 or i == len(fonts) - 1:
                self.text((WIDTH - w) // 2, baseline, text)
                return

    def marker(self, online: bool, inverted: bool = False, x: int = WIDTH - 4, y: int = 3) -> None:
        self.color = 0 if inverted else 1
        if online:
            self.disc(x, y, 2)
        else:
            self.circle(x, y, 2)
        self.color = 1

    def cell_line(self, text: str, max_chars: int, cx: int, baseline: int) -> None:
        n = min(len(text), max_chars)
        self.font = SMALL if n < _CELL_LINE_CHARS else CONDENSED
        self.centered(text, cx, baseline, n)

    def cell_label(self, label: str, cx: int, top: int) -> None:
        text = _ascii(label)
        if len(text) <= _CELL_LINE_CHARS:
            self.cell_line(text, _CELL_LINE_CHARS, cx, top + 17)
            return
        first, rest = _CELL_LINE_CHARS, text[_CELL_LINE_CHARS:]
        for i in range(_CELL_LINE_CHARS, 0, -1):
            if text[i] == " ":
                first, rest = i, text[i + 1 :]
                break
        self.cell_line(text, first, cx, top + 12)
        self.cell_line(rest, _CELL_LINE_CHARS, cx, top + 22)


def _draw(c: _Canvas, screen: Screen) -> None:
    kind = screen.kind
    if kind == "splash":
        c.font = LARGE
        c.centered("ChocPilot", WIDTH // 2, 30)
        c.font = SMALL
        c.centered("fw sym.  Pro Micro", WIDTH // 2, 50)
    elif kind == "offline":
        c.font = LARGE
        c.centered("Offline", WIDTH // 2, 28)
        c.font = SMALL
        c.centered("Czekam na aplikację", WIDTH // 2, 48)
        c.marker(False)
    elif kind == "idle":
        c.font = LARGE
        c.centered("ChocPilot", WIDTH // 2, 38)
        c.marker(screen.online)
    elif kind == "profile":
        c.centered_fit(screen.title, 40, [HUGE, LARGE, MEDIUM, SMALL])
        c.marker(screen.online)
    elif kind == "grid":
        c.box(0, 0, WIDTH, _TITLE_BAR_H)
        c.font = SMALL
        c.color = 0
        c.text(2, 8, screen.title)
        c.color = 1
        c.marker(screen.online, inverted=True, x=WIDTH - 5, y=4)
        for r in range(KEY_ROWS):
            for col in range(KEY_COLS):
                i = r * KEY_COLS + col
                label = screen.labels[i] if i < len(screen.labels) else ""
                c.cell_label(label, col * _CELL_W + _CELL_W // 2 - 1, _CELL_TOP + r * _CELL_H)
        for col in range(1, KEY_COLS):
            c.box(col * _CELL_W - 1, _CELL_TOP, 1, HEIGHT - _CELL_TOP)
        c.box(0, _CELL_TOP + _CELL_H - 1, WIDTH, 1)
    elif kind == "text":
        if not screen.line2:
            c.centered_fit(screen.line1, 40, [HUGE, LARGE, MEDIUM, SMALL])
        else:
            c.centered_fit(screen.line1, 26, [LARGE, MEDIUM, SMALL])
            c.centered_fit(screen.line2, 50, [MEDIUM, SMALL])
    elif kind == "bar":
        c.font = MEDIUM
        c.text(0, 14, screen.title)
        pct = f"{screen.value}%"
        c.text(WIDTH - c.width(pct), 14, pct)
        c.frame(0, 26, WIDTH, 24)
        fill = (WIDTH - 4) * screen.value // 100
        if fill > 0:
            c.box(2, 28, fill, 20)
    elif kind == "flash":
        c.centered_fit(screen.line1, 42, [HUGE, LARGE, MEDIUM, SMALL])
        if screen.key:
            c.font = SMALL
            c.text(0, 8, f"K{screen.key}")
    elif kind == "test":
        c.font = SMALL
        c.text(0, 8, "TEST")
        hint = "K1+K4 3s: koniec"
        c.text(WIDTH - c.width(hint), 8, hint)
        for r in range(KEY_ROWS):
            for col in range(KEY_COLS):
                key = r * KEY_COLS + col
                x, y = col * _CELL_W + 1, _CELL_TOP + 1 + r * _CELL_H
                w, h = _CELL_W - 3, _CELL_H - 4
                if key < len(screen.test_keys) and screen.test_keys[key]:
                    c.box(x, y, w, h)
                    c.color = 0
                else:
                    c.frame(x, y, w, h)
                c.centered(str(key + 1), x + w // 2, y + 15)
                c.color = 1


def render(screen: Screen) -> QImage:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGB32)
    image.fill(OFF)
    if screen.kind == "off":
        return image
    canvas = _Canvas()
    _draw(canvas, screen)
    on = ON.rgb()
    for y, row in enumerate(canvas.px):
        for x, value in enumerate(row):
            if value:
                image.setPixel(x, y, on)
    if screen.flip:
        image = image.mirrored(True, True)
    return image


class OledView(QLabel):
    """Powiększony podgląd ekranu (piksele skalowane bez wygładzania)."""

    def __init__(self, scale: int = 3, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = scale
        self.setFixedSize(QSize(WIDTH * scale + 8, HEIGHT * scale + 8))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:#000; border:2px solid #222; border-radius:4px;")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._last: Screen | None = None
        self.show_screen(Screen(kind="offline"))

    def show_screen(self, screen: Screen) -> None:
        if screen == self._last:
            return
        self._last = screen
        image = render(screen)
        if screen.kind != "off":
            # jasność OLED → przyciemnienie podglądu
            level = 0.45 + 0.55 * (screen.brightness / 255)
            if level < 0.99:
                painter = QPainter(image)
                painter.fillRect(image.rect(), QColor(0, 0, 0, int(255 * (1 - level))))
                painter.end()
        pix = QPixmap.fromImage(
            image.scaled(
                WIDTH * self._scale,
                HEIGHT * self._scale,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        )
        self.setPixmap(pix)

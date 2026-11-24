"""Biblioteka ikon klawiszy: wbudowane ikony liniowe, emoji z czcionki systemu, własne pliki.

Identyfikatory (pole KeyBinding.icon):
- „builtin:<nazwa>” – ikony z icon_set.py (rysowane obrysem),
- „emoji:<kod szesnastkowo>” – znak emoji (np. „emoji:1F3B5”), czcionka emoji systemu,
- „file:<nazwa pliku>” – PNG/SVG/JPG z folderu ikon w katalogu konfiguracji (custom_dir()).

Nowe ikony: wiersz w icon_set.ICONS albo plik w folderze ikon (przycisk w oknie wyboru ikony).
Urządzenie dostaje ikonę jako 32 × 32 px w 16 kolorach (device_payload) – rysuje ją w skali 2.
"""

from __future__ import annotations

import threading
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from ..core.config import default_config_dir
from .icon_set import ICONS

DEVICE_ICON = 32  # rozmiar ikony w urządzeniu (firmware: kIconSize)
# Tło kafelka siatki na LCD (firmware/src/display_tft.cpp: kPanel) i kolor ikon liniowych (kText).
DEVICE_PANEL = (32, 40, 62)
DEVICE_LINE = (235, 240, 245)
CUSTOM_SUFFIXES = (".png", ".svg", ".jpg", ".jpeg", ".bmp", ".webp")
EMOJI_FONTS = ("Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Twemoji Mozilla")
EMOJI_RANGES = (
    (0x2600, 0x27BF),  # różne symbole, dingbaty
    (0x1F300, 0x1F5FF),  # symbole i piktogramy
    (0x1F600, 0x1F64F),  # buźki
    (0x1F680, 0x1F6FF),  # transport i mapy
    (0x1F900, 0x1F9FF),  # symbole dodatkowe
    (0x1FA70, 0x1FAFF),  # symbole rozszerzone A
)
CATEGORY_EMOJI = "Emoji"
CATEGORY_CUSTOM = "Własne"

_render_lock = threading.Lock()  # renderowanie z wątku GUI i kontrolera


@dataclass(frozen=True)
class IconEntry:
    id: str
    name: str
    category: str
    keywords: str = ""

    def matches(self, query: str) -> bool:
        q = query.strip().lower()
        return not q or q in self.name.lower() or q in self.keywords or q in self.id.lower()


def custom_dir() -> Path:
    return default_config_dir() / "icons"


def emoji_family() -> str | None:
    families = set(QFontDatabase.families())
    return next((f for f in EMOJI_FONTS if f in families), None)


class IconLibrary:
    def __init__(self, custom: Path | None = None) -> None:
        self.custom = custom or custom_dir()
        self._builtin = {name: svg for name, _, _, _, svg in ICONS}
        self._entries: list[IconEntry] | None = None

    # ------------------------------------------------------------------ lista ikon

    def entries(self) -> list[IconEntry]:
        if self._entries is None:
            self._entries = self._builtin_entries() + self._custom_entries() + self._emoji_entries()
        return self._entries

    def reload(self) -> None:
        """Po dodaniu plików do folderu ikon."""
        self._entries = None
        self.render.cache_clear()
        self.device_payload.cache_clear()

    def categories(self) -> list[str]:
        seen: list[str] = []
        for e in self.entries():
            if e.category not in seen:
                seen.append(e.category)
        return seen

    def entry(self, icon_id: str) -> IconEntry | None:
        return next((e for e in self.entries() if e.id == icon_id), None)

    @staticmethod
    def _builtin_entries() -> list[IconEntry]:
        return [
            IconEntry(f"builtin:{name}", label, category, f"{name} {keywords}".lower())
            for name, label, category, keywords, _ in ICONS
        ]

    def _custom_entries(self) -> list[IconEntry]:
        if not self.custom.is_dir():
            return []
        files = sorted(
            p for p in self.custom.iterdir() if p.is_file() and p.suffix.lower() in CUSTOM_SUFFIXES
        )
        return [IconEntry(f"file:{p.name}", p.stem, CATEGORY_CUSTOM, p.stem.lower()) for p in files]

    @staticmethod
    def _emoji_entries() -> list[IconEntry]:
        family = emoji_family()
        metrics = QFontMetrics(QFont(family)) if family else None
        out = []
        for lo, hi in EMOJI_RANGES:
            for cp in range(lo, hi + 1):
                ch = chr(cp)
                if unicodedata.category(ch) != "So":
                    continue
                name = unicodedata.name(ch, "")
                if not name or (metrics is not None and not metrics.inFontUcs4(cp)):
                    continue
                out.append(IconEntry(f"emoji:{cp:X}", name.title(), CATEGORY_EMOJI, name.lower()))
        return out

    # ------------------------------------------------------------------ rysowanie

    @lru_cache(maxsize=2048)  # noqa: B019 (biblioteka żyje przez cały czas działania aplikacji)
    def render(self, icon_id: str, size: int, color: str = "#ebf0f5") -> QImage:
        """Ikona size × size, przezroczyste tło (ikony liniowe w kolorze `color`)."""
        image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        kind, _, value = icon_id.partition(":")
        with _render_lock:
            p = QPainter(image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            try:
                if kind == "builtin" and value in self._builtin:
                    self._paint_svg(p, size, _line_svg(self._builtin[value], color))
                elif kind == "emoji":
                    self._paint_emoji(p, size, value)
                elif kind == "file":
                    self._paint_file(p, size, self.custom / value)
            finally:
                p.end()
        return image

    @staticmethod
    def _paint_svg(p: QPainter, size: int, svg: bytes) -> None:
        renderer = QSvgRenderer(QByteArray(svg))
        if renderer.isValid():
            renderer.render(p, QRectF(0, 0, size, size))

    @staticmethod
    def _paint_emoji(p: QPainter, size: int, code: str) -> None:
        try:
            ch = chr(int(code, 16))
        except ValueError:
            return
        family = emoji_family()
        font = QFont(family) if family else QFont()
        font.setPixelSize(max(8, int(size * 0.82)))
        p.setFont(font)
        p.setPen(QColor("#ebf0f5"))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, ch)

    def _paint_file(self, p: QPainter, size: int, path: Path) -> None:
        if not path.is_file():
            return
        if path.suffix.lower() == ".svg":
            self._paint_svg(p, size, path.read_bytes())
            return
        img = QImage(str(path))
        if img.isNull():
            return
        scaled = img.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        p.drawImage((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)

    # ------------------------------------------------------------------ urządzenie

    @lru_cache(maxsize=256)  # noqa: B019
    def device_payload(self, icon_id: str) -> bytes | None:
        """544 B dla komendy icon: paleta 16 × RGB565 (big-endian) + 32 × 32 px po 4 bity.
        Ikona nałożona na tło kafelka LCD, kolory zredukowane do 16. None = brak ikony."""
        if not icon_id or self.entry(icon_id) is None:
            return None
        line = "#{:02x}{:02x}{:02x}".format(*DEVICE_LINE)
        image = self.render(icon_id, DEVICE_ICON, line)
        return encode_device_icon(image)


def _line_svg(body: str, color: str) -> bytes:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    ).encode()


def _rgb565(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Kolor po zaokrągleniu do RGB565 (tak, jak go pokaże LCD)."""
    return r & 0xF8, g & 0xFC, b & 0xF8


def encode_device_icon(image: QImage) -> bytes:
    """Obraz (z przezroczystością) → format urządzenia, tło = kolor kafelka LCD."""
    size = DEVICE_ICON
    if image.width() != size or image.height() != size:
        image = image.scaled(size, size)
    bg = DEVICE_PANEL
    pixels: list[tuple[int, int, int]] = []
    for y in range(size):
        for x in range(size):
            c = image.pixelColor(x, y)
            a = c.alpha() / 255
            rgb = (
                round(c.red() * a + bg[0] * (1 - a)),
                round(c.green() * a + bg[1] * (1 - a)),
                round(c.blue() * a + bg[2] * (1 - a)),
            )
            pixels.append(_rgb565(*rgb))
    palette = quantize(pixels, 16, keep=_rgb565(*bg))
    index_cache: dict[tuple[int, int, int], int] = {}

    def nearest(c: tuple[int, int, int]) -> int:
        if c not in index_cache:
            index_cache[c] = min(
                range(len(palette)),
                key=lambda i: sum((a - b) ** 2 for a, b in zip(c, palette[i], strict=True)),
            )
        return index_cache[c]

    indices = [nearest(c) for c in pixels]
    out = bytearray()
    for r, g, b in palette + [(0, 0, 0)] * (16 - len(palette)):
        value = (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3
        out += bytes((value >> 8, value & 0xFF))
    for i in range(0, len(indices), 2):
        out.append(indices[i] << 4 | indices[i + 1])
    return bytes(out)


def quantize(
    pixels: list[tuple[int, int, int]], count: int, keep: tuple[int, int, int] | None = None
) -> list[tuple[int, int, int]]:
    """Paleta ≤ count kolorów (median cut); `keep` (tło) zawsze dokładnie w palecie."""
    unique = list(dict.fromkeys(pixels))
    if len(unique) <= count:
        return unique
    others = [p for p in pixels if p != keep] if keep is not None else list(pixels)
    slots = count - (1 if keep is not None else 0)
    boxes = [others]
    while len(boxes) < slots:
        # dzielimy pudełko o największym zakresie na jego najszerszej osi, w medianie
        best = max(range(len(boxes)), key=lambda i: _box_range(boxes[i])[0])
        spread, axis = _box_range(boxes[best])
        if spread == 0:
            break
        box = sorted(boxes[best], key=lambda p: p[axis])
        mid = len(box) // 2
        boxes[best : best + 1] = [box[:mid], box[mid:]]
    palette = [
        _rgb565(*(round(sum(p[i] for p in box) / len(box)) for i in range(3)))
        for box in boxes
        if box
    ]
    if keep is not None:
        palette = [keep, *[c for c in palette if c != keep]]
    return list(dict.fromkeys(palette))[:count]


def _box_range(box: list[tuple[int, int, int]]) -> tuple[int, int]:
    if not box:
        return 0, 0
    ranges = [max(p[i] for p in box) - min(p[i] for p in box) for i in range(3)]
    axis = max(range(3), key=lambda i: ranges[i])
    return ranges[axis], axis


_library: IconLibrary | None = None


def library() -> IconLibrary:
    """Wspólna biblioteka aplikacji (edytor klawisza, podgląd urządzenia, wysyłanie ikon)."""
    global _library
    if _library is None:
        _library = IconLibrary()
    return _library

"""Generuje firmware/src/saver_data.h z animacji w app/chocpilot/core/savers.py.

Użycie (z katalogu firmware):  python tools/gen_savers.py
Test aplikacji (tests/test_savers.py) sprawdza, czy plik jest aktualny.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "firmware" / "src" / "saver_data.h"
sys.path.insert(0, str(ROOT / "app"))

from chocpilot.core import savers  # noqa: E402


def rgb565(c: tuple[int, int, int]) -> int:
    r, g, b = c
    return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3


def ident(name: str) -> str:
    return "k" + "".join(part.capitalize() for part in name.split("_"))


def pixels(s: savers.Saver) -> list[int]:
    """Ramki po kolei, wiersz po wierszu, 2 piksele na bajt (starszy półbajt = lewy piksel)."""
    index = {c: i for i, c in enumerate(s.color_index())}
    out: list[int] = []
    for frame in s.frames:
        for row in frame:
            values = [index[c] for c in row]
            if len(values) % 2:
                values.append(0)
            out.extend(values[i] << 4 | values[i + 1] for i in range(0, len(values), 2))
    return out


def chunks(values: list[str], per_line: int) -> str:
    lines = [", ".join(values[i : i + per_line]) for i in range(0, len(values), per_line)]
    return ",\n    ".join(lines)


def generate() -> str:
    parts = [
        "// Wygenerowane przez firmware/tools/gen_savers.py z app/chocpilot/core/savers.py –",
        "// nie edytuj ręcznie (zmień animację w savers.py i uruchom generator).",
        "#pragma once",
        "",
        "#include <stdint.h>",
        "",
        '#include "saver.h"',
        "",
        "namespace chocpilot {",
        "namespace saver_data {",
        "",
        f"constexpr int kGroundY = {savers.GROUND_Y};",
        f"constexpr int kGroundLineH = {savers.GROUND_LINE_H};",
        f"constexpr uint16_t kSky = 0x{rgb565(savers.SKY):04X};",
        f"constexpr uint16_t kGround = 0x{rgb565(savers.GROUND):04X};",
        f"constexpr uint16_t kGroundLine = 0x{rgb565(savers.GROUND_LINE):04X};",
        f"constexpr int kClockY = {savers.CLOCK_Y};",
        f"constexpr uint8_t kClockScale = {savers.CLOCK_SCALE};",
        f"constexpr uint16_t kClockColor = 0x{rgb565(savers.CLOCK_COLOR):04X};",
        "",
    ]
    table = []
    for s in savers.SAVERS:
        n = ident(s.name)
        palette = [f"0x{rgb565(savers.SKY):04X}"] + [
            f"0x{rgb565(c):04X}" for c in s.palette.values()
        ]
        steps = [f"{{{st.frame}, {st.dx}, {st.dy}}}" for st in s.steps]
        data = [f"0x{b:02X}" for b in pixels(s)]
        parts += [
            f"// {s.name}: {s.width}×{s.height} px, {len(s.frames)} ramki, skala {s.scale}",
            f"constexpr uint16_t {n}Palette[] = {{{', '.join(palette)}}};  // [0] = tło",
            f"constexpr SaverStep {n}Steps[] = {{{', '.join(steps)}}};",
            f"constexpr uint8_t {n}Pixels[] = {{\n    {chunks(data, 12)}}};",
            "",
        ]
        table.append(
            f'    {{"{s.name}", {s.width}, {s.height}, {s.scale}, {s.frame_ms}, '
            f"{len(s.steps)}, {s.cycle_dx}, {n}Steps, {n}Palette, {n}Pixels}},"
        )
    parts += [
        "constexpr SaverAnimation kSavers[] = {",
        *table,
        "};",
        f"constexpr uint8_t kSaverCount = {len(savers.SAVERS)};",
        "",
        "}  // namespace saver_data",
        "}  // namespace chocpilot",
        "",
    ]
    return "\n".join(parts)


def main() -> None:
    OUT.write_text(generate(), encoding="utf-8", newline="\n")
    print(f"zapisano {OUT}")


if __name__ == "__main__":
    main()

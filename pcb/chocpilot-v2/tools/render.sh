#!/bin/sh
# Podgląd płytki: SVG z kicad-cli → PNG (qlmanage). Użycie: render.sh <katalog_wyjściowy> [szerokość]
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-$DIR/tools/build}
W=${2:-2400}
mkdir -p "$OUT"
$CLI pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet \
  --layers Edge.Cuts,F.Cu,F.Silkscreen,F.Courtyard,F.Fab -o "$OUT/top.svg" "$DIR/chocpilot-v2.kicad_pcb" >/dev/null 2>&1
$CLI pcb export svg --mode-single --fit-page-to-board --exclude-drawing-sheet --mirror \
  --layers Edge.Cuts,B.Cu,B.Silkscreen,B.Courtyard,B.Fab -o "$OUT/bottom.svg" "$DIR/chocpilot-v2.kicad_pcb" >/dev/null 2>&1
for f in top bottom; do qlmanage -t -s "$W" -o "$OUT" "$OUT/$f.svg" >/dev/null 2>&1; mv -f "$OUT/$f.svg.png" "$OUT/$f.png"; done
ls "$OUT"/top.png "$OUT"/bottom.png

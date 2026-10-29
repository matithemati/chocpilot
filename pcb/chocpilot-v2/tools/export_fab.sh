#!/bin/sh
# Pliki produkcyjne: Gerbery + wiercenia (Excellon) → fab/chocpilot-v2-gerbers.zip
set -e
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT="$DIR/fab/gerbers"
rm -rf "$OUT" && mkdir -p "$OUT"
$CLI pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask -o "$OUT/" "$DIR/chocpilot-v2.kicad_pcb"
$CLI pcb export drill --format excellon --excellon-separate-th --generate-map --map-format pdf \
  -o "$OUT/" "$DIR/chocpilot-v2.kicad_pcb"
cd "$DIR/fab" && rm -f chocpilot-v2-gerbers.zip && zip -qj chocpilot-v2-gerbers.zip gerbers/*
ls -la "$DIR/fab"

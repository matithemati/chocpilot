"""Mapa montażu (solder map) ChocPilot: dane z chocpilot-v0.kicad_pcb -> HTML -> PDF (A4, Edge headless).

Ten sam układ co documentation/assembly_map.pdf w TMCAN32: dwie strony przeglądowe (spód, wierzch) ze
wszystkimi oznaczeniami, potem jedna karta na linię części (gdzie, symbol TME, ile, w którą stronę).
Symbole TME biorą się z bom/order_tme.csv (to, co faktycznie jest w zamówieniu), a gdy tam ich nie ma,
z pola TME w płytce.

    python tools/assembly_map/gen_assembly_map.py
"""

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import sexpr  # noqa: E402

PCB = ROOT / "chocpilot-v0.kicad_pcb"
ORDER = ROOT / "bom" / "order_tme.csv"
OUT_HTML = ROOT / "docs" / "assembly_map.html"
OUT_PDF = ROOT / "docs" / "assembly_map.pdf"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]

# Kolejność lutowania wg docs/ASSEMBLY.md (karty w kroku idą w tej kolejności).
ORDER_REFS = ("J1 F1 R1 R2 U3 C1 U2 C2 C3 C4 U1 C5 C6 C7 C8 C9 C10 C11 C12 R3 Y1 C13 C14 C15 C16 U4 C17 R6 "
              "SW1 SW2 C18 L1 C19 D1 S1 J2 J3 ENC1 RV1 H1").split()

# step: 1 wierzch SMD, 2 spód SMD, 3 THT, 4 nic do montażu
STEPS = {
    1: ["Top side: SMD", "Solder the top first, while the board still lies flat: finest and lowest parts first. "
                         "Cards follow the order in docs/ASSEMBLY.md, with tests after the power parts and after U1."],
    2: ["Bottom side: SMD", "Turn the board over. The LEDs light the desk through the case bottom, "
                            "so do them carefully: short heat, iron at most 320 °C."],
    3: ["Through-hole parts", "Insert from the top and solder on the bottom. Do them last, after the SMD parts "
                              "on both sides have been tested. Trim the pins short underneath."],
    4: ["Nothing to fit", "Mounting holes for the case."],
}

# Opisy i uwagi do kart, po MPN z płytki.
INFO = {
    "USB4105-GF-A": dict(v="USB-C receptacle, 16 SMD pads (0.5 mm pitch) + 4 THT shell tabs",
                         note="Press the pegs into the holes and the pads line up. Drag-solder the 0.5 mm row, "
                              "clear bridges with wick, then the 4 shell tabs with plenty of solder. "
                              "Check VBUS–GND and CC1/CC2 for shorts."),
    "MF-NSMF050-2": dict(v="PTC fuse 0.5 A hold / 1 A trip, 1206"),
    "RC0805FR-075K1L": dict(v="5.1 kΩ 1 %, 0805 (USB-C CC pull-downs)"),
    "USBLC6-2SC6": dict(v="USBLC6-2SC6 USB ESD protection, SOT-23-6", pol="1",
                        note="Dot on the package = pin 1 at the blue ring."),
    "C0805C106M8RACTU": dict(v="10 µF X7R, 0805"),
    "TPS73633DBVR": dict(v="TPS73633 LDO 3.3 V / 400 mA, SOT-23-5", pol="1",
                         note="Pins 1–3 are the row of three; pin 1 at the blue ring. "
                              "Test 1 after C2–C4: +5V ≈ 4.8–5.1 V on C1, +3V3 = 3.3 V on C3."),
    "KAM21KR71E105KU": dict(v="1 µF X7R, 0805"),
    "KGM21NR72A103KT": dict(v="10 nF X7R, 0805"),
    "STM32F072CBT6": dict(v="STM32F072CBT6 MCU, LQFP-48 0.5 mm", pol="1",
                          note="Dot = pin 1, at the blue ring (silkscreen triangle). Tack two opposite corners, "
                               "check all 4 rows sit centred, then drag-solder. Check for shorts at pins "
                               "23–24, 35–36, 47–48 and 8–9. Fit its capacitors and R3 straight away."),
    "KAM21BR71H104KT": dict(v="100 nF X7R, 0805"),
    "KGM21AR71C475KU": dict(v="4.7 µF X7R, 0805"),
    "RC0805FR-0710KL": dict(v="10 kΩ 1 %, 0805 (BOOT0 pull-down)"),
    "ABM3-8.000MHZ-D2Y-T": dict(v="8 MHz crystal, CL 18 pF, 5032", note="Optional: USB runs without it (HSI48 + CRS)."),
    "08055A270GAT2A": dict(v="27 pF C0G, 0805", note="Optional, only with Y1."),
    "SN74AHCT1G125DBVR": dict(v="74AHCT1G125 level shifter 3.3 → 5 V (LED data), SOT-23-5", pol="1",
                              note="Pins 1–3 are the row of three; pin 1 at the blue ring."),
    "RC0805FR-07330RL": dict(v="330 Ω 1 %, 0805 (LED data line)"),
    "PTS645SM43SMTR92 LFS": dict(v="Tact switch 6 × 6 mm SMD: SW1 RESET, SW2 BOOT0",
                                 note="Test 2 after these: hold BOOT0, tap RESET, release BOOT0. "
                                      "The PC should list DFU device 0483:df11 (dfu-util -l)."),
    "WS2812B-V6": dict(v="WS2812B addressable RGB LED, 5050 PLCC4", pol="1",
                       note="Pad 1 = VDD (+5V) at the blue ring, pad 3 = GND. The pin-1 mark on the LED varies by "
                            "batch: check your batch's datasheet. Short heat, one pad first. "
                            "Chain runs L1 → L12. Note: bom/order_tme.csv orders WS2812B-2020-V6 (2 × 2 mm), "
                            "which does not fit this 5 × 5 mm footprint."),
    "1N4148W-E3-08": dict(v="1N4148W switching diode, SOD-123", pol="K",
                          note="Cathode band toward the board edge, at the blue ring (silkscreen bar). "
                               "A reversed diode is a dead key."),
    "CPG1353 (Choc V2)": dict(v="Kailh Choc V2 switch (MX stem), soldered", src="Not at TME: Amazon, Kailh Choc V2",
                              note="Only after all SMD parts and the LED test. Press flat (through the case plate "
                                   "if you have it), solder one pin, check it sits flat and square, then the other."),
    "DS1021-1*8SF11-B": dict(v="Pin header 1 × 8, 2.54 mm (LCD cable)", pol="1",
                             note="Pin 1 = VCC at the blue ring; LCD PH2.0 cable 1:1, VCC on pin 1."),
    "DS1021-1*5SF11-B": dict(v="Pin header 1 × 5, 2.54 mm (SWD)", pol="1",
                             note="Optional: usually left empty, the programmer pins just press in."),
    "EC11E15244G1": dict(v="EC11 rotary encoder with push switch, 15 pulses / 30 detents",
                         note="Solder the two mounting tabs first with plenty of solder, then the 5 pins."),
    "RS45111A900F": dict(v="ALPS RS45 slide pot 45 mm, 10 kΩ linear",
                         note="3 pins; the two body pegs go in the Ø2.1 holes. Not in bom/order_tme.csv: order separately."),
    "": dict(v="M3 mounting hole"),
}

# Zamienniki z bom/order_tme.csv (inny producent, te same parametry) – po MPN z płytki.
ORDER_SUB = {
    "C0805C106M8RACTU": "CL21A106KAYNNNE",
    "KAM21KR71E105KU": "CL21B105KAFNNNE",
    "KGM21NR72A103KT": "CL21B103KBANNNC",
    "KAM21BR71H104KT": "CL21B104KBCNNNC",
    "KGM21AR71C475KU": "CL21A475KAQNNNE",
    "08055A270GAT2A": "C0805C270J5GAC",
}


def num(x):
    return float(x)


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def xy(node, name):
    k = kid(node, name)
    return (num(k[1]), num(k[2])) if k else None


def width(node):
    s = kid(node, "stroke")
    w = kid(s, "width") if s else kid(node, "width")
    return num(w[1]) if w else 0.1


def filled(node):
    f = kid(node, "fill")
    return bool(f) and str(f[1]) in ("yes", "solid")


def layer(node):
    k = kid(node, "layer")
    return str(k[1]) if k else ""


def r2(v):
    return round(v, 3)


class Tf:
    """Footprint -> płytka: obrót KiCad (kąt dodatni = przeciwnie do wskazówek na ekranie, oś Y w dół), potem przesunięcie."""

    def __init__(self, x, y, a, ox, oy):
        self.x, self.y, self.ox, self.oy = x, y, ox, oy
        self.c, self.s = math.cos(math.radians(a)), math.sin(math.radians(a))

    def __call__(self, p):
        lx, ly = p
        return [r2(self.x + lx * self.c + ly * self.s - self.ox), r2(self.y - lx * self.s + ly * self.c - self.oy)]


def shape(node, tf):
    kind = node[0]
    w = r2(width(node))
    if kind in ("fp_line", "gr_line"):
        return {"t": "l", "w": w, "a": tf(xy(node, "start")), "b": tf(xy(node, "end"))}
    if kind in ("fp_rect", "gr_rect"):
        (x0, y0), (x1, y1) = xy(node, "start"), xy(node, "end")
        return {"t": "p", "w": w, "f": filled(node), "pts": [[tf(p) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]]}
    if kind in ("fp_circle", "gr_circle"):
        c, e = tf(xy(node, "center")), tf(xy(node, "end"))
        return {"t": "c", "w": w, "f": filled(node), "c": c, "r": r2(math.dist(c, e))}
    if kind in ("fp_arc", "gr_arc"):
        return {"t": "a", "w": w, "a": tf(xy(node, "start")), "m": tf(xy(node, "mid")), "b": tf(xy(node, "end"))}
    if kind in ("fp_poly", "gr_poly"):
        pts = [tf((num(p[1]), num(p[2]))) for p in kid(node, "pts") if isinstance(p, list) and p[0] == "xy"]
        return {"t": "p", "w": w, "f": filled(node), "pts": [pts]}
    return None


def arc_points(a, m, b, n=8):
    """Łuk przez trzy punkty jako łamana (krawędź płytki rysujemy z odcinków)."""
    (ax, ay), (mx, my), (bx, by) = a, m, b
    d = 2 * (ax * (my - by) + mx * (by - ay) + bx * (ay - my))
    ux = ((ax * ax + ay * ay) * (my - by) + (mx * mx + my * my) * (by - ay) + (bx * bx + by * by) * (ay - my)) / d
    uy = ((ax * ax + ay * ay) * (bx - mx) + (mx * mx + my * my) * (ax - bx) + (bx * bx + by * by) * (mx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    t0, tm, t1 = (math.atan2(p[1] - uy, p[0] - ux) for p in (a, m, b))

    def ccw(t):
        return (t - t0) % (2 * math.pi)
    sweep = ccw(t1) if ccw(tm) < ccw(t1) else ccw(t1) - 2 * math.pi
    return [[r2(ux + r * math.cos(t0 + sweep * i / n)), r2(uy + r * math.sin(t0 + sweep * i / n))] for i in range(n + 1)]


def read_order():
    with ORDER.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))
    return {r[1]: {"tme": r[1], "mpn": r[2], "man": r[3]} for r in rows[1:] if len(r) > 3}


def main():
    pcb = sexpr.parse(PCB.read_text(encoding="utf-8"))
    order = read_order()

    # krawędź: środek płytki -> (0, 0)
    edge_nodes = [n for n in pcb if isinstance(n, list) and n[0] in ("gr_line", "gr_arc") and layer(n) == "Edge.Cuts"]
    raw = []
    for n in edge_nodes:
        if n[0] == "gr_line":
            raw.append([xy(n, "start"), xy(n, "end")])
        else:
            pts = arc_points(xy(n, "start"), xy(n, "mid"), xy(n, "end"))
            raw += [[pts[i], pts[i + 1]] for i in range(len(pts) - 1)]
    xs = [p[0] for s in raw for p in s]
    ys = [p[1] for s in raw for p in s]
    ox, oy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    W, H = max(xs) - min(xs), max(ys) - min(ys)
    edge = [{"w": 0.05, "t": "l", "a": [r2(a[0] - ox), r2(a[1] - oy)], "b": [r2(b[0] - ox), r2(b[1] - oy)]} for a, b in raw]
    ident = Tf(0, 0, 0, ox, oy)

    text = {"T": [], "B": []}
    for n in pcb:
        if not (isinstance(n, list) and n[0] == "gr_text" and layer(n) in ("F.SilkS", "B.SilkS")):
            continue
        at = kid(n, "at")
        eff = kid(n, "effects")
        size = kid(kid(eff, "font"), "size")
        just = kid(eff, "justify")
        left = bool(just) and "left" in [str(j) for j in just[1:]]
        side = "T" if layer(n).startswith("F") else "B"
        text[side].append({"s": str(n[1]), "p": ident((num(at[1]), num(at[2]))), "h": num(size[1]),
                           "ang": num(at[3]) if len(at) > 3 else 0.0, "left": left})

    tr = {"T": [], "B": []}
    for n in pcb:
        if isinstance(n, list) and n[0] == "segment" and layer(n) in ("F.Cu", "B.Cu"):
            a, b = ident(xy(n, "start")), ident(xy(n, "end"))
            tr["T" if layer(n) == "F.Cu" else "B"].append([*a, *b, r2(num(kid(n, "width")[1]))])
    via = [[*ident(xy(n, "at")), r2(num(kid(n, "size")[1]) / 2)] for n in pcb if isinstance(n, list) and n[0] == "via"]

    fps = []
    for f in (n for n in pcb if isinstance(n, list) and n[0] == "footprint"):
        P = {str(c[1]): str(c[2]) for c in kids(f, "property") if len(c) > 2}
        ref = P["Reference"]
        at = kid(f, "at")
        x, y, a = num(at[1]), num(at[2]), num(at[3]) if len(at) > 3 else 0.0
        tf = Tf(x, y, a, ox, oy)
        side = "T" if layer(f) == "F.Cu" else "B"
        silk_l, crt_l = ("F.SilkS", "F.CrtYd") if side == "T" else ("B.SilkS", "B.CrtYd")

        pads = []
        for p in kids(f, "pad"):
            kind, sh = str(p[2]), str(p[3])
            pat = kid(p, "at")
            size = kid(p, "size")
            drill = kid(p, "drill")
            dr = next((num(d) for d in (drill or [])[1:] if not isinstance(d, list) and str(d) != "oval"), 0.0)
            lays = [str(l) for l in (kid(p, "layers") or [])[1:]]
            net = kid(p, "net")
            rr = kid(p, "roundrect_rratio")
            pads.append({"n": str(p[1]), "net": str(net[2]) if net and len(net) > 2 else "",
                         "c": tf((num(pat[1]), num(pat[2]))), "w": num(size[1]), "h": num(size[2]),
                         "a": num(pat[3]) if len(pat) > 3 else 0.0,
                         "sh": {"circle": "c", "oval": "o", "roundrect": "rr"}.get(sh, "r"),
                         "rr": num(rr[1]) if rr else 0, "th": kind == "thru_hole", "np": kind == "np_thru_hole",
                         "dr": dr, "paste": any(l.endswith(".Paste") for l in lays)})

        silk, crt = [], []
        for g in f:
            if not (isinstance(g, list) and g and str(g[0]).startswith("fp_") and g[0] != "fp_text"):
                continue
            s = shape(g, tf)
            if s is None:
                continue
            if layer(g) == silk_l:
                silk.append(s)
            elif layer(g) == crt_l:
                crt.append(s)

        def pts_of(s):
            if s["t"] == "c":
                return [[s["c"][0] - s["r"], s["c"][1] - s["r"]], [s["c"][0] + s["r"], s["c"][1] + s["r"]]]
            if s["t"] == "p":
                return [q for o in s["pts"] for q in o]
            return [s[k] for k in ("a", "m", "b") if k in s]
        pts = [q for s in crt for q in pts_of(s)]
        if not pts:
            pts = [[p["c"][0] + dx * max(p["w"], p["h"]) / 2, p["c"][1] + dy * max(p["w"], p["h"]) / 2]
                   for p in pads for dx in (-1, 1) for dy in (-1, 1)]
        box = [r2(min(q[0] for q in pts)), r2(min(q[1] for q in pts)), r2(max(q[0] for q in pts)), r2(max(q[1] for q in pts))]

        mpn = P.get("MPN", "")
        info = INFO.get(mpn, {})
        fps.append({"ref": ref, "val": P.get("Value", ""), "side": side, "fp": str(f[1]).split(":")[-1],
                    "pos": ident((x, y)), "tme": P.get("TME", ""), "mpn": mpn, "man": P.get("Manufacturer", ""),
                    "url": "", "nobom": ref.startswith("H"), "pads": pads, "silk": silk, "box": box,
                    "mark": info.get("pol", ""), "pol": info.get("pol", ""), "group": ref.rstrip("0123456789")})

    # linie części: ta sama część po tej samej stronie
    def rank(r):
        pre = r.rstrip("0123456789")
        if r in ORDER_REFS:
            return ORDER_REFS.index(r), 0
        same = [i for i, o in enumerate(ORDER_REFS) if o.rstrip("0123456789") == pre]
        return (same[0] if same else 999), int(r[len(pre):] or 0)

    groups = {}
    for f in fps:
        groups.setdefault((f["side"], f["mpn"]), []).append(f)
    G = []
    for (side, mpn), fs in groups.items():
        fs.sort(key=lambda f: rank(f["ref"]))
        refs = [f["ref"] for f in fs]
        info = INFO.get(mpn, {})
        th = all(any(p["th"] for p in f["pads"]) and not any(p["paste"] for p in f["pads"]) for f in fs)
        step = 4 if refs[0].startswith("H") else 3 if th else 1 if side == "T" else 2
        sub = order.get(ORDER_SUB.get(mpn, ""), None) or order.get(fs[0]["tme"], None)
        tme, man, part = (sub["tme"], sub["man"], sub["mpn"]) if sub else (fs[0]["tme"], fs[0]["man"], mpn)
        if info.get("src"):
            tme = ""
        G.append({"key": mpn or "H", "refs": refs, "vals": [info.get("v", fs[0]["val"])], "tme": tme, "url": "",
                  "mpn": part, "man": man.upper() if man else "", "step": step, "side": side,
                  "pol": info.get("pol", ""), "note": info.get("note", ""), "src": info.get("src", ""),
                  "_rank": rank(refs[0])})
    G.sort(key=lambda g: (g["step"], g["_rank"]))
    for g in G:
        del g["_rank"]

    pad = 2.0
    data = {"board": {"edge": edge, "silk": {"T": [], "B": []}, "text": text, "tr": tr, "via": via, "fps": fps},
            "groups": G, "view": [r2(-W / 2 - pad), r2(-H / 2 - pad), r2(W + 2 * pad), r2(H + 2 * pad)],
            "steps": STEPS}
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    OUT_HTML.write_text(html, encoding="utf-8")

    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if not browser:
        sys.exit("no Edge/Chrome found: open docs/assembly_map.html and print to PDF")
    subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=5000",
                    f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()], check=True, capture_output=True)
    n = sum(len(g["refs"]) for g in G if g["step"] < 4)
    print(f"ok: {len(fps)} footprints, {len(G)} lines, {n} parts to fit, board {W:.1f} x {H:.1f} mm -> {OUT_PDF}")


if __name__ == "__main__":
    main()

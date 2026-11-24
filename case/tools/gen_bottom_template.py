"""Szablon dna ChocPilot v2 (płyta z pleksi/polistyrenu): PDF 1:1 do druku i DXF do cięcia laserem.

Rysunek jest WIDOKIEM OD SPODU (strona z fazowaniem pod łby wkrętów), krawędź z USB-C u góry.
Współrzędne otworów jak w chocpilot_v2_case.sc (widok od góry, środek płytki w (0, 0)); w widoku
od spodu oś X jest odbita.

    python tools/gen_bottom_template.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent.parent
W, D, R = 116.4, 95.4, 3.2  # obrys = obrys Shell
SCREWS = [(-50.5, 39.5), (53.5, 25.5), (-51.0, -40.0), (51.5, -40.0)]  # M3, widok od góry
ACCESS = [(-11.0, -13.5, "RESET"), (1.0, -13.5, "BOOT")]
SCREW_D, CS_D, ACCESS_D = 3.4, 6.4, 4.0
FEET = [(sx * 38.0, sy * 36.0) for sx in (-1, 1) for sy in (-1, 1)]  # nóżki Ø10, z dala od łbów
FOOT_D = 10.0


def bottom_view(x, y):
    return -x, y


def holes():
    for x, y in SCREWS:
        yield (*bottom_view(x, y), SCREW_D, "M3")
    for x, y, name in ACCESS:
        yield (*bottom_view(x, y), ACCESS_D, name)


# ------------------------------------------------------------------ PDF (A4, skala 1:1)

def make_pdf(path):
    fig = plt.figure(figsize=(210 / 25.4, 297 / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 210)
    ax.set_ylim(0, 297)
    ax.set_aspect("equal")
    ax.axis("off")
    cx, cy = 105, 180  # środek płyty na kartce
    x0, y0 = cx - W / 2, cy - D / 2

    ax.add_patch(FancyBboxPatch((x0 + R, y0 + R), W - 2 * R, D - 2 * R,
                                boxstyle=f"round,pad={R}", fill=False, lw=0.6))
    for hx, hy, d, name in holes():
        px, py = cx + hx, cy + hy
        ax.add_patch(Circle((px, py), d / 2, fill=False, lw=0.4))
        if name == "M3":
            ax.add_patch(Circle((px, py), CS_D / 2, fill=False, lw=0.3, ls="--"))
        ax.plot([px - 5, px + 5], [py, py], lw=0.2, color="k")
        ax.plot([px, px], [py - 5, py + 5], lw=0.2, color="k")
        ax.plot(px, py, "k.", ms=1.5)
        # wymiary od lewej i górnej krawędzi płyty (do trasowania bez drukarki)
        label = f"{name} Ø{d:g}\n{px - x0:.1f} / {y0 + D - py:.1f}"
        above = hy > 0  # dolne otwory opisane pod spodem – nad nimi są nóżki
        left = name == "BOOT"  # obok RESET – opis po drugiej stronie
        ax.text(px + (-4.5 if left else 4.5), py + (1.5 if above else -1.5), label, fontsize=5,
                va="bottom" if above else "top", ha="right" if left else "left")

    for fx, fy in FEET:
        ax.add_patch(Circle((cx + fx, cy + fy), FOOT_D / 2, fill=False, lw=0.3, ls=":"))
        ax.text(cx + fx, cy + fy, "nóżka", ha="center", va="center", fontsize=4.5, color="0.4")

    ax.text(cx, y0 + D + 3, "TYŁ – krawędź z USB-C", ha="center", fontsize=7)
    ax.text(cx, y0 - 5, "PRZÓD", ha="center", fontsize=7)
    ax.text(cx, y0 + D + 12,
            "ChocPilot v2 – dno z płyty mlecznej (opal) 3 mm   •   WIDOK OD SPODU",
            ha="center", fontsize=9, weight="bold")

    notes = [
        "Drukuj w skali 100 % („rzeczywisty rozmiar”, bez dopasowania do strony); sprawdź linijką skalę poniżej.",
        f"Obrys {W} × {D} mm, narożniki R{R} (wyrównaj pilnikiem). Tnij z naddatkiem ~0,5 mm i zeszlifuj do obrysu.",
        f"Otwory M3: Ø{SCREW_D}, od tej strony fazowanie 90° do Ø{CS_D} (linia przerywana) pod wkręty M3×16 z łbem stożkowym.",
        f"RESET / BOOT: Ø{ACCESS_D} (naciskane szpilką). Liczby przy otworach: odległość od lewej / od górnej krawędzi płyty.",
        "Folię ochronną zdejmij dopiero po wierceniu. Wierć ostrym wiertłem, wolno, płyta na desce, przez taśmę malarską.",
        "Nóżki (kropkowane): samoprzylepne odbojniki Ø10, wys. ≥ 3 mm – płyta nie leży na blacie, światło wychodzi spod niej.",
    ]
    for i, line in enumerate(notes):
        ax.text(15, 105 - i * 6, line, fontsize=6)

    # kontrola skali
    ax.plot([15, 115], [60, 60], lw=0.6, color="k")
    for t in range(0, 101, 10):
        ax.plot([15 + t, 15 + t], [60, 62 if t % 50 else 64], lw=0.4, color="k")
    ax.text(65, 56, "100 mm", ha="center", fontsize=6)
    ax.add_patch(Rectangle((140, 20), 50, 50, fill=False, lw=0.4))
    ax.text(165, 45, "50 × 50 mm", ha="center", va="center", fontsize=6)
    fig.savefig(path)
    plt.close(fig)


# ------------------------------------------------------------------ DXF (R12, mm, widok od spodu)

def make_dxf(path):
    ents = []

    def line(x1, y1, x2, y2):
        ents.append(f"0\nLINE\n8\nCUT\n10\n{x1:.4f}\n20\n{y1:.4f}\n11\n{x2:.4f}\n21\n{y2:.4f}\n")

    def arc(x, y, r, a1, a2):
        ents.append(f"0\nARC\n8\nCUT\n10\n{x:.4f}\n20\n{y:.4f}\n40\n{r:.4f}\n50\n{a1:g}\n51\n{a2:g}\n")

    def circle(x, y, r, layer="CUT"):
        ents.append(f"0\nCIRCLE\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n40\n{r:.4f}\n")

    hw, hd = W / 2, D / 2
    line(-hw + R, -hd, hw - R, -hd)
    line(hw, -hd + R, hw, hd - R)
    line(hw - R, hd, -hw + R, hd)
    line(-hw, hd - R, -hw, -hd + R)
    arc(hw - R, -hd + R, R, 270, 360)
    arc(hw - R, hd - R, R, 0, 90)
    arc(-hw + R, hd - R, R, 90, 180)
    arc(-hw + R, -hd + R, R, 180, 270)
    for x, y, d, name in holes():
        circle(x, y, d / 2)
        if name == "M3":
            circle(x, y, CS_D / 2, layer="COUNTERSINK_NO_CUT")
    path.write_text("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
                    "0\nSECTION\n2\nENTITIES\n" + "".join(ents) + "0\nENDSEC\n0\nEOF\n")


if __name__ == "__main__":
    make_pdf(OUT / "chocpilot_v2_bottom_template.pdf")
    make_dxf(OUT / "chocpilot_v2_bottom.dxf")
    print("ok")

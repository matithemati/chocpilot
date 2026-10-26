// ChocPilot – obudowa dla płytki 2×4 (Kailh Choc) z ekranem OLED 2,42" między rzędami klawiszy.
//
// Geometria płytki z pliku KiCad (esp_macropad/pcb/tap32/tap32.kicad_pcb, zapis 2026-10-26):
//   – obrys 79,5 × 117,0 mm (Edge.Cuts: 28,5…108 × 26,5…143,5),
//   – K1–K4 (S1–S4, Row 0) u góry, szczelina 4U na ekran, K5–K8 (S5–S8, Row 1); Choc V1, raster 19,05,
//   – 5 otworów M3 (H1–H5),
//   – Pro Micro (U1) poziomo przy prawej krawędzi, USB w prawo, wystaje ok. 1,9 mm poza PCB;
//     zakładamy montaż od spodu płytki (mcu_side) – nad nim leży moduł OLED,
//   – J1: JST XH 4-pin pionowe, pod dolną krawędzią modułu OLED.
// Ekran poziomo, przykręcony od spodu do podwyższonego „pokładu” obudowy i połączony przewodem
// z J1. Wymiary modułu OLED 2,42" to nadal ZAŁOŻENIA – zmierz swój moduł.
//
// Współrzędne: (0, 0) = lewy dolny róg PCB; k2s() zamienia współrzędne KiCad (oś Y w dół).
//
// Części:
//   "shell"    – skorupa: ścianki, niski pokład z otworami na rzędy klawiszy, podwyższony
//                pokład z oknem OLED i słupkami do przykręcenia modułu, wycięcie USB
//   "bottom"   – dno: słupki pod płytkę (wkręty M3 od góry przez PCB), kołnierz centrujący,
//                wpusty na nóżki gumowe
//   "assembly" – podgląd złożenia z modelem płytki, klawiszy, Pro Micro i OLED
//   "exploded" – podgląd rozstrzelony
//
// Eksport STL:  openscad -D part=\"shell\" -o chocpilot_shell.stl chocpilot_case.scad
// Druk: skorupa otwartą stroną do stołu, z podporami (najlepiej drzewiastymi) tylko pod oboma
//       pokładami od środka – wierzchnie powierzchnie wychodzą czyste; dno płasko.
// Montaż: moduł OLED → skorupa (4 wkręty M2,5 od spodu), płytka → dno (5× M3×6 od góry, przed
//         założeniem keycapów), przewód OLED → J1, skorupa na dno (4× M2×8 od spodu), keycapy.

/* [Wybór części] */
part = "assembly";  // [shell, bottom, assembly, exploded]

/* [Płytka – wartości z pliku KiCad, zwykle bez zmian] */
edge_kicad = [[28.5, 26.5], [108.0, 143.5]];  // Edge.Cuts: lewy górny, prawy dolny
pitch      = 19.05;
keys_kicad_x = [38.1, 57.15, 76.2, 95.25];
keys_kicad_y = [38.1, 133.35];                // Row 0 (S1–S4), Row 1 (S5–S8)
holes_kicad  = [[51, 120], [96.5, 121], [38, 51.5], [94.5, 51.5], [49.475, 81.475]];  // H1–H5
mcu_kicad    = [[76.83, 81.73], [109.85, 99.51]];  // obrys Pro Micro (U1, obrót −90°)
usb_kicad_y  = 90.62;                              // oś gniazda USB na prawej krawędzi
j1_kicad     = [[90.3, 109.1], [103.7, 115.9]];    // obrys J1 (JST XH 4-pin, pionowe)
pcb_t      = 1.6;
pcb_hole_d = 3.2;    // otwory M3

/* [Pro Micro (od spodu płytki)] */
mcu_lift = 2.5;      // plastik goldpinów między PCB a Pro Micro
mcu_t    = 1.6;
usb_h    = 3.2;      // gniazdo USB pod płytką Pro Micro (elementy w dół)
usb_cut  = [12.0, 8.0];  // otwór na wtyk z obudową (szer. × wys.)
mcu_pocket_clear = 0.6;  // luz wokół części Pro Micro wystającej poza PCB

/* [J1 – złącze OLED] */
j1_clear = 14.0;     // wolne miejsce nad PCB przy J1: wtyk XH (ok. 10 mm) + zgięcie przewodów

/* [OLED 2,42" SSD1309 – ZAŁOŻENIA, zmierz swój moduł] */
oled_pcb      = [70.0, 43.0];
oled_pcb_t    = 1.6;
oled_glass    = [60.5, 37.0, 2.0];  // szkło: szer., wys., grubość
oled_glass_d  = [0.0, 0.0];         // przesunięcie środka szkła od środka modułu
oled_active   = [55.01, 27.49];     // obszar aktywny 128×64
oled_active_d = [0.0, 0.0];         // przesunięcie obszaru aktywnego od środka szkła
oled_holes    = [65.0, 38.0];       // rozstaw otworów montażowych (Ø3)
oled_back_clear = 8.0;              // od tyłu modułu do góry PCB (min.; patrz też j1_clear)
oled_screw_pilot = 2.2;             // wkręt M2,5 wkręcany w słupek (do tworzyw)
oled_boss_d   = 4.4;                // słupek mieści się między otworem a szkłem
window_margin = 0.6;                // okno większe od obszaru aktywnego
window_chamfer = 1.2;

/* [Klawisze Choc] */
keycap    = [18.0, 18.0];  // keycap Choc w rastrze MX (pasują też mniejsze 17,5 × 16,5)
key_clear = 0.8;           // luz między keycapem a krawędzią otworu
key_deck_h = 6.0;          // wierzch niskiego pokładu nad górą PCB (keycap wystaje ok. 4 mm)
choc_h    = 5.2;           // korpus Choc nad PCB (tylko podgląd)
cap_h     = 3.0;           // tylko podgląd

/* [Obudowa] */
rim        = 5.0;   // od krawędzi PCB do zewnętrznej ścianki
pcb_clear  = 0.4;   // luz między PCB a ścianką
floor_t    = 2.4;   // grubość dna
standoff_h = 10.0;  // spód PCB nad dnem: Pro Micro z USB, piny Choc, diody
standoff_d = 7.0;
top_t      = 2.0;   // grubość pokładów
corner_r   = 4.0;
deck_slope = 4.0;   // skos boków podwyższonego pokładu (cofnięcie górnej krawędzi)
well_r     = 1.5;

/* [Wkręty] */
pcb_screw_pilot  = 2.6;  // M3 wkręcany w słupek dna (4.0 = wtapiana tuleja M3)
case_screw_pilot = 1.8;  // M2 w narożnik skorupy od spodu
case_screw_hole  = 2.4;  // przelot w dnie
case_screw_head  = [4.2, 1.4];  // łeb: średnica, głębokość wpustu

/* [Dno] */
lip_h  = 2.0;   // kołnierz centrujący wchodzący w skorupę
lip_t  = 1.6;
lip_gap = 0.25;
foot_d = 10.0;  // wpusty na nóżki gumowe
foot_t = 1.0;

$fn = 48;

// ---------------------------------------------------------------- wartości wyliczane

// KiCad (mm, Y w dół) → układ obudowy (lewy dolny róg PCB = 0, Y w górę)
function k2s(p) = [p[0] - edge_kicad[0][0], edge_kicad[1][1] - p[1]];
function box2s(b) = let(a = k2s(b[0]), c = k2s(b[1]))
  [min(a[0], c[0]), min(a[1], c[1]), abs(c[0] - a[0]), abs(c[1] - a[1])];  // x, y, szer., wys.

pcb   = [edge_kicad[1][0] - edge_kicad[0][0], edge_kicad[1][1] - edge_kicad[0][1]];
key_x = [for (x = keys_kicad_x) k2s([x, 0])[0]];
key_y = [for (y = keys_kicad_y) k2s([0, y])[1]];  // Row 0 (K1–K4), Row 1 (K5–K8)
keys_cx = (key_x[0] + key_x[3]) / 2;             // środek rzędów (PCB jest szersza w prawo)
gap_y0 = key_y[1] + pitch / 2;                   // góra pola dolnego rzędu
gap_y1 = key_y[0] - pitch / 2;                   // dół pola górnego rzędu
gap_c  = (gap_y0 + gap_y1) / 2;

pcb_holes = [for (h = holes_kicad) k2s(h)];
mcu_box = box2s(mcu_kicad);
usb_y   = k2s([0, usb_kicad_y])[1];
j1_box  = box2s(j1_kicad);
oled_c  = [keys_cx, gap_c];

inner = [pcb[0] + 2 * pcb_clear, pcb[1] + 2 * pcb_clear];  // wnętrze (od -pcb_clear)
outer = [inner[0] + 2 * rim, inner[1] + 2 * rim];
o0    = [-pcb_clear - rim, -pcb_clear - rim];               // narożnik zewnętrzny

// wysokości (z = 0: spód dna)
pcb_bot   = floor_t + standoff_h;
pcb_top   = pcb_bot + pcb_t;
key_top   = pcb_top + key_deck_h;
// szkło dotyka spodu pokładu; pokład musi też zmieścić wtyk J1 z przewodami
deck_under = pcb_top + max(oled_back_clear + oled_pcb_t + oled_glass[2], j1_clear);
deck_top  = deck_under + top_t;

well = [3 * pitch + keycap[0] + 2 * key_clear, keycap[1] + 2 * key_clear];
well_y = [for (y = key_y) y];
// podwyższony pokład w osi Y: od górnej krawędzi dolnego otworu do dolnej krawędzi górnego
deck_y0 = key_y[1] + well[1] / 2;
deck_y1 = key_y[0] - well[1] / 2;

case_screws = [[o0[0] + rim / 2 + 1, o0[1] + rim / 2 + 1],
               [o0[0] + outer[0] - rim / 2 - 1, o0[1] + rim / 2 + 1],
               [o0[0] + rim / 2 + 1, o0[1] + outer[1] - rim / 2 - 1],
               [o0[0] + outer[0] - rim / 2 - 1, o0[1] + outer[1] - rim / 2 - 1]];

oled_hole_pos = [for (sx = [-1, 1], sy = [-1, 1])
                 [oled_c[0] + sx * oled_holes[0] / 2, oled_c[1] + sy * oled_holes[1] / 2]];
glass_c  = oled_c + oled_glass_d;
active_c = glass_c + oled_active_d;
window   = oled_active + [2 * window_margin, 2 * window_margin];

usb_zc = pcb_bot - mcu_lift - mcu_t - usb_h / 2;
// część Pro Micro wystająca poza prawą krawędź PCB – kieszeń w ściance (pod płytką)
mcu_pocket = [pcb[0], mcu_box[1] - mcu_pocket_clear,
              mcu_box[0] + mcu_box[2] - pcb[0] + mcu_pocket_clear, mcu_box[3] + 2 * mcu_pocket_clear];

echo(str("PCB ", pcb[0], " × ", pcb[1], " mm; obudowa ", outer[0], " × ", outer[1],
         " mm, wys. ", key_top, " / ", deck_top, " mm"));

// ---------------------------------------------------------------- pomocnicze

module rrect(size, r) {
  offset(r) offset(-r) square(size);
}

module outline2d(grow = 0) {
  translate(o0 - [grow, grow]) rrect(outer + [2 * grow, 2 * grow], corner_r + grow);
}

module inner2d(grow = 0) {
  translate([-pcb_clear - grow, -pcb_clear - grow])
    rrect(inner + [2 * grow, 2 * grow], max(0.5, corner_r - rim + grow));
}

// Profil podwyższonego pokładu w płaszczyźnie Y-Z, wyciągnięty wzdłuż X przez całą obudowę.
module deck_prism(y0, y1, z0, z1, slope) {
  translate([o0[0] - 1, 0, 0])
    rotate([90, 0, 90])
      linear_extrude(outer[0] + 2)
        polygon([[y0, z0], [y1, z0], [y1 - slope, z1], [y0 + slope, z1]]);
}

module well2d(i) {
  translate([keys_cx - well[0] / 2, well_y[i] - well[1] / 2]) rrect(well, well_r);
}

// ---------------------------------------------------------------- skorupa

module shell() {
  difference() {
    union() {
      // ścianki + niski pokład
      translate([0, 0, floor_t]) linear_extrude(key_top - floor_t) outline2d();
      // podwyższony pokład nad ekranem
      intersection() {
        translate([0, 0, floor_t]) linear_extrude(deck_top - floor_t) outline2d();
        deck_prism(deck_y0, deck_y1, floor_t, deck_top, deck_slope);
      }
    }
    // wnętrze pod niskim pokładem
    translate([0, 0, floor_t - 0.01]) linear_extrude(key_top - top_t - floor_t + 0.01) inner2d();
    // wnętrze pod podwyższonym pokładem
    intersection() {
      translate([0, 0, floor_t - 0.01]) linear_extrude(deck_under - floor_t + 0.01) inner2d();
      deck_prism(deck_y0 + top_t, deck_y1 - top_t, floor_t - 0.01, deck_under,
                 deck_slope);
    }
    // otwory na rzędy klawiszy
    for (i = [0, 1]) translate([0, 0, pcb_top]) linear_extrude(deck_top) well2d(i);
    // okno OLED z fazą od góry
    translate([active_c[0] - window[0] / 2, active_c[1] - window[1] / 2, deck_under - 0.01])
      cube([window[0], window[1], top_t + 0.02]);
    hull() {
      translate([active_c[0] - window[0] / 2, active_c[1] - window[1] / 2, deck_top - window_chamfer])
        cube([window[0], window[1], 0.01]);
      translate([active_c[0] - window[0] / 2 - window_chamfer,
                 active_c[1] - window[1] / 2 - window_chamfer, deck_top])
        cube([window[0] + 2 * window_chamfer, window[1] + 2 * window_chamfer, 0.01]);
    }
    // USB (prawa ścianka)
    translate([pcb[0] - 1, usb_y - usb_cut[0] / 2, usb_zc - usb_cut[1] / 2])
      cube([rim + pcb_clear + 2, usb_cut[0], usb_cut[1]]);
    // kieszeń na Pro Micro wystające poza PCB (pod płytką)
    translate([mcu_pocket[0] - 0.01, mcu_pocket[1], floor_t - 0.01])
      cube([mcu_pocket[2] + 0.01, mcu_pocket[3], pcb_bot - floor_t - 0.2]);
    // wkręty skorupy od spodu
    for (p = case_screws) translate([p[0], p[1], floor_t - 0.01]) cylinder(d = case_screw_pilot, h = 9);
  }
  // słupki do przykręcenia modułu OLED (płytka modułu opiera się na ich końcach)
  for (p = oled_hole_pos)
    translate([p[0], p[1], deck_under - oled_glass[2]])
      difference() {
        cylinder(d = oled_boss_d, h = oled_glass[2] + 0.01);
        translate([0, 0, -0.01]) cylinder(d = oled_screw_pilot, h = oled_glass[2] + 0.03);
      }
}

// ---------------------------------------------------------------- dno

module bottom() {
  difference() {
    union() {
      linear_extrude(floor_t) outline2d();
      // kołnierz centrujący
      translate([0, 0, floor_t - 0.01])
        linear_extrude(lip_h)
          difference() {
            inner2d(-lip_gap);
            inner2d(-lip_gap - lip_t);
          }
      // słupki pod płytkę
      for (p = pcb_holes)
        translate([p[0], p[1], floor_t - 0.01]) cylinder(d = standoff_d, h = standoff_h + 0.01);
    }
    for (p = pcb_holes) translate([p[0], p[1], floor_t]) cylinder(d = pcb_screw_pilot, h = standoff_h + 1);
    for (p = case_screws) {
      translate([p[0], p[1], -0.01]) cylinder(d = case_screw_hole, h = floor_t + 0.02);
      translate([p[0], p[1], -0.01]) cylinder(d = case_screw_head[0], h = case_screw_head[1]);
    }
    // USB: kołnierz nie może blokować wtyku
    translate([pcb[0] - lip_t - 2, usb_y - usb_cut[0] / 2, floor_t - 0.02])
      cube([lip_t + 4, usb_cut[0], lip_h + 0.04]);
    translate([pcb[0] - lip_t - 2, mcu_pocket[1], floor_t - 0.02])
      cube([lip_t + 4, mcu_pocket[3], lip_h + 0.04]);
    // nóżki
    for (sx = [0, 1], sy = [0, 1])
      translate([o0[0] + 12 + sx * (outer[0] - 24), o0[1] + 12 + sy * (outer[1] - 24), -0.01])
        cylinder(d = foot_d, h = foot_t);
  }
}

// ---------------------------------------------------------------- podgląd elementów

module pcb_model() {
  color("darkgreen") translate([0, 0, pcb_bot])
    difference() {
      cube([pcb[0], pcb[1], pcb_t]);
      for (p = pcb_holes) translate([p[0], p[1], -1]) cylinder(d = pcb_hole_d, h = 4);
    }
  for (x = key_x, y = key_y) {
    color("dimgray") translate([x - 7.5, y - 7.5, pcb_top]) cube([15, 15, choc_h]);
    color("whitesmoke")
      translate([x - keycap[0] / 2, y - keycap[1] / 2, pcb_top + choc_h + 0.8]) cube([keycap[0], keycap[1], cap_h]);
  }
  color("navy") translate([mcu_box[0], mcu_box[1], pcb_bot - mcu_lift - mcu_t]) cube([mcu_box[2], mcu_box[3], mcu_t]);
  color("silver") translate([mcu_box[0] + mcu_box[2] - 5.5, usb_y - 3.7, usb_zc - usb_h / 2])
    cube([7.0, 7.4, usb_h]);
  // J1 (JST XH, pionowe) z wtykiem
  color("white") translate([j1_box[0], j1_box[1], pcb_top]) cube([j1_box[2], j1_box[3], 7.0]);
  color("ivory") translate([j1_box[0] + 1, j1_box[1] + 0.5, pcb_top + 7.0]) cube([j1_box[2] - 2, j1_box[3] - 1, 3.0]);
  // M3
  for (p = pcb_holes) color("gainsboro") translate([p[0], p[1], pcb_top]) cylinder(d = 5.5, h = 2.4);
}

module oled_model() {
  color("midnightblue") translate([oled_c[0] - oled_pcb[0] / 2, oled_c[1] - oled_pcb[1] / 2, deck_under - oled_glass[2] - oled_pcb_t])
    difference() {
      cube([oled_pcb[0], oled_pcb[1], oled_pcb_t]);
      for (p = oled_hole_pos)
        translate([p[0] - oled_c[0] + oled_pcb[0] / 2, p[1] - oled_c[1] + oled_pcb[1] / 2, -1]) cylinder(d = 3, h = 4);
    }
  color("black") translate([glass_c[0] - oled_glass[0] / 2, glass_c[1] - oled_glass[1] / 2, deck_under - oled_glass[2]])
    cube(oled_glass);
  color("deepskyblue") translate([active_c[0] - oled_active[0] / 2, active_c[1] - oled_active[1] / 2, deck_under - 0.05])
    cube([oled_active[0], oled_active[1], 0.06]);
}

// ---------------------------------------------------------------- wybór

if (part == "shell") {
  shell();
} else if (part == "bottom") {
  bottom();
} else if (part == "exploded") {
  color("lightgray") bottom();
  translate([0, 0, 25]) pcb_model();
  translate([0, 0, 55]) oled_model();
  translate([0, 0, 55]) color("silver", 0.9) shell();
} else {
  color("lightgray") bottom();
  pcb_model();
  oled_model();
  color("silver", 0.55) shell();
}

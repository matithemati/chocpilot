// ChocPilot – obudowa dla płytki 2×4 (Kailh Choc) z ekranem OLED 2,42" między rzędami klawiszy.
//
// Geometria płytki z pliku KiCad (esp_macropad/pcb/tap32/tap32.kicad_pcb, wersja kompaktowa
// 2026-10-26):
//   – obrys 79,5 × 88,75 mm (Edge.Cuts: 28,5…108 × 54,75…143,5),
//   – K1–K4 (S1–S4, Row 0) i K5–K8 (S5–S8, Row 1), środki rzędów 67 mm od siebie; Choc V1,
//     raster 19,05; ekran dokładnie pośrodku – ten sam odstęp od obu rzędów,
//   – 5 otworów M3 (H1–H5) – pod modułem OLED, więc wkręty z niskim łbem (ISO 7380, łeb 1,65 mm),
//   – Pro Micro (U1) poziomo przy prawej krawędzi, USB w prawo, wystaje ok. 1,9 mm poza PCB;
//     montaż od spodu płytki, piny od góry przycięte równo z lutem (leżą pod modułem),
//   – J1: pola lutownicze na przewody do modułu (bez złącza), pod modułem.
// Obudowa ma płaską górę na wysokości klawiszy; moduł OLED wisi 2 mm nad PCB, przykręcony od
// spodu do płyty, a jego szkło leży w otworze 0,4 mm poniżej powierzchni (nic nie wystaje).
// Moduł OLED: ShengYang 2,42" (oled_variant) – rozstaw otworów i położenie szkła oszacowane.
//
// Współrzędne: (0, 0) = lewy dolny róg PCB; k2s() zamienia współrzędne KiCad (oś Y w dół).
//
// Części:
//   "shell"    – skorupa: ścianki i płaska płyta z otworami na rzędy klawiszy, otworem na szkło
//                OLED i gniazdami wkrętów modułu, wycięcie USB
//   "bottom"   – dno: słupki pod płytkę (wkręty M3 od góry przez PCB), kołnierz centrujący,
//                wpusty na nóżki gumowe
//   "assembly" – podgląd złożenia z modelem płytki, klawiszy, Pro Micro i OLED
//   "exploded" – podgląd rozstrzelony
//
// Eksport STL:  openscad -D part=\"shell\" -o chocpilot_shell.stl chocpilot_case.scad
// Druk: skorupa płytą do stołu (górą w dół) – bez podpór; dno płasko.
// Montaż: przewody do modułu OLED (od tyłu), moduł → skorupa (4× M2,5×4 od spodu), płytka → dno
//         (5× M3×6 ISO 7380 od góry), przewody → J1, skorupa na dno (4× M2×8 od spodu), keycapy.

/* [Wybór części] */
part = "assembly";  // [shell, bottom, assembly, exploded]

/* [Płytka – wartości z pliku KiCad, zwykle bez zmian] */
edge_kicad = [[28.5, 54.75], [108.0, 143.5]];  // Edge.Cuts: lewy górny, prawy dolny
pitch      = 19.05;
keys_kicad_x = [38.1, 57.15, 76.2, 95.25];
keys_kicad_y = [66.35, 133.35];               // Row 0 (S1–S4), Row 1 (S5–S8)
holes_kicad  = [[51, 120], [96.5, 121], [38, 100], [104.5, 104.5], [60, 90]];  // H1–H5
mcu_kicad    = [[76.83, 81.73], [109.85, 99.51]];  // obrys Pro Micro (U1, obrót −90°)
usb_kicad_y  = 90.62;                              // oś gniazda USB na prawej krawędzi
j1_kicad     = [[92.4, 112.2], [101.6, 113.9]];    // pola J1 (bez złącza – przewody)
choc_court   = 7.75;  // połowa obrysu (courtyard) Choc V1
pcb_t      = 1.6;
pcb_hole_d = 3.2;    // otwory M3

/* [Pro Micro (od spodu płytki)] */
mcu_lift = 2.5;      // plastik goldpinów między PCB a Pro Micro
mcu_t    = 1.6;
usb_h    = 3.2;      // gniazdo USB pod płytką Pro Micro (elementy w dół)
usb_cut  = [12.0, 8.0];  // otwór na wtyk z obudową (szer. × wys.)
mcu_pocket_clear = 0.6;  // luz wokół części Pro Micro wystającej poza PCB

/* [OLED 2,42" SSD1309 – moduł ShengYang (docs/img/oled_242_shengyang.png)] */
// Warianty z karty sprzedawcy (wymiary płytki zwymiarowane, reszta – patrz uwagi):
//   "i2c_4pin" – 70,10 × 48,10 mm, 4 piny I²C u góry (zwykle GND VCC SCL SDA – sprawdź nadruk)
//                + złącze na dolnej krawędzi (od spodu – zdejmij, jeśli wystaje ponad 2 mm)
//   "spi_7pin" – 72,00 × 43,00 mm, 7 pinów z lewej (od pinu 1: GND VCC SCK SDA RES DC CS; I²C po
//                zmianie rezystorów), starsza wersja 70,90 × 43,40 mm
oled_variant  = "i2c_4pin";  // [i2c_4pin, spi_7pin]
oled_pcb      = oled_variant == "spi_7pin" ? [72.0, 43.0] : [70.1, 48.1];
// otwory Ø3 w narożnikach – rozstaw OSZACOWANY (ok. 3 mm od krawędzi), zmierz przed drukiem
oled_holes    = oled_variant == "spi_7pin" ? [66.0, 37.0] : [64.1, 42.1];
oled_pcb_t    = 1.6;
oled_glass    = [60.5, 37.0, 2.0];  // szkło panelu 2,42": szer., wys., grubość (typowe)
oled_glass_d  = [0.0, 0.0];         // przesunięcie środka szkła od środka modułu
oled_active   = [55.01, 27.49];     // obszar aktywny 128×64 (typowy dla panelu 2,42"), tylko podgląd
oled_back_clear = 2.0;              // tył modułu nad PCB: łby ISO 7380 (1,65), przycięte piny, przewody
oled_screw_pilot = 2.1;             // wkręt M2,5 wkręcany w płytę od spodu (do tworzyw)
glass_clear   = 0.3;                // luz szkła w otworze
glass_chamfer = 0.6;                // faza krawędzi otworu od góry

/* [Klawisze Choc] */
keycap    = [18.0, 18.0];  // keycap Choc w rastrze MX (pasują też mniejsze 17,5 × 16,5)
key_clear = 0.8;           // luz między keycapem a krawędzią otworu
key_deck_h = 6.0;          // wierzch płyty nad górą PCB (keycap wystaje ok. 3 mm)
choc_h    = 5.2;           // korpus Choc nad PCB (tylko podgląd)
cap_h     = 3.0;           // tylko podgląd

/* [Obudowa] */
rim        = 5.0;   // od krawędzi PCB do zewnętrznej ścianki
pcb_clear  = 0.4;   // luz między PCB a ścianką
floor_t    = 2.4;   // grubość dna
standoff_h = 10.0;  // spód PCB nad dnem: Pro Micro z USB, piny Choc, diody
standoff_d = 7.0;
top_t      = 2.0;   // grubość płyty górnej
corner_r   = 4.0;
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

pcb_holes = [for (h = holes_kicad) k2s(h)];
mcu_box = box2s(mcu_kicad);
usb_y   = k2s([0, usb_kicad_y])[1];
j1_box  = box2s(j1_kicad);
// ekran dokładnie pośrodku między rzędami
oled_c  = [keys_cx, (key_y[0] + key_y[1]) / 2];

inner = [pcb[0] + 2 * pcb_clear, pcb[1] + 2 * pcb_clear];  // wnętrze (od -pcb_clear)
// Obrys symetryczny względem klawiszy i ekranu w obu osiach (PCB jest szersza w prawo pod
// Pro Micro i ma większy margines nad górnym rzędem): dalszy bok wyznacza połowę wymiaru,
// po przeciwnej stronie ścianka jest odpowiednio grubsza.
half_w = max(pcb[0] + pcb_clear + rim - oled_c[0], oled_c[0] + pcb_clear + rim);
half_h = max(pcb[1] + pcb_clear + rim - oled_c[1], oled_c[1] + pcb_clear + rim);
outer = [2 * half_w, 2 * half_h];
o0    = [oled_c[0] - half_w, oled_c[1] - half_h];           // narożnik zewnętrzny

// wysokości (z = 0: spód dna)
pcb_bot   = floor_t + standoff_h;
pcb_top   = pcb_bot + pcb_t;
key_top   = pcb_top + key_deck_h;     // płaska góra obudowy
plate_under = key_top - top_t;
oled_back  = pcb_top + oled_back_clear;
oled_front = oled_back + oled_pcb_t;
glass_top  = oled_front + oled_glass[2];
boss_len   = plate_under - oled_front;  // gniazda wkrętów pod płytą (płytka modułu się o nie opiera)

well = [3 * pitch + keycap[0] + 2 * key_clear, keycap[1] + 2 * key_clear];

case_screws = [[o0[0] + rim / 2 + 1, o0[1] + rim / 2 + 1],
               [o0[0] + outer[0] - rim / 2 - 1, o0[1] + rim / 2 + 1],
               [o0[0] + rim / 2 + 1, o0[1] + outer[1] - rim / 2 - 1],
               [o0[0] + outer[0] - rim / 2 - 1, o0[1] + outer[1] - rim / 2 - 1]];

oled_hole_pos = [for (sx = [-1, 1], sy = [-1, 1])
                 [oled_c[0] + sx * oled_holes[0] / 2, oled_c[1] + sy * oled_holes[1] / 2]];
glass_c   = oled_c + oled_glass_d;
glass_cut = [oled_glass[0] + 2 * glass_clear, oled_glass[1] + 2 * glass_clear];

usb_zc = pcb_bot - mcu_lift - mcu_t - usb_h / 2;
// część Pro Micro wystająca poza prawą krawędź PCB – kieszeń w ściance (pod płytką)
mcu_pocket = [pcb[0], mcu_box[1] - mcu_pocket_clear,
              mcu_box[0] + mcu_box[2] - pcb[0] + mcu_pocket_clear, mcu_box[3] + 2 * mcu_pocket_clear];

// ---------------------------------------------------------------- kontrole

// materiał płyty wokół wkrętów modułu: do otworów na klawisze i do otworu na szkło
screw_to_well = min([for (h = oled_hole_pos) min(abs(h[1] - (key_y[0] - well[1] / 2)),
                                                 abs(h[1] - (key_y[1] + well[1] / 2)))])
                - oled_screw_pilot / 2;
screw_to_glass = min([for (h = oled_hole_pos) max(abs(h[0] - glass_c[0]) - glass_cut[0] / 2,
                                                  abs(h[1] - glass_c[1]) - glass_cut[1] / 2)])
                 - oled_screw_pilot / 2;
// moduł między obrysami przełączników (wisi nisko, obok ich korpusów)
module_to_switch = min(key_y[0] - choc_court - (oled_c[1] + oled_pcb[1] / 2),
                       (oled_c[1] - oled_pcb[1] / 2) - (key_y[1] + choc_court));
echo(str("ścianki: lewa ", -pcb_clear - o0[0], ", prawa ", o0[0] + outer[0] - pcb[0] - pcb_clear,
         ", dolna ", -pcb_clear - o0[1], ", górna ", o0[1] + outer[1] - pcb[1] - pcb_clear,
         " mm; środek obudowy ", o0 + outer / 2, " = środek klawiszy i ekranu ", oled_c));
echo(str("PCB ", pcb[0], " × ", pcb[1], " mm; obudowa ", outer[0], " × ", outer[1], " × ",
         key_top, " mm"));
echo(str("OLED ", oled_variant, ": szkło ", key_top - glass_top, " mm pod powierzchnią, gniazda ",
         boss_len, " mm, materiał wkręt–klawisze ", screw_to_well, " mm, wkręt–szkło ",
         screw_to_glass, " mm, moduł–przełączniki ", module_to_switch, " mm"));
assert(glass_top <= key_top, "szkło OLED wystaje ponad obudowę – zmniejsz oled_back_clear");
assert(boss_len >= 0, "moduł OLED nie mieści się pod płytą");
assert(screw_to_well >= 1.0, "za mało materiału między wkrętem OLED a otworem na klawisze");
assert(screw_to_glass >= 0.8, "za mało materiału między wkrętem OLED a otworem na szkło");
assert(module_to_switch >= 0.3, "moduł OLED nachodzi na przełączniki");

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

module well2d(i) {
  translate([keys_cx - well[0] / 2, key_y[i] - well[1] / 2]) rrect(well, well_r);
}

// ---------------------------------------------------------------- skorupa

module shell() {
  difference() {
    translate([0, 0, floor_t]) linear_extrude(key_top - floor_t) outline2d();
    // wnętrze pod płytą
    translate([0, 0, floor_t - 0.01]) linear_extrude(plate_under - floor_t + 0.01) inner2d();
    // otwory na rzędy klawiszy
    for (i = [0, 1]) translate([0, 0, pcb_top]) linear_extrude(key_top) well2d(i);
    // otwór na szkło OLED z fazą od góry
    translate([glass_c[0] - glass_cut[0] / 2, glass_c[1] - glass_cut[1] / 2, plate_under - 0.01])
      cube([glass_cut[0], glass_cut[1], top_t + 0.02]);
    hull() {
      translate([glass_c[0] - glass_cut[0] / 2, glass_c[1] - glass_cut[1] / 2, key_top - glass_chamfer])
        cube([glass_cut[0], glass_cut[1], 0.01]);
      translate([glass_c[0] - glass_cut[0] / 2 - glass_chamfer,
                 glass_c[1] - glass_cut[1] / 2 - glass_chamfer, key_top])
        cube([glass_cut[0] + 2 * glass_chamfer, glass_cut[1] + 2 * glass_chamfer, 0.01]);
    }
    // USB (prawa ścianka)
    translate([pcb[0] - 1, usb_y - usb_cut[0] / 2, usb_zc - usb_cut[1] / 2])
      cube([rim + pcb_clear + 2, usb_cut[0], usb_cut[1]]);
    // kieszeń na Pro Micro wystające poza PCB (pod płytką)
    translate([mcu_pocket[0] - 0.01, mcu_pocket[1], floor_t - 0.01])
      cube([mcu_pocket[2] + 0.01, mcu_pocket[3], pcb_bot - floor_t - 0.2]);
    // wkręty skorupy od spodu
    for (p = case_screws) translate([p[0], p[1], floor_t - 0.01]) cylinder(d = case_screw_pilot, h = 9);
    // wkręty modułu OLED od spodu w płytę (nie na wylot)
    for (p = oled_hole_pos)
      translate([p[0], p[1], oled_front - 0.01]) cylinder(d = oled_screw_pilot, h = key_top - oled_front - 0.6);
  }
  // gniazda wkrętów: płytka modułu opiera się o nie (wysokość boss_len pod płytą)
  if (boss_len > 0.05)
    for (p = oled_hole_pos)
      translate([p[0], p[1], oled_front])
        difference() {
          cylinder(d = oled_screw_pilot + 2.2, h = boss_len + 0.01);
          translate([0, 0, -0.01]) cylinder(d = oled_screw_pilot, h = boss_len + 0.03);
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
    // USB i Pro Micro: kołnierz nie może ich blokować
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
  // J1 – pola na przewody
  color("gold") translate([j1_box[0], j1_box[1], pcb_top]) cube([j1_box[2], j1_box[3], 0.1]);
  // łby M3 ISO 7380
  for (p = pcb_holes) color("gainsboro") translate([p[0], p[1], pcb_top]) cylinder(d = 5.7, h = 1.65);
}

module oled_model() {
  color("midnightblue") translate([oled_c[0] - oled_pcb[0] / 2, oled_c[1] - oled_pcb[1] / 2, oled_back])
    difference() {
      cube([oled_pcb[0], oled_pcb[1], oled_pcb_t]);
      for (p = oled_hole_pos)
        translate([p[0] - oled_c[0] + oled_pcb[0] / 2, p[1] - oled_c[1] + oled_pcb[1] / 2, -1]) cylinder(d = 3, h = 4);
    }
  color("black") translate([glass_c[0] - oled_glass[0] / 2, glass_c[1] - oled_glass[1] / 2, oled_front])
    cube(oled_glass);
  color("deepskyblue") translate([glass_c[0] - oled_active[0] / 2, glass_c[1] - oled_active[1] / 2, glass_top - 0.05])
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
  translate([0, 0, 45]) oled_model();
  translate([0, 0, 45]) color("silver", 0.9) shell();
} else {
  color("lightgray") bottom();
  pcb_model();
  oled_model();
  color("silver", 0.55) shell();
}

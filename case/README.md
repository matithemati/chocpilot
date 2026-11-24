# Obudowa ChocPilot v0

Model SolidCraft: `chocpilot_v0_case.sc` (eksporty: `chocpilot_v0_case.step`, `chocpilot_v0_case.3mf`,
`chocpilot_v0_shell.stl`, `chocpilot_v0_bottom.stl`). Stary `chocpilot_case.scad` jest dla wcześniejszej
płytki z Pro Micro i OLED – nie pasuje do v0.

Współrzędne modelu: środek płytki w (0, 0), X w prawo, Y w stronę USB-C (górna krawędź PCB),
Z = 0 pod dnem. Płytka: dół na z = 7,0, góra na z = 8,6.

Wersja z dnem z płyty mlecznej (zamiast drukowanego): [Obudowa v2](#obudowa-v2--dno-z-płyty-mlecznej).

## Części

| Część | Opis |
|---|---|
| **Shell** (góra) | 116,4 × 95,4 × 19,6 mm (z 2,0–21,6). Podwyższony środek i boczne kolumny (góra 13 mm nad PCB): okno ekranu, otwory pokręteł Ø7,4, szczelina suwaka 2,6 × 50 mm. Dwie obniżone wnęki na rzędy klawiszy (krawędź 4 mm nad PCB, otwarte na zewnątrz). Ścianki 0,9 mm pod płytką, 2,5 mm nad nią. |
| **Bottom** (dno) | 2 mm, kołnierz centrujący 1,5 mm wchodzący w Shell (luz 0,2 mm), 4 słupki 5 mm pod otworami M3 płytki, otwory Ø4 pod RESET i BOOT (naciskać szpilką). |

## Montaż

1. **Ekran** (Waveshare 2" LCD, 58 × 35 mm, otwory 2,5 mm od krawędzi = rozstaw 53 × 30): szkłem do okna,
   4× **M2×5** wkręcane w tuleje Shell (otwór wstępny Ø1,6). Piny / złącze PH2.0 modułu w prawo (w stronę J2).
2. **Płytka + obudowa:** płytka na słupki dna, Shell od góry; 4× **M3×14 z łbem stożkowym** (ISO 10642) od
   spodu przez dno, słupek i płytkę w kołki Shell (otwór Ø2,5 – wkręt gwintuje plastik). Jedna śruba na
   otwór ściska wszystko.
3. **USB-C:** gniazdo kończy się dokładnie na zewnętrznej ściance; otwór w kształcie gniazda (luz 0,1 mm
   na stronę), od zewnątrz faza 0,6 mm – wtyk wchodzi w gniazdo, a jego obudowa opiera się o ściankę.

## Do sprawdzenia przed drukiem

- **J2 – prosta listwa z żeńskimi wtykami jest za wysoka:** wtyki kabla sięgają ok. 16,5 mm nad PCB, a pod
  płytą jest 11 mm. Użyj listwy kątowej albo przylutuj przewody kabla bezpośrednio do J2.
- **Grubość szkła ekranu:** tuleje mają 2,6 mm (szkło dociskane do spodu płyty). Przy innej grubości zmień
  wysokość `ScreenBoss1–4` albo dołóż podkładki.
- **Położenie okna** (41,6 × 31,4 mm, środek 3,15 mm od środka modułu w stronę przeciwną do pinów,
  czyli w stronę pokręteł) – przesunięte o 1 mm w stronę pokręteł względem rysunku Waveshare po
  przymiarce na module.
- **Dźwignia suwaka** (4 × 1,2 mm): szczelina 2,6 mm zakłada cieńszy wymiar w poprzek szczeliny.
- **Pokrętła EC11 H20:** nad płytą zostaje ok. 7 mm osi na gałkę.

## Druk

- Shell górą do stołu, podpory tylko pod krawędziami wnęk klawiszy.
- Dno płasko; z półprzezroczystego filamentu, jeśli diody LED na spodzie mają podświetlać biurko.

## Keycapy, gałki pokręteł, nakładka suwaka

Model: `chocpilot_v0_caps.sc` (STEP: `chocpilot_v0_caps.step`; STL: `chocpilot_v0_keycap.stl` ×8,
`chocpilot_v0_knob.stl` ×2, `chocpilot_v0_slider_cap.stl` ×1). Części stoją w położeniu montażowym
(te same współrzędne co obudowa) – w slicerze połóż je górą do stołu.

| Część | Wymiary | Dopasowanie |
|---|---|---|
| **Keycap** (Kailh Choc V1, dwie nogi) | 17,8 × 17,8 mm, **wysokość 5 mm bez trzpienia** (podkładka i nogi pod spodem), wgłębienie 0,5 mm | Góra **równo z górą obudowy** (z = 21,6). Pod spodem podkładka 7,6 × 3,6 mm opierająca się o wierzch trzpienia i dwie nogi 1,2 × 3,0 mm, rozstaw 5,7 mm, długość 3 mm – wysokość keycapa zależy od `stem_top`. Ścianki 0,9 mm, wnęka 16 × 16 nad obudową przełącznika; dół keycapa 8 mm nad PCB, przy pełnym skoku 3 mm – 5 mm. **Nie pasuje do Choc V2** (trzpień krzyżakowy MX). |
| **Gałka EC11** | Ø18 × 8 mm, 24 rowki chwytu, znacznik na górze | 0,6 mm nad płytą (przycisk enkodera ma ok. 0,5 mm skoku). Otwór D: Ø6,1 ze ścięciem 4,6 mm (oś EC11E15244G1 Ø6, D 4,5), głębokość 6,7 mm. |
| **Nakładka suwaka** | 10 × 12 × 8 mm, wklęsła góra pod palec | 0,6 mm nad płytą. Gniazdo dźwigni 1,4 × 4,3 mm (dźwignia 1,2 × 4), głębokość 3,7 mm – dźwignia ALPS 10 mm, wierzch ok. 17 mm nad PCB. |

**Zmierz przed drukiem całego kompletu** (parametry w SolidCraft, `set_parameter`):
- `stem_top` – odległość od wierzchu PCB do wierzchu trzpienia Choc V1 w spoczynku (domyślnie 7,5 mm –
  oszacowanie: skok 3 mm ponad obudową; nie z rysunku Kailh). Keycap sam dopasuje się tak, by góra była
  równo z obudową.
- Nogi: `leg_w` 1,2 (grubość), `leg_d` 3,0, `leg_pitch` 5,7 (rozstaw), `leg_len` 3,0. Za luźno → `leg_w` 1,25,
  za ciasno (pęka trzpień) → 1,1.
- Pozostałe: `cap_h` (wysokość keycapa bez trzpienia, 5 mm), `top_t` (grubość góry), `dish` (głębokość wgłębienia).
- Gałka i suwak mają wymiary liczbowe (oś enkodera 20 mm, dźwignia 10 mm) – przy innej wysokości
  dźwigni zmień wysokość `LeverSocket`.

Druk: PLA/PETG, 0,12–0,16 mm warstwy, keycap i gałka górą do stołu (bez podpór, gładka góra),
nakładka suwaka też górą do stołu – wklęsła góra wymaga wtedy podpór, albo drukuj ją podstawą w dół.
Najpierw wydrukuj jeden keycap i sprawdź wysokość i krzyżak.

## Podstawka

Model: `chocpilot_v0_stand.sc` (STEP: `chocpilot_v0_stand.step`, STL: `chocpilot_v0_stand.stl`).

- Kołyska pochylająca urządzenie o **20°**: płyta pod całym spodem obudowy, z przodu próg 6 mm
  (przednia krawędź obudowy opiera się o niego), z tyłu stopka wysunięta 16 mm za płytę – mocne
  naciśnięcie tylnego rzędu nie przewróci podstawki do tyłu.
- 96 × 100 × 36 mm; podstawka jest węższa od urządzenia (116 mm), więc obudowa wystaje po 10 mm
  z boków – łatwo ją chwycić i podnieść. Nic jej nie trzyma poza progiem i grawitacją.
- **Naklejki gumowe 3M Ø9 mm (8 szt.):** 4 w gniazdach Ø9,6 × 1 mm na spodzie (podstawka nie jeździ
  po biurku) i 4 w gniazdach na płycie – urządzenie leży na gumie: nie stuka, nie zsuwa się na boki,
  a podnosi się bez oporu.
- USB-C (tylna krawędź obudowy) wystaje za płytę – kabel ma wolne miejsce.
- Trójkątne okno w profilu zmniejsza ilość materiału (ok. 98 cm³ litego materiału, przy 20 %
  wypełnienia ok. 50 g).

Druk: **na boku** (profil płasko na stole, oś X do góry) – bez podpór, warstwy wzdłuż profilu
(najmocniejszy kierunek), brim 5 mm. PLA/PETG, 3–4 obrysy, 15–20 % wypełnienia.

## Obudowa v2 – dno z płyty mlecznej

Model SolidCraft: `chocpilot_v2_case.sc` (STEP całości: `chocpilot_v2_case.step`). Górna część to **ten sam
Shell co w v0** (`chocpilot_v0_shell.stl` – już wydrukowany pasuje). Drukowane dno zastępuje płaska płyta
z tworzywa mlecznego (opal), która rozprasza światło 12 diod WS2812B ze spodu płytki: świeci cały spód
i krawędź płyty, a blat dostaje miękką poświatę zamiast 12 kropek.

| Część | Materiał | Pliki |
|---|---|---|
| **Dno** 116,4 × 95,4 mm, R3,2 | płyta mleczna (opal) **3 mm**: pleksi (PMMA, „szkło akrylowe”) albo polistyren – arkusze do cięcia w marketach budowlanych (dział szkło organiczne / płyty z tworzyw) | `chocpilot_v2_bottom_template.pdf` (szablon 1:1 do druku), `chocpilot_v2_bottom.dxf` (do cięcia laserem), `chocpilot_v2_bottom.step` |
| **Tulejki dystansowe** ×4, Ø6 × 5 mm, otwór Ø3,4 | druk 3D (PLA/PETG) | `chocpilot_v2_spacer.stl` (wydrukuj 4) |
| **Wkręty** ×4 | **M3×16 z łbem stożkowym** (DIN 7991 / ISO 10642), stal | – |
| **Nóżki** ×4 | samoprzylepne odbojniki Ø10, wysokość ≥ 3 mm | – |

Położenie w modelu: płyta od z = −1 do z = 2 (spód urządzenia o 1 mm niżej niż w v0), tulejki z = 2–7, płytka
z = 7,0–8,6 jak w v0. Diody (WS2812B, 1,6 mm) kończą się na z ≈ 5,4 – 3,4 mm nad płytą.

Parametry (`set_parameter`): `sheet_t` (grubość płyty – przy polistyrenie 2,5 mm ustaw 2,5; Shell i płytka
zostają na miejscu, zmienia się tylko spód), `spacer_h` (= `pcb_bot − rim_z`, 5 mm), `screw_d`, `cs_d`
(fazowanie pod łeb), `access_d`. Szablon generuje `tools/gen_bottom_template.py` – przy zmianie wymiarów
popraw liczby w skrypcie.

### Wykonanie dna

1. Wydrukuj `chocpilot_v2_bottom_template.pdf` w skali **100 %** i sprawdź linijką pasek 100 mm.
   Szablon to **widok od spodu** (strona z fazowaniem), krawędź z USB-C u góry – przy innym ułożeniu
   otwory wyjdą w lustrzanym odbiciu.
2. Przyklej szablon na płytę (na folię ochronną). Tnij z naddatkiem ~0,5 mm: pleksi/polistyren 2,5–3 mm
   zarysuj kilka razy nożem do tworzyw wzdłuż linijki i złam na krawędzi stołu; narożniki R3,2 i krawędzie
   wyrównaj pilnikiem / papierem ściernym do obrysu (albo po złożeniu równo ze ścianką Shell).
3. Wierć ostrym wiertłem, na małych obrotach, płyta na desce: 4× Ø3,4 i 2× Ø4 (RESET, BOOT). Od strony
   szablonu zfazuj otwory M3 pogłębiaczem 90° do Ø6,4 (łeb wkrętu równo z płytą). Otwór H2 jest 4,7 mm od
   krawędzi – fazuj delikatnie.
4. Zdejmij folię z obu stron. Krawędź płyty można przeszlifować na mat (P400–P800) – świeci równiej.

Zamiast cięcia ręcznego: `chocpilot_v2_bottom.dxf` (mm, widok od spodu; warstwa `CUT` – cięcie,
`COUNTERSINK_NO_CUT` – tylko oznaczenie fazowania) przyjmie każdy zakład cięcia laserem pleksi.

### Montaż v2

Jak w v0, ale zamiast dna: wkręt M3×16 od spodu przez płytę → tulejkę → płytkę → kołek Shell (otwór Ø2,5,
wkręt gwintuje plastik; ok. 6 mm gwintu w kołku). Dokręcaj z wyczuciem – łeb stożkowy rozpycha tworzywo
i przy przeciągnięciu pleksi pęka. Na koniec nóżki w miejscach z szablonu (z dala od łbów wkrętów).

### Do sprawdzenia

- **Równomierność światła:** 3,4 mm od diody do płyty to mało – przez gęstą płytę opal będą widać jaśniejsze
  plamy nad diodami. Płyta „satynowa” / mniej mleczna daje więcej światła na blat; firmware i tak musi
  ograniczać jasność.
- **Tulejki zamiast słupków dna:** drukowane, bo tulejek dystansowych M3 zwykle nie ma w marketach. Zamiast nich
  można dać 2 nakrętki M3 + podkładkę (≈ 5,3 mm) – wtedy między płytą a Shell zostaje ok. 0,3 mm szczeliny.

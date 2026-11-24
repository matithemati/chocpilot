# Obudowa ChocPilot

Obudowa, keycapy, gałki i podstawka dla płytki ChocPilot (STM32F072, `pcb/`) z ekranem Waveshare 2" IPS
LCD. Modele są w SolidCraft (`.sc`, parametryczne), obok eksporty STEP (do innych programów CAD),
3MF i STL (do druku).

Model obudowy: `chocpilot_case.sc` (eksporty: `chocpilot_case.step`, `chocpilot_case.3mf`,
`chocpilot_shell.stl`, `chocpilot_bottom.stl`).

Współrzędne modelu: środek płytki w (0, 0), X w prawo, Y w stronę USB-C (górna krawędź PCB),
Z = 0 pod dnem. Płytka: dół na z = 7,0, góra na z = 8,6.

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

Model: `chocpilot_caps.sc` (STEP: `chocpilot_caps.step`; STL: `chocpilot_keycap.stl` ×8,
`chocpilot_knob.stl` ×2, `chocpilot_slider_cap.stl` ×1). Części stoją w położeniu montażowym
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

Model: `chocpilot_stand.sc` (STEP: `chocpilot_stand.step`, STL: `chocpilot_stand.stl`).

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

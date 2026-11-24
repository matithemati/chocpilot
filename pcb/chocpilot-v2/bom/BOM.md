# ChocPilot v0 – BOM

Wygenerowano z `tools/design.py` (`python3 tools/gen_bom.py`). Ten sam plik jako CSV: [chocpilot-v0-bom.csv](chocpilot-v0-bom.csv).

Wszystkie elementy lutowane na płytce poza przełącznikami Kailh są w TME – numery sprawdzone w katalogu tme.eu 04.11.2026: na stanie TME w potrzebnej ilości i bez oznaczenia „Hardly available product” / „till the stock lasts”. Ekran (Waveshare WSH-17344) też jest w TME. TME nie sprzedaje produktów Kailh – przełączniki Choc V2 trzeba kupić gdzie indziej (Amazon), podobnie keycapy, gałki i nakładkę suwaka. Listwy kołkowe J2 (ekran) i J3 (SWD) nie są ujęte – z własnego zapasu.

| Poz. | Oznaczenia | Ilość | Opis | Obudowa | Producent | Nr producenta | TME | Amazon (alternatywa) | Montaż | Uwagi |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | J1 | 1 | USB-C 2.0, wlutowane 16 padów SMD (raster 0,5) + 4 kołki THT | SMD 16P + THT | GCT | USB4105-GF-A | USB4105-GF-A |  | SMD |  |
| 2 | F1 | 1 | Bezpiecznik polimerowy PTC 0,5 A (zadziałanie 1 A) | 1206 | Bourns | MF-NSMF050-2 | MF-NSMF050-2 |  | SMD |  |
| 3 | R1, R2 | 2 | Rezystor 5.1kΩ 1% 0805 | 0805 | Yageo | RC0805FR-075K1L | RC0805FR-075K1 |  | SMD |  |
| 4 | U3 | 1 | Ochrona ESD linii D+/D− | SOT-23-6 | STMicroelectronics | USBLC6-2SC6 | USBLC6-2SC6 |  | SMD |  |
| 5 | U2 | 1 | LDO 3,3 V / 400 mA | SOT-23-5 | Texas Instruments | TPS73633DBVR | TPS73633DBVR |  | SMD |  |
| 6 | C1, C3, C15, C18 | 4 | Kondensator 10µF X7R 0805 | 0805 | KEMET | C0805C106M8RACTU | C0805C106M8RACTU |  | SMD |  |
| 7 | C2, C11 | 2 | Kondensator 1µF X7R 0805 | 0805 | KYOCERA AVX | KAM21KR71E105KU | KAM21KR71E105KU |  | SMD |  |
| 8 | C4 | 1 | Kondensator 10nF X7R 0805 | 0805 | KYOCERA AVX | KGM21NR72A103KT | KGM21NR72A103KT |  | SMD |  |
| 9 | U1 | 1 | MCU Cortex-M0 48 MHz, USB FS bez kwarcu, bootloader DFU w ROM | LQFP-48 0,5 mm | STMicroelectronics | STM32F072CBT6 | STM32F072CBT6 |  | SMD |  |
| 10 | C5–C8, C10, C12, C16, C17, C19–C30 | 20 | Kondensator 100nF X7R 0805 | 0805 | KYOCERA AVX | KAM21BR71H104KT | KAM21BR71H104KT |  | SMD |  |
| 11 | C9 | 1 | Kondensator 4.7µF X7R 0805 | 0805 | KYOCERA AVX | KGM21AR71C475KU | KGM21AR71C475KU |  | SMD |  |
| 12 | Y1 | 1 | Kwarc 8 MHz, CL 18 pF (opcjonalny – USB działa z HSI48+CRS) | 5032 2-pad | Abracon | ABM3-8.000MHZ-D2Y-T | ABM3-8.000MHZ-D2Y |  | SMD | opcjonalny – USB działa bez kwarcu |
| 13 | C13, C14 | 2 | Kondensator 27pF C0G 0805 | 0805 | KYOCERA AVX | 08055A270GAT2A | 08055A270GAT2A |  | SMD |  |
| 14 | R3 | 1 | Rezystor 10kΩ 1% 0805 | 0805 | Yageo | RC0805FR-0710KL | RC0805FR-0710K |  | SMD |  |
| 15 | SW1 | 1 | Reset (od spodu płytki) | SMD 6×6 mm | C&K | PTS645SM43SMTR92 LFS | PTS645SM43SMTR92 |  | SMD (spód) |  |
| 16 | SW2 | 1 | BOOT0 – wejście do bootloadera DFU (od spodu płytki) | SMD 6×6 mm | C&K | PTS645SM43SMTR92 LFS | PTS645SM43SMTR92 |  | SMD (spód) |  |
| 17 | ENC1, ENC2 | 2 | Enkoder EC11 z przyciskiem (15 imp./30 zatrzasków) | THT | ALPS | EC11E15244G1 | EC11E15244G1 |  | THT |  |
| 18 | RV1 | 1 | Potencjometr suwakowy 45 mm, 10 kΩ liniowy (dół = GND, góra = 3,3 V) | THT | ALPS | RS45111A900F | RS45111A900F |  | THT |  |
| 19 | D1–D8 | 8 | Dioda matrycy klawisza K1 (katoda → wiersz) | SOD-123 | Vishay | 1N4148W-E3-08 | 1N4148W-E3-08 |  | SMD (spód) |  |
| 20 | U4 | 1 | Konwerter poziomu 3,3 V → 5 V dla linii danych LED | SOT-23-5 | Texas Instruments | SN74AHCT1G125DBVR | SN74AHCT1G125DBVR |  | SMD |  |
| 21 | R6 | 1 | Rezystor 330Ω 1% 0805 | 0805 | Yageo | RC0805FR-07330RL | RC0805FR-07330R |  | SMD |  |
| 22 | L1–L12 | 12 | LED adresowalny RGB, spód płytki (podświetlenie blatu) | 5050 PLCC4 | Worldsemi | WS2812B-V6 | WS2812B-V6 | WS2812B 5050 SMD chip (np. BTF-LIGHTING) | SMD (spód) |  |
| 23 | S1–S8 | 8 | Przełącznik Kailh Choc V2 (low profile, trzpień MX) | THT | Kailh | CPG1353 (Choc V2) | brak w TME | amazon.de B0CMZWF635 (Kailh Choc V2 Brown) lub inny Choc V2 | THT (lutowany od spodu) | brak w TME; pasują też Choc V1 (CPG1350) |
| 24 | — | 8 | Keycap 1u w profilu MX (Choc V2 ma trzpień MX) | — | — | — | brak w TME | keycaps MX 1u (np. low profile) | — | raster 19,05 mm |
| 25 | ENC1, ENC2 | 2 | Gałka do enkodera, oś 6 mm D, Ø ≤ 18 mm | — | — | — | — | potentiometer knob 6 mm D shaft | — | oś D 6 mm |
| 26 | RV1 | 1 | Nakładka na dźwignię suwaka ALPS RS (dźwignia 4 × 1,2 mm) | — | — | — | — | slide potentiometer knob cap 4 x 1.2 mm | — | wąska (≤ 8 mm) – patrz DESIGN_NOTES |
| 27 | J2 | 1 | Ekran LCD 2" IPS 240×320, ST7789V, SPI (Waveshare 2inch LCD Module, z kablem PH2.0) | 58 × 35 mm | Waveshare | 17344 | WSH-17344 |  | w obudowie, kabel PH2.0 → J2 | kabel 1:1 na J2 (VCC na pin 1); zasilanie 3,3 V – logika modułu = VCC |
| 28 | H1–H4 | 4 | Śruba M3 × 6 + tuleja dystansowa / wkładka do obudowy | — | — | — | — | M3 screws assortment | — | zależnie od obudowy |

## Footprinty

| Oznaczenia | Footprint KiCad |
|---|---|
| J1 | `Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal` |
| F1 | `Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder` |
| R1, R2 | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` |
| U3 | `Package_TO_SOT_SMD:SOT-23-6_Handsoldering` |
| U2 | `Package_TO_SOT_SMD:SOT-23-5_HandSoldering` |
| C1, C3, C15, C18 | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| C2, C11 | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| C4 | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| U1 | `Package_QFP:LQFP-48_7x7mm_P0.5mm` |
| C5–C8, C10, C12, C16, C17, C19–C30 | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| C9 | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| Y1 | `Crystal:Crystal_SMD_5032-2Pin_5.0x3.2mm_HandSoldering` |
| C13, C14 | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| R3 | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` |
| SW1 | `Button_Switch_SMD:SW_SPST_PTS645Sx43SMTR92` |
| SW2 | `Button_Switch_SMD:SW_SPST_PTS645Sx43SMTR92` |
| ENC1, ENC2 | `Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm` |
| RV1 | `chocpilot:Potentiometer_Alps_RS45111_Slide_45mm` |
| D1–D8 | `Diode_SMD:D_SOD-123` |
| U4 | `Package_TO_SOT_SMD:SOT-23-5_HandSoldering` |
| R6 | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` |
| L1–L12 | `LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm` |

Elementów lutowanych na płytce: 63 SMD, 3 THT (+8 przełączników Choc THT).

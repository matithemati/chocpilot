"""ChocPilot v2 – jedno źródło prawdy dla schematu, PCB i BOM.

Każdy element: oznaczenie, symbol z biblioteki KiCad, footprint, mapa pin → sieć
(None = pin niepodłączony, na schemacie znacznik „no connect”), położenie na płytce
(współrzędne względem lewego górnego rogu płytki, mm) oraz dane do BOM (producent, numer
części, TME, Amazon). Rozmieszczenie symboli na schemacie jest w gen_sch.py.

Uruchamiane z gen_sch.py, gen_pcb.py i gen_bom.py – nie zawiera logiki generującej.
"""

# ---------------------------------------------------------------- geometria płytki
BOARD_W = 110.0
BOARD_H = 93.0
BOARD_ORIGIN = (50.0, 50.0)       # lewy górny róg płytki we współrzędnych KiCad
CORNER_R = 2.0

XC = BOARD_W / 2                  # środek ekranu i rzędów klawiszy (oś symetrii)
YM = BOARD_H / 2                  # środek ekranu
PITCH = 19.05                     # raster klawiszy (Choc V2 = keycapy MX)
ROW_DY = 34.0                     # środek rzędu ↔ środek ekranu (rzędy 68 mm od siebie)
Y_TOP = YM - ROW_DY               # 12.5
Y_BOT = YM + ROW_DY               # 80.5
KEY_X = [XC + (i - 1.5) * PITCH for i in range(4)]

OLED_W, OLED_H = 70.10, 48.10     # moduł ShengYang 2,42" 4-pin I²C
OLED_PIN_Y = YM - OLED_H / 2 + 2.0  # piny modułu: środek górnej krawędzi, ~2 mm od niej

ENC_X = 12.5                      # oś enkoderów (lewa kolumna)
ENC_Y = [YM - 12.0, YM + 12.0]
SLIDER_X = 95.5                   # pin 1 PTA4543 (obrót 90°); korpus poza obrysem modułu OLED

MCU_X, MCU_Y = 62.0, 46.0


# ---------------------------------------------------------------- biblioteki
FP_R = 'Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder'
FP_C = 'Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder'
FP_SW = 'chocpilot:SW_Kailh_Choc_V1V2_Hotswap_1u'
FP_LED = 'LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm'
FP_BTN = 'Button_Switch_SMD:SW_SPST_PTS645Sx43SMTR92'
FP_ENC = 'Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm'
FP_HOLE = 'MountingHole:MountingHole_3.2mm_M3'

# Numery TME sprawdzone w katalogu tme.eu 2026-10-29 (patrz docs/BOM.md).
PASSIVE = {
    # wartość: (producent, numer producenta, symbol TME)
    'R5.1k': ('Yageo', 'RC0805FR-075K1L', 'RC0805FR-075K1'),
    'R10k': ('Yageo', 'RC0805FR-0710KL', 'RC0805FR-0710K'),
    'R4.7k': ('Yageo', 'RC0805FR-074K7L', 'RC0805FR-074K7'),
    'R330': ('Yageo', 'RC0805FR-07330RL', 'RC0805FR-07330R'),
    'C100n': ('Samsung', 'CL21B104KBCNNNC', 'CL21B104KBCNNNC'),
    'C10n': ('Samsung', 'CL21B103KBANNNC', 'CL21B103KBANNNC'),
    'C1u': ('Samsung', 'CL21B105KBFNNNE', 'CL21B105KBFNNNE'),
    'C4.7u': ('Samsung', 'CL21A475KAQNNNE', 'CL21A475KAQNNNE'),
    'C10u': ('Samsung', 'CL21A106KAYNNNE', 'CL21A106KAYNNNE'),
    'C27p': ('Samsung', 'CL21C270JBANNNC', 'CL21C270JBANNNC'),
}

parts = []


def part(ref, lib, value, fp, pins, pcb, bom=None, dnp=False, desc=''):
    """pcb = (x, y, rot, 'F'|'B') względem lewego górnego rogu płytki; rozmieszczenie na
    schemacie jest w gen_sch.py."""
    parts.append(dict(ref=ref, lib=lib, value=value, fp=fp, pins=pins, pcb=pcb,
                      bom=bom or {}, dnp=dnp, desc=desc))


def passive(ref, kind, value, net1, net2, pcb, desc=''):
    key = kind + value.replace('Ω', '').replace('F', '')
    mfr, mpn, tme = PASSIVE[key]
    fp = FP_R if kind == 'R' else FP_C
    part(ref, 'Device:' + kind, value, fp, {'1': net1, '2': net2}, pcb,
         bom=dict(mfr=mfr, mpn=mpn, tme=tme, pkg='0805'), desc=desc)


# ================================================================ USB i zasilanie
UX = 103.5                       # oś złącza USB-C (górna krawędź, prawy róg)
part('J1', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C',
     'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal',
     {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND',
      'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS',
      'A5': 'CC1', 'B5': 'CC2', 'A6': 'USB_CONN_DP', 'B6': 'USB_CONN_DP',
      'A7': 'USB_CONN_DN', 'B7': 'USB_CONN_DN', 'A8': None, 'B8': None, 'SH': 'GND'}, pcb=(UX, 3.675, 180, 'F'),
     bom=dict(mfr='GCT', mpn='USB4105-GF-A', tme='USB4105-GF-A', pkg='SMD 16P + THT'),
     desc='USB-C 2.0, wlutowane 16 padów SMD (raster 0,5) + 4 kołki THT')
part('F1', 'Device:Polyfuse', '500mA', 'Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder',
     {'1': 'VBUS', '2': '+5V'}, pcb=(UX, 12.5, 0, 'F'),
     bom=dict(mfr='Bourns', mpn='MF-NSMF050-2', tme='MF-NSMF050-2', pkg='1206'),
     desc='bezpiecznik polimerowy PTC 0,5 A (zadziałanie 1 A)')
passive('R1', 'R', '5.1k', 'CC1', 'GND', pcb=(107.5, 12.5, 90, 'F'),
        desc='CC1 → GND: urządzenie USB-C (Rd)')
passive('R2', 'R', '5.1k', 'CC2', 'GND', pcb=(99.5, 12.5, 90, 'F'),
        desc='CC2 → GND: urządzenie USB-C (Rd)')
part('U3', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6_Handsoldering',
     {'1': 'USB_CONN_DP', '6': 'USB_DP', '3': 'USB_CONN_DN', '4': 'USB_DN', '2': 'GND', '5': 'VBUS'}, pcb=(96.0, 11.5, 270, 'F'),
     bom=dict(mfr='STMicroelectronics', mpn='USBLC6-2SC6', tme='USBLC6-2SC6', pkg='SOT-23-6'),
     desc='ochrona ESD linii D+/D−')
part('U2', 'Regulator_Linear:TPS73633DBV', 'TPS73633DBVR', 'Package_TO_SOT_SMD:SOT-23-5_HandSoldering',
     {'1': '+5V', '3': '+5V', '2': 'GND', '4': 'LDO_NR', '5': '+3V3'}, pcb=(82.0, 30.0, 0, 'F'),
     bom=dict(mfr='Texas Instruments', mpn='TPS73633DBVR', tme='TPS73633DBVR', pkg='SOT-23-5'),
     desc='LDO 3,3 V / 400 mA')
passive('C1', 'C', '10uF', '+5V', 'GND', pcb=(UX + 1.0, 16.0, 0, 'F'),
        desc='+5V – pojemność wejściowa przy USB')
passive('C2', 'C', '1uF', '+5V', 'GND', pcb=(82.0, 34.0, 0, 'F'),
        desc='wejście LDO')
passive('C3', 'C', '10uF', '+3V3', 'GND', pcb=(86.5, 30.0, 90, 'F'),
        desc='wyjście LDO')
passive('C4', 'C', '10nF', 'LDO_NR', 'GND', pcb=(78.0, 30.0, 90, 'F'),
        desc='NR – filtr szumów LDO')

# ================================================================ MCU
MX, MY = MCU_X, MCU_Y
mcu_pins = {
    '1': '+3V3', '24': '+3V3', '48': '+3V3', '36': '+3V3', '9': '+3V3',
    '8': 'GND', '23': 'GND', '35': 'GND', '47': 'GND',
    '7': 'NRST', '44': 'BOOT0', '5': 'OSC_IN', '6': 'OSC_OUT',
    '32': 'USB_DN', '33': 'USB_DP', '34': 'SWDIO', '37': 'SWCLK',
    '42': 'OLED_SCL', '43': 'OLED_SDA',
    '46': 'K1', '45': 'K2', '41': 'K3', '40': 'K4',
    '14': 'K5', '15': 'K6', '20': 'K7', '21': 'K8',
    '10': 'ENC1_A', '11': 'ENC1_B', '12': 'ENC1_SW',
    '16': 'ENC2_A', '17': 'ENC2_B', '13': 'ENC2_SW',
    '19': 'SLIDER', '28': 'LED_DATA_3V3',
    # wolne: PC13–PC15, PB0, PB3, PA15, PB11–PB14, PA8–PA10
    '2': None, '3': None, '4': None, '18': None, '22': None, '25': None, '26': None,
    '27': None, '29': None, '30': None, '31': None, '38': None, '39': None,
}
part('U1', 'MCU_ST_STM32F0:STM32F072CBTx', 'STM32F072CBT6', 'Package_QFP:LQFP-48_7x7mm_P0.5mm',
     mcu_pins, pcb=(MX, MY, 0, 'F'),
     bom=dict(mfr='STMicroelectronics', mpn='STM32F072CBT6', tme='STM32F072CBT6', pkg='LQFP-48 0,5 mm'),
     desc='MCU Cortex-M0 48 MHz, USB FS bez kwarcu, bootloader DFU w ROM')
# odsprzęganie – przy każdej parze VDD/VSS
passive('C5', 'C', '100nF', '+3V3', 'GND', pcb=(MX - 3.75, MY - 8.5, 0, 'F'), desc='VDD (48)')
passive('C6', 'C', '100nF', '+3V3', 'GND', pcb=(MX + 4.5, MY + 7.0, 0, 'F'), desc='VDD (24)')
passive('C7', 'C', '100nF', '+3V3', 'GND', pcb=(MX + 8.5, MY - 4.0, 90, 'F'), desc='VDDIO2 (36)')
passive('C8', 'C', '100nF', '+3V3', 'GND', pcb=(MX - 7.5, MY - 5.75, 90, 'F'), desc='VBAT (1)')
passive('C9', 'C', '4.7uF', '+3V3', 'GND', pcb=(MX + 5.5, MY - 9.0, 0, 'F'), desc='3V3 – bufor przy MCU')
passive('C10', 'C', '100nF', '+3V3', 'GND', pcb=(MX - 7.25, MY + 5.0, 0, 'F'), desc='VDDA (9)')
passive('C11', 'C', '1uF', '+3V3', 'GND', pcb=(MX - 7.25, MY + 7.5, 0, 'F'), desc='VDDA (9)')
passive('C12', 'C', '100nF', 'NRST', 'GND', pcb=(MX - 9.0, MY - 0.75, 90, 'F'), desc='NRST')
part('Y1', 'Device:Crystal', '8MHz', 'Crystal:Crystal_SMD_5032-2Pin_5.0x3.2mm_HandSoldering',
     {'1': 'OSC_IN', '2': 'OSC_OUT'}, pcb=(MX - 14.5, MY - 5.0, 0, 'F'),
     bom=dict(mfr='Abracon', mpn='ABM3-8.000MHZ-D2Y-T', tme='ABM3-8.000MHZ-D2Y', pkg='5032 2-pad'),
     desc='kwarc 8 MHz, CL 18 pF (opcjonalny – USB działa z HSI48+CRS)')
passive('C13', 'C', '27pF', 'OSC_IN', 'GND', pcb=(MX - 17.1, MY - 8.5, 0, 'F'), desc='kwarc')
passive('C14', 'C', '27pF', 'OSC_OUT', 'GND', pcb=(MX - 11.9, MY - 8.5, 0, 'F'), desc='kwarc')
passive('R3', 'R', '10k', 'BOOT0', 'GND', pcb=(MX + 1.0, MY - 12.5, 0, 'F'), desc='BOOT0 → GND')
part('SW1', 'Switch:SW_Push', 'RESET', FP_BTN, {'1': 'NRST', '2': 'GND'}, pcb=(46.0, 60.0, 0, 'B'),
     bom=dict(mfr='C&K', mpn='PTS645SM43SMTR92 LFS', tme='PTS645SM43SMTR92', pkg='SMD 6×6 mm'),
     desc='reset (od spodu płytki)')
part('SW2', 'Switch:SW_Push', 'BOOT', FP_BTN, {'1': '+3V3', '2': 'BOOT0'}, pcb=(58.0, 60.0, 0, 'B'),
     bom=dict(mfr='C&K', mpn='PTS645SM43SMTR92 LFS', tme='PTS645SM43SMTR92', pkg='SMD 6×6 mm'),
     desc='BOOT0 – wejście do bootloadera DFU (od spodu płytki)')
part('J3', 'Connector_Generic:Conn_01x05', 'SWD', 'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical',
     {'1': '+3V3', '2': 'SWDIO', '3': 'SWCLK', '4': 'NRST', '5': 'GND'}, pcb=(72.0, 58.0, 90, 'F'),
     bom=dict(mfr='Connfly', mpn='DS1021-1*5SF11-B', tme='ZL201-05G', pkg='THT 2,54 mm'), dnp=True,
     desc='SWD do debugowania (opcjonalne, pady bez listwy)')

# ================================================================ OLED
part('J2', 'Connector_Generic:Conn_01x04', 'OLED I2C', 'Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical',
     {'1': 'GND', '2': 'OLED_VCC', '3': 'OLED_SCL', '4': 'OLED_SDA'}, pcb=(XC - 3.81, OLED_PIN_Y, 90, 'F'),
     bom=dict(mfr='Connfly', mpn='DS1023-1*4S21', tme='ZL262-4SG', pkg='THT 2,54 mm gniazdo'),
     desc='złącze modułu OLED 2,42": GND, VCC, SCL, SDA (jak nadruk modułu)')
part('JP1', 'Jumper:SolderJumper_3_Bridged12', 'OLED VCC', 'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm',
     {'1': '+3V3', '2': 'OLED_VCC', '3': '+5V'}, pcb=(XC - 8.0, OLED_PIN_Y + 4.55, 0, 'F'),
     desc='zasilanie OLED: 1–2 = 3,3 V (fabrycznie), 2–3 = 5 V')
passive('C15', 'C', '10uF', 'OLED_VCC', 'GND', pcb=(XC - 8.0, OLED_PIN_Y + 0.55, 90, 'F'), desc='zasilanie OLED')
passive('R4', 'R', '4.7k', '+3V3', 'OLED_SCL', pcb=(XC, OLED_PIN_Y + 4.55, 0, 'F'), desc='podciąganie SCL')
passive('R5', 'R', '4.7k', '+3V3', 'OLED_SDA', pcb=(XC + 4.0, OLED_PIN_Y + 4.55, 0, 'F'), desc='podciąganie SDA')

# ================================================================ enkodery i suwak
for i, (y, net) in enumerate(zip(ENC_Y, ['ENC1', 'ENC2'])):
    part('ENC%d' % (i + 1), 'Device:RotaryEncoder_Switch_MP', 'EC11', FP_ENC,
         {'A': net + '_A', 'B': net + '_B', 'C': 'GND', 'S1': net + '_SW', 'S2': 'GND', 'MP': 'GND'}, pcb=(ENC_X - 7.5, y - 2.5, 0, 'F'),
         bom=dict(mfr='ALPS', mpn='EC11E15244G1', tme='EC11E15244G1', pkg='THT'),
         desc='enkoder EC11 z przyciskiem (15 imp./30 zatrzasków)')
part('RV1', 'Device:R_Potentiometer_MountingPin', '10k', 'Potentiometer_THT:Potentiometer_Bourns_PTA4543_Single_Slide',
     {'1': 'GND', '2': 'SLIDER', '3': '+3V3', 'MP': 'GND'}, pcb=(SLIDER_X, YM + 29.25, 90, 'F'),
     bom=dict(mfr='Bourns', mpn='PTA4543-2015DPA103', tme='PTA45432015DPA10-0', pkg='THT',
              amazon='Bourns PTA4543-2015DPB103 (liniowy)'),
     desc='potencjometr suwakowy 45 mm, 10 kΩ (dół = GND, góra = 3,3 V)')
passive('C16', 'C', '100nF', 'SLIDER', 'GND', pcb=(MX - 4.0, MY + 8.5, 90, 'F'),
        desc='filtr wejścia ADC suwaka')

# ================================================================ klawisze
SW_BOM = dict(mfr='Kailh', mpn='CPG135001S30 (gniazdo) + CPG1353 (Choc V2)', tme='—',
              amazon='Kailh Choc hot-swap socket; Kailh Choc V2 switch', pkg='SMD (gniazdo)')
for i in range(8):
    row, col = divmod(i, 4)
    x = KEY_X[col]
    y = Y_TOP if row == 0 else Y_BOT
    rot = 180 if row == 0 else 0      # gniazda hotswap zawsze od strony ekranu
    part('S%d' % (i + 1), 'Switch:SW_Push', 'K%d' % (i + 1), FP_SW,
         {'1': 'K%d' % (i + 1), '2': 'GND'}, pcb=(x, y, rot, 'F'), bom=SW_BOM,
         desc='Kailh Choc V2 w gnieździe hotswap')

# ================================================================ LED (spód płytki)
part('U4', '74xGxx:74AHCT1G125', 'SN74AHCT1G125DBVR', 'Package_TO_SOT_SMD:SOT-23-5_HandSoldering',
     {'1': 'GND', '2': 'LED_DATA_3V3', '3': 'GND', '4': 'LED_DATA_5V', '5': '+5V'}, pcb=(75.0, 48.0, 0, 'F'),
     bom=dict(mfr='Texas Instruments', mpn='SN74AHCT1G125DBVR', tme='SN74AHCT1G125DBVR', pkg='SOT-23-5'),
     desc='konwerter poziomu 3,3 V → 5 V dla linii danych LED')
passive('C17', 'C', '100nF', '+5V', 'GND', pcb=(75.0, 52.0, 0, 'F'), desc='U4')
passive('R6', 'R', '330', 'LED_DATA_5V', 'LED_DIN', pcb=(79.5, 48.0, 90, 'F'),
        desc='rezystor szeregowy linii danych LED')
passive('C18', 'C', '10uF', '+5V', 'GND', pcb=(100.0, 40.0, 90, 'B'), desc='+5V – bufor łańcucha LED')

# Kolejność w łańcuchu: prawy bok w dół, dolna krawędź w lewo, lewy bok w górę, górna w prawo.
# (x, y, obrót LED, przesunięcie kondensatora dx, dy, obrót kondensatora). Obrót LED dobrany
# tak, by DIN był od strony poprzedniej diody (na spodzie obrót jest lustrzany);
# kondensator przy padzie VDD, z dala od otworów przełączników.
LED_POS = [
    (104.5, 28.0, 90, 0.5, 5.6, 0), (104.5, 65.0, 90, 0.5, 5.6, 0),
    (KEY_X[3], 87.5, 0, -6.2, 1.9, 0), (KEY_X[2], 87.5, 0, -6.2, 1.9, 0),
    (KEY_X[1], 87.5, 0, -6.2, 1.9, 0), (KEY_X[0], 87.5, 0, -6.2, 1.9, 0),
    (6.0, 72.0, 270, -0.5, -5.6, 0), (6.0, 21.0, 270, -0.5, -5.6, 0),
    (KEY_X[0], 5.5, 180, 6.2, -1.9, 0), (KEY_X[1], 5.5, 180, 6.2, -1.9, 0),
    (KEY_X[2], 5.5, 180, 6.2, -1.9, 0), (KEY_X[3], 5.5, 180, 6.2, -1.9, 0),
]
N_LED = len(LED_POS)
for i, (x, y, rot, cdx, cdy, crot) in enumerate(LED_POS):
    n = i + 1
    din = 'LED_DIN' if n == 1 else 'LED_D%d' % (n - 1)
    dout = 'LED_D%d' % n if n < N_LED else None
    part('L%d' % n, 'LED:WS2812B', 'WS2812B', FP_LED,
         {'1': '+5V', '2': dout, '3': 'GND', '4': din}, pcb=(x, y, rot, 'B'),
         bom=dict(mfr='Worldsemi', mpn='WS2812B-V5', tme='WS2812B-V5', pkg='5050 PLCC4',
                  amazon='WS2812B 5050 SMD chip (np. BTF-LIGHTING)'),
         desc='LED adresowalny RGB, spód płytki (podświetlenie blatu)')
    passive('C%d' % (18 + n), 'C', '100nF', '+5V', 'GND', pcb=(x + cdx, y + cdy, crot, 'B'),
            desc='odsprzęganie L%d' % n)

# ================================================================ mechanika
HOLES = [(6.5, 7.0), (106.5, 21.0), (6.0, 86.5), (104.5, 86.5)]
for i, (x, y) in enumerate(HOLES):
    part('H%d' % (i + 1), 'Mechanical:MountingHole', 'M3', FP_HOLE, {}, pcb=(x, y, 0, 'F'),
         bom=dict(mfr='—', mpn='—', tme='—', pkg='otwór Ø3,2'), desc='otwór montażowy M3')

# ---------------------------------------------------------------- szerokości ścieżek
NET_WIDTH = {'VBUS': 0.6, '+5V': 0.6, '+3V3': 0.3, 'GND': 0.3}
DEFAULT_WIDTH = 0.25


def nets():
    out = {}
    for p in parts:
        for pin, net in p['pins'].items():
            if net:
                out.setdefault(net, []).append((p['ref'], pin))
    return out


if __name__ == '__main__':
    for n, nodes in sorted(nets().items()):
        print('%-14s %s' % (n, ' '.join('%s.%s' % x for x in nodes)))
    print(len(parts), 'parts', len(nets()), 'nets')

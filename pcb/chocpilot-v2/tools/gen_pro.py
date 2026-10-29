"""Tworzy chocpilot-v2.kicad_pro z szablonu KiCad: reguły DRC i klasy sieci."""
import json
import os

TPL = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/kicad.kicad_pro'
OUT = os.path.join(os.path.dirname(__file__), '..', 'chocpilot-v2.kicad_pro')

d = json.load(open(TPL))
d['meta']['filename'] = 'chocpilot-v2.kicad_pro'
ds = d['board']['design_settings']
ds['rules'].update({
    'min_clearance': 0.2,
    'min_copper_edge_clearance': 0.3,
    'min_hole_clearance': 0.15,          # piny ustalające USB-C mają 0,19 mm do padów GND (footprint KiCad)
    'min_hole_to_hole': 0.25,
    'min_track_width': 0.2,
    'min_via_diameter': 0.6,
    'min_via_annular_width': 0.15,
    'min_through_hole_diameter': 0.3,
    'min_text_height': 0.8,
    'min_text_thickness': 0.12,
    'min_resolved_spokes': 1,         # małe pady GND mają też połączenie ścieżką
})
ds['track_widths'] = [0.0, 0.25, 0.3, 0.6]
ds['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.6, 'drill': 0.3}]
base = {
    'bus_width': 12, 'clearance': 0.2, 'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25,
    'diff_pair_width': 0.2, 'line_style': 0, 'microvia_diameter': 0.3, 'microvia_drill': 0.1,
    'name': 'Default', 'pcb_color': 'rgba(0, 0, 0, 0.000)', 'priority': 2147483647,
    'schematic_color': 'rgba(0, 0, 0, 0.000)', 'track_width': 0.25, 'tuning_profile': '',
    'via_diameter': 0.6, 'via_drill': 0.3, 'wire_width': 6}
base.update({'clearance': 0.2, 'track_width': 0.25, 'via_diameter': 0.6, 'via_drill': 0.3})


def cls(name, track, clearance=0.2):
    c = dict(base)
    c.update({'name': name, 'track_width': track, 'clearance': clearance, 'priority': 0})
    return c


d['net_settings']['classes'] = [base, cls('Power5V', 0.6, 0.2), cls('Power3V3', 0.3), cls('Ground', 0.3)]
d['net_settings']['netclass_patterns'] = [
    {'netclass': 'Power5V', 'pattern': 'VBUS'}, {'netclass': 'Power5V', 'pattern': '+5V'},
    {'netclass': 'Power3V3', 'pattern': '+3V3'}, {'netclass': 'Ground', 'pattern': 'GND'}]
json.dump(d, open(OUT, 'w'), indent=2)
print('zapisano', os.path.normpath(OUT))

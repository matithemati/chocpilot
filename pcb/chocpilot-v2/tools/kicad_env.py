"""Ścieżki instalacji KiCad 10 (macOS / Windows) dla generatorów w tools/."""
import os
import sys

if sys.platform == 'win32':
    _ROOT = os.environ.get('KICAD_ROOT', r'C:\Program Files\KiCad\10.0')
    SHARE = os.path.join(_ROOT, 'share', 'kicad') + os.sep
    CLI = os.path.join(_ROOT, 'bin', 'kicad-cli.exe')
    PYTHON = sys.executable              # router.py nie ma zależności – wystarczy Python KiCad
else:
    _ROOT = os.environ.get('KICAD_ROOT', '/Applications/KiCad/KiCad.app')
    SHARE = _ROOT + '/Contents/SharedSupport/'
    CLI = _ROOT + '/Contents/MacOS/kicad-cli'
    PYTHON = '/usr/local/bin/python3'

SYMDIR = SHARE + 'symbols' + os.sep
FPDIR = SHARE + 'footprints' + os.sep
TEMPLATE_PRO = os.path.join(SHARE, 'template', 'kicad.kicad_pro')

# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: aplikacja ChocPilot.
#   Windows: dist\ChocPilot.exe – jeden plik, bez konsoli, z metadanymi wersji (build_exe.ps1)
#   macOS:   dist/ChocPilot.app – pakiet aplikacji (build_macos.sh)
# Wersja pochodzi z chocpilot/__init__.py (jedno źródło dla aplikacji, pakietu i instalatora).

import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH)
VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"', (ROOT / "chocpilot" / "__init__.py").read_text("utf-8")
).group(1)
BUNDLE_ID = "com.chocpilot.app"  # = etykieta LaunchAgent autostartu (platform/macos.py)
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

hiddenimports = [*collect_submodules("chocpilot")]
if IS_WIN:
    hiddenimports += [
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "comtypes.stream",
        "win32timezone",
        *collect_submodules("pycaw"),
    ]
elif IS_MAC:
    hiddenimports += ["pynput.keyboard._darwin", "pynput.mouse._darwin"]

a = Analysis(
    ["chocpilot/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[("chocpilot/assets", "chocpilot/assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.Qt3DCore",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "pytest",
        "pytestqt",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)


def windows_version_info():
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )

    nums = tuple(int(n) for n in re.findall(r"\d+", VERSION)[:3]) + (0,)
    nums = (nums + (0, 0, 0, 0))[:4]
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=nums, prodvers=nums),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", "ChocPilot"),
                            StringStruct("FileDescription", "ChocPilot – macropad configurator"),
                            StringStruct("FileVersion", VERSION),
                            StringStruct("InternalName", "ChocPilot"),
                            StringStruct("OriginalFilename", "ChocPilot.exe"),
                            StringStruct("ProductName", "ChocPilot"),
                            StringStruct("ProductVersion", VERSION),
                            StringStruct("LegalCopyright", "MIT License"),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )


if IS_MAC:
    # Pakiet .app: katalog (onedir) – szybszy start niż jeden plik i poprawne podpisywanie.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="ChocPilot",
        console=False,
        debug=False,
        strip=False,
        upx=False,
        argv_emulation=False,
        target_arch=None,  # architektura Pythona, którym budujesz (arm64 na Apple Silicon)
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ChocPilot")
    app = BUNDLE(
        coll,
        name="ChocPilot.app",
        icon="chocpilot/assets/chocpilot.icns",
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        info_plist={
            "CFBundleName": "ChocPilot",
            "CFBundleDisplayName": "ChocPilot",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "12.0",
            "LSApplicationCategoryType": "public.app-category.utilities",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "MIT License",
            # Głośność, uśpienie ekranu i Terminal przez AppleScript (osascript).
            "NSAppleEventsUsageDescription": (
                "ChocPilot steruje głośnością, Terminalem i innymi programami na polecenie "
                "klawiszy macropada."
            ),
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="ChocPilot",
        icon="chocpilot/assets/chocpilot.ico",
        version=windows_version_info() if IS_WIN else None,
        console=False,
        debug=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
    )

"""Domyślne profile tworzone przy pierwszym uruchomieniu (zależne od systemu)."""

from __future__ import annotations

from .actions import make_action
from .config import KeyBinding, Profile
from .osinfo import OsName, current_os

# Programy klawiszy K1–K3 i proces OBS dla każdego systemu.
_APPS: dict[str, dict[str, str]] = {
    "windows": {
        "calc": "calc.exe",
        "notes": "notepad.exe",
        "files": "explorer.exe",
        "obs": "obs64.exe",
        "copy": "ctrl+c",
        "paste": "ctrl+v",
    },
    "macos": {
        "calc": "/System/Applications/Calculator.app",
        "notes": "/System/Applications/TextEdit.app",
        "files": "/System/Library/CoreServices/Finder.app",
        "obs": "OBS",
        "copy": "win+c",  # win = Cmd
        "paste": "win+v",
    },
}
_APPS["linux"] = {
    **_APPS["windows"],
    "calc": "gnome-calculator",
    "notes": "gedit",
    "files": "nautilus",
    "obs": "obs",
}


def default_profile(os_name: OsName | None = None) -> Profile:
    apps = _APPS[os_name or current_os()]
    # Górny rząd: programy i skróty; dolny: multimedia (przytrzymanie = poprzedni/następny
    # profil na skrajnych klawiszach).
    keys = {
        1: KeyBinding(label="Kalk", color="#2e7d32", tap=make_action("launch", path=apps["calc"])),
        2: KeyBinding(
            label="Notes", color="#1565c0", tap=make_action("launch", path=apps["notes"])
        ),
        3: KeyBinding(
            label="Kopiuj", color="#37474f", tap=make_action("hotkey", keys=apps["copy"])
        ),
        4: KeyBinding(
            label="Wklej", color="#37474f", tap=make_action("hotkey", keys=apps["paste"])
        ),
        5: KeyBinding(
            label="Głos -",
            color="#00838f",
            tap=make_action("media", key="vol_down"),
            hold=make_action("profile", mode="prev"),
        ),
        6: KeyBinding(label="Głos +", color="#00838f", tap=make_action("media", key="vol_up")),
        7: KeyBinding(label="Play", color="#c62828", tap=make_action("media", key="play_pause")),
        8: KeyBinding(
            label="Wycisz",
            color="#c62828",
            tap=make_action("media", key="mute"),
            hold=make_action("profile", mode="next"),
        ),
    }
    return Profile(name="Domyślny", keys=keys)


def stream_profile(os_name: OsName | None = None) -> Profile:
    """Przykład automatycznego przełączania: OBS (skróty F13–F20 do przypisania w OBS)."""
    keys = {
        i: KeyBinding(
            label=f"Scena {i}", color="#4527a0", tap=make_action("hotkey", keys=f"f{12 + i}")
        )
        for i in range(1, 5)
    }
    keys[5] = KeyBinding(label="Mic", color="#c62828", tap=make_action("hotkey", keys="f17"))
    keys[6] = KeyBinding(label="Kamera", color="#c62828", tap=make_action("hotkey", keys="f18"))
    keys[7] = KeyBinding(label="REC", color="#b71c1c", tap=make_action("hotkey", keys="f19"))
    keys[8] = KeyBinding(label="LIVE", color="#b71c1c", hold=make_action("hotkey", keys="f20"))
    obs = _APPS[os_name or current_os()]["obs"]
    return Profile(name="Stream", keys=keys, processes=[obs])


def default_profiles(os_name: OsName | None = None) -> list[Profile]:
    return [default_profile(os_name), stream_profile(os_name)]

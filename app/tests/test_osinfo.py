"""Różnice między systemami: nazwy procesów, katalogi, powłoki, profile, skróty, macOS."""

from __future__ import annotations

from pathlib import Path

import pytest

from chocpilot.core import osinfo
from chocpilot.core.actions import make_action
from chocpilot.core.config import Profile
from chocpilot.core.defaults import default_profiles
from chocpilot.platform import macos
from chocpilot.platform.base import PlatformError


def test_process_names() -> None:
    assert osinfo.same_process("obs64.exe", "OBS64")
    assert osinfo.same_process("Spotify.app", "spotify")
    assert not osinfo.same_process("obs64.exe", "obs")
    assert osinfo.process_name_from_path(r"C:\Program Files\App\app.exe", "windows") == "app.exe"
    assert osinfo.process_name_from_path("/Applications/Safari.app", "macos") == "Safari"
    assert osinfo.process_name_from_path("/Applications/Safari.app/", "macos") == "Safari"
    assert osinfo.normalize_process_entry("obs64", "windows") == "obs64.exe"
    assert osinfo.normalize_process_entry("game.bin", "windows") == "game.bin"
    assert osinfo.normalize_process_entry("Spotify.app", "macos") == "Spotify"
    assert osinfo.is_user_process("svchost.exe", "windows")
    assert not osinfo.is_user_process("System", "windows")
    assert osinfo.is_user_process("Safari", "macos")


def test_profile_matches_process_across_suffixes() -> None:
    profile = Profile(name="Gry", processes=["Game.exe", "Spotify"])
    assert profile.matches_process("game.exe")
    assert profile.matches_process("Spotify.app")
    assert not profile.matches_process("other.exe")


def test_config_dirs() -> None:
    home = Path("/home/u")
    assert (
        osinfo.config_base_dir("windows", {"APPDATA": r"C:\AD"}, home)
        == Path(r"C:\AD") / "ChocPilot"
    )
    assert (
        osinfo.config_base_dir("macos", {}, home)
        == home / "Library" / "Application Support" / "ChocPilot"
    )
    assert osinfo.config_base_dir("linux", {}, home) == home / ".config" / "chocpilot"
    assert osinfo.config_base_dir("linux", {"XDG_CONFIG_HOME": "/x"}, home) == Path("/x/chocpilot")


def test_shells() -> None:
    assert osinfo.default_shell("windows") == "cmd"
    assert osinfo.default_shell("macos") == "zsh"
    action = make_action("shell", command="ls", shell="zsh")
    assert action.shell == "zsh"  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        make_action("shell", command="ls", shell="fish")


def test_default_profiles_per_os() -> None:
    win, win_stream = default_profiles("windows")
    assert win.keys[1].tap.path == "calc.exe"  # type: ignore[union-attr]
    assert win.keys[3].tap.keys == "ctrl+c"  # type: ignore[union-attr]
    assert win_stream.processes == ["obs64.exe"]
    mac, mac_stream = default_profiles("macos")
    assert mac.keys[1].tap.path.endswith("Calculator.app")  # type: ignore[union-attr]
    assert mac.keys[3].tap.keys == "win+c"  # type: ignore[union-attr]
    assert mac_stream.processes == ["OBS"]


def test_hotkey_modifiers_on_macos() -> None:
    from PySide6.QtCore import Qt

    from chocpilot.gui.action_editor import modifier_names

    mods = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
    assert modifier_names(mods, "windows") == ["ctrl", "shift"]
    # na macOS Qt zgłasza Cmd jako ControlModifier, a Control jako MetaModifier
    assert modifier_names(mods, "macos") == ["shift", "win"]
    assert modifier_names(Qt.KeyboardModifier.MetaModifier, "macos") == ["ctrl"]


def test_macos_commands() -> None:
    assert macos.launch_argv("/Applications/Safari.app") == [
        "open",
        "-a",
        "/Applications/Safari.app",
    ]
    assert macos.launch_argv("Safari", "--x 1") == ["open", "-a", "Safari", "--args", "--x", "1"]
    assert macos.launch_argv("/usr/local/bin/tool", "-v") == ["/usr/local/bin/tool", "-v"]
    assert macos.open_url_argv("https://a.pl", "Firefox") == [
        "open",
        "-a",
        "Firefox",
        "https://a.pl",
    ]

    def which(name: str) -> str | None:
        return {"zsh": "/bin/zsh", "bash": "/bin/bash"}.get(name)

    assert macos.shell_argv("bash", "ls", which) == ["/bin/bash", "-c", "ls"]
    assert macos.shell_argv("cmd", "ls", which) == ["/bin/zsh", "-c", "ls"]
    with pytest.raises(PlatformError):
        macos.shell_argv("powershell", "ls", which)

    import plistlib

    plist = plistlib.loads(
        macos.launch_agent_plist(
            '"/Applications/ChocPilot.app/Contents/MacOS/ChocPilot" --minimized'
        )
    )
    assert plist["ProgramArguments"] == [
        "/Applications/ChocPilot.app/Contents/MacOS/ChocPilot",
        "--minimized",
    ]
    assert plist["RunAtLoad"] is True
    assert macos.parse_volume("37") == 37.0
    assert macos.parse_volume("missing value") is None

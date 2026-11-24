"""Konfiguracja ChocPilot: modele pydantic, migracje schematu, zapis atomowy, import/eksport."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from . import savers
from .actions import Action, ActionBase, make_action
from .gestures import Gesture
from .osinfo import config_base_dir, same_process
from .protocol import ENCODER_COUNT, KEY_COUNT, LED_SPEED_MAX, LED_SPEED_MIN, is_hex_color

log = logging.getLogger("chocpilot.config")

CURRENT_SCHEMA = 2
CONFIG_FILE = "config.json"


class Model(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)


# --------------------------------------------------------------------------- profile


class KeyBinding(Model):
    label: str = ""
    color: str = "#3c4a5c"
    # Ikona zamiast etykiety na ekranie LCD (gui/icon_library.py: builtin:… / emoji:… / file:…).
    icon: str = ""
    tap: Action | None = None
    hold: Action | None = None
    double_tap: Action | None = None

    def action_for(self, gesture: Gesture | str) -> ActionBase | None:
        name = str(gesture)
        if name not in ("tap", "hold", "double_tap"):
            return None
        action: ActionBase | None = getattr(self, name)
        return action

    def set_action(self, gesture: Gesture | str, action: ActionBase | None) -> None:
        setattr(self, str(gesture), action)

    def actions(self) -> list[ActionBase]:
        return [a for a in (self.tap, self.hold, self.double_tap) if a is not None]


def _empty_keys() -> dict[int, KeyBinding]:
    return {k: KeyBinding() for k in range(1, KEY_COUNT + 1)}


EncoderGesture = Literal["cw", "ccw", "press"]
ENCODER_GESTURES: tuple[EncoderGesture, ...] = ("cw", "ccw", "press")


class EncoderBinding(Model):
    """Pokrętło: obrót w prawo / w lewo (akcja × liczba zatrzasków) i przycisk."""

    label: str = ""
    cw: Action | None = None
    ccw: Action | None = None
    press: Action | None = None

    def action_for(self, gesture: EncoderGesture | str) -> ActionBase | None:
        if gesture not in ENCODER_GESTURES:
            return None
        action: ActionBase | None = getattr(self, gesture)
        return action

    def set_action(self, gesture: EncoderGesture | str, action: ActionBase | None) -> None:
        if gesture in ENCODER_GESTURES:
            setattr(self, gesture, action)

    def actions(self) -> list[ActionBase]:
        return [a for a in (self.cw, self.ccw, self.press) if a is not None]


SliderTarget = Literal["off", "system_volume", "app_volume"]


class SliderBinding(Model):
    """Suwak: położenie 0–100 % ustawia głośność systemu albo programu."""

    label: str = ""
    target: SliderTarget = "off"
    process: str = ""  # dla app_volume


def default_encoders() -> dict[int, EncoderBinding]:
    """Pokrętło 1 – głośność systemu i wyciszenie, 2 – przewijanie i odtwarzanie/pauza.
    Profile zapisane przed obsługą pokręteł dostają te przypisania przy wczytaniu."""
    return {
        1: EncoderBinding(
            label="Głośność",
            cw=make_action("media", key="vol_up"),
            ccw=make_action("media", key="vol_down"),
            press=make_action("media", key="mute"),
        ),
        2: EncoderBinding(
            label="Przewijanie",
            cw=make_action("scroll", direction="down"),
            ccw=make_action("scroll", direction="up"),
            press=make_action("media", key="play_pause"),
        ),
    }


class Profile(Model):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Profil"
    keys: dict[int, KeyBinding] = Field(default_factory=_empty_keys)
    encoders: dict[int, EncoderBinding] = Field(default_factory=default_encoders)
    slider: SliderBinding = Field(default_factory=lambda: SliderBinding())
    processes: list[str] = Field(default_factory=list)  # automatyczne przełączanie
    # Kolor podświetlenia LED, gdy profil jest aktywny (None = kolor z ustawień urządzenia).
    led_color: str | None = None

    @field_validator("led_color")
    @classmethod
    def _check_led_color(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not is_hex_color(value):
            raise ValueError("led_color must be #RRGGBB")
        return value.lower()

    @field_validator("keys")
    @classmethod
    def _fill_keys(cls, keys: dict[int, KeyBinding]) -> dict[int, KeyBinding]:
        filled = {k: keys.get(k, KeyBinding()) for k in range(1, KEY_COUNT + 1)}
        return filled

    @field_validator("encoders")
    @classmethod
    def _fill_encoders(cls, encoders: dict[int, EncoderBinding]) -> dict[int, EncoderBinding]:
        return {i: encoders.get(i, EncoderBinding()) for i in range(1, ENCODER_COUNT + 1)}

    @field_validator("processes")
    @classmethod
    def _normalize_processes(cls, items: list[str]) -> list[str]:
        return [p.strip() for p in items if p.strip()]

    def key(self, number: int) -> KeyBinding:
        return self.keys[number]

    def labels(self) -> list[str]:
        return [self.keys[k].label for k in range(1, KEY_COUNT + 1)]

    def icons(self) -> list[str]:
        return [self.keys[k].icon for k in range(1, KEY_COUNT + 1)]

    def action_for(self, key: int | None, gesture: Gesture) -> ActionBase | None:
        if key is None:
            return None
        return self.keys[key].action_for(gesture)

    def matches_process(self, exe: str) -> bool:
        return any(same_process(p, exe) for p in self.processes)


# --------------------------------------------------------------------------- ustawienia


LedMode = Literal["off", "status", "static", "breathe", "rainbow"]


class LedSettings(Model):
    """Podświetlenie LED – zapisywane też w pamięci urządzenia, działa offline."""

    mode: LedMode = "status"  # status = kolor połączenia (online turkus, offline bursztyn)
    color: str = "#00a0c0"
    brightness: int = Field(128, ge=0, le=255)
    speed: int = Field(5, ge=LED_SPEED_MIN, le=LED_SPEED_MAX)
    react: bool = True  # błysk diody przy naciśniętym klawiszu

    @field_validator("color")
    @classmethod
    def _check_color(cls, value: str) -> str:
        if not is_hex_color(value):
            raise ValueError("color must be #RRGGBB")
        return value.lower()


class DeviceSettings(Model):
    port: str = "auto"
    brightness: int = Field(128, ge=0, le=255)
    screensaver_s: int = Field(300, ge=0, le=65535)
    display_mode: Literal["grid", "profile"] = "grid"
    flip: bool = False
    debounce_ms: int = Field(8, ge=1, le=50)
    leds: LedSettings = Field(default_factory=LedSettings)
    # Animacja wygaszacza LCD ("off" = wygaszony ekran) i animacje zgłoszone przez firmware
    # (domyślnie wbudowane w aplikację – lista widoczna przed pierwszym połączeniem).
    saver: str = "off"
    savers_available: list[str] = Field(default_factory=lambda: list(savers.NAMES))


class GestureSettings(Model):
    hold_ms: int = Field(500, ge=100, le=5000)
    double_tap_ms: int = Field(300, ge=100, le=2000)
    hold_on_threshold: bool = False


FallbackSlot = Literal["1", "2", "3", "4", "5", "6", "7", "8"]


class FallbackEntry(Model):
    slot: FallbackSlot
    mods: list[str] = Field(default_factory=list)
    code: str | None = None
    media: str | None = None


class FallbackSettings(Model):
    from_profile: bool = True  # wyliczaj skróty z aktywnego profilu (hotkey/media)
    custom: list[FallbackEntry] = Field(default_factory=list)  # nadpisania


class AppSettings(Model):
    autostart: bool = False
    start_minimized: bool = False
    theme: Literal["system", "light", "dark"] = "system"
    language: Literal["pl", "en"] = "pl"
    flash_on_action: bool = True
    auto_switch: bool = True


class Settings(Model):
    device: DeviceSettings = Field(default_factory=lambda: DeviceSettings())
    gestures: GestureSettings = Field(default_factory=lambda: GestureSettings())
    fallback: FallbackSettings = Field(default_factory=lambda: FallbackSettings())
    app: AppSettings = Field(default_factory=lambda: AppSettings())


# --------------------------------------------------------------------------- Klipper

KlipperCommand = Literal[
    "gcode", "pause_resume", "cancel", "estop", "firmware_restart", "next_printer", "exit"
]
KLIPPER_COMMANDS: dict[str, str] = {
    "gcode": "G-code / makro",
    "pause_resume": "Pauza / wznowienie",
    "cancel": "Anuluj wydruk",
    "estop": "Awaryjne zatrzymanie",
    "firmware_restart": "Restart firmware",
    "next_printer": "Następna drukarka",
    "exit": "Wyjście z trybu Klipper",
}
# Parametry pokrętła E2 (naciśnięcie przełącza kolejny).
KlipperParam = Literal["nozzle", "bed", "speed", "flow", "fan"]
KLIPPER_PARAMS: dict[str, str] = {
    "nozzle": "Temperatura dyszy",
    "bed": "Temperatura stołu",
    "speed": "Prędkość (M220)",
    "flow": "Przepływ (M221)",
    "fan": "Wentylator",
}


_DEFAULT_PARAMS: tuple[KlipperParam, ...] = ("nozzle", "bed", "speed", "flow", "fan")


class KlipperPrinter(Model):
    name: str = "Drukarka"
    url: str = ""  # adres Moonrakera, np. http://voron.local albo 192.168.1.20:7125
    api_key: str = ""  # opcjonalny klucz API Moonrakera


class KlipperKey(Model):
    label: str = ""
    command: KlipperCommand = "gcode"
    gcode: str = ""  # dla command="gcode": G-code albo makro, wiele linii dozwolone
    hold: bool = False  # wymaga przytrzymania (anulowanie, awaryjne zatrzymanie…)
    icon: str = ""  # ikona zamiast etykiety na LCD (jak KeyBinding.icon)


def default_klipper_keys() -> dict[int, KlipperKey]:
    return {
        1: KlipperKey(label="Home", gcode="G28", icon="builtin:home"),
        2: KlipperKey(label="Pauza", command="pause_resume", icon="builtin:play-pause"),
        3: KlipperKey(label="PLA", gcode="M140 S60\nM104 S200", icon="builtin:fire"),
        4: KlipperKey(label="Stygnij", gcode="TURN_OFF_HEATERS", icon="builtin:fan"),
        5: KlipperKey(label="Silniki", gcode="M84", icon="builtin:power"),
        6: KlipperKey(label="Anuluj", command="cancel", hold=True, icon="builtin:x"),
        7: KlipperKey(label="Drukarka", command="next_printer", icon="builtin:printer"),
        8: KlipperKey(label="STOP", command="estop", hold=True, icon="builtin:warning"),
    }


class KlipperSettings(Model):
    """Tryb Klipper: sterowanie drukarkami 3D przez Moonraker z klawiszy, pokręteł i suwaka."""

    printers: list[KlipperPrinter] = Field(default_factory=list)
    active_printer: int = 0
    # Przełączanie trybu: przytrzymanie przycisku pokrętła (krótkie naciśnięcie działa jak zwykle)
    # albo tylko akcja „Klipper” przypisana do klawisza.
    toggle: Literal["e1_hold", "e2_hold", "action"] = "e2_hold"
    toggle_ms: int = Field(800, ge=300, le=3000)
    hold_ms: int = Field(800, ge=300, le=3000)  # klawisze z „Przytrzymanie”
    keys: dict[int, KlipperKey] = Field(default_factory=default_klipper_keys)
    jog_xy: float = Field(1.0, gt=0, le=100)  # mm na zatrzask E1
    jog_z: float = Field(0.1, gt=0, le=50)
    jog_feed: int = Field(6000, ge=60, le=60000)  # mm/min
    babystep: float = Field(0.01, gt=0, le=1)  # mm na zatrzask E1 w trakcie wydruku
    params: list[KlipperParam] = Field(default_factory=lambda: list(_DEFAULT_PARAMS))
    temp_step: int = Field(5, ge=1, le=50)
    slider: Literal["off", "fan", "speed"] = "fan"
    poll_s: float = Field(2.0, ge=0.5, le=30)

    @field_validator("keys")
    @classmethod
    def _fill_keys(cls, keys: dict[int, KlipperKey]) -> dict[int, KlipperKey]:
        defaults = default_klipper_keys()
        return {k: keys.get(k, defaults[k]) for k in range(1, KEY_COUNT + 1)}

    @field_validator("params")
    @classmethod
    def _dedupe_params(cls, params: list[str]) -> list[str]:
        seen: list[str] = []
        for p in params:
            if p not in seen:
                seen.append(p)
        return seen or ["nozzle"]


class Config(Model):
    schema_version: int = CURRENT_SCHEMA
    settings: Settings = Field(default_factory=lambda: Settings())
    klipper: KlipperSettings = Field(default_factory=lambda: KlipperSettings())
    profiles: list[Profile] = Field(default_factory=list)
    default_profile: str = ""

    def profile(self, name: str) -> Profile | None:
        for p in self.profiles:
            if p.name == name:
                return p
        return None

    def profile_names(self) -> list[str]:
        return [p.name for p in self.profiles]

    def unique_name(self, base: str) -> str:
        names = set(self.profile_names())
        if base not in names:
            return base
        i = 2
        while f"{base} ({i})" in names:
            i += 1
        return f"{base} ({i})"

    def ensure_valid(self) -> None:
        """Gwarantuje co najmniej jeden profil i poprawny profil domyślny."""
        if not self.profiles:
            from .defaults import default_profiles

            self.profiles = default_profiles()
        if self.profile(self.default_profile) is None:
            self.default_profile = self.profiles[0].name


# --------------------------------------------------------------------------- migracje


def _migrate_1_to_2(data: dict[str, Any]) -> dict[str, Any]:
    """Schemat 1: klawisze jako lista, progi gestów w korzeniu, `auto_processes`."""
    settings = data.setdefault("settings", {})
    gestures = settings.setdefault("gestures", {})
    for old, new in (("hold_ms", "hold_ms"), ("double_tap_ms", "double_tap_ms")):
        if old in data:
            gestures[new] = data.pop(old)
    for profile in data.get("profiles", []):
        keys = profile.get("keys")
        if isinstance(keys, list):
            profile["keys"] = {str(i + 1): k for i, k in enumerate(keys) if k is not None}
        if "auto_processes" in profile:
            profile["processes"] = profile.pop("auto_processes")
    data.pop("version", None)
    data["schema_version"] = 2
    return data


MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {1: _migrate_1_to_2}


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    version = data.get("schema_version", data.get("version", CURRENT_SCHEMA))
    if not isinstance(version, int):
        raise ValueError("bad schema_version")
    if version > CURRENT_SCHEMA:
        log.warning("Konfiguracja z nowszej wersji (%s) – wczytuję w miarę możliwości", version)
        return data
    while version < CURRENT_SCHEMA:
        step = MIGRATIONS.get(version)
        if step is None:
            raise ValueError(f"brak migracji ze schematu {version}")
        log.info("Migracja konfiguracji: %s → %s", version, version + 1)
        data = step(data)
        version = data["schema_version"]
    return data


# --------------------------------------------------------------------------- zapis i odczyt


def default_config_dir() -> Path:
    return config_base_dir()


def atomic_write(path: Path, text: str) -> None:
    """Zapis przez plik tymczasowy i os.replace (brak uszkodzonego pliku przy awarii)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class ConfigStore:
    """Plik config.json z kopią zapasową poprzedniej wersji (config.json.bak)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_dir() / CONFIG_FILE
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        self._lock = threading.Lock()

    def load(self) -> Config:
        if not self.path.exists():
            log.info("Brak konfiguracji – tworzę domyślną (%s)", self.path)
            config = Config()
            config.ensure_valid()
            return config
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("object expected")
            config = Config.model_validate(migrate(data))
        except (OSError, ValueError, ValidationError) as exc:
            log.error("Uszkodzona konfiguracja (%s) – wczytuję kopię zapasową", exc)
            config = self._load_backup()
            broken = self.path.with_suffix(".broken.json")
            try:
                shutil.copy2(self.path, broken)
            except OSError:
                pass
        config.ensure_valid()
        return config

    def _load_backup(self) -> Config:
        try:
            data = json.loads(self.backup_path.read_text(encoding="utf-8"))
            return Config.model_validate(migrate(data))
        except (OSError, ValueError, ValidationError):
            return Config()

    def save(self, config: Config) -> None:
        with self._lock:
            text = config.model_dump_json(indent=2)
            if self.path.exists():
                try:
                    shutil.copy2(self.path, self.backup_path)
                except OSError as exc:
                    log.warning("Nie udało się zrobić kopii zapasowej: %s", exc)
            atomic_write(self.path, text)


# --------------------------------------------------------------------------- import/eksport

EXPORT_FORMAT = "chocpilot-profile"


def export_profile(profile: Profile, path: Path) -> None:
    payload = {
        "format": EXPORT_FORMAT,
        "schema_version": CURRENT_SCHEMA,
        "profile": profile.model_dump(mode="json"),
    }
    atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))


def import_profile(path: Path, config: Config) -> Profile:
    """Wczytuje profil z pliku; przy konflikcie nazwy dodaje sufiks. Nie dodaje do config."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("format") == EXPORT_FORMAT:
        raw = data["profile"]
        version = data.get("schema_version", CURRENT_SCHEMA)
        if version < CURRENT_SCHEMA:
            raw = migrate({"schema_version": version, "profiles": [raw]})["profiles"][0]
    elif isinstance(data, dict) and "keys" in data:
        raw = data  # sam profil
    else:
        raise ValueError("To nie jest plik profilu ChocPilot")
    profile = Profile.model_validate(raw)
    profile.id = uuid.uuid4().hex[:12]
    profile.name = config.unique_name(profile.name)
    return profile


def duplicate_profile(profile: Profile, config: Config) -> Profile:
    copy = Profile.model_validate(profile.model_dump(mode="json"))
    copy.id = uuid.uuid4().hex[:12]
    copy.name = config.unique_name(f"{profile.name} – kopia")
    return copy


__all__ = [
    "CURRENT_SCHEMA",
    "ENCODER_GESTURES",
    "AppSettings",
    "Config",
    "ConfigStore",
    "DeviceSettings",
    "EncoderBinding",
    "FallbackEntry",
    "FallbackSettings",
    "GestureSettings",
    "KeyBinding",
    "Profile",
    "Settings",
    "SliderBinding",
    "atomic_write",
    "default_config_dir",
    "default_encoders",
    "duplicate_profile",
    "export_profile",
    "import_profile",
    "migrate",
]

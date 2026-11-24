"""Tryb Klipper: klient Moonraker, kontroler trybu, przełączanie w kontrolerze, strona w GUI."""

from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any

import pytest

from chocpilot.core import protocol
from chocpilot.core.actions import make_action
from chocpilot.core.config import Config, EncoderBinding, KlipperPrinter, KlipperSettings, Profile
from chocpilot.core.engine import Controller
from chocpilot.core.klipper import KlipperMode, KlipperWorker
from chocpilot.core.moonraker import MoonrakerClient, MoonrakerError, PrinterStatus, normalize_url
from chocpilot.core.protocol import DeviceInfo
from chocpilot.core.transport import ConnectionState
from tests.conftest import FakePlatform, FakeTransport, ManualClock

# --------------------------------------------------------------------------- Moonraker


class FakeHttp:
    def __init__(self, responses: dict[str, tuple[int, Any]]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float
    ) -> tuple[int, bytes]:
        self.requests.append((method, url, headers))
        path = urllib.parse.urlsplit(url).path
        if path not in self.responses:
            raise OSError("connection refused")
        status, data = self.responses[path]
        return status, json.dumps(data).encode()


READY = {"result": {"state": "ready", "state_message": "Printer is ready"}}
OBJECTS = {
    "result": {
        "status": {
            "print_stats": {"state": "printing", "filename": "benchy.gcode"},
            "display_status": {"progress": 0.42},
            "extruder": {"temperature": 214.6, "target": 215.0},
            "heater_bed": {"temperature": 59.8, "target": 60.0},
            "gcode_move": {
                "speed_factor": 1.1,
                "extrude_factor": 0.98,
                "homing_origin": [0, 0, 0.05, 0],
            },
            "toolhead": {"homed_axes": "xyz"},
            "fan": {"speed": 0.5},
        }
    }
}


def test_moonraker_status_and_commands() -> None:
    http = FakeHttp(
        {
            "/printer/info": (200, READY),
            "/printer/objects/query": (200, OBJECTS),
            "/printer/gcode/script": (200, {"result": "ok"}),
        }
    )
    client = MoonrakerClient("voron.local:7125/", api_key="secret", transport=http)
    assert client.url == "http://voron.local:7125"
    st = client.status()
    assert st.online and st.printing and st.busy
    assert (st.progress, st.nozzle_target, st.bed, st.homed) == (0.42, 215.0, 59.8, "xyz")
    assert st.speed_factor == pytest.approx(1.1) and st.z_offset == pytest.approx(0.05)
    client.gcode("G91\nG1 X+1.000 F6000\nG90")
    method, url, headers = http.requests[-1]
    assert method == "POST" and headers["X-Api-Key"] == "secret"
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert query["script"] == ["G91\nG1 X+1.000 F6000\nG90"]


def test_moonraker_klippy_down_and_errors() -> None:
    down = FakeHttp(
        {"/printer/info": (200, {"result": {"state": "shutdown", "state_message": "MCU lost\nx"}})}
    )
    st = MoonrakerClient("p", transport=down).status()
    assert st.online and st.state == "shutdown" and st.message == "MCU lost"

    denied = FakeHttp({"/printer/info": (401, {"error": {"message": "Unauthorized"}})})
    with pytest.raises(MoonrakerError, match="klucz API"):
        MoonrakerClient("p", transport=denied).status()
    with pytest.raises(MoonrakerError, match="brak połączenia"):
        MoonrakerClient("p", transport=FakeHttp({})).status()
    bad = FakeHttp({"/printer/gcode/script": (400, {"error": {"message": "Must home axis first"}})})
    with pytest.raises(MoonrakerError, match="Must home"):
        MoonrakerClient("p", transport=bad).gcode("G1 X10")
    assert normalize_url(" https://x/ ") == "https://x"


# --------------------------------------------------------------------------- tryb Klipper


class FakeClient:
    def __init__(self, status: PrinterStatus) -> None:
        self.status_value = status
        self.calls: list[tuple[str, ...]] = []
        self.fail: str | None = None

    def status(self) -> PrinterStatus:
        return self.status_value

    def _call(self, *call: str) -> None:
        if self.fail:
            raise MoonrakerError(self.fail)
        self.calls.append(call)

    def gcode(self, script: str, timeout: float = 120.0) -> None:
        self._call("gcode", script)

    def pause(self) -> None:
        self._call("pause")

    def resume(self) -> None:
        self._call("resume")

    def cancel(self) -> None:
        self._call("cancel")

    def emergency_stop(self) -> None:
        self._call("estop")

    def firmware_restart(self) -> None:
        self._call("restart")


class Host:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.changes = 0
        self.restored = 0

    def send(self, message: dict[str, Any], with_id: bool = False) -> bool:
        self.sent.append(message)
        return True

    def call_soon(self, fn: Any) -> None:
        fn()

    def klipper_changed(self) -> None:
        self.changes += 1

    def restore_display(self) -> None:
        self.restored += 1

    def sync_icons(self, icons: list[str]) -> None:
        self.icons = icons

    def texts(self) -> list[str]:
        return [m["line1"] for m in self.sent if m.get("mode") == "text"]


IDLE = PrinterStatus(online=True, state="standby", nozzle=25, bed=24, homed="xyz")


def make_mode(
    status: PrinterStatus = IDLE, printers: int = 1
) -> tuple[KlipperMode, FakeClient, Host, KlipperSettings, ManualClock]:
    settings = KlipperSettings(
        printers=[KlipperPrinter(name=f"P{i + 1}", url=f"p{i + 1}") for i in range(printers)]
    )
    client = FakeClient(status)
    host = Host()
    clock = ManualClock()
    mode = KlipperMode(
        lambda: settings, host, clock, lambda url, key: client, KlipperWorker(sync=True)
    )
    return mode, client, host, settings, clock


def test_enter_needs_printer_and_shows_status() -> None:
    mode, client, host, settings, _ = make_mode(printers=0)
    mode.enter()
    assert not mode.active and "Klipper" in host.texts()

    mode, client, host, settings, _ = make_mode(
        PrinterStatus(online=True, state="printing", progress=0.5, nozzle=215, bed=60)
    )
    mode.enter()
    assert mode.active and host.changes >= 1
    grid = [m for m in host.sent if m.get("mode") == "grid"][-1]
    assert host.icons[1] == "builtin:pause"  # drukuje – ikona pokazuje, że klawisz wstrzyma
    assert host.icons[0] == "builtin:home"
    assert grid["title"] == "P1 50% 215/60"
    assert grid["labels"][0] == "Home" and grid["labels"][1] == "Pauza"
    mode.exit()
    assert not mode.active and host.restored == 1


def test_keys_run_commands_and_hold_protection() -> None:
    mode, client, host, settings, clock = make_mode()
    mode.enter()
    mode.on_key(1, True, clock())  # Home – od razu
    assert client.calls[-1] == ("gcode", "G28")
    mode.on_key(1, False, clock())

    mode.on_key(8, True, clock())  # STOP wymaga przytrzymania
    mode.on_key(8, False, clock() + 0.2)
    assert ("estop",) not in client.calls
    assert any("Przytrzymaj" in t for t in host.texts())
    mode.on_key(8, True, clock())
    clock.advance(0.9)
    mode.tick(clock())
    assert client.calls[-1] == ("estop",)

    mode.on_key(2, True, clock())  # pauza bez wydruku
    assert "Nie drukuje" in host.texts()
    mode.status = PrinterStatus(online=True, state="printing")
    mode.on_key(2, True, clock())
    mode.status = PrinterStatus(online=True, state="paused")
    mode.on_key(2, True, clock())
    assert client.calls[-2:] == [("pause",), ("resume",)]


def test_encoders_jog_babystep_and_adjust() -> None:
    mode, client, host, settings, _ = make_mode(
        PrinterStatus(online=True, state="standby", homed="")
    )
    mode.enter()
    mode.on_encoder(1, 2)
    assert "Najpierw Home" in host.texts() and client.calls == []
    client.status_value = mode.status = IDLE
    mode.on_encoder(1, 2)
    assert client.calls[-1] == ("gcode", "G91\nG1 X+2.000 F6000\nG90")
    mode.on_encoder_press(1)
    mode.on_encoder_press(1)  # Z
    mode.on_encoder(1, -3)
    assert client.calls[-1] == ("gcode", "G91\nG1 Z-0.300 F6000\nG90")

    client.status_value = mode.status = PrinterStatus(
        online=True, state="printing", z_offset=0.1, homed="xyz"
    )
    mode.on_encoder(1, 2)  # w trakcie wydruku – Z offset zamiast ruchu
    assert client.calls[-1] == ("gcode", "SET_GCODE_OFFSET Z_ADJUST=+0.020 MOVE=1")

    client.status_value = mode.status = PrinterStatus(
        online=True, state="standby", nozzle_target=200, homed="xyz"
    )
    mode.on_encoder(2, 2)  # dysza +2 × 5 °C
    assert client.calls[-1] == ("gcode", "M104 S210")
    mode.on_encoder(2, 1)  # nastawa jeszcze niepotwierdzona – liczy od 210
    assert client.calls[-1] == ("gcode", "M104 S215")
    mode.on_encoder_press(2)  # stół
    mode.on_encoder(2, -100)
    assert client.calls[-1] == ("gcode", "M140 S0")  # ograniczenie do zakresu

    mode.on_slider(50)
    assert client.calls[-1] == ("gcode", "M106 S128")
    settings.slider = "speed"
    mode.on_slider(70)
    assert client.calls[-1] == ("gcode", "M220 S120")


def test_next_printer_and_errors() -> None:
    mode, client, host, settings, _ = make_mode(printers=2)
    mode.enter()
    mode.on_key(7, True, 0.0)  # następna drukarka
    assert settings.active_printer == 1
    client.fail = "Must home axis first"
    mode.on_key(1, True, 0.0)
    assert "Blad Klipper" in host.texts()


# --------------------------------------------------------------------------- kontroler


def make_controller(sync_executor) -> tuple[Controller, FakeTransport, FakeClient, ManualClock]:
    config = Config(profiles=[Profile(name="Domyślny")])
    config.ensure_valid()
    config.klipper.printers = [KlipperPrinter(name="Voron", url="voron")]
    clock = ManualClock()
    transport = FakeTransport()
    controller = Controller(config, transport, FakePlatform(), executor=sync_executor, clock=clock)
    client = FakeClient(IDLE)
    controller.klipper = KlipperMode(
        lambda: config.klipper, controller, clock, lambda u, k: client, KlipperWorker(sync=True)
    )
    transport.connect()
    controller.handle_state(
        ConnectionState.CONNECTED,
        DeviceInfo("chocpilot", "1.1.0", "chocpilot", encoder=True),
        "COM9",
    )
    return controller, transport, client, clock


def test_encoder_hold_toggles_mode_short_press_keeps_action(sync_executor) -> None:
    controller, transport, client, clock = make_controller(sync_executor)
    platform = controller.platform
    # krótkie naciśnięcie E2 – zwykła akcja profilu (odtwarzaj/pauza) po puszczeniu
    controller.handle_message({"type": "encoder_key", "index": 2, "action": "down", "t": 0})
    assert ("media", "play_pause") not in platform.calls
    controller.handle_message({"type": "encoder_key", "index": 2, "action": "up", "t": 1})
    assert ("media", "play_pause") in platform.calls
    assert not controller.klipper.active

    # przytrzymanie E2 – tryb Klipper, puszczenie nie wykonuje akcji
    controller.handle_message({"type": "encoder_key", "index": 2, "action": "down", "t": 2})
    clock.advance(0.9)
    controller.tick()
    assert controller.klipper.active
    calls = len(platform.calls)
    controller.handle_message({"type": "encoder_key", "index": 2, "action": "up", "t": 3})
    assert len(platform.calls) == calls

    # w trybie Klipper klawisze i pokrętła sterują drukarką, nie profilem
    transport.sent.clear()
    controller.handle_message({"type": "key", "key": 1, "action": "down", "t": 4})
    assert client.calls[-1] == ("gcode", "G28")
    controller.handle_message({"type": "encoder", "index": 1, "delta": 1, "t": 5})
    assert client.calls[-1] == ("gcode", "G91\nG1 X+1.000 F6000\nG90")
    # zmiana profilu nie zasłania ekranu Klippera
    controller.send_profile_state()
    assert transport.of_type("display")[-1]["title"].startswith("Voron")

    controller.handle_message({"type": "encoder_key", "index": 2, "action": "down", "t": 6})
    clock.advance(0.9)
    controller.tick()
    assert not controller.klipper.active
    assert transport.of_type("display")[-1]["title"] == "Domyslny"  # ekran: ASCII


def test_klipper_action_and_e1_press_in_mode(sync_executor) -> None:
    controller, transport, client, clock = make_controller(sync_executor)
    controller.config.klipper.toggle = "action"
    controller.config.profiles[0].encoders[1] = EncoderBinding(press=make_action("klipper"))
    controller.handle_message({"type": "encoder_key", "index": 1, "action": "down", "t": 0})
    assert controller.klipper.active
    controller.handle_message({"type": "encoder_key", "index": 1, "action": "down", "t": 1})
    assert controller.klipper.axis == 1  # w trybie: E1 zmienia oś
    controller.klipper_mode("exit")
    assert not controller.klipper.active
    assert make_action("klipper", mode="enter").summary() == "Włącz tryb Klipper"
    assert len("Voron 100% 215/60") <= protocol.TITLE_CHARS


# --------------------------------------------------------------------------- GUI


def test_klipper_page_edits_settings(qtbot) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from chocpilot.gui.klipper_page import KlipperPage, status_text

    settings = KlipperSettings()
    page = KlipperPage(settings)
    qtbot.addWidget(page)
    changes: list[bool] = []
    page.changed.connect(lambda: changes.append(True))
    page._add_printer()
    page.p_url.setText("192.168.1.20:7125")
    page.p_name.setText("Ender")
    page._printer_edited()
    assert settings.printers[0].url == "192.168.1.20:7125" and settings.printers[0].name == "Ender"
    name, command, gcode, hold = page.key_rows[3]
    command.setCurrentIndex(command.findData("firmware_restart"))
    assert settings.keys[3].command == "firmware_restart" and not gcode.isEnabled()
    page.param_checks["fan"].setChecked(False)
    assert "fan" not in settings.params
    assert page.key_icons[1] == "builtin:home"  # domyślne ikony klawiszy Klippera
    page.key_icons[1] = "builtin:crosshair"
    page._show_icon(1)
    page._edited()
    assert settings.keys[1].icon == "builtin:crosshair"
    page.toggle_combo.setCurrentIndex(page.toggle_combo.findData("e1_hold"))
    assert settings.toggle == "e1_hold" and changes

    tested: list[KlipperPrinter] = []
    page.testRequested.connect(tested.append)
    page._test()
    assert tested[0].name == "Ender"
    page._test_done(PrinterStatus(online=False, message="brak połączenia"))
    assert "brak połączenia" in page.status_label.text()
    assert "drukuje" in status_text(PrinterStatus(online=True, state="printing", progress=0.3))

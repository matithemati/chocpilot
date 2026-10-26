"""Testy kontrolera: wiadomości urządzenia → gesty → akcje, stan wysyłany do urządzenia."""

from __future__ import annotations

from chocpilot.core import protocol
from chocpilot.core.actions import make_action
from chocpilot.core.config import Config, FallbackEntry, Profile
from chocpilot.core.defaults import default_profiles
from chocpilot.core.engine import Controller, ControllerListener
from chocpilot.core.fallback import compute_fallback
from chocpilot.core.protocol import DeviceInfo
from chocpilot.core.transport import ConnectionState
from tests.conftest import FakePlatform, FakeTransport, ManualClock


def make_controller(
    platform: FakePlatform, clock: ManualClock, sync_executor
) -> tuple[Controller, FakeTransport]:
    config = Config(profiles=[*default_profiles(), Profile(name="Warstwa")])
    config.ensure_valid()
    transport = FakeTransport()
    controller = Controller(config, transport, platform, executor=sync_executor, clock=clock)
    transport.connect()
    controller.handle_state(
        ConnectionState.CONNECTED, DeviceInfo("chocpilot", "1.0.0", "promicro"), "COM7"
    )
    return controller, transport


def key(controller: Controller, clock: ManualClock, k: int, down: bool) -> None:
    controller.handle_message({"type": "key", "key": k, "action": "down" if down else "up", "t": 0})


def tap(controller: Controller, clock: ManualClock, k: int, hold_s: float = 0.05) -> None:
    key(controller, clock, k, True)
    clock.advance(hold_s)
    key(controller, clock, k, False)


def test_connect_pushes_state(platform, clock, sync_executor) -> None:
    _, transport = make_controller(platform, clock, sync_executor)
    kinds = [m["type"] for m in transport.sent]
    assert kinds == ["settings", "display", "set_fallback"]
    display = transport.of_type("display")[0]
    assert display["mode"] == "grid"
    assert display["title"] == "Domyslny"
    assert display["labels"][0] == "Kalk"
    assert "id" in transport.of_type("settings")[0]


def test_connect_pro_micro_splits_fallback(platform, clock, sync_executor) -> None:
    config = Config(profiles=default_profiles())
    config.ensure_valid()
    config.settings.fallback.custom = [
        FallbackEntry(slot=str(i), mods=["ctrl", "shift", "alt"], code="f12") for i in range(1, 9)
    ]
    transport = FakeTransport()
    controller = Controller(config, transport, platform, executor=sync_executor, clock=clock)
    transport.connect()
    controller.handle_state(
        ConnectionState.CONNECTED,
        DeviceInfo("chocpilot", "1.0.4", "promicro", max_line=272),
        "COM4",
    )
    parts = transport.of_type("set_fallback")
    assert len(parts) > 1 and parts[0]["replace"] is True
    for part in parts:
        assert len(protocol.encode(part)) <= 272


def test_tap_executes_and_flashes(platform, clock, sync_executor) -> None:
    controller, transport = make_controller(platform, clock, sync_executor)
    transport.sent.clear()
    tap(controller, clock, 3)
    assert platform.calls == [("hotkey", ("ctrl", "c"))]
    assert transport.of_type("flash") == [{"type": "flash", "text": "Kopiuj", "ms": 800, "key": 3}]


def test_paused_skips_actions(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    controller.paused = True
    tap(controller, clock, 5)
    assert platform.calls == []


def test_profile_switch_sends_display_and_fallback(platform, clock, sync_executor) -> None:
    controller, transport = make_controller(platform, clock, sync_executor)
    transport.sent.clear()
    tap(controller, clock, 8, hold_s=0.6)  # przytrzymanie K8: następny profil
    assert controller.profiles.active.name == "Stream"
    kinds = [m["type"] for m in transport.sent]
    assert kinds == ["display", "flash", "set_fallback"]
    assert transport.of_type("display")[0]["title"] == "Stream"


def test_layer_key(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    profile = controller.profiles.active
    profile.keys[4].tap = make_action("layer", profile="Warstwa")
    layer = controller.config.profile("Warstwa")
    assert layer is not None
    layer.keys[1].tap = make_action("hotkey", keys="f13")
    key(controller, clock, 4, True)
    assert controller.profiles.effective.name == "Warstwa"
    tap(controller, clock, 1)
    key(controller, clock, 4, False)
    assert controller.profiles.effective.name == "Domyślny"
    assert platform.calls == [("hotkey", ("f13",))]


def test_double_tap_through_tick(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    profile = controller.profiles.active
    profile.keys[3].double_tap = make_action("hotkey", keys="ctrl+x")
    tap(controller, clock, 3)
    assert platform.calls == []
    clock.advance(0.5)
    controller.tick()
    assert platform.calls == [("hotkey", ("ctrl", "c"))]
    tap(controller, clock, 3)
    clock.advance(0.1)
    tap(controller, clock, 3)
    assert platform.calls[-1] == ("hotkey", ("ctrl", "x"))


def test_ping_every_second(platform, clock, sync_executor) -> None:
    controller, transport = make_controller(platform, clock, sync_executor)
    transport.sent.clear()
    controller.tick()
    clock.advance(0.5)
    controller.tick()
    clock.advance(0.6)
    controller.tick()
    assert len(transport.of_type("ping")) == 2


def test_action_error_flashes(platform, clock, sync_executor) -> None:
    controller, transport = make_controller(platform, clock, sync_executor)
    controller.profiles.active.keys[2].tap = make_action("launch", path="")
    transport.sent.clear()
    tap(controller, clock, 2)
    assert transport.of_type("flash")[0]["text"] == "Blad!"


def test_listener_receives_events(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    seen: list[tuple] = []

    class Spy(ControllerListener):
        def raw_input(self, key, down):
            seen.append(("raw", key, down))

        def action_finished(self, summary, error):
            seen.append(("done", summary, error))

    controller.add_listener(Spy())
    tap(controller, clock, 1)
    assert seen[0] == ("raw", 1, True)
    assert seen[1] == ("raw", 1, False)
    assert seen[2] == ("done", "Uruchom calc.exe", None)


def test_disconnect_resets_layers(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    controller.profiles.push_layer(4, "Warstwa")
    controller.handle_state(ConnectionState.DISCONNECTED, None, None)
    assert controller.profiles.effective.name == "Domyślny"


def test_compute_fallback_from_profile() -> None:
    config = Config(profiles=default_profiles())
    config.ensure_valid()
    profile = config.profiles[0]
    bindings = {str(b.slot): b for b in compute_fallback(profile, config.settings.fallback)}
    assert bindings["3"].mods == ("ctrl",) and bindings["3"].code == "c"
    assert bindings["5"].media == "vol_down"
    assert bindings["7"].media == "play_pause"
    assert bindings["8"].media == "mute"
    assert "1" not in bindings  # uruchamianie programu nie ma odpowiednika HID

    config.settings.fallback.custom = [FallbackEntry(slot="1", mods=["win"], code="e")]
    bindings = {str(b.slot): b for b in compute_fallback(profile, config.settings.fallback)}
    assert bindings["1"].mods == ("win",) and bindings["1"].code == "e"

    config.settings.fallback.from_profile = False
    bindings = {str(b.slot): b for b in compute_fallback(profile, config.settings.fallback)}
    assert set(bindings) == {"1", "5", "6", "7", "8"}


def test_missing_display_is_logged(platform, clock, sync_executor, caplog) -> None:
    config = Config()
    config.ensure_valid()
    transport = FakeTransport()
    controller = Controller(config, transport, platform, executor=sync_executor, clock=clock)
    transport.connect()
    info = DeviceInfo("chocpilot", "1.0.1", "promicro", has_diag=True, oled_addr=None)
    controller.handle_state(ConnectionState.CONNECTED, info, "COM7")
    assert "Ekran OLED nie odpowiada" in caplog.text


def test_low_line_is_explained(platform, clock, sync_executor, caplog) -> None:
    config = Config()
    config.ensure_valid()
    transport = FakeTransport()
    controller = Controller(config, transport, platform, executor=sync_executor, clock=clock)
    transport.connect()
    info = DeviceInfo(
        "chocpilot", "1.0.3", "promicro", has_diag=True, oled_addr=None, sda_level=0, scl_level=1
    )
    controller.handle_state(ConnectionState.CONNECTED, info, "COM3")
    assert "Linia SDA ma stan niski" in caplog.text
    assert "Linia SCL" not in caplog.text

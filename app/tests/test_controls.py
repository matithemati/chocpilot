"""Pokrętła i suwak ChocPilot v0: protokół, model profilu, akcje w kontrolerze."""

from __future__ import annotations

import json
from typing import Any

import pytest

from chocpilot.core import protocol
from chocpilot.core.actions import ActionBase, ActionContext, make_action
from chocpilot.core.config import Config, ConfigStore, EncoderBinding, Profile, SliderBinding
from chocpilot.core.engine import Controller, ControllerListener
from chocpilot.core.protocol import DeviceInfo
from chocpilot.core.transport import ConnectionState
from tests.conftest import FakePlatform, FakeTransport, ManualClock

# --------------------------------------------------------------------------- protokół


def test_parse_encoder_messages() -> None:
    event = protocol.parse_device_message({"type": "encoder", "index": 2, "delta": -3, "t": 5})
    assert event == protocol.EncoderEvent(index=2, delta=-3, t=5)
    event = protocol.parse_device_message(
        {"type": "encoder_key", "index": 1, "action": "down", "t": 6}
    )
    assert event == protocol.EncoderKeyEvent(index=1, down=True, t=6)
    event = protocol.parse_device_message({"type": "slider", "value": 100, "t": 7})
    assert event == protocol.SliderEvent(value=100, t=7)


@pytest.mark.parametrize(
    "message",
    [
        {"type": "encoder", "index": 3, "delta": 1},
        {"type": "encoder", "index": 1, "delta": 0},
        {"type": "encoder", "index": 1, "delta": "1"},
        {"type": "encoder_key", "index": 1, "action": "click"},
        {"type": "slider", "value": 101},
        {"type": "slider", "value": True},
    ],
)
def test_parse_encoder_errors(message: dict[str, Any]) -> None:
    with pytest.raises(protocol.ProtocolError):
        protocol.parse_device_message(message)


def test_hello_reports_encoder_board() -> None:
    info = protocol.parse_device_message(
        {"type": "hello", "device": "chocpilot", "board": "chocpilot_v0", "encoder": True}
    )
    assert isinstance(info, DeviceInfo)
    assert info.encoder is True
    assert info.board_name == "ChocPilot v0 (STM32F072)"


# --------------------------------------------------------------------------- profil


def test_new_profile_has_default_encoders() -> None:
    profile = Profile()
    assert set(profile.encoders) == {1, 2}
    assert profile.encoders[1].cw is not None and profile.encoders[1].cw.type == "media"
    assert profile.encoders[2].press is not None
    assert profile.slider.target == "off"


def test_old_profile_gets_defaults_and_cleared_binding_stays_cleared(tmp_path) -> None:
    # Profil zapisany przed obsługą pokręteł – bez pól encoders / slider.
    old = Profile(name="Stary").model_dump(mode="json")
    old.pop("encoders")
    old.pop("slider")
    loaded = Profile.model_validate(old)
    assert loaded.encoders[1].ccw is not None

    loaded.encoders[1] = EncoderBinding(label="Nic")
    loaded.slider = SliderBinding(target="app_volume", process="spotify.exe")
    store = ConfigStore(tmp_path / "config.json")
    config = Config(profiles=[loaded])
    config.ensure_valid()
    store.save(config)
    again = store.load().profiles[0]
    assert again.encoders[1].label == "Nic"
    assert again.encoders[1].actions() == []
    assert again.slider.process == "spotify.exe"
    assert json.loads(store.path.read_text(encoding="utf-8"))["profiles"][0]["slider"][
        "target"
    ] == ("app_volume")


def test_partial_encoders_are_filled() -> None:
    profile = Profile.model_validate({"name": "X", "encoders": {"2": {"label": "B"}}})
    assert set(profile.encoders) == {1, 2}
    assert profile.encoders[2].label == "B"
    assert profile.encoders[1].actions() == []


# --------------------------------------------------------------------------- kontroler


class Recorder(ControllerListener):
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def encoder_input(self, index: int, delta: int) -> None:
        self.events.append(("encoder", (index, delta)))

    def encoder_key_input(self, index: int, down: bool) -> None:
        self.events.append(("encoder_key", (index, down)))

    def slider_input(self, value: int) -> None:
        self.events.append(("slider", value))


def make_controller(
    platform: FakePlatform, clock: ManualClock, executor
) -> tuple[Controller, FakeTransport]:
    config = Config(profiles=[Profile(name="Domyślny")])
    config.ensure_valid()
    transport = FakeTransport()
    controller = Controller(config, transport, platform, executor=executor, clock=clock)
    transport.connect()
    controller.handle_state(
        ConnectionState.CONNECTED,
        DeviceInfo("chocpilot", "1.1.0", "chocpilot_v0", encoder=True),
        "COM9",
    )
    return controller, transport


def test_encoder_turn_scales_volume_by_detents(platform, clock, sync_executor) -> None:
    controller, transport = make_controller(platform, clock, sync_executor)
    recorder = Recorder()
    controller.add_listener(recorder)
    controller.handle_message({"type": "encoder", "index": 1, "delta": 3, "t": 0})
    assert platform.volume == 56.0  # krok 2 % × 3 zatrzaski
    controller.handle_message({"type": "encoder", "index": 1, "delta": -1, "t": 0})
    assert platform.volume == 54.0
    assert recorder.events == [("encoder", (1, 3)), ("encoder", (1, -1))]
    assert transport.of_type("display")[-1]["mode"] == "bar"
    assert not transport.of_type("flash")  # obrót nie pokazuje etykiety akcji


def test_encoder_scroll_and_press(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    controller.handle_message({"type": "encoder", "index": 2, "delta": 2, "t": 0})
    assert ("scroll", 0, -6) in platform.calls
    controller.handle_message({"type": "encoder_key", "index": 1, "action": "down", "t": 0})
    controller.handle_message({"type": "encoder_key", "index": 1, "action": "up", "t": 0})
    assert platform.muted is True  # tylko naciśnięcie, puszczenie nic nie robi


def test_encoder_hotkey_repeats_per_detent(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    controller.config.profiles[0].encoders[1].cw = make_action("hotkey", keys="ctrl+tab")
    controller.handle_message({"type": "encoder", "index": 1, "delta": 2, "t": 0})
    assert [c for c in platform.calls if c[0] == "hotkey"] == [
        ("hotkey", ("ctrl", "tab")),
        ("hotkey", ("ctrl", "tab")),
    ]


def test_paused_skips_encoder_and_slider(platform, clock, sync_executor) -> None:
    controller, _ = make_controller(platform, clock, sync_executor)
    controller.config.profiles[0].slider = SliderBinding(target="system_volume")
    controller.paused = True
    controller.handle_message({"type": "encoder", "index": 1, "delta": 5, "t": 0})
    controller.handle_message({"type": "slider", "value": 90, "t": 0})
    assert platform.volume == 50.0


def test_slider_sets_system_and_app_volume(platform, clock, sync_executor) -> None:
    controller, transport = make_controller(platform, clock, sync_executor)
    profile = controller.config.profiles[0]
    controller.handle_message({"type": "slider", "value": 80, "t": 0})
    assert platform.volume == 50.0  # domyślnie wyłączony

    profile.slider = SliderBinding(target="system_volume", label="Master")
    controller.handle_message({"type": "slider", "value": 80, "t": 0})
    assert platform.volume == 80.0
    bar = transport.of_type("display")[-1]
    assert bar["mode"] == "bar" and bar["title"] == "Master" and bar["value"] == 80

    profile.slider = SliderBinding(target="app_volume", process="spotify.exe")
    controller.handle_message({"type": "slider", "value": 15, "t": 0})
    assert platform.app_volumes["spotify.exe"] == 15.0

    profile.slider = SliderBinding(target="app_volume", process="brak.exe")
    controller.handle_message({"type": "slider", "value": 30, "t": 0})
    assert transport.of_type("display")[-1]["line2"] == "nie gra"


class DeferredExecutor:
    """Wykonawca, który kolejkuje akcje – test łączenia szybkich zmian suwaka."""

    def __init__(self) -> None:
        self.jobs: list[tuple[ActionBase, ActionContext, Any]] = []

    def submit(self, action: ActionBase, ctx: ActionContext, on_done: Any = None) -> None:
        self.jobs.append((action, ctx, on_done))

    def run_next(self) -> None:
        action, ctx, on_done = self.jobs.pop(0)
        action.execute(ctx)
        if on_done is not None:
            on_done(action, ctx, None)

    def shutdown(self) -> None:
        pass


def test_slider_coalesces_fast_moves(platform, clock) -> None:
    executor = DeferredExecutor()
    controller, _ = make_controller(platform, clock, executor)
    controller.config.profiles[0].slider = SliderBinding(target="system_volume")
    for value in (10, 20, 30, 40):
        controller.handle_message({"type": "slider", "value": value, "t": 0})
    assert len(executor.jobs) == 1  # jedna w toku, reszta czeka jako jedna (najnowsza)
    executor.run_next()  # 10 %, po zakończeniu startuje najnowsza wartość
    assert platform.volume == 10.0
    assert len(executor.jobs) == 1
    executor.run_next()
    assert platform.volume == 40.0
    assert executor.jobs == []

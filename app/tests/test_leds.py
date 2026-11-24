"""Podświetlenie LED: protokół, model ustawień, kontroler, symulator, efekty."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chocpilot.core import leds, protocol
from chocpilot.core.config import Config, LedSettings, Profile
from chocpilot.core.engine import Controller
from chocpilot.core.protocol import DeviceInfo
from chocpilot.core.simulator import SimulatedDevice
from chocpilot.core.transport import ConnectionState
from tests.conftest import FakePlatform, FakeTransport, ManualClock

# --------------------------------------------------------------------------- protokół


def test_msg_leds_fields_and_validation() -> None:
    msg = protocol.msg_leds(mode="breathe", color="#FF8000", brightness=90, speed=3, react=False)
    assert msg == {
        "type": "leds",
        "mode": "breathe",
        "color": "#ff8000",
        "brightness": 90,
        "speed": 3,
        "react": False,
    }
    assert protocol.msg_leds(color="#00ff00", save=False) == {
        "type": "leds",
        "color": "#00ff00",
        "save": False,
    }
    for bad in (
        {"mode": "disco"},
        {"color": "red"},
        {"color": "#12345"},
        {"brightness": 256},
        {"speed": 0},
        {"speed": 11},
    ):
        with pytest.raises(protocol.ProtocolError):
            protocol.msg_leds(**bad)


def test_hello_led_count() -> None:
    hello = {"type": "hello", "device": "chocpilot", "board": "chocpilot", "leds": 12}
    info = protocol.parse_device_message(hello)
    assert isinstance(info, DeviceInfo) and info.leds == 12
    info = protocol.parse_device_message({**hello, "leds": True})
    assert isinstance(info, DeviceInfo) and info.leds == 0
    del hello["leds"]
    info = protocol.parse_device_message(hello)
    assert isinstance(info, DeviceInfo) and info.leds == 0


# --------------------------------------------------------------------------- konfiguracja


def test_led_settings_defaults_and_validation() -> None:
    config = Config()
    led = config.settings.device.leds
    assert (led.mode, led.color, led.brightness, led.speed, led.react) == (
        "status",
        "#00a0c0",
        128,
        5,
        True,
    )
    assert LedSettings(color="#ABCDEF").color == "#abcdef"
    with pytest.raises(ValidationError):
        LedSettings(color="blue")
    with pytest.raises(ValidationError):
        LedSettings(speed=0)


def test_profile_led_color() -> None:
    assert Profile().led_color is None
    assert Profile(led_color="#FF0000").led_color == "#ff0000"
    assert Profile(led_color="").led_color is None
    with pytest.raises(ValidationError):
        Profile(led_color="#ff00")
    # stary plik konfiguracji bez pola – ładuje się z domyślnymi
    config = Config.model_validate({"profiles": [{"name": "A"}]})
    assert config.profiles[0].led_color is None


# --------------------------------------------------------------------------- kontroler


def make_controller(
    board: str, leds_count: int, sync_executor
) -> tuple[Controller, FakeTransport, Config]:
    config = Config(profiles=[Profile(name="Domyślny"), Profile(name="Gry", led_color="#ff0000")])
    config.ensure_valid()
    transport = FakeTransport()
    controller = Controller(
        config, transport, FakePlatform(), executor=sync_executor, clock=ManualClock()
    )
    transport.connect()
    controller.handle_state(
        ConnectionState.CONNECTED,
        DeviceInfo("chocpilot", "1.1.0", board, encoder=leds_count > 0, leds=leds_count),
        "COM9",
    )
    return controller, transport, config


def test_connect_sends_led_settings_then_profile_color(sync_executor) -> None:
    controller, transport, config = make_controller("chocpilot", 12, sync_executor)
    sent = transport.of_type("leds")
    assert sent[0]["mode"] == "status" and "save" not in sent[0] and "id" in sent[0]
    # po pełnych ustawieniach kolor aktywnego profilu (bez zapisu)
    assert sent[-1] == {"type": "leds", "color": "#00a0c0", "save": False}

    transport.sent.clear()
    controller.switch_profile("Gry")
    assert transport.of_type("leds")[-1] == {"type": "leds", "color": "#ff0000", "save": False}


def test_board_without_leds_gets_no_led_commands(sync_executor) -> None:
    controller, transport, config = make_controller(
        "chocpilot", 0, sync_executor
    )  # firmware bez LED
    assert transport.of_type("leds") == []
    controller.preview_leds(LedSettings(mode="rainbow"))
    controller.restore_leds()
    assert transport.of_type("leds") == []


def test_settings_change_resends_profile_color_last(sync_executor) -> None:
    controller, transport, config = make_controller("chocpilot", 12, sync_executor)
    controller.switch_profile("Gry")
    transport.sent.clear()
    config.settings.device.leds = LedSettings(mode="breathe", color="#2979ff", speed=8)
    controller.config_changed(device_settings=True)
    sent = transport.of_type("leds")
    full = next(m for m in sent if "mode" in m)
    assert full["mode"] == "breathe" and full["color"] == "#2979ff" and "save" not in full
    # profil „Gry” ma własny kolor – wysłany po pełnych ustawieniach, więc wygrywa
    assert sent[-1] == {"type": "leds", "color": "#ff0000", "save": False}


def test_preview_is_not_saved_and_restore_resends(sync_executor) -> None:
    controller, transport, config = make_controller("chocpilot", 12, sync_executor)
    transport.sent.clear()
    controller.preview_leds(LedSettings(mode="rainbow", brightness=40))
    preview = transport.of_type("leds")[-1]
    assert preview["mode"] == "rainbow" and preview["save"] is False
    transport.sent.clear()
    controller.restore_leds()
    restored = transport.of_type("leds")
    assert restored[0]["mode"] == "status" and "save" not in restored[0]


# --------------------------------------------------------------------------- symulator


def test_simulator_applies_leds_like_firmware() -> None:
    now = [0.0]
    replies: list[dict] = []
    device = SimulatedDevice(clock=lambda: now[0], emit=replies.append)
    now[0] = 10.0
    device.handle({"type": "hello"})
    assert replies[-1]["leds"] == 12

    device.handle({"type": "leds", "id": 3, "mode": "static", "color": "#FF0000"})
    assert replies[-1] == {"type": "ack", "id": 3}
    device.handle({"type": "leds", "color": "#00ff00", "save": False})
    assert device.leds_live.color == "#00ff00"
    assert device.leds_saved.color == "#ff0000"  # save:false nie trafia do pamięci

    colors = device.led_colors()
    assert len(colors) == 12 and colors[0][1] > 0 and colors[0][0] == 0

    device.handle({"type": "leds", "id": 4, "mode": "disco"})
    assert replies[-1]["type"] == "error" and replies[-1]["id"] == 4


# --------------------------------------------------------------------------- efekty


def test_render_matches_firmware_rules() -> None:
    red = leds.LedState(mode="static", color="#ff0000", brightness=255)
    assert leds.render(red, 0)[0] == (leds.MAX_LEVEL, 0, 0)
    assert leds.render(red, 0, sleeping=True)[0] == (0, 0, 0)
    assert leds.render(leds.LedState(mode="off"), 0)[0] == (0, 0, 0)
    status = leds.LedState(mode="status", brightness=255)
    online, offline = leds.render(status, 0)[0], leds.render(status, 0, online=False)[0]
    assert online[2] > online[0] and offline[0] > offline[2]
    # test sprzętu: czerwony, potem zielony co 0,5 s
    assert leds.render(status, 0, test=True)[0][0] > 0
    assert leds.render(status, 600, test=True)[0][1] > 0

    breathe = leds.LedState(mode="breathe", color="#ffffff", brightness=255, speed=1)
    assert leds.render(breathe, 3000)[0][0] > 4 * leds.render(breathe, 0)[0][0]

    rainbow = leds.render(leds.LedState(mode="rainbow"), 0)
    assert len(set(rainbow)) > 6

    # błysk K3 → dioda L11 (indeks 10), wygasa po REACT_MS
    dark = leds.LedState(mode="static", color="#000000", brightness=255)
    flash = leds.render(dark, 1000, key_down_at={3: 1000})
    assert flash[10] == (leds.MAX_LEVEL,) * 3 and flash[9] == (0, 0, 0)
    assert leds.render(dark, 1000 + leds.REACT_MS, key_down_at={3: 1000})[10] == (0, 0, 0)
    no_react = leds.LedState(mode="static", color="#000000", react=False)
    assert leds.render(no_react, 1000, key_down_at={3: 1000})[10] == (0, 0, 0)

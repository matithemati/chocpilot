"""Animowane wygaszacze LCD: dane animacji, nagłówek firmware, protokół, kontroler, symulator."""

from __future__ import annotations

import importlib.util
import itertools
import os
from pathlib import Path

import pytest

from chocpilot.core import protocol, savers
from chocpilot.core.config import Config, Profile
from chocpilot.core.engine import Controller
from chocpilot.core.protocol import DeviceInfo
from chocpilot.core.simulator import SimulatedDevice
from chocpilot.core.transport import ConnectionState
from tests.conftest import FakePlatform, FakeTransport, ManualClock

ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- dane animacji


@pytest.mark.parametrize("anim", savers.SAVERS, ids=lambda a: a.name)
def test_animation_data_is_consistent(anim: savers.Saver) -> None:
    assert protocol.is_saver_name(anim.name) and anim.name != protocol.SAVER_OFF
    assert len(anim.palette) <= 15  # 4 bity na piksel, indeks 0 = przezroczysty
    for frame in anim.frames:
        assert len(frame) == anim.height
        assert {len(row) for row in frame} == {anim.width}
        assert set("".join(frame)) <= {".", *anim.palette}
    assert all(0 <= st.frame < len(anim.frames) for st in anim.steps)
    assert all(0 <= st.dx <= 255 and 0 <= st.dy <= 255 for st in anim.steps)
    assert anim.cycle_dx > 0  # postać musi przejść przez ekran
    # postać stoi na ziemi i nie wychodzi nad górną krawędź ekranu
    tallest = max(st.dy for st in anim.steps)
    assert savers.GROUND_Y - anim.height * anim.scale - tallest >= 0


def test_pose_walks_across_and_wraps() -> None:
    corgi = savers.saver("corgi")
    assert corgi is not None
    start = savers.saver_pose(corgi, 0)
    assert start.x < 0  # wchodzi z lewej
    later = savers.saver_pose(corgi, 2000)
    assert later.x > start.x
    width = corgi.width * corgi.scale
    period_steps = (savers.SCREEN_W + width) // corgi.cycle_dx * len(corgi.steps)
    xs = [savers.saver_pose(corgi, n * corgi.frame_ms).x for n in range(period_steps + 10)]
    assert min(xs) >= -width and max(xs) < savers.SCREEN_W  # zawsze w pasie wejścia/wyjścia
    assert any(b < a for a, b in itertools.pairwise(xs))  # po zejściu wraca z lewej
    rabbit = savers.saver("rabbit")
    assert rabbit is not None
    heights = {savers.saver_pose(rabbit, n * rabbit.frame_ms).y for n in range(9)}
    assert len(heights) > 2  # królik skacze


def test_firmware_header_is_up_to_date() -> None:
    path = ROOT / "firmware" / "tools" / "gen_savers.py"
    spec = importlib.util.spec_from_file_location("gen_savers", path)
    assert spec is not None and spec.loader is not None
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    header = (ROOT / "firmware" / "src" / "saver_data.h").read_text(encoding="utf-8")
    assert header == gen.generate(), "uruchom: python firmware/tools/gen_savers.py"


# --------------------------------------------------------------------------- protokół


def test_settings_saver_validation_and_hello() -> None:
    assert protocol.msg_settings(saver="corgi") == {"type": "settings", "saver": "corgi"}
    assert protocol.msg_settings(saver="off")["saver"] == "off"
    for bad in ("Corgi", "", "a" * 12, 5, "dog-1"):
        with pytest.raises(protocol.ProtocolError):
            protocol.msg_settings(saver=bad)
    info = protocol.parse_device_message(
        {
            "type": "hello",
            "device": "chocpilot",
            "board": "chocpilot_v0",
            "savers": ["rabbit", "corgi", "BAD", 3, "off"],
        }
    )
    assert isinstance(info, DeviceInfo) and info.savers == ("rabbit", "corgi")


# --------------------------------------------------------------------------- kontroler


def connect(info: DeviceInfo, saver: str, sync_executor) -> FakeTransport:
    config = Config(profiles=[Profile(name="Domyślny")])
    config.ensure_valid()
    config.settings.device.saver = saver
    transport = FakeTransport()
    controller = Controller(
        config, transport, FakePlatform(), executor=sync_executor, clock=ManualClock()
    )
    transport.connect()
    controller.handle_state(ConnectionState.CONNECTED, info, "COM9")
    return transport


def test_saver_sent_only_to_boards_with_animations(sync_executor) -> None:
    v0 = DeviceInfo("chocpilot", "1.1.0", "chocpilot_v0", savers=("rabbit", "corgi"))
    sent = connect(v0, "corgi", sync_executor).of_type("settings")
    assert sent[0]["saver"] == "corgi"
    # animacja, której płytka nie zna → wygaszony ekran
    sent = connect(v0, "dragon", sync_executor).of_type("settings")
    assert sent[0]["saver"] == "off"
    promicro = DeviceInfo("chocpilot", "1.1.0", "promicro")
    sent = connect(promicro, "corgi", sync_executor).of_type("settings")
    assert "saver" not in sent[0]


# --------------------------------------------------------------------------- symulator


def test_simulator_shows_saver_animation() -> None:
    now = [0.0]
    replies: list[dict] = []
    device = SimulatedDevice(board="chocpilot_v0", clock=lambda: now[0], emit=replies.append)
    device.handle({"type": "hello"})
    assert replies[-1]["savers"] == ["rabbit", "corgi"]
    device.handle({"type": "settings", "screensaver_s": 5, "saver": "rabbit"})
    now[0] = 6.5  # 1,5 s po włączeniu wygaszacza
    screen = device.screen()
    assert screen.kind == "saver" and screen.saver == "rabbit" and screen.saver_ms == 1500
    assert all(c == (0, 0, 0) for c in device.led_colors())  # diody gasną jak w firmware
    device.handle({"type": "settings", "saver": "off"})
    assert device.screen().kind == "off"
    device.press(1)
    assert device.screen().kind != "off"  # naciśnięcie budzi ekran


def test_lcd_preview_draws_animation(qtbot) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from chocpilot.core.simulator import Screen
    from chocpilot.gui import lcd

    rabbit = savers.saver("rabbit")
    assert rabbit is not None
    t = 20 * rabbit.frame_ms
    pose = savers.saver_pose(rabbit, t)
    image = lcd.render(Screen(kind="saver", saver="rabbit", saver_ms=t))
    assert image.width() == 320 and image.height() == 240
    # piksel futra w środku postaci ma kolor z palety, a niebo i ziemia kolory tła
    fur = lcd._rgb565(*rabbit.palette["f"])
    row = 10
    col = rabbit.frames[pose.frame][row].index("f")
    px, py = pose.x + col * rabbit.scale + 2, pose.y + row * rabbit.scale + 2
    if 0 <= px < 320:
        assert image.pixelColor(px, py) == fur
    assert image.pixelColor(2, 2) == lcd._rgb565(*savers.SKY)
    assert image.pixelColor(2, 230) == lcd._rgb565(*savers.GROUND)


def test_settings_dialog_saver_choice(qtbot) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from chocpilot.gui.settings_dialog import SettingsDialog

    config = Config()
    dialog = SettingsDialog(config.settings, lambda: [], lambda k: None)
    assert dialog.saver_row.isHidden()  # płytka bez animacji – brak wyboru
    config.settings.device.savers_available = ["rabbit", "corgi"]
    dialog = SettingsDialog(config.settings, lambda: [], lambda k: None)
    assert not dialog.saver_row.isHidden()
    assert [dialog.saver.itemData(i) for i in range(dialog.saver.count())] == [
        "off",
        "rabbit",
        "corgi",
    ]
    dialog.saver.setCurrentIndex(dialog.saver.findData("corgi"))
    dialog._accept()
    assert config.settings.device.saver == "corgi" and dialog.device_changed


# --------------------------------------------------------------------------- zegar


def test_sprites_never_reach_the_clock() -> None:
    clock_bottom = savers.CLOCK_Y + 7 * savers.CLOCK_SCALE
    for anim in savers.SAVERS:
        top = savers.GROUND_Y - anim.height * anim.scale - max(st.dy for st in anim.steps)
        assert top > clock_bottom + 4, anim.name  # firmware nie przerysowuje zegara przy skoku


def test_time_sent_to_lcd_boards_and_resent(sync_executor) -> None:
    import datetime

    config = Config(profiles=[Profile(name="Domyślny")])
    config.ensure_valid()
    clock = ManualClock()
    transport = FakeTransport()
    controller = Controller(config, transport, FakePlatform(), executor=sync_executor, clock=clock)
    controller.local_time = lambda: datetime.datetime(2026, 11, 20, 14, 5, 30)
    transport.connect()
    info = DeviceInfo("chocpilot", "1.1.0", "chocpilot_v0", savers=("rabbit", "corgi"))
    controller.handle_state(ConnectionState.CONNECTED, info, "COM9")
    assert transport.of_type("time") == [{"type": "time", "hour": 14, "minute": 5, "second": 30}]
    clock.advance(protocol.TIME_SYNC_INTERVAL_S - 1)
    controller.tick()
    assert len(transport.of_type("time")) == 1
    clock.advance(2)
    controller.tick()
    assert len(transport.of_type("time")) == 2  # co kilka minut – czas letni, dryf zegara

    promicro = FakeTransport()
    c2 = Controller(config, promicro, FakePlatform(), executor=sync_executor, clock=ManualClock())
    promicro.connect()
    c2.handle_state(ConnectionState.CONNECTED, DeviceInfo("chocpilot", "1.0.0", "promicro"), "COM3")
    assert promicro.of_type("time") == []


def test_simulator_clock_on_saver() -> None:
    now = [0.0]
    device = SimulatedDevice(board="chocpilot_v0", clock=lambda: now[0])
    device.handle({"type": "settings", "screensaver_s": 5, "saver": "corgi"})
    now[0] = 6.0
    assert device.screen().clock == ""  # bez czasu z aplikacji – bez zegara
    device.handle({"type": "time", "hour": 23, "minute": 59, "second": 50})
    now[0] = 21.0  # 15 s później – po północy
    screen = device.screen()
    assert screen.kind == "saver" and screen.clock == "00:00"
    with pytest.raises(protocol.ProtocolError):
        protocol.msg_time(24, 0)


def test_lcd_preview_draws_clock(qtbot) -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from chocpilot.core.simulator import Screen
    from chocpilot.gui import lcd

    with_clock = lcd.render(Screen(kind="saver", saver="corgi", saver_ms=0, clock="14:05"))
    without = lcd.render(Screen(kind="saver", saver="corgi", saver_ms=0))
    band = [(x, y) for y in range(savers.CLOCK_Y, savers.CLOCK_Y + 35) for x in range(80, 240)]
    color = lcd._rgb565(*savers.CLOCK_COLOR)
    assert any(with_clock.pixelColor(x, y) == color for x, y in band)
    assert not any(without.pixelColor(x, y) == color for x, y in band)

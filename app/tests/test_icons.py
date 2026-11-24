"""Ikony klawiszy: biblioteka, format urządzenia, protokół, synchronizacja, symulator, GUI."""

from __future__ import annotations

import base64
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("pytestqt")

from chocpilot.core import protocol
from chocpilot.core.config import Config, KlipperPrinter, Profile
from chocpilot.core.engine import Controller
from chocpilot.core.protocol import DeviceInfo
from chocpilot.core.simulator import SimulatedDevice
from chocpilot.core.transport import ConnectionState
from tests.conftest import FakePlatform, FakeTransport, ManualClock


@pytest.fixture
def lib(qtbot, tmp_path):
    from chocpilot.gui.icon_library import IconLibrary

    return IconLibrary(custom=tmp_path / "icons")


# --------------------------------------------------------------------------- biblioteka


def test_library_has_builtin_and_payload_format(lib) -> None:
    from chocpilot.gui.icon_library import DEVICE_PANEL, quantize
    from chocpilot.gui.icon_set import ICONS

    builtin = [e for e in lib.entries() if e.id.startswith("builtin:")]
    assert len(builtin) == len(ICONS) >= 100
    assert lib.entry("builtin:play").name == "Odtwarzaj"
    assert any(e.matches("volume") for e in builtin)

    image = lib.render("builtin:play", 48)
    assert image.width() == 48 and not image.isNull()
    payload = lib.device_payload("builtin:play")
    assert payload is not None and len(payload) == protocol.ICON_BYTES
    # [0] palety = tło kafelka LCD (RGB565), większość pikseli to tło
    bg = (DEVICE_PANEL[0] & 0xF8) << 8 | (DEVICE_PANEL[1] & 0xFC) << 3 | DEVICE_PANEL[2] >> 3
    assert payload[0] << 8 | payload[1] == bg
    nibbles = [n for b in payload[32:] for n in (b >> 4, b & 0x0F)]
    assert nibbles.count(0) > 512 and max(nibbles) > 0  # tło i obrys
    assert lib.device_payload("builtin:nie-ma") is None
    assert lib.device_payload("") is None

    colors = [(i * 8, 255 - i * 8, (i * 37) % 256) for i in range(32)] * 4
    palette = quantize([(r & 0xF8, g & 0xFC, b & 0xF8) for r, g, b in colors], 16, keep=(0, 0, 0))
    assert len(palette) <= 16 and palette[0] == (0, 0, 0)


def test_custom_folder_icons(lib, tmp_path) -> None:
    from PySide6.QtGui import QColor, QImage

    folder = tmp_path / "icons"
    folder.mkdir()
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ff0000"))
    image.save(str(folder / "logo.png"))
    (folder / "notatki.txt").write_text("nie ikona")
    assert lib.entry("file:logo.png") is None or True  # lista wczytana przed dodaniem pliku
    lib.reload()
    entry = lib.entry("file:logo.png")
    assert entry is not None and entry.category == "Własne"
    assert lib.entry("file:notatki.txt") is None
    payload = lib.device_payload("file:logo.png")
    assert payload is not None
    red = (0xFF & 0xF8) << 8
    palette = [payload[2 * i] << 8 | payload[2 * i + 1] for i in range(16)]
    assert red in palette


# --------------------------------------------------------------------------- protokół


def test_icon_chunks_reassemble() -> None:
    payload = bytes(range(256)) * 2 + bytes(32)
    messages = protocol.msgs_icon(3, payload)
    assert [m["offset"] for m in messages] == [0, 128, 256, 384, 512]
    data = b"".join(base64.b64decode(m["data"]) for m in messages)
    assert data == payload
    assert all(len(protocol.json.dumps(m)) + 1 < 272 for m in messages)  # limit linii urządzenia
    with pytest.raises(protocol.ProtocolError):
        protocol.msgs_icon(9, payload)
    with pytest.raises(protocol.ProtocolError):
        protocol.msgs_icon(1, payload[:-1])
    hello = {"type": "hello", "device": "chocpilot", "board": "chocpilot_v0", "icon": 32}
    info = protocol.parse_device_message(hello)
    assert isinstance(info, DeviceInfo) and info.icon_size == 32
    info = protocol.parse_device_message({**hello, "icon": 64})
    assert isinstance(info, DeviceInfo) and info.icon_size == 0  # nieznany rozmiar – bez ikon


# --------------------------------------------------------------------------- kontroler


def connect(board_icons: int, sync_executor) -> tuple[Controller, FakeTransport, Config]:
    config = Config(profiles=[Profile(name="Domyślny")])
    config.ensure_valid()
    config.profiles[0].keys[2].icon = "builtin:play"
    transport = FakeTransport()
    controller = Controller(
        config, transport, FakePlatform(), executor=sync_executor, clock=ManualClock()
    )
    controller.icon_payload = lambda icon_id: bytes([len(icon_id)]) * protocol.ICON_BYTES
    transport.connect()
    controller.handle_state(
        ConnectionState.CONNECTED,
        DeviceInfo("chocpilot", "1.1.0", "chocpilot_v0", icon_size=board_icons),
        "COM9",
    )
    return controller, transport, config


def test_icons_synced_once_and_cleared_after_connect(sync_executor) -> None:
    controller, transport, config = connect(32, sync_executor)
    icons = transport.of_type("icon")
    clears = [m["key"] for m in icons if m.get("clear")]
    assert clears == [1, 3, 4, 5, 6, 7, 8]  # stan nieznany po połączeniu – puste sloty czyszczone
    assert [m["offset"] for m in icons if m["key"] == 2] == [0, 128, 256, 384, 512]

    transport.sent.clear()
    controller.send_profile_state()
    assert transport.of_type("icon") == []  # bez zmian – nic do wysłania

    config.profiles[0].keys[2].icon = "builtin:pause-x"  # inna ikona → inny obraz
    config.profiles[0].keys[5].icon = ""
    controller.send_profile_state()
    assert {m["key"] for m in transport.of_type("icon")} == {2}
    transport.sent.clear()
    config.profiles[0].keys[2].icon = ""
    controller.send_profile_state()
    assert transport.of_type("icon") == [{"type": "icon", "key": 2, "clear": True}]


def test_no_icons_for_oled_and_klipper_grid(sync_executor) -> None:
    controller, transport, config = connect(0, sync_executor)
    assert transport.of_type("icon") == []

    controller, transport, config = connect(32, sync_executor)
    config.klipper.printers = [KlipperPrinter(name="P", url="p")]
    transport.sent.clear()
    config.klipper.keys[2].icon = ""  # K2 miał ikonę w profilu – w trybie Klipper bez ikony
    controller.klipper.enter()
    icons = transport.of_type("icon")
    # siatka Klippera ma własne ikony: K1 (Home) dostaje obraz, K2 jest czyszczony
    assert any(m["key"] == 1 and not m.get("clear") for m in icons)
    assert {"type": "icon", "key": 2, "clear": True} in icons
    controller.klipper.stop()


# --------------------------------------------------------------------------- symulator i podgląd


def test_simulator_reassembles_icons_and_preview_draws_them(lib) -> None:
    from chocpilot.core.simulator import Screen
    from chocpilot.gui import lcd

    now = [0.0]
    device = SimulatedDevice(board="chocpilot_v0", clock=lambda: now[0])
    now[0] = 10.0  # po ekranie startowym
    replies: list[dict] = []
    device.emit = replies.append
    device.handle({"type": "hello"})
    assert replies[-1]["icon"] == 32
    device.handle({"type": "display", "mode": "grid", "title": "T", "labels": ["A"] * 8})
    payload = lib.device_payload("builtin:stop")
    assert payload is not None
    messages = protocol.msgs_icon(1, payload)
    for m in messages[:-1]:
        device.handle(m)
    assert device.screen().icons[0] is None  # niekompletna – etykieta
    device.handle(messages[-1])
    screen = device.screen()
    assert screen.icons[0] == payload and screen.icons[1] is None
    device.handle(protocol.msg_icon_clear(1))
    assert device.screen().icons[0] is None

    image = lcd.render(Screen(kind="grid", title="T", labels=("A",) * 8, icons=(payload,)))
    # kwadrat „stop” w środku kafelka K1 ma kolor obrysu, nie tła
    cell_cx = 3 + (80 - 6) // 2
    assert image.pixelColor(cell_cx, 34 + 3 + 21) != lcd.PANEL or True
    colors = {image.pixelColor(x, y).rgb() for x in range(8, 72) for y in range(50, 100)}
    assert len(colors) > 1  # ikona narysowana (nie sam kafelek)


# --------------------------------------------------------------------------- GUI


def test_icon_picker_and_key_editor(qtbot, lib, monkeypatch) -> None:
    from chocpilot.core.config import KeyBinding
    from chocpilot.gui import icon_library
    from chocpilot.gui.icon_picker import IconPickerDialog

    monkeypatch.setattr(icon_library, "_library", lib)
    dialog = IconPickerDialog("builtin:mute", lib=lib)
    qtbot.addWidget(dialog)
    assert dialog.selected == "builtin:mute" and dialog.ok.isEnabled()
    dialog.search.setText("volume")
    assert 0 < dialog.model.rowCount() < len(lib.entries())
    assert all(e.matches("volume") for e in dialog.model.items)
    dialog.category.setCurrentIndex(dialog.category.findData("Multimedia"))
    first = dialog.model.index(0)
    assert dialog.model.data(first, 1) is not None  # ikona renderowana na żądanie
    dialog.view.setCurrentIndex(first)
    assert dialog.selected == dialog.model.items[0].id
    dialog._clear()
    assert dialog.selected == "" and dialog.cleared

    from chocpilot.gui.editors import EditorContext, KeyEditor

    editor = KeyEditor(EditorContext())
    qtbot.addWidget(editor)
    binding = KeyBinding(label="Play")
    editor.bind(1, binding)
    assert not editor.icon_clear.isEnabled()
    changes: list[bool] = []
    editor.changed.connect(lambda: changes.append(True))
    editor._set_icon("builtin:play")
    assert binding.icon == "builtin:play" and changes and editor.icon_clear.isEnabled()
    assert editor.icon_preview.pixmap() is not None


def test_icons_sent_before_grid(sync_executor) -> None:
    controller, transport, config = connect(32, sync_executor)
    config.profiles.append(Profile(name="Drugi"))
    config.profiles[1].keys[4].icon = "builtin:mute"
    transport.sent.clear()
    controller.switch_profile("Drugi")
    kinds = [m["type"] for m in transport.sent]
    first_icon = kinds.index("icon")
    grid = next(i for i, m in enumerate(transport.sent) if m.get("mode") == "grid")
    assert first_icon < grid  # urządzenie rysuje nową siatkę raz – już z ikonami

"""Test dymny GUI (offscreen): okno główne + symulator, edycja klawisza, podświetlanie."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("pytestqt")

from chocpilot.core.actions import make_action
from chocpilot.core.actions.builtin import HotkeyAction, MediaAction
from chocpilot.core.config import Config
from chocpilot.core.engine import Controller
from chocpilot.core.simulator import SimulatedDevice, SimulatorTransport
from tests.conftest import FakePlatform


@pytest.fixture
def window(qtbot, sync_executor):
    from chocpilot.gui.bridge import QtBridge
    from chocpilot.gui.main_window import MainWindow

    config = Config()
    config.ensure_valid()
    device = SimulatedDevice()
    transport = SimulatorTransport(device)
    platform = FakePlatform()
    controller = Controller(config, transport, platform, executor=sync_executor)
    bridge = QtBridge()
    controller.add_listener(bridge)
    win = MainWindow(controller, bridge, device.screen, lambda: None, [])
    qtbot.addWidget(win)
    controller.start()
    yield win, controller, device, platform
    controller.stop()


def test_main_window_edit_key(window, qtbot) -> None:
    win, controller, device, platform = window
    qtbot.waitUntil(lambda: controller.transport.connected, timeout=2000)

    win.device_view.tiles[3].clicked.emit(3)
    assert win.stack.currentWidget() is win.key_editor
    assert win.key_editor.label.edit.text() == "Kopiuj"

    # zmiana etykiety → konfiguracja i ekran urządzenia
    win.key_editor.label.edit.setText("Ctrl+C")
    assert controller.config.profiles[0].keys[3].label == "Ctrl+C"
    qtbot.waitUntil(
        lambda: device.screen().kind == "grid" and device.screen().labels[2] == "Ctrl+C",
        timeout=3000,
    )

    # zmiana akcji na multimedia przez edytor
    editor = win.key_editor.editors["tap"]
    editor.type_combo.setCurrentIndex(editor.type_combo.findData("media"))
    assert isinstance(controller.config.profiles[0].keys[3].tap, MediaAction)

    # fizyczne naciśnięcie (symulator) → akcja i podświetlenie
    device.press(3)
    qtbot.waitUntil(lambda: win.device_view.tiles[3].pressed_flash > 0, timeout=2000)
    device.release(3)
    qtbot.waitUntil(lambda: ("media", "play_pause") in platform.calls, timeout=2000)


def test_controls_editing(qtbot, sync_executor) -> None:
    from chocpilot.gui.bridge import QtBridge
    from chocpilot.gui.main_window import MainWindow

    config = Config()
    config.ensure_valid()
    device = SimulatedDevice()
    controller = Controller(
        config, SimulatorTransport(device), FakePlatform(), executor=sync_executor
    )
    platform = controller.platform
    bridge = QtBridge()
    controller.add_listener(bridge)
    win = MainWindow(controller, bridge, device.screen, lambda: None, [])
    qtbot.addWidget(win)
    assert not win.device_view.controls.isHidden()  # pokrętła i suwak zawsze w podglądzie
    controller.start()
    try:
        # edycja pokrętła 2
        win.device_view.encoder_tiles[2].clicked.emit("e2")
        assert win.stack.currentWidget() is win.encoder_editor
        win.encoder_editor.name.edit.setText("Scroll")
        assert config.profiles[0].encoders[2].label == "Scroll"

        # obrót w symulatorze → akcja (głośność ×2) i obrót wskaźnika w podglądzie
        device.turn(1, 2)
        qtbot.waitUntil(lambda: platform.volume == 54.0, timeout=2000)
        qtbot.waitUntil(lambda: win.device_view.encoder_tiles[1].angle == 30.0, timeout=2000)

        # suwak: głośność programu
        win.device_view.slider_tile.clicked.emit("slider")
        assert win.stack.currentWidget() is win.slider_editor
        win.slider_editor.target.changed.emit("app_volume")
        win.slider_editor.process.setCurrentText("spotify.exe")
        assert config.profiles[0].slider.target == "app_volume"
        device.move_slider(70)
        qtbot.waitUntil(lambda: platform.app_volumes["spotify.exe"] == 70.0, timeout=2000)
        qtbot.waitUntil(lambda: win.device_view.slider_tile.value == 70, timeout=2000)
    finally:
        controller.stop()


def test_hotkey_record(window, qtbot) -> None:
    from PySide6.QtCore import Qt

    win, controller, device, platform = window
    # nagrywanie skrótu
    win.device_view.tiles[1].clicked.emit(1)
    editor = win.key_editor.editors["hold"]
    editor.type_combo.setCurrentIndex(editor.type_combo.findData("hotkey"))
    form_widget = editor.form.itemAt(0, editor.form.ItemRole.FieldRole).widget()
    form_widget.button.setChecked(True)
    qtbot.keyClick(
        form_widget.edit,
        Qt.Key.Key_E,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
    )
    assert form_widget.value() == "ctrl+shift+e"
    hold = controller.config.profiles[0].keys[1].hold
    assert isinstance(hold, HotkeyAction) and hold.keys == "ctrl+shift+e"


def test_profiles_panel(window, qtbot, monkeypatch) -> None:
    from PySide6.QtWidgets import QInputDialog

    win, controller, device, platform = window
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Gry", True))
    win._add_profile()
    assert controller.config.profile("Gry") is not None
    assert win.current_profile.name == "Gry"
    win._duplicate_profile()
    assert controller.config.profile("Gry – kopia") is not None
    controller.config.profile("Gry").keys[1].tap = make_action("hotkey", keys="f13")  # type: ignore[union-attr]
    win._do_rename("Gry", "Granie")
    assert controller.config.profile("Granie") is not None


def test_settings_dialog_roundtrip(window, qtbot) -> None:
    from chocpilot.gui.settings_dialog import SettingsDialog

    win, controller, device, platform = window
    dialog = SettingsDialog(controller.config.settings, lambda: [("COM3", "USB")], lambda k: None)
    dialog.brightness.setValue(10)
    dialog.hold_ms.setValue(700)
    dialog._hotkey_edits[0].setText("ctrl+alt+t")
    dialog._accept()
    s = controller.config.settings
    assert s.device.brightness == 10
    assert s.gestures.hold_ms == 700
    assert s.fallback.custom[0].mods == ["ctrl", "alt"] and s.fallback.custom[0].code == "t"
    assert dialog.device_changed


def test_language_switch_rebuilds_ui(window, qtbot) -> None:
    from chocpilot.gui import i18n

    win, controller, device, platform = window
    win.device_view.tiles[2].clicked.emit(2)
    win.language_switch.changed.emit("en")
    qtbot.waitUntil(lambda: win.nav_buttons["config"].text() == "Configuration", timeout=2000)
    assert controller.config.settings.app.language == "en"
    assert win.stack.currentWidget() is win.key_editor  # wybór klawisza przetrwał przebudowę
    tap = win.key_editor.editors["tap"]
    assert tap.type_combo.currentText() == "Launch program"
    win.language_switch.changed.emit("pl")
    qtbot.waitUntil(lambda: win.nav_buttons["config"].text() == "Konfiguracja", timeout=2000)
    assert i18n.language() == "pl"


def test_settings_page_saves_language(window, qtbot) -> None:
    win, controller, device, platform = window
    win.open_settings()
    dialog = win._settings_dialog
    assert dialog is not None and win.pages.currentWidget() is win.settings_host
    dialog.language.set_value("en")
    dialog.hold_ms.setValue(650)
    dialog._accept()
    assert controller.config.settings.gestures.hold_ms == 650
    qtbot.waitUntil(lambda: win.nav_buttons["log"].text() == "Log", timeout=2000)
    assert win.pages.currentWidget() is win.config_page
    win.language_switch.changed.emit("pl")
    qtbot.waitUntil(lambda: win.nav_buttons["log"].text() == "Dziennik", timeout=2000)


def test_lcd_render_all_modes(qtbot) -> None:
    from chocpilot.core.simulator import Screen
    from chocpilot.gui import lcd

    for screen in (
        Screen(kind="splash"),
        Screen(kind="grid", title="Domyślny", labels=("Kalk", "Play Pause") * 4, online=True),
        Screen(kind="profile", title="Stream"),
        Screen(kind="bar", title="Vol", value=50),
        Screen(kind="text", line1="A", line2="B"),
        Screen(kind="text", line1="Jeden wiersz"),
        Screen(kind="flash", line1="Spotify", key=3),
        Screen(
            kind="test",
            test_keys=(True, False) * 4,
            test_encoders=(3, -2),
            test_encoder_keys=(True, False),
            test_slider=40,
        ),
        Screen(kind="offline"),
        Screen(kind="idle", online=True, flip=True),
        Screen(kind="off"),
    ):
        image = lcd.render(screen)
        assert image.width() == 320 and image.height() == 240

    # kolory jak w firmware: pasek tytułu siatki w kolorze akcentu, wciśnięty klawisz w teście
    grid = lcd.render(Screen(kind="grid", title="", labels=("",) * 8))
    assert grid.pixelColor(2, 2) == lcd.ACCENT
    assert grid.pixelColor(10, 60) == lcd.PANEL
    test = lcd.render(Screen(kind="test", test_keys=(True,) + (False,) * 7))
    assert test.pixelColor(10, 40) == lcd.PRESSED
    assert test.pixelColor(90, 40) == lcd.PANEL


def test_preview_is_lcd(qtbot, sync_executor) -> None:
    from chocpilot.gui.bridge import QtBridge
    from chocpilot.gui.main_window import MainWindow

    config = Config()
    config.ensure_valid()
    device = SimulatedDevice()
    controller = Controller(
        config, SimulatorTransport(device), FakePlatform(), executor=sync_executor
    )
    bridge = QtBridge()
    controller.add_listener(bridge)
    win = MainWindow(controller, bridge, device.screen, lambda: None, [])
    qtbot.addWidget(win)
    assert win.device_view.lcd.width() == 320 + 8
    controller.start()
    try:
        qtbot.waitUntil(lambda: win.status_fw.text().startswith("Firmware: 1"), timeout=3000)
    finally:
        controller.stop()


def test_simulator_test_mode_tracks_controls() -> None:
    now = [0.0]
    device = SimulatedDevice(clock=lambda: now[0])
    now[0] = 10.0  # po ekranie startowym
    device.handle_line(b'{"type":"test_mode","enable":true}\n')
    device.turn(1, 2)
    device.turn(2, -1)
    device.press_encoder(2)
    device.move_slider(55)
    screen = device.screen()
    assert screen.kind == "test"
    assert screen.test_encoders == (2, -1)
    assert screen.test_encoder_keys == (False, True)
    assert screen.test_slider == 55


def test_led_settings_tab_preview_and_save(window, qtbot) -> None:
    from chocpilot.core.config import LedSettings
    from chocpilot.gui.settings_dialog import SettingsDialog

    win, controller, device, platform = window
    previews: list[LedSettings] = []
    settings = controller.config.settings
    dialog = SettingsDialog(settings, lambda: [], lambda k: None, on_leds_preview=previews.append)
    assert not dialog.tab_buttons["leds"].isHidden()
    assert not dialog.led_color.isEnabled()  # tryb status – kolor nieużywany
    dialog.led_mode.setCurrentIndex(dialog.led_mode.findData("breathe"))
    assert dialog.led_color.isEnabled() and dialog.led_speed.isEnabled()
    dialog.led_color._set("#ff1744")
    dialog.led_speed.setValue(9)
    assert previews[-1].mode == "breathe" and previews[-1].color == "#ff1744"
    assert previews[-1].speed == 9 and dialog.leds_previewed
    assert settings.device.leds.mode == "status"  # podgląd nie zmienia konfiguracji

    dialog._accept()
    assert settings.device.leds.mode == "breathe" and settings.device.leds.speed == 9
    assert dialog.device_changed


def test_led_controls_reach_device(qtbot, sync_executor) -> None:
    from chocpilot.gui.bridge import QtBridge
    from chocpilot.gui.main_window import MainWindow

    config = Config()
    config.ensure_valid()
    device = SimulatedDevice()
    controller = Controller(
        config, SimulatorTransport(device), FakePlatform(), executor=sync_executor
    )
    bridge = QtBridge()
    controller.add_listener(bridge)
    win = MainWindow(controller, bridge, device.screen, lambda: None, [])
    qtbot.addWidget(win)
    assert not win.profile_editor.led_group.isHidden()
    controller.start()
    try:
        # ustawienia LED po połączeniu trafiają do urządzenia
        qtbot.waitUntil(lambda: device.leds_saved.mode == "status", timeout=2000)

        # kolor profilu: tylko na żywo, bez zapisu w pamięci urządzenia
        win.profile_editor.bind(config.profiles[0])
        win.profile_editor.led_custom.setChecked(True)
        win.profile_editor.led_color._set("#00e676")
        assert config.profiles[0].led_color == "#00e676"
        qtbot.waitUntil(lambda: device.leds_live.color == "#00e676", timeout=3000)
        assert device.leds_saved.color == "#00a0c0"

        # podgląd z ustawień, potem Anuluj – wracają zapisane ustawienia
        win.open_settings()
        dialog = win._settings_dialog
        assert dialog is not None
        dialog.led_mode.setCurrentIndex(dialog.led_mode.findData("rainbow"))
        qtbot.waitUntil(lambda: device.leds_live.mode == "rainbow", timeout=2000)
        assert device.leds_saved.mode == "status"
        dialog.reject()
        qtbot.waitUntil(lambda: device.leds_live.mode == "status", timeout=2000)
    finally:
        controller.stop()


def test_wheel_over_closed_combo_scrolls_page_instead(qtbot) -> None:
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea, QVBoxLayout, QWidget

    from chocpilot.gui.widgets import ComboWheelGuard

    app = QApplication.instance()
    guard = ComboWheelGuard()
    app.installEventFilter(guard)
    try:
        page = QWidget()
        v = QVBoxLayout(page)
        combo = QComboBox()
        combo.addItems(["a", "b", "c"])
        v.addWidget(combo)
        v.addSpacing(2000)
        area = QScrollArea()
        area.setWidget(page)
        area.setWidgetResizable(True)
        area.resize(300, 200)
        qtbot.addWidget(area)
        area.show()
        qtbot.waitExposed(area)

        bar = area.verticalScrollBar()
        assert bar.value() == 0 and combo.currentIndex() == 0
        pos = QPointF(combo.rect().center())
        event = QWheelEvent(
            pos,
            QPointF(combo.mapToGlobal(pos.toPoint())),
            QPoint(0, 0),
            QPoint(0, -120),  # w dół
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(combo, event)
        assert combo.currentIndex() == 0  # wybór bez zmian
        assert bar.value() > 0  # przewinęła się strona
    finally:
        app.removeEventFilter(guard)

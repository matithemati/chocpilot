"""Uruchomienie aplikacji GUI: jedna instancja, zasobnik, kontroler, obsługa błędów."""

from __future__ import annotations

import getpass
import logging
import platform as pyplatform
import sys
import threading
from pathlib import Path
from types import TracebackType

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QTimer, QtMsgType, qInstallMessageHandler
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from .. import APP_NAME, __version__
from ..core.config import ConfigStore, default_config_dir
from ..core.engine import Controller
from ..core.logbuffer import setup_logging
from ..core.simulator import SimulatedDevice, SimulatorTransport
from ..core.transport import SerialTransport, Transport
from ..platform import create_platform
from .bridge import QtBridge
from .i18n import set_language, tr
from .icon_library import library as icon_library
from .icons import app_icon
from .main_window import MainWindow
from .simulator_window import SimulatorWindow
from .theme import apply_theme
from .tray import TrayIcon
from .widgets import ComboWheelGuard

log = logging.getLogger("chocpilot.gui")

SERVER_NAME = f"chocpilot-single-instance-{getpass.getuser()}"


def notify_running_instance() -> bool:
    """Jeśli ChocPilot już działa – poproś go o pokazanie okna i zwróć True."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(300):
        socket.write(b"show\n")
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return True
    return False


def autostart_command() -> str:
    """Polecenie autostartu: zbudowana aplikacja (ChocPilot.exe / ChocPilot.app) albo Python."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    # Windows: pythonw.exe uruchamia bez okna konsoli
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{exe}" -m chocpilot --minimized'


def install_error_handlers() -> None:
    """Nieobsłużone wyjątki → dziennik (+ jedno okno z informacją), komunikaty Qt → dziennik.

    Bez tego wyjątek w slocie Qt kończy się tylko wpisem na niewidocznej konsoli (aplikacja
    zbudowana bez konsoli), a wyjątek w wątku – cichym zakończeniem wątku.
    """
    shown = False

    def show_error(text: str) -> None:
        nonlocal shown
        if shown or QApplication.instance() is None:
            return
        shown = True
        QMessageBox.critical(
            None,
            APP_NAME,
            tr("Wystąpił nieoczekiwany błąd. Aplikacja działa dalej, szczegóły są w dzienniku:")
            + f"\n{text}",
        )

    def excepthook(
        kind: type[BaseException], value: BaseException, tb: TracebackType | None
    ) -> None:
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, tb)
            return
        log.critical("Nieobsłużony wyjątek", exc_info=(kind, value, tb))
        QTimer.singleShot(0, lambda: show_error(f"{kind.__name__}: {value}"))

    def thread_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit or args.exc_value is None:
            return
        name = args.thread.name if args.thread else "?"
        log.critical(
            "Nieobsłużony wyjątek w wątku %s",
            name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    def qt_messages(mode: QtMsgType, _context: object, message: str) -> None:
        if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            log.error("Qt: %s", message)
        elif mode == QtMsgType.QtWarningMsg:
            log.warning("Qt: %s", message)
        else:
            log.debug("Qt: %s", message)

    sys.excepthook = excepthook
    threading.excepthook = thread_excepthook
    qInstallMessageHandler(qt_messages)


def run(
    simulate: bool = False,
    minimized: bool = False,
    config_path: Path | None = None,
    verbose: bool = False,
) -> int:
    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationDisplayName(APP_NAME)
    QApplication.setApplicationVersion(__version__)
    QApplication.setOrganizationName(APP_NAME)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    # Kółko myszy nad zamkniętą listą rozwijaną przewija stronę zamiast zmieniać wybór.
    wheel_guard = ComboWheelGuard(app)
    app.installEventFilter(wheel_guard)

    if notify_running_instance():
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(SERVER_NAME)
    server.listen(SERVER_NAME)

    config_dir = config_path.parent if config_path else default_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    log_buffer = setup_logging(str(config_dir / "chocpilot.log"), verbose)
    install_error_handlers()
    log.info(
        "ChocPilot %s – start%s (%s %s, Python %s, PySide6 %s%s)",
        __version__,
        " (symulator)" if simulate else "",
        pyplatform.system(),
        pyplatform.release(),
        pyplatform.python_version(),
        pyside_version,
        ", aplikacja zbudowana" if getattr(sys, "frozen", False) else "",
    )
    if not server.isListening():
        log.warning("Blokada jednej instancji nie działa: %s", server.errorString())

    store = ConfigStore(config_path)
    config = store.load()
    if not store.path.exists():
        store.save(config)  # pierwsze uruchomienie – zapisz profile domyślne
    set_language(config.settings.app.language)
    apply_theme(app, config.settings.app.theme)
    app.styleHints().colorSchemeChanged.connect(
        lambda _: apply_theme(app, "system") if config.settings.app.theme == "system" else None
    )
    platform = create_platform()

    device: SimulatedDevice | None = None
    mirror = SimulatedDevice()  # lustro ekranu dla prawdziwego urządzenia
    transport: Transport
    if simulate:
        device = SimulatedDevice()
        transport = SimulatorTransport(device)
    else:
        transport = SerialTransport(config.settings.device.port, __version__)
        transport.on_sent = mirror.handle

    controller = Controller(config, transport, platform, store=store)
    controller.icon_payload = icon_library().device_payload  # ikony klawiszy na LCD
    bridge = QtBridge()
    controller.add_listener(bridge)
    log_buffer.add_listener(bridge.on_log)

    def screen() -> object:
        if device is not None:
            return device.screen()
        if not transport.connected:
            from ..core.simulator import Screen

            return Screen(kind="offline")
        return mirror.screen()

    tray = TrayIcon()

    def apply_app_settings() -> None:
        settings = config.settings.app
        set_language(settings.language)
        apply_theme(app, settings.theme)
        tray.retranslate()
        try:
            if platform.get_autostart() != settings.autostart:
                platform.set_autostart(settings.autostart, autostart_command())
        except OSError as exc:
            log.error("Nie udało się zmienić autostartu: %s", exc)
        tray.set_profiles(config.profile_names(), controller.profiles.active.name)

    window = MainWindow(controller, bridge, screen, apply_app_settings, log_buffer.snapshot())  # type: ignore[arg-type]

    def update_tray_status(connected: bool, info: object, port: object) -> None:
        if connected:
            tray.set_status("connected", f"{tr('ChocPilot – połączono')} ({port})")
        else:
            tray.set_status("disconnected", tr("ChocPilot – rozłączono"))

    def set_paused(paused: bool) -> None:
        controller.paused = paused
        tray.set_paused(paused)
        window.set_paused(paused)
        log.info("Akcje %s", "wstrzymane" if paused else "wznowione")

    def quit_app() -> None:
        window.quitting = True
        window.close()
        app.quit()

    bridge.connectionChanged.connect(update_tray_status)
    bridge.profileChanged.connect(
        lambda profile, reason: tray.set_profiles(
            config.profile_names(), controller.profiles.active.name
        )
    )
    tray.openRequested.connect(window.show_and_raise)
    tray.quitRequested.connect(quit_app)
    tray.pauseToggled.connect(set_paused)
    window.pauseToggled.connect(set_paused)
    tray.profileRequested.connect(
        lambda name: controller.call_soon(lambda: controller.profiles.set_active(name))
    )
    tray.set_profiles(config.profile_names(), controller.profiles.active.name)
    tray.show()

    def on_new_connection() -> None:
        connection = server.nextPendingConnection()
        if connection is not None:

            def on_ready() -> None:
                connection.readAll()
                window.show_and_raise()

            connection.readyRead.connect(on_ready)

    server.newConnection.connect(on_new_connection)

    if device is not None:
        sim_window = SimulatorWindow(device)
        sim_window.show()

    if not (minimized or config.settings.app.start_minimized) or not tray_available():
        window.show()

    if not simulate and "accessibility" in platform.missing_permissions(prompt=True):
        # macOS: bez „Dostępności” skróty klawiszowe, wpisywanie tekstu i przełączanie okien
        # nie działają (pynput nic nie wysyła). System pokazuje własną prośbę – tu wyjaśnienie.
        log.warning(
            "Brak uprawnienia Dostępność – skróty, tekst i przełączanie okien nie zadziałają"
        )
        QTimer.singleShot(
            1500,
            lambda: QMessageBox.information(
                None,
                APP_NAME,
                tr(
                    "ChocPilot potrzebuje uprawnienia „Dostępność”, żeby wysyłać skróty "
                    "klawiszowe, wpisywać tekst i przełączać okna.\n\nUstawienia systemowe → "
                    "Prywatność i ochrona → Dostępność → włącz ChocPilot, a potem uruchom "
                    "aplikację ponownie."
                ),
            ),
        )

    controller.start()
    app.aboutToQuit.connect(controller.stop)
    code = app.exec()
    log.info("ChocPilot – koniec (kod %s)", code)
    return code


def tray_available() -> bool:
    from PySide6.QtWidgets import QSystemTrayIcon

    return QSystemTrayIcon.isSystemTrayAvailable()

"""Strona „Klipper”: drukarki (Moonraker), przełączanie trybu, klawisze, pokrętła i suwak.

Zmiany trafiają od razu do KlipperSettings (kontroler czyta je na bieżąco) i są zapisywane
z opóźnieniem jak reszta konfiguracji (sygnał changed).
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.config import (
    KLIPPER_COMMANDS,
    KLIPPER_PARAMS,
    KlipperKey,
    KlipperPrinter,
    KlipperSettings,
)
from ..core.moonraker import PrinterStatus
from ..core.protocol import KEY_COUNT
from . import theme
from .i18n import tr
from .widgets import button, frame, label

TOGGLE_CHOICES = (
    ("e2_hold", "Przytrzymanie przycisku pokrętła E2"),
    ("e1_hold", "Przytrzymanie przycisku pokrętła E1"),
    ("action", "Tylko akcja „Tryb Klipper” na klawiszu"),
)
SLIDER_CHOICES = (
    ("fan", "Wentylator chłodzenia 0–100 %"),
    ("speed", "Prędkość wydruku 50–150 %"),
    ("off", "Wyłączony"),
)
STATE_NAMES = {
    "printing": "drukuje",
    "paused": "wstrzymana",
    "complete": "wydruk zakończony",
    "cancelled": "wydruk anulowany",
    "standby": "gotowa",
    "ready": "gotowa",
    "error": "błąd",
    "shutdown": "zatrzymana (shutdown)",
    "startup": "uruchamianie",
    "offline": "brak połączenia",
}


def status_text(status: PrinterStatus | None) -> str:
    if status is None:
        return tr("Brak danych – włącz tryb Klipper albo przetestuj połączenie.")
    if not status.online:
        return f"{tr('Brak połączenia')}: {status.message}"
    state = tr(STATE_NAMES.get(status.state, status.state))
    if status.state in ("shutdown", "error", "startup"):
        return f"{state}. {status.message}".strip()
    parts = [state]
    if status.busy:
        parts.append(f"{status.progress * 100:.0f}% {status.filename}".strip())
    parts.append(
        f"{tr('dysza')} {status.nozzle:.0f}/{status.nozzle_target:.0f} °C, "
        f"{tr('stół')} {status.bed:.0f}/{status.bed_target:.0f} °C"
    )
    parts.append(
        f"{tr('prędkość')} {status.speed_factor * 100:.0f}%, "
        f"{tr('przepływ')} {status.flow_factor * 100:.0f}%, "
        f"{tr('wentylator')} {status.fan * 100:.0f}%"
    )
    return " · ".join(parts)


def _section(title: str, hint: str = "") -> tuple[QWidget, QVBoxLayout]:
    box = frame("card")
    v = QVBoxLayout(box)
    v.setContentsMargins(20, 16, 20, 18)
    v.setSpacing(10)
    v.addWidget(label(title, "h2"))
    if hint:
        v.addWidget(label(hint, "hint", wrap=True))
    return box, v


class KlipperPage(QWidget):
    changed = Signal()
    toggleRequested = Signal()
    testRequested = Signal(object)  # KlipperPrinter
    testFinished = Signal(object)  # PrinterStatus (emitowany z wątku kontrolera)

    def __init__(self, settings: KlipperSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._loading = False

        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(16)

        # --- nagłówek
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(label("Klipper", "h1"))
        titles.addWidget(
            label(
                tr(
                    "Sterowanie drukarkami 3D z Klipperem (przez Moonraker) z klawiszy, pokręteł "
                    "i suwaka ChocPilot."
                ),
                "hint",
                wrap=True,
            )
        )
        head.addLayout(titles, 1)
        self.toggle_button = button(tr("Włącz tryb Klipper"), primary=True)
        self.toggle_button.clicked.connect(self.toggleRequested.emit)
        head.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignBottom)
        v.addLayout(head)

        # --- drukarki
        box, bv = _section(
            tr("Drukarki"),
            tr(
                "Adres Moonrakera, np. http://voron.local albo 192.168.1.20:7125. Klucz API tylko, "
                "jeśli Moonraker go wymaga (Mainsail/Fluidd: Ustawienia → Klucz API)."
            ),
        )
        row = QHBoxLayout()
        self.printer_list = QListWidget()
        self.printer_list.setObjectName("boxed")
        self.printer_list.setMaximumHeight(130)
        self.printer_list.currentRowChanged.connect(self._printer_selected)
        row.addWidget(self.printer_list, 1)
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        self.p_name = QLineEdit()
        self.p_url = QLineEdit()
        self.p_url.setPlaceholderText("http://voron.local")
        self.p_key = QLineEdit()
        self.p_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.p_key.setPlaceholderText(tr("(opcjonalny)"))
        for r, (text, edit) in enumerate(
            ((tr("Nazwa"), self.p_name), (tr("Adres"), self.p_url), (tr("Klucz API"), self.p_key))
        ):
            form.addWidget(label(text, "lbl"), r, 0)
            form.addWidget(edit, r, 1)
            edit.editingFinished.connect(self._printer_edited)
        row.addLayout(form, 2)
        bv.addLayout(row)
        buttons = QHBoxLayout()
        add = button(tr("Dodaj drukarkę"))
        add.clicked.connect(self._add_printer)
        self.remove_button = button(tr("Usuń"))
        self.remove_button.clicked.connect(self._remove_printer)
        self.test_button = button(tr("Testuj połączenie"))
        self.test_button.clicked.connect(self._test)
        buttons.addWidget(add)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.test_button)
        buttons.addStretch(1)
        bv.addLayout(buttons)
        self.status_label = label(status_text(None), "muted", wrap=True)
        bv.addWidget(self.status_label)
        v.addWidget(box)
        self.testFinished.connect(self._test_done)

        # --- przełączanie trybu
        box, bv = _section(
            tr("Przełączanie trybu"),
            tr(
                "Przytrzymaj wybrany przycisk pokrętła, żeby wejść w tryb Klipper albo z niego "
                "wyjść – krótkie naciśnięcie działa jak zwykle. Akcję „Tryb Klipper” można też "
                "przypisać do dowolnego klawisza w profilu."
            ),
        )
        row = QHBoxLayout()
        self.toggle_combo = QComboBox()
        for key, text in TOGGLE_CHOICES:
            self.toggle_combo.addItem(tr(text), key)
        self.toggle_combo.currentIndexChanged.connect(self._edited)
        self.toggle_ms = self._spin(300, 3000, " ms")
        row.addWidget(self.toggle_combo, 2)
        row.addWidget(label(tr("Czas przytrzymania"), "lbl"))
        row.addWidget(self.toggle_ms)
        row.addStretch(1)
        bv.addLayout(row)
        v.addWidget(box)

        # --- klawisze
        box, bv = _section(
            tr("Klawisze w trybie Klipper"),
            tr(
                "Etykiety pojawiają się na ekranie urządzenia. „Przytrzymanie” chroni przed "
                "przypadkowym anulowaniem wydruku albo zatrzymaniem awaryjnym."
            ),
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        for c, text in enumerate(
            (
                "",
                tr("Etykieta"),
                tr("Ikona"),
                tr("Polecenie"),
                tr("G-code / makro"),
                tr("Przytrzymanie"),
            )
        ):
            grid.addWidget(label(text, "lbl"), 0, c)
        self.key_rows: dict[int, tuple[QLineEdit, QComboBox, QPlainTextEdit, QCheckBox]] = {}
        self.icon_buttons: dict[int, QPushButton] = {}
        self.key_icons: dict[int, str] = {}
        for k in range(1, KEY_COUNT + 1):
            name = QLineEdit()
            name.setMaxLength(10)
            command = QComboBox()
            for key, text in KLIPPER_COMMANDS.items():
                command.addItem(tr(text), key)
            gcode = QPlainTextEdit()
            gcode.setMaximumHeight(52)
            gcode.setPlaceholderText("G28")
            hold = QCheckBox()
            icon = QPushButton()
            icon.setFixedSize(40, 40)
            icon.setIconSize(QSize(26, 26))
            icon.setToolTip(tr("Ikona na ekranie zamiast etykiety"))
            icon.clicked.connect(lambda _=False, key=k: self._pick_icon(key))
            self.icon_buttons[k] = icon
            grid.addWidget(label(f"K{k}", "strong"), k, 0)
            grid.addWidget(name, k, 1)
            grid.addWidget(icon, k, 2)
            grid.addWidget(command, k, 3)
            grid.addWidget(gcode, k, 4)
            grid.addWidget(hold, k, 5, Qt.AlignmentFlag.AlignCenter)
            name.editingFinished.connect(self._edited)
            command.currentIndexChanged.connect(self._edited)
            gcode.textChanged.connect(self._edited)
            hold.toggled.connect(self._edited)
            self.key_rows[k] = (name, command, gcode, hold)
        grid.setColumnStretch(4, 1)
        bv.addLayout(grid)
        row = QHBoxLayout()
        row.addWidget(label(tr("Czas przytrzymania klawisza"), "lbl"))
        self.hold_ms = self._spin(300, 3000, " ms")
        row.addWidget(self.hold_ms)
        row.addStretch(1)
        bv.addLayout(row)
        v.addWidget(box)

        # --- pokrętła i suwak
        box, bv = _section(
            tr("Pokrętła i suwak"),
            tr(
                "E1 – ruch osi (naciśnięcie: X → Y → Z); podczas wydruku zmienia Z offset. "
                "E2 – nastawy (naciśnięcie: kolejny parametr z listy poniżej)."
            ),
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.jog_xy = self._dspin(0.01, 100, 2, " mm")
        self.jog_z = self._dspin(0.01, 50, 2, " mm")
        self.jog_feed = self._spin(60, 60000, " mm/min")
        self.babystep = self._dspin(0.005, 1, 3, " mm")
        self.temp_step = self._spin(1, 50, " °C")
        self.poll_s = self._dspin(0.5, 30, 1, " s")
        for r, (text, widget) in enumerate(
            (
                (tr("Krok X/Y na zatrzask"), self.jog_xy),
                (tr("Krok Z na zatrzask"), self.jog_z),
                (tr("Prędkość ruchu"), self.jog_feed),
                (tr("Z offset na zatrzask (wydruk)"), self.babystep),
                (tr("Krok temperatury"), self.temp_step),
                (tr("Odświeżanie stanu"), self.poll_s),
            )
        ):
            grid.addWidget(label(text, "lbl"), r // 2, (r % 2) * 2)
            grid.addWidget(widget, r // 2, (r % 2) * 2 + 1)
        bv.addLayout(grid)
        bv.addWidget(label(tr("Parametry pokrętła E2"), "lbl"))
        params_row = QHBoxLayout()
        self.param_checks: dict[str, QCheckBox] = {}
        for key, text in KLIPPER_PARAMS.items():
            check = QCheckBox(tr(text))
            check.toggled.connect(self._edited)
            self.param_checks[key] = check
            params_row.addWidget(check)
        params_row.addStretch(1)
        bv.addLayout(params_row)
        row = QHBoxLayout()
        row.addWidget(label(tr("Suwak"), "lbl"))
        self.slider_combo = QComboBox()
        for key, text in SLIDER_CHOICES:
            self.slider_combo.addItem(tr(text), key)
        self.slider_combo.currentIndexChanged.connect(self._edited)
        row.addWidget(self.slider_combo)
        row.addStretch(1)
        bv.addLayout(row)
        v.addWidget(box)
        v.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.load()

    # ------------------------------------------------------------------ pomocnicze

    def _spin(self, lo: int, hi: int, suffix: str) -> QSpinBox:
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setSuffix(suffix)
        s.valueChanged.connect(self._edited)
        return s

    def _dspin(self, lo: float, hi: float, decimals: int, suffix: str) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(decimals)
        s.setSingleStep(10**-decimals * (10 if decimals > 1 else 1))
        s.setSuffix(suffix)
        s.valueChanged.connect(self._edited)
        return s

    # ------------------------------------------------------------------ wczytanie / zapis

    def load(self) -> None:
        self._loading = True
        s = self.settings
        self._reload_printers()
        self.toggle_combo.setCurrentIndex(max(0, self.toggle_combo.findData(s.toggle)))
        self.toggle_ms.setValue(s.toggle_ms)
        self.hold_ms.setValue(s.hold_ms)
        for k, (name, command, gcode, hold) in self.key_rows.items():
            key = s.keys[k]
            name.setText(key.label)
            command.setCurrentIndex(max(0, command.findData(key.command)))
            gcode.setPlainText(key.gcode)
            gcode.setEnabled(key.command == "gcode")
            hold.setChecked(key.hold)
            self.key_icons[k] = key.icon
            self._show_icon(k)
        self.jog_xy.setValue(s.jog_xy)
        self.jog_z.setValue(s.jog_z)
        self.jog_feed.setValue(s.jog_feed)
        self.babystep.setValue(s.babystep)
        self.temp_step.setValue(s.temp_step)
        self.poll_s.setValue(s.poll_s)
        for param, check in self.param_checks.items():
            check.setChecked(param in s.params)
        self.slider_combo.setCurrentIndex(max(0, self.slider_combo.findData(s.slider)))
        self._loading = False

    def _edited(self, *_args: object) -> None:
        if self._loading:
            return
        s = self.settings
        s.toggle = self.toggle_combo.currentData()
        s.toggle_ms = self.toggle_ms.value()
        s.hold_ms = self.hold_ms.value()
        keys = {}
        for k, (name, command, gcode, hold) in self.key_rows.items():
            gcode.setEnabled(command.currentData() == "gcode")
            keys[k] = KlipperKey(
                label=name.text().strip(),
                command=command.currentData(),
                gcode=gcode.toPlainText().strip(),
                hold=hold.isChecked(),
                icon=self.key_icons.get(k, ""),
            )
        s.keys = keys
        s.jog_xy = self.jog_xy.value()
        s.jog_z = self.jog_z.value()
        s.jog_feed = self.jog_feed.value()
        s.babystep = self.babystep.value()
        s.temp_step = self.temp_step.value()
        s.poll_s = self.poll_s.value()
        params = [k for k, check in self.param_checks.items() if check.isChecked()]
        s.params = params or ["nozzle"]  # type: ignore[assignment]
        s.slider = self.slider_combo.currentData()
        self.changed.emit()

    # ------------------------------------------------------------------ ikony klawiszy

    def _show_icon(self, key: int) -> None:
        from .icon_library import library

        button_ = self.icon_buttons[key]
        icon_id = self.key_icons.get(key, "")
        lib = library()
        entry = lib.entry(icon_id) if icon_id else None
        if entry is None:
            button_.setIcon(QIcon())
            button_.setText("—")
            return
        image = lib.render(icon_id, 52, theme.tokens()["text"])
        button_.setText("")
        button_.setIcon(QIcon(QPixmap.fromImage(image)))
        button_.setToolTip(f"{entry.name} – {tr('kliknij, żeby zmienić')}")

    def _pick_icon(self, key: int) -> None:
        from .icon_picker import IconPickerDialog

        dialog = IconPickerDialog(self.key_icons.get(key, ""), self)
        if dialog.exec():
            self.key_icons[key] = dialog.selected
            self._show_icon(key)
            self._edited()

    # ------------------------------------------------------------------ drukarki

    def _reload_printers(self, select: int | None = None) -> None:
        self.printer_list.blockSignals(True)
        self.printer_list.clear()
        for p in self.settings.printers:
            self.printer_list.addItem(p.name or p.url or tr("(bez nazwy)"))
        self.printer_list.blockSignals(False)
        count = len(self.settings.printers)
        row = select if select is not None else min(self.settings.active_printer, count - 1)
        if count:
            self.printer_list.setCurrentRow(max(0, row))
        self._printer_selected(self.printer_list.currentRow())

    def _printer_selected(self, row: int) -> None:
        printers = self.settings.printers
        has = 0 <= row < len(printers)
        for w in (self.p_name, self.p_url, self.p_key, self.remove_button, self.test_button):
            w.setEnabled(has)
        p = printers[row] if has else KlipperPrinter(name="", url="")
        self.p_name.setText(p.name)
        self.p_url.setText(p.url)
        self.p_key.setText(p.api_key)

    def _printer_edited(self) -> None:
        row = self.printer_list.currentRow()
        if not 0 <= row < len(self.settings.printers):
            return
        printer = KlipperPrinter(
            name=self.p_name.text().strip() or tr("Drukarka"),
            url=self.p_url.text().strip(),
            api_key=self.p_key.text().strip(),
        )
        if printer == self.settings.printers[row]:
            return
        printers = list(self.settings.printers)
        printers[row] = printer
        self.settings.printers = printers
        self.printer_list.item(row).setText(printer.name)
        self.changed.emit()

    def _add_printer(self) -> None:
        n = len(self.settings.printers) + 1
        name = tr("Drukarka") if n == 1 else f"{tr('Drukarka')} {n}"
        self.settings.printers = [*self.settings.printers, KlipperPrinter(name=name)]
        self._reload_printers(select=n - 1)
        self.p_url.setFocus()
        self.changed.emit()

    def _remove_printer(self) -> None:
        row = self.printer_list.currentRow()
        if not 0 <= row < len(self.settings.printers):
            return
        printers = list(self.settings.printers)
        del printers[row]
        self.settings.printers = printers
        self.settings.active_printer = min(self.settings.active_printer, max(0, len(printers) - 1))
        self._reload_printers()
        self.changed.emit()

    def _test(self) -> None:
        self._printer_edited()
        row = self.printer_list.currentRow()
        if not 0 <= row < len(self.settings.printers):
            return
        self.status_label.setText(tr("Łączenie…"))
        self.test_button.setEnabled(False)
        self.testRequested.emit(self.settings.printers[row])

    def _test_done(self, status: PrinterStatus) -> None:
        self.test_button.setEnabled(True)
        self.status_label.setText(status_text(status))

    # ------------------------------------------------------------------ stan z kontrolera

    def set_state(self, active: bool, printer: str, status: PrinterStatus | None) -> None:
        self.toggle_button.setText(
            tr("Wyłącz tryb Klipper") if active else tr("Włącz tryb Klipper")
        )
        if active or status is not None:
            prefix = f"{printer}: " if printer else ""
            self.status_label.setText(prefix + status_text(status))


__all__ = ["KlipperPage", "status_text"]

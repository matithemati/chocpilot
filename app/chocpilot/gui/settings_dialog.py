"""Ustawienia: urządzenie, gesty, tryb awaryjny, aplikacja.

Klasa działa jako okno dialogowe albo – osadzona – jako strona okna głównego.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import osinfo
from ..core.actions import parse_hotkey
from ..core.config import FallbackEntry, LedSettings, Settings
from ..core.protocol import KEY_COUNT, LED_SPEED_MAX, LED_SPEED_MIN, MEDIA_KEYS
from .editors import LED_SWATCHES, ColorButton
from .i18n import tr
from .widgets import Segmented, Switch, button, frame, hline, label, styled

FALLBACK_SLOTS = [(str(i), f"K{i}") for i in range(1, KEY_COUNT + 1)]
# Nazwy wbudowanych animacji wygaszacza; nieznane (np. z nowszego firmware) – nazwa z urządzenia.
SAVER_LABELS = {"off": "Wygaszony ekran", "rabbit": "Królik", "corgi": "Corgi"}


def saver_label(name: str) -> str:
    return tr(SAVER_LABELS[name]) if name in SAVER_LABELS else name.replace("_", " ").capitalize()


TABS = (
    ("device", "Urządzenie"),
    ("leds", "Podświetlenie"),
    ("gestures", "Gesty"),
    ("fallback", "Tryb awaryjny"),
    ("app", "Aplikacja"),
)


def _spin(lo: int, hi: int, value: int, suffix: str = "") -> QSpinBox:
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(value)
    s.setMinimumWidth(140)
    if suffix:
        s.setSuffix(suffix)
    return s


def _row(title: str, hint: str, control: QWidget | None) -> QWidget:
    """Wiersz ustawienia: tytuł i opis po lewej, kontrolka po prawej."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 14, 0, 14)
    h.setSpacing(24)
    text = QVBoxLayout()
    text.setSpacing(2)
    text.addWidget(label(title, "strong", wrap=True))
    if hint:
        text.addWidget(label(hint, "hint", wrap=True))
    h.addLayout(text, 1)
    if control is not None:
        control.setMaximumWidth(360)
        h.addWidget(control, 1)
    return row


def _page(rows: list[QWidget]) -> QWidget:
    page = QWidget()
    v = QVBoxLayout(page)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    for i, r in enumerate(rows):
        if i:
            v.addWidget(hline())
        v.addWidget(r)
    v.addStretch(1)
    return page


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        list_ports: Callable[[], list[tuple[str, str]]],
        on_device_action: Callable[[str], None],
        parent: QWidget | None = None,
        on_leds_preview: Callable[[LedSettings], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Ustawienia – ChocPilot"))
        self.settings = settings
        self.resize(900, 620)
        self.device_changed = False
        self.port_changed = False
        self.language_changed = False

        self.pages = QStackedWidget()
        nav = QVBoxLayout()
        nav.setSpacing(2)
        self.tab_group = QButtonGroup(self)
        self.tab_buttons: dict[str, QPushButton] = {}

        # --- urządzenie
        d = settings.device
        self.port = QComboBox()
        self.port.addItem(tr("Automatycznie (wykryj ChocPilot)"), "auto")
        for device, description in list_ports():
            self.port.addItem(f"{device} – {description}", device)
        index = self.port.findData(d.port)
        if index < 0:
            self.port.addItem(d.port, d.port)
            index = self.port.count() - 1
        self.port.setCurrentIndex(index)
        self.brightness = QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(0, 255)
        self.brightness.setValue(d.brightness)
        brightness_value = label(str(d.brightness), "muted")
        brightness_value.setMinimumWidth(30)
        self.brightness.valueChanged.connect(lambda v: brightness_value.setText(str(v)))
        brightness_box = QWidget()
        bb = QHBoxLayout(brightness_box)
        bb.setContentsMargins(0, 0, 0, 0)
        bb.addWidget(self.brightness, 1)
        bb.addWidget(brightness_value)
        self.screensaver = _spin(0, 65535, d.screensaver_s, " s")
        self.screensaver.setSpecialValueText(tr("wyłączony"))
        # Animacja wygaszacza – lista z urządzenia (hello: savers), tylko płytki z LCD.
        self.saver = QComboBox()
        for name in ["off", *d.savers_available]:
            self.saver.addItem(saver_label(name), name)
        if self.saver.findData(d.saver) < 0:  # animacja z innej płytki – zostaje zapisana
            self.saver.addItem(saver_label(d.saver), d.saver)
        self.saver.setCurrentIndex(max(0, self.saver.findData(d.saver)))
        self.display_mode = QComboBox()
        self.display_mode.addItem(tr("Siatka etykiet 2×4"), "grid")
        self.display_mode.addItem(tr("Duża nazwa profilu"), "profile")
        self.display_mode.setCurrentIndex(max(0, self.display_mode.findData(d.display_mode)))
        self.flip = Switch()
        self.flip.setChecked(d.flip)
        self.debounce = _spin(1, 50, d.debounce_ms, " ms")
        actions = QWidget()
        ah = QHBoxLayout(actions)
        ah.setContentsMargins(0, 0, 0, 0)
        ah.setSpacing(6)
        for text, key in (
            ("Tryb testu sprzętu", "test"),
            ("Restart urządzenia", "reboot"),
            ("Tryb wgrywania firmware", "bootloader"),
        ):
            b = QPushButton(tr(text))
            b.clicked.connect(lambda _=False, k=key: on_device_action(k))
            ah.addWidget(b)
        device_page = _page(
            [
                _row(tr("Port"), tr("Port szeregowy ChocPilot"), self.port),
                _row(tr("Jasność ekranu"), "0–255", brightness_box),
                _row(tr("Wygaszacz po"), tr("0 = wyłączony"), self.screensaver),
                self._saver_row(),
                _row(tr("Tryb ekranu"), "", self.display_mode),
                _row(tr("Obróć ekran o 180°"), "", self.flip),
                _row(tr("Debounce klawiszy"), "1–50 ms", self.debounce),
            ]
        )
        device_page.layout().insertWidget(device_page.layout().count() - 1, hline())
        device_page.layout().insertWidget(
            device_page.layout().count() - 1, _row(tr("Akcje urządzenia"), "", None)
        )
        device_page.layout().insertWidget(device_page.layout().count() - 1, actions)

        # --- podświetlenie LED (płytki z diodami, np. ChocPilot v0)
        self._leds_preview = on_leds_preview
        self.leds_previewed = False
        led = d.leds
        self.led_mode = QComboBox()
        for key, text in (
            ("status", "Stan połączenia (turkus / bursztyn)"),
            ("static", "Stały kolor"),
            ("breathe", "Oddychanie"),
            ("rainbow", "Tęcza"),
            ("off", "Wyłączone"),
        ):
            self.led_mode.addItem(tr(text), key)
        self.led_mode.setCurrentIndex(max(0, self.led_mode.findData(led.mode)))
        self.led_color = ColorButton(swatches=LED_SWATCHES, title="", dialog_title=tr("Kolor LED"))
        self.led_color.set_color(led.color)
        self.led_brightness = QSlider(Qt.Orientation.Horizontal)
        self.led_brightness.setRange(0, 255)
        self.led_brightness.setValue(led.brightness)
        led_brightness_value = label(str(led.brightness), "muted")
        led_brightness_value.setMinimumWidth(30)
        self.led_brightness.valueChanged.connect(lambda v: led_brightness_value.setText(str(v)))
        led_brightness_box = QWidget()
        lbb = QHBoxLayout(led_brightness_box)
        lbb.setContentsMargins(0, 0, 0, 0)
        lbb.addWidget(self.led_brightness, 1)
        lbb.addWidget(led_brightness_value)
        self.led_speed = QSlider(Qt.Orientation.Horizontal)
        self.led_speed.setRange(LED_SPEED_MIN, LED_SPEED_MAX)
        self.led_speed.setValue(led.speed)
        self.led_react = Switch(tr("Błysk diody przy naciśniętym klawiszu"))
        self.led_react.setChecked(led.react)
        leds_page = _page(
            [
                _row(
                    tr("Efekt"),
                    tr("Działa też bez aplikacji (zapisany w urządzeniu)"),
                    self.led_mode,
                ),
                _row(
                    tr("Kolor"),
                    tr("Tryby stały i oddychanie; profil może mieć własny"),
                    self.led_color,
                ),
                _row(
                    tr("Jasność LED"),
                    tr("0–255; ograniczona w urządzeniu do bezpiecznego prądu USB"),
                    led_brightness_box,
                ),
                _row(tr("Tempo"), tr("Oddychanie i tęcza: 1 = wolno, 10 = szybko"), self.led_speed),
                self._wrap(self.led_react),
            ]
        )
        self.led_mode.currentIndexChanged.connect(self._leds_changed)
        self.led_color.changed.connect(self._leds_changed)
        self.led_brightness.valueChanged.connect(self._leds_changed)
        self.led_speed.valueChanged.connect(self._leds_changed)
        self.led_react.toggled.connect(self._leds_changed)
        self._update_led_controls()

        # --- gesty
        g = settings.gestures
        self.hold_ms = _spin(100, 5000, g.hold_ms, " ms")
        self.double_ms = _spin(100, 2000, g.double_tap_ms, " ms")
        self.hold_threshold = Switch(tr("Wykonuj „przytrzymanie” od razu po przekroczeniu progu"))
        self.hold_threshold.setChecked(g.hold_on_threshold)
        note = frame("soft")
        nl = QVBoxLayout(note)
        nl.setContentsMargins(14, 10, 14, 10)
        nl.addWidget(
            label(
                tr(
                    "Jeśli klawisz nie ma akcji „podwójne”, zwykłe naciśnięcie wykonuje się "
                    "od razu po puszczeniu. W przeciwnym razie czeka na upływ okna."
                ),
                "hint",
                wrap=True,
            )
        )
        gestures_page = _page(
            [
                _row(tr("Próg przytrzymania"), "100–5000 ms", self.hold_ms),
                _row(tr("Okno podwójnego naciśnięcia"), "100–2000 ms", self.double_ms),
                self._wrap(self.hold_threshold),
            ]
        )
        gestures_page.layout().insertWidget(gestures_page.layout().count() - 1, note)

        # --- tryb awaryjny
        fb = settings.fallback
        fall = QWidget()
        v = QVBoxLayout(fall)
        v.setContentsMargins(0, 16, 0, 0)
        v.setSpacing(12)
        info = label(
            tr(
                "Gdy aplikacja nie działa (brak sygnału przez 3 s), ChocPilot sam wysyła skróty "
                "klawiaturowe/multimedialne przez USB HID. Domyślnie są wyliczane z aktywnego "
                "profilu (akcje typu skrót i multimedia), a poniższe wpisy je nadpisują."
            ),
            "hint",
            wrap=True,
        )
        self.fallback_from_profile = Switch(tr("Wyliczaj skróty z aktywnego profilu"))
        self.fallback_from_profile.setChecked(fb.from_profile)
        self.fallback_table = QTableWidget(len(FALLBACK_SLOTS), 3)
        self.fallback_table.setHorizontalHeaderLabels(
            [tr("Element"), tr("Skrót (np. ctrl+c)"), tr("Multimedia")]
        )
        self.fallback_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fallback_table.verticalHeader().hide()
        self.fallback_table.setShowGrid(False)
        self.fallback_table.verticalHeader().setDefaultSectionSize(44)
        custom: dict[str, FallbackEntry] = {c.slot: c for c in fb.custom}
        self._media_combos: list[QComboBox] = []
        self._hotkey_edits: list[QLineEdit] = []
        for row, (slot, slot_label) in enumerate(FALLBACK_SLOTS):
            item = QTableWidgetItem(tr(slot_label))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.fallback_table.setItem(row, 0, item)
            entry = custom.get(slot)
            edit = QLineEdit(
                "+".join([*(entry.mods if entry else []), entry.code or ""]).strip("+")
                if entry and not entry.media
                else ""
            )
            edit.setPlaceholderText(tr("(z profilu)"))
            combo = QComboBox()
            combo.addItem("—", None)
            for media in MEDIA_KEYS:
                combo.addItem(media, media)
            combo.setCurrentIndex(max(0, combo.findData(entry.media if entry else None)))
            self.fallback_table.setCellWidget(row, 1, edit)
            self.fallback_table.setCellWidget(row, 2, combo)
            self._hotkey_edits.append(edit)
            self._media_combos.append(combo)
        self.fallback_error = label("", "error", wrap=True)
        v.addWidget(info)
        v.addWidget(self.fallback_from_profile)
        v.addWidget(self.fallback_table, 1)
        v.addWidget(self.fallback_error)

        # --- aplikacja
        a = settings.app
        self.language = Segmented([("pl", "Polski"), ("en", "English")])
        self.language.set_value(a.language)
        self.theme = QComboBox()
        for key, text in (("system", "Według systemu"), ("light", "Jasny"), ("dark", "Ciemny")):
            self.theme.addItem(tr(text), key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(a.theme)))
        self.autostart = Switch(
            tr("Uruchamiaj z systemem Windows")
            if osinfo.current_os() == "windows"
            else tr("Uruchamiaj po zalogowaniu")
        )
        self.autostart.setChecked(a.autostart)
        self.minimized = Switch(tr("Startuj zminimalizowana do zasobnika"))
        self.minimized.setChecked(a.start_minimized)
        self.flash = Switch(tr("Pokazuj etykietę na ekranie po wykonaniu akcji"))
        self.flash.setChecked(a.flash_on_action)
        self.auto_switch = Switch(tr("Automatycznie przełączaj profile według aktywnego okna"))
        self.auto_switch.setChecked(a.auto_switch)
        lang_box = QWidget()
        lb = QHBoxLayout(lang_box)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.addWidget(self.language)
        lb.addStretch(1)
        app_page = _page(
            [
                _row(tr("Język"), tr("Język interfejsu aplikacji"), lang_box),
                _row(tr("Motyw"), "", self.theme),
                self._wrap(self.autostart),
                self._wrap(self.minimized),
                self._wrap(self.flash),
                self._wrap(self.auto_switch),
            ]
        )

        for key, text in TABS:
            b = QPushButton(tr(text))
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            styled(b, stab=True)
            self.tab_group.addButton(b)
            self.tab_buttons[key] = b
            nav.addWidget(b)
        nav.addStretch(1)
        for key, page in zip(
            [k for k, _ in TABS],
            [device_page, leds_page, gestures_page, fall, app_page],
            strict=True,
        ):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(page)
            self.pages.addWidget(scroll)
            self.tab_buttons[key].clicked.connect(
                lambda _=False, w=scroll: self.pages.setCurrentWidget(w)
            )
        # Zakładka LED tylko dla płytek z diodami (ustawiane po pierwszym podłączeniu).
        self.tab_buttons["leds"].setVisible(d.leds_available)
        self.show_tab("device")

        # --- układ: nagłówek, karta z nawigacją i treścią
        self.cancel_button = button(tr("Anuluj"))
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = button(tr("Zapisz"), primary=True)
        self.save_button.clicked.connect(self._accept)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        self.title = label(tr("Ustawienia"), "h1")
        titles.addWidget(self.title)
        titles.addWidget(label(tr("Urządzenie, gesty, tryb awaryjny i aplikacja."), "hint"))
        head.addLayout(titles, 1)
        head.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignBottom)
        head.addWidget(self.save_button, 0, Qt.AlignmentFlag.AlignBottom)

        card = frame("card")
        ch = QHBoxLayout(card)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(0)
        nav_host = QWidget()
        nav_host.setLayout(nav)
        nav.setContentsMargins(12, 12, 12, 12)
        nav_host.setFixedWidth(220)
        ch.addWidget(nav_host)
        divider = frame("hline")
        divider.setFixedWidth(1)
        divider.setMaximumHeight(16777215)
        ch.addWidget(divider)
        content = QVBoxLayout()
        content.setContentsMargins(28, 8, 28, 20)
        content.addWidget(self.pages)
        ch.addLayout(content, 1)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addLayout(head)
        layout.addWidget(card, 1)

    def _saver_row(self) -> QWidget:
        row = _row(
            tr("Animacja wygaszacza"),
            tr("Co pokazuje ekran LCD, gdy włączy się wygaszacz"),
            self.saver,
        )
        row.setVisible(bool(self.settings.device.savers_available))
        self.saver_row = row
        return row

    @staticmethod
    def _wrap(widget: QWidget) -> QWidget:
        host = QWidget()
        h = QHBoxLayout(host)
        h.setContentsMargins(0, 14, 0, 14)
        h.addWidget(widget)
        h.addStretch(1)
        return host

    def show_tab(self, key: str) -> None:
        self.tab_buttons[key].setChecked(True)
        self.pages.setCurrentIndex([k for k, _ in TABS].index(key))

    def led_settings(self) -> LedSettings:
        return LedSettings(
            mode=self.led_mode.currentData(),
            color=self.led_color.color(),
            brightness=self.led_brightness.value(),
            speed=self.led_speed.value(),
            react=self.led_react.isChecked(),
        )

    def _update_led_controls(self) -> None:
        mode = self.led_mode.currentData()
        self.led_color.setEnabled(mode in ("static", "breathe"))
        self.led_speed.setEnabled(mode in ("breathe", "rainbow"))
        self.led_brightness.setEnabled(mode != "off")

    def _leds_changed(self, *_args: object) -> None:
        self._update_led_controls()
        if self._leds_preview is not None:
            self._leds_preview(self.led_settings())
            self.leds_previewed = True

    def embed(self) -> None:
        """Tryb strony okna głównego (bez ramki i tytułu okna)."""
        self.setWindowFlags(Qt.WindowType.Widget)
        self.layout().setContentsMargins(0, 0, 0, 0)

    def _fallback_entries(self) -> list[FallbackEntry] | None:
        entries = []
        for (slot, slot_label), edit, combo in zip(
            FALLBACK_SLOTS, self._hotkey_edits, self._media_combos, strict=True
        ):
            media = combo.currentData()
            text = edit.text().strip()
            if media:
                entries.append(FallbackEntry(slot=slot, media=media))  # type: ignore[arg-type]
            elif text:
                try:
                    keys = parse_hotkey(text)
                except ValueError as exc:
                    self.fallback_error.setText(f"{tr(slot_label)}: {exc}")
                    self.show_tab("fallback")
                    return None
                mods = [k for k in keys if k in ("ctrl", "shift", "alt", "win")]
                rest = [k for k in keys if k not in mods]
                if len(rest) > 1:
                    self.fallback_error.setText(
                        f"{tr(slot_label)}: {tr('tylko jeden klawisz poza modyfikatorami')}"
                    )
                    self.show_tab("fallback")
                    return None
                entries.append(FallbackEntry(slot=slot, mods=mods, code=rest[0] if rest else None))  # type: ignore[arg-type]
        return entries

    def _accept(self) -> None:
        entries = self._fallback_entries()
        if entries is None:
            return
        s = self.settings
        d = s.device
        before = d.model_dump()
        old_port = d.port
        d.port = self.port.currentData()
        d.brightness = self.brightness.value()
        d.screensaver_s = self.screensaver.value()
        d.saver = self.saver.currentData()
        d.display_mode = self.display_mode.currentData()
        d.flip = self.flip.isChecked()
        d.debounce_ms = self.debounce.value()
        d.leds = self.led_settings()
        self.device_changed = d.model_dump() != before
        self.port_changed = d.port != old_port

        s.gestures.hold_ms = self.hold_ms.value()
        s.gestures.double_tap_ms = self.double_ms.value()
        s.gestures.hold_on_threshold = self.hold_threshold.isChecked()
        s.fallback.from_profile = self.fallback_from_profile.isChecked()
        s.fallback.custom = entries
        s.app.autostart = self.autostart.isChecked()
        s.app.start_minimized = self.minimized.isChecked()
        s.app.flash_on_action = self.flash.isChecked()
        s.app.auto_switch = self.auto_switch.isChecked()
        s.app.theme = self.theme.currentData()
        language = self.language.value() or s.app.language
        self.language_changed = language != s.app.language
        s.app.language = language
        self.accept()

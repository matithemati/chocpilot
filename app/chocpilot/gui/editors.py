"""Panele edycji: klawisz, profil."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import osinfo
from ..core.config import EncoderBinding, KeyBinding, Profile, SliderBinding
from ..core.protocol import LABEL_CHARS, transliterate
from . import theme
from .action_editor import ActionEditor, EditorContext
from .i18n import tr
from .widgets import Segmented, Switch, button, combo, frame, hline, label, styled

GESTURE_TABS = (("tap", "Naciśnięcie"), ("hold", "Przytrzymanie"), ("double_tap", "Podwójne"))
ENCODER_TABS = (("cw", "W prawo"), ("ccw", "W lewo"), ("press", "Naciśnięcie"))
SLIDER_TARGETS = (
    ("off", "Wyłączony"),
    ("system_volume", "Głośność systemu"),
    ("app_volume", "Głośność programu"),
)

SWATCHES = (
    "#2e7d32",
    "#1565c0",
    "#ef6c00",
    "#6a1b9a",
    "#37474f",
    "#c62828",
    "#00838f",
    "#4527a0",
    "#ad1457",
    "#455a64",
)
# Jaskrawe kolory podświetlenia LED (ciemne kolory klawiszy na diodach wyglądają jak zgaszone).
LED_SWATCHES = (
    "#00a0c0",
    "#00e676",
    "#2979ff",
    "#d500f9",
    "#ff1744",
    "#ff9100",
    "#ffea00",
    "#ffffff",
)


def inspector_header(
    kicker: str, title: QLabel, badge: QLabel | None = None
) -> tuple[QHBoxLayout, QPushButton]:
    """Nagłówek panelu: znaczek, nadtytuł, tytuł i przycisk zamknięcia."""
    row = QHBoxLayout()
    row.setSpacing(10)
    if badge is not None:
        row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
    col = QVBoxLayout()
    col.setSpacing(0)
    col.addWidget(label(kicker.upper(), "kicker"))
    col.addWidget(title)
    row.addLayout(col, 1)
    close = button("", "x", ghost=True)
    close.setToolTip(tr("Zamknij"))
    close.setFixedSize(32, 32)
    row.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
    return row, close


def _badge_style(badge: QLabel, color: str) -> None:
    c = QColor(color)
    # ciemne kolory klawiszy byłyby nieczytelne na ciemnym tle
    text = theme.tokens()["text"] if theme.is_dark() and c.lightness() < 110 else color
    badge.setStyleSheet(
        f"background: rgba({c.red()},{c.green()},{c.blue()},60); color: {text}; "
        "border-radius: 11px; font-weight: 700;"
    )


class LabelEdit(QWidget):
    """Etykieta z licznikiem znaków (OLED: 7 znaków) i podglądem tekstu na ekranie."""

    changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setMaxLength(LABEL_CHARS)
        self.edit.setPlaceholderText(tr("np. Spotify"))
        self.counter = label("", "muted")
        self.preview = label("", "oledPreview")
        head = QHBoxLayout()
        head.addWidget(label(tr("Etykieta"), "lbl"))
        head.addStretch(1)
        head.addWidget(self.counter)
        foot = QHBoxLayout()
        foot.setSpacing(8)
        foot.addWidget(label(tr("Na ekranie:"), "muted"))
        foot.addWidget(self.preview)
        foot.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(head)
        layout.addWidget(self.edit)
        layout.addLayout(foot)
        self.edit.textChanged.connect(self._changed)
        self._changed(self.edit.text(), emit=False)

    def set_text(self, text: str) -> None:
        self.edit.blockSignals(True)
        self.edit.setText(text)
        self.edit.blockSignals(False)
        self._changed(text, emit=False)

    def _changed(self, text: str, emit: bool = True) -> None:
        self.counter.setText(f"{len(text)}/{LABEL_CHARS}")
        self.preview.setText(transliterate(text) or "—")
        if emit:
            self.changed.emit(text)


class ColorButton(QWidget):
    """Paleta kolorów (domyślnie kolory klawiszy) + kolor własny."""

    changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        swatches: tuple[str, ...] = SWATCHES,
        title: str | None = None,
        dialog_title: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._color = swatches[-1] if swatches is SWATCHES else swatches[0]
        self._dialog_title = dialog_title or tr("Kolor klawisza")
        self._swatches: dict[str, QPushButton] = {}
        row = QHBoxLayout()
        row.setSpacing(5)
        for c in swatches:
            b = QPushButton()
            b.setFixedSize(24, 24)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(c)
            b.clicked.connect(lambda _=False, col=c: self._set(col))
            self._swatches[c] = b
            row.addWidget(b)
        self.custom = QPushButton(tr("Własny…"))
        self.custom.clicked.connect(self._pick)
        row.addWidget(self.custom)
        row.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        if title != "":
            layout.addWidget(label(title or tr("Kolor"), "lbl"))
        layout.addLayout(row)
        self._refresh()

    def set_color(self, color: str) -> None:
        self._color = color
        self._refresh()

    def color(self) -> str:
        return self._color

    def _refresh(self) -> None:
        ring = theme.tokens()["text"]
        for c, b in self._swatches.items():
            selected = c.lower() == self._color.lower()
            b.setStyleSheet(
                f"QPushButton {{ background: {c}; border-radius: 7px; padding: 0; min-height: 0;"
                f" border: 2px solid {ring if selected else 'transparent'}; }}"
            )
        custom = self._color.lower() not in self._swatches
        self.custom.setStyleSheet(
            f"QPushButton {{ border: 2px solid {self._color}; }}" if custom else ""
        )

    def _set(self, color: str) -> None:
        self._color = color
        self._refresh()
        self.changed.emit(color)

    def _pick(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, self._dialog_title)
        if color.isValid():
            self._set(color.name())


class KeyEditor(QWidget):
    """Etykieta, kolor i akcje gestów tap / hold / double_tap jednego klawisza."""

    changed = Signal()
    closeRequested = Signal()

    def __init__(self, context: EditorContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.binding: KeyBinding | None = None
        self.title = label("", "h2")
        self.badge = label("", "badge")
        self.badge.setFixedSize(40, 40)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header = QWidget()
        head, close = inspector_header(tr("Klawisz"), self.title, self.badge)
        head.setContentsMargins(0, 0, 0, 0)
        self.header.setLayout(head)
        close.clicked.connect(self.closeRequested)

        self.label = LabelEdit()
        self.color = ColorButton()
        self.label.changed.connect(self._label_changed)
        self.color.changed.connect(self._color_changed)

        # Ikona zamiast etykiety na ekranie LCD.
        self.icon_box = QWidget()
        ib = QVBoxLayout(self.icon_box)
        ib.setContentsMargins(0, 0, 0, 0)
        ib.setSpacing(6)
        ib.addWidget(label(tr("Ikona na ekranie (zamiast etykiety)"), "lbl"))
        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(44, 44)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setObjectName("iconPreview")
        self.icon_name = label("", "muted")
        self.icon_pick = QPushButton(tr("Wybierz ikonę…"))
        self.icon_pick.clicked.connect(self._pick_icon)
        self.icon_clear = QPushButton(tr("Usuń ikonę"))
        self.icon_clear.clicked.connect(lambda: self._set_icon(""))
        icon_row.addWidget(self.icon_preview)
        icon_row.addWidget(self.icon_name, 1)
        icon_row.addWidget(self.icon_pick)
        icon_row.addWidget(self.icon_clear)
        ib.addLayout(icon_row)

        self.gesture_bar = Segmented([(g, tr(t)) for g, t in GESTURE_TABS])
        self.gesture_bar.changed.connect(self._show_gesture)
        self.gesture_stack = QStackedWidget()
        self.editors: dict[str, ActionEditor] = {}
        for gesture, _title in GESTURE_TABS:
            editor = ActionEditor(context)
            editor.changed.connect(lambda g=gesture: self._action_changed(g))
            self.editors[gesture] = editor
            self.gesture_stack.addWidget(editor)
        self.gesture_bar.set_value("tap")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self.header)
        layout.addWidget(self.label)
        layout.addWidget(self.icon_box)
        layout.addWidget(self.color)
        layout.addWidget(self.gesture_bar, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(hline())
        layout.addWidget(self.gesture_stack, 1)

    def bind(self, key: int, binding: KeyBinding) -> None:
        self.binding = binding
        self.title.setText(f"{tr('Klawisz')} K{key}")
        self.badge.setText(f"K{key}")
        self.label.set_text(binding.label)
        self.color.set_color(binding.color)
        _badge_style(self.badge, binding.color)
        self._show_icon(binding.icon)
        for gesture, editor in self.editors.items():
            editor.set_action(binding.action_for(gesture))
        self._update_tab_titles()

    def _show_gesture(self, gesture: str) -> None:
        self.gesture_stack.setCurrentWidget(self.editors[gesture])

    def _update_tab_titles(self) -> None:
        if self.binding is None:
            return
        for gesture, title in GESTURE_TABS:
            mark = "  ●" if self.binding.action_for(gesture) else ""
            self.gesture_bar.set_text(gesture, tr(title) + mark)

    def _label_changed(self, text: str) -> None:
        if self.binding is not None:
            self.binding.label = text
            self.changed.emit()

    def _show_icon(self, icon_id: str) -> None:
        from .icon_library import library

        lib = library()
        entry = lib.entry(icon_id) if icon_id else None
        if entry is None:
            self.icon_preview.clear()
            self.icon_name.setText(tr("Brak – na ekranie etykieta"))
        else:
            image = lib.render(icon_id, 40, theme.tokens()["text"])
            self.icon_preview.setPixmap(QPixmap.fromImage(image))
            self.icon_name.setText(entry.name)
        self.icon_clear.setEnabled(entry is not None)

    def _pick_icon(self) -> None:
        from .icon_picker import IconPickerDialog

        if self.binding is None:
            return
        dialog = IconPickerDialog(self.binding.icon, self)
        if dialog.exec():
            self._set_icon(dialog.selected)

    def _set_icon(self, icon_id: str) -> None:
        if self.binding is None:
            return
        self.binding.icon = icon_id
        self._show_icon(icon_id)
        self.changed.emit()

    def _color_changed(self, color: str) -> None:
        if self.binding is not None:
            self.binding.color = color
            _badge_style(self.badge, color)
            self.changed.emit()

    def _action_changed(self, gesture: str) -> None:
        if self.binding is not None:
            self.binding.set_action(gesture, self.editors[gesture].action())
            self._update_tab_titles()
            self.changed.emit()


class _NameEdit(QWidget):
    """Nazwa pokrętła / suwaka (tylko w aplikacji – ekran urządzenia jej nie pokazuje)."""

    changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.edit = QLineEdit()
        self.edit.setMaxLength(24)
        self.edit.setPlaceholderText(tr("np. Głośność"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(label(tr("Nazwa"), "lbl"))
        layout.addWidget(self.edit)
        self.edit.textChanged.connect(self.changed)

    def set_text(self, text: str) -> None:
        self.edit.blockSignals(True)
        self.edit.setText(text)
        self.edit.blockSignals(False)


class EncoderEditor(QWidget):
    """Akcje pokrętła: obrót w prawo, w lewo (× liczba zatrzasków) i naciśnięcie."""

    changed = Signal()
    closeRequested = Signal()

    def __init__(self, context: EditorContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.binding: EncoderBinding | None = None
        self.title = label("", "h2")
        self.badge = label("", "badge")
        self.badge.setFixedSize(40, 40)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header = QWidget()
        head, close = inspector_header(tr("Pokrętło"), self.title, self.badge)
        head.setContentsMargins(0, 0, 0, 0)
        header.setLayout(head)
        close.clicked.connect(self.closeRequested)

        self.name = _NameEdit()
        self.name.changed.connect(self._name_changed)
        hint = label(
            tr(
                "Obrót o kilka zatrzasków naraz: głośność i przewijanie mnożą krok, "
                "pozostałe akcje wykonują się raz na każdy zatrzask."
            ),
            "hint",
            wrap=True,
        )
        self.bar = Segmented([(g, tr(t)) for g, t in ENCODER_TABS])
        self.bar.changed.connect(self._show)
        self.stack = QStackedWidget()
        self.editors: dict[str, ActionEditor] = {}
        for gesture, _title in ENCODER_TABS:
            editor = ActionEditor(context)
            editor.changed.connect(lambda g=gesture: self._action_changed(g))
            self.editors[gesture] = editor
            self.stack.addWidget(editor)
        self.bar.set_value("cw")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(header)
        layout.addWidget(self.name)
        layout.addWidget(hint)
        layout.addWidget(self.bar, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(hline())
        layout.addWidget(self.stack, 1)

    def bind(self, index: int, binding: EncoderBinding) -> None:
        self.binding = binding
        self.title.setText(f"{tr('Pokrętło')} E{index}")
        self.badge.setText(f"E{index}")
        _badge_style(self.badge, theme.tokens()["accent"])
        self.name.set_text(binding.label)
        for gesture, editor in self.editors.items():
            editor.set_action(binding.action_for(gesture))
        self._update_tab_titles()

    def _show(self, gesture: str) -> None:
        self.stack.setCurrentWidget(self.editors[gesture])

    def _update_tab_titles(self) -> None:
        if self.binding is None:
            return
        for gesture, title in ENCODER_TABS:
            mark = "  ●" if self.binding.action_for(gesture) else ""
            self.bar.set_text(gesture, tr(title) + mark)

    def _name_changed(self, text: str) -> None:
        if self.binding is not None:
            self.binding.label = text
            self.changed.emit()

    def _action_changed(self, gesture: str) -> None:
        if self.binding is not None:
            self.binding.set_action(gesture, self.editors[gesture].action())
            self._update_tab_titles()
            self.changed.emit()


class SliderEditor(QWidget):
    """Suwak: położenie 0–100 % ustawia głośność systemu albo wybranego programu."""

    changed = Signal()
    closeRequested = Signal()

    def __init__(self, context: EditorContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.binding: SliderBinding | None = None
        self._audio = context.audio_processes
        badge = label("S", "badge")
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _badge_style(badge, theme.tokens()["accent"])
        header = QWidget()
        head, close = inspector_header(tr("Suwak"), label(tr("Suwak 45 mm"), "h2"), badge)
        head.setContentsMargins(0, 0, 0, 0)
        header.setLayout(head)
        close.clicked.connect(self.closeRequested)

        self.name = _NameEdit()
        self.name.changed.connect(self._name_changed)
        self.target = Segmented([(t, tr(text)) for t, text in SLIDER_TARGETS])
        self.target.changed.connect(self._target_changed)

        self.process_box = QWidget()
        self.process = combo()
        self.process.setEditable(True)
        process_edit = self.process.lineEdit()
        if process_edit is not None:
            process_edit.setPlaceholderText(
                tr("np. {name}").format(name=osinfo.example_process("audio"))
            )
        self.process.currentTextChanged.connect(self._process_changed)
        refresh = button("", "refresh")
        refresh.setToolTip(tr("Odśwież listę programów odtwarzających dźwięk"))
        refresh.setFixedWidth(36)
        refresh.clicked.connect(self._refresh_audio)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self.process, 1)
        row.addWidget(refresh)
        pl = QVBoxLayout(self.process_box)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addWidget(label(tr("Program"), "lbl"))
        pl.addLayout(row)

        hint = label(
            tr(
                "Dół suwaka = 0 %, góra = 100 %. Przy zmianie położenia ekran urządzenia "
                "pokazuje pasek głośności."
            ),
            "hint",
            wrap=True,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(header)
        layout.addWidget(self.name)
        layout.addWidget(label(tr("Działanie"), "lbl"))
        layout.addWidget(self.target, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.process_box)
        layout.addWidget(hint)
        layout.addStretch(1)

    def bind(self, binding: SliderBinding) -> None:
        self.binding = None  # bez zapisywania zmian z ustawiania pól
        self.name.set_text(binding.label)
        self.target.set_value(binding.target)
        self.process.blockSignals(True)
        self.process.setCurrentText(binding.process)
        self.process.blockSignals(False)
        self.process_box.setVisible(binding.target == "app_volume")
        self.binding = binding

    def _name_changed(self, text: str) -> None:
        if self.binding is not None:
            self.binding.label = text
            self.changed.emit()

    def _target_changed(self, target: str) -> None:
        self.process_box.setVisible(target == "app_volume")
        if self.binding is not None:
            self.binding.target = target  # type: ignore[assignment]
            self.changed.emit()

    def _process_changed(self, text: str) -> None:
        if self.binding is not None:
            self.binding.process = text.strip()
            self.changed.emit()

    def _refresh_audio(self) -> None:
        current = self.process.currentText()
        self.process.blockSignals(True)
        self.process.clear()
        self.process.addItems(self._audio())
        self.process.setCurrentText(current)
        self.process.blockSignals(False)


class ProfileEditor(QWidget):
    """Nazwa, profil domyślny i procesy do automatycznego przełączania."""

    changed = Signal()
    renameRequested = Signal(str, str)  # stara, nowa nazwa

    def __init__(
        self, running_processes: Callable[[], list[str]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.profile: Profile | None = None
        self._running = running_processes
        self.name = QLineEdit()
        self.name.editingFinished.connect(self._rename)
        self.default = Switch(tr("Profil domyślny (start aplikacji)"))
        self.default.toggled.connect(self._default_toggled)
        self._is_default_cb: Callable[[Profile], bool] = lambda p: False
        self._set_default_cb: Callable[[Profile], None] = lambda p: None

        group = frame("outlined")
        self.processes = QListWidget()
        self.processes.setObjectName("boxed")
        self.processes.setMinimumHeight(140)
        self.add_combo = combo()
        self.add_combo.setEditable(True)
        self.add_combo.lineEdit().setPlaceholderText(
            tr("np. {name}").format(name=osinfo.example_process("app"))
        )
        self.add_combo.setMinimumContentsLength(10)
        refresh = button("", "refresh")
        refresh.setToolTip(tr("Odśwież listę uruchomionych procesów"))
        refresh.setFixedWidth(36)
        refresh.clicked.connect(self._refresh_running)
        add = button(tr("Dodaj"), primary=True)
        add.clicked.connect(self._add_process)
        remove = button(tr("Usuń"))
        remove.clicked.connect(self._remove_process)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self.add_combo, 1)
        row.addWidget(refresh)
        row.addWidget(add)
        row.addWidget(remove)
        g = QVBoxLayout(group)
        g.setContentsMargins(14, 12, 14, 14)
        g.setSpacing(8)
        g.addWidget(label(tr("Automatyczne przełączanie"), "strong"))
        g.addWidget(
            label(
                tr("Profil włącza się, gdy aktywne jest okno jednego z tych procesów."),
                "hint",
                wrap=True,
            )
        )
        g.addWidget(self.processes, 1)
        g.addLayout(row)

        # Kolor podświetlenia profilu (płytki z diodami LED).
        self.led_group = frame("outlined")
        self.led_custom = Switch(tr("Własny kolor podświetlenia w tym profilu"))
        self.led_custom.toggled.connect(self._led_toggled)
        self.led_color = ColorButton(swatches=LED_SWATCHES, title="", dialog_title=tr("Kolor LED"))
        self.led_color.changed.connect(self._led_color_changed)
        lg = QVBoxLayout(self.led_group)
        lg.setContentsMargins(14, 12, 14, 14)
        lg.setSpacing(8)
        lg.addWidget(label(tr("Podświetlenie LED"), "strong"))
        lg.addWidget(
            label(
                tr(
                    "Kolor diod, gdy ten profil jest aktywny (tryby stały i oddychanie). "
                    "Bez zaznaczenia – kolor z ustawień urządzenia."
                ),
                "hint",
                wrap=True,
            )
        )
        lg.addWidget(self.led_custom)
        lg.addWidget(self.led_color)
        self.led_group.setVisible(False)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.addWidget(label(tr("Profil").upper(), "kicker"))
        title_col.addWidget(label(tr("Właściwości profilu"), "h2"))

        name_col = QVBoxLayout()
        name_col.setSpacing(6)
        name_col.addWidget(label(tr("Nazwa"), "lbl"))
        name_col.addWidget(self.name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(title_col)
        layout.addLayout(name_col)
        layout.addWidget(self.default)
        layout.addWidget(self.led_group)
        layout.addWidget(group, 1)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def set_default_handlers(
        self, is_default: Callable[[Profile], bool], set_default: Callable[[Profile], None]
    ) -> None:
        self._is_default_cb = is_default
        self._set_default_cb = set_default

    def bind(self, profile: Profile) -> None:
        self.profile = profile
        self.name.setText(profile.name)
        self.default.blockSignals(True)
        self.default.setChecked(self._is_default_cb(profile))
        self.default.setEnabled(not self.default.isChecked())
        self.default.blockSignals(False)
        self.processes.clear()
        self.processes.addItems(profile.processes)
        self.led_custom.blockSignals(True)
        self.led_custom.setChecked(profile.led_color is not None)
        self.led_custom.blockSignals(False)
        self.led_color.set_color(profile.led_color or LED_SWATCHES[0])
        self.led_color.setEnabled(profile.led_color is not None)

    def set_leds_available(self, available: bool) -> None:
        """Sekcja koloru LED tylko dla płytek z podświetleniem (ChocPilot v0)."""
        self.led_group.setVisible(available)

    def _led_toggled(self, checked: bool) -> None:
        self.led_color.setEnabled(checked)
        if self.profile is None:
            return
        self.profile.led_color = self.led_color.color() if checked else None
        self.changed.emit()

    def _led_color_changed(self, color: str) -> None:
        if self.profile is None or not self.led_custom.isChecked():
            return
        self.profile.led_color = color
        self.changed.emit()

    def _rename(self) -> None:
        if self.profile is None:
            return
        new = self.name.text().strip()
        if new and new != self.profile.name:
            self.renameRequested.emit(self.profile.name, new)

    def _default_toggled(self, checked: bool) -> None:
        if checked and self.profile is not None:
            self._set_default_cb(self.profile)
            self.default.setEnabled(False)
            self.changed.emit()

    def _refresh_running(self) -> None:
        current = self.add_combo.currentText()
        self.add_combo.clear()
        self.add_combo.addItems(self._running())
        self.add_combo.setCurrentText(current)

    def _add_process(self) -> None:
        name = self.add_combo.currentText().strip()
        if not name or self.profile is None:
            return
        name = osinfo.normalize_process_entry(name)
        if not any(osinfo.same_process(name, p) for p in self.profile.processes):
            self.profile.processes = [*self.profile.processes, name]
            self.processes.addItem(name)
            self.changed.emit()

    def _remove_process(self) -> None:
        row = self.processes.currentRow()
        if row < 0 or self.profile is None:
            return
        processes = list(self.profile.processes)
        del processes[row]
        self.profile.processes = processes
        self.processes.takeItem(row)
        self.changed.emit()


__all__ = [
    "LED_SWATCHES",
    "ColorButton",
    "EncoderEditor",
    "KeyEditor",
    "LabelEdit",
    "ProfileEditor",
    "SliderEditor",
    "styled",
]

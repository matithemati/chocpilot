"""Okno wyboru ikony klawisza: wyszukiwarka, kategorie, siatka ikon (rysowanych na żądanie)."""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPersistentModelIndex, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QListView,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .i18n import tr
from .icon_library import CATEGORY_CUSTOM, IconEntry, IconLibrary, custom_dir, library
from .widgets import button, label

ALL = ""


class IconModel(QAbstractListModel):
    """Lista ikon; obraz ikony renderowany dopiero, gdy widok o niego poprosi (1800+ pozycji)."""

    def __init__(self, lib: IconLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.lib = lib
        self.items: list[IconEntry] = []
        self._icons: dict[str, QIcon] = {}

    def set_items(self, items: list[IconEntry]) -> None:
        self.beginResetModel()
        self.items = items
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:  # type: ignore[override]
        return len(self.items)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid():
            return None
        entry = self.items[index.row()]
        if role == Qt.ItemDataRole.DecorationRole:
            icon = self._icons.get(entry.id)
            if icon is None:
                image = self.lib.render(entry.id, 64, theme.tokens()["text"])
                icon = QIcon(QPixmap.fromImage(image))
                self._icons[entry.id] = icon
            return icon
        if role in (Qt.ItemDataRole.ToolTipRole, Qt.ItemDataRole.DisplayRole):
            return entry.name if role == Qt.ItemDataRole.ToolTipRole else ""
        if role == Qt.ItemDataRole.UserRole:
            return entry.id
        return None


class IconPickerDialog(QDialog):
    def __init__(
        self, current: str = "", parent: QWidget | None = None, lib: IconLibrary | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Wybierz ikonę"))
        self.resize(720, 560)
        self.lib = lib or library()
        self.selected = current
        self.cleared = False

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Szukaj (np. play, folder, kot, music)…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.category = QComboBox()
        self.category.addItem(tr("Wszystkie"), ALL)
        for cat in self.lib.categories():
            self.category.addItem(tr(cat), cat)
        if CATEGORY_CUSTOM not in self.lib.categories():
            self.category.addItem(tr(CATEGORY_CUSTOM), CATEGORY_CUSTOM)
        self.category.currentIndexChanged.connect(self._filter)

        self.model = IconModel(self.lib, self)
        self.view = QListView()
        self.view.setViewMode(QListView.ViewMode.IconMode)
        self.view.setResizeMode(QListView.ResizeMode.Adjust)
        self.view.setUniformItemSizes(True)
        self.view.setIconSize(QSize(40, 40))
        self.view.setGridSize(QSize(58, 58))
        self.view.setMovement(QListView.Movement.Static)
        self.view.setModel(self.model)
        accent = theme.color("accent")
        self.view.setStyleSheet(
            "QListView::item { border-radius: 8px; }"
            f"QListView::item:selected {{ background: rgba({accent.red()}, {accent.green()}, "
            f"{accent.blue()}, 60); border: 2px solid {accent.name()}; }}"
        )
        self.view.selectionModel().currentChanged.connect(self._current_changed)
        self.view.doubleClicked.connect(lambda _i: self.accept())

        self.info = label("", "muted")
        self.count = label("", "hint")

        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.category)

        folder = button(tr("Folder własnych ikon"))
        folder.setToolTip(
            tr(
                "Dodaj pliki PNG/SVG do tego folderu, a potem kliknij Odśwież – "
                "pojawią się jako Własne."
            )
        )
        folder.clicked.connect(self._open_folder)
        refresh = button(tr("Odśwież"))
        refresh.clicked.connect(self._reload)
        none = button(tr("Bez ikony"))
        none.clicked.connect(self._clear)
        cancel = button(tr("Anuluj"))
        cancel.clicked.connect(self.reject)
        self.ok = button(tr("Wybierz"), primary=True)
        self.ok.clicked.connect(self.accept)

        bottom = QHBoxLayout()
        bottom.addWidget(folder)
        bottom.addWidget(refresh)
        bottom.addStretch(1)
        bottom.addWidget(none)
        bottom.addWidget(cancel)
        bottom.addWidget(self.ok)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.view, 1)
        info_row = QHBoxLayout()
        info_row.addWidget(self.info, 1)
        info_row.addWidget(self.count)
        layout.addLayout(info_row)
        layout.addLayout(bottom)
        self._filter()
        self._select(current)

    def _filter(self, *_args: object) -> None:
        cat = self.category.currentData()
        query = self.search.text()
        items = [
            e for e in self.lib.entries() if (cat == ALL or e.category == cat) and e.matches(query)
        ]
        self.model.set_items(items)
        self.count.setText(f"{len(items)} {tr('ikon')}")
        self._select(self.selected)

    def _select(self, icon_id: str) -> None:
        for row, entry in enumerate(self.model.items):
            if entry.id == icon_id:
                index = self.model.index(row)
                self.view.setCurrentIndex(index)
                self.view.scrollTo(index)
                return
        self._update_info()

    def _current_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if current.isValid():
            self.selected = self.model.items[current.row()].id
        self._update_info()

    def _update_info(self) -> None:
        entry = self.lib.entry(self.selected) if self.selected else None
        self.info.setText(f"{entry.name}  ·  {entry.id}" if entry else tr("Nie wybrano ikony"))
        self.ok.setEnabled(entry is not None)

    def _clear(self) -> None:
        self.selected = ""
        self.cleared = True
        self.accept()

    def _open_folder(self) -> None:
        path = custom_dir()
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _reload(self) -> None:
        self.lib.reload()
        self.model._icons.clear()
        self._filter()

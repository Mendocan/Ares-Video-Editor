from __future__ import annotations

import os
import webbrowser
from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.sfx_library import (
    SFX_CATEGORIES,
    SfxCategory,
    category_folder,
    ensure_sfx_folders,
    find_category,
    local_files_for,
)
from app.ui.app_theme import BORDER, BTN_PRIMARY_GRADIENT, TEXT_MUTED, TEXT_PRIMARY


class SfxLibraryDialog(QDialog):
    """Acik kaynak / CC0 ses efekti kataloguna goz atma ve timeline'a ekleme penceresi."""

    add_to_timeline_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ses Efektleri Kutuphanesi")
        self.resize(820, 520)
        ensure_sfx_folders()

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Kategoriler"))
        self.category_list = QListWidget()
        for category in SFX_CATEGORIES:
            item = QListWidgetItem(category.label)
            item.setData(Qt.UserRole, category.key)
            self.category_list.addItem(item)
        self.category_list.currentRowChanged.connect(self._on_category_changed)
        left.addWidget(self.category_list)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        info = QLabel(
            "Ruzgar, motor, silah ve patlama gibi ses efektleri icin acik kaynak/CC0 "
            "lisansli en iyi kaynaklar kategorilere ayrildi. Kaynagi tarayicida acip "
            "indirdiginiz dosyalari asagidaki klasore koyarsaniz burada listelenir ve "
            "tek tikla timeline'a eklenir."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        right.addWidget(info)

        self.sources_group = QGroupBox("Onerilen Acik Kaynaklar")
        self.sources_layout = QVBoxLayout(self.sources_group)
        right.addWidget(self.sources_group)

        folder_row = QHBoxLayout()
        self.folder_label = QLabel("-")
        self.folder_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        open_folder_btn = QPushButton("Klasoru Ac")
        open_folder_btn.clicked.connect(self._open_local_folder)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(open_folder_btn)
        right.addLayout(folder_row)

        right.addWidget(QLabel("Yerel Ses Dosyalari"))
        self.local_list = QListWidget()
        right.addWidget(self.local_list, 1)

        action_row = QHBoxLayout()
        preview_btn = QPushButton("Onizle")
        preview_btn.clicked.connect(self._preview_selected)
        import_btn = QPushButton("Bilgisayardan Sec...")
        import_btn.clicked.connect(self._import_from_disk)
        add_btn = QPushButton("Timeline'a Ekle")
        add_btn.setStyleSheet(
            f"background: {BTN_PRIMARY_GRADIENT}; color: {TEXT_PRIMARY}; font-weight: bold; padding: 6px 14px;"
        )
        add_btn.clicked.connect(self._add_selected_to_timeline)
        action_row.addWidget(preview_btn)
        action_row.addWidget(import_btn)
        action_row.addStretch(1)
        action_row.addWidget(add_btn)
        right.addLayout(action_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        right.addWidget(buttons)

        root.addLayout(right, 2)

        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def _current_category(self) -> SfxCategory | None:
        item = self.category_list.currentItem()
        if not item:
            return None
        return find_category(item.data(Qt.UserRole))

    def _clear_sources(self) -> None:
        while self.sources_layout.count():
            child = self.sources_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()

    def _on_category_changed(self, _row: int) -> None:
        self._clear_sources()
        category = self._current_category()
        if category is None:
            return

        for source in category.sources:
            row = QHBoxLayout()
            note = f" — {source.note}" if source.note else ""
            text = QLabel(f"<b>{source.name}</b><br/><span style='color:{TEXT_MUTED};'>{source.license}{note}</span>")
            text.setWordWrap(True)
            text.setTextFormat(Qt.RichText)
            open_btn = QPushButton("Kaynagi Ac")
            open_btn.clicked.connect(lambda _checked=False, url=source.url: webbrowser.open(url))
            row.addWidget(text, 1)
            row.addWidget(open_btn)
            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet(f"border-bottom: 1px solid {BORDER};")
            self.sources_layout.addWidget(container)

        self.folder_label.setText(str(category_folder(category)))
        self._refresh_local_files()

    def _refresh_local_files(self) -> None:
        self.local_list.clear()
        category = self._current_category()
        if category is None:
            return
        files = local_files_for(category)
        if not files:
            placeholder = QListWidgetItem(
                "(Bu kategoride henuz dosya yok - once yukaridan bir kaynagi acip indirin)"
            )
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.local_list.addItem(placeholder)
            return
        for path in files:
            item = QListWidgetItem(path.name)
            item.setData(Qt.UserRole, str(path))
            self.local_list.addItem(item)

    def _selected_local_path(self) -> str | None:
        item = self.local_list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _preview_selected(self) -> None:
        path = self._selected_local_path()
        if not path:
            return
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def _add_selected_to_timeline(self) -> None:
        path = self._selected_local_path()
        if not path:
            return
        self.add_to_timeline_requested.emit(path)

    def _open_local_folder(self) -> None:
        category = self._current_category()
        if category is None:
            return
        folder = category_folder(category)
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))  # noqa: S606 - Windows'a ozgu, uygulama Windows hedefliyor
        except (AttributeError, OSError):
            webbrowser.open(folder.as_uri())

    def _import_from_disk(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Ses Dosyasi Sec",
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a *.aac);;All Files (*)",
        )
        if file_path:
            self.add_to_timeline_requested.emit(file_path)

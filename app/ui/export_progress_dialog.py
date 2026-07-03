"""Dışa aktarım ilerleme penceresi — tamamlanınca otomatik kapanır."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from app.ui.dialog_chrome import apply_frameless_chrome
from app.ui.app_theme import TEXT_MUTED, TEXT_PRIMARY


class ExportProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setFixedWidth(360)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._on_closed: Callable[[], None] | None = None
        self._finished = False

        content = apply_frameless_chrome(self, "Dışa Aktar")
        self._status_label = QLabel("Dışa aktarım hazırlanıyor...")
        self._status_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        self._status_label.setWordWrap(True)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(22)

        content.addWidget(self._status_label)
        content.addWidget(self._progress)
        content.addStretch(0)

        hint = QLabel("Lütfen bekleyin…")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        content.addWidget(hint)

    def set_progress(self, percent: int, message: str) -> None:
        if self._finished:
            return
        self._progress.setValue(max(0, min(100, percent)))
        self._status_label.setText(message)

    def current_percent(self) -> int:
        return self._progress.value()

    def show_complete(self) -> None:
        """100% goster; kapatma main window tarafindan yapilir."""
        if self._finished:
            return
        self._progress.setValue(100)
        self._status_label.setText("Tamamlandı!")

    def close_now(self, on_closed: Callable[[], None] | None = None) -> None:
        """Pencereyi guvenilir sekilde kapat."""
        if self._finished:
            if on_closed:
                on_closed()
            return
        self._finished = True
        callback = on_closed or self._on_closed
        self._on_closed = None
        self.setModal(False)
        self.hide()
        self.accept()
        self.close()
        self.deleteLater()
        if callback:
            callback()

    def dismiss(self, on_closed: Callable[[], None] | None = None) -> None:
        self.close_now(on_closed)

    def reject(self) -> None:
        if not self._finished:
            return
        super().reject()

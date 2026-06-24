from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.subtitle_parser import SubtitleEntry


class SubtitleEditorDialog(QDialog):
    def __init__(self, entries: list[SubtitleEntry], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Altyazi Duzenleyici")
        self.resize(800, 600)
        self.entries = entries
        self.updated_entries: list[SubtitleEntry] = []

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Baslangic (ms)", "Bitis (ms)", "Metin"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_button = QPushButton("Kaydet")
        self.save_button.clicked.connect(self._on_save)
        
        self.cancel_button = QPushButton("Iptal")
        self.cancel_button.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_button)
        btn_layout.addWidget(self.cancel_button)

        layout.addLayout(btn_layout)

    def _load_data(self) -> None:
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            start_item = QTableWidgetItem(str(entry.start_ms))
            end_item = QTableWidgetItem(str(entry.end_ms))
            text_item = QTableWidgetItem(entry.text)

            self.table.setItem(row, 0, start_item)
            self.table.setItem(row, 1, end_item)
            self.table.setItem(row, 2, text_item)

    def _on_save(self) -> None:
        self.updated_entries = []
        for row in range(self.table.rowCount()):
            start_ms = int(self.table.item(row, 0).text())
            end_ms = int(self.table.item(row, 1).text())
            text = self.table.item(row, 2).text()
            
            # Zaman metinlerini formata uydurmak icin basit cevirici:
            entry = SubtitleEntry(
                index=row + 1,
                start=self._ms_to_srt_time(start_ms),
                end=self._ms_to_srt_time(end_ms),
                text=text,
                start_ms=start_ms,
                end_ms=end_ms
            )
            self.updated_entries.append(entry)

        self.accept()

    def _ms_to_srt_time(self, ms: int) -> str:
        hours, remainder = divmod(ms, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

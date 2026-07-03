from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from app.ui.app_theme import TEXT_MUTED


PREVIEW_PRESETS = [
    ("16:9 — YouTube / Yatay", "16:9"),
    ("9:16 — TikTok / Reels", "9:16"),
    ("1:1 — Instagram Kare", "1:1"),
    ("4:5 — Instagram Feed", "4:5"),
]


class PreviewSettingsDialog(QDialog):
    def __init__(self, current_format: str, parent=None) -> None:
        super().__init__(parent)
        self.selected_format = current_format
        self.take_screenshot = False
        self.setWindowTitle("Onizleme Ayarlari")
        self.resize(420, 320)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Onizleme gorunum orani ve hizli islemler"))

        self.preset_list = QListWidget()
        for label, value in PREVIEW_PRESETS:
            item = QListWidgetItem(label)
            item.setData(256, value)
            self.preset_list.addItem(item)
            if value == self.selected_format:
                self.preset_list.setCurrentItem(item)
        layout.addWidget(self.preset_list)

        hint = QLabel(
            "• Gorunum orani onizleme panelini aninda degistirir.\n"
            "• Ekran goruntusu: o anki kareyi JPG olarak kaydeder."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        shot_btn = buttons.addButton("Ekran Goruntusu", QDialogButtonBox.ActionRole)
        ok_btn = buttons.addButton("Uygula", QDialogButtonBox.AcceptRole)
        cancel_btn = buttons.addButton("Iptal", QDialogButtonBox.RejectRole)
        shot_btn.clicked.connect(self._choose_screenshot)
        ok_btn.clicked.connect(self._choose_apply)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_screenshot(self) -> None:
        self.take_screenshot = True
        item = self.preset_list.currentItem()
        if item:
            self.selected_format = item.data(256)
        self.accept()

    def _choose_apply(self) -> None:
        item = self.preset_list.currentItem()
        if item:
            self.selected_format = item.data(256)
        self.accept()

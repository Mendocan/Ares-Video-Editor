from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ui.app_theme import (
    BTN_PRIMARY_GRADIENT,
    EXPORT_COMPACT_BTN_QSS,
    QUALITY_RADIO_QSS,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from app.ui.dialog_chrome import apply_frameless_chrome
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QFileDialog,
    QWidget,
    QButtonGroup,
)

from app.core.export_presets import (
    EXPORT_FORMATS,
    FORMAT_EXTENSIONS,
    FPS_OPTIONS,
    QUALITY_GOOD,
    QUALITY_OPTIONS,
    QUALITY_PROFILES,
    RESOLUTION_PRESETS,
    estimate_size_mb,
    unique_output_path,
)


@dataclass(slots=True)
class ExportDialogResult:
    output_path: str
    title: str
    format_name: str
    quality: str
    aspect_ratio: str
    fps: str
    audio_bitrate: str
    video_crf: int
    video_preset: str


class ExportAdvancedDialog(QDialog):
    def __init__(self, fps: str, audio_bitrate: str, parent=None) -> None:
        super().__init__(parent)
        self.resize(340, 180)
        content = apply_frameless_chrome(self, "Gelişmiş Dışa Aktarma Ayarları")
        layout = QFormLayout()
        layout.setSpacing(8)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(FPS_OPTIONS)
        self.fps_combo.setCurrentText(fps)
        self.audio_combo = QComboBox()
        self.audio_combo.addItems(["128k", "192k", "256k", "320k"])
        self.audio_combo.setCurrentText(audio_bitrate.replace("Orijinal", "192k"))
        layout.addRow("Çekim hızı (FPS)", self.fps_combo)
        layout.addRow("Ses bit hızı", self.audio_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        content.addLayout(layout)

    def values(self) -> tuple[str, str]:
        return self.fps_combo.currentText(), self.audio_combo.currentText()


class ExportDialog(QDialog):
    def __init__(
        self,
        default_title: str,
        default_folder: str,
        duration_ms: int,
        current_aspect: str,
        current_fps: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.duration_ms = duration_ms
        self.result_data: ExportDialogResult | None = None
        self._advanced_fps = current_fps
        self._advanced_audio = "192k"
        self.resize(620, 400)
        self._build_ui(default_title, default_folder, current_aspect, current_fps)

    def _build_ui(self, default_title: str, default_folder: str, aspect: str, fps: str) -> None:
        content = apply_frameless_chrome(self, "Dışa Aktar")
        root = QHBoxLayout()
        content.addLayout(root)

        left = QVBoxLayout()
        left.addWidget(QLabel("Çıktı biçimi"))
        self.format_list = QListWidget()
        for fmt in EXPORT_FORMATS:
            item = QListWidgetItem(fmt)
            self.format_list.addItem(item)
        self.format_list.setCurrentRow(0)
        self.format_list.currentRowChanged.connect(self._update_stats)
        left.addWidget(self.format_list)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(10)
        header = QLabel("Videoyu bilgisayara kaydedin")
        header.setStyleSheet("font-weight: bold; font-size: 12px;")
        right.addWidget(header)

        form = QFormLayout()
        form.setSpacing(8)
        self.title_input = QLineEdit(default_title)
        form.addRow("Başlık", self.title_input)

        path_row = QHBoxLayout()
        self.folder_input = QLineEdit(default_folder)
        browse = QPushButton("Gözat")
        browse.setStyleSheet(EXPORT_COMPACT_BTN_QSS)
        browse.clicked.connect(self._pick_folder)
        path_row.addWidget(self.folder_input, 1)
        path_row.addWidget(browse)
        form.addRow("Kayıt yeri", path_row)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(RESOLUTION_PRESETS)
        if aspect in RESOLUTION_PRESETS:
            self.resolution_combo.setCurrentText(aspect)
        self.resolution_combo.currentTextChanged.connect(self._update_stats)
        form.addRow("Çözünürlük", self.resolution_combo)
        right.addLayout(form)

        quality_group = QGroupBox("Kalite")
        quality_group.setStyleSheet(QUALITY_RADIO_QSS)
        q_layout = QVBoxLayout(quality_group)
        q_layout.setSpacing(2)
        q_layout.setContentsMargins(6, 8, 6, 6)
        self.quality_buttons: dict[str, QRadioButton] = {}
        self.quality_group = QButtonGroup(self)
        for index, name in enumerate(QUALITY_OPTIONS):
            radio = QRadioButton(name)
            if name == QUALITY_GOOD:
                radio.setChecked(True)
            self.quality_buttons[name] = radio
            self.quality_group.addButton(radio, index)
            q_layout.addWidget(radio)
        self.quality_desc = QLabel(QUALITY_PROFILES[QUALITY_GOOD].description)
        self.quality_desc.setWordWrap(True)
        self.quality_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; padding: 2px 4px;")
        q_layout.addWidget(self.quality_desc)
        for radio in self.quality_buttons.values():
            radio.toggled.connect(self._on_quality_changed)
        right.addWidget(quality_group)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        right.addWidget(self.stats_label)

        right.addStretch(1)

        adv_row = QHBoxLayout()
        adv_btn = QPushButton("Gelişmiş ayarlar...")
        adv_btn.setStyleSheet(EXPORT_COMPACT_BTN_QSS)
        adv_btn.clicked.connect(self._open_advanced)
        adv_row.addWidget(adv_btn)
        adv_row.addStretch(1)
        cancel = QPushButton("İptal")
        start = QPushButton("Başlat")
        compact = (
            EXPORT_COMPACT_BTN_QSS
            + f"QPushButton#exportStart {{ background: {BTN_PRIMARY_GRADIENT}; color: {TEXT_PRIMARY}; }}"
        )
        cancel.setStyleSheet(compact)
        start.setObjectName("exportStart")
        start.setStyleSheet(compact)
        cancel.clicked.connect(self.reject)
        start.clicked.connect(self._accept_export)
        adv_row.addWidget(cancel)
        adv_row.addWidget(start)
        right.addLayout(adv_row)

        root.addLayout(right, 3)
        self._update_stats()

    def _format_duration(self) -> str:
        total = max(0, self.duration_ms)
        s, ms = divmod(total, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Çıktı Klasörü", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)

    def _current_quality(self) -> str:
        for name, radio in self.quality_buttons.items():
            if radio.isChecked():
                return name
        return QUALITY_GOOD

    def _on_quality_changed(self) -> None:
        quality = self._current_quality()
        profile = QUALITY_PROFILES.get(quality)
        if profile:
            self.quality_desc.setText(profile.description)
        self._update_stats()

    def _open_advanced(self) -> None:
        dialog = ExportAdvancedDialog(self._advanced_fps, self._advanced_audio, self)
        if dialog.exec() == QDialog.Accepted:
            self._advanced_fps, self._advanced_audio = dialog.values()

    def _update_stats(self, *_args) -> None:
        quality = self._current_quality()
        sec = max(1.0, self.duration_ms / 1000.0)
        low, high = estimate_size_mb(sec, quality)
        from app.core.video_presets import play_resolution

        res_x, res_y = play_resolution(self.resolution_combo.currentText())
        self.stats_label.setText(
            f"Süre: {self._format_duration()}   •   "
            f"Tahmini boyut: {low}-{high} MB   •   "
            f"Çıkış: {res_x}x{res_y}"
        )

    def _accept_export(self) -> None:
        title = self.title_input.text().strip() or "cikti"
        folder = Path(self.folder_input.text().strip() or str(Path.cwd() / "output"))
        fmt = self.format_list.currentItem().text() if self.format_list.currentItem() else "MP4"
        ext = FORMAT_EXTENSIONS.get(fmt, ".mp4")
        output = unique_output_path(folder, title, ext)
        quality = self._current_quality()
        profile = QUALITY_PROFILES[quality]
        self.result_data = ExportDialogResult(
            output_path=str(output),
            title=title,
            format_name=fmt,
            quality=quality,
            aspect_ratio=self.resolution_combo.currentText(),
            fps=self._advanced_fps,
            audio_bitrate=self._advanced_audio,
            video_crf=profile.crf,
            video_preset=profile.video_preset,
        )
        self.accept()

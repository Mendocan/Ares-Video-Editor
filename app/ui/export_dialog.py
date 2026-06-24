from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
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
        self.setWindowTitle("Disari Aktarma Ayarlari")
        self.resize(380, 220)
        layout = QFormLayout(self)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(FPS_OPTIONS)
        self.fps_combo.setCurrentText(fps)
        self.audio_combo = QComboBox()
        self.audio_combo.addItems(["128k", "192k", "256k", "320k"])
        self.audio_combo.setCurrentText(audio_bitrate.replace("Orijinal", "192k"))
        layout.addRow("Cekim hizi (FPS)", self.fps_combo)
        layout.addRow("Ses bit hizi", self.audio_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

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
        self.setWindowTitle("Disa Aktar")
        self.resize(760, 520)
        self._build_ui(default_title, default_folder, current_aspect, current_fps)

    def _build_ui(self, default_title: str, default_folder: str, aspect: str, fps: str) -> None:
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Cikti bicimi"))
        self.format_list = QListWidget()
        for fmt in EXPORT_FORMATS:
            item = QListWidgetItem(fmt)
            self.format_list.addItem(item)
        self.format_list.setCurrentRow(0)
        self.format_list.currentRowChanged.connect(self._update_stats)
        left.addWidget(self.format_list)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        header = QLabel("Videoyu bilgisayara kaydedin")
        header.setStyleSheet("font-weight: bold; font-size: 12px;")
        right.addWidget(header)

        form = QFormLayout()
        self.title_input = QLineEdit(default_title)
        form.addRow("Baslik", self.title_input)

        path_row = QHBoxLayout()
        self.folder_input = QLineEdit(default_folder)
        browse = QPushButton("Goz at")
        browse.clicked.connect(self._pick_folder)
        path_row.addWidget(self.folder_input, 1)
        path_row.addWidget(browse)
        form.addRow("Kayit hedefi", path_row)
        right.addLayout(form)

        quality_group = QGroupBox("Kalite")
        q_layout = QVBoxLayout(quality_group)
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
        self.quality_desc.setStyleSheet("color: #94A3B8; font-size: 10px;")
        q_layout.addWidget(self.quality_desc)
        for radio in self.quality_buttons.values():
            radio.toggled.connect(self._on_quality_changed)
        right.addWidget(quality_group)

        opts = QFormLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(RESOLUTION_PRESETS)
        if aspect in RESOLUTION_PRESETS:
            self.resolution_combo.setCurrentText(aspect)
        self.resolution_combo.currentTextChanged.connect(self._update_stats)
        opts.addRow("Cozunurluk", self.resolution_combo)
        right.addLayout(opts)

        stats = QFormLayout()
        self.duration_label = QLabel(self._format_duration())
        self.size_label = QLabel("-")
        self.resolution_label = QLabel("-")
        stats.addRow("Sure", self.duration_label)
        stats.addRow("Dosya boyutu (tahmini)", self.size_label)
        stats.addRow("Cikis cozunurlugu", self.resolution_label)
        right.addLayout(stats)

        adv_row = QHBoxLayout()
        adv_row.addStretch(1)
        adv_btn = QPushButton("Gelistirilmis...")
        adv_btn.clicked.connect(self._open_advanced)
        adv_row.addWidget(adv_btn)
        right.addLayout(adv_row)

        buttons = QDialogButtonBox()
        cancel = QPushButton("Iptal")
        cancel.clicked.connect(self.reject)
        start = QPushButton("Baslat")
        start.setStyleSheet("background-color: #F8FAFC; color: #0F172A; font-weight: bold; padding: 8px 20px;")
        start.clicked.connect(self._accept_export)
        buttons.addButton(cancel, QDialogButtonBox.RejectRole)
        buttons.addButton(start, QDialogButtonBox.AcceptRole)
        right.addWidget(buttons)

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
        folder = QFileDialog.getExistingDirectory(self, "Cikti Klasoru", self.folder_input.text())
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
        self.duration_label.setText(self._format_duration())
        quality = self._current_quality()
        sec = max(1.0, self.duration_ms / 1000.0)
        low, high = estimate_size_mb(sec, quality)
        self.size_label.setText(f"{low} MB - {high} MB")
        from app.core.video_presets import play_resolution

        res_x, res_y = play_resolution(self.resolution_combo.currentText())
        self.resolution_label.setText(f"{res_x} x {res_y}")

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

from __future__ import annotations

from pathlib import Path

from app.ui.app_theme import BTN_PRIMARY_GRADIENT, TEXT_MUTED
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.core.worker import Worker
from app.services.transcription_service import TranscriptionResult, TranscriptionService


MODEL_OPTIONS = [
    ("tiny", "Tiny — en hizli, dusuk dogruluk"),
    ("base", "Base — onerilen baslangic"),
    ("small", "Small — daha iyi dogruluk"),
    ("medium", "Medium — yuksek dogruluk, yavas"),
]

LANGUAGE_OPTIONS = [
    ("", "Otomatik algila"),
    ("tr", "Turkce"),
    ("en", "Ingilizce"),
    ("de", "Almanca"),
    ("fr", "Fransizca"),
    ("es", "Ispanyolca"),
    ("ar", "Arapca"),
]


class TranscriptionDialog(QDialog):
    def __init__(
        self,
        video_path: str,
        transcription_service: TranscriptionService,
        parent=None,
        translate_default: bool = False,
    ) -> None:
        super().__init__(parent)
        self.video_path = video_path
        self.transcription_service = transcription_service
        self.thread_pool = QThreadPool()
        self.result_data: TranscriptionResult | None = None
        self.setWindowTitle("Otomatik Altyazi — Whisper")
        self.resize(520, 380)
        self._build_ui(translate_default)

    def _build_ui(self, translate_default: bool) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(
            f"Video: <b>{Path(self.video_path).name}</b><br>"
            f"<span style='color:{TEXT_MUTED};'>faster-whisper ile kelime zamanlamali SRT uretilir.</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        settings = QGroupBox("Transkripsiyon Ayarlari")
        form = QFormLayout(settings)

        self.model_combo = QComboBox()
        for _value, label in MODEL_OPTIONS:
            self.model_combo.addItem(label)
        self.model_combo.setCurrentIndex(1)

        self.language_combo = QComboBox()
        for _code, label in LANGUAGE_OPTIONS:
            self.language_combo.addItem(label)
        self.language_combo.setCurrentIndex(1)  # Turkce varsayilan

        self.translate_checkbox = QCheckBox("Ingilizceye cevir (translate)")
        self.translate_checkbox.setChecked(translate_default)
        self.translate_checkbox.setToolTip(
            "Kaynak dili Ingilizceye cevirir. Aksi halde orijinal dilde yazar."
        )

        self.music_checkbox = QCheckBox("Sarki / muzik videosu")
        self.music_checkbox.setToolTip(
            "Sarki ve muzik kliplerinde VAD kapatilir; Whisper tum sesi kesintisiz isler. "
            "Konusma videolari icin isaretlemeyin."
        )

        form.addRow("Model", self.model_combo)
        form.addRow("Dil", self.language_combo)
        form.addRow("", self.translate_checkbox)
        form.addRow("", self.music_checkbox)
        layout.addWidget(settings)

        output_group = QGroupBox("Cikti")
        out_layout = QHBoxLayout(output_group)
        default_srt = str(Path(self.video_path).with_suffix(".srt"))
        self.output_input = QLineEdit(default_srt)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._pick_output)
        out_layout.addWidget(self.output_input, 1)
        out_layout.addWidget(browse_btn)
        layout.addWidget(output_group)

        self.status_label = QLabel("Hazir.")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        buttons = QDialogButtonBox()
        self.start_btn = QPushButton("Baslat")
        self.start_btn.setStyleSheet(f"background: {BTN_PRIMARY_GRADIENT}; font-weight: bold;")
        self.start_btn.clicked.connect(self._start)
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.reject)
        buttons.addButton(close_btn, QDialogButtonBox.RejectRole)
        buttons.addButton(self.start_btn, QDialogButtonBox.AcceptRole)
        layout.addWidget(buttons)

    def _pick_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "SRT Ciktisini Kaydet",
            self.output_input.text(),
            "Subtitle Files (*.srt)",
        )
        if path:
            self.output_input.setText(path)

    def _set_busy(self, busy: bool) -> None:
        self.start_btn.setEnabled(not busy)
        self.model_combo.setEnabled(not busy)
        self.language_combo.setEnabled(not busy)
        self.translate_checkbox.setEnabled(not busy)
        self.music_checkbox.setEnabled(not busy)
        self.output_input.setEnabled(not busy)

    def _start(self) -> None:
        output_path = self.output_input.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Uyari", "Lutfen bir SRT cikti yolu secin.")
            return

        model_size = MODEL_OPTIONS[self.model_combo.currentIndex()][0]
        language = LANGUAGE_OPTIONS[self.language_combo.currentIndex()][0]
        translate = self.translate_checkbox.isChecked()
        music_mode = self.music_checkbox.isChecked()

        if music_mode and model_size == "tiny":
            answer = QMessageBox.question(
                self,
                "Model Onerisi",
                "Sarki/muzik videolari icin 'Small' veya 'Medium' model onerilir.\n"
                "Tiny model ile devam edilsin mi?",
            )
            if answer != QMessageBox.Yes:
                return

        self.transcription_service.configure(model_size=model_size)
        self._set_busy(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Whisper modeli yukleniyor...")

        worker = Worker(
            self.transcription_service.generate_srt,
            self.video_path,
            output_path,
            translate=translate,
            language=language or None,
            music_mode=music_mode,
            progress_callback=lambda _msg: None,
        )

        def on_progress(message: str) -> None:
            if "|" in message:
                pct_str, label = message.split("|", 1)
                try:
                    self.progress_bar.setValue(int(pct_str))
                except ValueError:
                    pass
                self.status_label.setText(label)
            QApplication.processEvents()

        worker.signals.progress.connect(on_progress)
        worker.signals.result.connect(self._on_success)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(lambda: self._set_busy(False))
        self.thread_pool.start(worker)

    def _on_success(self, result: TranscriptionResult) -> None:
        self.result_data = result
        self.progress_bar.setValue(100)
        self.status_label.setText("Tamamlandi.")
        self.accept()

    def _on_error(self, error_data: tuple) -> None:
        _exc, trace = error_data
        QMessageBox.critical(self, "Transkripsiyon Hatasi", str(trace))
        self.status_label.setText("Hata olustu.")

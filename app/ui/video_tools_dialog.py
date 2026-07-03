from __future__ import annotations

import subprocess
from pathlib import Path

from app.ui.app_theme import COLOR_DANGER, TEXT_MUTED, TEXT_ON_ACCENT
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.silence_cutter import SilenceCutter
from app.core.worker import Worker


class VideoToolsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Video Araçları")
        self.resize(700, 500)
        self.thread_pool = QThreadPool()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_auto_cut_tab(), "Otomatik Boşluk Kes")
        tabs.addTab(self._build_trim_tab(), "Video Kes (Trim)")
        tabs.addTab(self._build_merge_tab(), "Videoları Birleştir")
        tabs.addTab(self._build_audio_extract_tab(), "Sesi Çıkar")

        layout.addWidget(tabs)

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    # --- OTOMATIK BOSLUK KESME SEKMESI ---
    def _build_auto_cut_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Sessizlikleri Otomatik Kes (Jumpcut)")
        form = QFormLayout(group)

        self.auto_cut_input = QLineEdit()
        self.auto_cut_input.setReadOnly(True)
        auto_cut_browse = QPushButton("Seç")
        auto_cut_browse.clicked.connect(lambda: self._browse_file(self.auto_cut_input, "Video Seç", "Video Files (*.mp4 *.mov *.mkv)"))

        row_layout = QHBoxLayout()
        row_layout.addWidget(self.auto_cut_input)
        row_layout.addWidget(auto_cut_browse)

        self.db_threshold = QLineEdit("-35")
        self.db_threshold.setToolTip("Hangi ses seviyesinin altı sessizlik kabul edilsin (Örn: -35)")
        
        self.min_duration = QLineEdit("0.5")
        self.min_duration.setToolTip("En az kaç saniyelik sessizlikler kesilsin (Örn: 0.5)")

        form.addRow("Kaynak Video:", row_layout)
        form.addRow("Sessizlik Sınırı (dB):", self.db_threshold)
        form.addRow("Min. Sessizlik Süresi (sn):", self.min_duration)

        layout.addWidget(group)

        self.auto_cut_btn = QPushButton("Sessizlikleri Temizle ve Kaydet")
        self.auto_cut_btn.setStyleSheet(
            f"background-color: {COLOR_DANGER}; color: {TEXT_ON_ACCENT}; font-weight: bold;"
        )
        self.auto_cut_btn.clicked.connect(self._run_auto_cut)
        layout.addWidget(self.auto_cut_btn)
        layout.addStretch()

        return widget

    def _run_auto_cut(self) -> None:
        source = self.auto_cut_input.text()
        if not source:
            QMessageBox.warning(self, "Hata", "Lütfen bir video seçin.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Kaydet", str(Path(source).parent / "bosluksuz.mp4"), "MP4 (*.mp4)")
        if not out_path:
            return

        try:
            db_val = int(self.db_threshold.text())
            dur_val = float(self.min_duration.text())
        except ValueError:
            QMessageBox.warning(self, "Hata", "Lütfen dB ve Süre için geçerli sayılar girin.")
            return

        cutter = SilenceCutter(db_threshold=db_val, min_duration=dur_val)
        
        self.auto_cut_btn.setEnabled(False)
        self.auto_cut_btn.setText("İşleniyor, Lütfen Bekleyin...")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        worker = Worker(cutter.auto_cut, source, out_path)
        worker.signals.result.connect(self._on_auto_cut_success)
        worker.signals.error.connect(self._on_auto_cut_error)
        worker.signals.finished.connect(self._on_auto_cut_finished)

        self.thread_pool.start(worker)

    def _on_auto_cut_success(self, path: Path) -> None:
        QMessageBox.information(self, "Başarılı", f"Sessizlikler temizlendi:\n{path.name}")

    def _on_auto_cut_error(self, error_data: tuple) -> None:
        exc, trace = error_data
        QMessageBox.critical(self, "Hata", f"İşlem sırasında hata oluştu:\n{str(exc)}")

    def _on_auto_cut_finished(self) -> None:
        self.auto_cut_btn.setEnabled(True)
        self.auto_cut_btn.setText("Sessizlikleri Temizle ve Kaydet")
        QApplication.restoreOverrideCursor()

    # --- KESME (TRIM) SEKMESI ---
    def _build_trim_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Videoyu Kes")
        form = QFormLayout(group)

        self.trim_input = QLineEdit()
        self.trim_input.setReadOnly(True)
        trim_browse = QPushButton("Seç")
        trim_browse.clicked.connect(lambda: self._browse_file(self.trim_input, "Video Seç", "Video Files (*.mp4 *.mov *.mkv)"))

        row_layout = QHBoxLayout()
        row_layout.addWidget(self.trim_input)
        row_layout.addWidget(trim_browse)

        self.start_time = QLineEdit("00:00:00")
        self.end_time = QLineEdit("00:00:10")

        form.addRow("Kaynak Video:", row_layout)
        form.addRow("Başlangıç (SS:DD:SS):", self.start_time)
        form.addRow("Bitiş (SS:DD:SS):", self.end_time)

        layout.addWidget(group)

        btn = QPushButton("Videoyu Kes ve Kaydet")
        btn.clicked.connect(self._run_trim)
        layout.addWidget(btn)
        layout.addStretch()

        return widget

    def _run_trim(self) -> None:
        source = self.trim_input.text()
        if not source:
            QMessageBox.warning(self, "Hata", "Lutfen bir video secin.")
            return

        start = self.start_time.text().strip()
        end = self.end_time.text().strip()

        out_path, _ = QFileDialog.getSaveFileName(self, "Kaydet", str(Path(source).parent / "kesilmis.mp4"), "MP4 (*.mp4)")
        if not out_path:
            return

        cmd = [
            "ffmpeg", "-y",
            "-i", source,
            "-ss", start,
            "-to", end,
            "-c", "copy",
            out_path
        ]
        self._execute_ffmpeg(cmd, "Video kesme islemi basariyla tamamlandi.")

    # --- BIRLESTIRME (MERGE) SEKMESI ---
    def _build_merge_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Videoları Birleştir (Aynı çözünürlük ve format önerilir)")
        vbox = QVBoxLayout(group)

        self.merge_list = QListWidget()
        vbox.addWidget(self.merge_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Video Ekle")
        add_btn.clicked.connect(self._add_to_merge_list)
        clear_btn = QPushButton("Listeyi Temizle")
        clear_btn.clicked.connect(self.merge_list.clear)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(clear_btn)
        vbox.addLayout(btn_row)

        layout.addWidget(group)

        btn = QPushButton("Videoları Birleştir ve Kaydet")
        btn.clicked.connect(self._run_merge)
        layout.addWidget(btn)

        return widget

    def _add_to_merge_list(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Videoları Seç", "", "Video Files (*.mp4 *.mov *.mkv)")
        if files:
            self.merge_list.addItems(files)

    def _run_merge(self) -> None:
        count = self.merge_list.count()
        if count < 2:
            QMessageBox.warning(self, "Hata", "Birlestirme icin en az 2 video eklemelisiniz.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Kaydet", str(Path.cwd() / "birlestirilmis.mp4"), "MP4 (*.mp4)")
        if not out_path:
            return

        # FFmpeg concat demuxer icin liste dosyasi olustur
        list_file = Path.cwd() / "merge_list.txt"
        with list_file.open("w", encoding="utf-8") as f:
            for i in range(count):
                # FFmpeg concat dosya yollarini cift tirnak icinde istemez ancak ozel karakterleri escape etmek gerekir.
                # En kolayi absolute path kullanip formatlamaktir.
                safe_path = Path(self.merge_list.item(i).text()).as_posix()
                f.write(f"file '{safe_path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            out_path
        ]
        success = self._execute_ffmpeg(cmd, "Videolar basariyla birlestirildi.")
        if list_file.exists():
            list_file.unlink()

    # --- SES CIKARMA (EXTRACT) SEKMESI ---
    def _build_audio_extract_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Sesi Çıkar")
        form = QFormLayout(group)

        self.audio_input = QLineEdit()
        self.audio_input.setReadOnly(True)
        audio_browse = QPushButton("Seç")
        audio_browse.clicked.connect(lambda: self._browse_file(self.audio_input, "Video Seç", "Video Files (*.mp4 *.mov *.mkv)"))

        row_layout = QHBoxLayout()
        row_layout.addWidget(self.audio_input)
        row_layout.addWidget(audio_browse)

        form.addRow("Kaynak Video:", row_layout)
        layout.addWidget(group)

        btn = QPushButton("Sesi MP3 Olarak Kaydet")
        btn.clicked.connect(self._run_audio_extract)
        layout.addWidget(btn)
        layout.addStretch()

        return widget

    def _run_audio_extract(self) -> None:
        source = self.audio_input.text()
        if not source:
            QMessageBox.warning(self, "Hata", "Lutfen bir video secin.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Kaydet", str(Path(source).with_suffix(".mp3")), "MP3 (*.mp3)")
        if not out_path:
            return

        cmd = [
            "ffmpeg", "-y",
            "-i", source,
            "-q:a", "0",
            "-map", "a",
            out_path
        ]
        self._execute_ffmpeg(cmd, "Ses basariyla cikarildi.")

    # --- YARDIMCI METOTLAR ---
    def _browse_file(self, line_edit: QLineEdit, title: str, filter_str: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, title, "", filter_str)
        if path:
            line_edit.setText(path)

    def _execute_ffmpeg(self, cmd: list[str], success_msg: str) -> bool:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "Bilinmeyen FFmpeg hatasi.")
            QMessageBox.information(self, "Basarili", success_msg)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Islem sirasinda hata olustu:\n{str(e)}")
            return False

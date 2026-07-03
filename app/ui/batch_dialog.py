from __future__ import annotations

from pathlib import Path

from app.ui.app_theme import ACCENT_TEAL, BTN_PRIMARY_GRADIENT, TEXT_MUTED
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from app.core.worker import Worker
from app.services.batch_service import BatchExportService, BatchResult
from app.services.export_service import ExportRequest, ExportService


class BatchExportDialog(QDialog):
    def __init__(
        self,
        request_template: ExportRequest,
        export_service: ExportService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Toplu Dışa Aktar")
        self.resize(640, 480)
        self.request_template = request_template
        self.export_service = export_service
        self.batch_service = BatchExportService()
        self.thread_pool = QThreadPool()
        self.output_dir = str(Path.cwd() / "output" / "batch")
        self._output_dir_customized = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        style_info = QLabel(
            f"Mevcut stil uygulanacak: {self.request_template.font_name} "
            f"{self.request_template.font_size}px | "
            f"{self.request_template.aspect_ratio}"
        )
        style_info.setStyleSheet(f"color: {ACCENT_TEAL}; font-weight: bold;")
        layout.addWidget(style_info)

        group = QGroupBox("Video Listesi")
        group_layout = QVBoxLayout(group)

        self.video_list = QListWidget()
        group_layout.addWidget(self.video_list)

        row = QHBoxLayout()
        add_btn = QPushButton("Video Ekle")
        add_btn.clicked.connect(self._add_videos)
        clear_btn = QPushButton("Listeyi Temizle")
        clear_btn.clicked.connect(self.video_list.clear)
        row.addWidget(add_btn)
        row.addWidget(clear_btn)
        group_layout.addLayout(row)
        layout.addWidget(group)

        options = QGroupBox("Secenekler")
        opt_layout = QVBoxLayout(options)
        self.auto_srt_checkbox = QCheckBox("Ayni isimli .srt dosyasini otomatik eslestir")
        self.auto_srt_checkbox.setChecked(True)
        opt_layout.addWidget(self.auto_srt_checkbox)

        out_row = QHBoxLayout()
        self.output_label = QLabel(self.output_dir)
        self.output_label.setStyleSheet(f"color: {TEXT_MUTED};")
        out_btn = QPushButton("Cikti Klasoru")
        out_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(self.output_label, 1)
        out_row.addWidget(out_btn)
        opt_layout.addLayout(out_row)
        layout.addWidget(options)

        footer = QHBoxLayout()
        self.start_btn = QPushButton("Toplu Dışa Aktar")
        self.start_btn.setStyleSheet(f"background: {BTN_PRIMARY_GRADIENT}; font-weight: bold;")
        self.start_btn.clicked.connect(self._start_batch)
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.reject)
        footer.addStretch(1)
        footer.addWidget(close_btn)
        footer.addWidget(self.start_btn)
        layout.addLayout(footer)

    def _add_videos(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Videolari Sec",
            "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm)",
        )
        if files:
            self.video_list.addItems(files)
            if not self._output_dir_customized:
                self.output_dir = str(Path(files[0]).resolve().parent)
                self.output_label.setText(self.output_dir)

    def _pick_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Cikti Klasoru", self.output_dir)
        if folder:
            self.output_dir = folder
            self._output_dir_customized = True
            self.output_label.setText(folder)

    def _start_batch(self) -> None:
        videos = [self.video_list.item(i).text() for i in range(self.video_list.count())]
        if not videos:
            QMessageBox.warning(self, "Uyari", "Lutfen en az bir video ekleyin.")
            return

        jobs = self.batch_service.build_jobs(
            videos,
            self.output_dir,
            auto_match_srt=self.auto_srt_checkbox.isChecked(),
        )

        missing = [job for job in jobs if not job.srt_path]
        if missing:
            names = "\n".join(Path(job.video_path).name for job in missing[:8])
            extra = f"\n... ve {len(missing) - 8} dosya daha" if len(missing) > 8 else ""
            answer = QMessageBox.question(
                self,
                "SRT Eksik",
                f"{len(missing)} video icin SRT bulunamadi:\n{names}{extra}\n\n"
                "SRT'si olmayan videolar atlanacak. Devam edilsin mi?",
            )
            if answer != QMessageBox.Yes:
                return

        progress = QProgressDialog("Toplu islem basliyor...", None, 0, 100, self)
        progress.setWindowTitle("Toplu Dışa Aktar")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        worker = Worker(
            self.batch_service.run_batch,
            jobs,
            self.request_template,
            self.export_service,
            progress_callback=lambda _msg: None,
            total_duration_ms=60_000,
        )

        def on_progress(message: str) -> None:
            if "|" in message:
                pct_str, label = message.split("|", 1)
                try:
                    progress.setValue(int(pct_str))
                except ValueError:
                    pass
                progress.setLabelText(label)
            QApplication.processEvents()

        worker.signals.progress.connect(on_progress)
        worker.signals.result.connect(lambda results: self._on_batch_done(results))
        worker.signals.error.connect(lambda err: self._on_batch_error(err))
        worker.signals.finished.connect(progress.close)

        self.start_btn.setEnabled(False)
        self.thread_pool.start(worker)

    def _on_batch_done(self, results: list[BatchResult]) -> None:
        self.start_btn.setEnabled(True)
        ok = sum(1 for item in results if item.success)
        fail = len(results) - ok
        lines = [f"Basarili: {ok}", f"Basarisiz: {fail}", ""]
        for item in results[:12]:
            status = "OK" if item.success else "HATA"
            lines.append(f"[{status}] {Path(item.video_path).name} â€” {item.message}")
        QMessageBox.information(self, "Toplu Islem Ozeti", "\n".join(lines))

    def _on_batch_error(self, error_data: tuple) -> None:
        self.start_btn.setEnabled(True)
        _exc, trace = error_data
        QMessageBox.critical(self, "Toplu Islem Hatasi", str(trace))

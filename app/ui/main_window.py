from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer, QSize, QUrl, QPointF
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFontDatabase,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPen,
    QPolygonF,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
    QMenuBar,
    QToolBar,
    QToolButton,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import qtawesome as qta

from app.core.edit_history import EditHistory, capture_snapshot, restore_snapshot
from app.core.ffmpeg_paths import ensure_ffmpeg_on_path, ffmpeg_missing_message
from app.core.media_probe import probe_media
from app.core.timeline import TRACK_AUDIO, TRACK_VIDEO, TimelineModel
from app.core.timeline_subtitles import (
    remap_subtitles_for_segments,
    ripple_delete_subtitles,
    split_subtitles_at,
)
from app.ui.timeline_panel import TimelinePanel
from app.ui.main_window_controls import MainWindowControlsMixin
from app.ui.main_window_preview import MainWindowPreviewMixin

from app.core.animation_presets import animation_from_legacy
from app.core.style_presets import CUSTOM_PRESET_NAME, default_aspect_ratio_options, get_preset
from app.core.subtitle_parser import parse_srt
from app.core.word_timing_data import (
    WordTimingDocument,
    build_timed_subtitles,
    document_from_entries,
    load_word_timing_document,
    save_word_timing_document,
    word_timing_path_for_srt,
)
from app.core.worker import Worker
from app.services.export_service import ExportRequest, ExportService
from app.services.thumbnail_service import ThumbnailService
from app.services.waveform_service import WaveformService
from app.services.project_service import PROJECT_EXTENSION, ProjectService, ProjectStyle
from app.services.transcription_service import TranscriptionResult, TranscriptionService
from app.ui.batch_dialog import BatchExportDialog
from app.ui.clip_effects_dialog import ClipEffectsDialog
from app.ui.export_dialog import ExportDialog
from app.ui.subtitle_editor import SubtitleEditorDialog
from app.ui.transcription_dialog import TranscriptionDialog
from app.ui.video_tools_dialog import VideoToolsDialog


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv"}
PLACEHOLDER_CLIP_DURATION_MS = 10_000


class MainWindow(QMainWindow, MainWindowControlsMixin, MainWindowPreviewMixin):

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)

        self.video_path: str | None = None
        self.subtitle_path: str | None = None
        self.subtitle_entries = []
        self.timeline_model = TimelineModel()
        self.timed_subtitles: list = []
        self.current_time_ms = 0
        self.normal_color = QColor("#FFFFFF")
        self.active_color = QColor("#3B82F6")
        self.logo_path = ""
        self.export_service = ExportService()
        self.thumbnail_service = ThumbnailService()
        self.waveform_service = WaveformService()
        self.transcription_service = TranscriptionService()
        self.edit_history = EditHistory()
        self.project_service = ProjectService()
        self.project_path: str | None = None
        self.word_timing_doc: WordTimingDocument | None = None
        self.thread_pool = QThreadPool()

        # Medya Oynatici (Gercek video onizlemesi)
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.durationChanged.connect(self._on_video_duration_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        # Alternatif onizleme zamanlayicisi (Video yoksa SRT onizlemesi icin)
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(80)
        self.preview_timer.timeout.connect(self._advance_preview)

        self.setWindowTitle("Ares Editor 2026")
        self.resize(1180, 760)

        self._build_ui()
        self._refresh_preview()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Ana bolucu (Ust: Ayarlar+Onizleme, Alt: Timeline)
        main_splitter = QSplitter(Qt.Vertical)

        # Ust bolucu (Sol: Ayarlar, Sag: Onizleme)
        top_splitter = QSplitter(Qt.Horizontal)

        controls = self._build_controls_panel()
        preview = self._build_preview_panel()

        top_splitter.addWidget(controls)
        top_splitter.addWidget(preview)
        
        # Sag paneli daralt (Ornegin Sol: 1, Sag: 1 veya sabit boyut)
        top_splitter.setStretchFactor(0, 5)
        top_splitter.setStretchFactor(1, 4)

        self.timeline_panel = TimelinePanel(self.timeline_model)
        self.timeline_panel.split_requested.connect(self._split_at_playhead)
        self.timeline_panel.delete_requested.connect(self._delete_selected_clips)
        self.timeline_panel.add_media_requested.connect(self._add_media_to_timeline)
        self.timeline_panel.playhead_changed.connect(self._on_timeline_playhead)
        self.timeline_panel.clip_selected.connect(self._on_clip_selected)
        self.timeline_panel.clip_moved.connect(self._on_clip_moved)
        self.timeline_panel.clip_drag_finished.connect(self._on_clip_drag_finished)
        self.timeline_panel.clip_trim_finished.connect(self._on_clip_trim_finished)
        self.timeline_panel.undo_requested.connect(self._undo)
        self.timeline_panel.redo_requested.connect(self._redo)
        self.timeline_panel.effects_requested.connect(self._open_clip_effects)
        self.timeline_panel.files_dropped.connect(self._import_timeline_files)

        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.timeline_panel)
        # Ust taraf 3 birim, Alt taraf 1 birim yukseklikte
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(main_splitter)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("Video ve SRT dosyalarini secerek baslayin.")
        
        self._build_menu_bar()
        self._build_tool_bar()
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Undo, self, self._undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, self._redo)
        QShortcut(QKeySequence.StandardKey.Save, self, self._save_project)
        QShortcut(QKeySequence.StandardKey.Open, self, self._open_project)

    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")
        
        file_menu = menubar.addMenu("Dosya")
        edit_menu = menubar.addMenu("Düzenle")
        view_menu = menubar.addMenu("Oynat")
        settings_menu = menubar.addMenu("Ayarlar")
        export_menu = menubar.addMenu("Dışa Aktar")
        batch_menu_action = QAction("Toplu Disa Aktar...", self)
        batch_menu_action.triggered.connect(self._open_batch_export)
        export_menu.addAction(batch_menu_action)

        help_menu = menubar.addMenu("Yardım")

        self.undo_action = QAction("Geri Al", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self._undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("Yinele", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self._redo)
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        self.save_project_action = QAction("Projeyi Kaydet", self)
        self.save_project_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_project_action.triggered.connect(self._save_project)
        file_menu.addAction(self.save_project_action)

        self.save_project_as_action = QAction("Projeyi Farkli Kaydet...", self)
        self.save_project_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(self.save_project_as_action)

        self.open_project_action = QAction("Proje Ac...", self)
        self.open_project_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_project_action.triggered.connect(self._open_project)
        file_menu.addAction(self.open_project_action)

        file_menu.addSeparator()
        exit_action = QAction("Çıkış", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _build_tool_bar(self) -> None:
        toolbar = QToolBar("Ana Araçlar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar { background-color: #1E293B; border-bottom: 1px solid #334155; padding: 4px; } "
            "QToolButton { color: #F8FAFC; font-weight: bold; font-size: 11px; padding: 4px 8px; border-radius: 4px; } "
            "QToolButton:hover { background-color: #334155; }"
        )
        self.addToolBar(toolbar)

        brand = QLabel("ARES")
        brand.setStyleSheet(
            "font-family: 'Michroma', 'Segoe UI', sans-serif; font-size: 10px; "
            "color: #2DD4BF; letter-spacing: 3px; padding: 0 10px 0 4px;"
        )
        toolbar.addWidget(brand)
        toolbar.addSeparator()

        # Görseldeki gibi yan yana hızlı erişim butonları
        import_action = QAction("➕ İçe Aktar", self)
        import_action.triggered.connect(self._pick_timeline_video)
        toolbar.addAction(import_action)

        open_project_action = QAction("📂 Proje Aç", self)
        open_project_action.triggered.connect(self._open_project)
        toolbar.addAction(open_project_action)

        save_project_action = QAction("💾 Kaydet", self)
        save_project_action.triggered.connect(self._save_project)
        toolbar.addAction(save_project_action)

        toolbar.addSeparator()

        video_tools_action = QAction("✂ Video Kes/Birleştir", self)
        video_tools_action.triggered.connect(self._open_video_tools)
        toolbar.addAction(video_tools_action)

        split_action = QAction("✂ Böl", self)
        split_action.triggered.connect(self._split_at_playhead)
        toolbar.addAction(split_action)

        self.toolbar_undo = QAction("↩ Geri Al", self)
        self.toolbar_undo.triggered.connect(self._undo)
        toolbar.addAction(self.toolbar_undo)

        self.toolbar_redo = QAction("↪ Yinele", self)
        self.toolbar_redo.triggered.connect(self._redo)
        toolbar.addAction(self.toolbar_redo)

        toolbar.addSeparator()

        delete_action = QAction("🗑 Sil", self)
        delete_action.triggered.connect(self._delete_selected_clips)
        toolbar.addAction(delete_action)

        add_media_action = QAction("➕ Şeride Ekle", self)
        add_media_action.triggered.connect(self._add_media_to_timeline)
        toolbar.addAction(add_media_action)

        edit_subtitle_action = QAction("📝 Altyazı Düzenle", self)
        edit_subtitle_action.triggered.connect(self._open_subtitle_editor)
        toolbar.addAction(edit_subtitle_action)

        translate_action = QAction("🌐 Whisper Çeviri", self)
        translate_action.triggered.connect(lambda: self._run_transcription(translate=True))
        toolbar.addAction(translate_action)
        
        denoise_action = QAction("🎧 Sesi Temizle", self)
        denoise_action.triggered.connect(lambda: self.denoise_checkbox.setChecked(not self.denoise_checkbox.isChecked()))
        toolbar.addAction(denoise_action)

        toolbar.addSeparator()

        batch_action = QAction("📦 Toplu İşlem", self)
        batch_action.triggered.connect(self._open_batch_export)
        toolbar.addAction(batch_action)

        export_action = QAction("🚀 Dışa Aktar", self)
        export_action.triggered.connect(self._prepare_export)
        toolbar.addAction(export_action)

    def _probe_duration_ms(self, file_path: str, use_player: bool = True) -> int:
        probe = probe_media(file_path)
        if probe.duration_ms > 0:
            return probe.duration_ms
        if not use_player:
            return 0
        player_ms = self.media_player.duration()
        if player_ms > 0 and (
            not self.video_path
            or Path(self.video_path).resolve() == Path(file_path).resolve()
        ):
            return player_ms
        return 0

    def _resolve_video_duration_ms(self, file_path: str) -> int | None:
        """Video suresini ffprobe ile okur; gerekirse oynaticidan dener."""
        duration_ms = self._probe_duration_ms(file_path, use_player=True)
        if duration_ms > 0:
            return duration_ms

        probe = probe_media(file_path)
        detail = probe.error or ffmpeg_missing_message()
        QMessageBox.critical(
            self,
            "Medya Hatasi",
            f"Video suresi okunamadi:\n{Path(file_path).name}\n\n{detail}",
        )
        return None

    def _ensure_timeline_has_video_clip(self) -> bool:
        """Onizleme acikken timeline bos kaldıysa klip olusturur."""
        if not self.video_path or not Path(self.video_path).exists():
            return False
        if self.timeline_model.clips_on_track(TRACK_VIDEO):
            return True

        duration_ms = self._probe_duration_ms(self.video_path, use_player=True)
        if duration_ms <= 0:
            duration_ms = PLACEHOLDER_CLIP_DURATION_MS

        self.timeline_model.replace_primary_media(self.video_path, duration_ms)
        if self.timed_subtitles:
            end_ms = max(duration_ms, self.timed_subtitles[-1].end_ms)
            self.timeline_model.replace_subtitle_span(end_ms)

        total = max(duration_ms, self.timeline_model.duration_ms)
        self.timeline_panel.configure_duration(total)
        self.timeline_panel.refresh()
        QTimer.singleShot(0, self._generate_instant_filmstrip)
        if not self.edit_history.can_undo() and not self.edit_history.can_redo():
            self._seed_history()
        self.statusBar().showMessage(
            f"Timeline senkronlandi: {Path(self.video_path).name} ({total // 1000}s)"
        )
        return True

    def _schedule_timeline_sync_retries(self) -> None:
        for delay_ms in (150, 500, 1200, 3000):
            QTimer.singleShot(delay_ms, self._sync_video_timeline_if_needed)

    def _sync_video_timeline_if_needed(self) -> None:
        """Oynatici veya dosya seciliyken timeline klipi yoksa olusturur."""
        if not self.video_path or not Path(self.video_path).exists():
            return

        duration_ms = self._probe_duration_ms(self.video_path, use_player=True)
        video_clips = self.timeline_model.clips_on_track(TRACK_VIDEO)

        if duration_ms <= 0:
            if not video_clips:
                self._schedule_timeline_sync_retries()
            return

        if not video_clips:
            self._ensure_timeline_media(duration_ms)
            if not self.timeline_model.clips_on_track(TRACK_VIDEO):
                QMessageBox.warning(
                    self,
                    "Timeline Hatasi",
                    f"Video yuklendi ancak timeline klipi olusturulamadi.\n\n{ffmpeg_missing_message()}",
                )
                return
        elif self.timeline_model.rescale_primary_media_duration(self.video_path, duration_ms):
            self._generate_thumbnails()

        total = max(duration_ms, self.timeline_model.duration_ms)
        self.timeline_panel.configure_duration(total)
        self.timeline_panel.refresh()

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            self._ensure_timeline_has_video_clip()
            self._sync_video_timeline_if_needed()

    def _import_video_to_timeline(self, file_path: str, at_ms: int | None = None) -> bool:
        """Dosyayi once timeline'a ekler; sure bilinmiyorsa gecici klip gosterir (NLE kalibi)."""
        file_path = str(Path(file_path).resolve())

        duration_ms = self._probe_duration_ms(file_path, use_player=False)
        used_placeholder = duration_ms <= 0
        if used_placeholder:
            duration_ms = PLACEHOLDER_CLIP_DURATION_MS

        video_clips = self.timeline_model.clips_on_track(TRACK_VIDEO)
        if at_ms is None:
            if not video_clips:
                at_ms = 0
            else:
                at_ms = max(self.timeline_model.duration_ms, self.current_time_ms)

        if not video_clips and at_ms == 0:
            self.timeline_model.replace_primary_media(file_path, duration_ms)
            if self.timed_subtitles:
                end_ms = max(duration_ms, self.timed_subtitles[-1].end_ms)
                self.timeline_model.replace_subtitle_span(end_ms)
        else:
            self.timeline_model.add_media_clip(file_path, at_ms=at_ms, duration_ms=duration_ms)

        self._sync_preview_video(file_path)

        total = max(duration_ms, self.timeline_model.duration_ms)
        self.timeline_panel.configure_duration(total)
        self.timeline_panel.refresh()
        if not self.edit_history.can_undo() and not self.edit_history.can_redo():
            self._seed_history()
        else:
            self._commit_history()
        self._update_actions()

        clip_count = len(self.timeline_model.clips_on_track(TRACK_VIDEO))
        if used_placeholder:
            self._schedule_timeline_sync_retries()
            self.statusBar().showMessage(
                f"Timeline klipi olusturuldu (sure okunuyor): {Path(file_path).name}"
            )
        else:
            self.statusBar().showMessage(
                f"Timeline'a eklendi: {Path(file_path).name} "
                f"({clip_count} video klip, {total // 1000}s)"
            )
        QTimer.singleShot(100, self.timeline_panel.refresh)
        QTimer.singleShot(0, self._generate_instant_filmstrip)
        return True

    def _generate_instant_filmstrip(self) -> None:
        """Import sonrasi filmstrip'i gecikmeden baslatir."""
        if not ensure_ffmpeg_on_path():
            return
        thumbs: dict[str, list[Path]] = {}
        for clip in self.timeline_model.clips_on_track(TRACK_VIDEO):
            if not clip.source_path:
                continue
            duration = max(clip.duration_ms, 500)
            strip = self.thumbnail_service.generate_strip(
                clip.source_path,
                clip.source_start_ms,
                clip.resolved_source_end_ms,
                count=max(4, min(16, duration // 200)),
                height=52,
            )
            if strip:
                thumbs[clip.clip_id] = strip
        if thumbs:
            self.timeline_panel.set_media_previews(thumbnails=thumbs, replace=False)
            self.statusBar().showMessage("Timeline filmstrip hazir.")
        self._generate_thumbnails()

    def _sync_preview_video(self, file_path: str) -> None:
        """Onizleme oynaticisini secilen dosyayla esitler."""
        self.video_path = file_path
        self.video_input.setText(file_path)
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.pause()

    def _import_timeline_files(self, paths: list[str]) -> None:
        """Movavi tarzi: medya dogrudan timeline'dan yuklenir, klip hemen olusur."""
        imported = 0
        for file_path in paths:
            ext = Path(file_path).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                if self._import_video_to_timeline(file_path):
                    imported += 1
            elif ext == ".srt":
                self._load_subtitle(file_path)
                self._parse_subtitle()
                imported += 1

        if imported:
            self.statusBar().showMessage(f"Timeline'a {imported} dosya eklendi.")

    def _pick_timeline_video(self) -> None:
        start_dir = ""
        if self.video_path:
            start_dir = str(Path(self.video_path).parent)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Timeline'a Video Ekle",
            start_dir,
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv);;All Files (*)",
        )
        if file_path:
            self._import_video_to_timeline(file_path)

    def _ensure_timeline_media(self, duration_ms: int) -> None:
        if not self.video_path or duration_ms <= 0:
            return

        video_clips = self.timeline_model.clips_on_track(TRACK_VIDEO)
        needs_rebuild = (
            not video_clips
            or Path(video_clips[0].source_path or "").resolve()
            != Path(self.video_path).resolve()
            or abs(video_clips[0].duration_ms - duration_ms) > 500
        )
        if needs_rebuild:
            self.timeline_model.replace_primary_media(self.video_path, duration_ms)
            if self.timed_subtitles:
                end_ms = max(duration_ms, self.timed_subtitles[-1].end_ms)
                self.timeline_model.replace_subtitle_span(end_ms)
            self._generate_thumbnails()
            if not self.edit_history.can_undo() and not self.edit_history.can_redo():
                self._seed_history()

        total = max(duration_ms, self.timeline_model.duration_ms)
        self.timeline_panel.configure_duration(total)
        self.timeline_panel.refresh()
        clip_count = len(self.timeline_model.clips_on_track(TRACK_VIDEO))
        self.statusBar().showMessage(
            f"Timeline hazir: {clip_count} video klip, sure {total // 1000}s"
        )
        QTimer.singleShot(100, self.timeline_panel.refresh)

    def _clear_video(self) -> None:
        self.video_path = None
        self.video_input.setText("")
        self.media_player.setSource(QUrl())
        self.timeline_model.clear()
        self.timeline_panel.configure_duration(0)
        self.timeline_panel.set_media_previews(thumbnails={}, waveforms={})
        self.edit_history.clear()
        self._update_history_buttons()
        self._refresh_preview()
        self._update_actions()

    def _on_video_timeline_ready(self, duration: int) -> None:
        self._ensure_timeline_media(duration)

    def _seed_history(self) -> None:
        self.edit_history.seed(
            capture_snapshot(self.timeline_model, self.subtitle_entries, self.word_timing_doc)
        )
        self._update_history_buttons()

    def _commit_history(self) -> None:
        self.edit_history.push(
            capture_snapshot(self.timeline_model, self.subtitle_entries, self.word_timing_doc)
        )
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        can_undo = self.edit_history.can_undo()
        can_redo = self.edit_history.can_redo()
        self.timeline_panel.set_history_state(can_undo, can_redo)
        if hasattr(self, "undo_action"):
            self.undo_action.setEnabled(can_undo)
            self.redo_action.setEnabled(can_redo)
        if hasattr(self, "toolbar_undo"):
            self.toolbar_undo.setEnabled(can_undo)
            self.toolbar_redo.setEnabled(can_redo)

    def _apply_snapshot(self, snapshot) -> None:
        entries, timed, word_doc = restore_snapshot(self.timeline_model, snapshot)
        self.subtitle_entries = entries
        self.timed_subtitles = timed
        self.word_timing_doc = word_doc
        self.timeline_panel.configure_duration(self.timeline_model.duration_ms)
        self._generate_thumbnails()
        self._refresh_preview()
        self._update_actions()

    def _undo(self) -> None:
        state = self.edit_history.undo()
        if state is None:
            return
        self._apply_snapshot(state)
        self._update_history_buttons()
        self.statusBar().showMessage("Geri alindi.")

    def _redo(self) -> None:
        state = self.edit_history.redo()
        if state is None:
            return
        self._apply_snapshot(state)
        self._update_history_buttons()
        self.statusBar().showMessage("Yinelendi.")

    def _generate_thumbnails(self) -> None:
        if not self.timeline_model.clips_on_track(TRACK_VIDEO) and not self.timeline_model.clips_on_track(TRACK_AUDIO):
            return
        worker = Worker(self._build_media_previews)
        worker.signals.result.connect(self._on_media_previews_ready)
        worker.signals.error.connect(self._on_media_preview_error)
        self.statusBar().showMessage("Timeline onizlemeleri hazirlaniyor (FFmpeg)...")
        self.thread_pool.start(worker)

    def _on_media_previews_ready(self, payload: tuple) -> None:
        thumbs, waves = payload
        self.timeline_panel.set_media_previews(thumbnails=thumbs, waveforms=waves)
        self.statusBar().showMessage(
            f"Timeline onizleme hazir: {len(thumbs)} video, {len(waves)} ses seridi."
        )

    def _on_media_preview_error(self, error_data: tuple) -> None:
        _exc, trace = error_data
        ffmpeg_path = ensure_ffmpeg_on_path() or "(bulunamadi)"
        detail = str(trace).strip() or str(_exc)
        QMessageBox.warning(
            self,
            "Onizleme Hatasi",
            f"Timeline onizlemesi uretilemedi.\n\n"
            f"FFmpeg: {ffmpeg_path}\n\n{detail}",
        )
        self.statusBar().showMessage("Timeline onizleme uretilemedi.")
        self.timeline_panel.refresh()

    def _build_media_previews(self) -> tuple[dict, dict]:
        if not ensure_ffmpeg_on_path():
            raise RuntimeError(ffmpeg_missing_message())

        thumbs: dict = {}
        waves: dict = {}
        for clip in self.timeline_model.clips_on_track(TRACK_VIDEO):
            if not clip.source_path:
                continue
            duration = max(clip.duration_ms, clip.resolved_source_end_ms - clip.source_start_ms)
            count = max(4, min(32, duration // 200))
            strip = self.thumbnail_service.generate_strip(
                clip.source_path,
                clip.source_start_ms,
                clip.resolved_source_end_ms,
                count=count,
                height=52,
            )
            if strip:
                thumbs[clip.clip_id] = strip

        for clip in self.timeline_model.clips_on_track(TRACK_AUDIO):
            if not clip.source_path:
                continue
            duration = clip.resolved_source_end_ms - clip.source_start_ms
            width = max(200, min(1600, duration // 8))
            wave = self.waveform_service.generate_waveform(
                clip.source_path,
                clip.source_start_ms,
                clip.resolved_source_end_ms,
                width=width,
                height=36,
            )
            if wave:
                waves[clip.clip_id] = wave

        return thumbs, waves

    def _on_clip_moved(self, clip_id: str, new_start_ms: int) -> None:
        self.timeline_model.move_clip(clip_id, new_start_ms)
        self.timeline_panel.refresh()

    def _on_clip_drag_finished(self, clip_id: str, new_start_ms: int) -> None:
        self.timeline_model.move_clip(clip_id, new_start_ms)
        self.timeline_panel.refresh()
        self._generate_thumbnails()
        self._commit_history()

    def _on_clip_trim_finished(self, _clip_id: str) -> None:
        self._generate_thumbnails()
        self._commit_history()

    def _load_subtitle(self, file_path: str) -> None:
        self.subtitle_path = file_path
        self.subtitle_input.setText(file_path)
        self.statusBar().showMessage(f"Altyazi secildi: {Path(file_path).name}")
        self._parse_subtitle()

    def _clear_subtitle(self) -> None:
        self.subtitle_path = None
        self.subtitle_input.setText("")
        self.timed_subtitles = []
        self.subtitle_entries = []
        self.timeline_model.replace_subtitle_span(0)
        self.timeline_panel.refresh()
        self._refresh_preview()
        self._update_actions()

    def _select_subtitle(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "SRT Sec",
            "",
            "Subtitle Files (*.srt);;All Files (*)",
        )
        if file_path:
            self._load_subtitle(file_path)

    def _select_logo(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Logo Sec",
            "",
            "Image Files (*.png *.jpg *.jpeg);;All Files (*)",
        )
        if not file_path:
            return

        self.logo_path = file_path
        self.logo_input.setText(file_path)
        self.statusBar().showMessage(f"Logo secildi: {Path(file_path).name}")

    def _on_clip_selected(self, clip_id: str, additive: bool) -> None:
        self.timeline_model.select_clip(clip_id, additive=additive)
        self.timeline_panel.refresh()

    def _split_at_playhead(self) -> None:
        split_time = self.current_time_ms
        if split_time <= 0:
            self.statusBar().showMessage("Bolme icin playhead'i ileri alin.")
            return

        count = self.timeline_model.split_at(split_time)
        if count == 0:
            self.statusBar().showMessage("Bu konumda bolunecek klip yok.")
            return

        if self.timed_subtitles:
            self.timed_subtitles = split_subtitles_at(self.timed_subtitles, split_time)
            self.subtitle_entries = [ts.entry for ts in self.timed_subtitles]
            self._sync_word_timing_doc()

        self.timeline_panel.refresh()
        self._generate_thumbnails()
        self._commit_history()
        self.statusBar().showMessage(f"Klipler {self._format_ms(split_time)} konumunda bolundu.")

    def _delete_selected_clips(self) -> None:
        removed = []
        for clip in list(self.timeline_model.selected_clips()):
            if clip.track in ("video", "audio"):
                removed.append((clip.timeline_start_ms, clip.timeline_end_ms))

        deleted = self.timeline_model.delete_selected()
        if deleted == 0:
            self.statusBar().showMessage("Silmek icin once bir klip secin.")
            return

        if self.timed_subtitles and removed:
            for start_ms, end_ms in removed:
                self.timed_subtitles = ripple_delete_subtitles(self.timed_subtitles, start_ms, end_ms)
            self.subtitle_entries = [ts.entry for ts in self.timed_subtitles]
            last_ms = self.timed_subtitles[-1].end_ms if self.timed_subtitles else 0
            self.timeline_model.replace_subtitle_span(last_ms)
            self._sync_word_timing_doc()

        self.timeline_panel.configure_duration(self.timeline_model.duration_ms)
        self._generate_thumbnails()
        self._commit_history()
        self.statusBar().showMessage(f"{deleted} klip silindi.")

    def _add_media_to_timeline(self) -> None:
        self._pick_timeline_video()

    def _sync_word_timing_doc(self) -> None:
        if not self.subtitle_entries:
            self.word_timing_doc = None
            return
        self.word_timing_doc = document_from_entries(self.subtitle_entries, self.timed_subtitles)
        if self.subtitle_path:
            save_word_timing_document(
                self.word_timing_doc,
                word_timing_path_for_srt(self.subtitle_path),
            )

    def _load_word_timing_sidecar(self) -> None:
        if not self.subtitle_path:
            self.word_timing_doc = None
            return
        sidecar = word_timing_path_for_srt(self.subtitle_path)
        self.word_timing_doc = load_word_timing_document(sidecar)

    def _collect_project_style(self) -> ProjectStyle:
        return ProjectStyle(
            font_name=self.font_combo.currentText(),
            font_size=self.font_size_spin.value(),
            normal_color=self.normal_color.name(),
            active_color=self.active_color.name(),
            stroke_size=self.stroke_spin.value(),
            shadow_size=self.shadow_spin.value(),
            position=self.position_combo.currentText(),
            use_animation=self.anim_combo.currentText() != "Yok",
            animation_style=self.anim_combo.currentText(),
            bg_box=self.bg_box_checkbox.isChecked(),
            logo_path=self.logo_path,
            logo_pos=self.logo_pos_combo.currentText(),
            logo_size=self.logo_size_spin.value(),
            aspect_ratio=self.format_combo.currentText(),
            fps=self.fps_combo.currentText(),
            audio_bitrate=self.audio_quality_combo.currentText(),
            denoise_audio=self.denoise_checkbox.isChecked(),
            use_gpu=self.gpu_checkbox.isChecked(),
            translate=False,
            preset_name=self.preset_combo.currentText() if hasattr(self, "preset_combo") else CUSTOM_PRESET_NAME,
        )

    def _apply_project_style(self, style: ProjectStyle) -> None:
        self.font_combo.setCurrentText(style.font_name)
        self.font_size_spin.setValue(style.font_size)
        self.normal_color = QColor(style.normal_color)
        self.active_color = QColor(style.active_color)
        self._update_color_button("normal")
        self._update_color_button("active")
        self.stroke_spin.setValue(style.stroke_size)
        self.shadow_spin.setValue(style.shadow_size)
        self.position_combo.setCurrentText(style.position)
        self.anim_combo.setCurrentText(
            style.animation_style
            if getattr(style, "animation_style", None)
            else animation_from_legacy(style.use_animation)
        )
        self.bg_box_checkbox.setChecked(style.bg_box)
        self.logo_path = style.logo_path
        self.logo_input.setText(style.logo_path)
        self.logo_pos_combo.setCurrentText(style.logo_pos)
        self.logo_size_spin.setValue(style.logo_size)
        self.format_combo.setCurrentText(style.aspect_ratio)
        self.fps_combo.setCurrentText(style.fps)
        self.audio_quality_combo.setCurrentText(style.audio_bitrate)
        self.denoise_checkbox.setChecked(style.denoise_audio)
        self.gpu_checkbox.setChecked(style.use_gpu)
        if hasattr(self, "preset_combo"):
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentText(style.preset_name)
            self.preset_combo.blockSignals(False)
            preset = get_preset(style.preset_name)
            self.preset_desc_label.setText(preset.description if preset else "")

    def _save_project(self) -> None:
        if not self.project_path:
            self._save_project_as()
            return
        self._write_project(self.project_path)

    def _save_project_as(self) -> None:
        default = str(Path.cwd() / "output" / "proje.aresproj")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Projeyi Kaydet",
            default,
            f"Ares Proje (*{PROJECT_EXTENSION})",
        )
        if not file_path:
            return
        if not file_path.endswith(PROJECT_EXTENSION):
            file_path += PROJECT_EXTENSION
        self._write_project(file_path)

    def _write_project(self, file_path: str) -> None:
        try:
            saved = self.project_service.save(
                file_path,
                video_path=self.video_path or "",
                subtitle_path=self.subtitle_path or "",
                timeline_model=self.timeline_model,
                subtitle_entries=self.subtitle_entries,
                word_document=self.word_timing_doc,
                style=self._collect_project_style(),
                current_time_ms=self.current_time_ms,
                zoom_level=self.timeline_panel.zoom_level,
                playback_speed=self.speed_combo.currentText(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Kayit Hatasi", str(exc))
            return

        self.project_path = str(saved)
        self.setWindowTitle(f"Ares Editor 2026 — {saved.stem}")
        self.statusBar().showMessage(f"Proje kaydedildi: {saved.name}")

    def _open_project(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Proje Ac",
            str(Path.cwd() / "output"),
            f"Ares Proje (*{PROJECT_EXTENSION})",
        )
        if not file_path:
            return
        self._load_project(file_path)

    def _load_project(self, file_path: str) -> None:
        try:
            project = self.project_service.load(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Proje Hatasi", str(exc))
            return

        if project.video_path and not Path(project.video_path).exists():
            QMessageBox.warning(
                self,
                "Dosya Eksik",
                f"Video bulunamadi:\n{project.video_path}",
            )

        self.project_path = file_path
        self.setWindowTitle(f"Ares Editor 2026 — {project.project_name}")

        self.project_service.apply_timeline(self.timeline_model, project.timeline)
        self.timeline_panel._set_edit_mode(project.timeline.get("edit_mode", "ripple"))

        if project.video_path and Path(project.video_path).exists():
            self.video_path = project.video_path
            self.video_input.setText(project.video_path)
            self.media_player.setSource(QUrl.fromLocalFile(project.video_path))
            self.media_player.pause()
        else:
            self._clear_video()
            self.project_service.apply_timeline(self.timeline_model, project.timeline)

        self.subtitle_entries = self.project_service.deserialize_subtitle_entries(
            project.subtitle_entries
        )
        self.word_timing_doc = self.project_service.deserialize_word_document(project.word_timing)
        self.timed_subtitles = build_timed_subtitles(
            self.subtitle_entries,
            self.word_timing_doc,
        )

        if project.subtitle_path:
            self.subtitle_path = project.subtitle_path
            self.subtitle_input.setText(project.subtitle_path)

        style = self.project_service.deserialize_style(project.style)
        self._apply_project_style(style)

        playback = project.playback
        self.timeline_panel.zoom_level = float(playback.get("zoom_level", 1.0))
        speed = str(playback.get("speed", "1.0x"))
        self.speed_combo.setCurrentText(speed)
        self._change_speed(speed)

        duration = max(self.timeline_model.duration_ms, self.media_player.duration())
        if not self.timeline_model.clips_on_track(TRACK_VIDEO) and self.video_path:
            self._ensure_timeline_has_video_clip()
            duration = max(duration, self.timeline_model.duration_ms)

        self.timeline_panel.configure_duration(duration if duration > 0 else self.timeline_model.duration_ms)
        QTimer.singleShot(300, self._ensure_timeline_has_video_clip)
        QTimer.singleShot(400, self._sync_video_timeline_if_needed)

        playhead = int(playback.get("current_time_ms", 0))
        self.current_time_ms = playhead
        self.timeline_panel.set_playhead(playhead)

        self._generate_thumbnails()
        self._seed_history()
        self._update_actions()
        self._refresh_preview()
        self.statusBar().showMessage(f"Proje yuklendi: {Path(file_path).name}")

    def _export_subtitles_for_timeline(self) -> list:
        segments = [
            (start, end)
            for _path, start, end, _effects in self.timeline_model.video_segments_for_export()
        ]
        if not segments or not self.timed_subtitles:
            return self.timed_subtitles
        if len(segments) == 1 and segments[0][0] == 0:
            clip = self.timeline_model.clips_on_track("video")
            if clip and clip[0].source_start_ms == 0:
                return self.timed_subtitles
        return remap_subtitles_for_segments(self.timed_subtitles, segments)

    def _build_export_request(self, output_path: str) -> ExportRequest:
        segments = self.timeline_model.video_segments_for_export()
        return ExportRequest(
            video_path=self.video_path or "",
            subtitle_path=self.subtitle_path or "",
            output_path=output_path,
            font_name=self.font_combo.currentText(),
            font_size=self.font_size_spin.value(),
            normal_color=self.normal_color.name(),
            active_color=self.active_color.name(),
            stroke_size=self.stroke_spin.value(),
            shadow_size=self.shadow_spin.value(),
            position=self.position_combo.currentText(),
            logo_path=self.logo_path,
            logo_pos=self.logo_pos_combo.currentText(),
            logo_size=self.logo_size_spin.value(),
            aspect_ratio=self.format_combo.currentText(),
            fps=self.fps_combo.currentText(),
            audio_bitrate=self.audio_quality_combo.currentText(),
            use_animation=self.anim_combo.currentText() != "Yok",
            animation_style=self.anim_combo.currentText(),
            denoise_audio=self.denoise_checkbox.isChecked(),
            use_gpu=self.gpu_checkbox.isChecked(),
            bg_box=self.bg_box_checkbox.isChecked(),
            video_segments=segments,
        )

    def _on_video_duration_changed(self, duration: int) -> None:
        if duration <= 0:
            return
        self.btn_play_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_backward.setEnabled(True)
        self.btn_forward.setEnabled(True)
        self._ensure_timeline_has_video_clip()
        self._sync_video_timeline_if_needed()

    def _configure_timeline(self) -> None:
        if not self.timed_subtitles:
            if self.media_player.source().isEmpty():
                self.timeline_panel.configure_duration(0)
                self.current_time_ms = 0
            self._refresh_preview()
            return

        end_ms = self.timed_subtitles[-1].end_ms
        if self.media_player.duration() > 0:
            end_ms = max(end_ms, self.media_player.duration())

        self.timeline_model.replace_subtitle_span(end_ms)
        self.timeline_panel.configure_duration(max(self.timeline_model.duration_ms, end_ms))
        self.btn_play_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_backward.setEnabled(True)
        self.btn_forward.setEnabled(True)
        self._refresh_preview()

    def _run_transcription(self, translate: bool = False) -> None:
        if not self.video_path:
            self.statusBar().showMessage("Devam etmek icin once bir video secin.")
            return

        dialog = TranscriptionDialog(
            self.video_path,
            self.transcription_service,
            self,
            translate_default=translate,
        )
        if dialog.exec() != QDialog.Accepted or not dialog.result_data:
            return

        self._on_transcription_success(dialog.result_data)

    def _on_transcription_success(self, result: TranscriptionResult) -> None:
        self.subtitle_path = str(result.srt_path)
        self.subtitle_input.setText(self.subtitle_path)
        self.subtitle_entries = parse_srt(self.subtitle_path)
        self.word_timing_doc = result.word_document
        self.timed_subtitles = build_timed_subtitles(
            self.subtitle_entries,
            self.word_timing_doc,
        )
        self._configure_timeline()
        self._update_actions()
        if self.timed_subtitles:
            last_sub = self.timed_subtitles[-1].end_ms
            self.timeline_model.replace_subtitle_span(last_sub)
            self.timeline_panel.refresh()
        self._commit_history()
        word_count = sum(len(seg.words) for seg in result.word_document.segments)
        self.statusBar().showMessage(
            f"Otomatik altyazi: {len(self.subtitle_entries)} satir, {word_count} kelime zamanlamasi."
        )

    def _on_transcription_error(self, error_data: tuple) -> None:
        _exc, trace = error_data
        QMessageBox.critical(self, "Transkripsiyon Hatasi", str(trace))
        self.statusBar().showMessage("Otomatik altyazi uretimi basarisiz oldu.")

    def _parse_subtitle(self) -> None:
        if not self.subtitle_path:
            self.statusBar().showMessage("Devam etmek icin once bir SRT dosyasi secin.")
            return

        self.subtitle_entries = parse_srt(self.subtitle_path)
        if not self.subtitle_entries:
            self.timed_subtitles = []
            self.word_timing_doc = None
            self._configure_timeline()
            self.statusBar().showMessage("SRT okundu ancak gecerli bir altyazi blogu bulunamadi.")
            return

        self._load_word_timing_sidecar()
        self.timed_subtitles = build_timed_subtitles(
            self.subtitle_entries,
            self.word_timing_doc,
        )
        self._configure_timeline()
        first_entry = self.subtitle_entries[0]
        timing_note = (
            "Whisper kelime zamanlamasi yuklendi."
            if self.word_timing_doc
            else "Kelime zamanlamasi tahmini (SRT satir bolmesi)."
        )
        self.statusBar().showMessage(
            f"{len(self.subtitle_entries)} altyazi blogu. {timing_note} Ornek: {first_entry.text}"
        )
        self.export_button.setEnabled(bool(self.video_path))

        if self.timed_subtitles:
            last_sub = self.timed_subtitles[-1].end_ms
            self.timeline_model.replace_subtitle_span(last_sub)
            self.timeline_panel.refresh()
        self._commit_history()

    def _open_batch_export(self) -> None:
        template = self._build_export_request(
            str(Path.cwd() / "output" / "batch" / "template.mp4")
        )
        dialog = BatchExportDialog(template, self.export_service, self)
        dialog.exec()

    def _open_clip_effects(self) -> None:
        selected = [
            clip for clip in self.timeline_model.selected_clips()
            if clip.track in ("video", "audio")
        ]
        if not selected:
            self.statusBar().showMessage("Efekt icin once bir video/ses klibi secin.")
            return

        base = selected[0].effects
        dialog = ClipEffectsDialog(base, self)
        if dialog.exec() != QDialog.Accepted:
            return

        updated = self.timeline_model.apply_effects_to_selected(dialog.updated_effects())
        if updated == 0:
            return
        self.timeline_panel.refresh()
        self._commit_history()
        self.statusBar().showMessage(f"{updated} klibe efekt uygulandi.")

    def _open_video_tools(self) -> None:
        dialog = VideoToolsDialog(self)
        dialog.exec()

    def _open_subtitle_editor(self) -> None:
        if not self.subtitle_entries:
            return

        dialog = SubtitleEditorDialog(self.subtitle_entries, self)
        if dialog.exec() == QDialog.Accepted:
            self.subtitle_entries = dialog.updated_entries
            self.word_timing_doc = None
            self.timed_subtitles = build_timed_subtitles(self.subtitle_entries, None)
            self._sync_word_timing_doc()
            self._configure_timeline()
            self._commit_history()
            self.statusBar().showMessage("Altyazilar guncellendi.")

    def _show_real_preview(self) -> None:
        if not self.video_path or not self.subtitle_entries:
            return

        default_name = f"{Path(self.video_path).stem}_preview.jpg"
        output_path = Path.cwd() / "output" / default_name

        request = self._build_export_request(str(output_path))
        
        self.statusBar().showMessage("Gercek onizleme olusturuluyor...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            export_subs = self._export_subtitles_for_timeline()
            preview_img_path = self.export_service.extract_preview_frame(
                request, export_subs, self.current_time_ms
            )
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Onizleme Hatasi", str(exc))
            self.statusBar().showMessage("Gercek onizleme basarisiz.")
            return

        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(f"Onizleme hazir: {preview_img_path.name}")
        
        # Basit bir dialog icinde resmi goster
        from PySide6.QtGui import QPixmap
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Gercek Export Onizlemesi")
        layout = QVBoxLayout(preview_dialog)
        img_label = QLabel()
        
        pixmap = QPixmap(str(preview_img_path))
        
        # Ekrana sigmasi icin olceklendir
        screen = QApplication.primaryScreen().geometry()
        max_w = screen.width() - 200
        max_h = screen.height() - 200
        
        if pixmap.width() > max_w or pixmap.height() > max_h:
            pixmap = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
        img_label.setPixmap(pixmap)
        layout.addWidget(img_label)
        preview_dialog.exec()

    def _prepare_export(self) -> None:
        if not self.video_path:
            self.statusBar().showMessage("Export icin once video secin.")
            return

        duration_ms = self.timeline_model.duration_ms or self.media_player.duration() or 0
        default_title = Path(self.video_path).stem + ("_subtitled" if self.timed_subtitles else "_export")
        default_folder = str(Path.cwd() / "output")

        dialog = ExportDialog(
            default_title=default_title,
            default_folder=default_folder,
            duration_ms=duration_ms,
            current_aspect=self.format_combo.currentText(),
            current_fps=self.fps_combo.currentText(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted or not dialog.result_data:
            return

        result = dialog.result_data
        if result.aspect_ratio in default_aspect_ratio_options():
            self.format_combo.setCurrentText(result.aspect_ratio)
        if result.fps in [self.fps_combo.itemText(i) for i in range(self.fps_combo.count())]:
            self.fps_combo.setCurrentText(result.fps)
        if result.audio_bitrate in [self.audio_quality_combo.itemText(i) for i in range(self.audio_quality_combo.count())]:
            self.audio_quality_combo.setCurrentText(result.audio_bitrate)

        request = self._build_export_request(result.output_path)
        request.aspect_ratio = result.aspect_ratio
        request.fps = result.fps
        request.audio_bitrate = result.audio_bitrate
        request.video_crf = result.video_crf
        request.video_preset = result.video_preset

        export_subs = self._export_subtitles_for_timeline()

        progress = QProgressDialog("Disa aktarim hazirlaniyor...", None, 0, 100, self)
        progress.setWindowTitle("Disa Aktar")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()

        worker = Worker(
            self.export_service.export,
            request,
            export_subs,
            progress_callback=lambda _msg: None,
            total_duration_ms=duration_ms,
        )

        def on_progress(message: str) -> None:
            if "|" in message:
                percent_str, label = message.split("|", 1)
                try:
                    progress.setValue(int(percent_str))
                except ValueError:
                    pass
                progress.setLabelText(label)
            else:
                progress.setLabelText(message)
            QApplication.processEvents()

        worker.signals.progress.connect(on_progress)
        worker.signals.result.connect(
            lambda exported_path: self._on_export_success(progress, exported_path)
        )
        worker.signals.error.connect(
            lambda err: self._on_export_error(progress, err)
        )
        worker.signals.finished.connect(lambda: progress.close())

        self.export_button.setEnabled(False)
        self.btn_export_mini.setEnabled(False)
        self.statusBar().showMessage("FFmpeg export basladi...")
        self.thread_pool.start(worker)

    def _on_export_success(self, progress: QProgressDialog, exported_path) -> None:
        self.export_button.setEnabled(True)
        self.btn_export_mini.setEnabled(True)
        progress.setValue(100)
        QMessageBox.information(self, "Export Tamamlandi", f"Cikti hazir: {exported_path}")
        self.statusBar().showMessage(f"Export tamamlandi: {exported_path}")

    def _on_export_error(self, progress: QProgressDialog, error_data: tuple) -> None:
        self.export_button.setEnabled(True)
        self.btn_export_mini.setEnabled(True)
        _exc, trace = error_data
        QMessageBox.critical(self, "Export Hatasi", str(trace))
        self.statusBar().showMessage("Export basarisiz oldu.")

    def _update_actions(self) -> None:
        self.transcribe_button.setEnabled(bool(self.video_path))
        has_subtitles = bool(self.timed_subtitles)
        has_both = bool(self.video_path and self.timed_subtitles)
        
        self.edit_button.setEnabled(has_subtitles)
        self.preview_export_button.setEnabled(has_both)
        self.export_button.setEnabled(bool(self.video_path))
        self._refresh_preview()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "timeline_panel"):
            self.timeline_panel.refresh()

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from app.core.timeline import TRACK_AUDIO, TRACK_SUBTITLE, TRACK_VIDEO, TimelineModel
from app.ui.timeline.clips import ClipWidget, TrackWidget
from app.ui.timeline.nav import (
    MiniTimeline,
    TimecodeLabel,
    TimelineScrollArea,
    TrackHeader,
)
from app.ui.timeline.ruler import TimeRuler, TimelineContainer

class TimelinePanel(QWidget):
    """Timeline şeridi — profesyonel video editörü görünümü."""

    split_requested   = Signal()
    delete_requested  = Signal()
    add_media_requested = Signal()
    undo_requested    = Signal()
    redo_requested    = Signal()
    edit_mode_changed = Signal(str)
    playhead_changed  = Signal(int)
    clip_selected     = Signal(str, bool)
    clip_moved        = Signal(str, int)
    clip_drag_started = Signal(str)
    clip_trim_started = Signal(str)
    clip_trim_finished = Signal(str)
    clip_drag_finished = Signal(str, int)
    effects_requested = Signal()
    files_dropped     = Signal(list)

    def __init__(self, model: TimelineModel, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("timelinePanel")
        self.setStyleSheet(
            "#timelinePanel {"
            "  background-color: #0F1520;"
            "  border-radius: 0px;"
            "  border: none;"
            "}"
        )
        self.model = model
        self.zoom_level   = 1.0
        self._playhead_ms = 0
        self._px_per_ms   = 0.1
        self._connected_widgets: set[str] = set()
        self._thumbnails: dict[str, list[Path]] = {}
        self._waveforms:  dict[str, Path] = {}
        self._trim_origin: dict[str, tuple[int, int, int, int]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────────
        toolbar_widget = QWidget()
        toolbar_widget.setFixedHeight(40)
        toolbar_widget.setStyleSheet(
            "background: #111827;"
            "border-bottom: 1px solid #1E2840;"
        )
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(8, 4, 8, 4)
        toolbar.setSpacing(4)

        def make_btn(icon: str, text: str, color: str, callback) -> QPushButton:
            btn = QPushButton(qta.icon(icon, color=color), f" {text}")
            btn.setStyleSheet(f"""
              QPushButton {{
                background-color: transparent; color: #CBD5E1;
                border: none; padding: 3px 8px;
                border-radius: 4px; font-weight: 600; font-size: 11px;
              }}
              QPushButton:hover {{ background-color: #1E2A3A; color: #FFF; }}
              QPushButton:pressed {{ background-color: #253145; }}
            """)
            btn.clicked.connect(callback)
            return btn

        toolbar.addWidget(make_btn("fa5s.plus",  "Ekle",    "#22C55E", self.add_media_requested.emit))
        toolbar.addWidget(make_btn("fa5s.cut",   "Böl",     "#EF4444", self.split_requested.emit))
        toolbar.addWidget(make_btn("fa5s.trash", "Sil",     "#9CA3AF", self.delete_requested.emit))

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #252F42;")
        toolbar.addWidget(sep)

        self.btn_undo = make_btn("fa5s.undo", "Geri Al", "#94A3B8", self.undo_requested.emit)
        self.btn_redo = make_btn("fa5s.redo", "Yinele",  "#94A3B8", self.redo_requested.emit)
        toolbar.addWidget(self.btn_undo)
        toolbar.addWidget(self.btn_redo)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #252F42;")
        toolbar.addWidget(sep2)

        self.btn_ripple = QPushButton(" Ripple")
        self.btn_slip   = QPushButton(" Slip")
        for mode_btn, mode, color in (
            (self.btn_ripple, "ripple", "#2DD4BF"),
            (self.btn_slip,   "slip",   "#F59E0B"),
        ):
            mode_btn.setCheckable(True)
            mode_btn.setStyleSheet(f"""
              QPushButton {{
                background-color: transparent; color: #64748B;
                border: 1px solid #252F42; padding: 3px 10px;
                border-radius: 4px; font-weight: 600; font-size: 11px;
              }}
              QPushButton:checked {{
                background-color: #1E2A3A; color: {color};
                border-color: {color};
              }}
              QPushButton:hover {{ background-color: #1E2A3A; color: #CBD5E1; }}
            """)
        self.btn_ripple.setChecked(True)
        self.btn_ripple.clicked.connect(lambda: self._set_edit_mode("ripple"))
        self.btn_slip.clicked.connect(lambda: self._set_edit_mode("slip"))
        toolbar.addWidget(self.btn_ripple)
        toolbar.addWidget(self.btn_slip)

        toolbar.addWidget(make_btn("fa5s.magic", "Efektler", "#8B5CF6", self.effects_requested.emit))

        toolbar.addStretch(1)

        # Timecode display
        self.timecode_label = TimecodeLabel()
        toolbar.addWidget(self.timecode_label)

        toolbar.addSpacing(12)

        # Zoom controls
        zoom_out_btn = QPushButton(qta.icon("fa5s.search-minus", color="#94A3B8"), "")
        zoom_in_btn  = QPushButton(qta.icon("fa5s.search-plus",  color="#94A3B8"), "")
        for zb in (zoom_out_btn, zoom_in_btn):
            zb.setFixedSize(26, 26)
            zb.setStyleSheet(
                "QPushButton { background: transparent; border: none; border-radius: 4px; }"
                "QPushButton:hover { background: #1E2A3A; }"
            )
        zoom_out_btn.clicked.connect(lambda: self._apply_zoom(self.zoom_level / 1.3))
        zoom_in_btn.clicked.connect( lambda: self._apply_zoom(self.zoom_level * 1.3))
        self.btn_zoom_out = zoom_out_btn
        self.btn_zoom_in  = zoom_in_btn

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(90)
        self.zoom_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 3px; background: #2A3548; border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #3B82F6; width: 10px; height: 10px;"
            "  margin: -4px 0; border-radius: 5px; }"
            "QSlider::sub-page:horizontal { background: #3B82F6; border-radius: 2px; }"
        )
        self.zoom_slider.valueChanged.connect(lambda v: self._apply_zoom(v / 100.0))

        toolbar.addWidget(zoom_out_btn)
        toolbar.addWidget(self.zoom_slider)
        toolbar.addWidget(zoom_in_btn)

        layout.addWidget(toolbar_widget)

        # ── Main body (headers + scroll) ───────────────────────────────────
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left: track headers column
        self._headers_col = QWidget()
        self._headers_col.setFixedWidth(TrackHeader.HEADER_WIDTH)
        self._headers_col.setStyleSheet("background: #131922;")
        headers_layout = QVBoxLayout(self._headers_col)
        headers_layout.setContentsMargins(0, 0, 0, 0)
        headers_layout.setSpacing(0)

        # Ruler spacer
        ruler_spacer = QWidget()
        ruler_spacer.setFixedHeight(TimeRuler.HEIGHT)
        ruler_spacer.setStyleSheet("background: #131922; border-bottom: 1px solid #1E2840;")
        headers_layout.addWidget(ruler_spacer)

        self._track_headers: list[TrackHeader] = []
        for ttype in (TRACK_VIDEO, TRACK_AUDIO, TRACK_SUBTITLE):
            hdr = TrackHeader(ttype, TrackWidget.TRACK_HEIGHTS[ttype])
            self._track_headers.append(hdr)
            headers_layout.addWidget(hdr)

        headers_layout.addStretch(1)
        body_layout.addWidget(self._headers_col)

        # Right: scrollable timeline
        self.scroll = TimelineScrollArea()
        self.scroll.setObjectName("timelineScroll")
        self.scroll.setWidgetResizable(False)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.zoom_changed.connect(self._on_scroll_zoom)
        self.scroll.scroll_changed.connect(self._on_scroll_changed)

        self.container = TimelineContainer()
        self.container.playhead_seek.connect(self._on_ruler_seek)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.time_ruler = TimeRuler()
        self.time_ruler.seek_requested.connect(self._on_ruler_seek)
        container_layout.addWidget(self.time_ruler)

        self.track_v = TrackWidget(
            TRACK_VIDEO, self._px_per_ms,
            on_files_dropped=self._handle_files_dropped,
            on_add_media=self.add_media_requested.emit,
        )
        self.track_a = TrackWidget(
            TRACK_AUDIO, self._px_per_ms,
            on_files_dropped=self._handle_files_dropped,
        )
        self.track_s = TrackWidget(
            TRACK_SUBTITLE, self._px_per_ms,
            on_files_dropped=self._handle_files_dropped,
        )

        for track in (self.track_v, self.track_a, self.track_s):
            track.on_trim = self._handle_trim
            track.on_move = self._handle_move

        container_layout.addWidget(self.track_v)
        container_layout.addWidget(self.track_a)
        container_layout.addWidget(self.track_s)
        container_layout.addStretch(1)

        self.scroll.setWidget(self.container)
        body_layout.addWidget(self.scroll, 1)
        layout.addWidget(body_widget, 1)

        # ── Mini navigator ─────────────────────────────────────────────────
        mini_row = QWidget()
        mini_row.setFixedHeight(MiniTimeline.HEIGHT)
        mini_row_layout = QHBoxLayout(mini_row)
        mini_row_layout.setContentsMargins(0, 0, 0, 0)
        mini_row_layout.setSpacing(0)

        mini_spacer = QWidget()
        mini_spacer.setFixedWidth(TrackHeader.HEADER_WIDTH)
        mini_spacer.setStyleSheet("background: #0C1220; border-top: 1px solid #1E2840;")
        mini_row_layout.addWidget(mini_spacer)

        self.mini_timeline = MiniTimeline()
        self.mini_timeline.scroll_requested.connect(self._on_mini_scroll)
        mini_row_layout.addWidget(self.mini_timeline, 1)

        layout.addWidget(mini_row)

        # ── Status bar ─────────────────────────────────────────────────────
        status_bar = QWidget()
        status_bar.setFixedHeight(22)
        status_bar.setStyleSheet(
            "background: #0D1117;"
            "border-top: 1px solid #1E2840;"
        )
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(8, 0, 8, 0)

        self.project_length_label = QLabel("Proje uzunluğu: 00:00")
        self.project_length_label.setStyleSheet("color: #475569; font-size: 10px;")
        status_layout.addWidget(self.project_length_label)
        status_layout.addStretch(1)

        # Zoom percentage label
        self.zoom_label = QLabel("Zoom: 100%")
        self.zoom_label.setStyleSheet("color: #3B4A6B; font-size: 10px;")
        status_layout.addWidget(self.zoom_label)

        layout.addWidget(status_bar)

        self.setAcceptDrops(True)

    # ── File drop handlers ─────────────────────────────────────────────────

    def _handle_files_dropped(self, paths: list[str]) -> None:
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths: list[str] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    # ── Zoom ───────────────────────────────────────────────────────────────

    def _apply_zoom(self, new_zoom: float) -> None:
        new_zoom = max(0.25, min(8.0, new_zoom))
        if abs(new_zoom - self.zoom_level) < 0.001:
            return
        self.zoom_level = new_zoom
        self.scroll._zoom_level = new_zoom
        # Sync slider without triggering its signal
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(new_zoom * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"Zoom: {int(new_zoom * 100)}%")
        self.refresh()

    def _on_scroll_zoom(self, new_zoom: float) -> None:
        self._apply_zoom(new_zoom)

    def change_zoom(self, delta: float) -> None:
        self._apply_zoom(self.zoom_level + delta)

    # ── Scroll / Mini navigator ────────────────────────────────────────────

    def _on_scroll_changed(self) -> None:
        self._update_mini_timeline()

    def _on_mini_scroll(self, start_n: float) -> None:
        sb  = self.scroll.horizontalScrollBar()
        sb.setValue(int(start_n * sb.maximum()))

    def _update_mini_timeline(self) -> None:
        sb         = self.scroll.horizontalScrollBar()
        max_val    = max(1, sb.maximum() + self.scroll.viewport().width())
        view_w     = self.scroll.viewport().width()
        view_start = sb.value() / max_val
        view_end   = (sb.value() + view_w) / max_val

        eff = self._effective_duration_ms()
        dur = max(1, eff)
        ph_n = self._playhead_ms / dur

        clips_n: list[tuple[float, float, str]] = []
        for clip in self.model.clips:
            s_n = clip.timeline_start_ms / dur
            e_n = clip.timeline_end_ms   / dur
            clips_n.append((s_n, e_n, clip.track))

        self.mini_timeline.update_state(view_start, view_end, ph_n, clips_n)

    # ── Ruler seek ────────────────────────────────────────────────────────

    def _on_ruler_seek(self, ms: int) -> None:
        self.set_playhead(ms, emit=True)

    # ── Project length ─────────────────────────────────────────────────────

    def update_project_length_label(self, duration_ms: int) -> None:
        duration_ms = max(duration_ms, self._effective_duration_ms())
        minutes, remainder = divmod(max(0, duration_ms), 60_000)
        seconds, ms_rem    = divmod(remainder, 1000)
        hours, minutes     = divmod(minutes, 60)
        if hours:
            text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        elif minutes > 0 or seconds > 0:
            text = f"{minutes:02d}:{seconds:02d}"
        else:
            text = f"00:00.{ms_rem:03d}" if ms_rem else "00:00"
        self.project_length_label.setText(f"Proje uzunluğu: {text}")

    # ── Edit mode ──────────────────────────────────────────────────────────

    def _set_edit_mode(self, mode: str) -> None:
        from app.core.timeline import EDIT_MODE_RIPPLE, EDIT_MODE_SLIP
        self.model.edit_mode = EDIT_MODE_RIPPLE if mode == "ripple" else EDIT_MODE_SLIP
        self.btn_ripple.setChecked(mode == "ripple")
        self.btn_slip.setChecked(mode == "slip")
        self.edit_mode_changed.emit(self.model.edit_mode)

    def set_history_state(self, can_undo: bool, can_redo: bool) -> None:
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

    # ── Clip signal forwarding ─────────────────────────────────────────────

    def _on_clip_drag_started(self, clip_id: str) -> None:
        self.clip_drag_started.emit(clip_id)

    def _on_clip_drag_finished(self, clip_id: str, new_start_ms: int) -> None:
        self.clip_drag_finished.emit(clip_id, new_start_ms)

    def _on_clip_trim_started(self, clip_id: str) -> None:
        clip = self.model.get_clip(clip_id)
        if clip:
            self._trim_origin[clip_id] = (
                clip.timeline_start_ms,
                clip.timeline_end_ms,
                clip.source_start_ms,
                clip.resolved_source_end_ms,
            )
        self.clip_trim_started.emit(clip_id)

    def _on_clip_trim_finished(self, clip_id: str) -> None:
        self._trim_origin.pop(clip_id, None)
        self.clip_trim_finished.emit(clip_id)

    def _connect_clip_widget(self, widget: ClipWidget) -> None:
        if widget.clip.clip_id in self._connected_widgets:
            return
        self._connected_widgets.add(widget.clip.clip_id)
        widget.clip_clicked.connect(self.clip_selected.emit)
        widget.clip_drag_started.connect(self._on_clip_drag_started)
        widget.clip_drag_finished.connect(self._on_clip_drag_finished)
        widget.clip_trim_started.connect(self._on_clip_trim_started)
        widget.clip_trim_finished.connect(self._on_clip_trim_finished)

    # ── Playhead ───────────────────────────────────────────────────────────

    def playhead_max_ms(self) -> int:
        return self._effective_duration_ms()

    def set_playhead(self, ms: int, emit: bool = True) -> None:
        max_ms = self.playhead_max_ms()
        self._playhead_ms = max(0, min(max_ms, ms)) if max_ms > 0 else max(0, ms)
        self.timecode_label.set_ms(self._playhead_ms)
        self.time_ruler.configure(self.model.duration_ms, self._px_per_ms, self._playhead_ms)
        self.container.set_playhead(
            self._playhead_ms, self._px_per_ms, self._effective_duration_ms()
        )
        self._update_mini_timeline()
        if emit:
            self.playhead_changed.emit(self._playhead_ms)

    # ── Duration ───────────────────────────────────────────────────────────

    def _effective_duration_ms(self) -> int:
        clip_end = max((c.timeline_end_ms for c in self.model.clips), default=0)
        return max(self.model.duration_ms, clip_end)

    def configure_duration(self, duration_ms: int) -> None:
        effective = max(0, duration_ms, self._effective_duration_ms())
        self.model.set_duration(effective)
        self.update_project_length_label(effective)
        self.refresh()

    # ── Thumbnails / waveforms ────────────────────────────────────────────

    def set_media_previews(
        self,
        thumbnails: dict[str, list[Path]] | None = None,
        waveforms:  dict[str, Path] | None = None,
        replace: bool = True,
    ) -> None:
        if replace:
            if thumbnails is not None:
                self._thumbnails = dict(thumbnails)
            if waveforms is not None:
                self._waveforms = dict(waveforms)
        else:
            if thumbnails:
                self._thumbnails.update(thumbnails)
            if waveforms:
                self._waveforms.update(waveforms)
        self.refresh()

    def set_thumbnails(self, mapping: dict[str, list[Path]], replace: bool = True) -> None:
        self.set_media_previews(thumbnails=mapping, replace=replace)

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        base_width  = max(self.scroll.viewport().width(), 400)
        total_width = max(int(base_width * self.zoom_level), 400)
        effective   = self._effective_duration_ms()
        duration    = effective if effective > 0 else 1000
        self._px_per_ms = total_width / duration

        content_h = (
            TimeRuler.HEIGHT
            + TrackWidget.TRACK_HEIGHTS[TRACK_VIDEO]
            + TrackWidget.TRACK_HEIGHTS[TRACK_AUDIO]
            + TrackWidget.TRACK_HEIGHTS[TRACK_SUBTITLE]
            + 8
        )
        self.container.setFixedSize(total_width, content_h)
        self.container.px_per_ms = self._px_per_ms

        for track in (self.track_v, self.track_a, self.track_s):
            track.px_per_ms = self._px_per_ms
            track.setFixedWidth(total_width)

        self.time_ruler.configure(duration, self._px_per_ms, self._playhead_ms)

        self.track_v.sync_clips(self.model.clips_on_track(TRACK_VIDEO),  self._thumbnails)
        self.track_a.sync_clips(self.model.clips_on_track(TRACK_AUDIO),  waveforms=self._waveforms)
        self.track_s.sync_clips(self.model.clips_on_track(TRACK_SUBTITLE))

        live_ids = set()
        for track in (self.track_v, self.track_a, self.track_s):
            live_ids.update(track.clip_widgets.keys())
            for widget in track.clip_widgets.values():
                self._connect_clip_widget(widget)
        self._connected_widgets &= live_ids

        self.container.set_playhead(
            self._playhead_ms, self._px_per_ms, duration
        )
        self.time_ruler.configure(duration, self._px_per_ms, self._playhead_ms)
        self.update_project_length_label(effective)
        self._update_mini_timeline()
        self.container.raise_playhead()

    # ── Trim / Move handlers ───────────────────────────────────────────────

    def _handle_move(self, clip_id: str, new_start_ms: int) -> None:
        self.clip_moved.emit(clip_id, new_start_ms)

    def _handle_trim(self, clip_id: str, edge: str, local_x: int) -> None:
        self.model.trim_clip(clip_id, edge, local_x, self._px_per_ms)
        self.refresh()

    # ── Resize / Show ──────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.refresh()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(50, self.refresh)

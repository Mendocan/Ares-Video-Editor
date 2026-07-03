from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPixmap, QLinearGradient, QCursor,
)
from PySide6.QtWidgets import QFrame, QLabel, QWidget

from app.core.timeline import TRACK_AUDIO, TRACK_SUBTITLE, TRACK_VIDEO, TimelineClip
from app.ui.app_theme import (
    BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TL_BG_TRACK,
)
from app.ui.timeline.theme import (
    C_ACCENT_A, C_ACCENT_S, C_ACCENT_V, C_SELECT, C_TEXT, C_TEXT_BRT, C_TEXT_LT, TRACK_COLORS,
)

class ClipWidget(QWidget):
    clip_clicked      = Signal(str, bool)
    clip_drag_started = Signal(str)
    clip_drag_finished = Signal(str, int)
    clip_moved        = Signal(str, int)
    clip_trim_started = Signal(str)
    clip_trim_finished = Signal(str)

    EDGE_ZONE = 8   # px

    def __init__(self, clip: TimelineClip, parent=None) -> None:
        super().__init__(parent)
        self.clip = clip
        self._dragging_edge: str | None = None
        self._dragging_body = False
        self._drag_start_x  = 0
        self._drag_origin_start_ms = 0
        self._pending_start_ms     = 0
        self._hover_edge: str | None = None
        self.thumbnails: list[Path] = []
        self.waveform_path: Path | None = None
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)
        self.update_style()

    # ── Thumbnails / waveform ──────────────────────────────────────────────

    def set_thumbnails(self, paths: list[Path]) -> None:
        self.thumbnails = paths
        self.update()

    def set_waveform(self, path: Path | None) -> None:
        self.waveform_path = path
        self.update()

    def update_style(self) -> None:
        self.update()

    # ── Mouse helpers ──────────────────────────────────────────────────────

    def _track_widget(self):
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, "px_per_ms"):
                return widget
            widget = widget.parent()
        return None

    def _hit_edge(self, x: int) -> str | None:
        if x <= self.EDGE_ZONE:
            return "left"
        if x >= self.width() - self.EDGE_ZONE:
            return "right"
        return None

    def mousePressEvent(self, event) -> None:
        edge = self._hit_edge(event.pos().x())
        if edge:
            self._dragging_edge = edge
            self.clip_trim_started.emit(self.clip.clip_id)
        else:
            additive = bool(event.modifiers() & Qt.ControlModifier)
            self.clip_clicked.emit(self.clip.clip_id, additive)
            if event.button() == Qt.LeftButton:
                self._dragging_body = True
                self._drag_start_x  = event.pos().x()
                self._drag_origin_start_ms = self.clip.timeline_start_ms
                self._pending_start_ms     = self.clip.timeline_start_ms
                self.clip_drag_started.emit(self.clip.clip_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        parent_track = self._track_widget()
        new_hover = self._hit_edge(event.pos().x())
        if new_hover != self._hover_edge:
            self._hover_edge = new_hover
            if new_hover:
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()

        if self._dragging_edge:
            if parent_track and hasattr(parent_track, "on_clip_trim"):
                parent_track.on_clip_trim(self.clip.clip_id, self._dragging_edge, event.pos().x())
        elif self._dragging_body:
            if parent_track and parent_track.px_per_ms > 0:
                delta_px = event.pos().x() - self._drag_start_x
                delta_ms = int(delta_px / parent_track.px_per_ms)
                new_start = max(0, self._drag_origin_start_ms + delta_ms)
                self._pending_start_ms = new_start
                self.clip_moved.emit(self.clip.clip_id, new_start)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging_body:
            self.clip_drag_finished.emit(self.clip.clip_id, self._pending_start_ms)
        if self._dragging_edge:
            self.clip_trim_finished.emit(self.clip.clip_id)
        self._dragging_edge = None
        self._dragging_body = False
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_edge = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────────

    def _paint_video_filmstrip(self, painter: QPainter, w: int, h: int) -> bool:
        if not self.thumbnails:
            return False
        first = QPixmap(str(self.thumbnails[0]))
        if first.isNull():
            return False
        if len(self.thumbnails) == 1 and first.width() >= first.height() * 2:
            scaled = first.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, w, h, scaled)
            return True
        tile_w = max(24, w // max(len(self.thumbnails), 1))
        painted_any = False
        for i, thumb_path in enumerate(self.thumbnails):
            x = i * tile_w
            if x >= w:
                break
            pixmap = QPixmap(str(thumb_path))
            if pixmap.isNull():
                continue
            scaled = pixmap.scaled(tile_w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(x, 0, tile_w, h, scaled)
            painted_any = True
        return painted_any

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        accent = TRACK_COLORS.get(self.clip.track, C_TEXT)

        # ── Video ──────────────────────────────────────────────────────────
        if self.clip.track == TRACK_VIDEO:
            painted = False
            if self.thumbnails:
                painted = self._paint_video_filmstrip(painter, w, h)
            if not painted:
                grad = QLinearGradient(0, 0, 0, h)
                grad.setColorAt(0, QColor("#1E3A5F"))
                grad.setColorAt(1, QColor("#152844"))
                painter.fillRect(0, 0, w, h, grad)
                painter.setPen(QPen(C_ACCENT_V, 1, Qt.DashLine))
                painter.drawRect(1, 1, w - 2, h - 2)
                painter.setPen(C_TEXT_LT)
                painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                lbl = self.clip.label if len(self.clip.label) <= 28 else f"{self.clip.label[:25]}..."
                painter.drawText(10, h // 2 + 2, lbl)
                painter.setPen(C_TEXT)
                painter.setFont(QFont("Segoe UI", 8))
                painter.drawText(10, h // 2 + 16, "Filmstrip hazırlanıyor…")

            # Bottom label bar
            painter.fillRect(0, h - 16, w, 16, QColor(0, 0, 0, 160))
            painter.setPen(QColor(248, 250, 252, 210))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(5, h - 4, self.clip.label[:32])

            # Left accent stripe
            painter.fillRect(0, 0, 3, h, accent)

            # Border
            painter.setPen(QPen(accent.darker(130), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(0, 0, w - 1, h - 1)

            self._paint_fx_badge(painter, w, h)

        # ── Audio ──────────────────────────────────────────────────────────
        elif self.clip.track == TRACK_AUDIO:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor("#063828"))
            grad.setColorAt(1, QColor("#052B1F"))
            painter.fillRect(0, 0, w, h, grad)
            if self.waveform_path and self.waveform_path.exists():
                pixmap = QPixmap(str(self.waveform_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, w, h, scaled)
            else:
                painter.setPen(QPen(C_ACCENT_A.darker(150), 1, Qt.DashLine))
                painter.drawRect(1, 1, w - 2, h - 2)
                painter.setPen(QColor("#6EE7B7"))
                painter.setFont(QFont("Segoe UI", 7))
                painter.drawText(6, h // 2 + 3, "Ses önizlemesi")
            painter.fillRect(0, 0, 3, h, C_ACCENT_A)
            painter.setPen(QPen(C_ACCENT_A.darker(140), 1))
            painter.drawRect(0, 0, w - 1, h - 1)
            self._paint_fx_badge(painter, w, h)

        # ── Subtitle ───────────────────────────────────────────────────────
        elif self.clip.track == TRACK_SUBTITLE:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor("#2D2060"))
            grad.setColorAt(1, QColor("#1E1545"))
            painter.fillRect(0, 0, w, h, grad)
            painter.setPen(QPen(C_ACCENT_S.darker(120), 1))
            seg_w = max(28, min(80, w // 6))
            for sx in range(4, w - 4, seg_w + 4):
                painter.drawRoundedRect(sx, 5, min(seg_w, w - sx - 4), h - 10, 2, 2)
            painter.fillRect(0, 0, 3, h, C_ACCENT_S)
            painter.setPen(QColor("#E9D5FF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.drawText(7, h - 5, "CC")

        # ── Selection overlay ──────────────────────────────────────────────
        if self.clip.selected:
            painter.setPen(QPen(C_SELECT, 2))
            painter.setBrush(QColor(255, 255, 255, 18))
            painter.drawRect(1, 1, w - 2, h - 2)
            # Corner handles
            handle_size = 6
            painter.setBrush(QBrush(C_SELECT))
            painter.setPen(Qt.NoPen)
            for hx, hy in [(2, 2), (w - handle_size - 2, 2),
                           (2, h - handle_size - 2), (w - handle_size - 2, h - handle_size - 2)]:
                painter.drawRoundedRect(hx, hy, handle_size, handle_size, 1, 1)

        # ── Trim handle hover ──────────────────────────────────────────────
        if self._hover_edge == "left":
            painter.fillRect(0, 0, self.EDGE_ZONE, h, QColor(255, 255, 255, 45))
            painter.setPen(QPen(C_TEXT_BRT, 2))
            painter.drawLine(self.EDGE_ZONE - 1, 4, self.EDGE_ZONE - 1, h - 4)
        elif self._hover_edge == "right":
            painter.fillRect(w - self.EDGE_ZONE, 0, self.EDGE_ZONE, h, QColor(255, 255, 255, 45))
            painter.setPen(QPen(C_TEXT_BRT, 2))
            painter.drawLine(w - self.EDGE_ZONE, 4, w - self.EDGE_ZONE, h - 4)

    def _paint_fx_badge(self, painter: QPainter, w: int, h: int) -> None:
        effects = self.clip.effects
        if effects and (effects.has_video_filters() or effects.has_audio_filters()):
            painter.setPen(Qt.NoPen)
            painter.setBrush(C_ACCENT_S)
            painter.drawEllipse(w - 14, 3, 11, 11)
            painter.setPen(C_TEXT_BRT)
            painter.setFont(QFont("Segoe UI", 6, QFont.Bold))
            painter.drawText(w - 12, 11, "fx")


# ─────────────────────────────────────────────────────────────────────────────
# TrackWidget — clip sahası
# ─────────────────────────────────────────────────────────────────────────────

class TrackWidget(QFrame):
    TRACK_HEIGHTS = {
        TRACK_VIDEO:    58,
        TRACK_AUDIO:    40,
        TRACK_SUBTITLE: 34,
    }

    def __init__(
        self,
        track_type: str,
        px_per_ms: float,
        on_files_dropped=None,
        on_add_media=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.track_type   = track_type
        self.px_per_ms    = px_per_ms
        self._on_files_dropped = on_files_dropped
        self._on_add_media     = on_add_media
        self.setAcceptDrops(True)
        track_height = self.TRACK_HEIGHTS.get(track_type, 44)
        self.setFixedHeight(track_height)
        self.setStyleSheet(
            f"TrackWidget {{"
            f"  background-color: {TL_BG_TRACK};"
            f"  border: none;"
            f"  border-bottom: 1px solid {BORDER};"
            f"}}"
        )
        self.clip_widgets: dict[str, ClipWidget] = {}
        self._render_clips: list[TimelineClip] = []
        self.on_trim: Callable[[str, str, int], None] | None = None
        self.on_move: Callable[[str, int], None] | None = None

        self.drop_hint = QLabel(self)
        self.drop_hint.setText("Dosyaları buraya sürükleyin")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-style: italic;"
            "background: transparent; border: none;"
        )
        self.drop_hint.hide()
        self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    # ── Drop hint ──────────────────────────────────────────────────────────

    def _sync_drop_hint_geometry(self) -> None:
        if self.track_type != TRACK_VIDEO or self._render_clips:
            self.drop_hint.hide()
            self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            return
        hint_w = min(280, max(160, self.width() - 24))
        self.drop_hint.setGeometry((self.width() - hint_w) // 2, 0, hint_w, self.height())
        self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.drop_hint.setCursor(Qt.ArrowCursor)
        self.drop_hint.show()
        self.drop_hint.lower()

    # ── Layout ─────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_clip_widgets()
        self._sync_drop_hint_geometry()

    def _layout_clip_widgets(self) -> None:
        track_h = max(1, self.height() - 2)
        for clip in self._render_clips:
            widget = self.clip_widgets.get(clip.clip_id)
            if widget is None:
                continue
            x = int(clip.timeline_start_ms * self.px_per_ms)
            w = max(24, int(clip.duration_ms * self.px_per_ms))
            widget.setGeometry(x, 1, w, track_h)
            widget.show()
            widget.raise_()
        if self._render_clips:
            self.drop_hint.hide()
            self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        w, h = self.width(), self.height()
        # Subtle alternating grid lines
        painter.setPen(QPen(QColor(BORDER), 1))
        step_px = 100
        x = 0
        while x < w:
            painter.drawLine(x, 0, x, h)
            x += step_px

    # ── Drag & Drop ────────────────────────────────────────────────────────

    def _paths_from_drop(self, event) -> list[str]:
        paths: list[str] = []
        if not event.mimeData().hasUrls():
            return paths
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        return paths

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = self._paths_from_drop(event)
        if paths and self._on_files_dropped:
            self._on_files_dropped(paths)
            event.acceptProposedAction()

    # ── Trim / Move callbacks ──────────────────────────────────────────────

    def on_clip_trim(self, clip_id: str, edge: str, local_x: int) -> None:
        if self.on_trim:
            self.on_trim(clip_id, edge, local_x)

    def on_clip_move(self, clip_id: str, new_start_ms: int) -> None:
        if self.on_move:
            self.on_move(clip_id, new_start_ms)

    # ── Sync ───────────────────────────────────────────────────────────────

    def sync_clips(
        self,
        clips: list[TimelineClip],
        thumbnails: dict[str, list[Path]] | None = None,
        waveforms: dict[str, Path] | None = None,
    ) -> None:
        self._render_clips = list(clips)
        current_ids = {c.clip_id for c in clips}
        for cid in list(self.clip_widgets):
            if cid not in current_ids:
                widget = self.clip_widgets.pop(cid)
                widget.setParent(None)
                widget.deleteLater()

        for clip in clips:
            if clip.clip_id not in self.clip_widgets:
                widget = ClipWidget(clip, self)
                widget.clip_moved.connect(self.on_clip_move)
                widget.show()
                self.clip_widgets[clip.clip_id] = widget
            else:
                widget = self.clip_widgets[clip.clip_id]
                widget.clip = clip
                widget.update_style()

            if thumbnails and clip.clip_id in thumbnails:
                self.clip_widgets[clip.clip_id].set_thumbnails(thumbnails[clip.clip_id])
            if waveforms and clip.clip_id in waveforms:
                self.clip_widgets[clip.clip_id].set_waveform(waveforms[clip.clip_id])

        self._layout_clip_widgets()

        content_width = max(self.width(), 200)
        if clips:
            last = max(c.timeline_end_ms for c in clips)
            content_width = max(content_width, int(last * self.px_per_ms) + 24)
        self.setMinimumWidth(content_width)

        self._update_drop_hint(len(clips) > 0)
        self._sync_drop_hint_geometry()
        self.update()

    def _update_drop_hint(self, has_clips: bool) -> None:
        if self.track_type == TRACK_VIDEO and not has_clips:
            self.drop_hint.setText("Dosyaları buraya sürükleyin")
            self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.drop_hint.show()
            self.drop_hint.lower()
        else:
            self.drop_hint.hide()
            self.drop_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            for widget in self.clip_widgets.values():
                widget.show()
                widget.raise_()

    def clear_clips(self) -> None:
        for widget in self.clip_widgets.values():
            widget.setParent(None)
            widget.deleteLater()
        self.clip_widgets.clear()
        self._update_drop_hint(False)

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from app.core.subtitle_positions import preview_padding, qt_preview_alignment
from app.core.word_timing import find_active_word_index, find_subtitle_at_time
from app.ui.aspect_ratio_frame import AspectRatioFrame
from app.ui.preview_settings_dialog import PreviewSettingsDialog
from app.ui.preview_widgets import AudioVisualizer, COLOR_PLAY_TEAL


class MainWindowPreviewMixin:
    def _on_preview_format_changed(self, label: str) -> None:
        if hasattr(self, "aspect_frame"):
            self.aspect_frame.set_ratio_from_label(label)

    def _open_preview_settings(self) -> None:
        current = self.preview_format_combo.currentText()
        dialog = PreviewSettingsDialog(current, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.preview_format_combo.blockSignals(True)
        self.preview_format_combo.setCurrentText(dialog.selected_format)
        self.preview_format_combo.blockSignals(False)
        self._on_preview_format_changed(dialog.selected_format)
        if dialog.take_screenshot:
            self._save_preview_screenshot()

    def _save_preview_screenshot(self) -> None:
        if not hasattr(self, "preview_surface"):
            return
        folder = Path.cwd() / "output" / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = self._format_ms(self.current_time_ms).replace(":", "-").replace(".", "-")
        path = folder / f"ares_frame_{stamp}.jpg"
        pixmap = self.preview_surface.grab()
        if pixmap.save(str(path), "JPG", 92):
            self.statusBar().showMessage(f"Ekran goruntusu kaydedildi: {path.name}")
        else:
            QMessageBox.warning(self, "Uyari", "Ekran goruntusu kaydedilemedi.")

    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewPanel")
        panel.setStyleSheet("QFrame#previewPanel { background-color: #0B1120; border-radius: 8px; }")
        
        main_layout = QHBoxLayout(panel)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        preview_col_layout = QVBoxLayout()
        preview_col_layout.setSpacing(10)

        self.aspect_frame = AspectRatioFrame(16, 9)
        self.aspect_frame.setStyleSheet("background-color: transparent;")

        self.preview_surface = QFrame()
        self.preview_surface.setObjectName("previewSurface")
        self.preview_surface.setMinimumSize(120, 120)
        self.preview_surface.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_surface.setStyleSheet(
            "#previewSurface { background-color: #000000; border-radius: 8px; border: 1px solid #1E293B; }"
        )
        self.aspect_frame.content_layout().addWidget(self.preview_surface, 1)

        preview_stack = QStackedLayout(self.preview_surface)
        preview_stack.setStackingMode(QStackedLayout.StackAll)

        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self.video_widget, "setAspectRatioMode"):
            self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.media_player.setVideoOutput(self.video_widget)

        self.subtitle_preview = QLabel()
        self.subtitle_preview.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        self.subtitle_preview.setWordWrap(True)
        self.subtitle_preview.setStyleSheet("background-color: transparent;")
        
        preview_stack.addWidget(self.subtitle_preview) # Top
        preview_stack.addWidget(self.video_widget)     # Bottom

        # ── Transport Bar ─────────────────────────────────────────────────────
        transport_widget = QWidget()
        transport_widget.setFixedHeight(48)
        transport_widget.setStyleSheet(
            "background: #0D1117;"
            "border-top: 1px solid #1E293B;"
        )
        controls_row = QHBoxLayout(transport_widget)
        controls_row.setContentsMargins(10, 0, 10, 0)
        controls_row.setSpacing(8)

        C_TRANSPORT = "#94A3B8"
        C_TRANSPORT_DIM = "#64748B"
        C_PLAY_ACCENT = "#22D3EE"
        C_STOP_ACCENT = "#F87171"

        def make_transport_btn(
            icon_name: str,
            color: str,
            tooltip: str,
            size: int = 32,
            icon_size: int = 16,
            callback=None,
        ) -> QPushButton:
            btn = QPushButton(qta.icon(icon_name, color=color), "")
            btn.setFixedSize(size, size)
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: rgba(148, 163, 184, 0.12);
                }}
                QPushButton:pressed {{
                    background: rgba(148, 163, 184, 0.2);
                }}
                QPushButton:disabled {{
                    color: #334155;
                }}
            """)
            if callback:
                btn.clicked.connect(callback)
            return btn

        def make_divider(height: int = 20) -> QFrame:
            d = QFrame()
            d.setFrameShape(QFrame.VLine)
            d.setFixedSize(1, height)
            d.setStyleSheet("background: #252F42; border: none;")
            return d

        transport_cluster = QWidget()
        transport_cluster.setStyleSheet("background: transparent;")
        cluster_layout = QHBoxLayout(transport_cluster)
        cluster_layout.setContentsMargins(0, 0, 0, 0)
        cluster_layout.setSpacing(2)

        self.btn_frame_back = make_transport_btn(
            "mdi.skip-previous-outline", C_TRANSPORT_DIM, "1 Kare Geri (←)", 30, 15,
            lambda: self._jump_time(-40),
        )
        self.btn_backward = make_transport_btn(
            "mdi.rewind-5", C_TRANSPORT, "5 sn Geri", 32, 17,
            lambda: self._jump_time(-5000),
        )

        self.btn_play_pause = make_transport_btn(
            "mdi.play-outline", C_PLAY_ACCENT, "Oynat / Duraklat", 38, 20,
            self._toggle_preview_playback,
        )
        self.btn_stop = make_transport_btn(
            "mdi.square-outline", C_STOP_ACCENT, "Durdur", 34, 16,
            self._stop_preview,
        )

        self.btn_forward = make_transport_btn(
            "mdi.fast-forward-5", C_TRANSPORT, "5 sn İleri", 32, 17,
            lambda: self._jump_time(5000),
        )
        self.btn_frame_fwd = make_transport_btn(
            "mdi.skip-next-outline", C_TRANSPORT_DIM, "1 Kare İleri (→)", 30, 15,
            lambda: self._jump_time(40),
        )

        cluster_layout.addWidget(self.btn_frame_back)
        cluster_layout.addWidget(self.btn_backward)
        cluster_layout.addSpacing(6)
        cluster_layout.addWidget(self.btn_play_pause)
        cluster_layout.addWidget(self.btn_stop)
        cluster_layout.addSpacing(6)
        cluster_layout.addWidget(self.btn_forward)
        cluster_layout.addWidget(self.btn_frame_fwd)
        cluster_layout.addSpacing(10)
        cluster_layout.addWidget(make_divider(22))

        self.timeline_label = QLabel("00:00.000")
        self.timeline_label.setAlignment(Qt.AlignCenter)
        self.timeline_label.setFixedWidth(96)
        self.timeline_label.setStyleSheet(
            "color: #E2E8F0;"
            "font-size: 12px;"
            "font-family: 'Consolas', monospace;"
            "font-weight: 600;"
            "letter-spacing: 0.5px;"
            "background: transparent;"
            "border: none;"
            "padding: 0px 4px;"
        )

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(64)
        self.speed_combo.setToolTip("Oynatma Hızı")
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background: transparent;
                color: #94A3B8;
                border: 1px solid #252F42;
                border-radius: 4px;
                padding: 2px 4px;
                font-weight: 600;
                font-size: 11px;
            }
            QComboBox:hover { border-color: #3B4F70; color: #CBD5E1; }
            QComboBox::drop-down { border: none; width: 14px; }
            QComboBox QAbstractItemView {
                background: #111827;
                color: #CBD5E1;
                border: 1px solid #1E2840;
                selection-background-color: #1E3A5F;
            }
        """)
        self.speed_combo.currentTextChanged.connect(self._change_speed)

        cluster_layout.addWidget(self.timeline_label)
        cluster_layout.addWidget(self.speed_combo)

        right_grp = QHBoxLayout()
        right_grp.setSpacing(6)
        right_grp.setContentsMargins(0, 0, 0, 0)

        self.visualizer = AudioVisualizer()
        self.visualizer.hide()
        right_grp.addWidget(self.visualizer)

        self.preview_format_combo = QComboBox()
        self.preview_format_combo.addItems(["16:9", "9:16", "1:1", "4:5"])
        self.preview_format_combo.setFixedWidth(58)
        self.preview_format_combo.setToolTip("En-Boy Oranı")
        self.preview_format_combo.setStyleSheet("""
            QComboBox {
                background: transparent;
                color: #94A3B8;
                border: 1px solid #252F42;
                border-radius: 4px;
                padding: 2px 4px;
                font-weight: 600;
                font-size: 11px;
            }
            QComboBox:hover { border-color: #3B4F70; color: #CBD5E1; }
            QComboBox::drop-down { border: none; width: 14px; }
            QComboBox QAbstractItemView {
                background: #111827;
                color: #CBD5E1;
                border: 1px solid #1E2840;
                selection-background-color: #1E3A5F;
            }
        """)
        self.preview_format_combo.currentTextChanged.connect(self._on_preview_format_changed)
        right_grp.addWidget(self.preview_format_combo)

        self.btn_settings = make_transport_btn(
            "mdi.tune-vertical", C_TRANSPORT_DIM, "Önizleme Ayarları", 32, 16,
            self._open_preview_settings,
        )
        right_grp.addWidget(self.btn_settings)
        right_grp.addWidget(make_divider(22))

        self.btn_export_mini = QPushButton("Dışa Aktar")
        self.btn_export_mini.setIcon(qta.icon("mdi.export", color="#E2E8F0"))
        self.btn_export_mini.setIconSize(QSize(14, 14))
        self.btn_export_mini.setFixedHeight(30)
        self.btn_export_mini.setToolTip("Projeyi Dışa Aktar")
        self.btn_export_mini.setStyleSheet("""
            QPushButton {
                background: #2563EB;
                color: #F8FAFC;
                border: none;
                border-radius: 6px;
                padding: 0px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton:pressed { background: #1E40AF; }
        """)
        self.btn_export_mini.clicked.connect(self._prepare_export)
        right_grp.addWidget(self.btn_export_mini)

        controls_row.addStretch(1)
        controls_row.addWidget(transport_cluster)
        controls_row.addStretch(1)
        controls_row.addLayout(right_grp)

        preview_col_layout.addWidget(self.aspect_frame, 1)
        preview_col_layout.addWidget(transport_widget)

        main_layout.addLayout(preview_col_layout, 1)

        QTimer.singleShot(0, lambda: self._on_preview_format_changed(self.preview_format_combo.currentText()))

        return panel

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
        if paths:
            self._import_timeline_files(paths)
            event.acceptProposedAction()

    def _refresh_preview(self) -> None:
        font_name = self.font_combo.currentText() if hasattr(self, "font_combo") else "Arial"
        size = self.font_size_spin.value() if hasattr(self, "font_size_spin") else 32
        stroke = self.stroke_spin.value() if hasattr(self, "stroke_spin") else 3
        shadow = self.shadow_spin.value() if hasattr(self, "shadow_spin") else 4
        position = self.position_combo.currentText() if hasattr(self, "position_combo") else "Alt Orta"
        subtitle = find_subtitle_at_time(self.timed_subtitles, self.current_time_ms)
        active_index = find_active_word_index(subtitle, self.current_time_ms)

        self.subtitle_preview.setAlignment(qt_preview_alignment(position))
        self.subtitle_preview.setText(self._build_preview_markup(subtitle, active_index))
        self.subtitle_preview.setStyleSheet(
            "QLabel {"
            f"font-family: '{font_name}';"
            f"font-size: {size}px;"
            f"{preview_padding(position, shadow)}"
            "background-color: transparent;"
            "}"
        )
        self.subtitle_preview.setToolTip(
            f"Font: {font_name} | Boyut: {size} | Stroke: {stroke} | Golge: {shadow}"
        )
        self.timeline_label.setText(self._format_ms(self.current_time_ms))

    def _build_preview_markup(self, subtitle, active_index: int | None) -> str:
        if subtitle and subtitle.words:
            parts = []
            for word in subtitle.words:
                color = self.active_color.name() if word.index == active_index else self.normal_color.name()
                weight = "700" if word.index == active_index else "500"
                parts.append(
                    f'<span style="color:{color}; font-weight:{weight};">{escape(word.text)}</span>'
                )
            return " ".join(parts)

        return (
            f'<span style="color:{self.normal_color.name()};">Bugün </span>'
            f'<span style="color:{self.active_color.name()}; font-weight:700;">aktif</span>'
            f'<span style="color:{self.normal_color.name()};"> kelime vurgulanıyor.</span>'
        )

    def _build_subtitle_info(self, subtitle, active_index: int | None) -> str:
        if subtitle is None:
            return "Hazir altyazi yuklenmedi."

        word_count = len(subtitle.words)
        active_display = active_index + 1 if active_index is not None else 0
        return (
            f"Satir {subtitle.entry.index} | Aralik: {self._format_ms(subtitle.start_ms)} - "
            f"{self._format_ms(subtitle.end_ms)} | Aktif kelime: {active_display}/{word_count}"
        )

    def _format_ms(self, value: int) -> str:
        minutes, remainder = divmod(max(0, value), 60_000)
        seconds, milliseconds = divmod(remainder, 1_000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def _change_zoom(self, delta: float) -> None:
        self.timeline_panel.change_zoom(delta)

    def _on_timeline_playhead(self, value: int) -> None:
        self.current_time_ms = value
        if not self.media_player.source().isEmpty():
            self.media_player.setPosition(value)
        self._refresh_preview()

    def _playback_max_ms(self) -> int:
        return self.timeline_panel.playhead_max_ms()

    def _seek_playhead(self, ms: int, *, emit: bool = True) -> None:
        self.timeline_panel.set_playhead(ms, emit=emit)
        self.current_time_ms = self.timeline_panel._playhead_ms

    def _jump_time(self, delta_ms: int) -> None:
        self._seek_playhead(self.current_time_ms + delta_ms)

    def _set_playback_icon(self, state: str) -> None:
        icon_name = "mdi.pause" if state == "pause" else "mdi.play-outline"
        self.btn_play_pause.setIcon(qta.icon(icon_name, color=COLOR_PLAY_TEAL))

    def _stop_preview(self) -> None:
        self.media_player.stop()
        self.preview_timer.stop()
        self.visualizer.update_wave(False)
        self._set_playback_icon("play")
        self._seek_playhead(0)
        self._refresh_preview()

    def _change_speed(self, text: str) -> None:
        speed = float(text.replace("x", ""))
        self.media_player.setPlaybackRate(speed)

    def _toggle_preview_playback(self) -> None:
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.preview_timer.stop()
            self.visualizer.update_wave(False)
            self._set_playback_icon("play")
        else:
            max_ms = self._playback_max_ms()
            if max_ms > 0 and self.current_time_ms >= max_ms:
                self._seek_playhead(0, emit=False)
            self.media_player.play()
            self.preview_timer.start()
            self.visualizer.update_wave(True)
            self._set_playback_icon("pause")

        self._refresh_preview()

    def _advance_preview(self) -> None:
        if not self.media_player.source().isEmpty():
            pos = self.media_player.position()
            self.current_time_ms = pos
            self.timeline_panel.set_playhead(pos, emit=False)
            
            if self.media_player.playbackState() == QMediaPlayer.StoppedState:
                self._stop_preview()
                return
        else:
            if not self.timed_subtitles:
                self.preview_timer.stop()
                self.visualizer.update_wave(False)
                return
            
            max_ms = self._playback_max_ms()
            next_value = min(max_ms, self.current_time_ms + self.preview_timer.interval())
            self._seek_playhead(next_value)
            
            if max_ms > 0 and next_value >= max_ms:
                self._stop_preview()
                return

        self.visualizer.update_wave(True)
        self._refresh_preview()


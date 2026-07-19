from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFontDatabase, QPalette
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from app.core.animation_presets import ANIMATION_POP, animation_names
from app.core.ffmpeg_paths import is_nvenc_available
from app.core.style_presets import CUSTOM_PRESET_NAME, default_aspect_ratio_options, get_preset, preset_names
from app.core.subtitle_positions import position_names
from app.core.video_presets import is_vertical_format
from app.ui.app_theme import (
    ACCENT_HOVER,
    ACCENT_TEAL,
    BG_DROP_ZONE,
    BG_DROP_ZONE_HOVER,
    BG_HOVER,
    BG_INPUT,
    BG_PANEL,
    BG_SIDEBAR,
    BG_STACK,
    BORDER,
    BORDER_DASHED,
    BTN_MP4_GRADIENT,
    BTN_MP4_HOVER,
    BTN_PREVIEW_GRADIENT,
    BTN_PREVIEW_HOVER,
    BTN_PRIMARY_GRADIENT,
    BTN_PRIMARY_HOVER,
    BTN_SRT_GRADIENT,
    BTN_SRT_HOVER,
    COLOR_DANGER,
    COLOR_ICON_ACTIVE,
    COLOR_ICON_DEFAULT,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    TEXT_MUTED,
    TEXT_ON_ACCENT,
    TEXT_PRIMARY,
    action_button_qss,
)


class MainWindowControlsMixin:
    def _build_controls_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("controlsPanel")
        panel.setStyleSheet(
            f"QFrame#controlsPanel {{"
            f"  background-color: {BG_PANEL};"
            f"  border-right: 1px solid {BORDER};"
            f"}}"
        )

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar_icon_specs = [
            ("ph.plus-bold", "Medya & Dosya", COLOR_SUCCESS),
            ("ph.gear-fill", "Video Ayarlari", COLOR_INFO),
            ("ph.image-fill", "Logo Ayarlari", COLOR_WARNING),
            ("ph.text-t-bold", "Altyazi Stili", "#5A4A8A"),
            ("ph.lightning-fill", "Islemler", ACCENT_TEAL),
        ]

        # Sidebar — Movavi tarzi: sade ikonlar, sol cizgi ile secim
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(52)
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        self.sidebar.setIconSize(QSize(22, 22))
        self.sidebar.setSpacing(2)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        self.sidebar.setAutoFillBackground(False)
        self.sidebar.viewport().setAutoFillBackground(False)
        sidebar_palette = self.sidebar.palette()
        sidebar_palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        sidebar_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        sidebar_palette.setColor(QPalette.ColorRole.Highlight, Qt.GlobalColor.transparent)
        sidebar_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ACCENT_TEAL))
        self.sidebar.setPalette(sidebar_palette)
        self.sidebar.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_SIDEBAR};
                border: none;
                border-right: 2px solid {ACCENT_TEAL};
                outline: 0;
                padding: 12px 0px;
            }}
            QListWidget::item {{
                height: 44px;
                padding: 0px;
                margin: 2px 0px;
                background: transparent;
                border: none;
                border-left: 3px solid transparent;
            }}
            QListWidget::item:selected,
            QListWidget::item:selected:active,
            QListWidget::item:selected:!active,
            QListWidget::item:hover,
            QListWidget::item:focus {{
                background: transparent;
                outline: none;
            }}
            QListWidget::item:selected {{
                border-left: 3px solid {ACCENT_TEAL};
            }}
        """)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"""
            QStackedWidget {{ background-color: {BG_STACK}; }}
            QGroupBox {{
                background-color: transparent;
                border: none;
                margin-top: 6px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0px;
                left: 0px;
                top: 0px;
                color: {TEXT_PRIMARY};
                font-weight: bold;
                font-size: 13px;
                background: transparent;
            }}
        """)

        def add_page(icon_name: str, tooltip: str, icon_color: str, widget: QWidget) -> None:
            item = QListWidgetItem()
            item.setIcon(qta.icon(icon_name, color=icon_color))
            item.setToolTip(tooltip)
            item.setTextAlignment(Qt.AlignCenter)
            self.sidebar.addItem(item)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet(
                "QScrollArea { background-color: transparent; border: none; }"
                "QWidget { background-color: transparent; }"
            )

            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(16, 16, 16, 16)

            v_layout.addWidget(widget)
            v_layout.addStretch(1)

            scroll.setWidget(container)
            self.stacked_widget.addWidget(scroll)

        add_page("ph.plus-bold", "Medya & Dosya", COLOR_SUCCESS, self._build_file_group())
        add_page("ph.gear-fill", "Video Ayarlari", COLOR_INFO, self._build_video_settings_group())
        add_page("ph.image-fill", "Logo Ayarlari", COLOR_WARNING, self._build_logo_group())
        add_page("ph.text-t-bold", "Altyazi Stili", "#5A4A8A", self._build_style_group())
        add_page("ph.lightning-fill", "Islemler", ACCENT_TEAL, self._build_action_group())

        self.sidebar.currentRowChanged.connect(self._on_sidebar_row_changed)
        self.sidebar.setCurrentRow(0)
        self._update_sidebar_icons(0)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stacked_widget)

        return panel

    def _on_sidebar_row_changed(self, row: int) -> None:
        if row < 0:
            return
        self._update_sidebar_icons(row)
        self.stacked_widget.setCurrentIndex(row)

    def _update_sidebar_icons(self, selected_row: int) -> None:
        for index, (icon_name, _tooltip, icon_color) in enumerate(self._sidebar_icon_specs):
            color = icon_color if index == selected_row else COLOR_ICON_DEFAULT
            item = self.sidebar.item(index)
            if item is not None:
                item.setIcon(qta.icon(icon_name, color=color))

    def _build_video_settings_group(self) -> QGroupBox:
        group = QGroupBox("Video Ayarları")
        layout = QFormLayout(group)
        layout.setSpacing(10)

        self.format_combo = QComboBox()
        self.format_combo.addItems(default_aspect_ratio_options())
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["Orijinal", "30", "60"])
        
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["Orijinal", "128k", "192k", "256k", "320k"])
        self.audio_quality_combo.setCurrentText("192k")
        
        self.denoise_checkbox = QCheckBox("Dip Sesi ve Gürültüyü Temizle")
        self.denoise_checkbox.setChecked(False)

        self.gpu_checkbox = QCheckBox("GPU Hızlandırma (NVIDIA NVENC)")
        gpu_ready = is_nvenc_available()
        self.gpu_checkbox.setChecked(gpu_ready)
        self.gpu_checkbox.setEnabled(gpu_ready)
        if gpu_ready:
            self.gpu_checkbox.setToolTip("NVIDIA ekran kartınız varsa dışa aktarımı çok hızlandırır.")
        else:
            self.gpu_checkbox.setToolTip(
                "Bu bilgisayarda NVIDIA NVENC kullanılamıyor (nvcuda.dll / sürücü yok). "
                "Export CPU ile yapılır."
            )

        layout.addRow("Format", self.format_combo)
        layout.addRow("FPS", self.fps_combo)
        layout.addRow("Ses Kalitesi", self.audio_quality_combo)
        layout.addRow("", self.denoise_checkbox)
        layout.addRow("", self.gpu_checkbox)

        return group

    def _build_file_group(self) -> QWidget:
        group = QGroupBox("Ice aktar")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)

        self.import_drop_zone = QFrame()
        self.import_drop_zone.setObjectName("importDropZone")
        self.import_drop_zone.setMinimumHeight(150)
        self.import_drop_zone.setCursor(Qt.PointingHandCursor)
        self.import_drop_zone.setStyleSheet(
            f"QFrame#importDropZone {{"
            f"  background-color: {BG_DROP_ZONE};"
            f"  border: 1px dashed {BORDER_DASHED};"
            f"  border-radius: 8px;"
            f"}}"
            f"QFrame#importDropZone:hover {{"
            f"  border-color: {ACCENT_TEAL};"
            f"  background-color: {BG_DROP_ZONE_HOVER};"
            f"}}"
        )
        drop_layout = QVBoxLayout(self.import_drop_zone)
        drop_layout.setContentsMargins(20, 24, 20, 24)
        drop_layout.setSpacing(14)

        drop_hint = QLabel("Dosyalari veya klasorleri buraya surukleyin")
        drop_hint.setAlignment(Qt.AlignCenter)
        drop_hint.setWordWrap(True)
        drop_hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; background: transparent; border: none;")
        drop_layout.addWidget(drop_hint)

        self.btn_add_files = QPushButton("Dosyalari ekle")
        self.btn_add_files.setCursor(Qt.PointingHandCursor)
        self.btn_add_files.setStyleSheet(
            f"QPushButton {{"
            f"  background: {BTN_PRIMARY_GRADIENT};"
            f"  color: {TEXT_ON_ACCENT};"
            f"  border: 1px solid {ACCENT_HOVER};"
            f"  border-radius: 6px;"
            f"  padding: 10px 24px;"
            f"  font-weight: bold;"
            f"  font-size: 12px;"
            f"}}"
            f"QPushButton:hover {{ background: {BTN_PRIMARY_HOVER}; }}"
        )
        self.btn_add_files.clicked.connect(self._pick_timeline_video)
        drop_layout.addWidget(self.btn_add_files, 0, Qt.AlignHCenter)

        def _drop_zone_clicked(event) -> None:
            if event.button() == Qt.LeftButton:
                self._pick_timeline_video()

        self.import_drop_zone.mousePressEvent = _drop_zone_clicked
        layout.addWidget(self.import_drop_zone)

        path_box = QVBoxLayout()
        path_box.setSpacing(8)

        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Timeline'daki video...")
        self.video_input.setReadOnly(True)
        self.video_input.setStyleSheet(
            f"QLineEdit {{ background-color: {BG_INPUT}; border: 1px solid {BORDER}; font-size: 11px; }}"
        )

        video_row = QHBoxLayout()
        video_row.setSpacing(6)
        v_lbl = QLabel("Video")
        v_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; min-width: 48px;")
        video_row.addWidget(v_lbl)
        video_row.addWidget(self.video_input, 1)

        self.btn_clear_video = QPushButton(qta.icon("fa5s.times", color=COLOR_DANGER), "")
        self.btn_clear_video.setFixedSize(26, 26)
        self.btn_clear_video.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {BORDER}; border-radius: 4px; padding: 2px; }}"
            f"QPushButton:hover {{ background: rgba(181,58,58,0.12); border-color: {COLOR_DANGER}; }}"
        )
        self.btn_clear_video.clicked.connect(self._clear_video)
        video_row.addWidget(self.btn_clear_video)
        path_box.addLayout(video_row)

        self.subtitle_input = QLineEdit()
        self.subtitle_input.setPlaceholderText("Altyazi dosyasi (SRT)...")
        self.subtitle_input.setReadOnly(True)
        self.subtitle_input.setCursor(Qt.PointingHandCursor)
        self.subtitle_input.setStyleSheet(
            f"QLineEdit {{ background-color: {BG_INPUT}; border: 1px solid {BORDER}; font-size: 11px; }}"
        )
        self.subtitle_input.mousePressEvent = self._subtitle_input_clicked

        subtitle_row = QHBoxLayout()
        subtitle_row.setSpacing(6)
        s_lbl = QLabel("Altyazi")
        s_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; min-width: 48px;")
        subtitle_row.addWidget(s_lbl)
        subtitle_row.addWidget(self.subtitle_input, 1)

        self.btn_clear_subtitle = QPushButton(qta.icon("fa5s.times", color=COLOR_DANGER), "")
        self.btn_clear_subtitle.setFixedSize(26, 26)
        self.btn_clear_subtitle.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {BORDER}; border-radius: 4px; padding: 2px; }}"
            f"QPushButton:hover {{ background: rgba(181,58,58,0.12); border-color: {COLOR_DANGER}; }}"
        )
        self.btn_clear_subtitle.clicked.connect(self._clear_subtitle)
        subtitle_row.addWidget(self.btn_clear_subtitle)
        path_box.addLayout(subtitle_row)

        layout.addLayout(path_box)
        return group

    def _subtitle_input_clicked(self, event) -> None:
        from PySide6.QtWidgets import QLineEdit
        if event.button() == Qt.LeftButton:
            self._select_subtitle()
        QLineEdit.mousePressEvent(self.subtitle_input, event)

    def _build_logo_group(self) -> QGroupBox:
        group = QGroupBox("Logo Ayarları")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(10)

        self.logo_input = QLineEdit()
        self.logo_input.setPlaceholderText("Videoya eklenecek logo seçin (PNG)")
        self.logo_input.setReadOnly(True)
        logo_button = QPushButton("Logo Seç")
        logo_button.clicked.connect(self._select_logo)

        self.logo_pos_combo = QComboBox()
        self.logo_pos_combo.addItems(["Sol Üst", "Sağ Üst", "Sol Alt", "Sağ Alt"])
        self.logo_pos_combo.setCurrentText("Sağ Üst")

        self.logo_size_spin = QSpinBox()
        self.logo_size_spin.setRange(50, 1000)
        self.logo_size_spin.setValue(150)
        self.logo_size_spin.setSuffix(" px")

        layout.addWidget(QLabel("Dosya"), 0, 0)
        layout.addWidget(self.logo_input, 0, 1)
        layout.addWidget(logo_button, 0, 2)
        
        layout.addWidget(QLabel("Konum"), 1, 0)
        layout.addWidget(self.logo_pos_combo, 1, 1, 1, 2)
        
        layout.addWidget(QLabel("Boyut"), 2, 0)
        layout.addWidget(self.logo_size_spin, 2, 1, 1, 2)

        return group

    def _build_style_group(self) -> QGroupBox:
        group = QGroupBox("Altyazı Stili")
        layout = QFormLayout(group)
        layout.setSpacing(10)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(preset_names())
        self.preset_combo.setCurrentText(CUSTOM_PRESET_NAME)
        self.preset_combo.currentTextChanged.connect(self._apply_style_preset)
        layout.addRow("Stil Şablonu", self.preset_combo)

        self.preset_desc_label = QLabel("")
        self.preset_desc_label.setWordWrap(True)
        self.preset_desc_label.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: normal; font-size: 10px;")
        layout.addRow("", self.preset_desc_label)

        self.font_combo = QComboBox()
        # Turkce karakter destegi yuksek olan yaygin fontlari one alalim
        fonts = ["Arial", "Segoe UI", "Roboto", "Tahoma", "Verdana", "Michroma"] + QFontDatabase.families()
        unique_fonts = []
        for f in fonts:
            if f not in unique_fonts:
                unique_fonts.append(f)
        self.font_combo.addItems(unique_fonts)
        self.font_combo.setCurrentText("Arial")
        self.font_combo.currentTextChanged.connect(self._on_style_control_changed)

        self.normal_color_button = QPushButton()
        self.normal_color_button.clicked.connect(lambda: self._pick_color("normal"))

        self.active_color_button = QPushButton()
        self.active_color_button.clicked.connect(lambda: self._pick_color("active"))

        self.position_combo = QComboBox()
        self.position_combo.addItems(position_names())
        self.position_combo.setCurrentText("Alt Orta")
        self.position_combo.currentTextChanged.connect(self._on_style_control_changed)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 96)
        self.font_size_spin.setValue(32)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setAccelerated(True)
        self.font_size_spin.setKeyboardTracking(False)
        self.font_size_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.font_size_spin.setFixedWidth(58)
        self.font_size_spin.setToolTip("8–96 px — kaydırıcı veya doğrudan yazın")

        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(8, 96)
        self.font_size_slider.setValue(32)
        self.font_size_slider.setPageStep(4)
        self.font_size_slider.setSingleStep(1)
        self.font_size_slider.setToolTip("Yazı boyutunu sürükleyerek ayarlayın")

        font_size_row = QWidget()
        font_size_layout = QHBoxLayout(font_size_row)
        font_size_layout.setContentsMargins(0, 0, 0, 0)
        font_size_layout.setSpacing(8)
        font_size_layout.addWidget(self.font_size_slider, 1)
        font_size_layout.addWidget(self.font_size_spin)

        self.font_size_slider.valueChanged.connect(self._on_font_size_slider_changed)
        self.font_size_spin.valueChanged.connect(self._on_font_size_spin_changed)

        self.stroke_spin = QSpinBox()
        self.stroke_spin.setRange(0, 12)
        self.stroke_spin.setValue(3)
        self.stroke_spin.valueChanged.connect(self._on_style_control_changed)

        self.shadow_spin = QSpinBox()
        self.shadow_spin.setRange(0, 20)
        self.shadow_spin.setValue(4)
        self.shadow_spin.valueChanged.connect(self._on_style_control_changed)

        self.anim_combo = QComboBox()
        self.anim_combo.addItems(animation_names())
        self.anim_combo.setCurrentText(ANIMATION_POP)
        self.anim_combo.currentTextChanged.connect(self._on_style_control_changed)

        self.bg_box_checkbox = QCheckBox("Altyazı Arkasına Siyah Kutu (Bg Box)")
        self.bg_box_checkbox.setChecked(False)
        self.bg_box_checkbox.toggled.connect(self._on_style_control_changed)

        layout.addRow("Font", self.font_combo)
        layout.addRow("Normal Renk", self.normal_color_button)
        layout.addRow("Aktif Kelime Rengi", self.active_color_button)
        layout.addRow("Konum", self.position_combo)
        layout.addRow("Yazı Boyutu", font_size_row)
        layout.addRow("Kalınlık", self.stroke_spin)
        layout.addRow("Gölge", self.shadow_spin)
        layout.addRow("Animasyon", self.anim_combo)
        layout.addRow(self.bg_box_checkbox)

        self._update_color_button("normal")
        self._update_color_button("active")

        return group

    def _on_format_changed(self, name: str) -> None:
        self._sync_preview_format(name)

    def _sync_preview_format(self, format_name: str) -> None:
        if not hasattr(self, "preview_format_combo"):
            return
        target = "9:16" if is_vertical_format(format_name) else "16:9"
        self.preview_format_combo.blockSignals(True)
        self.preview_format_combo.setCurrentText(target)
        self.preview_format_combo.blockSignals(False)

    def _set_font_size(self, value: int) -> None:
        value = max(8, min(96, int(value)))
        self.font_size_spin.blockSignals(True)
        self.font_size_slider.blockSignals(True)
        self.font_size_spin.setValue(value)
        self.font_size_slider.setValue(value)
        self.font_size_spin.blockSignals(False)
        self.font_size_slider.blockSignals(False)

    def _on_font_size_slider_changed(self, value: int) -> None:
        if self.font_size_spin.value() != value:
            self.font_size_spin.blockSignals(True)
            self.font_size_spin.setValue(value)
            self.font_size_spin.blockSignals(False)
        self._on_style_control_changed()

    def _on_font_size_spin_changed(self, value: int) -> None:
        if self.font_size_slider.value() != value:
            self.font_size_slider.blockSignals(True)
            self.font_size_slider.setValue(value)
            self.font_size_slider.blockSignals(False)
        self._on_style_control_changed()

    def _on_style_control_changed(self, *_args) -> None:
        if getattr(self, "_applying_preset", False):
            self._refresh_preview()
            return
        if hasattr(self, "preset_combo") and self.preset_combo.currentText() != CUSTOM_PRESET_NAME:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentText(CUSTOM_PRESET_NAME)
            self.preset_combo.blockSignals(False)
            self.preset_desc_label.setText("")
        self._refresh_preview()

    def _apply_style_preset(self, name: str) -> None:
        preset = get_preset(name)
        if preset is None:
            self.preset_desc_label.setText("")
            return

        self._applying_preset = True
        try:
            self.preset_desc_label.setText(preset.description)
            self.font_combo.setCurrentText(preset.font_name)
            self._set_font_size(preset.font_size)
            self.normal_color = QColor(preset.normal_color)
            self.active_color = QColor(preset.active_color)
            self._update_color_button("normal")
            self._update_color_button("active")
            self.position_combo.setCurrentText(preset.position)
            self.stroke_spin.setValue(preset.stroke_size)
            self.shadow_spin.setValue(preset.shadow_size)
            self.anim_combo.setCurrentText(preset.animation_style)
            self.bg_box_checkbox.setChecked(preset.bg_box)
            self.format_combo.setCurrentText(preset.aspect_ratio)
            self.fps_combo.setCurrentText(preset.fps)
            self._sync_preview_format(preset.aspect_ratio)
        finally:
            self._applying_preset = False
        self._refresh_preview()
        self.statusBar().showMessage(f"Stil sablonu uygulandi: {name}")

    def _build_action_group(self) -> QGroupBox:
        group = QGroupBox("İşlemler")
        layout = QVBoxLayout(group)
        
        self.video_tools_button = QPushButton("Video Araçları (Kes/Birleştir)")
        self.video_tools_button.setStyleSheet(
            f"background: {BTN_PRIMARY_GRADIENT}; color: {TEXT_ON_ACCENT};"
        )
        self.video_tools_button.clicked.connect(self._open_video_tools)

        self.transcribe_button = QPushButton("Otomatik Altyazı Üret (Whisper)")
        self.transcribe_button.setStyleSheet(
            f"background: {BTN_PRIMARY_GRADIENT}; color: {TEXT_ON_ACCENT};"
        )
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.clicked.connect(self._run_transcription)

        transcribe_hint = QLabel(
            "Model, dil ve ceviri secenekleri ile kelime zamanlamali SRT uretir."
        )
        transcribe_hint.setWordWrap(True)
        transcribe_hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: normal;")

        self.parse_button = QPushButton("SRT Ön Hazırlık")
        self.parse_button.setStyleSheet(
            action_button_qss(BTN_SRT_GRADIENT, BTN_SRT_HOVER, ACCENT_TEAL)
        )
        self.parse_button.clicked.connect(self._parse_subtitle)

        self.edit_button = QPushButton("Altyazı Düzenle")
        self.edit_button.setStyleSheet(
            action_button_qss(BTN_SRT_GRADIENT, BTN_SRT_HOVER, ACCENT_TEAL)
        )
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self._open_subtitle_editor)

        self.preview_export_button = QPushButton("Gerçek Önizleme (Kare)")
        self.preview_export_button.setStyleSheet(
            action_button_qss(BTN_PREVIEW_GRADIENT, BTN_PREVIEW_HOVER, COLOR_INFO)
        )
        self.preview_export_button.setEnabled(False)
        self.preview_export_button.clicked.connect(self._show_real_preview)

        self.export_button = QPushButton("MP4 Dışa Aktar")
        self.export_button.setStyleSheet(
            action_button_qss(BTN_MP4_GRADIENT, BTN_MP4_HOVER, COLOR_SUCCESS)
        )
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._prepare_export)

        helper_text = QLabel(
            "Gerçek Önizleme (Kare) butonu, o anki saniyede FFmpeg üzerinden "
            "logolu ve altyazılı final görüntüyü oluşturur."
        )
        helper_text.setWordWrap(True)
        helper_text.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: normal; font-size: 10px; margin-top: 8px;")
        helper_text.setAlignment(Qt.AlignTop)

        layout.addWidget(self.video_tools_button)
        layout.addWidget(self.transcribe_button)
        layout.addWidget(transcribe_hint)
        layout.addWidget(self.parse_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.preview_export_button)
        layout.addWidget(self.export_button)
        layout.addWidget(helper_text)

        return group

    def _pick_color(self, target: str) -> None:
        current = self.normal_color if target == "normal" else self.active_color
        selected = QColorDialog.getColor(current, self, "Renk Sec")
        if not selected.isValid():
            return

        if target == "normal":
            self.normal_color = selected
        else:
            self.active_color = selected

        self._update_color_button(target)
        self._on_style_control_changed()

    def _update_color_button(self, target: str) -> None:
        color = self.normal_color if target == "normal" else self.active_color
        button = self.normal_color_button if target == "normal" else self.active_color_button
        button.setText(color.name().upper())
        button.setStyleSheet(
            "QPushButton {"
            f"background-color: {color.name()};"
            f"color: {TEXT_PRIMARY};"
            "font-weight: 600;"
            "padding: 8px 12px;"
            "border-radius: 8px;"
            "}"
        )


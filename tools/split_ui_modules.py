"""One-off script to split large UI modules."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "ui"


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def split_timeline() -> None:
    src_path = ROOT / "timeline_panel.py"
    lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)
    timeline_dir = ROOT / "timeline"
    timeline_dir.mkdir(exist_ok=True)

    (timeline_dir / "theme.py").write_text(
        "from __future__ import annotations\n\n"
        "from PySide6.QtGui import QColor\n\n"
        "from app.core.timeline import TRACK_AUDIO, TRACK_SUBTITLE, TRACK_VIDEO\n\n"
        + slice_lines(lines, 29, 62),
        encoding="utf-8",
    )

    (timeline_dir / "ruler.py").write_text(
        "from __future__ import annotations\n\n"
        "from PySide6.QtCore import Qt, Signal, QPointF\n"
        "from PySide6.QtGui import (\n"
        "    QColor, QPainter, QPen, QPolygonF, QBrush, QFont, QMouseEvent, QLinearGradient,\n"
        ")\n"
        "from PySide6.QtWidgets import QWidget\n\n"
        "from app.ui.timeline.theme import C_BORDER, C_PLAYHEAD, C_TEXT, C_TICK_MAJ, C_TICK_MIN\n\n"
        + slice_lines(lines, 68, 234),
        encoding="utf-8",
    )

    (timeline_dir / "clips.py").write_text(
        "from __future__ import annotations\n\n"
        "from pathlib import Path\n"
        "from typing import Callable\n\n"
        "from PySide6.QtCore import Qt, Signal\n"
        "from PySide6.QtGui import (\n"
        "    QColor, QPainter, QPen, QBrush, QFont, QPixmap, QLinearGradient, QCursor,\n"
        ")\n"
        "from PySide6.QtWidgets import QFrame, QLabel, QWidget\n\n"
        "from app.core.timeline import TRACK_AUDIO, TRACK_SUBTITLE, TRACK_VIDEO, TimelineClip\n"
        "from app.ui.timeline.theme import (\n"
        "    C_ACCENT_A, C_ACCENT_S, C_ACCENT_V, C_SELECT, C_TEXT, C_TEXT_BRT, C_TEXT_LT, TRACK_COLORS,\n"
        ")\n\n"
        + slice_lines(lines, 241, 768),
        encoding="utf-8",
    )

    nav_body = slice_lines(lines, 493, 568) + "\n" + slice_lines(lines, 775, 986)
    (timeline_dir / "nav.py").write_text(
        "from __future__ import annotations\n\n"
        "from PySide6.QtCore import Qt, Signal, QTimer\n"
        "from PySide6.QtGui import (\n"
        "    QColor, QPainter, QPen, QBrush, QFont, QWheelEvent, QMouseEvent, QLinearGradient,\n"
        ")\n"
        "from PySide6.QtWidgets import QLabel, QScrollArea, QWidget, QSizePolicy\n\n"
        "from app.ui.timeline.theme import C_BORDER, C_PLAYHEAD, C_TEXT, C_TEXT_LT, TRACK_COLORS, TRACK_LABELS\n\n"
        + nav_body,
        encoding="utf-8",
    )

    panel_header = '''from __future__ import annotations

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

'''
    (timeline_dir / "panel.py").write_text(
        panel_header + slice_lines(lines, 993, 1510),
        encoding="utf-8",
    )

    (timeline_dir / "__init__.py").write_text(
        'from app.ui.timeline.panel import TimelinePanel\n\n__all__ = ["TimelinePanel"]\n',
        encoding="utf-8",
    )

    src_path.write_text(
        '"""Backward-compatible re-export."""\n\n'
        "from app.ui.timeline.panel import TimelinePanel\n\n"
        '__all__ = ["TimelinePanel"]\n',
        encoding="utf-8",
    )


def extract_class_methods(lines: list[str], method_names: set[str]) -> str:
    """Extract methods by name from MainWindow class body (indented with 4 spaces)."""
    chunks: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("    def ") and line[8:].split("(")[0] in method_names:
            start = i
            i += 1
            while i < n:
                nxt = lines[i]
                if nxt.startswith("    def ") or (nxt.startswith("class ") and not nxt.startswith("    ")):
                    break
                i += 1
            chunks.append("".join(lines[start:i]))
        else:
            i += 1
    return "".join(chunks)


def split_main_window() -> None:
    src_path = ROOT / "main_window.py"
    content = src_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # AudioVisualizer block (lines 70-116)
    preview_widgets = (
        "from __future__ import annotations\n\n"
        "import random\n\n"
        "from PySide6.QtGui import QColor, QLinearGradient, QPainter\n"
        "from PySide6.QtWidgets import QWidget\n\n"
        + slice_lines(lines, 70, 116)
        + "\n\nCOLOR_PLAY_TEAL = \"#2DD4BF\"\n"
    )
    (ROOT / "preview_widgets.py").write_text(preview_widgets, encoding="utf-8")

    controls_methods = {
        "_build_controls_panel",
        "_on_sidebar_row_changed",
        "_update_sidebar_icons",
        "_build_video_settings_group",
        "_build_file_group",
        "_subtitle_input_clicked",
        "_build_logo_group",
        "_build_style_group",
        "_on_format_changed",
        "_sync_preview_format",
        "_on_style_control_changed",
        "_apply_style_preset",
        "_build_action_group",
        "_pick_color",
        "_update_color_button",
    }

    preview_methods = {
        "_build_preview_panel",
        "_on_preview_format_changed",
        "_open_preview_settings",
        "_save_preview_screenshot",
        "dragEnterEvent",
        "dropEvent",
        "_refresh_preview",
        "_build_preview_markup",
        "_build_subtitle_info",
        "_format_ms",
        "_change_zoom",
        "_on_timeline_playhead",
        "_playback_max_ms",
        "_seek_playhead",
        "_jump_time",
        "_set_playback_icon",
        "_stop_preview",
        "_change_speed",
        "_toggle_preview_playback",
        "_advance_preview",
    }

    controls_imports = '''from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFontDatabase, QPalette
from PySide6.QtWidgets import (
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
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from app.core.animation_presets import ANIMATION_POP, animation_names
from app.core.style_presets import CUSTOM_PRESET_NAME, default_aspect_ratio_options, get_preset, preset_names
from app.core.subtitle_positions import position_names
from app.core.video_presets import is_vertical_format


class MainWindowControlsMixin:
'''

    preview_imports = '''from __future__ import annotations

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
'''

    controls_body = extract_class_methods(lines, controls_methods)
    preview_body = extract_class_methods(lines, preview_methods)

    (ROOT / "main_window_controls.py").write_text(
        controls_imports + controls_body,
        encoding="utf-8",
    )
    (ROOT / "main_window_preview.py").write_text(
        preview_imports + preview_body,
        encoding="utf-8",
    )

    # Build slim main_window.py: header + constants + MainWindow without extracted methods
    keep_methods = set()
    for i, line in enumerate(lines):
        if line.startswith("    def "):
            name = line[8:].split("(")[0]
            if name not in controls_methods and name not in preview_methods:
                keep_methods.add(name)

    # Lines 1-68 (imports through timeline import), skip AudioVisualizer 70-116
    header = slice_lines(lines, 1, 68)
    # Fix imports in header
    header = header.replace(
        "from app.ui.timeline_panel import TimelinePanel\n",
        "from app.ui.timeline_panel import TimelinePanel\n"
        "from app.ui.main_window_controls import MainWindowControlsMixin\n"
        "from app.ui.main_window_preview import MainWindowPreviewMixin\n",
    )
    # Remove duplicate imports that moved to mixins - keep core imports
    header_lines = header.splitlines(keepends=True)
    # Remove lines 118-148 area (animation_presets etc partially moved) - read original
    # Simpler: take lines 118-163 constants and class start 164-205
    tail_header = slice_lines(lines, 118, 205)
    # Remove unused constants from tail if needed
    tail_header = tail_header.replace(
        "# Onizleme transport kontrolleri — renk ve boyut sabitleri\n"
        "CTRL_BTN_SIZE = 32\n"
        "CTRL_ICON_SIZE = 22\n"
        "COLOR_PLAY_TEAL = \"#2DD4BF\"\n"
        "COLOR_STOP_RED = \"#EF4444\"\n"
        "COLOR_SKIP_ORANGE = \"#F97316\"\n"
        "COLOR_SETTINGS_METAL = \"#A8B4C4\"\n\n\n",
        "",
    )

    class_line = "class MainWindow(QMainWindow, MainWindowControlsMixin, MainWindowPreviewMixin):\n"
    core_body = extract_class_methods(lines, keep_methods)

    # Clean header: remove imports now only in mixins
    skip_imports = {
        "from html import escape",
        "from app.core.animation_presets",
        "from app.core.subtitle_positions",
        "from app.core.style_presets",
        "from app.core.video_presets",
        "from app.core.word_timing import",
        "from app.ui.aspect_ratio_frame",
        "from app.ui.preview_settings_dialog",
    }
    cleaned_header = []
    for ln in header_lines:
        if any(ln.strip().startswith(s) for s in skip_imports):
            continue
        cleaned_header.append(ln)

    main_content = (
        "".join(cleaned_header)
        + tail_header.replace("class MainWindow(QMainWindow):", class_line)
        + core_body
    )

    # Fix class declaration if replace didn't work
    main_content = main_content.replace(
        "class MainWindow(QMainWindow):",
        class_line,
    )

    src_path.write_text(main_content, encoding="utf-8")


if __name__ == "__main__":
    split_timeline()
    split_main_window()
    print("split complete")

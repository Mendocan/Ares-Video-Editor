import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.core.ffmpeg_paths import ensure_ffmpeg_on_path, ffmpeg_version
from app.ui.main_window import MainWindow

APP_STYLE = """
QMainWindow, QWidget {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI', 'Bahnschrift', sans-serif;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #2DD4BF);
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 12px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #14B8A6);
}

QPushButton:disabled {
    background: #334155;
    color: #94A3B8;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #1E293B;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
    color: #F8FAFC;
    selection-background-color: #3B82F6;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2DD4BF;
}

QGroupBox {
    border: 1px solid #2DD4BF;
    border-radius: 6px;
    margin-top: 14px;
    font-weight: bold;
    font-size: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #2DD4BF;
}

QSlider::groove:horizontal {
    border: 1px solid #334155;
    height: 6px;
    background: #1E293B;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #2DD4BF;
    border: none;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:disabled {
    background: #475569;
}
"""

def main() -> int:
    ffmpeg_path = ensure_ffmpeg_on_path()
    if not ffmpeg_path:
        print("UYARI: FFmpeg bulunamadi. Timeline onizleme ve export calismayabilir.")
        print("Cozum: setup_ffmpeg_path.ps1 calistirin veya winget install Gyan.FFmpeg")

    app = QApplication(sys.argv)
    
    # Arayuz fontu — Turkce karakterler icin Segoe UI
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    app.setApplicationName("Ares Editor 2026")
    
    # Michroma yalnizca ARES marka etiketi icin (main_window toolbar)
    font_path = Path(__file__).parent / "assets" / "Michroma-Regular.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))

    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    if ffmpeg_path:
        version = ffmpeg_version()
        if version:
            window.statusBar().showMessage(f"FFmpeg hazir: {version}")
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from app.core.ffmpeg_paths import ensure_ffmpeg_on_path, ffmpeg_version
from app.ui.app_theme import APP_STYLE
from app.ui.main_window import MainWindow

def main() -> int:
    ffmpeg_path = ensure_ffmpeg_on_path()
    if not ffmpeg_path:
        print("UYARI: FFmpeg bulunamadi. Timeline onizleme ve export calismayabilir.")
        print("Cozum: setup_ffmpeg_path.ps1 calistirin veya winget install Gyan.FFmpeg")

    app = QApplication(sys.argv)

    # Fusion stili, ozel QSS'in acilir menu/liste gibi native pencerelerde de
    # tam olarak uygulanmasini saglar (Windows karanlik tema sizintisini onler).
    app.setStyle("Fusion")

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

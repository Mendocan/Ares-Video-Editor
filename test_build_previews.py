import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from app.ui.main_window import MainWindow
import traceback

win = MainWindow()
video_path = r"C:\Users\Diş Hekimliği\Desktop\Denemeler\Korku 1.mp4"
win._import_video_to_timeline(video_path)

try:
    print("Building media previews...")
    thumbs, waves = win._build_media_previews()
    print("Success!")
    print("Thumbs:", thumbs)
    print("Waves:", waves)
except Exception as e:
    print("Exception:")
    traceback.print_exc()

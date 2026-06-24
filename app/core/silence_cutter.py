from __future__ import annotations

import re
import subprocess
from pathlib import Path

class SilenceCutter:
    def __init__(self, db_threshold: int = -35, min_duration: float = 0.5):
        """
        db_threshold: Hangi ses seviyesinin alti sessizlik kabul edilecek (-35dB genelde iyidir).
        min_duration: En az kac saniyelik sessizlikler kesilsin (0.5 saniye).
        """
        self.db_threshold = db_threshold
        self.min_duration = min_duration

    def _detect_silences(self, video_path: str) -> list[tuple[float, float]]:
        """
        FFmpeg silencedetect kullanarak sessizlik anlarinin (baslangic, bitis) saniyelerini doner.
        """
        cmd = [
            "ffmpeg", "-i", video_path,
            "-af", f"silencedetect=noise={self.db_threshold}dB:d={self.min_duration}",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = result.stderr

        silences = []
        start_time = None

        for line in output.split("\n"):
            if "silence_start" in line:
                match = re.search(r"silence_start:\s*([0-9.]+)", line)
                if match:
                    start_time = float(match.group(1))
            elif "silence_end" in line and start_time is not None:
                match = re.search(r"silence_end:\s*([0-9.]+)", line)
                if match:
                    end_time = float(match.group(1))
                    silences.append((start_time, end_time))
                    start_time = None

        return silences

    def _get_video_duration(self, video_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return float(result.stdout.strip())

    def auto_cut(self, video_path: str, output_path: str) -> Path:
        """
        Videodaki sessizlikleri analiz eder, sadece sesli (konusma olan) bolumleri
        kesip birlestirerek yeni bir video olusturur.
        """
        silences = self._detect_silences(video_path)
        duration = self._get_video_duration(video_path)

        if not silences:
            # Sessizlik yoksa oldugu gibi kopyala
            subprocess.run(["ffmpeg", "-y", "-i", video_path, "-c", "copy", output_path], check=True)
            return Path(output_path)

        # Sessizlikleri cikararak "konusma" bloklarini (sesli kisimlari) hesapla
        keep_segments = []
        last_end = 0.0

        for s_start, s_end in silences:
            if s_start > last_end:
                keep_segments.append((last_end, s_start))
            last_end = s_end

        if last_end < duration:
            keep_segments.append((last_end, duration))

        # Gecici liste dosyasi (concat icin) ve kesilmis parcalar olustur
        temp_dir = Path(output_path).parent / "temp_segments"
        temp_dir.mkdir(exist_ok=True)
        list_file = temp_dir / "concat_list.txt"
        
        try:
            with list_file.open("w", encoding="utf-8") as f:
                for i, (start, end) in enumerate(keep_segments):
                    seg_out = temp_dir / f"seg_{i:03d}.mp4"
                    cmd = [
                        "ffmpeg", "-y", "-i", video_path,
                        "-ss", str(start), "-to", str(end),
                        "-c", "copy", str(seg_out)
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)
                    f.write(f"file '{seg_out.as_posix()}'\n")

            # Birlestir
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file), "-c", "copy", output_path
            ]
            subprocess.run(concat_cmd, capture_output=True, check=True)
            
        finally:
            # Gecici dosyalari temizle
            if list_file.exists():
                list_file.unlink()
            for file in temp_dir.glob("seg_*.mp4"):
                file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()

        return Path(output_path)

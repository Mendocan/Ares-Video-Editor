from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.ffmpeg_paths import ensure_ffmpeg_on_path
from app.core.media_probe import probe_duration_ms


class WaveformService:
    """FFmpeg showwavespic ile ses dalga formu gorseli uretir."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path.cwd() / "output" / ".waveforms"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(
        self,
        media_path: str,
        source_start_ms: int,
        source_end_ms: int,
        width: int,
        height: int,
    ) -> Path:
        stem = Path(media_path).stem
        return self.cache_dir / f"{stem}_{source_start_ms}_{source_end_ms}_{width}x{height}.png"

    def generate_waveform(
        self,
        media_path: str,
        source_start_ms: int = 0,
        source_end_ms: int | None = None,
        width: int = 640,
        height: int = 36,
    ) -> Path | None:
        path = Path(media_path)
        if not path.exists():
            return None

        if source_end_ms is None or source_end_ms <= source_start_ms:
            source_end_ms = source_start_ms + self._probe_duration_ms(media_path)

        duration_ms = max(1, source_end_ms - source_start_ms)
        out = self._cache_path(media_path, source_start_ms, source_end_ms, width, height)
        if out.exists():
            return out

        start_sec = source_start_ms / 1000.0
        duration_sec = max(0.05, duration_ms / 1000.0)
        width = max(120, min(2400, width))
        ffmpeg = ensure_ffmpeg_on_path()
        if not ffmpeg:
            return None

        cmd = [
            ffmpeg, "-y",
            "-ss", str(start_sec),
            "-i", str(path),
            "-t", str(duration_sec),
            "-filter_complex",
            f"showwavespic=s={width}x{height}:colors=#10B981|#059669",
            "-frames:v", "1",
            str(out),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0 and out.exists():
            return out
        return None

    @staticmethod
    def _probe_duration_ms(media_path: str) -> int:
        return probe_duration_ms(media_path) or 10_000

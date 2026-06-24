from __future__ import annotations

from dataclasses import dataclass
import subprocess
from pathlib import Path

from app.core.ffmpeg_paths import ffmpeg_missing_message, resolve_ffprobe


@dataclass(slots=True)
class ProbeResult:
    duration_ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.duration_ms > 0 and self.error is None


def probe_media(media_path: str) -> ProbeResult:
    path = Path(media_path)
    if not path.exists():
        return ProbeResult(0, error=f"Dosya bulunamadi: {media_path}")

    ffprobe = resolve_ffprobe()
    if not ffprobe:
        return ProbeResult(0, error=ffmpeg_missing_message())

    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return ProbeResult(
            0,
            error=detail or f"ffprobe dosyayi okuyamadi (kod {result.returncode})",
        )

    try:
        duration_ms = max(0, int(float(result.stdout.strip()) * 1000))
    except ValueError:
        return ProbeResult(0, error="Video suresi okunamadi (ffprobe ciktisi gecersiz).")

    if duration_ms <= 0:
        return ProbeResult(0, error="Video suresi sifir veya okunamadi.")
    return ProbeResult(duration_ms)


def probe_duration_ms(media_path: str) -> int:
    return probe_media(media_path).duration_ms

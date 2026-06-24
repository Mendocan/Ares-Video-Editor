from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.ffmpeg_paths import ensure_ffmpeg_on_path
from app.core.media_probe import probe_duration_ms


class ThumbnailService:
    """FFmpeg ile timeline filmstrip (kare seridi) uretir."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path.cwd() / "output" / ".thumbnails"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_folder(
        self,
        video_path: str,
        source_start_ms: int,
        source_end_ms: int,
        count: int,
    ) -> Path:
        stem = Path(video_path).stem
        return self.cache_dir / f"{stem}_{source_start_ms}_{source_end_ms}_{count}"

    def _resolve_duration_ms(
        self,
        video_path: str,
        source_start_ms: int,
        source_end_ms: int | None,
    ) -> tuple[int, int]:
        if source_end_ms and source_end_ms > source_start_ms:
            duration_ms = source_end_ms - source_start_ms
        else:
            duration_ms = probe_duration_ms(video_path) or 3_000
            source_end_ms = source_start_ms + duration_ms
        return max(duration_ms, 200), source_end_ms

    def _frame_count(self, duration_ms: int, count: int | None) -> int:
        if count is not None:
            return max(2, min(48, count))
        return max(4, min(32, duration_ms // 200))

    def generate_strip(
        self,
        video_path: str,
        source_start_ms: int = 0,
        source_end_ms: int | None = None,
        count: int | None = None,
        height: int = 52,
    ) -> list[Path]:
        path = Path(video_path)
        if not path.exists():
            return []

        duration_ms, source_end_ms = self._resolve_duration_ms(
            video_path, source_start_ms, source_end_ms
        )
        frame_count = self._frame_count(duration_ms, count)
        cache_folder = self._cache_folder(video_path, source_start_ms, source_end_ms, frame_count)
        mosaic = cache_folder / "filmstrip.jpg"
        if mosaic.exists():
            return [mosaic]

        cached = sorted(cache_folder.glob("thumb_*.jpg"))
        if cached:
            return cached

        cache_folder.mkdir(parents=True, exist_ok=True)
        ffmpeg = ensure_ffmpeg_on_path()
        if not ffmpeg:
            return []

        if self._generate_mosaic(
            ffmpeg=ffmpeg,
            path=path,
            source_start_ms=source_start_ms,
            duration_ms=duration_ms,
            frame_count=frame_count,
            height=height,
            mosaic=mosaic,
        ):
            return [mosaic]

        return self._generate_frames(
            ffmpeg=ffmpeg,
            path=path,
            source_start_ms=source_start_ms,
            duration_ms=duration_ms,
            frame_count=frame_count,
            height=height,
            cache_folder=cache_folder,
        )

    def _generate_mosaic(
        self,
        ffmpeg: str,
        path: Path,
        source_start_ms: int,
        duration_ms: int,
        frame_count: int,
        height: int,
        mosaic: Path,
    ) -> bool:
        duration_sec = max(0.2, duration_ms / 1000.0)
        fps = max(0.5, frame_count / duration_sec)
        vf = f"fps={fps:.3f},scale=-2:{height},tile={frame_count}x1"
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{source_start_ms / 1000.0:.3f}",
            "-i",
            str(path.resolve()),
            "-t",
            f"{duration_sec:.3f}",
            "-vf",
            vf,
            "-frames:v",
            "1",
            str(mosaic),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0 and mosaic.exists()

    def _generate_frames(
        self,
        ffmpeg: str,
        path: Path,
        source_start_ms: int,
        duration_ms: int,
        frame_count: int,
        height: int,
        cache_folder: Path,
    ) -> list[Path]:
        interval_sec = max(0.05, (duration_ms / 1000.0) / max(frame_count, 1))
        start_sec = source_start_ms / 1000.0
        frames: list[Path] = []
        for i in range(frame_count):
            offset = start_sec + (i * interval_sec)
            out = cache_folder / f"thumb_{i:03d}.jpg"
            cmd = [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{offset:.3f}",
                "-i",
                str(path.resolve()),
                "-vframes",
                "1",
                "-vf",
                f"scale=-2:{height}",
                "-q:v",
                "3",
                str(out),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and out.exists():
                frames.append(out)
        return frames

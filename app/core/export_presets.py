from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


EXPORT_FORMATS = ["MP4", "MOV", "MKV", "WebM", "AVI"]

FORMAT_EXTENSIONS = {
    "MP4": ".mp4",
    "MOV": ".mov",
    "MKV": ".mkv",
    "WebM": ".webm",
    "AVI": ".avi",
}

QUALITY_DRAFT = "Taslak"
QUALITY_GOOD = "Iyi"
QUALITY_HIGH = "Yuksek"

QUALITY_OPTIONS = [QUALITY_DRAFT, QUALITY_GOOD, QUALITY_HIGH]

RESOLUTION_PRESETS = [
    "Kaynak (Orijinal)",
    "TikTok / Reels (1080x1920)",
    "YouTube Shorts (1080x1920)",
    "YouTube HD (1920x1080)",
    "HD (1280x720)",
    "Instagram 4:5 (1080x1350)",
    "Instagram Kare (1080x1080)",
    "Dikey (9:16)",
    "Yatay (16:9)",
]

FPS_OPTIONS = ["Orijinal", "24", "25", "29.97", "30", "60"]


@dataclass(slots=True)
class ExportQualityProfile:
    name: str
    video_preset: str
    crf: int
    audio_bitrate: str
    description: str


QUALITY_PROFILES: dict[str, ExportQualityProfile] = {
    QUALITY_DRAFT: ExportQualityProfile(
        name=QUALITY_DRAFT,
        video_preset="ultrafast",
        crf=28,
        audio_bitrate="128k",
        description="Hizli aktarim, dusuk dosya boyutu.",
    ),
    QUALITY_GOOD: ExportQualityProfile(
        name=QUALITY_GOOD,
        video_preset="fast",
        crf=23,
        audio_bitrate="192k",
        description="Dengeli sure, boyut ve kalite.",
    ),
    QUALITY_HIGH: ExportQualityProfile(
        name=QUALITY_HIGH,
        video_preset="slow",
        crf=18,
        audio_bitrate="256k",
        description="En yuksek kalite, daha uzun sure.",
    ),
}


def unique_output_path(folder: Path, base_name: str, extension: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    clean = base_name.strip() or "cikti"
    ext = extension if extension.startswith(".") else f".{extension}"
    candidate = folder / f"{clean}{ext}"
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        numbered = folder / f"{clean}_{index}{ext}"
        if not numbered.exists():
            return numbered
        index += 1


def estimate_size_mb(duration_sec: float, quality: str) -> tuple[int, int]:
    profiles = QUALITY_PROFILES.get(quality, QUALITY_PROFILES[QUALITY_GOOD])
    base_kbps = {QUALITY_DRAFT: 2500, QUALITY_GOOD: 5000, QUALITY_HIGH: 9000}.get(quality, 5000)
    audio_kbps = int(profiles.audio_bitrate.replace("k", ""))
    total_kbps = base_kbps + audio_kbps
    size_mb = (total_kbps * duration_sec) / 8 / 1024
    low = max(1, int(size_mb * 0.75))
    high = max(low + 1, int(size_mb * 1.35))
    return low, high

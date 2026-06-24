from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FormatMode(str, Enum):
    NONE = "none"
    CROP = "crop"
    FIT = "fit"


@dataclass(frozen=True, slots=True)
class VideoFormat:
    name: str
    mode: FormatMode
    width: int = 0
    height: int = 0
    crop_w_ratio: int = 0
    crop_h_ratio: int = 0
    description: str = ""


VIDEO_FORMATS: dict[str, VideoFormat] = {
    "Orijinal": VideoFormat(
        name="Orijinal",
        mode=FormatMode.NONE,
        description="Kaynak cozunurluk korunur",
    ),
    "Dikey (9:16)": VideoFormat(
        name="Dikey (9:16)",
        mode=FormatMode.CROP,
        crop_w_ratio=9,
        crop_h_ratio=16,
        description="Ortadan kirp — hizli dikey crop",
    ),
    "Yatay (16:9)": VideoFormat(
        name="Yatay (16:9)",
        mode=FormatMode.CROP,
        crop_w_ratio=16,
        crop_h_ratio=9,
        description="Ortadan kirp — yatay crop",
    ),
    "TikTok / Reels (1080x1920)": VideoFormat(
        name="TikTok / Reels (1080x1920)",
        mode=FormatMode.FIT,
        width=1080,
        height=1920,
        description="9:16, siyah bantli tam boyut",
    ),
    "YouTube Shorts (1080x1920)": VideoFormat(
        name="YouTube Shorts (1080x1920)",
        mode=FormatMode.FIT,
        width=1080,
        height=1920,
        description="Shorts icin 1080x1920",
    ),
    "Instagram 4:5 (1080x1350)": VideoFormat(
        name="Instagram 4:5 (1080x1350)",
        mode=FormatMode.FIT,
        width=1080,
        height=1350,
        description="Feed dikey 4:5",
    ),
    "Instagram Kare (1080x1080)": VideoFormat(
        name="Instagram Kare (1080x1080)",
        mode=FormatMode.FIT,
        width=1080,
        height=1080,
        description="Kare 1:1 format",
    ),
    "Kaynak (Orijinal)": VideoFormat(
        name="Kaynak (Orijinal)",
        mode=FormatMode.NONE,
        description="Kaynak cozunurluk",
    ),
    "YouTube HD (1920x1080)": VideoFormat(
        name="YouTube HD (1920x1080)",
        mode=FormatMode.FIT,
        width=1920,
        height=1080,
        description="Full HD yatay",
    ),
    "HD (1280x720)": VideoFormat(
        name="HD (1280x720)",
        mode=FormatMode.FIT,
        width=1280,
        height=720,
        description="HD 720p",
    ),
}


def format_names() -> list[str]:
    return list(VIDEO_FORMATS.keys())


def get_format(name: str) -> VideoFormat | None:
    return VIDEO_FORMATS.get(name)


def is_vertical_format(name: str) -> bool:
    fmt = get_format(name)
    if fmt is None:
        return False
    if fmt.mode == FormatMode.CROP:
        return fmt.crop_h_ratio > fmt.crop_w_ratio
    if fmt.mode == FormatMode.FIT:
        return fmt.height > fmt.width
    return False


def play_resolution(name: str) -> tuple[int, int]:
    fmt = get_format(name)
    if fmt is None or fmt.mode == FormatMode.NONE:
        return 1920, 1080
    if fmt.mode == FormatMode.FIT:
        return fmt.width, fmt.height
    if fmt.mode == FormatMode.CROP and fmt.crop_h_ratio > fmt.crop_w_ratio:
        return 1080, 1920
    return 1920, 1080


def build_ffmpeg_video_filter(name: str) -> str | None:
    """ASS sonrasi uygulanacak FFmpeg video filtresi."""
    fmt = get_format(name)
    if fmt is None or fmt.mode == FormatMode.NONE:
        return None

    if fmt.mode == FormatMode.CROP:
        if fmt.crop_w_ratio == 9 and fmt.crop_h_ratio == 16:
            return "crop=ih*9/16:ih"
        if fmt.crop_w_ratio == 16 and fmt.crop_h_ratio == 9:
            return "crop=iw:iw*9/16"
        return None

    w, h = fmt.width, fmt.height
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
    )

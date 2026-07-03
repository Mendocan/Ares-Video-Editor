from __future__ import annotations

import os
from pathlib import Path

REFERENCE_PLAY_Y = 1080


def scale_style_for_play_res(
    font_size: int,
    stroke_size: int,
    shadow_size: int,
    play_y: int,
    *,
    reference_play_y: int = REFERENCE_PLAY_Y,
) -> tuple[int, int, int]:
    """UI'daki stil degerleri 1080p referansina goredir; ASS PlayResY'ye olceklenir."""
    scale = max(play_y, 1) / max(reference_play_y, 1)
    return (
        max(8, round(font_size * scale)),
        max(0, round(stroke_size * scale)),
        max(0, round(shadow_size * scale)),
    )


def export_style_from_preview(
    font_size: int,
    stroke_size: int,
    shadow_size: int,
    play_y: int,
    preview_height: int,
) -> tuple[int, int, int]:
    """Onizlemede gorulen stil degerlerini ASS PlayResY'ye cevirir."""
    if preview_height <= 0:
        return scale_style_for_play_res(font_size, stroke_size, shadow_size, play_y)
    scale = play_y / preview_height
    return (
        max(8, round(font_size * scale)),
        max(0, round(stroke_size * scale)),
        max(0, round(shadow_size * scale)),
    )


LOGO_OVERLAY_POSITIONS = {
    "Sol Üst": "10:10",
    "Sağ Üst": "W-w-10:10",
    "Sol Alt": "10:H-h-10",
    "Sağ Alt": "W-w-10:H-h-10",
    "Sol Ust": "10:10",
    "Sag Ust": "W-w-10:10",
}


def resolve_ffmpeg_fonts_dir() -> Path:
    assets = Path(__file__).resolve().parents[1] / "assets"
    if assets.exists() and any(assets.glob("*.ttf")):
        return assets
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return Path(windir) / "Fonts"


def ass_filter_value(ass_path: Path, fonts_dir: Path | None = None, cwd: Path | None = None) -> str:
    fonts_path = (fonts_dir or resolve_ffmpeg_fonts_dir()).resolve()
    if cwd is not None:
        try:
            fonts = Path(fonts_path).relative_to(Path(cwd).resolve()).as_posix()
        except ValueError:
            fonts = _ffmpeg_escape_path(fonts_path)
    else:
        fonts = _ffmpeg_escape_path(fonts_path)
    name = ass_path.name.replace("'", r"\'")
    return f"ass=filename='{name}':fontsdir='{fonts}'"


def _ffmpeg_escape_path(path: Path) -> str:
    posix = path.resolve().as_posix()
    if len(posix) > 1 and posix[1] == ":":
        return posix[0] + r"\:" + posix[2:]
    return posix

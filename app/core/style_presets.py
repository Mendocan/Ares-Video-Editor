from __future__ import annotations

from dataclasses import dataclass

from app.core.animation_presets import ANIMATION_GLOW, ANIMATION_NONE, ANIMATION_POP
from app.core.video_presets import format_names as video_format_names


@dataclass(frozen=True, slots=True)
class StylePreset:
    name: str
    description: str
    font_name: str
    font_size: int
    normal_color: str
    active_color: str
    stroke_size: int
    shadow_size: int
    position: str
    animation_style: str
    bg_box: bool
    aspect_ratio: str
    fps: str


CUSTOM_PRESET_NAME = "Özel"


STYLE_PRESETS: dict[str, StylePreset] = {
    "TikTok / Reels": StylePreset(
        name="TikTok / Reels",
        description="Dikey 9:16, buyuk yazi, pop-up animasyon",
        font_name="Arial",
        font_size=36,
        normal_color="#FFFFFF",
        active_color="#3B82F6",
        stroke_size=4,
        shadow_size=6,
        position="Alt Orta",
        animation_style=ANIMATION_POP,
        bg_box=False,
        aspect_ratio="TikTok / Reels (1080x1920)",
        fps="30",
    ),
    "YouTube Shorts": StylePreset(
        name="YouTube Shorts",
        description="Dikey format, sari vurgu, kalin kontur",
        font_name="Segoe UI",
        font_size=36,
        normal_color="#FFFFFF",
        active_color="#FACC15",
        stroke_size=5,
        shadow_size=5,
        position="Alt Orta",
        animation_style=ANIMATION_POP,
        bg_box=True,
        aspect_ratio="YouTube Shorts (1080x1920)",
        fps="30",
    ),
    "YouTube Yatay": StylePreset(
        name="YouTube Yatay",
        description="16:9 yatay video, okunakli altyazi",
        font_name="Segoe UI",
        font_size=30,
        normal_color="#FFFFFF",
        active_color="#EF4444",
        stroke_size=3,
        shadow_size=4,
        position="Alt Orta",
        animation_style=ANIMATION_POP,
        bg_box=False,
        aspect_ratio="Yatay (16:9)",
        fps="30",
    ),
    "Minimal": StylePreset(
        name="Minimal",
        description="Sade beyaz metin, animasyon yok",
        font_name="Roboto",
        font_size=26,
        normal_color="#F8FAFC",
        active_color="#E2E8F0",
        stroke_size=2,
        shadow_size=2,
        position="Alt Orta",
        animation_style=ANIMATION_NONE,
        bg_box=False,
        aspect_ratio="Orijinal",
        fps="Orijinal",
    ),
    "Karaoke Bold": StylePreset(
        name="Karaoke Bold",
        description="Buyuk font, siyah kutu, turkuaz vurgu",
        font_name="Arial",
        font_size=42,
        normal_color="#FFFFFF",
        active_color="#2DD4BF",
        stroke_size=4,
        shadow_size=0,
        position="Alt Orta",
        animation_style=ANIMATION_GLOW,
        bg_box=True,
        aspect_ratio="TikTok / Reels (1080x1920)",
        fps="30",
    ),
}


def default_aspect_ratio_options() -> list[str]:
    return video_format_names()


def preset_names() -> list[str]:
    return [CUSTOM_PRESET_NAME, *STYLE_PRESETS.keys()]


def get_preset(name: str) -> StylePreset | None:
    return STYLE_PRESETS.get(name)

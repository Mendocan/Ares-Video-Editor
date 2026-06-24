from __future__ import annotations

ANIMATION_NONE = "Yok"
ANIMATION_POP = "Pop-up"
ANIMATION_FADE = "Fade"
ANIMATION_BOUNCE = "Bounce"
ANIMATION_GLOW = "Parlak Vurgu"


def animation_names() -> list[str]:
    return [ANIMATION_NONE, ANIMATION_POP, ANIMATION_FADE, ANIMATION_BOUNCE, ANIMATION_GLOW]


def build_active_word_tags(style: str, active_ass_color: str) -> str:
    """Aktif kelime icin ASS override etiketleri."""
    if style == ANIMATION_NONE:
        return rf"{{\1c{active_ass_color}\b1}}"

    if style == ANIMATION_FADE:
        return rf"{{\1c{active_ass_color}\b1\alpha&HFF&\t(0,120,\alpha&H00&)}}"

    if style == ANIMATION_BOUNCE:
        return (
            rf"{{\1c{active_ass_color}\b1\fscx125\fscy125"
            rf"\t(0,70,\fscx95\fscy95)\t(70,140,\fscx100\fscy100)}}"
        )

    if style == ANIMATION_GLOW:
        return rf"{{\1c{active_ass_color}\b1\blur2\fscx115\fscy115\t(0,80,\fscx100\fscy100)}}"

    # Pop-up (varsayilan)
    return rf"{{\1c{active_ass_color}\b1\fscx130\fscy130\t(0,100,\fscx100\fscy100)}}"


def animation_from_legacy(use_animation: bool, animation_style: str | None = None) -> str:
    if animation_style and animation_style in animation_names():
        return animation_style
    return ANIMATION_POP if use_animation else ANIMATION_NONE

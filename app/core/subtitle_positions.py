from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubtitlePosition:
    name: str
    ass_alignment: int
    margin_ratio: float


POSITIONS: dict[str, SubtitlePosition] = {
    "Ust Orta": SubtitlePosition("Ust Orta", 8, 0.10),
    "Orta": SubtitlePosition("Orta", 5, 0.0),
    "Alt Orta": SubtitlePosition("Alt Orta", 2, 0.10),
}


def position_names() -> list[str]:
    return list(POSITIONS.keys())


def get_position(name: str) -> SubtitlePosition:
    return POSITIONS.get(name, POSITIONS["Alt Orta"])


def ass_style_values(position_name: str, play_res_y: int) -> tuple[int, int]:
    """ASS Style satiri icin (alignment, margin_v) dondurur."""
    pos = get_position(position_name)
    margin_v = max(30, int(play_res_y * pos.margin_ratio)) if pos.margin_ratio > 0 else 20
    return pos.ass_alignment, margin_v


def qt_preview_alignment(position_name: str):
    from PySide6.QtCore import Qt

    mapping = {
        "Ust Orta": Qt.AlignHCenter | Qt.AlignTop,
        "Orta": Qt.AlignCenter,
        "Alt Orta": Qt.AlignHCenter | Qt.AlignBottom,
    }
    return mapping.get(position_name, Qt.AlignHCenter | Qt.AlignBottom)


def preview_padding(position_name: str, shadow: int) -> str:
    edge = 24 + shadow
    if position_name == "Ust Orta":
        return f"padding: {edge}px 8px 12px 8px;"
    if position_name == "Orta":
        return "padding: 12px 8px;"
    return f"padding: 12px 8px {edge}px 8px;"

from __future__ import annotations

from dataclasses import dataclass

# FFmpeg'in yerlesik `xfade` filtresindeki gecis efektleri (ek bagimlilik gerektirmez).
# Anahtar: arayuzde gosterilen Turkce isim, deger: ffmpeg xfade transition adi.
TRANSITION_NONE = "Yok"
XFADE_TRANSITIONS: dict[str, str] = {
    TRANSITION_NONE: "",
    "Capraz Gecis (Fade)": "fade",
    "Siyaha Sonme": "fadeblack",
    "Beyaza Sonme": "fadewhite",
    "Erime (Dissolve)": "dissolve",
    "Sola Kaydir": "slideleft",
    "Saga Kaydir": "slideright",
    "Yukari Kaydir": "slideup",
    "Asagi Kaydir": "slidedown",
    "Sola Sil (Wipe)": "wipeleft",
    "Saga Sil (Wipe)": "wiperight",
    "Daire Ac": "circleopen",
    "Daire Kapat": "circleclose",
    "Dikey Ac": "vertopen",
    "Yatay Ac": "horzopen",
    "Yakinlastir (Zoom)": "zoomin",
    "Piksellestir": "pixelize",
    "Bulanik Gecis": "hblur",
}


@dataclass(slots=True)
class ClipEffects:
    speed: float = 1.0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    volume: float = 1.0
    transition_in: str = TRANSITION_NONE
    transition_duration_ms: int = 500

    def has_video_filters(self) -> bool:
        return self.speed != 1.0 or self.fade_in_ms > 0 or self.fade_out_ms > 0

    def has_audio_filters(self) -> bool:
        return self.speed != 1.0 or abs(self.volume - 1.0) > 0.01 or self.fade_in_ms > 0 or self.fade_out_ms > 0

    def has_transition(self) -> bool:
        return self.transition_in != TRANSITION_NONE and XFADE_TRANSITIONS.get(self.transition_in, "") != ""

    def xfade_name(self) -> str:
        return XFADE_TRANSITIONS.get(self.transition_in, "fade")


def build_atempo_chain(speed: float) -> str:
    """atempo 0.5-2.0 araliginda; dis degerler icin zincirle."""
    if speed <= 0:
        return "atempo=1.0"
    filters: list[str] = []
    remaining = speed
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    return ",".join(filters)


def build_segment_filter(duration_sec: float, effects: ClipEffects) -> tuple[str | None, str | None]:
    """FFmpeg -vf ve -af filtre dizelerini dondurur."""
    vf: list[str] = []
    af: list[str] = []

    if effects.speed != 1.0:
        vf.append(f"setpts=PTS/{effects.speed:.4f}")
        af.append(build_atempo_chain(effects.speed))

    if effects.fade_in_ms > 0:
        fade_in_sec = effects.fade_in_ms / 1000.0
        vf.append(f"fade=t=in:st=0:d={fade_in_sec:.3f}")
        af.append(f"afade=t=in:st=0:d={fade_in_sec:.3f}")

    if effects.fade_out_ms > 0 and duration_sec > 0:
        fade_out_sec = effects.fade_out_ms / 1000.0
        start = max(0.0, duration_sec - fade_out_sec)
        vf.append(f"fade=t=out:st={start:.3f}:d={fade_out_sec:.3f}")
        af.append(f"afade=t=out:st={start:.3f}:d={fade_out_sec:.3f}")

    if abs(effects.volume - 1.0) > 0.01:
        af.append(f"volume={effects.volume:.2f}")

    vf_str = ",".join(vf) if vf else None
    af_str = ",".join(af) if af else None
    return vf_str, af_str

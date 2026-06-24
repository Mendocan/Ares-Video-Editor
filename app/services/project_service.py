from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.clip_effects import ClipEffects
from app.core.timeline import EDIT_MODE_RIPPLE, TimelineClip, TimelineModel
from app.core.word_timing_data import WordTimingDocument


PROJECT_VERSION = 1
PROJECT_EXTENSION = ".aresproj"


@dataclass
class ProjectStyle:
    font_name: str = "Arial"
    font_size: int = 32
    normal_color: str = "#FFFFFF"
    active_color: str = "#3B82F6"
    stroke_size: int = 3
    shadow_size: int = 4
    position: str = "Alt Orta"
    use_animation: bool = True
    animation_style: str = "Pop-up"
    bg_box: bool = False
    logo_path: str = ""
    logo_pos: str = "Sag Ust"
    logo_size: int = 150
    aspect_ratio: str = "Orijinal"
    fps: str = "Orijinal"
    audio_bitrate: str = "192k"
    denoise_audio: bool = False
    use_gpu: bool = True
    translate: bool = False
    preset_name: str = "Özel"


@dataclass
class ProjectData:
    version: int
    project_name: str
    video_path: str
    subtitle_path: str
    timeline: dict
    subtitle_entries: list[dict]
    word_timing: dict | None
    style: dict
    playback: dict


class ProjectService:
    def save(
        self,
        file_path: str,
        *,
        video_path: str,
        subtitle_path: str,
        timeline_model: TimelineModel,
        subtitle_entries: list,
        word_document: WordTimingDocument | None,
        style: ProjectStyle,
        current_time_ms: int,
        zoom_level: float,
        playback_speed: str,
    ) -> Path:
        output = Path(file_path)
        if output.suffix.lower() != PROJECT_EXTENSION:
            output = output.with_suffix(PROJECT_EXTENSION)

        payload = {
            "version": PROJECT_VERSION,
            "project_name": output.stem,
            "video_path": video_path,
            "subtitle_path": subtitle_path,
            "timeline": self._serialize_timeline(timeline_model),
            "subtitle_entries": [self._serialize_subtitle_entry(entry) for entry in subtitle_entries],
            "word_timing": word_document.to_dict() if word_document else None,
            "style": asdict(style),
            "playback": {
                "current_time_ms": current_time_ms,
                "zoom_level": zoom_level,
                "speed": playback_speed,
            },
        }

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def load(self, file_path: str) -> ProjectData:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Proje dosyasi bulunamadi: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        version = int(data.get("version", 1))
        if version > PROJECT_VERSION:
            raise ValueError(f"Desteklenmeyen proje surumu: {version}")

        return ProjectData(
            version=version,
            project_name=str(data.get("project_name", path.stem)),
            video_path=str(data.get("video_path", "")),
            subtitle_path=str(data.get("subtitle_path", "")),
            timeline=dict(data.get("timeline", {})),
            subtitle_entries=list(data.get("subtitle_entries", [])),
            word_timing=data.get("word_timing"),
            style=dict(data.get("style", {})),
            playback=dict(data.get("playback", {})),
        )

    def apply_timeline(self, timeline_model: TimelineModel, timeline_data: dict) -> None:
        timeline_model.clips.clear()
        timeline_model.duration_ms = int(timeline_data.get("duration_ms", 0))
        timeline_model.edit_mode = timeline_data.get("edit_mode", EDIT_MODE_RIPPLE)

        for item in timeline_data.get("clips", []):
            effects_data = item.get("effects", {})
            effects = ClipEffects(
                speed=float(effects_data.get("speed", 1.0)),
                fade_in_ms=int(effects_data.get("fade_in_ms", 0)),
                fade_out_ms=int(effects_data.get("fade_out_ms", 0)),
                volume=float(effects_data.get("volume", 1.0)),
            )
            timeline_model.clips.append(
                TimelineClip(
                    clip_id=str(item["clip_id"]),
                    track=str(item["track"]),
                    label=str(item.get("label", "")),
                    timeline_start_ms=int(item["timeline_start_ms"]),
                    timeline_end_ms=int(item["timeline_end_ms"]),
                    source_path=item.get("source_path"),
                    source_start_ms=int(item.get("source_start_ms", 0)),
                    source_end_ms=item.get("source_end_ms"),
                    selected=bool(item.get("selected", False)),
                    linked_clip_id=item.get("linked_clip_id"),
                    effects=effects,
                )
            )

        if timeline_model.duration_ms <= 0 and timeline_model.clips:
            timeline_model._recalc_duration()

    def _serialize_timeline(self, model: TimelineModel) -> dict:
        return {
            "duration_ms": model.duration_ms,
            "edit_mode": model.edit_mode,
            "clips": [
                {
                    "clip_id": clip.clip_id,
                    "track": clip.track,
                    "label": clip.label,
                    "timeline_start_ms": clip.timeline_start_ms,
                    "timeline_end_ms": clip.timeline_end_ms,
                    "source_path": clip.source_path,
                    "source_start_ms": clip.source_start_ms,
                    "source_end_ms": clip.source_end_ms,
                    "selected": clip.selected,
                    "linked_clip_id": clip.linked_clip_id,
                    "effects": {
                        "speed": clip.effects.speed if clip.effects else 1.0,
                        "fade_in_ms": clip.effects.fade_in_ms if clip.effects else 0,
                        "fade_out_ms": clip.effects.fade_out_ms if clip.effects else 0,
                        "volume": clip.effects.volume if clip.effects else 1.0,
                    },
                }
                for clip in model.clips
            ],
        }

    def _serialize_subtitle_entry(self, entry) -> dict:
        return {
            "index": entry.index,
            "start": entry.start,
            "end": entry.end,
            "text": entry.text,
            "start_ms": entry.start_ms,
            "end_ms": entry.end_ms,
        }

    def deserialize_subtitle_entries(self, items: list[dict]):
        from app.core.subtitle_parser import SubtitleEntry

        return [
            SubtitleEntry(
                index=int(item["index"]),
                start=str(item["start"]),
                end=str(item["end"]),
                text=str(item["text"]),
                start_ms=int(item["start_ms"]),
                end_ms=int(item["end_ms"]),
            )
            for item in items
        ]

    def deserialize_word_document(self, data: dict | None) -> WordTimingDocument | None:
        if not data:
            return None
        return WordTimingDocument.from_dict(data)

    def deserialize_style(self, data: dict) -> ProjectStyle:
        return ProjectStyle(
            font_name=str(data.get("font_name", "Arial")),
            font_size=int(data.get("font_size", 42)),
            normal_color=str(data.get("normal_color", "#FFFFFF")),
            active_color=str(data.get("active_color", "#3B82F6")),
            stroke_size=int(data.get("stroke_size", 3)),
            shadow_size=int(data.get("shadow_size", 4)),
            position=str(data.get("position", "Alt Orta")),
            use_animation=bool(data.get("use_animation", True)),
            animation_style=str(
                data.get(
                    "animation_style",
                    "Pop-up" if data.get("use_animation", True) else "Yok",
                )
            ),
            bg_box=bool(data.get("bg_box", False)),
            logo_path=str(data.get("logo_path", "")),
            logo_pos=str(data.get("logo_pos", "Sag Ust")),
            logo_size=int(data.get("logo_size", 150)),
            aspect_ratio=str(data.get("aspect_ratio", "Orijinal")),
            fps=str(data.get("fps", "Orijinal")),
            audio_bitrate=str(data.get("audio_bitrate", "192k")),
            denoise_audio=bool(data.get("denoise_audio", False)),
            use_gpu=bool(data.get("use_gpu", True)),
            translate=bool(data.get("translate", False)),
            preset_name=str(data.get("preset_name", "Özel")),
        )

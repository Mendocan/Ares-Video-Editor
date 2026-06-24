from __future__ import annotations

import copy
from dataclasses import dataclass

from app.core.clip_effects import ClipEffects
from app.core.subtitle_parser import SubtitleEntry
from app.core.timeline import TimelineClip, TimelineModel
from app.core.word_timing_data import WordTimingDocument, build_timed_subtitles


@dataclass
class EditorSnapshot:
    clips: list[TimelineClip]
    subtitle_entries: list[SubtitleEntry]
    duration_ms: int
    word_timing: dict | None = None


def _clone_clip(clip: TimelineClip) -> TimelineClip:
    return TimelineClip(
        clip_id=clip.clip_id,
        track=clip.track,
        label=clip.label,
        timeline_start_ms=clip.timeline_start_ms,
        timeline_end_ms=clip.timeline_end_ms,
        source_path=clip.source_path,
        source_start_ms=clip.source_start_ms,
        source_end_ms=clip.source_end_ms,
        selected=clip.selected,
        linked_clip_id=clip.linked_clip_id,
        effects=ClipEffects(
            speed=clip.effects.speed,
            fade_in_ms=clip.effects.fade_in_ms,
            fade_out_ms=clip.effects.fade_out_ms,
            volume=clip.effects.volume,
        )
        if clip.effects
        else ClipEffects(),
    )


def capture_snapshot(
    model: TimelineModel,
    subtitle_entries: list[SubtitleEntry],
    word_document: WordTimingDocument | None = None,
) -> EditorSnapshot:
    return EditorSnapshot(
        clips=[_clone_clip(c) for c in model.clips],
        subtitle_entries=copy.deepcopy(subtitle_entries),
        duration_ms=model.duration_ms,
        word_timing=word_document.to_dict() if word_document else None,
    )


def restore_snapshot(
    model: TimelineModel,
    snapshot: EditorSnapshot,
) -> tuple[list[SubtitleEntry], list, WordTimingDocument | None]:
    model.clips = [_clone_clip(c) for c in snapshot.clips]
    model.duration_ms = snapshot.duration_ms
    entries = copy.deepcopy(snapshot.subtitle_entries)
    word_document = (
        WordTimingDocument.from_dict(snapshot.word_timing)
        if snapshot.word_timing
        else None
    )
    return entries, build_timed_subtitles(entries, word_document), word_document


class EditHistory:
    """Timeline ve altyazi duzenlemeleri icin geri/ileri al."""

    def __init__(self, max_depth: int = 40) -> None:
        self.max_depth = max_depth
        self._undo: list[EditorSnapshot] = []
        self._redo: list[EditorSnapshot] = []

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def push(self, snapshot: EditorSnapshot) -> None:
        self._undo.append(snapshot)
        if len(self._undo) > self.max_depth:
            self._undo.pop(0)
        self._redo.clear()

    def can_undo(self) -> bool:
        return len(self._undo) > 1

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> EditorSnapshot | None:
        if len(self._undo) < 2:
            return None
        current = self._undo.pop()
        self._redo.append(current)
        return self._undo[-1]

    def redo(self) -> EditorSnapshot | None:
        if not self._redo:
            return None
        snapshot = self._redo.pop()
        self._undo.append(snapshot)
        return snapshot

    def seed(self, snapshot: EditorSnapshot) -> None:
        self.clear()
        self._undo.append(snapshot)

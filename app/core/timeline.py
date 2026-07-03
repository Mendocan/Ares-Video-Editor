from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path


TRACK_VIDEO = "video"
TRACK_AUDIO = "audio"
TRACK_SUBTITLE = "subtitle"

EDIT_MODE_RIPPLE = "ripple"
EDIT_MODE_SLIP = "slip"


from app.core.clip_effects import ClipEffects


@dataclass
class TimelineClip:
    """Tek bir timeline klip parçası."""

    clip_id: str
    track: str
    label: str
    timeline_start_ms: int
    timeline_end_ms: int
    source_path: str | None = None
    source_start_ms: int = 0
    source_end_ms: int | None = None
    selected: bool = False
    linked_clip_id: str | None = None
    effects: ClipEffects | None = None

    def __post_init__(self) -> None:
        if self.effects is None:
            self.effects = ClipEffects()

    @property
    def duration_ms(self) -> int:
        return max(0, self.timeline_end_ms - self.timeline_start_ms)

    @property
    def resolved_source_end_ms(self) -> int:
        if self.source_end_ms is not None:
            return self.source_end_ms
        return self.source_start_ms + self.duration_ms

    def contains_time(self, time_ms: int) -> bool:
        return self.timeline_start_ms < time_ms < self.timeline_end_ms


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class TimelineModel:
    """Timeline üzerindeki tüm klipleri yönetir."""

    def __init__(self) -> None:
        self.clips: list[TimelineClip] = []
        self.duration_ms: int = 0
        self.edit_mode: str = EDIT_MODE_RIPPLE

    def clear(self) -> None:
        self.clips.clear()
        self.duration_ms = 0

    def set_duration(self, duration_ms: int) -> None:
        self.duration_ms = max(0, duration_ms)

    def clips_on_track(self, track: str) -> list[TimelineClip]:
        return sorted(
            [c for c in self.clips if c.track == track],
            key=lambda c: c.timeline_start_ms,
        )

    def get_clip(self, clip_id: str) -> TimelineClip | None:
        for clip in self.clips:
            if clip.clip_id == clip_id:
                return clip
        return None

    def selected_clips(self) -> list[TimelineClip]:
        return [c for c in self.clips if c.selected]

    def clear_selection(self) -> None:
        for clip in self.clips:
            clip.selected = False

    def select_clip(self, clip_id: str, additive: bool = False) -> None:
        if not additive:
            self.clear_selection()
        clip = self.get_clip(clip_id)
        if clip:
            clip.selected = True

    def select_track(self, track: str, additive: bool = False) -> None:
        """Bir track'teki tum klipleri secer (V1 / A1 / S1 basligi)."""
        if not additive:
            self.clear_selection()
        for clip in self.clips_on_track(track):
            clip.selected = True

    def _break_links_to(self, removed_ids: set[str]) -> None:
        for clip in self.clips:
            if clip.linked_clip_id in removed_ids:
                clip.linked_clip_id = None

    def _recalc_duration(self) -> None:
        if not self.clips:
            return
        self.duration_ms = max(c.timeline_end_ms for c in self.clips)

    def add_media_clip(
        self,
        source_path: str,
        label: str | None = None,
        at_ms: int | None = None,
        duration_ms: int | None = None,
        link_audio: bool = True,
    ) -> TimelineClip:
        """Video + isteğe bağlı ses klibi ekler."""
        path = Path(source_path).resolve()
        if duration_ms is None:
            duration_ms = self.duration_ms or 0
        if at_ms is None:
            video_clips = self.clips_on_track(TRACK_VIDEO)
            at_ms = video_clips[-1].timeline_end_ms if video_clips else 0

        display = label or path.name
        end_ms = at_ms + duration_ms

        video_id = _new_id()
        video_clip = TimelineClip(
            clip_id=video_id,
            track=TRACK_VIDEO,
            label=display,
            timeline_start_ms=at_ms,
            timeline_end_ms=end_ms,
            source_path=str(path),
            source_start_ms=0,
            source_end_ms=duration_ms,
        )
        self.clips.append(video_clip)

        if link_audio:
            audio_id = _new_id()
            audio_clip = TimelineClip(
                clip_id=audio_id,
                track=TRACK_AUDIO,
                label=f"{display} (Ses)",
                timeline_start_ms=at_ms,
                timeline_end_ms=end_ms,
                source_path=str(path),
                source_start_ms=0,
                source_end_ms=duration_ms,
                linked_clip_id=video_id,
            )
            video_clip.linked_clip_id = audio_id
            self.clips.append(audio_clip)

        self._recalc_duration()
        return video_clip

    def add_audio_clip(
        self,
        source_path: str,
        at_ms: int,
        duration_ms: int,
        label: str | None = None,
    ) -> TimelineClip:
        """Video ile eslesmemis, bagimsiz bir ses klibi (orn. ses efekti) ekler."""
        path = Path(source_path).resolve()
        display = label or path.stem
        at_ms = max(0, at_ms)
        end_ms = at_ms + max(1, duration_ms)

        clip = TimelineClip(
            clip_id=_new_id(),
            track=TRACK_AUDIO,
            label=display,
            timeline_start_ms=at_ms,
            timeline_end_ms=end_ms,
            source_path=str(path),
            source_start_ms=0,
            source_end_ms=duration_ms,
        )
        self.clips.append(clip)
        self._recalc_duration()
        return clip

    def add_subtitle_clip(self, duration_ms: int, label: str = "Altyazı") -> TimelineClip:
        """Altyazı track'ine görsel klip ekler."""
        existing = self.clips_on_track(TRACK_SUBTITLE)
        start_ms = 0
        if existing:
            start_ms = existing[-1].timeline_end_ms

        end_ms = max(start_ms + duration_ms, duration_ms)
        clip = TimelineClip(
            clip_id=_new_id(),
            track=TRACK_SUBTITLE,
            label=label,
            timeline_start_ms=start_ms,
            timeline_end_ms=end_ms,
        )
        self.clips.append(clip)
        self._recalc_duration()
        return clip

    def replace_primary_media(self, source_path: str, duration_ms: int) -> None:
        """Ana video/ses kliplerini sıfırdan kurar."""
        resolved = str(Path(source_path).resolve())
        self.clips = [c for c in self.clips if c.track == TRACK_SUBTITLE]
        self.add_media_clip(resolved, duration_ms=duration_ms, at_ms=0)
        self.duration_ms = max(self.duration_ms, duration_ms)

    def rescale_primary_media_duration(self, source_path: str, duration_ms: int) -> bool:
        """Aynı ana kaynak için video/ses klip surelerini günceller."""
        if duration_ms <= 0:
            return False

        resolved = str(Path(source_path).resolve())
        video_clips = self.clips_on_track(TRACK_VIDEO)
        if not video_clips:
            return False

        primary = video_clips[0]
        if Path(primary.source_path or "").resolve() != resolved:
            return False
        if abs(primary.duration_ms - duration_ms) <= 200:
            return False

        primary.timeline_end_ms = primary.timeline_start_ms + duration_ms
        primary.source_end_ms = duration_ms

        if primary.linked_clip_id:
            audio = self.get_clip(primary.linked_clip_id)
            if audio:
                audio.timeline_end_ms = audio.timeline_start_ms + duration_ms
                audio.source_end_ms = duration_ms

        self._recalc_duration()
        return True

    def replace_subtitle_span(self, duration_ms: int) -> None:
        """Altyazı kliplerini tek parça olarak günceller."""
        self.clips = [c for c in self.clips if c.track != TRACK_SUBTITLE]
        if duration_ms > 0:
            self.add_subtitle_clip(duration_ms)
        self._recalc_duration()

    def split_at(self, time_ms: int) -> int:
        """Playhead konumunda tüm track'lerdeki klipleri böler. Bölünen klip sayısını döner."""
        if time_ms <= 0:
            return 0

        split_count = 0
        new_clips: list[TimelineClip] = []

        for clip in list(self.clips):
            if not clip.contains_time(time_ms):
                continue

            left_duration = time_ms - clip.timeline_start_ms
            source_split = clip.source_start_ms + left_duration

            right_clip = TimelineClip(
                clip_id=_new_id(),
                track=clip.track,
                label=clip.label,
                timeline_start_ms=time_ms,
                timeline_end_ms=clip.timeline_end_ms,
                source_path=clip.source_path,
                source_start_ms=source_split,
                source_end_ms=clip.resolved_source_end_ms,
                linked_clip_id=None,
            )

            clip.timeline_end_ms = time_ms
            clip.source_end_ms = source_split
            clip.linked_clip_id = None

            new_clips.append(right_clip)
            split_count += 1

        self.clips.extend(new_clips)
        self._recalc_duration()
        return split_count

    def delete_selected(self, ripple: bool | None = None) -> int:
        """Secili klipleri siler. Yalnizca secilen track'ler etkilenir; bagli klip otomatik silinmez."""
        to_remove = list(self.selected_clips())
        if not to_remove:
            return 0

        use_ripple = self.edit_mode == EDIT_MODE_RIPPLE if ripple is None else ripple
        remove_ids = {c.clip_id for c in to_remove}
        removed = sorted(to_remove, key=lambda c: c.timeline_start_ms)

        for clip in removed:
            gap = clip.duration_ms
            self.clips.remove(clip)
            if use_ripple:
                for other in self.clips:
                    if other.track == clip.track and other.timeline_start_ms >= clip.timeline_end_ms:
                        other.timeline_start_ms -= gap
                        other.timeline_end_ms -= gap

        self._break_links_to(remove_ids)
        self._recalc_duration()
        return len(removed)

    def merge_selected(self) -> int:
        """Bitişik, aynı kaynaktan ve aynı track'teki seçili klipleri tek klipte birleştirir.

        Genellikle bir "Böl" işlemini geri almak için kullanılır. Kaynakları
        farklı ya da aralarında boşluk olan klipler birleştirilmez.
        Birleştirilen klip çifti sayısını döner.
        """
        selected = [c for c in self.selected_clips()]
        if len(selected) < 2:
            return 0

        by_track: dict[str, list[TimelineClip]] = {}
        for clip in selected:
            by_track.setdefault(clip.track, []).append(clip)

        merged_count = 0
        for clips in by_track.values():
            clips.sort(key=lambda c: c.timeline_start_ms)
            i = 0
            while i < len(clips) - 1:
                a, b = clips[i], clips[i + 1]
                mergeable = (
                    a.source_path is not None
                    and a.source_path == b.source_path
                    and a.timeline_end_ms == b.timeline_start_ms
                    and a.resolved_source_end_ms == b.source_start_ms
                )
                if mergeable:
                    a.timeline_end_ms = b.timeline_end_ms
                    a.source_end_ms = b.resolved_source_end_ms
                    a.selected = True
                    if b in self.clips:
                        self.clips.remove(b)
                    if b.linked_clip_id and a.linked_clip_id != b.linked_clip_id:
                        linked = self.get_clip(b.linked_clip_id)
                        if linked:
                            linked.linked_clip_id = a.linked_clip_id
                    clips.pop(i + 1)
                    merged_count += 1
                else:
                    i += 1

        self._recalc_duration()
        return merged_count

    def trim_clip(
        self,
        clip_id: str,
        edge: str,
        local_x: int,
        px_per_ms: float,
        ripple: bool | None = None,
    ) -> bool:
        """Klip kenarini kirpar. Ripple modda sol kenar sonrakileri kaydirir."""
        clip = self.get_clip(clip_id)
        if not clip or px_per_ms <= 0:
            return False

        use_ripple = self.edit_mode == EDIT_MODE_RIPPLE if ripple is None else ripple
        delta_ms = int(local_x / px_per_ms)

        if edge == "left":
            new_start = clip.timeline_start_ms + delta_ms
            if new_start >= clip.timeline_end_ms - 100:
                return False
            shift = new_start - clip.timeline_start_ms
            source_delta = shift
            clip.timeline_start_ms = new_start
            clip.source_start_ms += source_delta
            if use_ripple and shift != 0:
                for other in self.clips:
                    if other.clip_id == clip_id:
                        continue
                    if other.track == clip.track and other.timeline_start_ms >= clip.timeline_end_ms:
                        other.timeline_start_ms -= shift
                        other.timeline_end_ms -= shift
        else:
            new_end = clip.timeline_start_ms + delta_ms
            if new_end <= clip.timeline_start_ms + 100:
                return False
            old_end = clip.timeline_end_ms
            clip.timeline_end_ms = new_end
            clip.source_end_ms = clip.source_start_ms + clip.duration_ms
            if use_ripple:
                shrink = old_end - new_end
                if shrink != 0:
                    for other in self.clips:
                        if other.clip_id == clip_id:
                            continue
                        if other.track == clip.track and other.timeline_start_ms >= old_end:
                            other.timeline_start_ms -= shrink
                            other.timeline_end_ms -= shrink

        self._recalc_duration()
        return True

    def move_clip(self, clip_id: str, new_start_ms: int) -> None:
        clip = self.get_clip(clip_id)
        if not clip:
            return

        new_start_ms = max(0, new_start_ms)
        duration = clip.duration_ms
        clip.timeline_start_ms = new_start_ms
        clip.timeline_end_ms = new_start_ms + duration

        self._recalc_duration()

    def video_segments_for_export(self) -> list[tuple[str, int, int, ClipEffects]]:
        """Export icin (kaynak, baslangic, bitis, efektler)."""
        segments: list[tuple[str, int, int, ClipEffects]] = []
        for clip in self.clips_on_track(TRACK_VIDEO):
            if not clip.source_path:
                continue
            effects = clip.effects or ClipEffects()
            segments.append(
                (
                    clip.source_path,
                    clip.source_start_ms,
                    clip.resolved_source_end_ms,
                    effects,
                )
            )
        return segments

    def standalone_audio_segments_for_export(self) -> list[tuple[str, int, int, int]]:
        """Videoya bagli olmayan (orn. eklenen ses efekti) klipleri dondurur.

        Donus: (kaynak_yolu, source_start_ms, source_end_ms, timeline_start_ms).
        Bir video klibine bagli (linked_clip_id'li) ses klipleri video dosyasinin
        kendi ses izi zaten export'a dahil oldugu icin burada tekrar sayilmaz.
        """
        segments: list[tuple[str, int, int, int]] = []
        for clip in self.clips_on_track(TRACK_AUDIO):
            if not clip.source_path or clip.linked_clip_id:
                continue
            segments.append(
                (
                    clip.source_path,
                    clip.source_start_ms,
                    clip.resolved_source_end_ms,
                    clip.timeline_start_ms,
                )
            )
        return segments

    def apply_effects_to_selected(self, effects: ClipEffects) -> int:
        """Secili video/ses kliplerine efekt uygular."""
        updated = 0
        for clip in self.selected_clips():
            if clip.track not in (TRACK_VIDEO, TRACK_AUDIO):
                continue
            clip.effects = ClipEffects(
                speed=effects.speed,
                fade_in_ms=effects.fade_in_ms,
                fade_out_ms=effects.fade_out_ms,
                volume=effects.volume,
                transition_in=effects.transition_in,
                transition_duration_ms=effects.transition_duration_ms,
            )
            updated += 1
        return updated

    def has_timeline_edits(self) -> bool:
        """Timeline'da kesme/bölme yapılıp yapılmadığını kontrol eder."""
        video_clips = self.clips_on_track(TRACK_VIDEO)
        if len(video_clips) != 1:
            return len(video_clips) > 1
        if not video_clips:
            return False
        clip = video_clips[0]
        return clip.source_start_ms != 0 or clip.timeline_start_ms != 0

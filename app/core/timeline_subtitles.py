from __future__ import annotations

from app.core.subtitle_parser import SubtitleEntry
from app.core.word_timing import TimedSubtitle, TimedWord, build_word_timings


def split_subtitles_at(subtitles: list[TimedSubtitle], time_ms: int) -> list[TimedSubtitle]:
    """Playhead konumunda altyazı bloklarını böler."""
    if time_ms <= 0:
        return subtitles

    new_entries: list[SubtitleEntry] = []
    index = 1

    for ts in subtitles:
        entry = ts.entry
        if entry.start_ms < time_ms < entry.end_ms:
            left_text_words = []
            right_text_words = []
            for word in ts.words:
                if word.end_ms <= time_ms:
                    left_text_words.append(word.text)
                elif word.start_ms >= time_ms:
                    right_text_words.append(word.text)
                else:
                    left_text_words.append(word.text)
                    right_text_words.append(word.text)

            left_entry = SubtitleEntry(
                index=index,
                start=entry.start,
                end=_ms_to_srt(time_ms),
                text=" ".join(left_text_words) or entry.text,
                start_ms=entry.start_ms,
                end_ms=time_ms,
            )
            index += 1
            right_entry = SubtitleEntry(
                index=index,
                start=_ms_to_srt(time_ms),
                end=entry.end,
                text=" ".join(right_text_words) or entry.text,
                start_ms=time_ms,
                end_ms=entry.end_ms,
            )
            index += 1
            new_entries.extend([left_entry, right_entry])
        else:
            new_entry = SubtitleEntry(
                index=index,
                start=entry.start,
                end=entry.end,
                text=entry.text,
                start_ms=entry.start_ms,
                end_ms=entry.end_ms,
            )
            index += 1
            new_entries.append(new_entry)

    return build_word_timings(new_entries)


def ripple_delete_subtitles(
    subtitles: list[TimedSubtitle],
    delete_start_ms: int,
    delete_end_ms: int,
) -> list[TimedSubtitle]:
    """Silinen zaman aralığına göre altyazıları kaldırır ve sonrakileri sola kaydırır."""
    gap = delete_end_ms - delete_start_ms
    if gap <= 0:
        return subtitles

    new_entries: list[SubtitleEntry] = []
    index = 1

    for ts in subtitles:
        entry = ts.entry
        if entry.end_ms <= delete_start_ms:
            new_entries.append(
                SubtitleEntry(
                    index=index,
                    start=entry.start,
                    end=entry.end,
                    text=entry.text,
                    start_ms=entry.start_ms,
                    end_ms=entry.end_ms,
                )
            )
            index += 1
        elif entry.start_ms >= delete_end_ms:
            new_entries.append(
                SubtitleEntry(
                    index=index,
                    start=_ms_to_srt(entry.start_ms - gap),
                    end=_ms_to_srt(entry.end_ms - gap),
                    text=entry.text,
                    start_ms=entry.start_ms - gap,
                    end_ms=entry.end_ms - gap,
                )
            )
            index += 1
        elif entry.start_ms < delete_start_ms and entry.end_ms > delete_end_ms:
            new_entries.append(
                SubtitleEntry(
                    index=index,
                    start=entry.start,
                    end=_ms_to_srt(delete_start_ms),
                    text=entry.text,
                    start_ms=entry.start_ms,
                    end_ms=delete_start_ms,
                )
            )
            index += 1

    return build_word_timings(new_entries)


def remap_subtitles_for_segments(
    subtitles: list[TimedSubtitle],
    segments: list[tuple[int, int]],
) -> list[TimedSubtitle]:
    """
    Kaynak video segmentlerine göre altyazı zamanlarını yeniden eşler.
    Whisper kelime zamanlamaları korunur.
    segments: (kaynak_baslangic_ms, kaynak_bitis_ms) listesi.
    """
    if not segments:
        return subtitles

    output_cursor = 0
    mapped: list[TimedSubtitle] = []
    index = 1

    for seg_start, seg_end in segments:
        for ts in subtitles:
            entry = ts.entry
            if entry.end_ms <= seg_start or entry.start_ms >= seg_end:
                continue

            clip_start = max(entry.start_ms, seg_start)
            clip_end = min(entry.end_ms, seg_end)
            line_start = output_cursor + (clip_start - seg_start)
            line_end = line_start + (clip_end - clip_start)

            remapped_words: list[TimedWord] = []
            for word in ts.words:
                if word.end_ms <= seg_start or word.start_ms >= seg_end:
                    continue
                word_clip_start = max(word.start_ms, seg_start)
                word_clip_end = min(word.end_ms, seg_end)
                word_offset = word_clip_start - clip_start
                remapped_words.append(
                    TimedWord(
                        text=word.text,
                        start_ms=line_start + word_offset,
                        end_ms=line_start + word_offset + (word_clip_end - word_clip_start),
                        index=len(remapped_words),
                    )
                )

            if remapped_words:
                text = " ".join(word.text for word in remapped_words)
            elif entry.text.strip():
                text = entry.text
            else:
                continue

            mapped.append(
                TimedSubtitle(
                    entry=SubtitleEntry(
                        index=index,
                        start=_ms_to_srt(line_start),
                        end=_ms_to_srt(line_end),
                        text=text,
                        start_ms=line_start,
                        end_ms=line_end,
                    ),
                    words=remapped_words,
                )
            )
            index += 1

        output_cursor += seg_end - seg_start

    if not mapped:
        return subtitles

    return mapped


def _ms_to_srt(ms: int) -> str:
    hours, remainder = divmod(max(0, ms), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

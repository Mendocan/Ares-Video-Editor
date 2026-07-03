from __future__ import annotations

from dataclasses import dataclass

from app.core.subtitle_text import capitalize_word_start
from app.core.subtitle_parser import SubtitleEntry


@dataclass(slots=True)
class TimedWord:
    text: str
    start_ms: int
    end_ms: int
    index: int


@dataclass(slots=True)
class TimedSubtitle:
    entry: SubtitleEntry
    words: list[TimedWord]

    @property
    def text(self) -> str:
        return self.entry.text

    @property
    def start_ms(self) -> int:
        return self.entry.start_ms

    @property
    def end_ms(self) -> int:
        return self.entry.end_ms


def build_word_timings(entries: list[SubtitleEntry]) -> list[TimedSubtitle]:
    timed_subtitles: list[TimedSubtitle] = []

    for entry in entries:
        raw_words = entry.text.split()
        if not raw_words:
            timed_subtitles.append(TimedSubtitle(entry=entry, words=[]))
            continue

        duration_ms = max(entry.duration_ms, len(raw_words))
        base_step = duration_ms // len(raw_words)
        remainder = duration_ms % len(raw_words)
        cursor = entry.start_ms
        timed_words: list[TimedWord] = []

        for index, word in enumerate(raw_words):
            extra = 1 if index < remainder else 0
            word_duration = max(1, base_step + extra)
            word_end = min(entry.end_ms, cursor + word_duration)

            if index == len(raw_words) - 1:
                word_end = entry.end_ms

            timed_words.append(
                TimedWord(
                    text=word,
                    start_ms=cursor,
                    end_ms=max(cursor + 1, word_end),
                    index=index,
                )
            )
            cursor = word_end

        timed_words = _ensure_first_word_capitalized(timed_words)
        timed_subtitles.append(align_words_to_entry_bounds(TimedSubtitle(entry=entry, words=timed_words)))

    return timed_subtitles


def _ensure_first_word_capitalized(words: list[TimedWord]) -> list[TimedWord]:
    if not words:
        return words
    first = words[0]
    capped = capitalize_word_start(first.text)
    if capped == first.text:
        return words
    words[0] = TimedWord(
        text=capped,
        start_ms=first.start_ms,
        end_ms=first.end_ms,
        index=first.index,
    )
    return words


def find_subtitle_at_time(subtitles: list[TimedSubtitle], current_ms: int) -> TimedSubtitle | None:
    for subtitle in subtitles:
        if subtitle.start_ms <= current_ms <= subtitle.end_ms:
            return subtitle
    return None


def align_words_to_entry_bounds(subtitle: TimedSubtitle) -> TimedSubtitle:
    """Kelime zamanlarini satir araligina hizalar; ilk kelime satir basinda aktif olur."""
    words = subtitle.words
    if not words:
        return subtitle

    line_start = subtitle.start_ms
    line_end = subtitle.end_ms
    aligned: list[TimedWord] = []

    for index, word in enumerate(words):
        start_ms = word.start_ms
        end_ms = word.end_ms
        if index == 0:
            start_ms = min(start_ms, line_start)
        if index == len(words) - 1:
            end_ms = max(end_ms, line_end)
        start_ms = max(line_start, min(start_ms, line_end - 1))
        end_ms = max(start_ms + 1, min(end_ms, line_end))
        aligned.append(
            TimedWord(
                text=word.text,
                start_ms=start_ms,
                end_ms=end_ms,
                index=index,
            )
        )

    aligned = _ensure_first_word_capitalized(aligned)
    return TimedSubtitle(entry=subtitle.entry, words=aligned)


def find_active_word_index(subtitle: TimedSubtitle | None, current_ms: int) -> int | None:
    if subtitle is None or not subtitle.words:
        return None

    if current_ms < subtitle.start_ms or current_ms > subtitle.end_ms:
        return None

    for word in subtitle.words:
        if word.start_ms <= current_ms < word.end_ms:
            return word.index

    # Satir yeni acildi, ilk kelime zamanlamasi henuz eslesmiyorsa
    if current_ms <= subtitle.words[0].start_ms:
        return 0

    return None


def ensure_subtitle_words(subtitles: list[TimedSubtitle]) -> list[TimedSubtitle]:
    """Kelime zamanlamasi eksik altyazilar icin metinden zamanlama uretir."""
    output: list[TimedSubtitle] = []
    for subtitle in subtitles:
        if subtitle.words:
            output.append(align_words_to_entry_bounds(subtitle))
            continue
        rebuilt = build_word_timings([subtitle.entry])
        item = rebuilt[0] if rebuilt else subtitle
        output.append(align_words_to_entry_bounds(item) if item.words else item)
    return output

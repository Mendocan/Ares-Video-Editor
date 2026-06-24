from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.subtitle_parser import SubtitleEntry, parse_timecode
from app.core.word_timing import TimedSubtitle, TimedWord, build_word_timings


WORD_TIMING_VERSION = 1
WORD_TIMING_SUFFIX = ".areswords.json"


@dataclass(slots=True)
class WordTimingSegment:
    index: int
    start_ms: int
    end_ms: int
    words: list[dict[str, int | str]]


@dataclass
class WordTimingDocument:
    version: int
    segments: list[WordTimingSegment]

    def words_for_index(self, entry_index: int) -> list[dict[str, int | str]] | None:
        for segment in self.segments:
            if segment.index == entry_index:
                return segment.words
        return None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "segments": [
                {
                    "index": segment.index,
                    "start_ms": segment.start_ms,
                    "end_ms": segment.end_ms,
                    "words": segment.words,
                }
                for segment in self.segments
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> WordTimingDocument:
        segments = [
            WordTimingSegment(
                index=int(item["index"]),
                start_ms=int(item.get("start_ms", 0)),
                end_ms=int(item.get("end_ms", 0)),
                words=list(item.get("words", [])),
            )
            for item in data.get("segments", [])
        ]
        return cls(version=int(data.get("version", WORD_TIMING_VERSION)), segments=segments)


def word_timing_path_for_srt(srt_path: str) -> Path:
    path = Path(srt_path)
    return path.with_name(f"{path.stem}{WORD_TIMING_SUFFIX}")


def save_word_timing_document(document: WordTimingDocument, file_path: str | Path) -> Path:
    output = Path(file_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output


def load_word_timing_document(file_path: str | Path) -> WordTimingDocument | None:
    path = Path(file_path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return WordTimingDocument.from_dict(data)


def build_timed_subtitles(
    entries: list[SubtitleEntry],
    word_document: WordTimingDocument | None = None,
) -> list[TimedSubtitle]:
    """SRT girislerinden TimedSubtitle listesi; varsa Whisper kelime zamanlarini kullanir."""
    if word_document is None:
        return build_word_timings(entries)

    timed: list[TimedSubtitle] = []
    for entry in entries:
        raw_words = word_document.words_for_index(entry.index)
        if not raw_words:
            timed.extend(build_word_timings([entry]))
            continue

        timed_words: list[TimedWord] = []
        for index, item in enumerate(raw_words):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            start_ms = int(item.get("start_ms", entry.start_ms))
            end_ms = int(item.get("end_ms", start_ms + 1))
            timed_words.append(
                TimedWord(
                    text=text,
                    start_ms=max(0, start_ms),
                    end_ms=max(start_ms + 1, end_ms),
                    index=len(timed_words),
                )
            )

        if not timed_words:
            timed.extend(build_word_timings([entry]))
            continue

        timed.append(TimedSubtitle(entry=entry, words=timed_words))

    return timed


def document_from_entries(entries: list[SubtitleEntry], timed: list[TimedSubtitle]) -> WordTimingDocument:
    """Mevcut TimedSubtitle verisinden kayit dosyasi olusturur."""
    timed_by_index = {ts.entry.index: ts for ts in timed}
    segments: list[WordTimingSegment] = []
    for entry in entries:
        ts = timed_by_index.get(entry.index)
        words: list[dict[str, int | str]] = []
        if ts:
            for word in ts.words:
                words.append(
                    {"text": word.text, "start_ms": word.start_ms, "end_ms": word.end_ms}
                )
        segments.append(
            WordTimingSegment(
                index=entry.index,
                start_ms=entry.start_ms,
                end_ms=entry.end_ms,
                words=words,
            )
        )
    return WordTimingDocument(version=WORD_TIMING_VERSION, segments=segments)


def ms_to_srt_time(ms: int) -> str:
    hours, remainder = divmod(max(0, ms), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def entries_from_document(document: WordTimingDocument) -> list[SubtitleEntry]:
    """Kelime dokumanindan SubtitleEntry listesi (yedek/icerik)."""
    entries: list[SubtitleEntry] = []
    for segment in document.segments:
        text = " ".join(str(w.get("text", "")) for w in segment.words).strip()
        start_ms = segment.start_ms
        end_ms = segment.end_ms
        if segment.words:
            start_ms = int(segment.words[0].get("start_ms", start_ms))
            end_ms = int(segment.words[-1].get("end_ms", end_ms))
        entries.append(
            SubtitleEntry(
                index=segment.index,
                start=ms_to_srt_time(start_ms),
                end=ms_to_srt_time(end_ms),
                text=text,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )
    return entries

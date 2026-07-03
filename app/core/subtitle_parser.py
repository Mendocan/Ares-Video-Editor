from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.core.subtitle_text import capitalize_subtitle_text


TIMECODE_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


@dataclass(slots=True)
class SubtitleEntry:
    index: int
    start: str
    end: str
    text: str
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def __post_init__(self) -> None:
        normalized = capitalize_subtitle_text(self.text)
        if normalized != self.text:
            object.__setattr__(self, "text", normalized)


def parse_timecode(value: str) -> int:
    hours, minutes, seconds_ms = value.split(":")
    seconds, milliseconds = seconds_ms.split(",")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(milliseconds)
    )


def parse_srt(file_path: str) -> list[SubtitleEntry]:
    """
    MVP sonrasi kelime bazli isleme altyapisina temel olmasi icin basit SRT ayraci.
    """
    path = Path(file_path)
    content = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\r?\n", content.strip())
    entries: list[SubtitleEntry] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue

        if not lines[0].isdigit():
            continue

        match = TIMECODE_RE.fullmatch(lines[1])
        if not match:
            continue

        start = match.group("start")
        end = match.group("end")
        entries.append(
            SubtitleEntry(
                index=int(lines[0]),
                start=start,
                end=end,
                text=" ".join(lines[2:]),
                start_ms=parse_timecode(start),
                end_ms=parse_timecode(end),
            )
        )

    return entries

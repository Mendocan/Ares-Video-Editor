from __future__ import annotations

import re
import sys
from pathlib import Path


def strip_ass(text: str) -> str:
    return " ".join(re.sub(r"\{[^}]*\}", "", text).split())


def ass_time_to_ms(value: str) -> int:
    hours, minutes, rest = value.split(":")
    seconds, centis = (rest.split(".") + ["0"])[:2]
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(centis) * 10
    )


def ms_to_srt(ms: int) -> str:
    hours, remainder = divmod(max(0, ms), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def ass_to_srt(ass_path: Path, srt_path: Path | None = None) -> Path:
    srt_path = srt_path or ass_path.with_suffix(".srt")
    dialogues: list[tuple[int, int, str]] = []

    for line in ass_path.read_text(encoding="utf-8-sig").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        payload = line.split(",", 9)
        if len(payload) < 10:
            continue
        start, end, text = payload[1], payload[2], payload[9]
        dialogues.append((ass_time_to_ms(start), ass_time_to_ms(end), strip_ass(text)))

    groups: list[dict[str, int | str]] = []
    for start, end, text in dialogues:
        if groups and groups[-1]["text"] == text:
            groups[-1]["end"] = end
        else:
            groups.append({"start": start, "end": end, "text": text})

    blocks: list[str] = []
    for index, group in enumerate(groups, 1):
        blocks.append(str(index))
        blocks.append(f"{ms_to_srt(int(group['start']))} --> {ms_to_srt(int(group['end']))}")
        blocks.append(str(group["text"]))
        blocks.append("")

    srt_path.write_text("\n".join(blocks), encoding="utf-8-sig")
    return srt_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Kullanim: python ass_to_srt.py <dosya.ass> [cikti.srt]")

    ass_path = Path(sys.argv[1])
    srt_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ass_path.with_suffix(".srt")
    output = ass_to_srt(ass_path, srt_path)
    print(f"{len(output.read_text(encoding='utf-8-sig').splitlines())} satir yazildi: {output}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from app.core.word_timing_data import (
    WordTimingDocument,
    WordTimingSegment,
    WORD_TIMING_VERSION,
    save_word_timing_document,
    word_timing_path_for_srt,
)


@dataclass(slots=True)
class TranscriptionResult:
    srt_path: Path
    words_path: Path
    word_document: WordTimingDocument


class TranscriptionService:
    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "default"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

    def configure(self, model_size: str | None = None) -> None:
        if model_size and model_size != self.model_size:
            self.model_size = model_size
            self._model = None

    def _load_model(self, progress_callback: Callable[[str], None] | None = None) -> WhisperModel:
        if self._model is None:
            self._notify(progress_callback, 5, f"Whisper modeli yukleniyor ({self.model_size})...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def generate_srt(
        self,
        video_path: str,
        output_srt_path: str,
        translate: bool = False,
        language: str | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> TranscriptionResult:
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video bulunamadi: {video_path}")

        model = self._load_model(progress_callback)
        task_name = "translate" if translate else "transcribe"
        self._notify(progress_callback, 12, "Ses analiz ediliyor...")

        transcribe_kwargs: dict = {"word_timestamps": True, "task": task_name}
        if language:
            transcribe_kwargs["language"] = language

        segments, info = model.transcribe(video_path, **transcribe_kwargs)
        duration = float(getattr(info, "duration", 0) or 0)

        output_path = Path(output_srt_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        words_path = word_timing_path_for_srt(str(output_path))
        timing_segments: list[WordTimingSegment] = []

        with output_path.open("w", encoding="utf-8-sig") as handle:
            for index, segment in enumerate(segments, start=1):
                start_time = self._format_timestamp(segment.start)
                end_time = self._format_timestamp(segment.end)
                text = segment.text.strip()

                handle.write(f"{index}\n")
                handle.write(f"{start_time} --> {end_time}\n")
                handle.write(f"{text}\n\n")

                words: list[dict[str, int | str]] = []
                if segment.words:
                    for word in segment.words:
                        token = word.word.strip()
                        if not token:
                            continue
                        words.append(
                            {
                                "text": token,
                                "start_ms": self._seconds_to_ms(word.start),
                                "end_ms": self._seconds_to_ms(word.end),
                            }
                        )

                timing_segments.append(
                    WordTimingSegment(
                        index=index,
                        start_ms=self._seconds_to_ms(segment.start),
                        end_ms=self._seconds_to_ms(segment.end),
                        words=words,
                    )
                )

                if progress_callback and duration > 0:
                    ratio = min(1.0, segment.end / duration)
                    pct = 15 + int(ratio * 80)
                    self._notify(
                        progress_callback,
                        pct,
                        f"Satir {index} isleniyor ({int(ratio * 100)}%)",
                    )

        document = WordTimingDocument(version=WORD_TIMING_VERSION, segments=timing_segments)
        save_word_timing_document(document, words_path)
        self._notify(progress_callback, 98, "Kelime zamanlamasi kaydediliyor...")

        return TranscriptionResult(
            srt_path=output_path,
            words_path=words_path,
            word_document=document,
        )

    @staticmethod
    def _notify(callback: Callable[[str], None] | None, percent: int, message: str) -> None:
        if callback:
            callback(f"{percent}|{message}")

    def _seconds_to_ms(self, value: float) -> int:
        return max(0, int(round(value * 1000)))

    def _format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int(round(seconds - int(seconds), 3) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

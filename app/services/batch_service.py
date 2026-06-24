from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.subtitle_parser import parse_srt
from app.core.word_timing_data import build_timed_subtitles, load_word_timing_document, word_timing_path_for_srt
from app.services.export_service import ExportRequest, ExportService


@dataclass(slots=True)
class BatchJob:
    video_path: str
    srt_path: str | None
    output_path: str


@dataclass(slots=True)
class BatchResult:
    video_path: str
    output_path: str | None
    success: bool
    message: str


class BatchExportService:
    def find_srt_for_video(self, video_path: str) -> str | None:
        path = Path(video_path)
        candidates = [
            path.with_suffix(".srt"),
            path.parent / f"{path.stem}.srt",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def build_jobs(
        self,
        video_paths: list[str],
        output_dir: str,
        auto_match_srt: bool = True,
    ) -> list[BatchJob]:
        jobs: list[BatchJob] = []
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        for video_path in video_paths:
            video = Path(video_path)
            srt_path = self.find_srt_for_video(video_path) if auto_match_srt else None
            output_path = str(out / f"{video.stem}_subtitled.mp4")
            jobs.append(BatchJob(video_path=str(video), srt_path=srt_path, output_path=output_path))
        return jobs

    def run_batch(
        self,
        jobs: list[BatchJob],
        request_template: ExportRequest,
        export_service: ExportService,
        progress_callback=None,
        total_duration_ms: int = 60_000,
    ) -> list[BatchResult]:
        results: list[BatchResult] = []
        total = max(len(jobs), 1)

        for index, job in enumerate(jobs):
            base_pct = int((index / total) * 100)
            self._notify(progress_callback, base_pct, f"Isleniyor ({index + 1}/{total}): {Path(job.video_path).name}")

            if not job.srt_path or not Path(job.srt_path).exists():
                results.append(
                    BatchResult(
                        video_path=job.video_path,
                        output_path=None,
                        success=False,
                        message="Eslesen SRT bulunamadi",
                    )
                )
                continue

            try:
                entries = parse_srt(job.srt_path)
                word_doc = load_word_timing_document(word_timing_path_for_srt(job.srt_path))
                timed = build_timed_subtitles(entries, word_doc)

                request = ExportRequest(
                    video_path=job.video_path,
                    subtitle_path=job.srt_path,
                    output_path=job.output_path,
                    font_name=request_template.font_name,
                    font_size=request_template.font_size,
                    normal_color=request_template.normal_color,
                    active_color=request_template.active_color,
                    stroke_size=request_template.stroke_size,
                    shadow_size=request_template.shadow_size,
                    position=request_template.position,
                    logo_path=request_template.logo_path,
                    logo_pos=request_template.logo_pos,
                    logo_size=request_template.logo_size,
                    aspect_ratio=request_template.aspect_ratio,
                    fps=request_template.fps,
                    audio_bitrate=request_template.audio_bitrate,
                    use_animation=request_template.use_animation,
                    animation_style=request_template.animation_style,
                    denoise_audio=request_template.denoise_audio,
                    use_gpu=request_template.use_gpu,
                    bg_box=request_template.bg_box,
                    video_segments=[],
                )

                def item_progress(message: str) -> None:
                    if not progress_callback or "|" not in message:
                        return
                    pct_str, label = message.split("|", 1)
                    try:
                        sub_pct = int(pct_str)
                    except ValueError:
                        return
                    combined = min(99, base_pct + int(sub_pct / total))
                    progress_callback(f"{combined}|{label}")

                export_service.export(
                    request,
                    timed,
                    progress_callback=item_progress,
                    total_duration_ms=total_duration_ms,
                )
                results.append(
                    BatchResult(
                        video_path=job.video_path,
                        output_path=job.output_path,
                        success=True,
                        message="Tamamlandi",
                    )
                )
            except Exception as exc:
                results.append(
                    BatchResult(
                        video_path=job.video_path,
                        output_path=None,
                        success=False,
                        message=str(exc),
                    )
                )

        self._notify(progress_callback, 100, "Toplu islem tamamlandi")
        return results

    @staticmethod
    def _notify(callback, percent: int, message: str) -> None:
        if callback:
            callback(f"{percent}|{message}")

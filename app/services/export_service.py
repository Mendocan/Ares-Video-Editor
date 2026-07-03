from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
import re
import subprocess
import threading

from app.core.clip_effects import ClipEffects, build_segment_filter
from app.core.font_resolver import prepare_export_fonts
from app.core.ffmpeg_paths import ensure_ffmpeg_on_path, ffmpeg_missing_message, is_nvenc_available
from app.core.media_probe import probe_duration_ms
from app.core.subtitle_positions import ass_style_values
from app.core.subtitle_style import (
    LOGO_OVERLAY_POSITIONS,
    ass_filter_value,
    export_style_from_preview,
)
from app.core.video_presets import build_ffmpeg_video_filter, play_resolution
from app.core.word_timing import TimedSubtitle, ensure_subtitle_words

_OUT_TIME_RE = re.compile(
    r"out_time=(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)\.(?P<micro>\d+)"
)


def _parse_progress_time_ms(line: str) -> int | None:
    if not line.startswith("out_time="):
        return None
    match = _OUT_TIME_RE.match(line.strip())
    if not match:
        return None
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    micro = int(match.group("micro")[:6].ljust(6, "0"))
    return hours * 3_600_000 + minutes * 60_000 + seconds * 1_000 + micro // 1000


@dataclass(slots=True)
class ExportRequest:
    video_path: str
    subtitle_path: str
    output_path: str
    font_name: str
    font_size: int
    normal_color: str
    active_color: str
    stroke_size: int
    shadow_size: int
    position: str = "Alt Orta"
    logo_path: str = ""
    logo_pos: str = "Sag Ust"
    logo_size: int = 150
    aspect_ratio: str = "Orijinal"
    fps: str = "Orijinal"
    audio_bitrate: str = "192k"
    use_animation: bool = True
    animation_style: str = "Pop-up"
    denoise_audio: bool = False
    use_gpu: bool = False
    bg_box: bool = False
    video_crf: int = 23
    video_preset: str = "fast"
    video_segments: list[tuple[str, int, int, ClipEffects]] = field(default_factory=list)
    preview_height_px: int = 0


class ExportService:
    def validate(self, request: ExportRequest) -> None:
        if not ensure_ffmpeg_on_path():
            raise RuntimeError(ffmpeg_missing_message())

        if not Path(request.video_path).exists():
            raise FileNotFoundError(f"Dosya bulunamadi: {request.video_path}")

        output_parent = Path(request.output_path).parent
        output_parent.mkdir(parents=True, exist_ok=True)

    def _prepare_video_source(
        self,
        request: ExportRequest,
        work_dir: Path,
        is_preview: bool = False,
        preview_time_sec: float = 0,
        progress_callback: Callable[[str], None] | None = None,
    ) -> tuple[str, bool]:
        """
        Timeline segmentlerinden birleşik video hazırlar.
        Dönüş: (video_girdi_yolu, geçici_dosya_mi)
        """
        segments = request.video_segments
        if not segments:
            segments = [(request.video_path, 0, 0, ClipEffects())]

        if len(segments) == 1 and not is_preview:
            path, start_ms, end_ms, effects = segments[0]
            if start_ms == 0 and end_ms == 0 and not effects.has_video_filters() and not effects.has_audio_filters():
                return path, False
            if end_ms > start_ms or start_ms > 0 or effects.has_video_filters() or effects.has_audio_filters():
                trimmed = work_dir / "timeline_trimmed.mp4"
                self._cut_segment(path, start_ms, end_ms, trimmed, effects)
                return str(trimmed), True

        if len(segments) == 1 and is_preview:
            return request.video_path, False

        temp_dir = work_dir / "timeline_segments"
        temp_dir.mkdir(parents=True, exist_ok=True)
        list_file = temp_dir / "concat.txt"
        part_paths: list[str] = []

        for i, (path, start_ms, end_ms, effects) in enumerate(segments):
            if progress_callback and len(segments) > 1:
                pct = 8 + int((i / len(segments)) * 3)
                self._notify(
                    progress_callback,
                    pct,
                    f"Video segmenti hazirlaniyor ({i + 1}/{len(segments)})...",
                )
            part = temp_dir / f"part_{i:03d}.mp4"
            self._cut_segment(path, start_ms, end_ms, part, effects)
            part_paths.append(str(part))

        with list_file.open("w", encoding="utf-8") as handle:
            for part in part_paths:
                handle.write(f"file '{Path(part).as_posix()}'\n")

        merged = work_dir / "timeline_merged.mp4"
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(merged)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Timeline segmentleri birlestirilemedi.")

        if is_preview:
            preview_src = work_dir / "preview_source.mp4"
            preview_cmd = [
                "ffmpeg", "-y", "-ss", str(preview_time_sec),
                "-i", str(merged), "-vframes", "1", "-f", "null", "-",
            ]
            subprocess.run(preview_cmd, capture_output=True, check=False)
            trim_cmd = [
                "ffmpeg", "-y", "-ss", str(max(0, preview_time_sec - 0.05)),
                "-i", str(merged), "-t", "0.2", "-c", "copy", str(preview_src),
            ]
            subprocess.run(trim_cmd, capture_output=True, check=False)
            return str(merged), True

        return str(merged), True

    def _cut_segment(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        output: Path,
        effects: ClipEffects,
    ) -> None:
        start_sec = start_ms / 1000.0
        if end_ms > start_ms:
            duration_sec = max(0.001, (end_ms - start_ms) / 1000.0)
        else:
            duration_sec = 0.0

        cmd = ["ffmpeg", "-y"]
        if start_ms > 0:
            cmd.extend(["-ss", f"{start_sec:.3f}"])
        cmd.extend(["-i", path])
        if end_ms > start_ms:
            cmd.extend(["-t", f"{duration_sec:.3f}"])

        vf, af = build_segment_filter(duration_sec if end_ms > start_ms else 0, effects)
        if vf:
            cmd.extend(["-vf", vf])
        if af:
            cmd.extend(["-af", af])

        if vf or af:
            cmd.extend(["-c:v", "libx264", "-preset", "fast", "-c:a", "aac"])
        else:
            cmd.extend(["-c", "copy"])
        cmd.append(str(output))

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Video segmenti islenemedi.")

    def _build_ffmpeg_command(
        self,
        request: ExportRequest,
        ass_path: Path | None,
        output_path: str,
        video_input: str,
        is_preview: bool = False,
        preview_time_sec: float = 0,
        fonts_dir: Path | None = None,
        ffmpeg_cwd: Path | None = None,
    ) -> list[str]:
        command = ["ffmpeg", "-y"]

        if is_preview:
            command.extend(["-ss", str(preview_time_sec)])

        command.extend(["-i", video_input])

        fmt_filter = build_ffmpeg_video_filter(request.aspect_ratio)
        ass_filter = (
            ass_filter_value(ass_path, fonts_dir, ffmpeg_cwd)
            if ass_path is not None
            else None
        )

        if request.logo_path and Path(request.logo_path).exists():
            command.extend(["-i", request.logo_path])

            overlay = LOGO_OVERLAY_POSITIONS.get(request.logo_pos, "W-w-10:10")

            if ass_filter is not None:
                filter_str = (
                    f"[1:v]scale={request.logo_size}:-1[logo_scaled];"
                    f"[0:v]{ass_filter}[v_ass];"
                    f"[v_ass][logo_scaled]overlay={overlay}[out_v]"
                )
            else:
                filter_str = (
                    f"[1:v]scale={request.logo_size}:-1[logo_scaled];"
                    f"[0:v][logo_scaled]overlay={overlay}[out_v]"
                )
            
            if request.aspect_ratio == "Dikey (9:16)":
                filter_str += ";[out_v]crop=ih*9/16:ih[out_v]"
            elif request.aspect_ratio == "Yatay (16:9)":
                filter_str += ";[out_v]crop=iw:iw*9/16[out_v]"
            elif fmt_filter:
                filter_str += f";[out_v]{fmt_filter}[out_v]"
                
            command.extend(["-filter_complex", filter_str, "-map", "[out_v]"])
            if not is_preview:
                command.extend(["-map", "0:a?"])
        elif ass_filter is not None:
            vf_str = ass_filter
            if fmt_filter:
                vf_str += f",{fmt_filter}"
            command.extend(["-vf", vf_str])
        elif fmt_filter:
            command.extend(["-vf", fmt_filter])

        if is_preview:
            command.extend(["-vframes", "1", "-q:v", "2", output_path])
            return command

        if request.fps != "Orijinal":
            command.extend(["-r", request.fps])

        # GPU Hizlandirma (NVIDIA NVENC)
        if request.use_gpu:
            command.extend(["-c:v", "h264_nvenc", "-preset", "p4"])
        else:
            command.extend([
                "-c:v", "libx264",
                "-preset", request.video_preset,
                "-crf", str(request.video_crf),
            ])

        if request.audio_bitrate == "Orijinal" and not request.denoise_audio:
            command.extend(["-c:a", "copy"])
        else:
            command.extend(["-c:a", "aac"])
            if request.audio_bitrate != "Orijinal":
                command.extend(["-b:a", request.audio_bitrate])
            if request.denoise_audio:
                command.extend(["-af", "afftdn"])

        if str(output_path).lower().endswith(".mp4"):
            command.extend(["-movflags", "+faststart"])

        command.append(output_path)
        return command

    def export(
        self,
        request: ExportRequest,
        subtitles: list[TimedSubtitle],
        progress_callback: Callable[[str], None] | None = None,
        total_duration_ms: int = 0,
    ) -> Path:
        self.validate(request)

        output_path = Path(request.output_path)
        work_dir = output_path.parent
        ass_path: Path | None = None
        fonts_dir: Path | None = None
        if subtitles:
            self._notify(progress_callback, 2, "Altyazi dosyasi hazirlaniyor...")
            subtitles = ensure_subtitle_words(subtitles)
            fonts_dir, ass_font_name = prepare_export_fonts(request.font_name, work_dir)
            ass_path = output_path.with_suffix(".ass")
            ass_path.write_text(
                self._build_ass_document(request, subtitles, ass_font_name),
                encoding="utf-8-sig",
            )
        else:
            self._notify(progress_callback, 2, "Video hazirlaniyor...")

        self._notify(progress_callback, 8, "Video segmentleri hazirlaniyor...")
        video_input, _ = self._prepare_video_source(
            request, work_dir, progress_callback=progress_callback
        )
        request = self._resolve_gpu_request(request, progress_callback)
        ffmpeg_cwd = Path(ass_path.parent) if ass_path is not None else work_dir
        command = self._build_ffmpeg_command(
            request,
            ass_path,
            str(output_path),
            video_input,
            fonts_dir=fonts_dir,
            ffmpeg_cwd=ffmpeg_cwd,
        )

        resolved_duration_ms = self._resolve_export_duration_ms(
            total_duration_ms,
            video_input,
            request,
        )

        self._notify(progress_callback, 12, "FFmpeg disa aktarimi basliyor...")
        self._run_ffmpeg_with_gpu_fallback(
            request,
            command,
            ass_path,
            str(output_path),
            video_input,
            str(ffmpeg_cwd),
            progress_callback,
            resolved_duration_ms,
            fonts_dir,
        )
        self._notify(progress_callback, 100, "Tamamlandi")
        return output_path

    def _resolve_gpu_request(
        self,
        request: ExportRequest,
        progress_callback: Callable[[str], None] | None,
    ) -> ExportRequest:
        if not request.use_gpu:
            return request
        if is_nvenc_available():
            return request
        self._notify(
            progress_callback,
            10,
            "NVIDIA GPU kullanilamiyor; CPU kodlayici (libx264) ile devam ediliyor...",
        )
        return replace(request, use_gpu=False)

    @staticmethod
    def _is_nvenc_failure(stderr: str) -> bool:
        lowered = stderr.lower()
        markers = ("nvcuda.dll", "h264_nvenc", "nvenc", "cuda")
        return any(marker in lowered for marker in markers)

    def _run_ffmpeg_with_gpu_fallback(
        self,
        request: ExportRequest,
        command: list[str],
        ass_path: Path | None,
        output_path: str,
        video_input: str,
        ffmpeg_cwd: str,
        progress_callback: Callable[[str], None] | None,
        total_duration_ms: int,
        fonts_dir: Path | None = None,
    ) -> None:
        try:
            self._run_ffmpeg(command, ffmpeg_cwd, progress_callback, total_duration_ms)
        except RuntimeError as exc:
            if not request.use_gpu or not self._is_nvenc_failure(str(exc)):
                raise
            self._notify(
                progress_callback,
                12,
                "GPU hatasi algilandi; CPU kodlayici ile tekrar deneniyor...",
            )
            cpu_request = replace(request, use_gpu=False)
            cpu_command = self._build_ffmpeg_command(
                cpu_request,
                ass_path,
                output_path,
                video_input,
                fonts_dir=fonts_dir,
                ffmpeg_cwd=Path(ffmpeg_cwd),
            )
            self._run_ffmpeg(cpu_command, ffmpeg_cwd, progress_callback, total_duration_ms)

    @staticmethod
    def _notify(callback: Callable[[str], None] | None, percent: int, message: str) -> None:
        if callback:
            callback(f"{percent}|{message}")

    @staticmethod
    def _resolve_export_duration_ms(
        total_duration_ms: int,
        video_input: str,
        request: ExportRequest,
    ) -> int:
        if total_duration_ms > 0:
            return total_duration_ms

        segments = request.video_segments
        if segments:
            segment_total = 0
            for _path, start_ms, end_ms, _effects in segments:
                if end_ms > start_ms:
                    segment_total += end_ms - start_ms
                else:
                    probed = probe_duration_ms(_path)
                    if probed > 0:
                        segment_total += probed
            if segment_total > 0:
                return segment_total

        probed = probe_duration_ms(video_input)
        if probed > 0:
            return probed
        return max(total_duration_ms, 1)

    @staticmethod
    def _format_progress_time(ms: int) -> str:
        total_seconds, milliseconds = divmod(max(0, ms), 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def _progress_from_output_time(self, line: str, total_duration_ms: int) -> int | None:
        if line.startswith("out_time_us="):
            try:
                out_us = int(line.split("=", 1)[1])
                ratio = min(1.0, out_us / (max(total_duration_ms, 1) * 1000))
                return 12 + int(ratio * 86)
            except ValueError:
                return None

        if line.startswith("out_time_ms="):
            try:
                out_ms = int(line.split("=", 1)[1])
                ratio = min(1.0, out_ms / max(total_duration_ms, 1))
                return 12 + int(ratio * 86)
            except ValueError:
                return None

        if line.startswith("out_time="):
            out_ms = _parse_progress_time_ms(line)
            if out_ms is None:
                return None
            ratio = min(1.0, out_ms / max(total_duration_ms, 1))
            return 12 + int(ratio * 86)

        return None

    def _current_output_ms(self, line: str) -> int | None:
        if line.startswith("out_time_us="):
            try:
                return int(line.split("=", 1)[1]) // 1000
            except ValueError:
                return None
        if line.startswith("out_time_ms="):
            try:
                return int(line.split("=", 1)[1])
            except ValueError:
                return None
        if line.startswith("out_time="):
            return _parse_progress_time_ms(line)
        return None

    def _run_ffmpeg(
        self,
        command: list[str],
        cwd: str,
        progress_callback: Callable[[str], None] | None,
        total_duration_ms: int,
    ) -> None:
        run_command = list(command)
        if "-nostdin" not in run_command:
            run_command.insert(1, "-nostdin")
        if progress_callback:
            run_command[1:1] = ["-progress", "pipe:1", "-nostats", "-loglevel", "error"]

        process = subprocess.Popen(
            run_command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stderr_chunks: list[str] = []
        total_ms = max(total_duration_ms, 1)
        total_label = self._format_progress_time(total_ms)
        progress_state = {"last_percent": 12}

        def _drain_stderr() -> None:
            if not process.stderr:
                return
            try:
                stderr_chunks.append(process.stderr.read() or "")
            except Exception:
                pass

        def _drain_stdout() -> None:
            if not process.stdout:
                return
            try:
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue

                    percent = self._progress_from_output_time(line, total_ms)
                    if percent is not None:
                        progress_state["last_percent"] = max(progress_state["last_percent"], percent)
                        current_ms = self._current_output_ms(line)
                        if current_ms is not None:
                            current_label = self._format_progress_time(current_ms)
                            message = f"Video disa aktariliyor... {current_label} / {total_label}"
                        else:
                            message = "Video disa aktariliyor..."
                        self._notify(progress_callback, progress_state["last_percent"], message)
                        continue

                    if line == "progress=continue" and progress_state["last_percent"] == 12:
                        self._notify(
                            progress_callback,
                            12,
                            f"Video isleniyor... 00:00 / {total_label}",
                        )
                    elif line == "progress=end":
                        self._notify(progress_callback, 98, "Dosya yaziliyor...")
            except Exception:
                pass

        stdout_thread = threading.Thread(target=_drain_stdout, daemon=True)
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        code = process.wait()
        stdout_thread.join(timeout=60)
        stderr_thread.join(timeout=60)

        stderr = "".join(stderr_chunks)
        if code != 0:
            raise RuntimeError(stderr.strip() or "FFmpeg export basarisiz oldu.")

    def extract_preview_frame(self, request: ExportRequest, subtitles: list[TimedSubtitle], current_ms: int) -> Path:
        self.validate(request)
        work_dir = Path(request.output_path).parent
        output_path = work_dir / "preview_frame.jpg"
        ass_path: Path | None = None
        fonts_dir: Path | None = None
        if subtitles:
            fonts_dir, ass_font_name = prepare_export_fonts(request.font_name, work_dir)
            subtitles = ensure_subtitle_words(subtitles)
            ass_path = work_dir / "preview_temp.ass"
            ass_path.write_text(
                self._build_ass_document(request, subtitles, ass_font_name),
                encoding="utf-8-sig",
            )

        video_input, _ = self._prepare_video_source(
            request, work_dir, is_preview=True, preview_time_sec=current_ms / 1000.0
        )
        preview_cwd = work_dir
        command = self._build_ffmpeg_command(
            request,
            ass_path,
            str(output_path),
            video_input,
            is_preview=True,
            preview_time_sec=current_ms / 1000.0,
            fonts_dir=fonts_dir,
            ffmpeg_cwd=preview_cwd,
        )
        
        result = subprocess.run(
            command,
            cwd=str(ass_path.parent if ass_path is not None else work_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Onizleme karesi cikarilamadi.")
            
        return output_path

    def _build_ass_document(
        self,
        request: ExportRequest,
        subtitles: list[TimedSubtitle],
        ass_font_name: str | None = None,
    ) -> str:
        border_style = "3" if request.bg_box else "1"
        back_color = "&H80000000" if request.bg_box else "&H64000000"
        font_name = ass_font_name or request.font_name
        use_karaoke = any(subtitle.words for subtitle in subtitles)
        normal_colour = self._hex_to_ass_color(request.normal_color)
        active_colour = self._hex_to_ass_color(request.active_color)
        if use_karaoke:
            # \\k: kelime basinda anlik renk degisimi (\\kf duz/sweep dolgu yapar)
            primary_colour = active_colour
            secondary_colour = normal_colour
        else:
            primary_colour = normal_colour
            secondary_colour = "&H000000FF"

        play_x, play_y = play_resolution(request.aspect_ratio)
        font_size, stroke_size, shadow_size = export_style_from_preview(
            request.font_size,
            request.stroke_size,
            request.shadow_size,
            play_y,
            request.preview_height_px,
        )
        alignment, margin_v = ass_style_values(request.position, play_y)
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {play_x}",
            f"PlayResY: {play_y}",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            (
                "Style: Default,"
                f"{font_name},{font_size},{primary_colour},"
                f"{secondary_colour},&H00000000,{back_color},0,0,0,0,100,100,0,0,{border_style},"
                f"{stroke_size},{shadow_size},{alignment},60,60,{margin_v},1"
            ),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        for subtitle in subtitles:
            if use_karaoke and subtitle.words:
                text = self._build_karaoke_text(subtitle)
                effect = "karaoke"
            else:
                text = self._escape_ass_text(subtitle.text)
                effect = ""

            lines.append(
                "Dialogue: 0,"
                f"{self._ms_to_ass_time(subtitle.start_ms)},{self._ms_to_ass_time(subtitle.end_ms)},"
                f"Default,,0,0,0,{effect},{text}"
            )

        return "\n".join(lines) + "\n"

    def _build_karaoke_text(self, subtitle: TimedSubtitle) -> str:
        """Onizlemedeki kelime vurgusu ile ayni zamanlama: \\k etiketleri."""
        words = subtitle.words
        if not words:
            return self._escape_ass_text(subtitle.text)

        line_start = subtitle.start_ms
        parts: list[str] = []

        lead_ms = words[0].start_ms - line_start
        if lead_ms > 0:
            parts.append(f"{{\\k{max(1, lead_ms // 10)}}}")

        for index, word in enumerate(words):
            if index + 1 < len(words):
                duration_ms = words[index + 1].start_ms - word.start_ms
            else:
                duration_ms = max(subtitle.end_ms - word.start_ms, word.end_ms - word.start_ms)
            duration_cs = max(1, duration_ms // 10)
            parts.append(f"{{\\k{duration_cs}}}{self._escape_ass_text(word.text)}")

        return " ".join(parts)

    def _hex_to_ass_color(self, value: str) -> str:
        cleaned = value.lstrip("#")
        if len(cleaned) != 6:
            raise ValueError(f"Gecersiz renk degeri: {value}")

        red = cleaned[0:2]
        green = cleaned[2:4]
        blue = cleaned[4:6]
        return f"&H00{blue}{green}{red}"

    def _ms_to_ass_time(self, value: int) -> str:
        hours, remainder = divmod(max(0, value), 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1_000)
        centiseconds = round(milliseconds / 10)

        if centiseconds >= 100:
            seconds += 1
            centiseconds = 0
        if seconds >= 60:
            minutes += 1
            seconds = 0
        if minutes >= 60:
            hours += 1
            minutes = 0

        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def _escape_ass_text(self, value: str) -> str:
        return value.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

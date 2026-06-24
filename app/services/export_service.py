from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import subprocess

from app.core.animation_presets import ANIMATION_NONE, build_active_word_tags
from app.core.clip_effects import ClipEffects, build_segment_filter
from app.core.subtitle_positions import ass_style_values
from app.core.video_presets import build_ffmpeg_video_filter, play_resolution
from app.core.word_timing import TimedSubtitle
from app.core.ffmpeg_paths import ensure_ffmpeg_on_path, ffmpeg_missing_message


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
    ) -> list[str]:
        command = ["ffmpeg", "-y"]

        if is_preview:
            command.extend(["-ss", str(preview_time_sec)])

        command.extend(["-i", video_input])

        fmt_filter = build_ffmpeg_video_filter(request.aspect_ratio)

        if request.logo_path and Path(request.logo_path).exists():
            command.extend(["-i", request.logo_path])
            
            pos_map = {
                "Sol Ust": "10:10",
                "Sag Ust": "W-w-10:10",
                "Sol Alt": "10:H-h-10",
                "Sag Alt": "W-w-10:H-h-10"
            }
            overlay = pos_map.get(request.logo_pos, "W-w-10:10")

            if ass_path is not None:
                filter_str = (
                    f"[1:v]scale={request.logo_size}:-1[logo_scaled];"
                    f"[0:v]ass=filename='{ass_path.name}'[v_ass];"
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
        elif ass_path is not None:
            vf_str = f"ass=filename='{ass_path.name}'"
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
                # afftdn: Audio FFT Denoise filtresi dip sesi azaltir.
                command.extend(["-af", "afftdn"])

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
        if subtitles:
            self._notify(progress_callback, 2, "Altyazi dosyasi hazirlaniyor...")
            ass_path = output_path.with_suffix(".ass")
            ass_path.write_text(self._build_ass_document(request, subtitles), encoding="utf-8-sig")
        else:
            self._notify(progress_callback, 2, "Video hazirlaniyor...")

        self._notify(progress_callback, 8, "Video segmentleri hazirlaniyor...")
        video_input, _ = self._prepare_video_source(request, work_dir)
        command = self._build_ffmpeg_command(request, ass_path, str(output_path), video_input)

        self._notify(progress_callback, 12, "FFmpeg disa aktarimi basliyor...")
        ffmpeg_cwd = str(ass_path.parent) if ass_path is not None else str(work_dir)
        self._run_ffmpeg(command, ffmpeg_cwd, progress_callback, total_duration_ms)
        self._notify(progress_callback, 100, "Tamamlandi")
        return output_path

    @staticmethod
    def _notify(callback: Callable[[str], None] | None, percent: int, message: str) -> None:
        if callback:
            callback(f"{percent}|{message}")

    def _run_ffmpeg(
        self,
        command: list[str],
        cwd: str,
        progress_callback: Callable[[str], None] | None,
        total_duration_ms: int,
    ) -> None:
        run_command = list(command)
        if progress_callback:
            run_command[1:1] = ["-progress", "pipe:1", "-nostats"]

        process = subprocess.Popen(
            run_command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        total_us = max(total_duration_ms, 1) * 1000

        if progress_callback and process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line.startswith("out_time_us="):
                    try:
                        out_us = int(line.split("=", 1)[1])
                        ratio = min(1.0, out_us / total_us)
                        percent = 12 + int(ratio * 86)
                        self._notify(progress_callback, percent, "Video disa aktariliyor...")
                    except ValueError:
                        continue
                elif line == "progress=end":
                    self._notify(progress_callback, 98, "Dosya yaziliyor...")

        stderr = process.stderr.read() if process.stderr else ""
        code = process.wait()
        if code != 0:
            raise RuntimeError(stderr.strip() or "FFmpeg export basarisiz oldu.")

    def extract_preview_frame(self, request: ExportRequest, subtitles: list[TimedSubtitle], current_ms: int) -> Path:
        self.validate(request)
        work_dir = Path(request.output_path).parent
        output_path = work_dir / "preview_frame.jpg"
        ass_path: Path | None = None
        if subtitles:
            ass_path = work_dir / "preview_temp.ass"
            ass_path.write_text(self._build_ass_document(request, subtitles), encoding="utf-8-sig")

        video_input, _ = self._prepare_video_source(
            request, work_dir, is_preview=True, preview_time_sec=current_ms / 1000.0
        )
        command = self._build_ffmpeg_command(
            request,
            ass_path,
            str(output_path),
            video_input,
            is_preview=True,
            preview_time_sec=current_ms / 1000.0,
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

    def _build_ass_document(self, request: ExportRequest, subtitles: list[TimedSubtitle]) -> str:
        border_style = "3" if request.bg_box else "1"
        back_color = "&H80000000" if request.bg_box else "&H64000000"

        play_x, play_y = play_resolution(request.aspect_ratio)
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
                f"{request.font_name},{request.font_size},{self._hex_to_ass_color(request.normal_color)},"
                f"&H000000FF,&H00000000,{back_color},0,0,0,0,100,100,0,0,{border_style},"
                f"{request.stroke_size},{request.shadow_size},{alignment},60,60,{margin_v},1"
            ),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        for subtitle in subtitles:
            if not subtitle.words:
                lines.append(
                    "Dialogue: 0,"
                    f"{self._ms_to_ass_time(subtitle.start_ms)},{self._ms_to_ass_time(subtitle.end_ms)},"
                    f"Default,,0,0,0,,{self._escape_ass_text(subtitle.text)}"
                )
                continue

            for word in subtitle.words:
                lines.append(
                    "Dialogue: 0,"
                    f"{self._ms_to_ass_time(word.start_ms)},{self._ms_to_ass_time(word.end_ms)},"
                    f"Default,,0,0,0,,{self._build_dialogue_text(subtitle, word.index, request)}"
                )

        return "\n".join(lines) + "\n"

    def _build_dialogue_text(self, subtitle: TimedSubtitle, active_index: int, request: ExportRequest) -> str:
        words: list[str] = []
        active_ass_color = self._hex_to_ass_color(request.active_color)
        style = request.animation_style if request.animation_style != "Yok" else ANIMATION_NONE
        if not request.use_animation:
            style = ANIMATION_NONE

        for word in subtitle.words:
            escaped_word = self._escape_ass_text(word.text)
            if word.index == active_index:
                tags = build_active_word_tags(style, active_ass_color)
                words.append(f"{tags}{escaped_word}{{\\r}}")
            else:
                words.append(escaped_word)

        return " ".join(words)

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

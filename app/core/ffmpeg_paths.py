from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _candidate_bin_dirs() -> list[Path]:
    candidates: list[Path] = []

    env_bin = os.environ.get("ARES_FFMPEG_BIN", "").strip()
    if env_bin:
        candidates.append(Path(env_bin))

    project_tools = Path(__file__).resolve().parents[2] / "tools" / "ffmpeg" / "bin"
    candidates.append(project_tools)

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        winget_packages = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.exists():
            for pattern in ("Gyan.FFmpeg*", "ffmpeg*", "*FFmpeg*"):
                for match in winget_packages.glob(pattern):
                    bin_dir = match / "bin" if match.is_dir() else None
                    if bin_dir and bin_dir.exists():
                        candidates.append(bin_dir)
                    for nested in match.glob("**/bin"):
                        if nested.is_dir():
                            candidates.append(nested)

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    for name in ("ffmpeg", "FFmpeg"):
        candidates.append(Path(program_files) / name / "bin")

    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidates.append(Path(program_files_x86) / "ffmpeg" / "bin")

    unique: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item).lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _prepend_path(directory: Path) -> None:
    path_value = os.environ.get("PATH", "")
    folder = str(directory)
    if folder.lower() in path_value.lower():
        return
    os.environ["PATH"] = folder + os.pathsep + path_value


def _resolve_tool(exe_name: str) -> str | None:
    found = shutil.which(exe_name)
    if found:
        return found

    for directory in _candidate_bin_dirs():
        tool_exe = directory / exe_name
        if tool_exe.exists():
            _prepend_path(directory)
            return str(tool_exe)

    return shutil.which(exe_name)


def ensure_ffmpeg_on_path() -> str | None:
    """FFmpeg'i bulur; bulunursa PATH'e ekler ve ffmpeg.exe yolunu dondurur."""
    return _resolve_tool("ffmpeg.exe" if os.name == "nt" else "ffmpeg")


def resolve_ffprobe() -> str | None:
    """ffprobe yolunu bulur; bulunursa PATH'e ekler."""
    return _resolve_tool("ffprobe.exe" if os.name == "nt" else "ffprobe")


def ffmpeg_missing_message() -> str:
    return (
        "FFmpeg/ffprobe bulunamadi.\n\n"
        "Cozum:\n"
        "1) WinGet ile kurun: winget install Gyan.FFmpeg\n"
        "2) Veya ARES_FFMPEG_BIN ortam degiskenine bin klasorunu yazin\n"
        "3) Uygulamayi yeniden baslatin"
    )


def ffmpeg_available() -> bool:
    return ensure_ffmpeg_on_path() is not None


def ffmpeg_version() -> str | None:
    ffmpeg = ensure_ffmpeg_on_path()
    if not ffmpeg:
        return None
    result = subprocess.run(
        [ffmpeg, "-version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.splitlines()[0] if result.stdout else None

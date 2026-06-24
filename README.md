# Ares Video Editor

Desktop video editor with a multi-track timeline, FFmpeg export, and subtitle tools. Built with **Python** and **PySide6**.

## Features

- **Timeline editing** — video, audio, and subtitle tracks with clip trim, split, move, ripple/slip modes
- **Filmstrip previews** — thumbnail strips on video clips for precise cutting
- **Playback** — preview player with transport controls and scrubbable playhead
- **Export** — MP4 export via FFmpeg (optional burned-in subtitles, logo, effects, GPU/NVENC)
- **Subtitles** — SRT import, styling, word-level timing, Whisper auto-transcription
- **Projects** — save and load `.aresproj` project files
- **Batch export** — export multiple videos with shared settings

## Requirements

- **Windows 10/11** (primary target)
- **Python 3.10+**
- **FFmpeg** — must be available on `PATH` (e.g. `winget install Gyan.FFmpeg`)

Optional:

- **NVIDIA GPU** — for NVENC-accelerated export
- **faster-whisper** — for automatic subtitle generation (downloads models on first use)

## Quick Start

```powershell
cd Ares-Edit
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app\main.py
```

Or use the helper script:

```powershell
.\run.ps1
```

## Usage

1. **Import** — add a video via the sidebar, toolbar, or drag-and-drop onto the timeline.
2. **Edit** — trim clips on the timeline, split at the playhead, apply effects.
3. **Subtitles** (optional) — load an SRT file or generate subtitles with Whisper.
4. **Export** — click **Export** and choose format, resolution, and quality settings.

Exported files are saved to the `output/` folder by default.

## Project Structure

```
app/
  main.py              # Application entry point
  core/                # Timeline model, subtitles, presets, FFmpeg helpers
  services/            # Export, thumbnails, transcription, projects
  ui/                  # Main window, timeline, dialogs
tools/                 # Development utilities
requirements.txt
run.ps1                # Launch script
```

## Building a Standalone App

```powershell
.\build_app.ps1
```

Output is written under `build/dist/`.

## FFmpeg Setup

If export or thumbnails fail with an FFmpeg error, install FFmpeg and ensure it is on your PATH:

```powershell
winget install Gyan.FFmpeg
```

Or run `setup_ffmpeg_path.ps1` if provided in this repo.

## Status

Active development. UI and timeline features are evolving; expect breaking changes between versions.

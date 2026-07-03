from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
MICHROMA_URL = (
    "https://github.com/google/fonts/raw/main/ofl/michroma/Michroma-Regular.ttf"
)

_FONT_ALIASES = {
    "michroma": ["Michroma-Regular.ttf", "michroma.ttf", "Michroma.ttf"],
}


def _ensure_michroma_in_assets() -> Path | None:
    target = ASSETS_DIR / "Michroma-Regular.ttf"
    if target.exists():
        return target
    try:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MICHROMA_URL, target)
    except OSError:
        return None
    except urllib.error.URLError:
        return None
    return target if target.exists() else None


def _windows_fonts_dir() -> Path:
    return Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def _find_font_source(font_name: str) -> Path | None:
    normalized = font_name.strip().lower()
    if normalized == "michroma":
        asset = _ensure_michroma_in_assets()
        if asset:
            return asset

    if ASSETS_DIR.exists():
        for path in ASSETS_DIR.glob("*.ttf"):
            if normalized in path.stem.lower():
                return path
        for path in ASSETS_DIR.glob("*.otf"):
            if normalized in path.stem.lower():
                return path

    fonts_dir = _windows_fonts_dir()
    if fonts_dir.exists():
        for path in fonts_dir.iterdir():
            if path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
                continue
            if normalized in path.stem.lower():
                return path

    for alias in _FONT_ALIASES.get(normalized, []):
        candidate = ASSETS_DIR / alias
        if candidate.exists():
            return candidate
        win_candidate = fonts_dir / alias
        if win_candidate.exists():
            return win_candidate

    return None


def prepare_export_fonts(font_name: str, work_dir: Path) -> tuple[Path, str]:
    """
    Export icin font dosyasini hazirlar.
    Donus: (fontsdir, ass_icinde_kullanilacak_font_adi)
    """
    export_fonts = work_dir / "_export_fonts"
    export_fonts.mkdir(parents=True, exist_ok=True)

    source = _find_font_source(font_name)
    if source is not None:
        dest = export_fonts / source.name
        if not dest.exists() or dest.stat().st_size != source.stat().st_size:
            shutil.copy2(source, dest)
        return export_fonts, font_name

    return _windows_fonts_dir(), font_name

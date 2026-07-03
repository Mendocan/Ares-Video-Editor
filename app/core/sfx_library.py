from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets" / "sfx"

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"}


@dataclass(slots=True)
class SfxSource:
    name: str
    license: str
    url: str
    note: str = ""


@dataclass(slots=True)
class SfxCategory:
    key: str
    label: str
    folder: str
    sources: list[SfxSource] = field(default_factory=list)


# Acik kaynak / CC0 arastirmasindan secilen, GitHub'da veya CC0 olarak
# yayinlanan en iyi ses efekti kaynaklari. Lisans kosullari her kaynagin
# kendi sayfasinda dogrulanmalidir; CC0 olanlar atifsiz ticari kullanima
# uygundur, "karisik" olarak isaretlenenlerde dosya bazinda kontrol gerekir.
SFX_CATEGORIES: list[SfxCategory] = [
    SfxCategory(
        key="wind",
        label="Ruzgar",
        folder="wind",
        sources=[
            SfxSource(
                name="Kenney Audio (kenney.nl)",
                license="CC0",
                url="https://kenney.nl/assets?q=audio",
                note="Atifsiz, ticari kullanima uygun ruzgar/ambiyans paketleri.",
            ),
            SfxSource(
                name="OpenGameArt - Wind / Ambient SFX",
                license="CC0 (karisik, sayfada filtreleyin)",
                url="https://opengameart.org/art-search-advanced?keys=wind&field_art_type_tid%5B%5D=13",
                note="'Windy sound', 'Strong Wind Blowing' gibi CC0 kayitlar.",
            ),
        ],
    ),
    SfxCategory(
        key="engine",
        label="Motor",
        folder="engine",
        sources=[
            SfxSource(
                name="Pttn/stk-assets (SuperTuxKart)",
                license="Cogunlukla CC0/GPL - dosya bazinda kontrol edin",
                url="https://github.com/Pttn/stk-assets/tree/main/sfx",
                note="engine_large.ogg, engine_small.ogg, machine_sound.ogg",
            ),
            SfxSource(
                name="Kenney Audio (kenney.nl)",
                license="CC0",
                url="https://kenney.nl/assets?q=audio",
                note="Arac/motor sesleri iceren CC0 paketler.",
            ),
        ],
    ),
    SfxCategory(
        key="gun",
        label="Silah",
        folder="gun",
        sources=[
            SfxSource(
                name="PanderMusubi/sound-effects-library-weapons",
                license="CC0",
                url="https://github.com/PanderMusubi/sound-effects-library-weapons",
                note="Ates ve ortacag silahlari icin CC0 ses efektleri.",
            ),
            SfxSource(
                name="Pttn/stk-assets - shoot.ogg",
                license="Cogunlukla CC0/GPL - dosya bazinda kontrol edin",
                url="https://github.com/Pttn/stk-assets/tree/main/sfx",
                note="",
            ),
        ],
    ),
    SfxCategory(
        key="explosion",
        label="Patlama",
        folder="explosion",
        sources=[
            SfxSource(
                name="OpenGameArt - SoundFX Library [CC0]",
                license="CC0",
                url="https://opengameart.org/content/soundfx-library-cc0",
                note="Patlama, bang/firework, sci-fi koleksiyonlarini iceren toplu paket.",
            ),
            SfxSource(
                name="Pttn/stk-assets - explosion.ogg",
                license="Cogunlukla CC0/GPL - dosya bazinda kontrol edin",
                url="https://github.com/Pttn/stk-assets/tree/main/sfx",
                note="",
            ),
        ],
    ),
]


def ensure_sfx_folders() -> None:
    for category in SFX_CATEGORIES:
        (ASSETS_ROOT / category.folder).mkdir(parents=True, exist_ok=True)


def category_folder(category: SfxCategory) -> Path:
    return ASSETS_ROOT / category.folder


def local_files_for(category: SfxCategory) -> list[Path]:
    folder = category_folder(category)
    if not folder.exists():
        return []
    return sorted(
        p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )


def find_category(key: str) -> SfxCategory | None:
    return next((c for c in SFX_CATEGORIES if c.key == key), None)

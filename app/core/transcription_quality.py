from __future__ import annotations

import re

from app.core.subtitle_parser import SubtitleEntry

# Ekranda gorunen altyazi imza / jenerik satirlari (Whisper bazen sadece bunu yakalar).
_CREDIT_PATTERNS = (
    re.compile(r"^altyaz[ıi]\s+[\w.]+\.?$", re.IGNORECASE),
    re.compile(r"^subtitle[s]?\s+by\b", re.IGNORECASE),
    re.compile(r"^çeviri\s*:", re.IGNORECASE),
    re.compile(r"^translated\s+by\b", re.IGNORECASE),
)


def is_credit_line(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return True
    return any(pattern.match(cleaned) for pattern in _CREDIT_PATTERNS)


def is_stub_subtitle(entries: list[SubtitleEntry], duration_ms: int) -> bool:
    """Altyazi dosyasi gercek icerik yerine sadece imza/jenerik gibi mi?"""
    if not entries:
        return True

    total_chars = sum(len(entry.text.strip()) for entry in entries)
    duration_sec = max(1.0, duration_ms / 1000.0)

    if len(entries) <= 2 and all(is_credit_line(entry.text) for entry in entries):
        return True

    # Uzun videoda cok az metin = muhtemelen eksik transkripsiyon
    if duration_sec >= 20 and total_chars < 40 and len(entries) <= 2:
        return True

    return False


def is_weak_transcription(segment_count: int, total_text_chars: int, duration_sec: float) -> bool:
    """Whisper sonucu videoya gore suphe derecede kisa mi?"""
    if duration_sec <= 0:
        return False
    if segment_count == 0:
        return True
    chars_per_sec = total_text_chars / duration_sec
    # Konusma/sarki icin saniyede ~2 karakterden az genelde yetersiz
    return chars_per_sec < 2.0 and duration_sec >= 10.0

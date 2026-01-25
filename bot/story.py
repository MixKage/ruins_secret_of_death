from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

STORY_MAX_CHAPTERS = 10
STORY_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "history"
STORY_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "story.json"

ROMAN_NUMERALS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
    7: "VII",
    8: "VIII",
    9: "IX",
    10: "X",
}

def _load_chapters() -> Dict[int, Dict[str, str]]:
    if not STORY_DATA_PATH.exists():
        return {}
    try:
        payload = json.loads(STORY_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    source = payload.get("chapters") if isinstance(payload, dict) else None
    if source is None:
        source = payload
    if not isinstance(source, dict):
        return {}
    chapters: Dict[int, Dict[str, str]] = {}
    for key, value in source.items():
        try:
            chapter_id = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        title = value.get("title")
        text = value.get("text")
        if title or text:
            chapters[chapter_id] = {
                "title": str(title) if title else "",
                "text": str(text) if text else "",
            }
    return chapters


CHAPTERS: Dict[int, Dict[str, str]] = _load_chapters()


def chapter_title(chapter: int) -> str:
    data = CHAPTERS.get(chapter, {})
    if data.get("title"):
        return data["title"]
    roman = ROMAN_NUMERALS.get(chapter, str(chapter))
    return f"Глава {roman}"


def chapter_text(chapter: int) -> str:
    data = CHAPTERS.get(chapter, {})
    return data.get("text", "Глава еще не написана.")


def chapter_photo_path(chapter: int) -> Path:
    return STORY_ASSETS_DIR / f"h{chapter}-rus.jpg"


def apply_slash_style(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    formatted: list[str] = []
    for idx, line in enumerate(lines, start=1):
        formatted.append(line)
        if idx % 4 == 0 and idx != len(lines):
            formatted.append("")
    return "<i>" + "\n".join(formatted) + "</i>"


def build_chapter_caption(chapter: int) -> str:
    title = chapter_title(chapter)
    text = apply_slash_style(chapter_text(chapter))
    return f"<b>{title}</b>\n{text}"


def max_unlocked_chapter(level: int) -> int:
    return max(1, min(int(level), STORY_MAX_CHAPTERS))

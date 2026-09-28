"""Parse English scenario vocabulary lessons for the static audio app."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


FENCE_RE = re.compile(r"```(?:yaml|yml)\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        return line.strip(), ""
    key, value = line.split(":", 1)
    return key.strip(), _scalar(value)


def _parse_yaml_subset(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    current_item: dict[str, Any] | None = None
    current_sublist: str | None = None

    for raw_line in block.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            current_item = None
            current_sublist = None
            if line.endswith(":"):
                key = line[:-1].strip()
                data[key] = []
                current_list = key
                continue
            key, value = _split_key_value(line)
            data[key] = value
            current_list = None
            continue

        if indent == 2 and line.startswith("- ") and current_list:
            key, value = _split_key_value(line[2:])
            current_item = {key: value}
            data[current_list].append(current_item)
            current_sublist = None
            continue

        if indent == 4 and current_item is not None:
            if line.endswith(":"):
                key = line[:-1].strip()
                current_item[key] = []
                current_sublist = key
                continue
            key, value = _split_key_value(line)
            current_item[key] = value
            current_sublist = None
            continue

        if indent == 6 and line.startswith("- ") and current_item is not None and current_sublist:
            current_item[current_sublist].append(_scalar(line[2:]))

    return data


def _source_block(text: str) -> str:
    match = FENCE_RE.search(text)
    if not match:
        return ""
    return match.group(1)


def _scenario_hits(text: str, target_words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for word in target_words:
        target = str(word.get("word", "")).strip()
        if not target:
            continue
        match = re.search(rf"\b{re.escape(target)}\b", text, re.IGNORECASE)
        if match:
            hits.append(
                {
                    "word": target,
                    "start": match.start(),
                    "end": match.end(),
                    "ipa": word.get("ipa", ""),
                    "meaning_zh": word.get("meaning_zh", ""),
                }
            )
    hits.sort(key=lambda hit: hit["start"])
    return hits


def parse_english_lesson(path: Path, text: str) -> dict[str, Any]:
    """Parse one English lesson Markdown file."""

    raw = _parse_yaml_subset(_source_block(text))
    target_words = [
        {
            "word": str(word.get("word", "")).strip(),
            "ipa": str(word.get("ipa", "")).strip(),
            "meaning_zh": str(word.get("meaning_zh", "")).strip(),
            "part_of_speech": str(word.get("part_of_speech", "")).strip(),
            "collocations": list(word.get("collocations", [])),
        }
        for word in raw.get("target_words", [])
    ]
    dialogue = [
        {
            "speaker": str(line.get("speaker", "")).strip(),
            "text": str(line.get("text", "")).strip(),
            "meaning_zh": str(line.get("meaning_zh", "")).strip(),
        }
        for line in raw.get("dialogue", [])
    ]
    scenario_text = str(raw.get("scenario_memory_zh", "")).strip()

    return {
        "id": str(raw.get("id", path.stem)).strip(),
        "language": str(raw.get("language", "english")).strip() or "english",
        "track": str(raw.get("track", "")).strip(),
        "category": str(raw.get("category", "")).strip(),
        "categoryLabel": str(raw.get("category_label_zh", "")).strip(),
        "difficulty": str(raw.get("difficulty", "")).strip(),
        "title": str(raw.get("title_zh", "")).strip(),
        "scenarioMemoryText": scenario_text,
        "scenarioMemory": _scenario_hits(scenario_text, target_words),
        "targetWords": target_words,
        "dialogue": dialogue,
        "reviewPrompt": str(raw.get("review_prompt_zh", "")).strip(),
        "source": path.name,
    }


def validate_english_lesson(lesson: dict[str, Any], source: str) -> list[str]:
    """Return validation errors for one parsed English lesson."""

    errors: list[str] = []
    for field in ["id", "language", "track", "category", "categoryLabel", "difficulty", "title"]:
        if not lesson.get(field):
            errors.append(f"{source}: missing {field}")

    if lesson.get("language") != "english":
        errors.append(f"{source}: language must be english")

    target_words = lesson.get("targetWords") or []
    if not target_words:
        errors.append(f"{source}: missing targetWords")

    for index, word in enumerate(target_words, start=1):
        for field in ["word", "ipa", "meaning_zh", "part_of_speech"]:
            if not word.get(field):
                errors.append(f"{source}: targetWords[{index}] missing {field}")

    if not lesson.get("scenarioMemoryText") or not lesson.get("scenarioMemory"):
        errors.append(f"{source}: missing scenarioMemory")

    if not lesson.get("dialogue"):
        errors.append(f"{source}: missing dialogue")

    return errors

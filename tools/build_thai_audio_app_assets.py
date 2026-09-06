"""Build static data and MP3 files for the Thai audio app."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_DIR = ROOT / "learning-records" / "thai"
APP_DIR = ROOT / "thai-audio-app"
DATA_FILE = APP_DIR / "data" / "phrases.js"
AUDIO_DIR = APP_DIR / "audio"
VOICE = "th-TH-PremwadeeNeural"
CATEGORY_LABELS = {
    "Greetings, Thanks, and Names": "基础问候、感谢和名字",
}

TABLE_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|")
FIELD_RE = re.compile(r"^(中文意思|泰语|拉丁拼音读音|简单日常泰语例句|中文句意)：(.+)$")
BREAKDOWN_PINYIN_RE = re.compile(r"\(([^()]+)\)＝")


def category_from_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            if "：" in line:
                category = line.split("：", 1)[1].strip()
                return CATEGORY_LABELS.get(category, category)
            if ":" in line:
                category = line.split(":", 1)[1].strip()
                return CATEGORY_LABELS.get(category, category)
            category = line[2:].strip()
            return CATEGORY_LABELS.get(category, category)
    return "泰语学习"


def audio_filename(index: int, thai: str) -> str:
    digest = hashlib.sha1(thai.encode("utf-8")).hexdigest()[:10]
    return f"{index:03d}-{digest}.mp3"


def add_item(items: list[dict], seen: set[tuple[str, str]], item: dict) -> None:
    key = (item["thai"], item["meaning"])
    if key in seen:
        return
    seen.add(key)
    items.append(item)


def parse_table_records(path: Path, text: str, items: list[dict], seen: set[tuple[str, str]]) -> None:
    category = category_from_title(text)
    for line in text.splitlines():
        match = TABLE_RE.match(line)
        if not match:
            continue
        meaning, thai, pinyin = [part.strip() for part in match.groups()]
        if meaning in {"中文意思", "---"} or thai == "泰语" or pinyin == "拉丁拼音读音":
            continue
        if not re.search(r"[\u0E00-\u0E7F]", thai):
            continue
        add_item(
            items,
            seen,
            {
                "source": path.name,
                "category": category,
                "kind": "词句",
                "meaning": meaning,
                "thai": thai,
                "pinyin": pinyin.rstrip("."),
            },
        )


def parse_block_records(path: Path, text: str, items: list[dict], seen: set[tuple[str, str]]) -> None:
    category = category_from_title(text)
    blocks = re.split(r"^###\s+", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        fields: dict[str, str] = {}
        breakdown = ""
        for raw_line in block.splitlines():
            line = raw_line.strip()
            field = FIELD_RE.match(line)
            if field:
                fields[field.group(1)] = field.group(2).strip()
            elif line.startswith("> 例句拆解："):
                breakdown = line.split("：", 1)[1].strip()

        meaning = fields.get("中文意思")
        thai = fields.get("泰语")
        pinyin = fields.get("拉丁拼音读音")
        if meaning and thai and pinyin:
            add_item(
                items,
                seen,
                {
                    "source": path.name,
                    "category": category,
                    "kind": "词语",
                    "meaning": meaning,
                    "thai": thai,
                    "pinyin": pinyin.rstrip("."),
                },
            )

        sentence = fields.get("简单日常泰语例句")
        sentence_meaning = fields.get("中文句意")
        pinyin_parts = BREAKDOWN_PINYIN_RE.findall(breakdown)
        if sentence and sentence_meaning and pinyin_parts:
            add_item(
                items,
                seen,
                {
                    "source": path.name,
                    "category": category,
                    "kind": "例句",
                    "meaning": sentence_meaning.rstrip("。"),
                    "thai": sentence,
                    "pinyin": " ".join(pinyin_parts).rstrip("."),
                },
            )


def collect_items() -> list[dict]:
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(RECORD_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parse_table_records(path, text, items, seen)
        parse_block_records(path, text, items, seen)

    for index, item in enumerate(items, 1):
        item["id"] = f"thai-{index:03d}"
        item["audio"] = f"audio/{audio_filename(index, item['thai'])}"
    return items


def write_data(items: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items, ensure_ascii=False, indent=2)
    DATA_FILE.write_text(
        "window.THAI_AUDIO_APP_ITEMS = "
        + payload
        + ";\n"
        + "window.THAI_AUDIO_APP_META = {\n"
        + f"  count: {len(items)},\n"
        + f"  voice: {json.dumps(VOICE)},\n"
        + "  format: \"中文意思 | 泰语 | 拉丁拼音读音\"\n"
        + "};\n",
        encoding="utf-8",
    )


async def generate_audio(items: list[dict], overwrite: bool) -> None:
    import edge_tts

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    for index, item in enumerate(items, 1):
        output = APP_DIR / item["audio"]
        if output.exists() and output.stat().st_size > 0 and not overwrite:
            continue
        if output.exists() and output.stat().st_size == 0:
            output.unlink()
        print(f"[{index}/{len(items)}] -> {output.name}")
        for attempt in range(1, 4):
            try:
                communicate = edge_tts.Communicate(item["thai"], VOICE)
                await communicate.save(str(output))
                break
            except Exception as exc:  # noqa: BLE001 - keep batch generation moving.
                if output.exists():
                    output.unlink()
                if attempt == 3:
                    failures.append(
                        {
                            "index": index,
                            "meaning": item["meaning"],
                            "thai": item["thai"],
                            "audio": item["audio"],
                            "error": str(exc),
                        }
                    )
                else:
                    await asyncio.sleep(1.5 * attempt)

    if failures:
        failure_file = APP_DIR / "audio-generation-failures.json"
        failure_file.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError(f"{len(failures)} audio files failed; see {failure_file.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-audio", action="store_true", help="Only write phrase data.")
    parser.add_argument("--overwrite-audio", action="store_true", help="Regenerate existing MP3 files.")
    args = parser.parse_args()

    items = collect_items()
    write_data(items)
    print(f"Wrote {len(items)} items to {DATA_FILE.relative_to(ROOT)}")

    if not args.skip_audio:
        asyncio.run(generate_audio(items, overwrite=args.overwrite_audio))


if __name__ == "__main__":
    main()

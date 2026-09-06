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
BREAKDOWN_WORD_RE = re.compile(r"([^｜]+?)\s*\(([^()]+)\)＝([^｜]+)")
PIPE_ENTRY_RE = re.compile(r"^\s*(.+?)\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*$")
THAI_RE = re.compile(r"[\u0E00-\u0E7F]")
LOW_TONE_CHARS = set("àèìòùỳÀÈÌÒÙỲ\u0300")
FALLING_TONE_CHARS = set("âêîôûŷÂÊÎÔÛŶ\u0302")
HIGH_TONE_CHARS = set("áéíóúýÁÉÍÓÚÝ\u0301")
RISING_TONE_CHARS = set("ǎěǐǒǔǍĚǏǑǓ\u030c")

MANUAL_WORDS = [
    {"meaning": "你好 / 打招呼", "thai": "สวัสดี", "pinyin": "sà-wàt-dii"},
    {"meaning": "男性礼貌结尾", "thai": "ครับ", "pinyin": "khráp"},
    {"meaning": "女性礼貌结尾", "thai": "ค่ะ", "pinyin": "khâ"},
    {"meaning": "谢谢", "thai": "ขอบคุณ", "pinyin": "khàawp-khun"},
    {"meaning": "谢谢", "thai": "ขอบคุณ", "pinyin": "khàawp khun"},
    {"meaning": "是 / 对", "thai": "ใช่", "pinyin": "châi"},
    {"meaning": "不", "thai": "ไม่", "pinyin": "mâi"},
    {"meaning": "再见", "thai": "ลาก่อน", "pinyin": "laa-gàawn"},
    {"meaning": "我（男性用）", "thai": "ผม", "pinyin": "phǒm"},
    {"meaning": "名字 / 叫", "thai": "ชื่อ", "pinyin": "chʉ̂ʉ"},
    {"meaning": "名字 / 叫", "thai": "ชื่อ", "pinyin": "chûue"},
    {"meaning": "名字 Lucas", "thai": "Lucas", "pinyin": "Lucas"},
    {"meaning": "替换姓名的位置", "thai": "...", "pinyin": "..."},
    {"meaning": "你", "thai": "คุณ", "pinyin": "khun"},
    {"meaning": "什么", "thai": "อะไร", "pinyin": "a-rai"},
    {"meaning": "很好 / 状态好", "thai": "สบายดี", "pinyin": "sà-baai dii"},
    {"meaning": "吗 / 疑问语气", "thai": "ไหม", "pinyin": "mái"},
    {"meaning": "然后 / 那么", "thai": "แล้ว", "pinyin": "láew"},
    {"meaning": "呢 / 反问语气", "thai": "ล่ะ", "pinyin": "lâ"},
    {"meaning": "对不起", "thai": "ขอโทษ", "pinyin": "khǎaw thôot"},
    {"meaning": "是 / 在", "thai": "เป็น", "pinyin": "pen"},
    {"meaning": "事 / 什么事", "thai": "ไร", "pinyin": "rai"},
    {"meaning": "高兴", "thai": "ยินดี", "pinyin": "yin-dii"},
    {"meaning": "连接词", "thai": "ที่", "pinyin": "thîi"},
    {"meaning": "得以 / 能够", "thai": "ได้", "pinyin": "dâai"},
    {"meaning": "认识某个人", "thai": "รู้จัก", "pinyin": "rúu jàk"},
    {"meaning": "哪里", "thai": "ไหน", "pinyin": "nǎi"},
    {"meaning": "来自", "thai": "มาจาก", "pinyin": "maa jàak"},
    {"meaning": "来", "thai": "มา", "pinyin": "maa"},
    {"meaning": "从 / 来自", "thai": "จาก", "pinyin": "jàak"},
    {"meaning": "国家", "thai": "ประเทศ", "pinyin": "bprà-thêet"},
    {"meaning": "中国", "thai": "จีน", "pinyin": "jiin"},
    {"meaning": "让语气更自然柔和", "thai": "นะ", "pinyin": "ná"},
    {"meaning": "幸福", "thai": "ความสุข", "pinyin": "khwaam suk"},
    {"meaning": "有", "thai": "มี", "pinyin": "mii"},
    {"meaning": "以……方式 / ……地", "thai": "อย่าง", "pinyin": "yàang"},
    {"meaning": "年长者 / 哥哥姐姐", "thai": "พี่", "pinyin": "phîi"},
    {"meaning": "男性", "thai": "ชาย", "pinyin": "chaai"},
    {"meaning": "年幼者 / 弟弟妹妹", "thai": "น้อง", "pinyin": "nóng"},
    {"meaning": "女性 / 女孩", "thai": "สาว", "pinyin": "sǎao"},
    {"meaning": "声音", "thai": "เสียง", "pinyin": "sǐang"},
    {"meaning": "好听 / 悦耳", "thai": "เพราะ", "pinyin": "phráw"},
    {"meaning": "非常 / 很", "thai": "มาก", "pinyin": "mâak"},
    {"meaning": "今天", "thai": "วันนี้", "pinyin": "wan-níi"},
    {"meaning": "吃", "thai": "กิน", "pinyin": "gin"},
    {"meaning": "想念", "thai": "คิดถึง", "pinyin": "khít thǔeng"},
    {"meaning": "爱", "thai": "รัก", "pinyin": "rák"},
]
MANUAL_BY_THAI = {}
for word in MANUAL_WORDS:
    MANUAL_BY_THAI.setdefault(word["thai"], word)
PHRASE_WORD_OVERRIDES = {
    "ไม่ใช่": [MANUAL_BY_THAI["ไม่"], MANUAL_BY_THAI["ใช่"]],
    "ผมชื่อ ... ครับ": [
        MANUAL_BY_THAI["ผม"],
        MANUAL_BY_THAI["ชื่อ"],
        MANUAL_BY_THAI["..."],
        MANUAL_BY_THAI["ครับ"],
    ],
    "ผมชื่อ Lucas ครับ": [
        MANUAL_BY_THAI["ผม"],
        MANUAL_BY_THAI["ชื่อ"],
        MANUAL_BY_THAI["Lucas"],
        MANUAL_BY_THAI["ครับ"],
    ],
    "คุณชื่ออะไร": [
        MANUAL_BY_THAI["คุณ"],
        MANUAL_BY_THAI["ชื่อ"],
        MANUAL_BY_THAI["อะไร"],
    ],
    "สบายดีไหม": [MANUAL_BY_THAI["สบายดี"], MANUAL_BY_THAI["ไหม"]],
    "แล้วคุณล่ะ": [
        MANUAL_BY_THAI["แล้ว"],
        MANUAL_BY_THAI["คุณ"],
        MANUAL_BY_THAI["ล่ะ"],
    ],
    "สบายดี แล้วคุณล่ะ": [
        MANUAL_BY_THAI["สบายดี"],
        MANUAL_BY_THAI["แล้ว"],
        MANUAL_BY_THAI["คุณ"],
        MANUAL_BY_THAI["ล่ะ"],
    ],
    "ไม่เป็นไร": [
        MANUAL_BY_THAI["ไม่"],
        MANUAL_BY_THAI["เป็น"],
        MANUAL_BY_THAI["ไร"],
    ],
}


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


def word_audio_filename(thai: str) -> str:
    digest = hashlib.sha1(thai.encode("utf-8")).hexdigest()[:10]
    return f"word-audio/{digest}.mp3"


def add_item(items: list[dict], seen: set[tuple[str, str]], item: dict) -> None:
    key = (item["thai"], item["meaning"])
    if key in seen:
        return
    seen.add(key)
    items.append(item)


def add_word(lexicon: dict[str, dict], word: dict) -> None:
    thai = word["thai"].strip()
    if not thai:
        return
    lexicon.setdefault(
        thai,
        {
            "meaning": word["meaning"].strip().rstrip("。"),
            "thai": thai,
            "pinyin": word["pinyin"].strip().rstrip(".?？"),
        },
    )


def parse_breakdown_words(text: str) -> list[dict]:
    words: list[dict] = []
    for thai, pinyin, meaning in BREAKDOWN_WORD_RE.findall(text):
        thai = thai.strip()
        if not thai:
            continue
        words.append(
            {
                "meaning": meaning.strip().rstrip("。"),
                "thai": thai,
                "pinyin": pinyin.strip().rstrip(".?？"),
            }
        )
    return words


def has_any(text: str, chars: set[str]) -> bool:
    return any(char in chars for char in text)


HIGH_CONSONANT_WORD_RULES = [
    (
        "สวัสดี",
        "สวัสดี 里的 สะ 是“高辅音 + 短元音 + 没有结尾辅音”，读第 2 调低调 sà。",
    ),
    (
        "สบายดี",
        "สบายดี 里的 สะ 是“高辅音 + 短元音 + 没有结尾辅音”，读第 2 调低调 sà。",
    ),
    (
        "ฉัน",
        "ฉัน 上面的 ั 是短元音 a，不是声调符号；ฉ 是高辅音，น 是 n 鼻音结尾，所以是“高辅音 + 短元音 + 鼻音结尾”，读第 5 调升调 chǎn。",
    ),
    (
        "ถุง",
        "ถุง 没有声调符号；ถ 是高辅音，ง 是 ng 鼻音结尾，所以是“高辅音 + 短元音 + 鼻音结尾”，读第 5 调升调 thǔng。",
    ),
    (
        "ผม",
        "ผม 没有声调符号；ผ 是高辅音，ม 是 m 鼻音结尾，所以是“高辅音 + 短元音 + 鼻音结尾”，读第 5 调升调 phǒm。",
    ),
    (
        "ฝน",
        "ฝน 没有声调符号；ฝ 是高辅音，น 是 n 鼻音结尾，所以是“高辅音 + 短元音 + 鼻音结尾”，读第 5 调升调 fǒn。",
    ),
    (
        "ฐาน",
        "ฐาน 没有声调符号；ฐ 是高辅音，า 是长元音 aa，น 是 n 鼻音结尾，属于活音节，所以读第 5 调升调 thǎan。",
    ),
    (
        "ศาลา",
        "ศาลา 的 ศา 没有声调符号；ศ 是高辅音，า 是长元音 aa，属于活音节，所以读第 5 调升调 sǎa。",
    ),
    (
        "ฤๅษี",
        "ฤๅษี 的 ษี 没有声调符号；ษ 是高辅音，ี 是长元音 ii，属于活音节，所以读第 5 调升调 sǐi。",
    ),
    (
        "ของ",
        "ของ 没有声调符号；ข 是高辅音，ง 是 ng 鼻音结尾，属于活音节，所以读第 5 调升调 khǎawng。",
    ),
    (
        "ขอโทษ",
        "ขอโทษ 里的 ขอ 没有声调符号；ข 是高辅音，อ 是长元音 aaw，属于活音节，所以读第 5 调升调 khǎaw。",
    ),
    (
        "ขอบคุณ",
        "ขอบคุณ 里的 ขอบ 没有声调符号，末尾 บ 是 p 收尾，属于死音节，所以读第 2 调低调 khàawp。",
    ),
    (
        "ขวด",
        "ขวด 没有声调符号，末尾 ด 是 t 收尾，属于死音节，所以读第 2 调低调 khùat，末尾轻轻收住。",
    ),
]


def auto_pronunciation_rules(thai: str, pinyin: str) -> list[str]:
    rules: list[str] = []
    if has_any(pinyin, LOW_TONE_CHARS):
        rules.append("à 这类标记是第 2 调：低调，声音压低。")
    if has_any(pinyin, FALLING_TONE_CHARS):
        rules.append("â 这类标记是第 3 调：降调，声音从高往下落。")
    if has_any(pinyin, HIGH_TONE_CHARS):
        rules.append("á 这类标记是第 4 调：高调，声音偏高。")
    if has_any(pinyin, RISING_TONE_CHARS):
        rules.append("ǎ 这类标记是第 5 调：升调，声音从低往高走。")
    if "ครับ" in thai:
        rules.append("ครับ | khráp 是男性礼貌结尾，末尾轻轻收在 p。")
    if "ไหม" in thai:
        rules.append("ไหม | mái 是问句里的“吗”，读高调。")
    for word, rule in HIGH_CONSONANT_WORD_RULES:
        if word in thai:
            rules.append(rule)
    if "ไข่" in thai:
        rules.append("ไข่ 里面的 ่ 是声调符号ไม้เอก；高辅音 ข + ่ 读低调 khài。")
    if "ห้า" in thai:
        rules.append("ห้า 里面的 ้ 是声调符号ไม้โท；高辅音 ห + ้ 读降调 hâa。")

    return rules or ["先按拉丁拼音读；没有声调标记的音节先平稳读。"]


def add_pronunciation_rules(item: dict, explicit_rule: str | None = None) -> dict:
    if explicit_rule:
        item["pronunciationRules"] = [explicit_rule.strip()]
        return item

    rules: list[str] = []
    for rule in auto_pronunciation_rules(item["thai"], item["pinyin"]):
        rules.append(rule)
    item["pronunciationRules"] = rules
    return item


def parse_table_records(path: Path, text: str, items: list[dict], seen: set[tuple[str, str]]) -> None:
    category = category_from_title(text)
    for line in text.splitlines():
        match = TABLE_RE.match(line)
        if not match:
            continue
        meaning, thai, pinyin = [part.strip() for part in match.groups()]
        if meaning in {"中文意思", "---"} or thai == "泰语" or pinyin == "拉丁拼音读音":
            continue
        if not THAI_RE.search(thai):
            continue
        item = {
            "source": path.name,
            "category": category,
            "kind": "词句",
            "meaning": meaning,
            "thai": thai,
            "pinyin": pinyin.rstrip("."),
        }
        add_item(
            items,
            seen,
            add_pronunciation_rules(item),
        )


def parse_block_records(
    path: Path,
    text: str,
    items: list[dict],
    seen: set[tuple[str, str]],
    lexicon: dict[str, dict],
) -> None:
    category = category_from_title(text)
    blocks = re.split(r"^###\s+", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        fields: dict[str, str] = {}
        breakdown = ""
        pronunciation_rule = ""
        for raw_line in block.splitlines():
            line = raw_line.strip()
            field = FIELD_RE.match(line)
            if field:
                fields[field.group(1)] = field.group(2).strip()
            elif line.startswith("> 例句拆解："):
                breakdown = line.split("：", 1)[1].strip()
            elif line.startswith("> 发音规则提示："):
                pronunciation_rule = line.split("：", 1)[1].strip()

        meaning = fields.get("中文意思")
        thai = fields.get("泰语")
        pinyin = fields.get("拉丁拼音读音")
        if meaning and thai and pinyin:
            word = {
                "meaning": meaning,
                "thai": thai,
                "pinyin": pinyin.rstrip("."),
            }
            add_word(lexicon, word)
            add_item(
                items,
                seen,
                add_pronunciation_rules(
                    {
                        "source": path.name,
                        "category": category,
                        "kind": "词语",
                        **word,
                        "words": [word],
                    }
                ),
            )

        sentence = fields.get("简单日常泰语例句")
        sentence_meaning = fields.get("中文句意")
        pinyin_parts = BREAKDOWN_PINYIN_RE.findall(breakdown)
        if sentence and sentence_meaning and pinyin_parts:
            words = parse_breakdown_words(breakdown)
            for word in words:
                add_word(lexicon, word)
            add_item(
                items,
                seen,
                add_pronunciation_rules(
                    {
                        "source": path.name,
                        "category": category,
                        "kind": "例句",
                        "meaning": sentence_meaning.rstrip("。"),
                        "thai": sentence,
                        "pinyin": " ".join(pinyin_parts).rstrip("."),
                        "words": words,
                    },
                    pronunciation_rule,
                ),
            )


def parse_practice_records(path: Path, text: str, items: list[dict], seen: set[tuple[str, str]]) -> None:
    category = category_from_title(text)
    active = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            active = line in {"## 本次练习", "## 练习小对话"}
            continue
        if not active or not line.startswith("- "):
            continue
        for segment in line[2:].split("；"):
            match = PIPE_ENTRY_RE.match(segment.strip())
            if not match:
                continue
            meaning, thai, pinyin = [part.strip(" “”。") for part in match.groups()]
            if THAI_RE.search(thai):
                item = {
                    "source": path.name,
                    "category": category,
                    "kind": "练习句",
                    "meaning": meaning,
                    "thai": thai,
                    "pinyin": pinyin.rstrip("."),
                }
                add_item(
                    items,
                    seen,
                    add_pronunciation_rules(item),
                )


def item_words_from_lexicon(item: dict, lexicon: dict[str, dict]) -> list[dict]:
    if item.get("words"):
        return item["words"]
    if item["thai"] in PHRASE_WORD_OVERRIDES:
        return PHRASE_WORD_OVERRIDES[item["thai"]]

    thai = item["thai"]
    words: list[dict] = []
    index = 0
    word_keys = sorted(lexicon, key=len, reverse=True)
    punctuation = set(" \t\r\n,.!?？。……")

    while index < len(thai):
        char = thai[index]
        if char in punctuation:
            index += 1
            continue

        matched = None
        for key in word_keys:
            if thai.startswith(key, index):
                matched = lexicon[key]
                break

        if matched:
            words.append(matched)
            index += len(matched["thai"])
            continue

        latin = re.match(r"[A-Za-z]+", thai[index:])
        if latin:
            name = latin.group(0)
            words.append({"meaning": f"名字 {name}", "thai": name, "pinyin": name})
            index += len(name)
            continue

        return [
            {
                "meaning": item["meaning"],
                "thai": item["thai"],
                "pinyin": item["pinyin"],
            }
        ]

    return words or [
        {
            "meaning": item["meaning"],
            "thai": item["thai"],
            "pinyin": item["pinyin"],
        }
    ]


def annotate_words(items: list[dict], lexicon: dict[str, dict]) -> None:
    for manual_word in MANUAL_WORDS:
        add_word(lexicon, manual_word)

    for item in items:
        item["words"] = item_words_from_lexicon(item, lexicon)
        for word in item["words"]:
            if THAI_RE.search(word["thai"]):
                word["audio"] = word_audio_filename(word["thai"])


def collect_items() -> list[dict]:
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    lexicon: dict[str, dict] = {}
    for path in sorted(RECORD_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parse_table_records(path, text, items, seen)
        parse_block_records(path, text, items, seen, lexicon)

    for path in sorted(RECORD_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parse_practice_records(path, text, items, seen)

    annotate_words(items, lexicon)

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


def collect_audio_targets(items: list[dict]) -> list[dict]:
    targets: list[dict] = []
    seen_audio: set[str] = set()

    for item in items:
        if item["audio"] not in seen_audio:
            seen_audio.add(item["audio"])
            targets.append(
                {
                    "meaning": item["meaning"],
                    "thai": item["thai"],
                    "audio": item["audio"],
                }
            )

    for item in items:
        for word in item.get("words", []):
            audio = word.get("audio")
            if not audio or audio in seen_audio:
                continue
            seen_audio.add(audio)
            targets.append(
                {
                    "meaning": word["meaning"],
                    "thai": word["thai"],
                    "audio": audio,
                }
            )

    return targets


async def generate_audio(items: list[dict], overwrite: bool) -> None:
    import edge_tts

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    targets = collect_audio_targets(items)
    failures: list[dict] = []
    for index, item in enumerate(targets, 1):
        output = APP_DIR / item["audio"]
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and output.stat().st_size > 0 and not overwrite:
            continue
        if output.exists() and output.stat().st_size == 0:
            output.unlink()
        print(f"[{index}/{len(targets)}] -> {output.relative_to(AUDIO_DIR.parent)}")
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

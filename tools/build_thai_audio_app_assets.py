"""Build static data and MP3 files for the multilingual audio app."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD_ROOT = ROOT / "learning-records"
THAI_RECORD_DIR = RECORD_ROOT / "thai"
APP_DIR = ROOT / "thai-audio-app"
DATA_FILE = APP_DIR / "data" / "phrases.js"
AUDIO_DIR = APP_DIR / "audio"
VOICE = "th-TH-PremwadeeNeural"
LANGUAGES = {
    "thai": {
        "label": "泰语",
        "record_dir": THAI_RECORD_DIR,
        "target_field": "泰语",
        "roman_field": "拉丁拼音读音",
        "voice": VOICE,
    },
    "indonesian": {
        "label": "印尼语",
        "record_dir": RECORD_ROOT / "indonesian",
        "target_field": "印尼语",
        "roman_field": "拉丁读音",
        "voice": "id-ID-ArdiNeural",
    },
    "english": {
        "label": "英语",
        "record_dir": RECORD_ROOT / "english",
        "target_field": "English",
        "roman_field": "IPA",
        "voice": "en-US-JennyNeural",
    },
}
TTS_THAI_OVERRIDES = {
    "ฃ": "ขวด",
    "ฅ": "คน",
}
CATEGORY_LABELS = {
    "Greetings, Thanks, and Names": "基础问候、感谢和名字",
}

TABLE_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|")
FIELD_RE = re.compile(r"^(中文意思|泰语|印尼语|拉丁拼音读音|拉丁读音|简单日常泰语例句|简单日常印尼语例句|中文句意)：(.+)$")
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


def category_from_title(path: Path, text: str) -> str:
    prefix = path.stem.split("-", 1)[0]
    for line in text.splitlines():
        if line.startswith("# "):
            if "：" in line:
                category = line.split("：", 1)[1].strip()
                label = CATEGORY_LABELS.get(category, category)
                return f"{prefix} {label}" if prefix.isdigit() else label
            if ":" in line:
                category = line.split(":", 1)[1].strip()
                label = CATEGORY_LABELS.get(category, category)
                return f"{prefix} {label}" if prefix.isdigit() else label
            category = line[2:].strip()
            label = CATEGORY_LABELS.get(category, category)
            return f"{prefix} {label}" if prefix.isdigit() else label
    return "泰语学习"


def load_english_parser():
    spec = importlib.util.spec_from_file_location("english_lesson_parser", ROOT / "tools" / "english_lesson_parser.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load English lesson parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def language_config(language: str) -> dict:
    return LANGUAGES[language]


def record_dir(language: str) -> Path:
    return language_config(language)["record_dir"]


def target_field(language: str) -> str:
    return language_config(language)["target_field"]


def roman_field(language: str) -> str:
    return language_config(language)["roman_field"]


def target_has_language_text(language: str, target: str) -> bool:
    if language == "thai":
        return bool(THAI_RE.search(target))
    return bool(re.search(r"[A-Za-z]", target))


def normalize_item(language: str, item: dict) -> dict:
    target = item.get("target", item.get("thai", "")).strip()
    item["language"] = language
    item["target"] = target
    # Keep the historical key so existing tests and UI code can migrate gradually.
    item["thai"] = target
    return item


def audio_filename(language: str, index: int, target: str) -> str:
    digest_source = target if language == "thai" else f"{language}:{target}"
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:10]
    name = f"{index:03d}-{digest}.mp3"
    if language == "thai":
        return name
    return f"{language}/{name}"


def word_audio_filename(language: str, target: str) -> str:
    digest_source = target if language == "thai" else f"{language}:{target}"
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:10]
    if language == "thai":
        return f"word-audio/{digest}.mp3"
    return f"word-audio/{language}/{digest}.mp3"


def add_item(items: list[dict], seen: set[tuple[str, str]], item: dict) -> None:
    key = (item["language"], item["target"], item["meaning"])
    if key in seen:
        return
    seen.add(key)
    items.append(item)


def add_word(lexicon: dict[str, dict], word: dict) -> None:
    target = word.get("target", word.get("thai", "")).strip()
    if not target:
        return
    lexicon.setdefault(
        target,
        {
            "meaning": word["meaning"].strip().rstrip("。"),
            "target": target,
            "thai": target,
            "pinyin": word["pinyin"].strip().rstrip(".?？"),
        },
    )


def parse_breakdown_words(text: str) -> list[dict]:
    words: list[dict] = []
    for target, pinyin, meaning in BREAKDOWN_WORD_RE.findall(text):
        target = target.strip()
        if not target:
            continue
        words.append(
            {
                "meaning": meaning.strip().rstrip("。"),
                "target": target,
                "thai": target,
                "pinyin": pinyin.strip().rstrip(".?？"),
            }
        )
    return words


def has_any(text: str, chars: set[str]) -> bool:
    return any(char in chars for char in text)


HIGH_CONSONANT_WORD_RULES = [
    (
        "สวัสดี",
        "สวัสดี 里的 สะ 读 sà。原因：辅音类别=高辅音 ส；声调符号=无；音节类型=短元音、无尾辅音的死音节；规则结果=高辅音 + 无声调符号 + 短死音节，读第 2 调低调。",
    ),
    (
        "สบายดี",
        "สบายดี 里的 สะ 读 sà。原因：辅音类别=高辅音 ส；声调符号=无；音节类型=短元音、无尾辅音的死音节；规则结果=高辅音 + 无声调符号 + 短死音节，读第 2 调低调。",
    ),
    (
        "ฉัน",
        "ฉัน 读 chǎn。原因：辅音类别=高辅音 ฉ；声调符号=无，ั 是短元音 a；音节类型=น 是 n 鼻音结尾，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ถุง",
        "ถุง 读 thǔng。原因：辅音类别=高辅音 ถ；声调符号=无；音节类型=ง 是 ng 鼻音结尾，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ผม",
        "ผม 读 phǒm。原因：辅音类别=高辅音 ผ；声调符号=无；音节类型=ม 是 m 鼻音结尾，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ฝน",
        "ฝน 读 fǒn。原因：辅音类别=高辅音 ฝ；声调符号=无；音节类型=น 是 n 鼻音结尾，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ฐาน",
        "ฐาน 读 thǎan。原因：辅音类别=高辅音 ฐ；声调符号=无；音节类型=长元音 aa + น 鼻音结尾，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ศาลา",
        "ศาลา 的 ศา 读 sǎa。原因：辅音类别=高辅音 ศ；声调符号=无；音节类型=长元音 aa 的开音节，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ฤๅษี",
        "ฤๅษี 的 ษี 读 sǐi。原因：辅音类别=高辅音 ษ；声调符号=无；音节类型=长元音 ii 的开音节，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ของ",
        "ของ 读 khǎawng。原因：辅音类别=高辅音 ข；声调符号=无；音节类型=ง 是 ng 鼻音结尾，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ขอโทษ",
        "ขอโทษ 里的 ขอ 读 khǎaw。原因：辅音类别=高辅音 ข；声调符号=无；音节类型=长元音 aaw 的开音节，属于活音节；规则结果=高辅音 + 无声调符号 + 活音节，读第 5 调升调。",
    ),
    (
        "ขอบคุณ",
        "ขอบคุณ 里的 ขอบ 读 khàawp。原因：辅音类别=高辅音 ข；声调符号=无；音节类型=末尾 บ 是 p 收尾，属于死音节；规则结果=高辅音 + 无声调符号 + 死音节，读第 2 调低调。",
    ),
    (
        "ขวด",
        "ขวด 读 khùat。原因：辅音类别=高辅音 ข；声调符号=无；音节类型=末尾 ด 是 t 收尾，属于死音节；规则结果=高辅音 + 无声调符号 + 死音节，读第 2 调低调，末尾轻轻收住。",
    ),
]


def auto_pronunciation_rules(thai: str, pinyin: str) -> list[str]:
    rules: list[str] = []
    tone_hints: list[str] = []
    if has_any(pinyin, LOW_TONE_CHARS):
        tone_hints.append("à/è/ì/ò/ù＝第 2 调低调")
    if has_any(pinyin, FALLING_TONE_CHARS):
        tone_hints.append("â/ê/î/ô/û＝第 3 调降调")
    if has_any(pinyin, HIGH_TONE_CHARS):
        tone_hints.append("á/é/í/ó/ú＝第 4 调高调")
    if has_any(pinyin, RISING_TONE_CHARS):
        tone_hints.append("ǎ/ě/ǐ/ǒ/ǔ＝第 5 调升调")
    if tone_hints:
        rules.append(
            "快速读音提示："
            + "，".join(tone_hints)
            + "；真正判断声调时，要按“辅音类别 + 声调符号 + 活音节/死音节”来推。"
        )
    if "ครับ" in thai:
        rules.append("ครับ | khráp 是男性礼貌结尾；末尾 บ 是 p 收尾，发音时嘴唇轻轻闭住，不要加元音。")
    if "ไหม" in thai:
        rules.append("ไหม | mái 是问句里的“吗”；本记录先按学习时标注的 mái 练习，重点记它放在句末表示疑问。")
    for word, rule in HIGH_CONSONANT_WORD_RULES:
        if word in thai:
            rules.append(rule)
    if "ไข่" in thai:
        rules.append("ไข่ 读 khài。原因：辅音类别=高辅音 ข；声调符号=ไม้เอก ่；规则结果=高辅音 + ไม้เอก，读第 2 调低调。")
    if "ห้า" in thai:
        rules.append("ห้า 读 hâa。原因：辅音类别=高辅音 ห；声调符号=ไม้โท ้；规则结果=高辅音 + ไม้โท，读第 3 调降调。")

    return rules or ["先按拉丁拼音读；如果要判断泰语本身声调，再看辅音类别、声调符号，以及这个音节是活音节还是死音节。"]


def auto_indonesian_pronunciation_rules(target: str, pinyin: str) -> list[str]:
    rules = ["印尼语一般按拉丁字母拼读；先按拉丁读音分音节慢读，再连起来读。"]
    lowered = target.lower()
    if any(pair in lowered for pair in ("ga", "ka", "gu", "ku", "g", "k")):
        rules.append("注意 g / k 清浊对比：g 是浊音，声带震动更强；k 是清音，声带震动更弱。")
    if any(pair in lowered for pair in ("da", "ta", "di", "ti", "d", "t")):
        rules.append("注意 d / t 清浊对比：d 是浊音，t 是清音。")
    if any(pair in lowered for pair in ("ba", "pa", "bu", "pu", "b", "p")):
        rules.append("注意 b / p 清浊对比：b 是浊音，p 是清音。")
    return rules


def add_pronunciation_rules(item: dict, explicit_rule: str | None = None) -> dict:
    if explicit_rule:
        item["pronunciationRules"] = [explicit_rule.strip()]
        return item

    if item["language"] == "thai":
        rules = list(auto_pronunciation_rules(item["target"], item["pinyin"]))
    else:
        rules = list(auto_indonesian_pronunciation_rules(item["target"], item["pinyin"]))
    item["pronunciationRules"] = rules
    return item


def parse_table_records(language: str, path: Path, text: str, items: list[dict], seen: set[tuple[str, str]]) -> None:
    category = category_from_title(path, text)
    for line in text.splitlines():
        match = TABLE_RE.match(line)
        if not match:
            continue
        meaning, target, pinyin = [part.strip() for part in match.groups()]
        if meaning in {"中文意思", "---"} or target in {"泰语", "印尼语"} or pinyin in {"拉丁拼音读音", "拉丁读音"}:
            continue
        if not target_has_language_text(language, target):
            continue
        item = normalize_item(
            language,
            {
                "source": path.name,
                "category": category,
                "kind": "词句",
                "meaning": meaning,
                "target": target,
                "pinyin": pinyin.rstrip("."),
            },
        )
        add_item(
            items,
            seen,
            add_pronunciation_rules(item),
        )


def parse_block_records(
    language: str,
    path: Path,
    text: str,
    items: list[dict],
    seen: set[tuple[str, str]],
    lexicon: dict[str, dict],
) -> None:
    category = category_from_title(path, text)
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
        target = fields.get(target_field(language))
        pinyin = fields.get(roman_field(language))
        sentence = fields.get(f"简单日常{language_config(language)['label']}例句")
        sentence_meaning = fields.get("中文句意")
        pinyin_parts = BREAKDOWN_PINYIN_RE.findall(breakdown)
        if meaning and target and pinyin:
            word = {
                "meaning": meaning,
                "target": target,
                "thai": target,
                "pinyin": pinyin.rstrip("."),
            }
            add_word(lexicon, word)
            if sentence != target:
                explicit_word_rule = pronunciation_rule if pronunciation_rule and target in pronunciation_rule else None
                add_item(
                    items,
                    seen,
                    add_pronunciation_rules(
                        normalize_item(
                            language,
                            {
                                "source": path.name,
                                "category": category,
                                "kind": "词语",
                                **word,
                                "words": [word],
                            },
                        ),
                        explicit_word_rule,
                    ),
                )

        if sentence and sentence_meaning and pinyin_parts:
            words = parse_breakdown_words(breakdown)
            for word in words:
                add_word(lexicon, word)
            add_item(
                items,
                seen,
                add_pronunciation_rules(
                    normalize_item(
                        language,
                        {
                            "source": path.name,
                            "category": category,
                            "kind": "例句",
                            "meaning": sentence_meaning.rstrip("。"),
                            "target": sentence,
                            "pinyin": " ".join(pinyin_parts).rstrip("."),
                            "words": words,
                        },
                    ),
                    pronunciation_rule,
                ),
            )


def parse_practice_records(language: str, path: Path, text: str, items: list[dict], seen: set[tuple[str, str]]) -> None:
    category = category_from_title(path, text)
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
            meaning, target, pinyin = [part.strip(" “”。") for part in match.groups()]
            if target_has_language_text(language, target):
                item = normalize_item(
                    language,
                    {
                        "source": path.name,
                        "category": category,
                        "kind": "练习句",
                        "meaning": meaning,
                        "target": target,
                        "pinyin": pinyin.rstrip("."),
                    },
                )
                add_item(
                    items,
                    seen,
                    add_pronunciation_rules(item),
                )


def item_words_from_lexicon(item: dict, lexicon: dict[str, dict]) -> list[dict]:
    if item.get("words"):
        return item["words"]
    if item["language"] == "thai" and item["target"] in PHRASE_WORD_OVERRIDES:
        return PHRASE_WORD_OVERRIDES[item["thai"]]

    target = item["target"]
    words: list[dict] = []
    index = 0
    word_keys = sorted(lexicon, key=len, reverse=True)
    punctuation = set(" \t\r\n,.!?？。……")

    while index < len(target):
        char = target[index]
        if char in punctuation:
            index += 1
            continue

        matched = None
        for key in word_keys:
            if target.startswith(key, index):
                matched = lexicon[key]
                break

        if matched:
            words.append(matched)
            index += len(matched["target"])
            continue

        latin = re.match(r"[A-Za-z]+", target[index:])
        if latin:
            name = latin.group(0)
            words.append({"meaning": f"名字 {name}", "target": name, "thai": name, "pinyin": name})
            index += len(name)
            continue

        return [
            {
                "meaning": item["meaning"],
                "target": item["target"],
                "thai": item["target"],
                "pinyin": item["pinyin"],
            }
        ]

    return words or [
        {
            "meaning": item["meaning"],
            "target": item["target"],
            "thai": item["target"],
            "pinyin": item["pinyin"],
        }
    ]


def annotate_words(language: str, items: list[dict], lexicon: dict[str, dict]) -> None:
    if language == "thai":
        for manual_word in MANUAL_WORDS:
            add_word(lexicon, manual_word)

    for item in items:
        item["words"] = item_words_from_lexicon(item, lexicon)
        for word in item["words"]:
            word.setdefault("target", word["thai"])
            word.setdefault("thai", word["target"])
            if target_has_language_text(language, word["target"]):
                word["audio"] = word_audio_filename(language, word["target"])


def english_category_from_lesson(path: Path, lesson: dict) -> str:
    prefix = path.stem.split("-", 1)[0]
    label = lesson.get("categoryLabel") or lesson.get("category") or "English"
    return f"{prefix} {label}" if prefix.isdigit() else label


def english_word_from_target(word: dict) -> dict:
    return {
        "meaning": word["meaning_zh"],
        "target": word["word"],
        "thai": word["word"],
        "pinyin": word["ipa"],
        "partOfSpeech": word["part_of_speech"],
        "collocations": word.get("collocations", []),
        "audio": word_audio_filename("english", word["word"]),
    }


def collect_english_items() -> list[dict]:
    directory = record_dir("english")
    if not directory.exists():
        return []

    parser = load_english_parser()
    items: list[dict] = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lesson = parser.parse_english_lesson(path, text)
        errors = parser.validate_english_lesson(lesson, path.name)
        if errors:
            raise ValueError("\n".join(errors))

        words = [english_word_from_target(word) for word in lesson["targetWords"]]
        target = " ".join(f"{line['speaker']}: {line['text']}" for line in lesson["dialogue"])
        item = {
            "id": lesson["id"],
            "language": "english",
            "kind": "lesson",
            "source": lesson["source"],
            "category": english_category_from_lesson(path, lesson),
            "meaning": lesson["title"],
            "target": target,
            "thai": target,
            "pinyin": f"{lesson['track'].upper()} | {lesson['difficulty']}",
            "track": lesson["track"],
            "difficulty": lesson["difficulty"],
            "title": lesson["title"],
            "scenarioMemoryText": lesson["scenarioMemoryText"],
            "scenarioMemory": lesson["scenarioMemory"],
            "targetWords": lesson["targetWords"],
            "dialogue": lesson["dialogue"],
            "reviewPrompt": lesson["reviewPrompt"],
            "words": words,
        }
        items.append(item)

    for index, item in enumerate(items, 1):
        item["id"] = f"english-{index:03d}"
        item["audio"] = f"audio/{audio_filename('english', index, item['target'])}"
        for dialogue_index, line in enumerate(item["dialogue"], 1):
            line["audio"] = f"audio/{audio_filename('english', index * 100 + dialogue_index, line['text'])}"

    return items


def collect_language_items(language: str) -> list[dict]:
    items: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    lexicon: dict[str, dict] = {}
    directory = record_dir(language)
    if not directory.exists():
        return []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parse_table_records(language, path, text, items, seen)
        parse_block_records(language, path, text, items, seen, lexicon)

    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parse_practice_records(language, path, text, items, seen)

    annotate_words(language, items, lexicon)

    for index, item in enumerate(items, 1):
        item["id"] = f"{language}-{index:03d}"
        item["audio"] = f"audio/{audio_filename(language, index, item['target'])}"
    return items


def collect_items() -> list[dict]:
    items: list[dict] = []
    for language in LANGUAGES:
        if language == "english":
            items.extend(collect_english_items())
        else:
            items.extend(collect_language_items(language))
    return items


def write_data(items: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items, ensure_ascii=False, indent=2)
    languages = [
        {"id": key, "label": config["label"]}
        for key, config in LANGUAGES.items()
        if any(item["language"] == key for item in items)
    ]
    DATA_FILE.write_text(
        "window.THAI_AUDIO_APP_ITEMS = "
        + payload
        + ";\n"
        + "window.THAI_AUDIO_APP_META = {\n"
        + f"  count: {len(items)},\n"
        + f"  voice: {json.dumps(VOICE)},\n"
        + f"  languages: {json.dumps(languages, ensure_ascii=False)},\n"
        + "  format: \"中文意思 | 目标语言 | 拉丁读音\"\n"
        + "};\n",
        encoding="utf-8",
    )


def collect_audio_targets(items: list[dict]) -> list[dict]:
    targets: list[dict] = []
    seen_audio: set[str] = set()

    for item in items:
        if item["audio"] not in seen_audio:
            seen_audio.add(item["audio"])
            tts_target = TTS_THAI_OVERRIDES.get(item["target"], item["target"]) if item["language"] == "thai" else item["target"]
            targets.append(
                {
                    "meaning": item["meaning"],
                    "thai": item["thai"],
                    "target": item["target"],
                    "ttsThai": tts_target,
                    "ttsTarget": tts_target,
                    "language": item["language"],
                    "voice": language_config(item["language"])["voice"],
                    "audio": item["audio"],
                }
            )

    for item in items:
        for word in item.get("words", []):
            audio = word.get("audio")
            if not audio or audio in seen_audio:
                continue
            seen_audio.add(audio)
            language = item["language"]
            tts_target = TTS_THAI_OVERRIDES.get(word["target"], word["target"]) if language == "thai" else word["target"]
            targets.append(
                {
                    "meaning": word["meaning"],
                    "thai": word["thai"],
                    "target": word["target"],
                    "ttsThai": tts_target,
                    "ttsTarget": tts_target,
                    "language": language,
                    "voice": language_config(language)["voice"],
                    "audio": audio,
                }
            )

    for item in items:
        for line in item.get("dialogue", []):
            audio = line.get("audio")
            if not audio or audio in seen_audio:
                continue
            seen_audio.add(audio)
            targets.append(
                {
                    "meaning": line.get("meaning_zh", item["meaning"]),
                    "thai": line["text"],
                    "target": line["text"],
                    "ttsThai": line["text"],
                    "ttsTarget": line["text"],
                    "language": item["language"],
                    "voice": language_config(item["language"])["voice"],
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
                communicate = edge_tts.Communicate(item["ttsTarget"], item["voice"])
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
                            "target": item["target"],
                            "ttsThai": item["ttsThai"],
                            "ttsTarget": item["ttsTarget"],
                            "language": item["language"],
                            "voice": item["voice"],
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

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build_thai_audio_app_assets.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("thai_audio_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_english_parser():
    spec = importlib.util.spec_from_file_location(
        "english_lesson_parser", ROOT / "tools" / "english_lesson_parser.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_english_lesson_collects_scenario_words_and_dialogue(tmp_path):
    parser = load_english_parser()
    path = tmp_path / "001-cet4-campus-study.md"
    text = """# CET-4 Campus Study

```yaml
id: cet4-campus-study-001
language: english
track: cet4
category: campus-study
category_label_zh: 校园学习
difficulty: core
title_zh: 考试准备
scenario_memory_zh: 我先 prepare 学习计划，再 review 重点内容。
target_words:
  - word: prepare
    ipa: /prɪˈper/
    meaning_zh: 准备
    part_of_speech: v.
    collocations:
      - prepare for an exam
  - word: review
    ipa: /rɪˈvjuː/
    meaning_zh: 复习
    part_of_speech: v.
dialogue:
  - speaker: A
    text: Are you ready for the exam?
    meaning_zh: 你准备好考试了吗？
review_prompt_zh: 先听整段对话，再逐句跟读。
```
"""

    lesson = parser.parse_english_lesson(path, text)

    assert lesson["language"] == "english"
    assert lesson["track"] == "cet4"
    assert lesson["scenarioMemory"][0]["word"] == "prepare"
    assert lesson["targetWords"][0]["ipa"] == "/prɪˈper/"
    assert lesson["dialogue"][0]["speaker"] == "A"


def test_validate_english_lesson_requires_scenario_ipa_and_dialogue():
    parser = load_english_parser()
    errors = parser.validate_english_lesson(
        {
            "id": "broken",
            "language": "english",
            "track": "cet4",
            "category": "campus-study",
            "categoryLabel": "校园学习",
            "difficulty": "core",
            "title": "坏示例",
            "scenarioMemoryText": "",
            "scenarioMemory": [],
            "targetWords": [{"word": "prepare", "meaning_zh": "准备", "part_of_speech": "v."}],
            "dialogue": [],
            "reviewPrompt": "",
        },
        "broken.md",
    )

    message = " ".join(errors)
    assert "scenarioMemory" in message
    assert "ipa" in message
    assert "dialogue" in message


def test_english_starter_lesson_has_required_memory_dialogue_and_words():
    parser = load_english_parser()
    path = ROOT / "learning-records" / "english" / "001-cet4-campus-study.md"

    lesson = parser.parse_english_lesson(path, path.read_text(encoding="utf-8"))
    errors = parser.validate_english_lesson(lesson, path.name)

    assert errors == []
    assert len(lesson["targetWords"]) == 8
    assert "prepare" in lesson["scenarioMemoryText"]
    assert any(line["text"].startswith("Are you ready") for line in lesson["dialogue"])


def test_collect_items_adds_audio_to_thai_word_blocks_only():
    builder = load_builder()
    items = builder.collect_items()
    assert len(items) >= 444

    thai_words = [
        word
        for item in items
        for word in item.get("words", [])
        if builder.THAI_RE.search(word["thai"])
    ]
    assert thai_words
    assert all(word.get("audio", "").startswith("word-audio/") for word in thai_words)

    lucas_words = [
        word
        for item in items
        for word in item.get("words", [])
        if word["thai"] == "Lucas"
    ]
    assert lucas_words
    assert all("audio" not in word for word in lucas_words)


def test_word_audio_paths_are_reused_for_duplicate_thai_words():
    builder = load_builder()
    items = builder.collect_items()

    seen = {}
    for item in items:
        for word in item.get("words", []):
            if not builder.THAI_RE.search(word["thai"]):
                continue
            previous = seen.setdefault(word["thai"], word["audio"])
            assert word["audio"] == previous


def test_frontend_has_word_audio_playback_controls():
    app_js = (ROOT / "thai-audio-app" / "assets" / "app.js").read_text(encoding="utf-8")
    assert "playWord" in app_js
    assert "word-play-button" in app_js


def test_frontend_has_playback_speed_controls():
    index_html = (ROOT / "thai-audio-app" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "thai-audio-app" / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'id="speedSelect"' in index_html
    assert 'value="0.7"' in index_html
    assert "getPlaybackRate" in app_js
    assert ".playbackRate" in app_js


def test_collect_items_separates_thai_and_indonesian_records():
    builder = load_builder()
    items = builder.collect_items()

    thai_item = next(item for item in items if item["thai"] == "สวัสดี")
    indonesian_item = next(item for item in items if item["target"] == "Saya makan nasi.")

    assert thai_item["language"] == "thai"
    assert thai_item["id"].startswith("thai-")
    assert thai_item["category"].startswith("001 ")

    assert indonesian_item["language"] == "indonesian"
    assert indonesian_item["id"].startswith("indonesian-")
    assert indonesian_item["source"] == "001-basic-pronunciation-pronouns-sentences.md"
    assert indonesian_item["category"] == "001 基础发音、代词和简单句"
    assert indonesian_item["meaning"] == "我吃米饭"
    assert indonesian_item["pinyin"] == "sa-ya ma-kan na-si"
    assert [word["target"] for word in indonesian_item["words"]] == ["Saya", "makan", "nasi"]
    assert indonesian_item["audio"].startswith("audio/indonesian/")
    assert all(word["audio"].startswith("word-audio/indonesian/") for word in indonesian_item["words"])


def test_frontend_has_language_filter_before_category_filter():
    index_html = (ROOT / "thai-audio-app" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "thai-audio-app" / "assets" / "app.js").read_text(encoding="utf-8")

    language_start = index_html.index('id="languageSelect"')
    category_start = index_html.index('id="categorySelect"')

    assert language_start < category_start
    assert "languageSelect" in app_js
    assert "setupLanguages" in app_js


def test_frontend_has_guided_reading_controls():
    app_js = (ROOT / "thai-audio-app" / "assets" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "thai-audio-app" / "assets" / "styles.css").read_text(encoding="utf-8")

    assert "follow-button" in app_js
    assert "startGuidedReading" in app_js
    assert "guided-word-panel" in app_js
    assert "is-reading-current" in app_js
    assert ".guided-word-panel" in styles
    assert ".is-reading-current" in styles


def test_frontend_opens_tone_rule_summary_in_overlay_without_reflowing_cards():
    index_html = (ROOT / "thai-audio-app" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "thai-audio-app" / "assets" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "thai-audio-app" / "assets" / "styles.css").read_text(encoding="utf-8")

    trigger_start = index_html.index('id="toneGuideButton"')
    controls_start = index_html.index('<section class="controls"')

    assert trigger_start < controls_start
    assert '<details class="tone-guide"' not in index_html
    assert 'id="toneGuideDialog"' in index_html
    assert 'aria-haspopup="dialog"' in index_html
    assert "发音规则总表" in index_html
    assert "高辅音 + 活音节" in index_html
    assert "低辅音 + 短元音死音节" in index_html
    assert "活音节" in index_html
    assert "死音节" in index_html
    assert "showModal" in app_js
    assert "close()" in app_js
    assert ".tone-guide-dialog" in styles
    assert "position: fixed" in styles
    assert ".tone-guide" in styles


def test_sentence_that_is_also_the_main_phrase_keeps_split_words():
    builder = load_builder()
    items = builder.collect_items()
    item = next(item for item in items if item["thai"] == "ผมก็ถึงบ้านแล้วครับ")

    assert item["kind"] == "例句"
    assert [word["thai"] for word in item["words"]] == [
        "ผม",
        "ก็",
        "ถึง",
        "บ้าน",
        "แล้ว",
        "ครับ",
    ]


def test_record_008_new_sleep_phrase_keeps_split_words_and_rules():
    builder = load_builder()
    items = builder.collect_items()
    assert any(item["thai"] == "ผมง่วงนิดหน่อยครับ" for item in items)
    item = next(
        item
        for item in items
        if item["thai"] == "คุณพูดได้ดีมากแล้วครับ เก่งมากครับ"
    )

    assert item["source"] == "008-arrived-home-and-shower.md"
    assert [word["thai"] for word in item["words"]] == [
        "คุณ",
        "พูดได้",
        "ดีมาก",
        "แล้ว",
        "ครับ",
        "เก่งมาก",
        "ครับ",
    ]
    assert item["pronunciationRules"]


def test_record_008_loei_usage_table_is_collected():
    builder = load_builder()
    items = builder.collect_items()

    assert any(item["thai"] == "ไม่ดีเลย" for item in items)
    assert any(item["thai"] == "ผมง่วง ก็เลยนอน" for item in items)


def test_categories_include_document_number_prefixes():
    builder = load_builder()
    items = builder.collect_items()

    assert all(item["category"][:3].isdigit() for item in items)
    assert any(item["category"].startswith("001 ") for item in items)
    assert any(item["category"].startswith("008 ") for item in items)


def test_record_009_body_parts_are_collected_with_examples():
    builder = load_builder()
    items = builder.collect_items()
    head_item = next(item for item in items if item["thai"] == "ผมปวดหัวครับ")
    hand_item = next(item for item in items if item["thai"] == "นี่คือมือครับ")

    assert head_item["source"] == "009-body-parts.md"
    assert head_item["category"].startswith("009 ")
    assert [word["thai"] for word in head_item["words"]] == ["ผม", "ปวด", "หัว", "ครับ"]
    assert head_item["pronunciationRules"]
    assert hand_item["source"] == "009-body-parts.md"


def test_record_009_rules_explain_tone_reasoning():
    builder = load_builder()
    items = builder.collect_items()
    back_item = next(item for item in items if item["thai"] == "หลังเจ็บครับ")
    knee_item = next(item for item in items if item["thai"] == "เข่าเจ็บครับ")

    back_rules = " ".join(back_item["pronunciationRules"])
    knee_rules = " ".join(knee_item["pronunciationRules"])

    assert "原因：" in back_rules
    assert "辅音类别" in back_rules
    assert "声调符号" in back_rules
    assert "活音节" in back_rules
    assert "第 5 调升调" in back_rules
    assert "ห 前引字" in back_rules

    assert "原因：" in knee_rules
    assert "辅音类别" in knee_rules
    assert "声调符号" in knee_rules
    assert "ไม้เอก" in knee_rules
    assert "第 2 调低调" in knee_rules


def test_record_009_word_cards_keep_the_detailed_rule():
    builder = load_builder()
    items = builder.collect_items()
    back_word = next(
        item
        for item in items
        if item["source"] == "009-body-parts.md"
        and item["kind"] == "词语"
        and item["thai"] == "หลัง"
    )

    rules = " ".join(back_word["pronunciationRules"])
    assert "原因：" in rules
    assert "ห 前引字" in rules
    assert "活音节" in rules
    assert "第 5 调升调" in rules


def test_record_007_consonant_chart_marks_middle_high_and_low_classes():
    builder = load_builder()
    items = builder.collect_items()
    record_items = [item for item in items if item["source"] == "007-high-consonant-memory-sentences.md"]

    assert any(
        item["thai"] == "ก"
        and item["meaning"] == "中辅音：鸡字母"
        and item["pinyin"] == "gor gai"
        for item in record_items
    )
    assert any(
        item["thai"] == "ข"
        and item["meaning"] == "高辅音：蛋字母"
        and item["pinyin"] == "khor khai"
        for item in record_items
    )
    assert any(
        item["thai"] == "ค"
        and item["meaning"] == "低辅音：水牛字母"
        and item["pinyin"] == "khor khwai"
        for item in record_items
    )


def test_obsolete_consonant_audio_targets_use_pronounceable_memory_words():
    builder = load_builder()
    items = builder.collect_items()
    targets = builder.collect_audio_targets(items)

    obsolete_letter_targets = [
        target
        for target in targets
        if target["thai"] == "ฃ" and target["audio"].endswith("746142f4fa.mp3")
    ]

    assert obsolete_letter_targets
    assert all(target["ttsThai"] == "ขวด" for target in obsolete_letter_targets)


def test_record_007_vowel_cards_are_collected_for_audio_practice():
    builder = load_builder()
    items = builder.collect_items()
    record_items = [item for item in items if item["source"] == "007-high-consonant-memory-sentences.md"]

    assert any(
        item["thai"] == "อะ"
        and item["meaning"] == "元音：短 a，符号 -ะ"
        and item["pinyin"] == "a"
        for item in record_items
    )
    assert any(
        item["thai"] == "อา"
        and item["meaning"] == "元音：长 aa，符号 -า"
        and item["pinyin"] == "aa"
        for item in record_items
    )
    assert any(
        item["thai"] == "เอีย"
        and item["meaning"] == "元音：复合 ia，符号 เ-ีย"
        and item["pinyin"] == "ia"
        for item in record_items
    )

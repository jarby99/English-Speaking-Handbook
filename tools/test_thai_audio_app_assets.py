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


def test_collect_items_adds_audio_to_thai_word_blocks_only():
    builder = load_builder()
    items = builder.collect_items()
    assert len(items) >= 400

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


def test_frontend_has_guided_reading_controls():
    app_js = (ROOT / "thai-audio-app" / "assets" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "thai-audio-app" / "assets" / "styles.css").read_text(encoding="utf-8")

    assert "follow-button" in app_js
    assert "startGuidedReading" in app_js
    assert "guided-word-panel" in app_js
    assert "is-reading-current" in app_js
    assert ".guided-word-panel" in styles
    assert ".is-reading-current" in styles


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

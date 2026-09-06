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
    assert len(items) == 369

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

# English Vocabulary Scenario App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an English vocabulary scenario-learning mode where CET-4, CET-6, and IELTS words are grouped into lessons with Chinese scenario memory paragraphs, IPA, audio, word breakdown, and English dialogues.

**Architecture:** Reuse the existing static multilingual audio app and generator pipeline. Add an English lesson schema under `learning-records/english/`, parse it into lesson-shaped frontend data, then render English lessons with a specialized card layout while preserving the current Thai and Indonesian card behavior.

**Tech Stack:** Python asset generator and pytest tests; vanilla HTML/CSS/JavaScript frontend; pre-generated MP3 assets; Capacitor Android packaging.

**Spec:** `docs/superpowers/specs/2026-09-28-english-vocabulary-scenario-app-design.md`

## Global Constraints

- Keep the first version static: no backend, login, cloud sync, payment, or online AI chat.
- Preserve existing Thai and Indonesian content, filters, audio, and APK packaging.
- English lessons must be grouped by exam track, category, and difficulty.
- Each English lesson must include a Chinese scenario memory paragraph with highlighted English target words.
- Each English lesson must include 8 to 15 target words unless a test fixture explicitly uses a smaller minimal case.
- Each target word must include `word`, `ipa`, `meaning_zh`, and `part_of_speech`.
- English examples and dialogues must be self-written for this app, not copied from paid lists, short-video captions, textbooks, or proprietary materials.
- Full CET-4, CET-6, and IELTS import must be handled as later batch content work after a legally usable source list is selected.

## Review Focus

- Existing Thai/Indonesian records still render as current phrase cards: Task 4 tests `renderPhraseCard` and data compatibility.
- English lessons with missing IPA or missing scenario memory fail validation: Task 1 tests schema validation errors.
- Search finds English lessons by Chinese meaning, English word, IPA, track, category, and dialogue text: Task 4 tests search haystack behavior.
- Audio generation creates distinct English word, sentence, and dialogue paths without colliding with Thai/Indonesian paths: Task 3 tests filenames.
- The UI remains usable when an English lesson has many target words: Task 4 tests the lesson card contains a scroll-safe word group and does not nest cards.

---

## File Structure

- Create `learning-records/english/001-cet4-campus-study.md`: first self-written English lesson source using the new format.
- Create `tools/english_lesson_parser.py`: focused parser and validator for English lesson Markdown/YAML-like source blocks.
- Modify `tools/build_thai_audio_app_assets.py`: register English as a language, collect English lessons, add lesson audio metadata, and write combined data.
- Modify `tools/test_thai_audio_app_assets.py`: add parser, generator, and frontend assertions while preserving existing tests.
- Modify `thai-audio-app/index.html`: add English-specific filter controls and lesson template regions.
- Modify `thai-audio-app/assets/app.js`: split phrase rendering from English lesson rendering, add track filtering, scenario highlighting, dialogue playback, and English search support.
- Modify `thai-audio-app/assets/styles.css`: add responsive styling for scenario memory, highlighted English words, target word groups, and dialogue rows.

## Task 1: English Lesson Parser and Validation

**Files:**
- Create: `tools/english_lesson_parser.py`
- Test: `tools/test_thai_audio_app_assets.py`

**Interfaces:**
- Produces: `parse_english_lesson(path: Path, text: str) -> dict`
- Produces: `validate_english_lesson(lesson: dict, source: str) -> list[str]`
- Produces lesson keys: `id`, `language`, `track`, `category`, `categoryLabel`, `difficulty`, `title`, `scenarioMemory`, `targetWords`, `dialogue`, `reviewPrompt`, `source`

- [ ] **Step 1: Write failing parser tests**

Add `test_parse_english_lesson_collects_scenario_words_and_dialogue()` with a minimal source containing:

```python
lesson = parser.parse_english_lesson(path, text)
assert lesson["language"] == "english"
assert lesson["track"] == "cet4"
assert lesson["scenarioMemory"][0]["word"] == "prepare"
assert lesson["targetWords"][0]["ipa"] == "/prɪˈper/"
assert lesson["dialogue"][0]["speaker"] == "A"
```

Add `test_validate_english_lesson_requires_scenario_ipa_and_dialogue()` asserting validation messages include `scenarioMemory`, `ipa`, and `dialogue` for incomplete data.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_parse_english_lesson_collects_scenario_words_and_dialogue tools/test_thai_audio_app_assets.py::test_validate_english_lesson_requires_scenario_ipa_and_dialogue -v`

Expected: FAIL because `tools.english_lesson_parser` does not exist.

- [ ] **Step 3: Implement `tools/english_lesson_parser.py`**

Use standard-library parsing only. Accept a Markdown file with a fenced `yaml` block as the machine-readable source. Validate required fields and preserve Chinese text as UTF-8.

- [ ] **Step 4: Run parser tests to verify they pass**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_parse_english_lesson_collects_scenario_words_and_dialogue tools/test_thai_audio_app_assets.py::test_validate_english_lesson_requires_scenario_ipa_and_dialogue -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/english_lesson_parser.py tools/test_thai_audio_app_assets.py
git commit -m "Add English lesson parser"
```

## Task 2: Starter English Scenario Lesson Source

**Files:**
- Create: `learning-records/english/001-cet4-campus-study.md`
- Test: `tools/test_thai_audio_app_assets.py`

**Interfaces:**
- Consumes: `parse_english_lesson(path: Path, text: str) -> dict`
- Produces: a self-written CET-4 campus lesson with Chinese scenario memory, 8 target words, and English dialogue.

- [ ] **Step 1: Write failing content test**

Add `test_english_starter_lesson_has_required_memory_dialogue_and_words()`:

```python
lesson = parser.parse_english_lesson(path, path.read_text(encoding="utf-8"))
errors = parser.validate_english_lesson(lesson, path.name)
assert errors == []
assert len(lesson["targetWords"]) == 8
assert "prepare" in lesson["scenarioMemoryText"]
assert any(line["text"].startswith("Are you ready") for line in lesson["dialogue"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_english_starter_lesson_has_required_memory_dialogue_and_words -v`

Expected: FAIL because the source file does not exist.

- [ ] **Step 3: Create `learning-records/english/001-cet4-campus-study.md`**

Use the spec's campus exam lesson. Include these words: `prepare`, `review`, `exam`, `pressure`, `improve`, `result`, `efficient`, `confident`. Include IPA, Chinese meaning, part of speech, and collocations. Include a Chinese scenario memory paragraph that embeds every target word inline.

- [ ] **Step 4: Run content test to verify it passes**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_english_starter_lesson_has_required_memory_dialogue_and_words -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add learning-records/english/001-cet4-campus-study.md tools/test_thai_audio_app_assets.py
git commit -m "Add starter English scenario lesson"
```

## Task 3: Generator Integration and Audio Metadata

**Files:**
- Modify: `tools/build_thai_audio_app_assets.py`
- Modify: `tools/test_thai_audio_app_assets.py`

**Interfaces:**
- Consumes: `parse_english_lesson(path: Path, text: str) -> dict`
- Produces English frontend items with `language: "english"`, `kind: "lesson"`, `track`, `difficulty`, `scenarioMemory`, `targetWords`, `dialogue`, `words`, and `audio`.
- Produces English audio paths: `audio/english/<index>-<digest>.mp3`, `word-audio/english/<digest>.mp3`, and sentence audio path values inside dialogue rows.

- [ ] **Step 1: Write failing generator tests**

Add `test_collect_items_includes_english_lesson_with_track_and_scenario()`:

```python
items = builder.collect_items()
lesson = next(item for item in items if item["language"] == "english" and item["kind"] == "lesson")
assert lesson["track"] == "cet4"
assert lesson["category"].startswith("001 ")
assert lesson["targetWords"][0]["word"] == "prepare"
assert lesson["words"][0]["target"] == "prepare"
assert lesson["audio"].startswith("audio/english/")
assert lesson["dialogue"][0]["audio"].startswith("audio/english/")
```

Add `test_english_word_audio_paths_are_language_scoped()` asserting every English word audio starts with `word-audio/english/`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_collect_items_includes_english_lesson_with_track_and_scenario tools/test_thai_audio_app_assets.py::test_english_word_audio_paths_are_language_scoped -v`

Expected: FAIL because English is not registered in the builder.

- [ ] **Step 3: Modify the builder**

Add `english` to `LANGUAGES` with label `英语`, record directory `learning-records/english`, and a US English voice such as `en-US-JennyNeural`. Add a `collect_english_items()` path that uses the parser and normalizes target words into existing `words` shape for frontend compatibility.

- [ ] **Step 4: Run generator tests**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_collect_items_includes_english_lesson_with_track_and_scenario tools/test_thai_audio_app_assets.py::test_english_word_audio_paths_are_language_scoped -v`

Expected: PASS.

- [ ] **Step 5: Run full builder tests**

Run: `python -m pytest tools/test_thai_audio_app_assets.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/build_thai_audio_app_assets.py tools/test_thai_audio_app_assets.py
git commit -m "Generate English scenario lesson data"
```

## Task 4: English Lesson Frontend Rendering

**Files:**
- Modify: `thai-audio-app/index.html`
- Modify: `thai-audio-app/assets/app.js`
- Modify: `thai-audio-app/assets/styles.css`
- Test: `tools/test_thai_audio_app_assets.py`

**Interfaces:**
- Consumes English lesson item shape from Task 3.
- Produces UI sections: `.scenario-memory`, `.scenario-token`, `.lesson-word-list`, `.dialogue-list`, `.dialogue-play-button`, `.track-filter`.
- Preserves existing phrase card template for Thai and Indonesian items.

- [ ] **Step 1: Write failing frontend tests**

Add `test_frontend_has_english_lesson_layout_and_track_filter()`:

```python
assert 'id="trackSelect"' in index_html
assert "renderEnglishLessonCard" in app_js
assert "renderPhraseCard" in app_js
assert "scenario-memory" in app_js
assert "dialogue-play-button" in app_js
assert ".scenario-token" in styles
```

Add `test_frontend_search_includes_english_dialogue_and_scenario()` asserting `scenarioMemory`, `targetWords`, and `dialogue` are included in the search haystack.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_frontend_has_english_lesson_layout_and_track_filter tools/test_thai_audio_app_assets.py::test_frontend_search_includes_english_dialogue_and_scenario -v`

Expected: FAIL because the frontend does not have English lesson rendering.

- [ ] **Step 3: Modify `index.html`**

Add a track filter select with options `全部`, `四级`, `六级`, `雅思`; keep it useful only for English by disabling or hiding it for Thai/Indonesian in JavaScript. Add template elements only if they simplify the DOM; otherwise create English lesson DOM in `app.js`.

- [ ] **Step 4: Modify `app.js`**

Add `renderEnglishLessonCard(item)` and keep existing card code as `renderPhraseCard(item)`. In English cards, render Chinese scenario memory with highlighted target words, then word breakdown, then English dialogue rows with sentence play buttons and whole lesson playback.

- [ ] **Step 5: Modify `styles.css`**

Style English lesson cards with stable card dimensions, readable scenario text, highlighted word tokens, compact word rows, and dialogue rows. Keep mobile layout single-column and avoid nested card styling.

- [ ] **Step 6: Run frontend tests**

Run: `python -m pytest tools/test_thai_audio_app_assets.py::test_frontend_has_english_lesson_layout_and_track_filter tools/test_thai_audio_app_assets.py::test_frontend_search_includes_english_dialogue_and_scenario -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add thai-audio-app/index.html thai-audio-app/assets/app.js thai-audio-app/assets/styles.css tools/test_thai_audio_app_assets.py
git commit -m "Render English scenario lessons"
```

## Task 5: Asset Generation, Static Verification, and Android Sync

**Files:**
- Modify: `thai-audio-app/data/phrases.js`
- Create/modify: generated English MP3 files under `thai-audio-app/audio/english/` and `thai-audio-app/word-audio/english/`
- Modify: Android synced assets under `android/app/src/main/assets/public/`

**Interfaces:**
- Consumes generator and frontend from Tasks 3 and 4.
- Produces generated app data and synchronized Android assets.

- [ ] **Step 1: Run full test suite before generation**

Run: `python -m pytest tools/test_thai_audio_app_assets.py -v`

Expected: PASS.

- [ ] **Step 2: Generate static app assets**

Run: `python tools/build_thai_audio_app_assets.py`

Expected: output reports English items and no generation errors. If TTS service or network is unavailable, record the exact failure and do not claim audio generation succeeded.

- [ ] **Step 3: Check generated JavaScript syntax**

Run: `node --check thai-audio-app/assets/app.js`

Expected: no syntax errors.

- [ ] **Step 4: Sync Android assets**

Run: `npm.cmd run android:sync`

Expected: Capacitor sync completes successfully.

- [ ] **Step 5: Verify Git only contains intended generated changes**

Run: `git status --short`

Expected: changes are limited to English docs/source, generator/tests/frontend, generated app data/audio, and Android synced assets.

- [ ] **Step 6: Commit**

```bash
git add learning-records/english thai-audio-app android tools
git commit -m "Build English scenario vocabulary app"
```

## Task 6: Packaging and Push

**Files:**
- No source changes expected unless packaging metadata requires an update.

**Interfaces:**
- Consumes synced Android app from Task 5.
- Produces pushed `main` commit and, if local Java is available, a debug APK; otherwise relies on GitHub Actions.

- [ ] **Step 1: Check working tree**

Run: `git status --short --branch`

Expected: local `main` is clean except being ahead of `origin/main`.

- [ ] **Step 2: Try local Android debug build**

Run: `npm.cmd run android:build:debug`

Expected: PASS and APK path is reported. If Java/JDK is unavailable, record the exact failure and continue to push so GitHub Actions can build.

- [ ] **Step 3: Push main**

Run: `git push origin main`

Expected: push succeeds.

- [ ] **Step 4: Verify remote contains the final commit**

Run: `git ls-remote origin refs/heads/main`

Expected: remote commit matches local `HEAD`.

- [ ] **Step 5: Commit status report**

Report final commit, whether local APK build succeeded, whether push succeeded, and whether GitHub Actions should be used for release APK if local Java is unavailable.

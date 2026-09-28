# English Vocabulary Scenario App Design

## Goal

Build an English vocabulary learning module for CET-4, CET-6, and IELTS learners. The app should help the learner remember groups of related words through small scene dialogues, not isolated word cards.

The first implementation should reuse the existing static audio app direction: local data, generated audio files, and Android packaging. A backend is not required for the first version.

## Learner Experience

The learner should be able to:

- Switch to English from the existing language selector.
- Choose CET-4, CET-6, or IELTS.
- Learn words by category and difficulty, from easy to hard.
- Study a small group of related words as one memory unit.
- Read a short scene dialogue that naturally uses the target word group.
- Tap any word, sentence, or dialogue to hear audio.
- See IPA phonetics for English words and sentences where useful.
- Review word chunks, Chinese meanings, common collocations, and example sentences.
- Mark words or lessons as known, needs review, or favorite using local device storage.

## Content Principle

The content unit is a word group lesson, not a single word.

Each lesson should contain:

- Exam track: CET-4, CET-6, IELTS, or shared.
- Difficulty level: beginner, core, advanced, academic, or high-value writing/speaking replacement.
- Topic category: campus, daily life, travel, work, technology, environment, health, economy, society, education, emotion, personality, opinion, chart writing, IELTS speaking, IELTS listening, IELTS reading, IELTS writing.
- 8 to 15 related target words.
- One short scene dialogue using the target words.
- Word breakdown with Chinese meaning, IPA, part of speech, collocations, and audio.
- Sentence breakdown with Chinese translation and audio.
- A short review prompt.

Words should be grouped by meaning and use case first, then sorted by difficulty inside the group.

## Difficulty Ordering

The app should order lessons and words with these rules:

1. High-frequency concrete words first.
2. Common spoken and writing words next.
3. CET-4 core words before CET-6 abstract words.
4. CET-6 abstract and academic words before IELTS topic-specific words.
5. IELTS writing and reading academic words later.
6. Advanced replacement words appear after the basic word they replace.

Example:

- important -> significant -> essential -> crucial
- help -> assist -> support -> facilitate
- problem -> issue -> challenge -> obstacle

## Top-Level Structure

```text
English
+-- CET-4
|   +-- High-frequency basics
|   +-- Campus and study
|   +-- Daily life
|   +-- Feelings and personality
|   +-- Work and society
|   +-- Technology and internet
|   +-- Environment and health
|   +-- Basic opinion writing
+-- CET-6
|   +-- CET-4 upgrade words
|   +-- Academic expression
|   +-- Social issues
|   +-- Economy and business
|   +-- Science and technology
|   +-- Culture and education
|   +-- Advanced writing replacements
+-- IELTS
    +-- Speaking Part 1 common topics
    +-- Speaking Part 2 people, places, objects, and experiences
    +-- Listening scenes
    +-- Reading academic words
    +-- Writing Task 1 chart language
    +-- Writing Task 2 education, technology, environment, government, society
```

The UI category labels can be Chinese, but the data should preserve stable English IDs for filtering and future tooling.

## Lesson Example

```text
Track: CET-4
Category: Campus and study
Difficulty: Core

Word group:
- prepare /prɪˈper/ 准备
- review /rɪˈvjuː/ 复习
- exam /ɪɡˈzæm/ 考试
- pressure /ˈpreʃər/ 压力
- improve /ɪmˈpruːv/ 提高，改善
- result /rɪˈzʌlt/ 结果，成绩
- efficient /ɪˈfɪʃnt/ 有效率的
- confident /ˈkɑːnfɪdənt/ 有信心的

Scene dialogue:
A: Are you ready for the exam?
B: Not yet. I still need to review more.
A: Don't put too much pressure on yourself.
B: I know, but I want to improve my result.
A: Try to make your study plan more efficient.
B: Good idea. That will make me feel more confident.
```

The app should show this as one learning card or lesson view, with separate play buttons for each word, each sentence, and the whole dialogue.

## Data Model

Add an English source format under `learning-records/english/`.

Recommended source structure:

```yaml
id: cet4-campus-study-001
language: english
track: cet4
category: campus-study
category_label_zh: 校园学习
difficulty: core
title_zh: 考试准备
target_words:
  - word: prepare
    ipa: /prɪˈper/
    meaning_zh: 准备
    part_of_speech: v.
    collocations:
      - prepare for an exam
      - prepare a plan
  - word: review
    ipa: /rɪˈvjuː/
    meaning_zh: 复习
    part_of_speech: v./n.
dialogue:
  - speaker: A
    text: Are you ready for the exam?
    meaning_zh: 你准备好考试了吗？
  - speaker: B
    text: Not yet. I still need to review more.
    meaning_zh: 还没有。我还需要多复习。
review_prompt_zh: 先听整段对话，再逐句跟读，最后回忆本组单词。
```

The generated frontend data should flatten this into searchable cards while preserving the lesson grouping.

## Audio Design

The first version should use pre-generated static audio:

- Word audio for each target word.
- Sentence audio for each dialogue sentence.
- Full dialogue audio assembled or generated separately.
- Normal speed and browser-controlled slow playback.

The app can continue using browser playback rate for slow audio first. If slow playback quality is not good enough, a later version can generate separate slow MP3 files.

Recommended English voices:

- US English voice for CET and IELTS by default.
- Optional UK English voice later for IELTS listening contrast.

## IPA and Pronunciation

Every word should include IPA.

For complete beginner friendliness, word cards should show:

- Word spelling.
- IPA.
- Chinese meaning.
- Syllable split when useful.
- Stress marker explanation when useful.

Example:

```text
environment
/ɪnˈvaɪrənmənt/
重音在第二部分：vi
中文：环境
```

The first version should keep pronunciation guidance short. It should not try to teach the full English phonetic system inside every card.

## App UI Changes

The current app already supports language switching, categories, search, speed control, repeat playback, word breakdown, and static audio. English should reuse these controls but add an English-specific lesson view.

Required UI additions:

- Language option: English.
- Exam filter: All, CET-4, CET-6, IELTS.
- Lesson cards that group multiple words and one scene dialogue.
- Word group panel below each dialogue.
- Per-word play button.
- Per-sentence play button.
- Whole-dialogue follow-reading button.
- Local review controls: known, review later, favorite.

Category options should include document or lesson sequence numbers when useful, matching the existing learning-record organization style.

## Import and Word Source

The app needs a legally usable vocabulary source. Individual English words are not copyrightable, but copied proprietary lists, example sentences, and textbook dialogues may be copyrighted.

Acceptable approaches:

- User-provided word lists.
- Public or self-created CET-4, CET-6, and IELTS word lists.
- Self-written example sentences and dialogues generated specifically for this app.

The implementation should keep source attribution notes when a list source is used.

## First Milestone

Build a small but complete English slice before importing all words:

- 3 tracks: CET-4, CET-6, IELTS.
- 3 categories per track.
- 3 lessons per category.
- 8 to 15 words per lesson.
- Word audio, sentence audio, and dialogue playback.
- Search and category filtering.
- Local review state.

This creates the full structure and verifies the learning experience before importing the full vocabulary set.

## Full Vocabulary Expansion

After the first milestone works, import full word coverage in batches:

1. CET-4 full vocabulary grouped into lessons.
2. CET-6 full vocabulary grouped into lessons.
3. IELTS core vocabulary grouped by speaking, listening, reading, and writing use cases.
4. Advanced replacement-word lessons for writing and speaking.

Each import batch should run validation:

- Every word has Chinese meaning.
- Every word has IPA.
- Every lesson has 8 to 15 target words unless there is a clear reason.
- Every lesson has a scene dialogue.
- Every word appears in the lesson dialogue or examples.
- Every playable item has a generated audio file.

## Non-Goals for First Version

The first version should not include:

- Backend login.
- Cloud sync.
- Online AI chat.
- Payment.
- Social features.
- Automatic daily push notifications.

These can be added later after the static learning flow is useful.

## Open Decision Before Implementation Plan

The only major product decision left is the first content source:

- Use a small self-created starter set first, then import full lists.
- Or import user-provided full CET-4, CET-6, and IELTS lists immediately.

Recommended choice: start with a small self-created starter set to validate the app flow, then import the full lists in controlled batches.

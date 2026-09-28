(function () {
  const items = window.THAI_AUDIO_APP_ITEMS || [];
  const meta = window.THAI_AUDIO_APP_META || {};
  const grid = document.querySelector("#phraseGrid");
  const template = document.querySelector("#phraseCardTemplate");
  const searchInput = document.querySelector("#searchInput");
  const languageSelect = document.querySelector("#languageSelect");
  const trackSelect = document.querySelector("#trackSelect");
  const categorySelect = document.querySelector("#categorySelect");
  const speedSelect = document.querySelector("#speedSelect");
  const repeatButton = document.querySelector("#repeatButton");
  const toneGuideButton = document.querySelector("#toneGuideButton");
  const toneGuideDialog = document.querySelector("#toneGuideDialog");
  const toneGuideTitle = document.querySelector("#toneGuideTitle");
  const toneGuideCloseButton = document.querySelector("#toneGuideCloseButton");
  const nowPlaying = document.querySelector("#nowPlaying");
  const itemCount = document.querySelector("#itemCount");

  let activeAudio = null;
  let activeCard = null;
  let activeButton = null;
  let activeFollowButton = null;
  let activeGuidedPanel = null;
  let activeGuidedRows = [];
  let guidedRunId = 0;
  let repeat = false;

  const languageLabels = Object.fromEntries(
    (meta.languages || []).map((language) => [language.id, language.label])
  );
  const reviewStorageKey = "englishScenarioReviewState";

  function itemTarget(item) {
    return item.target || item.thai;
  }

  function loadReviewState() {
    try {
      return JSON.parse(window.localStorage.getItem(reviewStorageKey) || "{}");
    } catch {
      return {};
    }
  }

  function saveReviewState(state) {
    window.localStorage.setItem(reviewStorageKey, JSON.stringify(state));
  }

  function toggleReviewState(itemId, key, button) {
    const state = loadReviewState();
    state[itemId] = state[itemId] || {};
    state[itemId][key] = !state[itemId][key];
    saveReviewState(state);
    button.setAttribute("aria-pressed", String(state[itemId][key]));
  }

  function uniqueLanguages() {
    const languages = Array.from(new Set(items.map((item) => item.language || "thai")));
    return languages.length > 0 ? languages : ["thai"];
  }

  function languageLabel(language) {
    return languageLabels[language] || language;
  }

  function currentLanguage() {
    return languageSelect.value || uniqueLanguages()[0];
  }

  function currentTrack() {
    return trackSelect ? trackSelect.value || "all" : "all";
  }

  function itemsForLanguage(language) {
    return items.filter((item) => (item.language || "thai") === language);
  }

  function setupLanguages() {
    languageSelect.innerHTML = "";
    uniqueLanguages().forEach((language) => {
      const option = document.createElement("option");
      option.value = language;
      option.textContent = languageLabel(language);
      languageSelect.appendChild(option);
    });
  }

  function uniqueCategories(language) {
    return ["全部", ...Array.from(new Set(itemsForLanguage(language).map((item) => item.category)))];
  }

  function setupCategories() {
    categorySelect.innerHTML = "";
    uniqueCategories(currentLanguage()).forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      categorySelect.appendChild(option);
    });
  }

  function updateTrackFilterVisibility() {
    if (!trackSelect) return;
    const label = trackSelect.closest("label");
    const isEnglish = currentLanguage() === "english";
    trackSelect.disabled = !isEnglish;
    if (label) {
      label.hidden = !isEnglish;
    }
    if (!isEnglish) {
      trackSelect.value = "all";
    }
  }

  function matches(item, query, language, category, track) {
    const inLanguage = (item.language || "thai") === language;
    const inCategory = category === "全部" || item.category === category;
    const inTrack = language !== "english" || track === "all" || item.track === track;
    const words = (item.words || [])
      .map((word) => [word.meaning, itemTarget(word), word.pinyin, word.partOfSpeech, (word.collocations || []).join(" ")].join(" "))
      .join(" ");
    const targetWords = (item.targetWords || [])
      .map((word) => [word.word, word.ipa, word.meaning_zh, word.part_of_speech, (word.collocations || []).join(" ")].join(" "))
      .join(" ");
    const scenarioText = [item.scenarioMemoryText, ...(item.scenarioMemory || []).map((entry) => entry.word)].join(" ");
    const dialogueText = (item.dialogue || [])
      .map((line) => [line.speaker, line.text, line.meaning_zh].join(" "))
      .join(" ");
    const rules = (item.pronunciationRules || []).join(" ");
    const haystack = [
      item.meaning,
      item.title,
      itemTarget(item),
      item.pinyin,
      item.kind,
      item.category,
      item.track,
      item.difficulty,
      words,
      targetWords,
      scenarioText,
      dialogueText,
      rules,
    ]
      .join(" ")
      .toLowerCase();
    return inLanguage && inCategory && inTrack && haystack.includes(query);
  }

  function getPlaybackRate() {
    const rate = Number.parseFloat(speedSelect.value);
    return Number.isFinite(rate) && rate > 0 ? rate : 1;
  }

  function getFollowPauseMs() {
    const rate = getPlaybackRate();
    if (rate <= 0.7) {
      return 2100;
    }
    if (rate < 1) {
      return 1700;
    }
    return 1300;
  }

  function clearGuidedReading() {
    activeGuidedRows.forEach((row) => row.classList.remove("is-reading-current"));
    activeGuidedRows = [];
    if (activeGuidedPanel) {
      activeGuidedPanel.hidden = true;
      activeGuidedPanel.querySelector(".guided-meaning").textContent = "";
      activeGuidedPanel.querySelector(".guided-thai").textContent = "";
      activeGuidedPanel.querySelector(".guided-pinyin").textContent = "";
    }
    if (activeFollowButton) {
      activeFollowButton.classList.remove("is-playing");
    }
    activeFollowButton = null;
    activeGuidedPanel = null;
  }

  function clearActiveAudio() {
    if (activeAudio) {
      activeAudio.pause();
      activeAudio.currentTime = 0;
    }
    if (activeCard) {
      activeCard.classList.remove("is-playing");
    }
    if (activeButton) {
      activeButton.classList.remove("is-playing");
    }
    activeAudio = null;
    activeCard = null;
    activeButton = null;
  }

  function stopCurrent() {
    guidedRunId += 1;
    clearActiveAudio();
    clearGuidedReading();
  }

  function playTarget(target, card, button, missingMessage, options = {}) {
    const allowRepeat = options.allowRepeat !== false;
    clearActiveAudio();
    const audio = new Audio(target.audio);
    activeAudio = audio;
    activeCard = card;
    activeButton = button;
    audio.playbackRate = getPlaybackRate();
    card.classList.add("is-playing");
    button.classList.add("is-playing");
    nowPlaying.textContent = `${target.meaning} | ${itemTarget(target)}`;

    return new Promise((resolve) => {
      audio.addEventListener("ended", () => {
        if (allowRepeat && repeat) {
          audio.currentTime = 0;
          audio.play();
          return;
        }
        card.classList.remove("is-playing");
        button.classList.remove("is-playing");
        activeAudio = null;
        activeCard = null;
        activeButton = null;
        resolve(true);
      });

      audio.addEventListener("error", () => {
        nowPlaying.textContent = `${missingMessage}：${itemTarget(target)}`;
        card.classList.remove("is-playing");
        button.classList.remove("is-playing");
        resolve(false);
      });

      audio.play().catch(() => {
        nowPlaying.textContent = "浏览器阻止了播放，请再点击一次播放按钮";
        card.classList.remove("is-playing");
        button.classList.remove("is-playing");
        resolve(false);
      });
    });
  }

  function playAudio(target, card, button, missingMessage) {
    stopCurrent();
    playTarget(target, card, button, missingMessage);
  }

  function showGuidedWord(panel, word) {
    panel.hidden = false;
    panel.querySelector(".guided-meaning").textContent = word.meaning;
    panel.querySelector(".guided-thai").textContent = itemTarget(word);
    panel.querySelector(".guided-pinyin").textContent = word.pinyin;
  }

  function waitForFollow(runId, ms) {
    return new Promise((resolve) => {
      window.setTimeout(() => resolve(runId === guidedRunId), ms);
    });
  }

  function markCurrentWord(row) {
    activeGuidedRows.forEach((item) => item.classList.remove("is-reading-current"));
    activeGuidedRows = [];
    if (row) {
      row.classList.add("is-reading-current");
      activeGuidedRows = [row];
    }
  }

  async function startGuidedReading(item, card, followButton, wordRows) {
    if (activeFollowButton === followButton) {
      stopCurrent();
      nowPlaying.textContent = "已停止跟读";
      return;
    }

    stopCurrent();
    const runId = guidedRunId;
    const thaiButton = card.querySelector(".thai-button");
    const panel = card.querySelector(".guided-word-panel");
    const words = item.words || [];
    activeFollowButton = followButton;
    activeGuidedPanel = panel;
    followButton.classList.add("is-playing");

    nowPlaying.textContent = `跟读整句 | ${itemTarget(item)}`;
    await playTarget(item, card, thaiButton, "音频未找到", { allowRepeat: false });
    if (runId !== guidedRunId) return;

    if (!(await waitForFollow(runId, 700))) return;

    for (let index = 0; index < words.length; index += 1) {
      const word = words[index];
      const row = wordRows[index];
      showGuidedWord(panel, word);
      markCurrentWord(row);
      nowPlaying.textContent = `跟读词块 ${index + 1}/${words.length} | ${itemTarget(word)}`;
      if (word.audio) {
        const wordButton = row ? row.querySelector(".word-play-button") : followButton;
        await playTarget(word, card, wordButton || followButton, "词块音频未找到", {
          allowRepeat: false,
        });
      }
      if (runId !== guidedRunId) return;
      if (!(await waitForFollow(runId, getFollowPauseMs()))) return;
    }

    markCurrentWord(null);
    nowPlaying.textContent = `跟读整句复习 | ${itemTarget(item)}`;
    await playTarget(item, card, thaiButton, "音频未找到", { allowRepeat: false });
    if (runId !== guidedRunId) return;

    nowPlaying.textContent = `跟读完成 | ${itemTarget(item)}`;
    clearGuidedReading();
  }

  function playItem(item, card) {
    playAudio(item, card, card.querySelector(".thai-button"), "音频未找到");
  }

  function playWord(word, card, button) {
    playAudio(word, card, button, "词块音频未找到");
  }

  function openToneGuide() {
    stopCurrent();
    if (typeof toneGuideDialog.showModal === "function") {
      toneGuideDialog.showModal();
      return;
    }
    toneGuideDialog.setAttribute("open", "");
  }

  function closeToneGuide() {
    if (typeof toneGuideDialog.close === "function") {
      toneGuideDialog.close();
      return;
    }
    toneGuideDialog.removeAttribute("open");
  }

  function updateLanguageGuide() {
    const language = currentLanguage();
    document.querySelectorAll(".language-guide").forEach((guide) => {
      guide.hidden = guide.dataset.language !== language;
    });
    toneGuideButton.textContent = `${languageLabel(language)}发音规则`;
    toneGuideTitle.textContent = `${languageLabel(language)}发音规则总表`;
  }

  function appendWordRows(list, words, node, listClassName = "word-list") {
    const wordRows = [];
    list.className = listClassName;
    words.forEach((word) => {
      const row = document.createElement("li");

      const meaning = document.createElement("span");
      meaning.className = "word-meaning";
      meaning.textContent = word.meaning;

      const target = document.createElement("span");
      target.className = "word-thai";
      target.textContent = itemTarget(word);

      const pinyin = document.createElement("span");
      pinyin.className = "word-pinyin";
      pinyin.textContent = word.pinyin;

      row.append(meaning, target, pinyin);

      if (word.partOfSpeech) {
        const part = document.createElement("span");
        part.className = "word-part";
        part.textContent = word.partOfSpeech;
        row.appendChild(part);
      }

      if ((word.collocations || []).length > 0) {
        const collocations = document.createElement("span");
        collocations.className = "collocation-list";
        collocations.textContent = word.collocations.join(" / ");
        row.appendChild(collocations);
      }

      if (word.audio) {
        const playButton = document.createElement("button");
        playButton.type = "button";
        playButton.className = "word-play-button";
        playButton.textContent = "▶";
        playButton.setAttribute("aria-label", `播放词块 ${itemTarget(word)}`);
        playButton.addEventListener("click", (event) => {
          event.stopPropagation();
          playWord(word, node, playButton);
        });
        row.appendChild(playButton);
      }

      wordRows.push(row);
      list.appendChild(row);
    });
    return wordRows;
  }

  function appendRules(breakdown, item) {
    const rules = item.pronunciationRules || [];
    if (rules.length === 0) return;
    const ruleBox = document.createElement("div");
    ruleBox.className = "pronunciation-rules";

    const ruleTitle = document.createElement("p");
    ruleTitle.className = "breakdown-title";
    ruleTitle.textContent = "发音规则提示";
    ruleBox.appendChild(ruleTitle);

    const ruleList = document.createElement("ul");
    ruleList.className = "rule-list";
    rules.forEach((rule) => {
      const row = document.createElement("li");
      row.textContent = rule;
      ruleList.appendChild(row);
    });
    ruleBox.appendChild(ruleList);
    breakdown.appendChild(ruleBox);
  }

  function renderPhraseCard(item) {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".kind").textContent = item.kind;
    node.querySelector(".source").textContent = item.source;
    node.querySelector(".meaning").textContent = item.meaning;
    node.querySelector(".thai-button").textContent = itemTarget(item);
    node.querySelector(".thai-button").setAttribute("aria-label", `播放 ${itemTarget(item)}`);
    node.querySelector(".pinyin").textContent = item.pinyin;
    const breakdown = node.querySelector(".word-breakdown");
    const words = item.words || [];
    let wordRows = [];

    if (words.length > 0) {
      const title = document.createElement("p");
      title.className = "breakdown-title";
      title.textContent = "词块拆解";
      breakdown.appendChild(title);

      const list = document.createElement("ul");
      wordRows = appendWordRows(list, words, node);
      breakdown.appendChild(list);
    }

    appendRules(breakdown, item);

    node.querySelector(".thai-button").addEventListener("click", () => playItem(item, node));
    node.querySelector(".follow-button").addEventListener("click", () => {
      startGuidedReading(item, node, node.querySelector(".follow-button"), wordRows);
    });
    return node;
  }

  function renderScenarioMemory(item) {
    const paragraph = document.createElement("p");
    paragraph.className = "scenario-memory";
    const text = item.scenarioMemoryText || "";
    const hits = [...(item.scenarioMemory || [])].sort((left, right) => left.start - right.start);
    let cursor = 0;
    hits.forEach((hit) => {
      if (hit.start > cursor) {
        paragraph.appendChild(document.createTextNode(text.slice(cursor, hit.start)));
      }
      const token = document.createElement("span");
      token.className = "scenario-token";
      token.textContent = text.slice(hit.start, hit.end);
      paragraph.appendChild(token);
      cursor = hit.end;
    });
    if (cursor < text.length) {
      paragraph.appendChild(document.createTextNode(text.slice(cursor)));
    }
    return paragraph;
  }

  function playDialogueLine(line, card, button) {
    playAudio(
      {
        audio: line.audio,
        meaning: line.meaning_zh,
        target: line.text,
        thai: line.text,
      },
      card,
      button,
      "句子音频未找到"
    );
  }

  function renderEnglishLessonCard(item) {
    const node = document.createElement("article");
    node.className = "phrase-card english-lesson-card";

    const head = document.createElement("div");
    head.className = "card-head";
    const kind = document.createElement("span");
    kind.className = "kind";
    kind.textContent = "词群课";
    const source = document.createElement("span");
    source.className = "source";
    source.textContent = item.source;
    head.append(kind, source);

    const title = document.createElement("p");
    title.className = "meaning";
    title.textContent = item.title || item.meaning;

    const meta = document.createElement("p");
    meta.className = "pinyin";
    meta.textContent = `${(item.track || "").toUpperCase()} | ${item.difficulty || ""}`;

    const scenarioTitle = document.createElement("p");
    scenarioTitle.className = "breakdown-title";
    scenarioTitle.textContent = "中文情景串记";

    const playAll = document.createElement("button");
    playAll.className = "follow-button";
    playAll.type = "button";
    playAll.textContent = "整段跟读";
    playAll.addEventListener("click", () => playAudio(item, node, playAll, "整段音频未找到"));

    const reviewState = loadReviewState()[item.id] || {};
    const reviewControls = document.createElement("div");
    reviewControls.className = "lesson-review-controls";
    [
      ["known", "已掌握"],
      ["review", "待复习"],
      ["favorite", "收藏"],
    ].forEach(([key, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "review-state-button";
      button.textContent = label;
      button.setAttribute("aria-pressed", String(Boolean(reviewState[key])));
      button.addEventListener("click", () => toggleReviewState(item.id, key, button));
      reviewControls.appendChild(button);
    });

    const wordTitle = document.createElement("p");
    wordTitle.className = "breakdown-title";
    wordTitle.textContent = "词块拆解";

    const wordList = document.createElement("ul");
    appendWordRows(wordList, item.words || [], node, "word-list lesson-word-list");

    const dialogueTitle = document.createElement("p");
    dialogueTitle.className = "breakdown-title";
    dialogueTitle.textContent = "英文场景对话";

    const dialogueList = document.createElement("div");
    dialogueList.className = "dialogue-list";
    (item.dialogue || []).forEach((line) => {
      const row = document.createElement("div");
      row.className = "dialogue-row";
      const text = document.createElement("p");
      text.className = "dialogue-text";
      text.textContent = `${line.speaker}: ${line.text}`;
      const meaning = document.createElement("p");
      meaning.className = "dialogue-meaning";
      meaning.textContent = line.meaning_zh;
      const playButton = document.createElement("button");
      playButton.type = "button";
      playButton.className = "dialogue-play-button";
      playButton.textContent = "▶";
      playButton.setAttribute("aria-label", `播放句子 ${line.text}`);
      playButton.addEventListener("click", () => playDialogueLine(line, node, playButton));
      row.append(text, meaning, playButton);
      dialogueList.appendChild(row);
    });

    node.append(head, title, meta, scenarioTitle, renderScenarioMemory(item), playAll, reviewControls, wordTitle, wordList, dialogueTitle, dialogueList);
    return node;
  }

  function render() {
    const query = searchInput.value.trim().toLowerCase();
    const language = currentLanguage();
    const category = categorySelect.value || "全部";
    const track = currentTrack();
    const languageItems = itemsForLanguage(language);
    const visibleItems = items.filter((item) => matches(item, query, language, category, track));

    grid.innerHTML = "";
    itemCount.textContent = String(query || category !== "全部" || track !== "all" ? visibleItems.length : languageItems.length);
    updateTrackFilterVisibility();
    updateLanguageGuide();

    if (visibleItems.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "没有找到匹配的词句";
      grid.appendChild(empty);
      return;
    }

    visibleItems.forEach((item) => {
      if ((item.language || "thai") === "english" && item.kind === "lesson") {
        grid.appendChild(renderEnglishLessonCard(item));
        return;
      }
      grid.appendChild(renderPhraseCard(item));
    });
  }

  searchInput.addEventListener("input", () => {
    stopCurrent();
    render();
  });
  languageSelect.addEventListener("change", () => {
    stopCurrent();
    setupCategories();
    updateTrackFilterVisibility();
    render();
  });
  if (trackSelect) {
    trackSelect.addEventListener("change", () => {
      stopCurrent();
      render();
    });
  }
  categorySelect.addEventListener("change", () => {
    stopCurrent();
    render();
  });
  repeatButton.addEventListener("click", () => {
    repeat = !repeat;
    repeatButton.setAttribute("aria-pressed", String(repeat));
    repeatButton.textContent = repeat ? "重复播放：开" : "重复播放：关";
  });
  toneGuideButton.addEventListener("click", openToneGuide);
  toneGuideCloseButton.addEventListener("click", closeToneGuide);
  toneGuideDialog.addEventListener("click", (event) => {
    if (event.target === toneGuideDialog) {
      closeToneGuide();
    }
  });

  setupLanguages();
  setupCategories();
  render();
})();

(function () {
  const items = window.THAI_AUDIO_APP_ITEMS || [];
  const meta = window.THAI_AUDIO_APP_META || {};
  const grid = document.querySelector("#phraseGrid");
  const template = document.querySelector("#phraseCardTemplate");
  const searchInput = document.querySelector("#searchInput");
  const categorySelect = document.querySelector("#categorySelect");
  const speedSelect = document.querySelector("#speedSelect");
  const repeatButton = document.querySelector("#repeatButton");
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

  itemCount.textContent = String(meta.count || items.length);

  function uniqueCategories() {
    return ["全部", ...Array.from(new Set(items.map((item) => item.category)))];
  }

  function setupCategories() {
    categorySelect.innerHTML = "";
    uniqueCategories().forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      categorySelect.appendChild(option);
    });
  }

  function matches(item, query, category) {
    const inCategory = category === "全部" || item.category === category;
    const words = (item.words || [])
      .map((word) => [word.meaning, word.thai, word.pinyin].join(" "))
      .join(" ");
    const rules = (item.pronunciationRules || []).join(" ");
    const haystack = [item.meaning, item.thai, item.pinyin, item.kind, item.category, words, rules]
      .join(" ")
      .toLowerCase();
    return inCategory && haystack.includes(query);
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
    nowPlaying.textContent = `${target.meaning} | ${target.thai}`;

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
        nowPlaying.textContent = `${missingMessage}：${target.thai}`;
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
    panel.querySelector(".guided-thai").textContent = word.thai;
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

    nowPlaying.textContent = `跟读整句 | ${item.thai}`;
    await playTarget(item, card, thaiButton, "音频未找到", { allowRepeat: false });
    if (runId !== guidedRunId) return;

    if (!(await waitForFollow(runId, 700))) return;

    for (let index = 0; index < words.length; index += 1) {
      const word = words[index];
      const row = wordRows[index];
      showGuidedWord(panel, word);
      markCurrentWord(row);
      nowPlaying.textContent = `跟读词块 ${index + 1}/${words.length} | ${word.thai}`;
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
    nowPlaying.textContent = `跟读整句复习 | ${item.thai}`;
    await playTarget(item, card, thaiButton, "音频未找到", { allowRepeat: false });
    if (runId !== guidedRunId) return;

    nowPlaying.textContent = `跟读完成 | ${item.thai}`;
    clearGuidedReading();
  }

  function playItem(item, card) {
    playAudio(item, card, card.querySelector(".thai-button"), "音频未找到");
  }

  function playWord(word, card, button) {
    playAudio(word, card, button, "词块音频未找到");
  }

  function render() {
    const query = searchInput.value.trim().toLowerCase();
    const category = categorySelect.value || "全部";
    const visibleItems = items.filter((item) => matches(item, query, category));

    grid.innerHTML = "";

    if (visibleItems.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "没有找到匹配的词句";
      grid.appendChild(empty);
      return;
    }

    visibleItems.forEach((item) => {
      const node = template.content.firstElementChild.cloneNode(true);
      node.querySelector(".kind").textContent = item.kind;
      node.querySelector(".source").textContent = item.source;
      node.querySelector(".meaning").textContent = item.meaning;
      node.querySelector(".thai-button").textContent = item.thai;
      node.querySelector(".thai-button").setAttribute("aria-label", `播放 ${item.thai}`);
      node.querySelector(".pinyin").textContent = item.pinyin;
      const breakdown = node.querySelector(".word-breakdown");
      const words = item.words || [];
      const wordRows = [];

      if (words.length > 0) {
        const title = document.createElement("p");
        title.className = "breakdown-title";
        title.textContent = "词块拆解";
        breakdown.appendChild(title);

        const list = document.createElement("ul");
        list.className = "word-list";
        words.forEach((word) => {
          const row = document.createElement("li");

          const meaning = document.createElement("span");
          meaning.className = "word-meaning";
          meaning.textContent = word.meaning;

          const thai = document.createElement("span");
          thai.className = "word-thai";
          thai.textContent = word.thai;

          const pinyin = document.createElement("span");
          pinyin.className = "word-pinyin";
          pinyin.textContent = word.pinyin;

          row.append(meaning, thai, pinyin);

          if (word.audio) {
            const playButton = document.createElement("button");
            playButton.type = "button";
            playButton.className = "word-play-button";
            playButton.textContent = "▶";
            playButton.setAttribute("aria-label", `播放词块 ${word.thai}`);
            playButton.addEventListener("click", (event) => {
              event.stopPropagation();
              playWord(word, node, playButton);
            });
            row.appendChild(playButton);
          }

          wordRows.push(row);
          list.appendChild(row);
        });
        breakdown.appendChild(list);
      }

      const rules = item.pronunciationRules || [];
      if (rules.length > 0) {
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

      node.querySelector(".thai-button").addEventListener("click", () => playItem(item, node));
      node.querySelector(".follow-button").addEventListener("click", () => {
        startGuidedReading(item, node, node.querySelector(".follow-button"), wordRows);
      });
      grid.appendChild(node);
    });
  }

  searchInput.addEventListener("input", () => {
    stopCurrent();
    render();
  });
  categorySelect.addEventListener("change", () => {
    stopCurrent();
    render();
  });
  repeatButton.addEventListener("click", () => {
    repeat = !repeat;
    repeatButton.setAttribute("aria-pressed", String(repeat));
    repeatButton.textContent = repeat ? "重复播放：开" : "重复播放：关";
  });

  setupCategories();
  render();
})();

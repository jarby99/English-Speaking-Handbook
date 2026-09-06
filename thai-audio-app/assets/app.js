(function () {
  const items = window.THAI_AUDIO_APP_ITEMS || [];
  const meta = window.THAI_AUDIO_APP_META || {};
  const grid = document.querySelector("#phraseGrid");
  const template = document.querySelector("#phraseCardTemplate");
  const searchInput = document.querySelector("#searchInput");
  const categorySelect = document.querySelector("#categorySelect");
  const repeatButton = document.querySelector("#repeatButton");
  const nowPlaying = document.querySelector("#nowPlaying");
  const itemCount = document.querySelector("#itemCount");

  let activeAudio = null;
  let activeCard = null;
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

  function stopCurrent() {
    if (activeAudio) {
      activeAudio.pause();
      activeAudio.currentTime = 0;
    }
    if (activeCard) {
      activeCard.classList.remove("is-playing");
    }
    activeAudio = null;
    activeCard = null;
  }

  function playItem(item, card) {
    stopCurrent();

    const audio = new Audio(item.audio);
    activeAudio = audio;
    activeCard = card;
    card.classList.add("is-playing");
    nowPlaying.textContent = `${item.meaning} | ${item.thai}`;

    audio.addEventListener("ended", () => {
      if (repeat) {
        audio.currentTime = 0;
        audio.play();
        return;
      }
      card.classList.remove("is-playing");
      activeAudio = null;
      activeCard = null;
    });

    audio.addEventListener("error", () => {
      nowPlaying.textContent = `音频未找到：${item.thai}`;
      card.classList.remove("is-playing");
    });

    audio.play().catch(() => {
      nowPlaying.textContent = "浏览器阻止了播放，请再点击一次泰语卡片";
      card.classList.remove("is-playing");
    });
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
      grid.appendChild(node);
    });
  }

  searchInput.addEventListener("input", render);
  categorySelect.addEventListener("change", render);
  repeatButton.addEventListener("click", () => {
    repeat = !repeat;
    repeatButton.setAttribute("aria-pressed", String(repeat));
    repeatButton.textContent = repeat ? "重复播放：开" : "重复播放：关";
  });

  setupCategories();
  render();
})();

const state = {
  indexData: null,
  currentType: "tw",
  currentDate: null,
  digestCache: new Map(),
  existsCache: new Map(),
  typeDateCache: new Map(),
};

const elements = {
  themeToggle: document.getElementById("theme-toggle"),
  themeToggleIcon: document.getElementById("theme-toggle-icon"),
  tabButtons: Array.from(document.querySelectorAll(".tab-button")),
  prevDate: document.getElementById("prev-date"),
  nextDate: document.getElementById("next-date"),
  currentDateText: document.getElementById("current-date-text"),
  statusMessage: document.getElementById("status-message"),
  marketSnapshot: document.getElementById("market-snapshot"),
  trumpUpdates: document.getElementById("trump-updates"),
  financialNews: document.getElementById("financial-news"),
  economicEventsSection: document.getElementById("economic-events-section"),
  economicEvents: document.getElementById("economic-events"),
  aiInsight: document.getElementById("ai-insight"),
  riskList: document.getElementById("risk-list"),
  sentimentText: document.getElementById("sentiment-text"),
  generatedAt: document.getElementById("generated-at"),
};

function setStatus(message) {
  elements.statusMessage.textContent = message;
}

function formatDateText(dateString) {
  if (!dateString) return "尚無資料";
  return `${dateString.slice(0, 4)}-${dateString.slice(4, 6)}-${dateString.slice(6, 8)}`;
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "⚠️ 資料暫時無法取得";
  }
  return Number(value).toLocaleString("zh-Hant", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatChange(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "flat";
  }
  return Number(value) > 0 ? "up" : Number(value) < 0 ? "down" : "flat";
}

function arrowForChange(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "•";
  }
  return Number(value) > 0 ? "▲" : Number(value) < 0 ? "▼" : "•";
}

function getDataPath(type, date) {
  return `./data/${type}_${date}.json`;
}

async function fetchIndexData() {
  const response = await fetch("./data/index.json", { cache: "no-store" });
  if (!response.ok) {
    return {
      available_dates: [],
      latest_tw: null,
      latest_us: null,
    };
  }
  return response.json();
}

async function digestExists(type, date) {
  const key = `${type}_${date}`;
  if (state.existsCache.has(key)) {
    return state.existsCache.get(key);
  }

  try {
    const headResponse = await fetch(getDataPath(type, date), {
      method: "HEAD",
      cache: "no-store",
    });
    if (headResponse.ok) {
      state.existsCache.set(key, true);
      return true;
    }
  } catch (error) {
    // Fall back to GET below.
  }

  try {
    const getResponse = await fetch(getDataPath(type, date), { cache: "no-store" });
    const exists = getResponse.ok;
    state.existsCache.set(key, exists);
    if (exists) {
      const payload = await getResponse.json();
      state.digestCache.set(key, payload);
    }
    return exists;
  } catch (error) {
    state.existsCache.set(key, false);
    return false;
  }
}

async function fetchDigest(type, date) {
  const key = `${type}_${date}`;
  if (state.digestCache.has(key)) {
    return state.digestCache.get(key);
  }

  const response = await fetch(getDataPath(type, date), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Digest not found for ${key}`);
  }
  const payload = await response.json();
  state.digestCache.set(key, payload);
  state.existsCache.set(key, true);
  return payload;
}

function getDefaultType() {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Taipei",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = formatter.formatToParts(new Date());
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? "0");
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? "0");
  const totalMinutes = hour * 60 + minute;
  return totalMinutes < 13 * 60 + 30 ? "tw" : "us";
}

async function getDatesForType(type) {
  if (state.typeDateCache.has(type)) {
    return state.typeDateCache.get(type);
  }

  const dates = [...(state.indexData?.available_dates ?? [])].sort();
  const available = [];
  for (const date of dates) {
    if (await digestExists(type, date)) {
      available.push(date);
    }
  }

  state.typeDateCache.set(type, available);
  return available;
}

function setActiveTab(type) {
  elements.tabButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.type === type);
  });
}

function buildSnapshotCard(label, value, changePct, detail = "") {
  const changeClass = formatChange(changePct);
  const detailMarkup = detail ? `<div class="summary-text">${detail}</div>` : "";
  return `
    <article class="snapshot-card">
      <span class="label">${label}</span>
      <div class="value">${formatNumber(value)}</div>
      <div class="change ${changeClass}">
        ${arrowForChange(changePct)} ${changePct === null || changePct === undefined ? "⚠️ 資料暫時無法取得" : `${Number(changePct).toFixed(2)}%`}
      </div>
      ${detailMarkup}
    </article>
  `;
}

function renderEmpty(container, message = "⚠️ 資料暫時無法取得") {
  container.innerHTML = `<div class="empty-state">${message}</div>`;
}

function renderSnapshot(payload) {
  const cards = [];

  if (payload.type === "tw") {
    const twIndex = payload.tw_market_index ?? {};
    cards.push(
      buildSnapshotCard(
        twIndex.name ?? "台灣加權指數",
        twIndex.price,
        twIndex.change_pct,
        "台股開盤前快速掌握大盤方向與自選股表現。"
      )
    );

    for (const item of payload.tw_watchlist ?? []) {
      cards.push(buildSnapshotCard(item.name ?? item.symbol, item.price, item.change_pct));
    }
  } else {
    const indices = [
      ["S&P 500", payload.us_market_close?.sp500],
      ["Dow Jones", payload.us_market_close?.dow],
      ["Nasdaq", payload.us_market_close?.nasdaq],
      ["ES=F", payload.futures?.sp500],
      ["NQ=F", payload.futures?.nasdaq],
    ];
    indices.forEach(([label, data]) => {
      cards.push(buildSnapshotCard(label, data?.price, data?.change_pct));
    });

    for (const item of payload.us_watchlist ?? []) {
      cards.push(buildSnapshotCard(item.name ?? item.symbol, item.price, item.change_pct));
    }
  }

  elements.marketSnapshot.innerHTML = cards.length
    ? cards.join("")
    : `<div class="empty-state">⚠️ 資料暫時無法取得</div>`;
}

function renderTrumpUpdates(items) {
  if (!items?.length) {
    renderEmpty(elements.trumpUpdates);
    return;
  }

  elements.trumpUpdates.innerHTML = items
    .map(
      (item) => `
        <article class="content-card">
          <span class="source-tag">${item.source ?? "Unknown"}</span>
          <div class="body-text">${item.content ?? "⚠️ 資料暫時無法取得"}</div>
          <div class="impact-text">影響分析：${item.impact ?? "⚠️ 資料暫時無法取得"}</div>
        </article>
      `
    )
    .join("");
}

function renderFinancialNews(items) {
  if (!items?.length) {
    renderEmpty(elements.financialNews);
    return;
  }

  elements.financialNews.innerHTML = items
    .map(
      (item, index) => `
        <article class="content-card">
          <strong>${item.title ?? "⚠️ 資料暫時無法取得"}</strong>
          <div class="summary-text">${item.summary ?? "⚠️ 資料暫時無法取得"}</div>
          <button class="accordion-button" type="button" data-accordion-target="impact-${index}">
            <span>查看影響分析</span>
            <span>+</span>
          </button>
          <div id="impact-${index}" class="accordion-panel">
            <div class="accordion-panel-inner impact-text">${item.impact ?? "⚠️ 資料暫時無法取得"}</div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderEconomicEvents(payload) {
  if (payload.type !== "us") {
    elements.economicEventsSection.classList.add("hidden");
    return;
  }

  elements.economicEventsSection.classList.remove("hidden");
  const items = payload.economic_events ?? [];
  if (!items.length) {
    renderEmpty(elements.economicEvents);
    return;
  }

  elements.economicEvents.innerHTML = items
    .map(
      (item) => `
        <article class="content-card">
          <div class="body-text">${item}</div>
        </article>
      `
    )
    .join("");
}

function renderInsight(payload) {
  elements.aiInsight.textContent = payload.ai_insight || "⚠️ 本次 AI 洞察暫時無法生成。";
}

function renderRisks(items) {
  if (!items?.length) {
    renderEmpty(elements.riskList);
    return;
  }

  elements.riskList.innerHTML = items
    .map(
      (item) => `
        <article class="risk-card">⚠️ ${item}</article>
      `
    )
    .join("");
}

function renderSentiment(payload) {
  elements.sentimentText.textContent = payload.sentiment || "市場情緒暫時無法判讀。";
}

function renderFooter(payload) {
  elements.generatedAt.textContent = `資料生成時間（UTC）：${payload.generated_at ?? "--"}`;
}

function updateDateControls(typeDates) {
  const currentIndex = typeDates.indexOf(state.currentDate);
  elements.prevDate.disabled = currentIndex <= 0;
  elements.nextDate.disabled = currentIndex === -1 || currentIndex >= typeDates.length - 1;
}

function bindAccordions() {
  document.querySelectorAll(".accordion-button").forEach((button) => {
    button.addEventListener("click", () => {
      const panel = document.getElementById(button.dataset.accordionTarget);
      if (!panel) return;

      const isOpen = panel.style.maxHeight && panel.style.maxHeight !== "0px";
      panel.style.maxHeight = isOpen ? "0px" : `${panel.scrollHeight}px`;
      button.querySelector("span:last-child").textContent = isOpen ? "+" : "−";
    });
  });
}

async function renderCurrentDigest() {
  try {
    const payload = await fetchDigest(state.currentType, state.currentDate);
    renderSnapshot(payload);
    renderTrumpUpdates(payload.trump_updates);
    renderFinancialNews(payload.financial_news);
    renderEconomicEvents(payload);
    renderInsight(payload);
    renderRisks(payload.risks);
    renderSentiment(payload);
    renderFooter(payload);
    bindAccordions();
    elements.currentDateText.textContent = formatDateText(state.currentDate);
    setStatus(`顯示 ${state.currentType === "tw" ? "台股" : "美股"} ${formatDateText(state.currentDate)} 摘要`);
  } catch (error) {
    renderEmpty(elements.marketSnapshot);
    renderEmpty(elements.trumpUpdates);
    renderEmpty(elements.financialNews);
    elements.economicEventsSection.classList.toggle("hidden", state.currentType !== "us");
    if (state.currentType === "us") {
      renderEmpty(elements.economicEvents);
    }
    elements.aiInsight.textContent = "⚠️ 本次 AI 洞察暫時無法生成。";
    renderEmpty(elements.riskList);
    elements.sentimentText.textContent = "市場情緒暫時無法判讀。";
    elements.generatedAt.textContent = "資料生成時間（UTC）：--";
    setStatus("目前沒有對應日期的資料。");
  }
}

async function switchType(type) {
  state.currentType = type;
  setActiveTab(type);
  const typeDates = await getDatesForType(type);
  const latestKey = type === "tw" ? "latest_tw" : "latest_us";
  state.currentDate = typeDates.includes(state.indexData?.[latestKey])
    ? state.indexData[latestKey]
    : typeDates[typeDates.length - 1] ?? null;

  elements.currentDateText.textContent = formatDateText(state.currentDate);
  updateDateControls(typeDates);

  if (!state.currentDate) {
    setStatus(`尚無${type === "tw" ? "台股" : "美股"}資料。`);
    renderEmpty(elements.marketSnapshot, "尚無資料，請先執行對應 workflow。");
    renderEmpty(elements.trumpUpdates, "尚無資料，請先執行對應 workflow。");
    renderEmpty(elements.financialNews, "尚無資料，請先執行對應 workflow。");
    elements.aiInsight.textContent = "尚無資料，請先執行對應 workflow。";
    renderEmpty(elements.riskList, "尚無資料，請先執行對應 workflow。");
    elements.sentimentText.textContent = "尚無資料";
    elements.generatedAt.textContent = "資料生成時間（UTC）：--";
    elements.economicEventsSection.classList.toggle("hidden", type !== "us");
    if (type === "us") {
      renderEmpty(elements.economicEvents, "尚無資料，請先執行對應 workflow。");
    }
    return;
  }

  await renderCurrentDigest();
  updateDateControls(typeDates);
}

async function moveDate(direction) {
  const typeDates = await getDatesForType(state.currentType);
  const currentIndex = typeDates.indexOf(state.currentDate);
  const nextIndex = currentIndex + direction;
  if (nextIndex < 0 || nextIndex >= typeDates.length) {
    return;
  }
  state.currentDate = typeDates[nextIndex];
  await renderCurrentDigest();
  updateDateControls(typeDates);
}

function applySavedTheme() {
  const savedTheme = localStorage.getItem("daily-digest-theme");
  const theme = savedTheme === "light" ? "theme-light" : "theme-dark";
  document.body.classList.remove("theme-light", "theme-dark");
  document.body.classList.add(theme);
  elements.themeToggleIcon.textContent = theme === "theme-light" ? "☀️" : "🌙";
}

function toggleTheme() {
  const isLight = document.body.classList.contains("theme-light");
  document.body.classList.toggle("theme-light", !isLight);
  document.body.classList.toggle("theme-dark", isLight);
  localStorage.setItem("daily-digest-theme", isLight ? "dark" : "light");
  elements.themeToggleIcon.textContent = isLight ? "🌙" : "☀️";
}

async function init() {
  applySavedTheme();
  state.indexData = await fetchIndexData();

  elements.themeToggle.addEventListener("click", toggleTheme);
  elements.tabButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      await switchType(button.dataset.type);
    });
  });
  elements.prevDate.addEventListener("click", async () => moveDate(-1));
  elements.nextDate.addEventListener("click", async () => moveDate(1));

  const defaultType = getDefaultType();
  await switchType(defaultType);
}

init().catch(() => {
  setStatus("載入失敗，請稍後重新整理。");
});

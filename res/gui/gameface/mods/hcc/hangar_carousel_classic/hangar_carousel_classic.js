const MODEL_NAME = "hangarCarouselClassic";
const CARD_PREFIX = "vehicleCard-";

const LABELS = {
  en: {
    filters: "HCC filters",
    filter_count_description: "ALL shows the vehicles matching every active filter; each filter count shows the matching vehicles within that current selection.",
    filter_all: "All vehicles",
    filter_favorite: "Favorite tanks",
    filter_non_elite: "Non-elite tanks",
    filter_not_ready: "Broken / crew incomplete",
    filter_marks_incomplete: "Marks incomplete (Tier V+)",
    filter_crew_not_maxed: "Crew not fully trained",
    sort_default: "Default order",
    sort_battles: "Battles",
    sort_winRate: "Win rate",
    sort_averageDamage: "Average damage",
    sort_alphaDamage: "Alpha damage",
    sort_marksOnGun: "Marks of Excellence",
    sort_lastPlayed: "Last played (HCC)",
    sorting: "HCC sorting",
    stat_battles: "Batt",
    stat_win_rate: "WR",
    stat_damage: "Avg",
    stat_alpha_damage: "Alpha",
    stat_mastery: "M",
    stat_marks: "MoE",
    carousel_rows: "Carousel rows",
    carousel_rows_description: "Number of vehicle rows displayed in the hangar carousel.",
    carousel_auto: "Automatic rows",
    carousel_auto_description: "Uses 1 row for up to 8 matching vehicles, 2 for up to 16, 3 for up to 24, and 4 above 24.",
    ascending: "Ascending",
    descending: "Descending",
    refresh: "Refresh HCC data",
    unavailable: "Vehicle playlists are unavailable in this client mode"
  }
};

const SORT_ICONS = {
  default: "<>",
  battles: "##",
  winRate: "WR",
  averageDamage: "DMG",
  alphaDamage: "ALPHA",
  marksOnGun: "MOE",
  lastPlayed: "LP"
};

const SORT_DIRECTION_ICONS = {
  descending: "v",
  ascending: "^"
};

const FILTER_SVG_NS = "http://www.w3.org/2000/svg";

const FILTER_ICONS = {
  all: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  favorite: '<path d="M12 3.5l2.47 5.13 5.53.82-4 3.98.94 5.57L12 16.4l-4.94 2.6.94-5.57-4-3.98 5.53-.82L12 3.5z"/>',
  non_elite: '<rect x="12" y="4.2" width="11" height="11" rx="1.5" transform="rotate(45 12 12)"/>',
  not_ready: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  marks_incomplete: '<circle cx="12" cy="8" r="5.2"/><path d="M8.4 12.9L7 21l5-2.8L17 21l-1.4-8.1"/>',
  crew_not_maxed: '<circle cx="12" cy="8" r="3.2"/><path d="M5.5 20c0-3.6 2.9-6.2 6.5-6.2s6.5 2.6 6.5 6.2"/>'
};

function setButtonIcon(button, filterId) {
  while (button.firstChild) {
    button.removeChild(button.firstChild);
  }
  const svg = document.createElementNS(FILTER_SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = FILTER_ICONS[filterId] || FILTER_ICONS.all;
  button.appendChild(svg);
}

let state = { stats: {}, statsConfig: {}, filtering: {}, sorting: {}, actionCards: {}, carousel: { rows: 2 }, filters: [], activeFilters: [], enabled: false };
let lastStateJson = "";
let lastActiveFiltersJson = "";
let lastStatsDiagnostic = "";
let scheduled = false;
let tooltipElement = null;

function setButtonGlyph(element, glyph, className) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
  const span = document.createElement("span");
  span.className = className;
  span.textContent = String(glyph || "");
  element.appendChild(span);
}

function unwrap(value) {
  if (value && typeof value === "object" && Object.prototype.hasOwnProperty.call(value, "value")) {
    return value.value;
  }
  return value;
}

function labels() {
  return LABELS.en;
}

function findModel() {
  if (!window.subViews) return null;
  for (const id of window.subViews.ids()) {
    const candidate = window.subViews.get(id)?.model?.[MODEL_NAME];
    if (candidate) return candidate;
  }
  return null;
}

function callCommand(commandName, payload) {
  const model = findModel();
  if (!model || typeof model[commandName] !== "function") return false;
  try {
    if (payload === undefined) model[commandName]();
    else model[commandName](payload);
    return true;
  } catch (error) {
    console.error(`[HangarCarouselClassic] ${commandName} failed`, error);
    return false;
  }
}

function scheduleRender() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    applyCarouselRowsClass();
    applyActionCardsVisibility();
    renderNativeFilterPanel();
    renderCardStats();
  });
}

function applyCarouselRowsClass() {
  const rows = Math.max(1, Math.min(4, Number(state.carousel?.rows || 2)));
  for (const root of [document.documentElement, document.body]) {
    if (!root) continue;
    root.classList.remove("hcc-carousel-rows-1", "hcc-carousel-rows-2", "hcc-carousel-rows-3", "hcc-carousel-rows-4");
    root.classList.add(`hcc-carousel-rows-${rows}`);
  }
}

function applyActionCardsVisibility() {
  const classes = {
    hideBuyTank: "hcc-hide-buy-tank",
    hideBuySlot: "hcc-hide-buy-slot",
    hideRestoreTank: "hcc-hide-restore-tank"
  };
  for (const root of [document.documentElement, document.body]) {
    if (!root) continue;
    for (const [key, className] of Object.entries(classes)) {
      root.classList.toggle(className, Boolean(state.actionCards?.[key]));
    }
  }
}

function formatCompact(value) {
  const number = Number(value || 0);
  if (number >= 10000) return `${(number / 1000).toFixed(number >= 100000 ? 0 : 1)}k`;
  return number.toLocaleString();
}

function masteryLabel(value) {
  const mastery = Number(value || 0);
  if (mastery >= 4) return "ASS";
  return `${labels().stat_mastery}${mastery}`;
}

function marksLevel(stats) {
  const explicitLevel = Number(stats.marksOnGunLevel || 0);
  if (explicitLevel > 0) return explicitLevel;
  const rating = Number(stats.marksOnGun || 0);
  if (rating >= 95) return 3;
  if (rating >= 85) return 2;
  if (rating >= 65) return 1;
  return 0;
}

function winRateBand(value) {
  const winRate = Number(value || 0);
  if (winRate < 47) return "bad";
  if (winRate < 50) return "below-average";
  if (winRate < 52) return "average";
  if (winRate < 55) return "good";
  if (winRate < 60) return "great";
  return "exceptional";
}

function statRows(stats) {
  const fields = state.statsConfig?.fields || [];
  const items = [];
  if (fields.includes("battles")) {
    items.push({ classes: ["battles"], text: `${labels().stat_battles} ${formatCompact(stats.battles)}` });
  }
  if (fields.includes("winRate")) {
    const winRate = Number(stats.winRate || 0);
    items.push({
      classes: ["win-rate"],
      text: `${labels().stat_win_rate} ${winRate.toFixed(1)}%`
    });
  }
  if (fields.includes("averageDamage")) {
    items.push({ classes: ["damage"], text: `${labels().stat_damage} ${formatCompact(stats.averageDamage)}` });
  }
  if (fields.includes("alphaDamage")) {
    items.push({ classes: ["alpha-damage"], text: `${labels().stat_alpha_damage} ${formatCompact(stats.alphaDamage)}` });
  }
  if (fields.includes("mastery")) {
    const mastery = Number(stats.mastery || 0);
    items.push({ classes: ["mastery", `mastery-${mastery}`], text: masteryLabel(mastery) });
  }
  if (fields.includes("marksOnGun")) {
    const marks = Number(stats.marksOnGun || 0);
    const level = marksLevel(stats);
    const classes = ["marks"];
    if (level > 0) classes.push(`marks-${level}`);
    items.push({ classes, text: `${labels().stat_marks} ${marks.toFixed(2)}%` });
  }

  const rows = [];
  for (let index = 0; index < items.length; index += 2) {
    rows.push(items.slice(index, index + 2));
  }
  return rows;
}

function directChildByClass(parent, className) {
  for (const child of parent.children) {
    if (child.classList.contains(className)) return child;
  }
  return null;
}

function renderCardStats() {
  const minimumBattles = Number(state.statsConfig?.minimumBattles ?? 1);
  const cards = Array.from(document.querySelectorAll(`[data-test-id^="${CARD_PREFIX}"]`));
  let matched = 0;
  let visible = 0;
  let sampleText = "";
  cards.forEach((card) => {
    const id = card.getAttribute("data-test-id").slice(CARD_PREFIX.length);
    const stats = state.stats?.[id];
    const nativeContent = card.querySelector('[class*="Card_content_"]');
    const staleOverlay = nativeContent ? directChildByClass(nativeContent, "hcc-card-stats") : null;
    if (staleOverlay) staleOverlay.remove();
    const host = card;
    host.classList.add("hcc-card-stats-host");
    let overlay = directChildByClass(host, "hcc-card-stats");
    if (stats) matched += 1;
    card.removeAttribute("data-hcc-stats");
    if (!stats || Number(stats.battles) < minimumBattles || state.statsConfig?.enabled === false) {
      if (overlay) overlay.remove();
      return;
    }

    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "hcc-card-stats";
      overlay.dataset.vehicleId = id;
      host.appendChild(overlay);
    }

    const rows = statRows(stats);
    const signature = JSON.stringify(rows);
    if (overlay.dataset.signature !== signature) {
      overlay.dataset.signature = signature;
      overlay.innerHTML = "";
      rows.forEach((items) => {
        const line = document.createElement("div");
        line.className = "hcc-card-stats-line";
        items.forEach((item) => {
          const value = document.createElement("span");
          value.className = `hcc-card-stat ${item.classes.map((name) => `hcc-card-stat--${name}`).join(" ")}`;
          value.textContent = item.text;
          line.appendChild(value);
        });
        overlay.appendChild(line);
      });
    }
    if (!sampleText) sampleText = `${id}=${overlay.textContent}`;
    visible += 1;
  });

  const diagnostic = `${cards.length}/${matched}/${visible}/${Object.keys(state.stats || {}).length}`;
  if (diagnostic !== lastStatsDiagnostic) {
    lastStatsDiagnostic = diagnostic;
    console.warn(`[HangarCarouselClassic] cards/matched/visible/stats: ${diagnostic}; sample: ${sampleText}`);
  }
}

function hideTooltip() {
  if (!tooltipElement) return;
  tooltipElement.remove();
  tooltipElement = null;
}

function showTooltip(anchor, title, description) {
  hideTooltip();
  const rect = anchor.getBoundingClientRect();
  const tooltip = document.createElement("div");
  tooltip.className = "hcc-hover-tooltip";
  const titleElement = document.createElement("div");
  titleElement.className = "hcc-hover-tooltip-title";
  titleElement.textContent = title;
  tooltip.appendChild(titleElement);
  if (description) {
    const descriptionElement = document.createElement("div");
    descriptionElement.className = "hcc-hover-tooltip-description";
    descriptionElement.textContent = description;
    tooltip.appendChild(descriptionElement);
  }
  tooltip.style.left = `${Math.round(rect.right + 8)}px`;
  tooltip.style.top = `${Math.round(rect.top + rect.height / 2)}px`;
  document.body.appendChild(tooltip);
  tooltipElement = tooltip;
}

function bindTooltip(button, title, description) {
  button.addEventListener("mouseenter", () => showTooltip(button, title, description));
  button.addEventListener("mouseleave", hideTooltip);
  button.addEventListener("click", hideTooltip);
}

function addHeading(parent, text, description = "") {
  const heading = document.createElement("div");
  heading.className = "hcc-native-heading";
  heading.textContent = text;
  if (description) {
    heading.title = description;
    bindTooltip(heading, text, description);
  }
  parent.appendChild(heading);
}

function carouselRowButtonContent(rows) {
  const automatic = Number(rows) === 0;
  const visibleRows = automatic ? 4 : Number(rows);
  const bars = [];
  for (let index = 0; index < visibleRows; index += 1) {
    bars.push('<span class="hcc-native-row-bar"></span>');
  }
  return `<span class="hcc-native-row-bars" aria-hidden="true">${bars.join("")}</span>` +
    `<span class="hcc-native-row-button-label" style="color:#fff!important">${automatic ? "A" : rows}</span>`;
}

function renderNativeFilterPanel() {
  const popover = document.querySelector('[class*="FilterPopover_popover_"]');
  if (!popover) return;
  const nativeCategories = popover.querySelectorAll('[class*="FilterPopover_category_"]');
  if (!nativeCategories.length) return;
  const nativeContent = nativeCategories[nativeCategories.length - 1].parentElement;
  if (!nativeContent) return;

  let section = popover.querySelector(".hcc-native-section");
  if (!section) {
    section = document.createElement("div");
    section.className = "hcc-native-section";
    nativeContent.appendChild(section);
  }

  const signature = JSON.stringify([state.enabled, state.filters, state.activeFilters, state.sorting, state.actionCards, state.carousel]);
  if (section.dataset.signature === signature) return;  // Early exit if no state change
  section.dataset.signature = signature;
  hideTooltip();
  
  // Clear listeners and content by replacing entire section
  const newSection = document.createElement("div");
  newSection.className = "hcc-native-section";
  newSection.dataset.signature = signature;
  
  const refresh = document.createElement("button");
  refresh.type = "button";
  refresh.className = "hcc-native-icon-button";
  refresh.textContent = "↻";
  refresh.title = labels().refresh;
  refresh.setAttribute("aria-label", labels().refresh);
  bindTooltip(refresh, labels().refresh, "");
  newSection.appendChild(refresh);
  refresh.addEventListener("click", () => callCommand("onRefresh"));

  if (state.filtering?.enabled !== false && Array.isArray(state.filters) && state.filters.length) {
    addHeading(newSection, labels().filters, labels().filter_count_description);
    const filters = document.createElement("div");
    filters.className = "hcc-native-filters";
    newSection.appendChild(filters);
    const activeFilters = new Set(state.activeFilters || []);
    for (const filter of state.filters) {
      const filterId = String(filter.id || "");
      if (!filterId) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hcc-native-filter";
      const active = filterId === "all" ? activeFilters.size === 0 : activeFilters.has(filterId);
      if (active) button.classList.add("hcc-native-filter--active");
      const title = labels()[`filter_${filterId}`] || filterId;
      setButtonIcon(button, filterId);
      if (filterId !== "all") {
        const badge = document.createElement("span");
        badge.className = "hcc-native-filter-badge";
        badge.textContent = String(filter.count || 0);
        button.appendChild(badge);
      }
      button.setAttribute("aria-label", title);
      button.setAttribute("aria-pressed", String(active));
      button.title = title;
      bindTooltip(button, title, `${filter.count || 0}`);
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        callCommand("onToggleFilter", { filterId });
      });
      filters.appendChild(button);
    }
  }

  if (state.sorting?.enabled && Array.isArray(state.sorting.options)) {
    addHeading(newSection, labels().sorting);
    const sorting = document.createElement("div");
    sorting.className = "hcc-native-sorting";
    newSection.appendChild(sorting);
    for (const mode of state.sorting.options) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hcc-native-sort-button";
      if (mode === state.sorting.mode) button.classList.add("hcc-native-sort-button--active");
      setButtonGlyph(button, SORT_ICONS[mode] || SORT_ICONS.default, "hcc-native-sort-glyph");
      const title = labels()[`sort_${mode}`] || mode;
      button.setAttribute("aria-label", title);
      button.title = title;
      bindTooltip(button, title, mode === state.sorting.mode
        ? (state.sorting.descending ? labels().descending : labels().ascending)
        : "");
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        callCommand("onSetSorting", { mode, descending: Boolean(state.sorting.descending) });
      });
      sorting.appendChild(button);
    }
    const direction = document.createElement("button");
    direction.type = "button";
    direction.className = "hcc-native-sort-button hcc-native-sort-direction";
    setButtonGlyph(
      direction,
      state.sorting.descending ? SORT_DIRECTION_ICONS.descending : SORT_DIRECTION_ICONS.ascending,
      "hcc-native-sort-direction-glyph"
    );
    direction.title = state.sorting.descending ? labels().descending : labels().ascending;
    bindTooltip(direction, direction.title, labels()[`sort_${state.sorting.mode}`] || state.sorting.mode);
    direction.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      callCommand("onSetSorting", {
        mode: state.sorting.mode || "default",
        descending: !Boolean(state.sorting.descending)
      });
    });
    sorting.appendChild(direction);
  }

  addHeading(newSection, labels().carousel_rows);
  const carouselRows = document.createElement("div");
  carouselRows.className = "hcc-native-carousel-rows";
  newSection.appendChild(carouselRows);
  const automaticRows = state.carousel?.mode === "auto";
  const activeRows = Math.max(1, Math.min(4, Number(state.carousel?.rows || 2)));
  const supportedRows = state.carousel?.supportedRows || [1, 2, 3, 4];
  for (const rows of [0, ...supportedRows]) {
    const automatic = Number(rows) === 0;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hcc-native-row-button";
    if ((automatic && automaticRows) || (!automatic && !automaticRows && Number(rows) === activeRows)) {
      button.classList.add("hcc-native-row-button--active");
    }
    button.innerHTML = carouselRowButtonContent(rows);
    const buttonTitle = automatic ? labels().carousel_auto : `${labels().carousel_rows}: ${rows}`;
    const buttonDescription = automatic ? labels().carousel_auto_description : labels().carousel_rows_description;
    button.setAttribute("aria-label", buttonTitle);
    button.title = buttonTitle;
    bindTooltip(button, buttonTitle, buttonDescription);
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      callCommand("onSetCarouselRows", { rows: Number(rows) });
    });
    carouselRows.appendChild(button);
  }
  
  // Replace old section with new one (clears all old event listeners)
  section.parentElement.replaceChild(newSection, section);
}

function syncModel() {
  const model = findModel();
  if (!model) return;
  const stateJson = String(unwrap(model.stateJson) || "{}");
  const activeFiltersJson = String(unwrap(model.activeFiltersJson) || "[]");
  const stateChanged = stateJson !== lastStateJson;
  const activeFiltersChanged = activeFiltersJson !== lastActiveFiltersJson;
  if (!stateChanged && !activeFiltersChanged) return;
  lastStateJson = stateJson;
  lastActiveFiltersJson = activeFiltersJson;
  if (stateChanged) {
    try {
      const parsedState = JSON.parse(stateJson);
      // Validate payload structure for compatibility
      if (typeof parsedState !== "object" || !("version" in parsedState)) {
        console.warn("[HangarCarouselClassic] Invalid payload structure; expected versioned object");
        state = { stats: {}, statsConfig: {}, sorting: {}, actionCards: {}, carousel: { rows: 2 }, filters: [], activeFilters: [], enabled: false };
        return;
      }
      state = parsedState;
    } catch (error) {
      console.error("[HangarCarouselClassic] Invalid state JSON", error);
      state = { stats: {}, statsConfig: {}, sorting: {}, actionCards: {}, carousel: { rows: 2 }, filters: [], activeFilters: [], enabled: false };
      return;
    }
  }
  try {
    state.activeFilters = JSON.parse(activeFiltersJson);
  } catch (error) {
    state.activeFilters = [];
  }
  scheduleRender();
}

engine.whenReady.then(() => {
  const observer = new MutationObserver(scheduleRender);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["data-test-id"]
  });
  window.engine.on("subViews.onAdded", syncModel);
  // Sync model every 1 second (matches Python refresh rate)
  window.setInterval(syncModel, 1000);
  // Vehicle cards can be mounted after the model state stops changing.
  window.setInterval(scheduleRender, 1000);
  syncModel();
  scheduleRender();
});

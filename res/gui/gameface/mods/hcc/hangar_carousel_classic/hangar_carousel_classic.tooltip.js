const HCC_TOOLTIP_MODEL = "hangarCarouselClassicTooltip";

const HCC_TOOLTIP_LABELS = {
  en: {
    tooltip_statistics: "Vehicle statistics",
    tooltip_battles: "Battles",
    tooltip_win_rate: "Win rate",
    tooltip_average_damage: "Average damage",
    tooltip_alpha_damage: "Alpha damage",
    tooltip_mastery: "Mastery badge",
    tooltip_marks: "Marks of Excellence"
  }
};

let HCCTooltipState = { stats: {}, statsConfig: {} };
let HCCTooltipStateJson = "";
let HCCTooltipScheduled = false;
let HCCTooltipModelLogged = false;
let HCCTooltipRenderLogged = false;

function HCCTooltipUnwrap(value) {
  if (value && typeof value === "object" && Object.prototype.hasOwnProperty.call(value, "value")) {
    return value.value;
  }
  return value;
}

function HCCTooltipLabels() {
  return HCC_TOOLTIP_LABELS.en;
}

function HCCTooltipFindModel() {
  const rootCandidate = window.model?.[HCC_TOOLTIP_MODEL];
  if (rootCandidate) return rootCandidate;
  if (!window.subViews) return null;
  for (const id of window.subViews.ids()) {
    const root = window.subViews.get(id)?.model;
    const candidate = root?.[HCC_TOOLTIP_MODEL];
    if (candidate) return candidate;
  }
  return null;
}

function HCCTooltipFormat(value) {
  return Number(value || 0).toLocaleString();
}

function HCCTooltipWinRateBand(value) {
  const winRate = Number(value || 0);
  if (winRate < 47) return "bad";
  if (winRate < 50) return "below-average";
  if (winRate < 52) return "average";
  if (winRate < 55) return "good";
  if (winRate < 60) return "great";
  return "exceptional";
}

function HCCTooltipMarksLevel(stats) {
  const explicitLevel = Number(stats.marksOnGunLevel || 0);
  if (explicitLevel > 0) return explicitLevel;
  const rating = Number(stats.marksOnGun || 0);
  if (rating >= 95) return 3;
  if (rating >= 85) return 2;
  if (rating >= 65) return 1;
  return 0;
}

function HCCTooltipItems() {
  const stats = HCCTooltipState.stats || {};
  const fields = HCCTooltipState.statsConfig?.fields || [];
  const labels = HCCTooltipLabels();
  const items = [];
  if (fields.includes("battles")) {
    items.push({ label: labels.tooltip_battles, value: HCCTooltipFormat(stats.battles), classes: ["battles"] });
  }
  if (fields.includes("winRate")) {
    const winRate = Number(stats.winRate || 0);
    items.push({
      label: labels.tooltip_win_rate,
      value: `${winRate.toFixed(1)}%`,
      classes: ["win-rate"]
    });
  }
  if (fields.includes("averageDamage")) {
    items.push({
      label: labels.tooltip_average_damage,
      value: HCCTooltipFormat(stats.averageDamage),
      classes: ["damage"]
    });
  }
  if (fields.includes("alphaDamage")) {
    items.push({
      label: labels.tooltip_alpha_damage,
      value: HCCTooltipFormat(stats.alphaDamage),
      classes: ["alpha-damage"]
    });
  }
  if (fields.includes("mastery") && Number(stats.mastery) > 0) {
    const mastery = Number(stats.mastery);
    const badgeClass = mastery === 1 ? 3 : mastery === 3 ? 1 : mastery;
    items.push({
      label: labels.tooltip_mastery,
      value: mastery >= 4 ? "ACE" : `MB ${badgeClass}`,
      classes: ["mastery", `mastery-${mastery}`]
    });
  }
  if (fields.includes("marksOnGun") && Number(stats.marksOnGun) > 0) {
    const level = HCCTooltipMarksLevel(stats);
    const classes = ["marks"];
    if (level > 0) classes.push(`marks-${level}`);
    items.push({
      label: labels.tooltip_marks,
      value: `${Number(stats.marksOnGun).toFixed(2)}%`,
      classes
    });
  }
  return items;
}

function HCCTooltipNativeSectionClass(root) {
  for (const child of root.children) {
    for (const className of child.classList) {
      if (className.startsWith("Tooltip_section_") && !className.startsWith("Tooltip_section__")) {
        return className;
      }
    }
  }
  return "";
}

function HCCTooltipRender() {
  const status = document.querySelector('[class*="Tooltip_status_"]');
  const root = status?.parentElement;
  if (!root) return;

  const minimumBattles = Number(HCCTooltipState.statsConfig?.minimumBattles ?? 1);
  const stats = HCCTooltipState.stats || {};
  let section = root.querySelector(".hcc-tooltip-stats");
  if (HCCTooltipState.statsConfig?.enabled === false || Number(stats.battles || 0) < minimumBattles) {
    if (section) section.remove();
    return;
  }

  const items = HCCTooltipItems();
  if (!items.length) {
    if (section) section.remove();
    return;
  }

  if (!section) {
    section = document.createElement("div");
    const nativeSectionClass = HCCTooltipNativeSectionClass(root);
    section.className = `hcc-tooltip-stats${nativeSectionClass ? ` ${nativeSectionClass}` : ""}`;
    root.insertBefore(section, status);
  }

  if (!HCCTooltipRenderLogged) {
    HCCTooltipRenderLogged = true;
    console.warn(`[mod_hangar_carousel_classic] rendered ${items.length} statistic rows`);
  }

  const signature = JSON.stringify([items]);
  if (section.dataset.signature === signature) return;
  section.dataset.signature = signature;
  section.innerHTML = "";

  const title = document.createElement("div");
  title.className = "hcc-tooltip-stats-title";
  title.textContent = HCCTooltipLabels().tooltip_statistics;
  section.appendChild(title);

  for (const item of items) {
    const row = document.createElement("div");
    row.className = "hcc-tooltip-stat-row";
    const value = document.createElement("div");
    value.className = `hcc-tooltip-stat-value ${item.classes.map((name) => `hcc-tooltip-stat-value--${name}`).join(" ")}`;
    value.textContent = item.value;
    const label = document.createElement("div");
    label.className = "hcc-tooltip-stat-label";
    label.textContent = item.label;
    row.appendChild(value);
    row.appendChild(label);
    section.appendChild(row);
  }
}

function HCCTooltipScheduleRender() {
  if (HCCTooltipScheduled) return;
  HCCTooltipScheduled = true;
  requestAnimationFrame(() => {
    HCCTooltipScheduled = false;
    HCCTooltipRender();
  });
}

function HCCTooltipSyncModel() {
  const model = HCCTooltipFindModel();
  if (!model) return;
  if (!HCCTooltipModelLogged) {
    HCCTooltipModelLogged = true;
    console.warn("[mod_hangar_carousel_classic] statistics model connected");
  }
  const stateJson = String(HCCTooltipUnwrap(model.stateJson) || "{}");
  if (stateJson === HCCTooltipStateJson) return;
  HCCTooltipStateJson = stateJson;
  try {
    HCCTooltipState = JSON.parse(stateJson);
  } catch (error) {
    console.error("[mod_hangar_carousel_classic] Invalid tooltip state JSON", error);
    HCCTooltipState = { stats: {}, statsConfig: {} };
  }
  HCCTooltipScheduleRender();
}

engine.whenReady.then(() => {
  console.warn("[mod_hangar_carousel_classic] script loaded");
  const observer = new MutationObserver(HCCTooltipScheduleRender);
  observer.observe(document.body, { childList: true, subtree: true });
  window.engine.on("subViews.onAdded", HCCTooltipSyncModel);
  window.setInterval(HCCTooltipSyncModel, 200);
  window.setInterval(HCCTooltipRender, 250);
  HCCTooltipSyncModel();
  HCCTooltipScheduleRender();
});

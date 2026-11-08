const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class Element {
  constructor(id = "") {
    this.id = id;
    this.children = [];
    this.dataset = {};
    this.className = "";
    this.attributes = {};
    this.classList = {
      add: () => {},
      contains: (name) => this.className.split(" ").includes(name)
    };
  }
  getAttribute(name) { return name === "data-test-id" ? this.id : this.attributes[name]; }
  removeAttribute(name) { delete this.attributes[name]; }
  querySelector() { return null; }
  appendChild(child) { child.parentElement = this; this.children.push(child); }
  remove() {
    this.parentElement.children = this.parentElement.children.filter((child) => child !== this);
  }
  set innerHTML(value) { assert.equal(value, ""); this.children = []; }
  set textContent(value) { this.text = value; }
  get textContent() { return this.text || this.children.map((child) => child.textContent).join(""); }
}

const sourcePath = path.join(__dirname, "..", "res", "gui", "gameface", "mods", "hcc",
  "hangar_carousel_classic", "hangar_carousel_classic.js");
let cards = [new Element("vehicleCard-1"), new Element("vehicleCard-2")];
const model = { stateJson: "", activeFiltersJson: "[]" };
const context = vm.createContext({
  document: {
    querySelectorAll: () => cards,
    createElement: () => new Element()
  },
  window: { subViews: { ids: () => [1], get: () => ({ model: { hangarCarouselClassic: model } }) } },
  engine: { whenReady: { then: () => {} } },
  requestAnimationFrame: () => {},
  console: { warn: () => {}, error: (...args) => { throw new Error(args.join(" ")); } }
});
vm.runInContext(fs.readFileSync(sourcePath, "utf8"), context);

const stats = {
  1: { battles: 10, alphaDamage: 240 },
  2: { battles: 0, alphaDamage: 320 }
};
function publish(enabled, records = stats) {
  model.stateJson = JSON.stringify({
    version: "test", hangarActive: true, stats: records,
    statsConfig: { enabled, minimumBattles: 1, fields: ["battles", "alphaDamage"] }
  });
  vm.runInContext("syncModel(); renderCardStats();", context);
}
function overlays(card) {
  return card.children.filter((child) => child.className === "hcc-card-stats");
}

publish(true);
assert.equal(overlays(cards[0]).length, 1);
assert.match(overlays(cards[0])[0].textContent, /240/);
assert.equal(overlays(cards[1]).length, 0);
for (let i = 0; i < 3; i += 1) {
  publish(false, {});
  assert.equal(overlays(cards[0]).length, 0);
  publish(true);
  assert.equal(overlays(cards[0]).length, 1, "Off/on must recreate overlays on the same card");
}
cards = [new Element("vehicleCard-2")];
publish(true);
assert.equal(overlays(cards[0]).length, 0, "A different zero-battle card must remain hidden");
cards[0].id = "vehicleCard-1";
vm.runInContext("renderCardStats();", context);
assert.equal(overlays(cards[0]).length, 1, "A recycled eligible card must show its overlay");
console.log("Card-stat off/on, minimum-battle exclusion, changed card set and recycled card tests passed.");

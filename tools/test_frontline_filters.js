const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const patchSource = fs.readFileSync(path.join(__dirname, "patch-native-frontline-carousel.ps1"), "utf8");
const replacements = [...patchSource.matchAll(/'([^'\r\n]+)',\s*\r?\n\s*'([^'\r\n]+)'/g)];
function replacement(prefix) {
  const matches = replacements.filter((match) => match[1].startsWith(prefix));
  assert.equal(matches.length, 1, `Expected exactly one patch for ${prefix}`);
  return { before: matches[0][1], after: matches[0][2] };
}
const sorted = replacement("m=ka.primitive(");
const rendered = replacement("i=(n?l(n.list):m())");
if (process.argv[2]) {
  const bundle = fs.readFileSync(process.argv[2], "utf8");
  for (const patch of [sorted, rendered]) {
    assert.ok(bundle.includes(patch.after), "Built bundle must contain the tested expression");
    assert.ok(!bundle.includes(patch.before), "Built bundle must not retain the unpatched expression");
  }
}

const inventory = [
  { id: "101", inventoryId: "11", level: 8, name: "Alpha", ready: false, trained: true },
  { id: "102", inventoryId: "12", level: 8, name: "Bravo", ready: true, trained: false },
  { id: "103", inventoryId: "13", level: 8, name: "Charlie", ready: true, trained: true },
  { id: "104", inventoryId: "14", level: 8, name: "Delta", ready: false, trained: false },
  { id: "105", inventoryId: "15", level: 10, name: "Echo", ready: false, trained: false }
];
let payload = {};
let playlist;
let nativeFilters = { level: 8 };
let search = "";
let displayed = [];
const statistics = new Map(inventory.map((vehicle) => [vehicle.id, vehicle]));
const nativeIds = new Set(inventory.map((vehicle) => vehicle.id));
let payloadReads = 0;
const context = vm.createContext({
  console,
  ka: { primitive: (callback) => callback },
  c: { getAll: () => inventory },
  e: { requires: {
    filters: { model: {
      hccSortJson: { get: () => { payloadReads += 1; return JSON.stringify(payload); } },
      computes: { nationToIndex: () => ({}) }
    } },
    statistic: { model: { get: (id) => statistics.get(id) } }
  } },
  jn: {},
  bn: (_nations, _types, left, right) => left.id.localeCompare(right.id),
  hn: (filters, vehicle, stats) => Boolean(stats) && (!filters.level || vehicle.level === filters.level),
  gn: (text, vehicle) => vehicle.name.toLowerCase().includes(text.toLowerCase()),
  l: (ids) => ids.map((id) => inventory.find((vehicle) => vehicle.id === id)).filter(Boolean),
  a: { set: (vehicles) => { displayed = Array.from(vehicles, (vehicle) => vehicle.id); } },
  ls: (callback) => callback(),
  r: nativeIds
});
function refresh(patched = true) {
  context.t = nativeFilters;
  context.s = search;
  context.n = playlist;
  vm.runInContext(sorted[patched ? "after" : "before"], context);
  vm.runInContext(`(() => { let i; ${rendered[patched ? "after" : "before"]} })()`, context);
  return displayed;
}
function select(filters, byInventoryId = false) {
  payload = {
    filtered: filters.length > 0,
    allowed: inventory.filter((vehicle) => filters.every((filter) =>
      filter === "not_ready" ? !vehicle.ready : !vehicle.trained
    )).map((vehicle) => byInventoryId ? vehicle.inventoryId : vehicle.id),
    values: {}
  };
}

select(["not_ready"]);
assert.deepEqual(refresh(false), ["101", "102", "103", "104"],
  "Reproduce the old rendered-list bug: HCC filter changes do not affect the carousel");
assert.deepEqual(refresh(), ["101", "104"], "Not-ready filter must change displayed tier-VIII vehicles");
select(["crew_not_maxed"]);
assert.deepEqual(refresh(), ["102", "104"], "Crew filter must change displayed vehicles");
select(["not_ready", "crew_not_maxed"]);
assert.deepEqual(refresh(), ["104"], "Multiple HCC filters must combine with AND");
select([]);
assert.deepEqual(refresh(), ["101", "102", "103", "104"], "Turning filters off must restore the list");
payload = { filtered: true, allowed: [], values: {} };
assert.deepEqual(refresh(), [], "An active filter with no matches must show an empty carousel");
select(["not_ready"], true);
assert.deepEqual(refresh(), ["101", "104"], "Inventory-ID allowlists must work");
search = "delta";
assert.deepEqual(refresh(), ["104"], "Native text search must still intersect HCC filtering");
search = "";
playlist = { list: ["103", "104", "102"] };
select(["crew_not_maxed"]);
assert.deepEqual(refresh(), ["104", "102"], "Playlists must not bypass HCC filtering");
payload.values = { 102: [-20], 104: [-10] };
assert.deepEqual(refresh(), ["102", "104"], "Sort keys must reorder the displayed playlist");
payload = { filtered: false, values: {}, allowed: [] };
assert.deepEqual(refresh(), ["103", "104", "102"], "Default sorting must preserve native playlist order");
playlist = undefined;
payload.values = { 101: [0, 30], 102: [0, 10], 103: [0, 20], 104: [1, 0] };
assert.deepEqual(refresh(), ["102", "103", "101", "104"], "Hierarchical sorting must apply to the actual carousel");
assert.ok(payloadReads > 0, "Rendered expressions must read the observable HCC payload");
assert.deepEqual(inventory.map((vehicle) => vehicle.id), ["101", "102", "103", "104", "105"],
  "Filtering must not mutate the shared native inventory");
nativeIds.delete("104");
select(["not_ready"]);
assert.deepEqual(refresh(), ["101"], "Native membership exclusions must remain effective");
console.log("Frontline rendered-list regression passed: filter toggles, AND, tier VIII, empty matches, inventory IDs, search, playlists and sorting.");

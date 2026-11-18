const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const sourcePath = path.join(__dirname, "..", "res", "gui", "gameface", "mods", "hcc",
  "hangar_carousel_classic", "hangar_carousel_classic.js");
const source = fs.readFileSync(sourcePath, "utf8");
const readyCallbacks = [];
const engineListeners = new Map();
const engine = {
  whenReady: { then: (callback) => readyCallbacks.push(callback) },
  on: (eventName, callback) => {
    const listeners = engineListeners.get(eventName) || new Set();
    listeners.add(callback);
    engineListeners.set(eventName, listeners);
  },
  off: (eventName, callback) => {
    engineListeners.get(eventName)?.delete(callback);
  }
};
const observers = [];
const intervals = new Map();
const animationFrames = new Map();
const windowListeners = new Map();
let nextTimerId = 1;
const body = { classList: { add() {}, remove() {}, toggle() {} } };
const documentElement = { classList: { add() {}, remove() {}, toggle() {} } };
const window = {
  engine,
  addEventListener: (eventName, callback) => {
    const listeners = windowListeners.get(eventName) || new Set();
    listeners.add(callback);
    windowListeners.set(eventName, listeners);
  },
  removeEventListener: (eventName, callback) => windowListeners.get(eventName)?.delete(callback),
  dispatchEvent: (eventName) => {
    for (const callback of [...(windowListeners.get(eventName) || [])]) callback();
  },
  setInterval: (callback, delay) => {
    const id = nextTimerId++;
    intervals.set(id, { callback, delay });
    return id;
  },
  clearInterval: (id) => intervals.delete(id),
  requestAnimationFrame: (callback) => {
    const id = nextTimerId++;
    animationFrames.set(id, callback);
    return id;
  },
  cancelAnimationFrame: (id) => animationFrames.delete(id),
  subViews: { ids: () => [], get: () => null }
};
const document = {
  body,
  documentElement,
  querySelectorAll: () => [],
  createElement: () => ({ remove() {} })
};
class MutationObserver {
  constructor(callback) {
    this.callback = callback;
    this.disconnected = false;
    observers.push(this);
  }
  observe(target, options) {
    this.target = target;
    this.options = options;
  }
  disconnect() {
    this.disconnected = true;
  }
}
function evaluate() {
  const context = vm.createContext({
    MutationObserver,
    document,
    engine,
    window,
    console: { warn() {}, error: (...args) => { throw new Error(args.join(" ")); } }
  });
  vm.runInContext(source, context);
  return context;
}
function listenerCount(eventName) {
  return engineListeners.get(eventName)?.size || 0;
}
function assertStarted(observerIndex) {
  assert.equal(observers[observerIndex].target, body);
  assert.equal(observers[observerIndex].disconnected, false);
  assert.equal(intervals.size, 2);
  assert.equal(listenerCount("subViews.onAdded"), 1);
  assert.equal(animationFrames.size, 1);
}
function assertStopped(observerIndex) {
  assert.equal(observers[observerIndex].disconnected, true);
  assert.equal(intervals.size, 0);
  assert.equal(listenerCount("subViews.onAdded"), 0);
  assert.equal(animationFrames.size, 0);
}

evaluate();
window.dispatchEvent("pageshow");
assert.equal(observers.length, 0, "Initialization waits for the engine readiness signal");
readyCallbacks[0]();
assertStarted(0);
window.dispatchEvent("pageshow");
assertStarted(0);
assert.equal(observers.length, 1, "Repeated pageshow events must not duplicate resources");

window.dispatchEvent("pagehide");
assertStopped(0);
window.dispatchEvent("pagehide");
assertStopped(0);
window.dispatchEvent("pageshow");
assertStarted(1);

evaluate();
assertStopped(1);
assert.equal(windowListeners.get("pagehide").size, 1, "Reinitialization must replace lifecycle handlers");
assert.equal(windowListeners.get("pageshow").size, 1, "Reinitialization must not duplicate lifecycle handlers");
readyCallbacks[0]();
assert.equal(observers.length, 2, "A disposed readiness callback must not restart old resources");
readyCallbacks[1]();
assertStarted(2);

window.dispatchEvent("pagehide");
assertStopped(2);
window.dispatchEvent("pagehide");
assertStopped(2);
console.log("GameFace lifecycle teardown and reinitialization tests passed.");

import assert from 'node:assert/strict';
import fs from 'node:fs';

class MemoryStorage {
  constructor() { this.data = new Map(); }
  getItem(key) { return this.data.has(key) ? this.data.get(key) : null; }
  setItem(key, value) { this.data.set(key, String(value)); }
  removeItem(key) { this.data.delete(key); }
}

class FakeClassList {
  constructor() { this.values = new Set(); }
  toggle(name, enabled) { enabled ? this.values.add(name) : this.values.delete(name); }
}

class FakeElement {
  constructor() {
    this.id = '';
    this.parentNode = null;
    this.textContent = '';
    this.innerHTML = '';
    this.title = '';
    this.classList = new FakeClassList();
    this.attributes = new Map();
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  appendChild(child) { child.parentNode = this; return child; }
  insertBefore(child) { child.parentNode = this; return child; }
}

const elements = new Map();
const statTargets = new Map([
  ['visitors', new FakeElement()],
  ['games', new FakeElement()],
  ['online', new FakeElement()]
]);
const windowListeners = new Map();
const documentListeners = new Map();
const body = new FakeElement();
body.appendChild = child => { if (child.id) elements.set(child.id, child); child.parentNode = body; return child; };

globalThis.window = globalThis;
globalThis.localStorage = new MemoryStorage();
globalThis.sessionStorage = new MemoryStorage();
Object.defineProperty(globalThis, 'navigator', {
  configurable: true,
  value: { onLine: true }
});
globalThis.document = {
  readyState: 'complete',
  visibilityState: 'visible',
  head: new FakeElement(),
  body,
  getElementById(id) { return elements.get(id) || null; },
  createElement() { return new FakeElement(); },
  querySelector(selector) {
    const match = selector.match(/data-s2="([^"]+)"/);
    return match ? statTargets.get(match[1]) : null;
  },
  addEventListener(name, handler) { documentListeners.set(name, handler); }
};
globalThis.addEventListener = (name, handler) => windowListeners.set(name, handler);
globalThis.setInterval = () => 1;

let offline = false;
let games = 48;
let online = 0;
const completedEvents = new Set();
const calls = [];
globalThis.fetch = async (url, options = {}) => {
  const name = String(url).split('/').at(-1);
  calls.push(name);
  if (offline) throw new Error('offline');
  let data = { visitors: 12, games, online };
  if (name === 'snake2_level_started') {
    online = 1;
    data = { ...data, online, accepted: true, duplicate: false };
  } else if (name === 'snake2_level_completed') {
    const eventId = JSON.parse(options.body || '{}').p_event_id;
    if (!completedEvents.has(eventId)) { completedEvents.add(eventId); games += 1; }
    data = { visitors: 12, games, online, accepted: true, duplicate: false };
  } else if (name === 'snake2_leave') {
    online = 0;
    data = { visitors: 12, games, online };
  }
  return { ok: true, json: async () => data };
};

const source = fs.readFileSync(new URL('./snake2-stats.js', import.meta.url), 'utf8');
const originalDebug = console.debug;
console.debug = () => {};
(0, eval)(source);
await new Promise(resolve => setTimeout(resolve, 30));

window.snake2TrackLevelStart({ level: 7, daily: false });
await new Promise(resolve => setTimeout(resolve, 30));
window.snake2TrackLevelComplete({ level: 7, daily: false });
await new Promise(resolve => setTimeout(resolve, 80));
assert.equal(games, 49);
assert.equal(localStorage.getItem('snake2_pending_completions_v2'), null);

const completionsBeforeDuplicate = calls.filter(name => name === 'snake2_level_completed').length;
window.snake2TrackLevelComplete({ level: 7, daily: false });
await new Promise(resolve => setTimeout(resolve, 30));
assert.equal(calls.filter(name => name === 'snake2_level_completed').length, completionsBeforeDuplicate);

offline = true;
navigator.onLine = false;
window.snake2TrackLevelStart({ level: 8, daily: false });
await new Promise(resolve => setTimeout(resolve, 20));
window.snake2TrackLevelComplete({ level: 8, daily: false });
await new Promise(resolve => setTimeout(resolve, 30));
assert.ok(localStorage.getItem('snake2_pending_completions_v2'));

offline = false;
navigator.onLine = true;
windowListeners.get('online')();
await new Promise(resolve => setTimeout(resolve, 120));
assert.equal(games, 50);
assert.equal(localStorage.getItem('snake2_pending_completions_v2'), null);
assert.equal(statTargets.get('games').textContent, '50');

console.debug = originalDebug;
console.log(JSON.stringify({
  passed: true,
  games,
  completionCalls: calls.filter(name => name === 'snake2_level_completed').length,
  pendingQueueEmpty: localStorage.getItem('snake2_pending_completions_v2') === null
}));

import fs from 'node:fs';
import assert from 'node:assert/strict';

const game = fs.readFileSync('./dist/game.js', 'utf8');
const index = fs.readFileSync('./dist/index.html', 'utf8');
const install = fs.readFileSync('./dist/install-gate-v225.js', 'utf8');
const sw = fs.readFileSync('./dist/sw.js', 'utf8');

const mustContain = [
  [game, "const VERSION = '2.2.11'", 'runtime version'],
  [game, 'hapticsRuntimeVersion: 0', 'haptics migration field'],
  [game, 'save.hapticsRuntimeVersion = 1', 'haptics one-time migration'],
  [game, "typeof navigator.vibrate !== 'function'", 'vibration API guard'],
  [game, 'navigator.userActivation.hasBeenActive', 'user activation guard'],
  [game, 'return navigator.vibrate(pattern) === true', 'vibration result handling'],
  [game, 'vibrate(35);', 'green apple haptic'],
  [game, 'window.setTimeout(() => vibrate(45), 55);', 'ordinary food second pulse'],
  [game, "vibrate(kind === 'gold' ? [45, 30, 70] : 35)", 'bonus haptic'],
  [game, 'vibrate([70, 35, 110])', 'settings test haptic'],
  [game, "toast(hapticOk ? 'Vibrations activées'", 'settings feedback'],
  [index, 'game.js?v=2.2.11-volume1', 'game cache bust'],
  [index, 'install-gate-v225.js?v=2.2.11-volume1', 'install gate cache bust'],
  [install, "serviceWorker.register('./sw.js?v=2.2.11-volume1'", 'service worker registration'],
  [sw, "const CACHE = 'snake-2.0-v2.2.11-volume-20260817-v1'", 'service worker cache'],
];

for (const [source, needle, label] of mustContain) {
  assert.ok(source.includes(needle), `Missing ${label}: ${needle}`);
}

assert.ok(!game.includes('function vibrate(ms = 25)'), 'Legacy silent vibration helper is still present');
assert.ok(!game.includes('vibrate(18);'), 'Imperceptible 18 ms apple vibration is still present');
console.log('Snake 2.0 haptic runtime checks passed');

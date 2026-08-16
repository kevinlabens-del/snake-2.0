import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const game = fs.readFileSync('./dist/game.js', 'utf8');

const start = game.indexOf('  function effectiveMusicVolume(percent) {');
const end = game.indexOf('\n\n  function syncAudio()', start);
assert.notEqual(start, -1, 'effectiveMusicVolume start missing');
assert.notEqual(end, -1, 'effectiveMusicVolume end missing');
const source = game.slice(start, end);
const context = vm.createContext({});
vm.runInContext(`${source}\nglobalThis.effectiveMusicVolume = effectiveMusicVolume;`, context);

const map = context.effectiveMusicVolume;
assert.equal(map(0), 0, '0% must remain silent');
assert.ok(Math.abs(map(75) - 0.06) < 1e-12, '75% must equal the old 6% effective volume');
assert.ok(Math.abs(map(100) - 0.08) < 1e-12, '100% must remain capped at a safe 8% effective volume');
assert.ok(Math.abs(map(50) - 0.04) < 1e-12, '50% should map to 4% effective volume');
assert.ok(map(25) < map(50) && map(50) < map(75) && map(75) < map(100), 'volume mapping must be monotonic');

assert.ok(game.includes('audioVolumeRuntimeVersion: 0'), 'audio migration field missing');
assert.ok(game.includes('legacyMusicVolume * 12.5'), 'legacy slider migration missing');
assert.ok(game.includes('music?.setVolume(effectiveMusicVolume(musicVolume))'), 'syncAudio bypasses calibrated curve');
assert.ok(game.includes('music?.setVolume(effectiveMusicVolume(save.musicVolume))'), 'live slider bypasses calibrated curve');
assert.ok(!game.includes('music?.setVolume(save.musicVolume / 100)'), 'legacy direct slider mapping is still present');

console.log(JSON.stringify({
  passed: true,
  slider75Effective: map(75),
  slider100Effective: map(100),
  legacy6MigratesTo: 6 * 12.5,
}));

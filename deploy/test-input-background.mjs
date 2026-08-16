import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';


const gamePath = path.resolve('dist/game.js');
const swPath = path.resolve('dist/sw.js');
const indexPath = path.resolve('dist/index.html');
const game = fs.readFileSync(gamePath, 'utf8');
const sw = fs.readFileSync(swPath, 'utf8');
const index = fs.readFileSync(indexPath, 'utf8');

function sliceBetween(source, startMarker, endMarker, label) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(start, -1, `${label}: start marker missing`);
  assert.notEqual(end, -1, `${label}: end marker missing`);
  return source.slice(start, end);
}

// Exercise the production direction function itself. Two perpendicular turns
// entered inside one movement interval must be preserved in their original order.
const directionSource = sliceBetween(
  game,
  '  const MAX_DIRECTION_QUEUE = 2;',
  '\n\n  function eatGreen()',
  'direction runtime',
);
const directionState = {
  running: true,
  paused: false,
  dir: { x: 1, y: 0 },
  nextDir: { x: 1, y: 0 },
  inputQueue: [],
};
const directionContext = vm.createContext({
  state: directionState,
  missionSettings: () => ({}),
  missionElapsed: () => 0,
  levelEngine: { record() {} },
  beep() {},
  performance: { now: () => 123 },
});
vm.runInContext(`${directionSource}\nglobalThis.queueDirection = setDir;`, directionContext);

assert.equal(directionContext.queueDirection(0, -1, 'keyboard'), true);
assert.equal(directionContext.queueDirection(-1, 0, 'keyboard'), true);
assert.equal(directionContext.queueDirection(0, 1, 'keyboard'), false, 'queue must remain bounded');
assert.deepEqual(
  directionState.inputQueue.map(({ x, y }) => [x, y]),
  [[0, -1], [-1, 0]],
  'rapid turns were not preserved',
);

// Execute the exact queue-consumption statements used at each grid step.
const consumeSource = sliceBetween(
  game,
  '    const queuedDirection = state.inputQueue.shift();',
  '    let head = {',
  'direction consumption',
);
vm.runInContext(`globalThis.consumeDirection = () => {\n${consumeSource}\n};`, directionContext);
directionContext.consumeDirection();
assert.deepEqual([directionState.dir.x, directionState.dir.y], [0, -1]);
assert.deepEqual([directionState.nextDir.x, directionState.nextDir.y], [-1, 0]);
directionContext.consumeDirection();
assert.deepEqual([directionState.dir.x, directionState.dir.y], [-1, 0]);
assert.equal(directionState.inputQueue.length, 0);

// The pointer handler must commit a swipe as soon as its movement crosses the
// threshold; waiting for pointerup was the source of the mobile delay.
const pointerMove = game.indexOf("gameShell.addEventListener('pointermove'");
const pointerUp = game.indexOf("gameShell.addEventListener('pointerup'");
assert.ok(pointerMove >= 0 && pointerMove < pointerUp, 'pointermove must handle swipes before pointerup');
assert.match(
  game.slice(pointerMove, pointerUp),
  /consumeSwipeDirection\(e\)/,
  'pointermove does not dispatch the swipe',
);
assert.match(game, /addEventListener\('keydown',[\s\S]*?e\.code[\s\S]*?capture: true/);

// Exercise the production critical-asset selector. Starting the game must not
// trigger a burst of all terrain photographs.
const loadAssetsSource = sliceBetween(
  game,
  '  async function loadAssets() {',
  '\n\n  function currentGameplayBackground()',
  'critical asset loader',
);
const loadedKeys = [];
const assetContext = vm.createContext({
  assetManifest: {
    head: './assets/sprites/head.png',
    body: './assets/sprites/body.png',
    backgroundForest: './assets/backgrounds/forest.jpg',
    backgroundDesert: './assets/backgrounds/desert.jpg',
  },
  assets: {},
  loadImageAsset: async key => {
    loadedKeys.push(key);
    return true;
  },
  buildBodyWarpFrames() {},
});
vm.runInContext(`${loadAssetsSource}\nglobalThis.loadCriticalAssets = loadAssets;`, assetContext);
assert.equal(await assetContext.loadCriticalAssets(), true);
assert.deepEqual(loadedKeys, ['head', 'body']);

const backgroundCatalog = sliceBetween(
  game,
  '  const gameplayBackgroundCatalog = Object.freeze([',
  '\n  ]);',
  'terrain catalog',
);
const backgroundEntries = [...backgroundCatalog.matchAll(/file:\s*'([^']+)'/g)];
assert.equal(backgroundEntries.length, 150, 'all 150 gameplay terrains must be selectable');
assert.equal((backgroundCatalog.match(/overlay:\s*'rgba\(0,0,0,0\)'/g) || []).length, 150,
  'every terrain must explicitly use a transparent overlay');
for (const [, filename] of backgroundEntries) {
  const relativePath = path.join('assets', 'backgrounds', filename);
  assert.ok(fs.existsSync(path.resolve('dist', relativePath)), `missing terrain file: ${relativePath}`);
}
assert.match(game, /background\.src \|\| assetManifest\[background\.key\]/, 'bank backgrounds must use their lazy source URL');
assert.match(game, /frameCtx\.fillStyle = background\.overlay \|\| 'rgba\(0,0,0,0\)'/,
  'background renderer must never reuse an opaque fillStyle when overlay is absent');
assert.doesNotMatch(sw, /'\.\/assets\/backgrounds\//, 'terrain images must be cached lazily');
assert.match(game, /await selectRandomGameplayBackground\(\);/);
assert.match(game, /scheduleGameplayBackgroundRetry/);
assert.match(game, /assetErrors\.delete\(background\.key\)/);

for (const filename of ['manifest.webmanifest', 'styles-v225.css', 'install-gate-v225.js', 'game.js']) {
  assert.ok(index.includes(`${filename}?v=2.2.9-input-background1`), `${filename} release id is stale`);
}

console.log(JSON.stringify({
  passed: true,
  rapidTurns: 2,
  criticalAssetsLoaded: loadedKeys.length,
  terrainFiles: backgroundEntries.length,
  terrainTransparentOverlays: 150,
  terrainPrecacheEntries: 0,
}));

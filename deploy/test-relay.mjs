import assert from 'node:assert/strict';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';

// Apply the relay-specific playability correction after the main relay patch.
// This mutates the rebuilt dist/ files that are subsequently uploaded to Pages.
execFileSync('python3', ['deploy/patch-relay-playability.py'], { stdio: 'inherit' });
// Verify the artwork itself—not only the collision box—fills exactly 2x2 cells.
execFileSync('python3', ['deploy/test-relay-visual.py'], { stdio: 'inherit' });

const require = createRequire(import.meta.url);
const Levels = require('../dist/apple-snake-levels.js');
const game = fs.readFileSync('./dist/game.js', 'utf8');

const expectedTargets = [1,2,3,4,5];
const expectedObstacles = [0,1,2,3,4];
for (let i = 0; i < 5; i++) {
  const level = 71 + i;
  const mission = Levels.getMission(level, {}, { adaptive:false, seed:level });
  assert.equal(mission.missionType, 'intervals', `L${level}: not a relay mission`);
  assert.equal(Number(mission.settings.intervalCount), expectedTargets[i], `L${level}: wrong relay target`);
  assert.equal(mission.settings.intervalTimeSec, undefined, `L${level}: legacy relay timer still active`);
  assert.equal(mission.settings.intervalTarget, undefined, `L${level}: legacy apple relay target still active`);
  assert.equal(Number(mission.settings.obstacles || 0), expectedObstacles[i], `L${level}: wrong obstacle progression`);
  assert.ok(Number(mission.settings.obstacles || 0) <= 4, `L${level}: relay arena is too crowded`);
  const objective = mission.objectives.find(o => o.metric === 'intervals.completed');
  assert.ok(objective, `L${level}: relay objective missing`);
  assert.equal(Number(objective.value), expectedTargets[i], `L${level}: objective target mismatch`);
}

for (const needle of [
  'function relayMissionActive()',
  'function relayTarget()',
  'relayNestCells(nest = state.relayNest)',
  'const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2',
  'ctx.drawImage(assets.relayNest,3,5,26,19,x,y,size,size)',
  'drawRelayNestSquirrels(x,y,state.relayCompleted,Boolean(state.relayPendingCompleteAt))',
  'if (relayMissionActive()) { state.greenFood = null; return; }',
  'if (relayMissionActive()) { state.specialFood = null; return; }',
  'state.relayCompleted+=1;',
  "levelEngine?.record('intervalComplete')",
  'spawnRelayRound();'
]) assert.ok(game.includes(needle), `game.js missing relay guard: ${needle}`);

const duplicateRelayObstacleBuild = `    if (relayMissionActive()) {\n      state.greenFood = null;\n      state.specialFood = null;\n      buildMissionObstacles();\n      spawnRelayRound();\n    } else {`;
assert.equal(game.includes(duplicateRelayObstacleBuild), false, 'relay obstacle generation is duplicated');

const correctedRelayStart = `    if (relayMissionActive()) {\n      state.greenFood = null;\n      state.specialFood = null;\n      spawnRelayRound();\n    } else {`;
assert.ok(game.includes(correctedRelayStart), 'corrected relay start block missing');

for (const asset of ['./dist/assets/relay/squirrel.png','./dist/assets/relay/nest.png']) {
  const data = fs.readFileSync(asset);
  assert.equal(data.subarray(0,8).toString('hex'), '89504e470d0a1a0a', `${asset}: invalid PNG`);
}

console.log(JSON.stringify({passed:true, relayLevels:'71-75', targets:expectedTargets, obstacles:expectedObstacles, maxObstacles:4, duplicateObstacleBuild:false, nestVisible:'2x2-exact', apples:false, persistentSquirrels:true}));

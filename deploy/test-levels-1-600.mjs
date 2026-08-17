import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const Levels = require('../dist/apple-snake-levels.js');

const profiles = [
  { successRate:.35, deathRate:.55, streak:0, averageScore:70, averageCompletionSec:80 },
  { successRate:.55, deathRate:.30, streak:1, averageScore:130, averageCompletionSec:60 },
  { successRate:.68, deathRate:.22, streak:4, averageScore:180, averageCompletionSec:42 },
  { successRate:.90, deathRate:.05, streak:12, averageScore:450, averageCompletionSec:24 },
];
const ops = new Set(['>=','>','<=','<','==','!=']);
let assertions = 0;
const nested = (o,p) => p.split('.').reduce((a,k)=>a?.[k],o);
const satisfy = o => o.operator==='>' && typeof o.value==='number' ? o.value+1 : o.operator==='<' && typeof o.value==='number' ? o.value-1 : o.value;
const violate = f => f.operator==='>' ? (typeof f.value==='number'?f.value+1:true) : f.operator==='>=' ? f.value : f.operator==='<' ? (typeof f.value==='number'?f.value-1:false) : f.operator==='<=' ? f.value : f.value;

for (const profile of profiles) {
  for (let level=1; level<=600; level++) {
    const m = Levels.getMission(level, profile, { adaptive:true, seed:level });
    assert.equal(m.globalLevel, level); assertions++;
    assert.ok(m.id && m.title && m.description && m.objectives.length); assertions++;
    assert.ok(Number(m.settings.lives || 1) >= 1 && Number(m.settings.speedMultiplier || 1) > 0); assertions++;
    for (const c of [...m.objectives, ...m.failConditions]) {
      assert.ok(c.metric && ops.has(c.operator), `L${level}: invalid condition`); assertions++;
      if (typeof c.value === 'number') assert.ok(Number.isFinite(c.value), `L${level}: invalid numeric target`); assertions++;
    }

    const timeLimit = Number(m.settings.timeLimitSec || 0);
    const nonTime = m.objectives.some(o => o.metric !== 'time.elapsed');
    if (timeLimit && nonTime) {
      const deadline = m.failConditions.find(f => f.metric==='time.elapsed' && f.operator==='>');
      assert.ok(deadline, `L${level}: countdown has no fail condition`); assertions++;
      assert.equal(Number(deadline.value), timeLimit, `L${level}: deadline mismatch`); assertions++;
    }
    const survival = Math.max(0, ...m.objectives.filter(o=>o.metric==='time.elapsed' && ['>=','>'].includes(o.operator)).map(o=>Number(o.value)||0));
    if (timeLimit && survival && nonTime) { assert.ok(timeLimit >= survival + 8, `L${level}: survival has no completion margin`); assertions++; }

    for (const o of m.objectives) {
      const same = m.failConditions.filter(f=>f.metric===o.metric);
      if (o.metric==='turns' && o.operator==='<=') {
        const f=same.find(f=>f.operator==='>'); assert.ok(f, `L${level}: turn mission can become unwinnable`); assertions++;
        assert.equal(Number(f.value), Number(o.value)); assertions++;
      }
      if (typeof o.value==='number' && ['<=','<','=='].includes(o.operator)) {
        for (const f of same.filter(f=>['>','>='].includes(f.operator))) { assert.equal(Number(f.value), Number(o.value), `L${level}: adaptive fail threshold mismatch`); assertions++; }
      }
    }

    const combo = m.objectives.find(o=>o.metric==='combo.max' && ['>=','>'].includes(o.operator));
    const windowSec = Number(m.settings.comboWindowSec || 0);
    if (combo && windowSec) {
      const fair = Math.min(10, 6 + Math.ceil(Number(combo.value)/6));
      assert.ok(windowSec >= fair, `L${level}: combo window too short`); assertions++;
      const e=Levels.createEngine({profile}); e.startLevel(level,profile,{adaptive:true,seed:level});
      const target=Math.ceil(Number(combo.value)+(combo.operator==='>'?1:0));
      for(let i=0;i<target;i++){ if(i)e.record('tick',{deltaSec:Math.min(3,windowSec-.25)}); e.record('apple',{kind:'classic',points:10,length:4+i}); }
      assert.ok(Number(nested(e.snapshot().metrics,'combo.max')) >= target, `L${level}: combo runtime failed`); assertions++;
    }

    const apples = Math.max(0, ...m.objectives.filter(o=>o.metric==='apples.total' && ['>=','>'].includes(o.operator)).map(o=>Number(o.value)||0));
    if (timeLimit && apples) { assert.ok(timeLimit >= Math.ceil(apples*2.8+8), `L${level}: timed collection too RNG-dependent`); assertions++; }

    const engine = Levels.createEngine({profile});
    const started = engine.startLevel(level, profile, {adaptive:true, seed:level});
    assert.deepEqual(started.mission, m, `L${level}: preview differs from launched mission`); assertions++;
    const metrics={}; for(const o of m.objectives) metrics[o.metric]=satisfy(o);
    assert.equal(engine.record('__batch__',{metrics}).status,'complete',`L${level}: all objectives satisfied but mission not complete`); assertions++;

    for (const f of m.failConditions) {
      const failEngine=Levels.createEngine({profile}); failEngine.startLevel(level,profile,{adaptive:true,seed:level});
      const value=String(f.metric).startsWith('collisions.') && f.operator==='>' && Number(f.value)===0 ? Math.max(1,Number(m.settings.lives)||1) : violate(f);
      assert.equal(failEngine.record('__batch__',{metrics:{[f.metric]:value}}).status,'failed',`L${level}: fail condition ${f.metric} is inert`); assertions++;
    }
    if (timeLimit && nonTime) {
      const timer=Levels.createEngine({profile}); timer.startLevel(level,profile,{adaptive:true,seed:level});
      assert.equal(timer.record('tick',{deltaSec:timeLimit+.01}).status,'failed',`L${level}: timer reaches zero without failing`); assertions++;
    }
  }
}

// Endless smoke test: same systemic invariants must keep holding after level 600.
for (let level=601; level<=2000; level++) {
  const m=Levels.getMission(level,profiles[2],{adaptive:true,seed:level});
  const t=Number(m.settings.timeLimitSec||0), nonTime=m.objectives.some(o=>o.metric!=='time.elapsed');
  if(t&&nonTime){const f=m.failConditions.find(f=>f.metric==='time.elapsed'&&f.operator==='>'); assert.ok(f&&Number(f.value)===t,`L${level}: endless deadline mismatch`); assertions++;}
}

console.log(JSON.stringify({passed:true, levels:'1-600', profiles:profiles.length, endlessSmoke:'601-2000', assertions}));

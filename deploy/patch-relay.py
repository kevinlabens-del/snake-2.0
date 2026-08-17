from pathlib import Path
import base64, json, re

GAME = Path('game.js') if Path('game.js').exists() else Path('dist/game.js')
LEVELS = Path('apple-snake-levels.js') if Path('apple-snake-levels.js').exists() else Path('dist/apple-snake-levels.js')
ROOT = GAME.parent
DEPLOY = Path('deploy')

# Decode committed transparent PNG assets into the deployed app.
asset_dir = ROOT / 'assets' / 'relay'
asset_dir.mkdir(parents=True, exist_ok=True)
for src_name, dst_name in [('relay-squirrel.png.b64','squirrel.png'),('relay-nest.png.b64','nest.png')]:
    src = DEPLOY / src_name
    if not src.exists():
        raise SystemExit(f'missing relay asset source: {src}')
    raw = base64.b64decode(''.join(src.read_text(encoding='utf-8').split()))
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise SystemExit(f'invalid PNG payload: {src}')
    (asset_dir / dst_name).write_bytes(raw)

js = GAME.read_text(encoding='utf-8')

def once(old, new, label):
    global js
    if new in js:
        return
    if old not in js:
        raise SystemExit(f'{label} marker missing')
    js = js.replace(old, new, 1)

# State + assets.
once("    specialFood: null,\n    score: 0,", "    specialFood: null,\n    relaySquirrel: null,\n    relayNest: null,\n    relayCarrying: false,\n    relayPendingCompleteAt: 0,\n    relayCompleted: 0,\n    score: 0,", 'relay state')
once("    malusScorpion: ASSET_BASE + 'malus-scorpion.png',", "    malusScorpion: ASSET_BASE + 'malus-scorpion.png',\n    relaySquirrel: './assets/relay/squirrel.png',\n    relayNest: './assets/relay/nest.png',", 'relay assets')

# Helpers inserted before freeCell().
helpers = r'''  function relayMissionActive() {
    return state.mission?.missionType === 'intervals';
  }

  function relayTarget() {
    if (!relayMissionActive()) return 0;
    const objective = state.mission?.objectives?.find(o => o.metric === 'intervals.completed');
    return Math.max(1, Number(objective?.value || missionSettings().intervalCount || 1));
  }

  function relayNestCells(nest = state.relayNest) {
    if (!nest) return [];
    return [{x:nest.x,y:nest.y},{x:nest.x+1,y:nest.y},{x:nest.x,y:nest.y+1},{x:nest.x+1,y:nest.y+1}];
  }

  function relayCellOccupied(p, ignoreRelay = false) {
    return !cellInsideBoard(p) || state.snake.some(s => same(s,p)) || same(state.greenFood,p)
      || (state.specialFood && same(state.specialFood,p)) || (state.portal && same(state.portal,p))
      || (state.lockedPortal && same(state.lockedPortal,p)) || state.decoyPortals.some(q => same(q,p))
      || isObstacleCell(p) || (!ignoreRelay && state.relaySquirrel && same(state.relaySquirrel,p))
      || (!ignoreRelay && relayNestCells().some(c => same(c,p)));
  }

  function freeRelayNest() {
    const min = Math.max(0,state.boardMargin), max = Math.min(cells-2,cells-state.boardMargin-2);
    for (let tries=0; tries<1600; tries++) {
      const x=min+((Math.random()*Math.max(1,max-min+1))|0), y=min+((Math.random()*Math.max(1,max-min+1))|0);
      const area=[{x,y},{x:x+1,y},{x,y:y+1},{x:x+1,y:y+1}];
      if (area.every(p => !relayCellOccupied(p,true))) return {x,y};
    }
    return {x:min,y:min};
  }

  function freeRelaySquirrel() {
    for (let tries=0; tries<1600; tries++) {
      const p={x:(Math.random()*cells)|0,y:(Math.random()*cells)|0};
      if (!relayCellOccupied(p)) return p;
    }
    return freeCell();
  }

  function spawnRelayRound() {
    if (!relayMissionActive() || !state.running || state.relayCompleted >= relayTarget()) return;
    state.relayNest=freeRelayNest();
    state.relaySquirrel=freeRelaySquirrel();
    state.relayCarrying=false;
    state.relayPendingCompleteAt=0;
  }

  function updateRelay(head) {
    if (!relayMissionActive()) return;
    const now=performance.now();
    if (state.relayPendingCompleteAt && now >= state.relayPendingCompleteAt) {
      state.relayPendingCompleteAt=0;
      state.relayCompleted+=1;
      levelEngine?.record('intervalComplete');
      if (!state.running) return;
      if (state.relayCompleted < relayTarget()) {
        spawnRelayRound();
        toast(`Relais ${state.relayCompleted}/${relayTarget()}`);
      }
      return;
    }
    if (!head || state.relayPendingCompleteAt) return;
    if (!state.relayCarrying && state.relaySquirrel && same(head,state.relaySquirrel)) {
      state.relayCarrying=true;
      state.relaySquirrel=null;
      state.headOpenUntil=now+220;
      beep('eat'); vibrate(35);
      toast('Écureuil récupéré · ramène-le au nid');
      return;
    }
    if (state.relayCarrying && relayNestCells().some(c => same(c,head))) {
      state.relayCarrying=false;
      state.relayPendingCompleteAt=now+650;
      beep('eat'); vibrate([45,30,70]);
      toast('Écureuil déposé dans le nid ✓');
    }
  }

  function drawRelayNestSquirrels(x, y, count, includePending = false) {
    if (!assets.relaySquirrel) return;
    const total = Math.max(0, Number(count || 0)) + (includePending ? 1 : 0);
    if (!total) return;
    const shown = Math.min(total, 9);
    const cols = shown <= 4 ? 2 : 3;
    const rows = Math.ceil(shown / cols);
    const icon = cell * (shown <= 4 ? .82 : .60);
    const spreadX = cell * 1.12;
    const spreadY = cell * .86;
    for (let i=0;i<shown;i++) {
      const col=i%cols, row=Math.floor(i/cols);
      const px=x+cell+(col-(cols-1)/2)*(spreadX/Math.max(1,cols-1));
      const py=y+cell+(row-(rows-1)/2)*(spreadY/Math.max(1,rows-1));
      drawImageContain(assets.relaySquirrel,px-icon/2,py-icon*.64,icon,icon);
    }
    if (total > shown) {
      ctx.save();
      ctx.fillStyle='#d7ffbf'; ctx.font=`700 ${Math.max(10,cell*.52)}px system-ui`;
      ctx.textAlign='right'; ctx.textBaseline='bottom';
      ctx.fillText(`+${total-shown}`,x+cell*1.92,y+cell*1.92);
      ctx.restore();
    }
  }

'''
if 'function relayMissionActive()' not in js:
    if '  function freeCell() {' not in js:
        raise SystemExit('freeCell marker missing')
    js = js.replace('  function freeCell() {', helpers + '  function freeCell() {', 1)

# freeCell must reserve the 2x2 nest and loose squirrel.
once("        || state.decoyPortals.some(portal => same(portal, p))\n        || isObstacleCell(p);", "        || state.decoyPortals.some(portal => same(portal, p))\n        || (state.relaySquirrel && same(state.relaySquirrel, p))\n        || relayNestCells().some(c => same(c, p))\n        || isObstacleCell(p);", 'free cell relay exclusion')

# Reset relay state with every run.
once("    state.specialFood = null;\n    state.headOpenUntil = 0;", "    state.specialFood = null;\n    state.relaySquirrel = null;\n    state.relayNest = null;\n    state.relayCarrying = false;\n    state.relayPendingCompleteAt = 0;\n    state.relayCompleted = 0;\n    state.headOpenUntil = 0;", 'reset relay state')

# Relay missions never spawn apples. Their challenge can still come from mission obstacles.
old_start = """    if (!state.portal && snapshot.portalUnlocked) spawnExitPortal();
    spawnGreen();
    if (missionSpecialPool().length || missionSettings().numberedAppleCount) maybeSpawnSpecial(true);
    else if (!missionSettings().exactScore && Math.random() < .35) maybeSpawnSpecial(true);"""
new_start = """    if (!state.portal && snapshot.portalUnlocked) spawnExitPortal();
    if (relayMissionActive()) {
      state.greenFood = null;
      state.specialFood = null;
      buildMissionObstacles();
      spawnRelayRound();
    } else {
      spawnGreen();
      if (missionSpecialPool().length || missionSettings().numberedAppleCount) maybeSpawnSpecial(true);
      else if (!missionSettings().exactScore && Math.random() < .35) maybeSpawnSpecial(true);
    }"""
once(old_start, new_start, 'relay start without apples')

# Process pickup/deposit immediately after the snake head advances.
once("    state.snake.unshift(head);\n    if (state.respawnGraceMoves > 0) state.respawnGraceMoves--;\n    updateZoneProgress(head);", "    state.snake.unshift(head);\n    if (state.respawnGraceMoves > 0) state.respawnGraceMoves--;\n    updateRelay(head);\n    if (!state.running) return;\n    updateZoneProgress(head);", 'relay collision')

# Disable legacy timed interval/apple mechanics for relay missions.
once("    if (settings.intervalCount && settings.intervalTimeSec && levelEngine.status === 'running') {", "    if (!relayMissionActive() && settings.intervalCount && settings.intervalTimeSec && levelEngine.status === 'running') {", 'old interval runtime')

# Block all apple generation during relay missions.
once("  function spawnGreen() {\n    const settings = missionSettings();", "  function spawnGreen() {\n    if (relayMissionActive()) { state.greenFood = null; return; }\n    const settings = missionSettings();", 'block green apples in relay')
once("  function maybeSpawnSpecial(force = false) {\n    const now = performance.now();", "  function maybeSpawnSpecial(force = false) {\n    if (relayMissionActive()) { state.specialFood = null; return; }\n    const now = performance.now();", 'block special apples in relay')

# Mission rule uses the dynamic target.
once("    if (s.laserCount) return 'Règle · Les lasers", "    if (relayMissionActive()) return `Règle · Attrape l’écureuil avec la tête, transporte-le sur ton dos puis dépose-le dans le nid 2×2. Objectif : ${relayTarget()} relais.`;\n    if (s.laserCount) return 'Règle · Les lasers", 'relay briefing')

# Draw a true 2x2 nest and keep every delivered squirrel visible as the nest moves.
layer_old = """  function drawMissionLayer(time) {
    const settings = missionSettings();"""
layer_new = r'''  function drawMissionLayer(time) {
    const settings = missionSettings();
    if (relayMissionActive()) {
      if (state.relayNest) {
        const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2;
        ctx.save();
        ctx.shadowBlur=14; ctx.shadowColor='rgba(120,255,72,.55)';
        if (assets.relayNest) drawImageContain(assets.relayNest,x,y,size,size);
        else { ctx.strokeStyle='#83ff55'; ctx.lineWidth=2; ctx.strokeRect(x,y,size,size); }
        drawRelayNestSquirrels(x,y,state.relayCompleted,Boolean(state.relayPendingCompleteAt));
        ctx.restore();
      }
      if (state.relaySquirrel && !state.relayCarrying) {
        const x=state.relaySquirrel.x*cell, y=state.relaySquirrel.y*cell;
        ctx.save(); ctx.shadowBlur=12; ctx.shadowColor='rgba(255,196,67,.68)';
        if (assets.relaySquirrel) drawImageContain(assets.relaySquirrel,x-cell*.12,y-cell*.12,cell*1.24,cell*1.24);
        ctx.restore();
      }
    }'''
once(layer_old, layer_new, 'relay layer')

# Rider remains on the snake until delivery.
rider_old = """    // 4. Tête clairement reconnaissable, légèrement plus large que le cou.
    const head = points[0];"""
rider_new = r'''    // Écureuil transporté : posé visuellement sur le dos, derrière la tête.
    if (relayMissionActive() && state.relayCarrying && assets.relaySquirrel && points.length > 1) {
      const rider=points[Math.min(2,points.length-1)], riderSize=cell*1.22*scale;
      ctx.save(); ctx.shadowBlur=8; ctx.shadowColor='rgba(0,0,0,.42)';
      drawImageContain(assets.relaySquirrel,rider.x-riderSize/2,rider.y-riderSize*.78,riderSize,riderSize);
      ctx.restore();
    }

    // 4. Tête clairement reconnaissable, légèrement plus large que le cou.
    const head = points[0];'''
once(rider_old, rider_new, 'relay rider')

GAME.write_text(js, encoding='utf-8')

# Rewrite the five relay missions as a clear 1→5 progression. No apple/timer semantics remain.
txt = LEVELS.read_text(encoding='utf-8')
m = re.search(r'const MISSIONS = (\[.*?\]);\n', txt, re.S)
if not m:
    raise SystemExit('MISSIONS table missing')
missions = json.loads(m.group(1))
relay_missions = [mission for mission in missions if mission.get('missionType') == 'intervals']
if len(relay_missions) != 5:
    raise SystemExit(f'expected 5 relay missions, found {len(relay_missions)}')

for index, mission in enumerate(relay_missions, start=1):
    target = index
    mission['description'] = f'Attrape un écureuil, transporte-le sur le dos du serpent et dépose-le dans le nid. Réussis {target} relais.'
    mission['primaryObjective'] = f'Déposer {target} écureuil' + (' dans le nid' if target == 1 else 's dans le nid')
    for objective in mission.get('objectives', []):
        if objective.get('metric') == 'intervals.completed':
            objective['value'] = target
            objective['label'] = f'Réussir {target} relais'
    settings = mission.setdefault('settings', {})
    settings['intervalCount'] = target
    settings.pop('intervalTarget', None)
    settings.pop('intervalTimeSec', None)
    settings['obstacles'] = [0, 2, 4, 6, 8][index-1]

replacement = 'const MISSIONS = ' + json.dumps(missions, ensure_ascii=False, separators=(',',':')) + ';\n'
LEVELS.write_text(txt[:m.start()] + replacement + txt[m.end():], encoding='utf-8')

# Build guards.
final_js = GAME.read_text(encoding='utf-8')
for needle in [
    'function relayTarget()', 'const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2',
    'drawRelayNestSquirrels(x,y,state.relayCompleted,Boolean(state.relayPendingCompleteAt))',
    'if (relayMissionActive()) { state.greenFood = null; return; }',
    'if (relayMissionActive()) { state.specialFood = null; return; }',
    'buildMissionObstacles();', 'spawnRelayRound();', "levelEngine?.record('intervalComplete')"
]:
    if needle not in final_js:
        raise SystemExit(f'relay build guard missing: {needle}')

print('Relay gameplay updated: nest=2x2, persistent squirrels, no apples, targets=1..5, obstacles progressive')

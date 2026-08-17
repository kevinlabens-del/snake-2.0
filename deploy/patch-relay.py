from pathlib import Path
import re, json

game = Path('dist/game.js')
js = game.read_text(encoding='utf-8')

def once(old, new, label):
    global js
    if new in js: return
    if old not in js: raise SystemExit(f'{label} marker missing')
    js = js.replace(old, new, 1)

once("    specialFood: null,\n    score: 0,", "    specialFood: null,\n    relaySquirrel: null,\n    relayNest: null,\n    relayCarrying: false,\n    relayDeliveredUntil: 0,\n    relayPendingCompleteAt: 0,\n    relayCompleted: 0,\n    score: 0,", 'relay state')
once("    malusScorpion: ASSET_BASE + 'malus-scorpion.png',", "    malusScorpion: ASSET_BASE + 'malus-scorpion.png',\n    relaySquirrel: './assets/relay/squirrel.png',\n    relayNest: './assets/relay/nest.png',", 'relay assets')

once("    buildMissionObstacles();\n    if (settings.portalOnComplete", """    buildMissionObstacles();
    state.relaySquirrel = null;
    state.relayNest = null;
    state.relayCarrying = false;
    state.relayDeliveredUntil = 0;
    state.relayPendingCompleteAt = 0;
    state.relayCompleted = 0;
    if (mission?.missionType === 'intervals') spawnRelayRound();
    if (settings.portalOnComplete""", 'relay init')

helpers = r'''  function relayNestCells(nest = state.relayNest) {
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
    for (let tries=0; tries<1200; tries++) {
      const x=min+((Math.random()*Math.max(1,max-min+1))|0), y=min+((Math.random()*Math.max(1,max-min+1))|0);
      const area=[{x,y},{x:x+1,y},{x,y:y+1},{x:x+1,y:y+1}];
      if (area.every(p => !relayCellOccupied(p,true))) return {x,y};
    }
    return {x:min,y:min};
  }

  function freeRelaySquirrel() {
    for (let tries=0; tries<1200; tries++) {
      const p={x:(Math.random()*cells)|0,y:(Math.random()*cells)|0};
      if (!relayCellOccupied(p)) return p;
    }
    return freeCell();
  }

  function spawnRelayRound() {
    if (state.mission?.missionType !== 'intervals' || !state.running) return;
    state.relayNest=freeRelayNest();
    state.relaySquirrel=freeRelaySquirrel();
    state.relayCarrying=false;
    state.relayDeliveredUntil=0;
    state.relayPendingCompleteAt=0;
  }

  function updateRelay(head) {
    if (state.mission?.missionType !== 'intervals') return;
    const now=performance.now();
    if (state.relayPendingCompleteAt && now >= state.relayPendingCompleteAt) {
      state.relayPendingCompleteAt=0;
      state.relayCompleted+=1;
      levelEngine?.record('intervalComplete');
      if (!state.running) return;
      spawnRelayRound();
      toast(`Relais ${state.relayCompleted}/3`);
      return;
    }
    if (!head || state.relayPendingCompleteAt) return;
    if (!state.relayCarrying && state.relaySquirrel && same(head,state.relaySquirrel)) {
      state.relayCarrying=true; state.relaySquirrel=null; state.headOpenUntil=now+220;
      beep('eat'); vibrate(35); toast('Écureuil récupéré · ramène-le au nid'); return;
    }
    if (state.relayCarrying && relayNestCells().some(c => same(c,head))) {
      state.relayCarrying=false; state.relayDeliveredUntil=now+700; state.relayPendingCompleteAt=now+700;
      beep('eat'); vibrate([45,30,70]); toast('Écureuil déposé dans le nid ✓');
    }
  }

'''
if 'function relayNestCells(' not in js:
    if '  function freeCell() {' not in js: raise SystemExit('freeCell marker missing')
    js = js.replace('  function freeCell() {', helpers + '  function freeCell() {', 1)

once("        || state.decoyPortals.some(portal => same(portal, p))\n        || isObstacleCell(p);", "        || state.decoyPortals.some(portal => same(portal, p))\n        || (state.relaySquirrel && same(state.relaySquirrel, p))\n        || relayNestCells().some(c => same(c, p))\n        || isObstacleCell(p);", 'free cell relay exclusion')
once("    state.snake.unshift(head);\n    if (state.respawnGraceMoves > 0) state.respawnGraceMoves--;\n    updateZoneProgress(head);", "    state.snake.unshift(head);\n    if (state.respawnGraceMoves > 0) state.respawnGraceMoves--;\n    updateRelay(head);\n    if (!state.running) return;\n    updateZoneProgress(head);", 'relay collision')
once("    if (settings.intervalCount && settings.intervalTimeSec && levelEngine.status === 'running') {", "    if (state.mission?.missionType !== 'intervals' && settings.intervalCount && settings.intervalTimeSec && levelEngine.status === 'running') {", 'old interval runtime')
once("    if (s.laserCount) return 'Règle · Les lasers", "    if (state.mission?.missionType === 'intervals') return 'Règle · Attrape l’écureuil avec la tête, transporte-le sur ton dos puis dépose-le dans le nid de 4 cases. Réussis 3 relais.';\n    if (s.laserCount) return 'Règle · Les lasers", 'relay briefing')

layer = r'''  function drawMissionLayer(time) {
    const settings = missionSettings();
    if (state.mission?.missionType === 'intervals') {
      if (state.relayNest) {
        const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2;
        ctx.save(); ctx.shadowBlur=14; ctx.shadowColor='rgba(120,255,72,.55)';
        if (assets.relayNest) drawImageContain(assets.relayNest,x,y,size,size);
        else { ctx.strokeStyle='#83ff55'; ctx.lineWidth=2; ctx.strokeRect(x,y,size,size); }
        if (state.relayDeliveredUntil > performance.now() && assets.relaySquirrel)
          drawImageContain(assets.relaySquirrel,x+cell*.48,y+cell*.42,cell*1.05,cell*1.05);
        ctx.restore();
      }
      if (state.relaySquirrel && !state.relayCarrying) {
        const x=state.relaySquirrel.x*cell, y=state.relaySquirrel.y*cell;
        ctx.save(); ctx.shadowBlur=12; ctx.shadowColor='rgba(255,196,67,.68)';
        if (assets.relaySquirrel) drawImageContain(assets.relaySquirrel,x-cell*.12,y-cell*.12,cell*1.24,cell*1.24);
        ctx.restore();
      }
    }'''
once("  function drawMissionLayer(time) {\n    const settings = missionSettings();", layer, 'relay layer')

rider = r'''    // Écureuil transporté : posé visuellement sur le dos, derrière la tête.
    if (state.mission?.missionType === 'intervals' && state.relayCarrying && assets.relaySquirrel && points.length > 1) {
      const rider=points[Math.min(2,points.length-1)], riderSize=cell*1.22*scale;
      ctx.save(); ctx.shadowBlur=8; ctx.shadowColor='rgba(0,0,0,.42)';
      drawImageContain(assets.relaySquirrel,rider.x-riderSize/2,rider.y-riderSize*.78,riderSize,riderSize);
      ctx.restore();
    }

    // 4. Tête clairement reconnaissable, légèrement plus large que le cou.
    const head = points[0];'''
once("    // 4. Tête clairement reconnaissable, légèrement plus large que le cou.\n    const head = points[0];", rider, 'relay rider')
game.write_text(js, encoding='utf-8')

levels = Path('dist/apple-snake-levels.js')
txt = levels.read_text(encoding='utf-8')
m = re.search(r'const MISSIONS = (\[.*?\]);\n', txt, re.S)
if not m: raise SystemExit('MISSIONS table missing')
missions = json.loads(m.group(1)); changed=0
for mission in missions:
    if mission.get('missionType') == 'intervals':
        changed += 1
        mission['description'] = 'Attrape un écureuil, transporte-le sur le dos du serpent et dépose-le dans le nid. Réussis 3 relais.'
        mission['primaryObjective'] = 'Déposer 3 écureuils dans le nid'
        for objective in mission.get('objectives', []):
            if objective.get('metric') == 'intervals.completed': objective['value']=3; objective['label']='Réussir 3 relais'
        mission['settings']['intervalCount']=3
        mission['settings'].pop('intervalTarget',None); mission['settings'].pop('intervalTimeSec',None)
if changed != 5: raise SystemExit(f'expected 5 relay missions, found {changed}')
replacement = 'const MISSIONS = ' + json.dumps(missions, ensure_ascii=False, separators=(',',':')) + ';\n'
levels.write_text(txt[:m.start()] + replacement + txt[m.end():], encoding='utf-8')
print(f'Relay gameplay applied to {changed} missions')

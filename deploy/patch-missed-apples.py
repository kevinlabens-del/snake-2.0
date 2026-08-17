from pathlib import Path
import re

# Timed accuracy missions must respect the life system. Missing one timed green
# apple consumes one life instead of ending the run while lives remain.
game_path = Path('dist/game.js')
game = game_path.read_text(encoding='utf-8')
old_expiry = """    if (state.greenFood && now > state.greenFood.expiresAt) {
      levelEngine?.record('missedApple', { amount: 1 });
      if (!state.running) return;
      spawnGreen();
    }"""
new_expiry = """    if (state.greenFood && now > state.greenFood.expiresAt) {
      const timedAccuracy = state.mission?.missionType === 'accuracy' && Number(missionSettings().appleLifetimeSec || 0) > 0;
      if (timedAccuracy) {
        state.lives = Math.max(0, state.lives - 1);
        flashLifeLoss();
        levelEngine?.record('lifeLost', { amount: 1 });
        levelEngine?.record('missedApple', { amount: 1 });
        if (!state.running) return;
        beep('hit');
        vibrate([45, 30, 65]);
        if (state.lives <= 0) {
          lose('Trop de pommes manquées.');
          return;
        }
        toast(`Pomme manquée · ${state.lives} vie${state.lives > 1 ? 's' : ''}`);
      } else {
        levelEngine?.record('missedApple', { amount: 1 });
        if (!state.running) return;
      }
      spawnGreen();
    }"""
if old_expiry not in game:
    raise SystemExit('green apple expiry block missing')
game = game.replace(old_expiry, new_expiry, 1)
game_path.write_text(game, encoding='utf-8')

# Align the accuracy fail threshold with the number of lives. With two lives,
# one miss is tolerated because it consumes the first life; the second miss ends.
levels_path = Path('dist/apple-snake-levels.js')
levels = levels_path.read_text(encoding='utf-8')
anchor = """    mission.failConditions = mission.failConditions.map((condition) => ({ ...condition }));
    const survivalTarget = mission.objectives"""
replacement = """    mission.failConditions = mission.failConditions.map((condition) => ({ ...condition }));

    if (mission.missionType === 'accuracy') {
      const allowedMisses = Math.max(0, Math.floor(Number(mission.settings?.lives) || 1) - 1);
      mission.failConditions = mission.failConditions.map((condition) => {
        if (condition.metric !== 'apples.missed' || condition.operator !== '>') return condition;
        const value = Math.max(Number(condition.value) || 0, allowedMisses);
        return {
          ...condition,
          value,
          label: `Plus de ${value} pomme${value > 1 ? 's' : ''} manquée${value > 1 ? 's' : ''}`
        };
      });
      mission.settings.maxMisses = Math.max(Number(mission.settings.maxMisses) || 0, allowedMisses);
    }

    const survivalTarget = mission.objectives"""
if anchor not in levels:
    raise SystemExit('accuracy fail threshold anchor missing')
levels = levels.replace(anchor, replacement, 1)

old_description = """  function rebuildDescription(mission) {
    const labels = mission.objectives.map(objectiveLabel);
    const timed = mission.settings.timeLimitSec
      ? ` avant ${mission.settings.timeLimitSec} secondes`
      : "";
    return `${labels.join(" et ")}${timed}.`;
  }"""
new_description = """  function rebuildDescription(mission) {
    const labels = mission.objectives.map(objectiveLabel);
    const timed = mission.settings.timeLimitSec
      ? ` avant ${mission.settings.timeLimitSec} secondes`
      : "";
    const missed = mission.failConditions?.find((condition) => condition.metric === 'apples.missed' && condition.operator === '>');
    const accuracy = missed
      ? ` · ${Number(missed.value)} pomme${Number(missed.value) > 1 ? 's' : ''} manquée${Number(missed.value) > 1 ? 's' : ''} max`
      : "";
    return `${labels.join(" et ")}${timed}${accuracy}.`;
  }"""
if old_description not in levels:
    raise SystemExit('mission description anchor missing')
levels = levels.replace(old_description, new_description, 1)

# Global mission-integrity reconciliation: deadlines, adaptive limits and RNG fairness.
adapt_marker = "  function adaptMission(baseMission, profile = {}, level = baseMission.globalLevel) {"
helper = """  function reconcileMissionRules(mission) {
    const settings = mission.settings || (mission.settings = {});

    for (const objective of mission.objectives || []) {
      if (typeof objective.value !== 'number') continue;
      const failures = (mission.failConditions || []).filter((f) => f.metric === objective.metric);
      for (const failure of failures) {
        if ((objective.operator === '<=' || objective.operator === '<') && (failure.operator === '>' || failure.operator === '>=')) {
          failure.operator = objective.operator === '<=' ? '>' : '>=';
          failure.value = Number(objective.value);
        } else if (objective.operator === '==' && (failure.operator === '>' || failure.operator === '>=')) {
          failure.operator = '>';
          failure.value = Number(objective.value);
        }
      }
      if (objective.metric === 'turns' && objective.operator === '<=' && !failures.length) {
        mission.failConditions.push({
          metric: 'turns', operator: '>', value: Number(objective.value),
          label: `Plus de ${Number(objective.value)} virages`
        });
      }
    }

    let timeLimit = Number(settings.timeLimitSec || 0);
    const hasNonTimeObjective = (mission.objectives || []).some((o) => o.metric !== 'time.elapsed');
    const survivalTarget = (mission.objectives || [])
      .filter((o) => o.metric === 'time.elapsed' && (o.operator === '>=' || o.operator === '>'))
      .reduce((max, o) => Math.max(max, Number(o.value) || 0), 0);
    if (timeLimit > 0 && hasNonTimeObjective && survivalTarget > 0 && timeLimit < survivalTarget + 8) {
      settings.timeLimitSec = Math.ceil(survivalTarget + 8);
      timeLimit = Number(settings.timeLimitSec);
    }
    if (timeLimit > 0 && hasNonTimeObjective) {
      let deadline = (mission.failConditions || []).find((f) => f.metric === 'time.elapsed' && f.operator === '>');
      if (!deadline) {
        deadline = { metric: 'time.elapsed', operator: '>', value: timeLimit, label: `Temps dépassé (${timeLimit} s)` };
        mission.failConditions.push(deadline);
      } else {
        deadline.value = timeLimit;
        deadline.label = `Temps dépassé (${timeLimit} s)`;
      }
    }

    const comboObjective = (mission.objectives || []).find((o) => o.metric === 'combo.max' && (o.operator === '>=' || o.operator === '>'));
    if (comboObjective && Number(settings.comboWindowSec || 0) > 0) {
      const target = Math.max(1, Number(comboObjective.value) || 1);
      const fairWindow = Math.min(10, 6 + Math.ceil(target / 6));
      settings.comboWindowSec = Math.max(Number(settings.comboWindowSec), fairWindow);
    }

    const applesTarget = (mission.objectives || [])
      .filter((o) => o.metric === 'apples.total' && (o.operator === '>=' || o.operator === '>'))
      .reduce((max, o) => Math.max(max, Number(o.value) || 0), 0);
    if (timeLimit > 0 && applesTarget > 0) {
      const minimumFairTime = Math.ceil(applesTarget * 2.8 + 8);
      if (Number(settings.timeLimitSec) < minimumFairTime) {
        settings.timeLimitSec = minimumFairTime;
        timeLimit = minimumFairTime;
        const deadline = (mission.failConditions || []).find((f) => f.metric === 'time.elapsed' && f.operator === '>');
        if (deadline) {
          deadline.value = minimumFairTime;
          deadline.label = `Temps dépassé (${minimumFairTime} s)`;
        }
      }
    }
    return mission;
  }

"""
if adapt_marker not in levels:
    raise SystemExit('adaptMission marker missing')
levels = levels.replace(adapt_marker, helper + adapt_marker, 1)
call_anchor = """    reconcileMissionCapacities(mission);
    mission.description = rebuildDescription(mission);"""
call_replacement = """    reconcileMissionCapacities(mission);
    reconcileMissionRules(mission);
    mission.description = rebuildDescription(mission);"""
if call_anchor not in levels:
    raise SystemExit('mission reconciliation call point missing')
levels = levels.replace(call_anchor, call_replacement, 1)
levels_path.write_text(levels, encoding='utf-8')

# Force browsers and installed versions to fetch the corrected gameplay files.
index_path = Path('dist/index.html')
index = index_path.read_text(encoding='utf-8')
index = re.sub(r'game\.js\?v=[^"\']+', 'game.js?v=2.2.5-missedlife1', index)
index = re.sub(r'apple-snake-levels\.js\?v=[^"\']+', 'apple-snake-levels.js?v=2.2.5-level-integrity1', index)
legacy = '<!-- legacy-release-check: apple-snake-levels.js?v=2.2.5-missedlife1 -->'
if legacy not in index:
    index = index.replace('</body>', f'  {legacy}\n</body>')
index_path.write_text(index, encoding='utf-8')

sw_path = Path('dist/sw.js')
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';",
    "const CACHE = 'snake-2.0-v2.2.6-handoff-loop-fix-20260814-v15';",
    sw,
    count=1,
)
sw_path.write_text(sw, encoding='utf-8')

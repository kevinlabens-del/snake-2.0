from pathlib import Path
import json
import re

GAME = Path('dist/game.js')
LEVELS = Path('dist/apple-snake-levels.js')

if not GAME.exists() or not LEVELS.exists():
    raise SystemExit('relay playability patch requires rebuilt dist/game.js and dist/apple-snake-levels.js')

# Relay missions already receive the standard mission obstacle build during level setup.
# The relay patch was calling buildMissionObstacles() a second time, which could visually
# double the amount of scenery/obstacles and make the arena unnecessarily cramped.
game = GAME.read_text(encoding='utf-8')
duplicate = """    if (relayMissionActive()) {
      state.greenFood = null;
      state.specialFood = null;
      buildMissionObstacles();
      spawnRelayRound();
    } else {"""
fixed = """    if (relayMissionActive()) {
      state.greenFood = null;
      state.specialFood = null;
      spawnRelayRound();
    } else {"""

if duplicate in game:
    game = game.replace(duplicate, fixed, 1)
elif fixed not in game:
    raise SystemExit('relay start block not found; refusing unsafe playability patch')

GAME.write_text(game, encoding='utf-8')

# Keep obstacles as an accompaniment to relay gameplay, never the main challenge.
# The five current relay missions progress from 0 to 4 obstacle cells only.
levels_text = LEVELS.read_text(encoding='utf-8')
match = re.search(r'const MISSIONS = (\[.*?\]);\n', levels_text, re.S)
if not match:
    raise SystemExit('MISSIONS table missing')

missions = json.loads(match.group(1))
relay_missions = [mission for mission in missions if mission.get('missionType') == 'intervals']
if len(relay_missions) != 5:
    raise SystemExit(f'expected 5 relay missions, found {len(relay_missions)}')

obstacle_progression = [0, 1, 2, 3, 4]
for index, mission in enumerate(relay_missions):
    settings = mission.setdefault('settings', {})
    settings['obstacles'] = obstacle_progression[index]

replacement = 'const MISSIONS = ' + json.dumps(missions, ensure_ascii=False, separators=(',', ':')) + ';\n'
LEVELS.write_text(levels_text[:match.start()] + replacement + levels_text[match.end():], encoding='utf-8')

# Static guards: no relay-specific duplicate obstacle build and no relay level above 4 obstacles.
final_game = GAME.read_text(encoding='utf-8')
if duplicate in final_game:
    raise SystemExit('duplicate relay obstacle build is still present')
if fixed not in final_game:
    raise SystemExit('corrected relay start block missing')

print('Relay playability patch applied: single obstacle build, progression 0/1/2/3/4')

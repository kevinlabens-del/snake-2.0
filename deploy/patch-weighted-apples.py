from pathlib import Path

GAME = Path('dist/game.js')
LEVELS = Path('dist/apple-snake-levels.js')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor missing')
    return text.replace(old, new, 1)


# Red and gold apples count as 2 and 3 apples for mission progression,
# while keeping their existing score values and all other effects unchanged.
game = GAME.read_text(encoding='utf-8')

record_anchor = """  function recordAppleToMission(kind, points, meta = {}) {
    if (!levelEngine || levelEngine.status !== 'running') return;
"""
record_replacement = """  function missionAppleWeight(kind) {
    if (kind === 'red') return 2;
    if (kind === 'gold') return 3;
    return 1;
  }

  function recordAppleToMission(kind, points, meta = {}) {
    if (!levelEngine || levelEngine.status !== 'running') return;
"""
game = replace_once(game, record_anchor, record_replacement, 'mission apple weight helper')

game = replace_once(
    game,
    "    state.aux.applesSincePortal = Number(state.aux.applesSincePortal || 0) + 1;",
    "    state.aux.applesSincePortal = Number(state.aux.applesSincePortal || 0) + missionAppleWeight(kind);",
    'portal apple progression weight',
)
GAME.write_text(game, encoding='utf-8')

levels = LEVELS.read_text(encoding='utf-8')
old_apple_case = """        case \"apple\": {
          const kind = String(payload.kind || \"classic\");
          incrementPath(this.metrics, \"apples.total\", 1);
          incrementPath(this.metrics, `apples.${kind}`, 1);
          if (kind !== \"classic\" && kind !== \"poison\") incrementPath(this.metrics, \"apples.specialTotal\", 1);
          if (payload.corner) incrementPath(this.metrics, \"apples.corner\", 1);
          if (payload.inActiveZone) incrementPath(this.metrics, \"apples.inActiveZone\", 1);
"""
new_apple_case = """        case \"apple\": {
          const kind = String(payload.kind || \"classic\");
          const appleWeight = kind === \"red\" ? 2 : kind === \"gold\" ? 3 : 1;
          incrementPath(this.metrics, \"apples.total\", appleWeight);
          incrementPath(this.metrics, `apples.${kind}`, 1);
          if (kind !== \"classic\" && kind !== \"poison\") incrementPath(this.metrics, \"apples.specialTotal\", 1);
          if (payload.corner) incrementPath(this.metrics, \"apples.corner\", appleWeight);
          if (payload.inActiveZone) incrementPath(this.metrics, \"apples.inActiveZone\", appleWeight);
"""
levels = replace_once(levels, old_apple_case, new_apple_case, 'level engine apple weighting')
LEVELS.write_text(levels, encoding='utf-8')

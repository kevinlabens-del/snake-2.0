from pathlib import Path
import re


GAME_PATH = Path('dist/game.js')
INDEX_PATH = Path('dist/index.html')
INSTALL_GATE_PATH = Path('dist/install-gate-v225.js')
SW_PATH = Path('dist/sw.js')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor missing')
    return text.replace(old, new, 1)


game = GAME_PATH.read_text(encoding='utf-8')

# Keep every runtime request on the same release identifier. Background URLs
# use this value too, so a corrected deployment cannot reuse a failed browser
# response from an older build.
game = re.sub(
    r"const VERSION = '[^']+';",
    "const VERSION = '2.2.9';",
    game,
    count=1,
)

game = replace_once(
    game,
    "    nextDir: { x: 1, y: 0 },\n",
    "    nextDir: { x: 1, y: 0 },\n    inputQueue: [],\n",
    'input queue state',
)

game = replace_once(
    game,
    "  let gameplayBackgroundBag = [];\n",
    """  let gameplayBackgroundBag = [];
  const gameplayBackgroundLoads = new Map();
  let gameplayBackgroundRetryTimer = 0;
""",
    'background loader state',
)

game = replace_once(
    game,
    "  function loadImageAsset(key, src) {",
    "  function loadImageAsset(key, src, timeoutOverride = 0) {",
    'image loader signature',
)
game = replace_once(
    game,
    "          assets[key] = img;\n        } else {",
    "          assets[key] = img;\n          assetErrors.delete(key);\n        } else {",
    'image success handling',
)
game = replace_once(
    game,
    "      const timeoutMs = key.startsWith('background') ? 12000 : 5500;",
    "      const timeoutMs = Number(timeoutOverride) > 0 ? Number(timeoutOverride) : (key.startsWith('background') ? 12000 : 5500);",
    'image timeout handling',
)

old_load_assets = """  async function loadAssets() {
    const results = await Promise.all(Object.entries(assetManifest).map(([key, src]) => loadImageAsset(key, src)));
    if (assets.body) buildBodyWarpFrames(assets.body);
    return results.every(Boolean);
  }
"""
new_load_assets = """  async function loadAssets() {
    // Gameplay must not wait for all nine large terrain photographs. Only the
    // sprites and obstacles are critical; the selected terrain is loaded below.
    const criticalAssets = Object.entries(assetManifest).filter(([key]) => !key.startsWith('background'));
    const results = await Promise.all(criticalAssets.map(([key, src]) => loadImageAsset(key, src)));
    if (assets.body) buildBodyWarpFrames(assets.body);
    return results.every(Boolean);
  }
"""
game = replace_once(game, old_load_assets, new_load_assets, 'critical asset loading')

background_start = game.find('  function selectRandomGameplayBackground() {')
background_end = game.find('\n\n\n  function pickFromPool', background_start)
if background_start < 0 or background_end < 0:
    raise SystemExit('background selection block missing')

background_loader = """  function gameplayBackgroundIsReady(background) {
    const image = background ? assets[background.key] : null;
    return Boolean(image?.complete && image.naturalWidth > 0 && image.naturalHeight > 0);
  }

  function takeGameplayBackgroundCandidate() {
    if (!gameplayBackgroundBag.length) refillGameplayBackgroundBag(gameplayBackgroundCatalog);
    return gameplayBackgroundBag.shift() || gameplayBackgroundCatalog[0];
  }

  async function ensureGameplayBackgroundLoaded(background, { attempts = 2, timeoutMs = 7000 } = {}) {
    if (!background) return false;
    if (gameplayBackgroundIsReady(background)) return true;
    if (gameplayBackgroundLoads.has(background.key)) return gameplayBackgroundLoads.get(background.key);

    const job = (async () => {
      for (let attempt = 0; attempt < Math.max(1, attempts); attempt++) {
        assetErrors.delete(background.key);
        const loaded = await loadImageAsset(background.key, assetManifest[background.key], timeoutMs);
        if (loaded && gameplayBackgroundIsReady(background)) return true;
      }
      return false;
    })();

    gameplayBackgroundLoads.set(background.key, job);
    try {
      return await job;
    } finally {
      if (gameplayBackgroundLoads.get(background.key) === job) gameplayBackgroundLoads.delete(background.key);
    }
  }

  function scheduleGameplayBackgroundRetry(background) {
    clearTimeout(gameplayBackgroundRetryTimer);
    gameplayBackgroundRetryTimer = window.setTimeout(async () => {
      const loaded = await ensureGameplayBackgroundLoaded(background, { attempts: 2, timeoutMs: 9000 });
      if (!loaded || state.gameplayBackgroundId !== background.id) return;
      renderGameplayBackgroundFrame(background);
      if (state.running) draw();
    }, 1200);
  }

  async function selectRandomGameplayBackground() {
    const selected = takeGameplayBackgroundCandidate();
    const selectedLoaded = await ensureGameplayBackgroundLoaded(selected);
    const alreadyLoaded = gameplayBackgroundCatalog.find(gameplayBackgroundIsReady);
    const displayed = selectedLoaded ? selected : (alreadyLoaded || selected);

    state.gameplayBackgroundId = displayed.id;
    canvas.dataset.background = displayed.id;
    renderGameplayBackgroundFrame(displayed);

    // A temporary network failure is never permanent. Keep the playable
    // fallback, then replace it in place as soon as the same terrain succeeds.
    if (!selectedLoaded && displayed === selected) scheduleGameplayBackgroundRetry(selected);

    // Warm only one upcoming terrain. This avoids the previous nine-file burst
    // while making the next level instantaneous in normal conditions.
    const upcoming = gameplayBackgroundBag[0];
    if (upcoming) window.setTimeout(() => {
      void ensureGameplayBackgroundLoaded(upcoming, { attempts: 1, timeoutMs: 7000 });
    }, 1000);
    return displayed;
  }"""
game = game[:background_start] + background_loader + game[background_end:]

game = replace_once(
    game,
    "    resetRunState();\n    selectRandomGameplayBackground();\n    state.running = true;",
    "    resetRunState();\n    state.running = true;",
    'stage background selection',
)
game = replace_once(
    game,
    "    if (assetsReady) await assetsReady.catch(() => false);\n    startStage(stage, daily);",
    "    if (assetsReady) await assetsReady.catch(() => false);\n    await selectRandomGameplayBackground();\n    startStage(stage, daily);",
    'await selected background',
)

game = replace_once(
    game,
    "    state.nextDir = { x: 1, y: 0 };\n    state.score = 0;",
    "    state.nextDir = { x: 1, y: 0 };\n    state.inputQueue.length = 0;\n    state.score = 0;",
    'reset input queue',
)
game = replace_once(
    game,
    "    state.dir = { ...respawn.direction };\n    state.nextDir = { ...respawn.direction };",
    "    state.dir = { ...respawn.direction };\n    state.nextDir = { ...respawn.direction };\n    state.inputQueue.length = 0;",
    'respawn input queue',
)

set_dir_start = game.find('  function setDir(x, y) {')
set_dir_end = game.find('\n\n  function eatGreen()', set_dir_start)
if set_dir_start < 0 or set_dir_end < 0:
    raise SystemExit('direction input block missing')

direction_queue = """  const MAX_DIRECTION_QUEUE = 2;

  function setDir(x, y, source = 'unknown') {
    if (!state.running || state.paused) return false;
    const settings = missionSettings();
    const pulse = Number(settings.reverseControlsPulseSec || 0);
    const duration = Number(settings.reverseControlsDurationSec || 0);
    const elapsed = missionElapsed();
    const phaseTime = pulse ? elapsed % pulse : elapsed;
    const reverse = duration > 0 && phaseTime < duration;
    if (reverse) { x *= -1; y *= -1; }

    const previous = state.inputQueue.length
      ? state.inputQueue[state.inputQueue.length - 1]
      : state.dir;
    if (x === -previous.x && y === -previous.y) return false;
    if (x === previous.x && y === previous.y) return false;
    if (state.inputQueue.length >= MAX_DIRECTION_QUEUE) return false;

    state.inputQueue.push({ x, y, source, queuedAt: performance.now() });
    const next = state.inputQueue[0];
    state.nextDir = { x: next.x, y: next.y };
    levelEngine?.record('turn');
    beep('click');
    return true;
  }"""
game = game[:set_dir_start] + direction_queue + game[set_dir_end:]

game = replace_once(
    game,
    "    snapshotSnake();\n    state.dir = state.nextDir;\n    let head = { x: state.snake[0].x + state.dir.x, y: state.snake[0].y + state.dir.y };",
    """    snapshotSnake();
    const queuedDirection = state.inputQueue.shift();
    if (queuedDirection) state.dir = { x: queuedDirection.x, y: queuedDirection.y };
    const followingDirection = state.inputQueue[0] || state.dir;
    state.nextDir = { x: followingDirection.x, y: followingDirection.y };
    let head = { x: state.snake[0].x + state.dir.x, y: state.snake[0].y + state.dir.y };""",
    'consume queued direction',
)

game = replace_once(
    game,
    "    const progress = state.paused ? 1 : smoothStep01(state.acc / Math.max(1, state.visualStepMs));",
    "    const progress = state.paused ? 1 : clamp(state.acc / Math.max(1, state.visualStepMs), 0, 1);",
    'linear movement interpolation',
)

game = replace_once(
    game,
    """  function smoothStep01(value) {
    const t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }
""",
    """  function smoothStep01(value) {
    const t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }

  function lerpAngle(from, to, amount) {
    const delta = Math.atan2(Math.sin(to - from), Math.cos(to - from));
    return from + delta * clamp(amount, 0, 1);
  }
""",
    'head angle interpolation helper',
)

game = replace_once(
    game,
    "    const baseHeadAngle = visualBodyAngle(0, points);",
    """    const geometricHeadAngle = visualBodyAngle(0, points);
    const logicalHeadAngle = Math.atan2(state.dir.y, state.dir.x);
    const visualTurnProgress = state.paused ? 1 : clamp(state.acc / Math.min(45, Math.max(1, state.visualStepMs)), 0, 1);
    const baseHeadAngle = lerpAngle(geometricHeadAngle, logicalHeadAngle, visualTurnProgress);""",
    'responsive head direction',
)

keyboard_start = game.find("  addEventListener('keydown', e => {")
keyboard_end = game.find("\n\n  function bindToggle", keyboard_start)
if keyboard_start < 0 or keyboard_end < 0:
    raise SystemExit('keyboard and pointer controls block missing')

input_handlers = """  addEventListener('keydown', e => {
    const controls = {
      ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
      KeyW: [0, -1], KeyZ: [0, -1], KeyS: [0, 1], KeyA: [-1, 0], KeyQ: [-1, 0], KeyD: [1, 0]
    };
    const direction = controls[e.code];
    if (direction) {
      e.preventDefault();
      if (!e.repeat) setDir(...direction, 'keyboard');
    }
    if (e.code === 'Space' && state.currentScreen === 'game' && !e.repeat) {
      e.preventDefault();
      $('#pauseBtn').click();
    }
  }, { capture: true });

  const gameShell = $('#gameShell');
  function swipeThreshold() {
    return clamp(gameShell.getBoundingClientRect().width / (cells * 2), 12, 18);
  }
  function consumeSwipeDirection(e) {
    if (!state.swipe || state.swipe.pointerId !== e.pointerId || state.swipe.consumed) return false;
    const dx = e.clientX - state.swipe.x;
    const dy = e.clientY - state.swipe.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < swipeThreshold()) return false;
    state.swipe.consumed = true;
    return Math.abs(dx) > Math.abs(dy)
      ? setDir(Math.sign(dx), 0, 'pointer')
      : setDir(0, Math.sign(dy), 'pointer');
  }
  function clearSwipe(e, consume = false) {
    if (!state.swipe || state.swipe.pointerId !== e.pointerId) return;
    if (consume) consumeSwipeDirection(e);
    try {
      if (gameShell.hasPointerCapture(e.pointerId)) gameShell.releasePointerCapture(e.pointerId);
    } catch {}
    state.swipe = null;
  }
  gameShell.addEventListener('pointerdown', e => {
    if (!e.isPrimary || (e.pointerType === 'mouse' && e.button !== 0)) return;
    state.swipe = { pointerId: e.pointerId, x: e.clientX, y: e.clientY, consumed: false };
    try { gameShell.setPointerCapture(e.pointerId); } catch {}
  });
  gameShell.addEventListener('pointermove', e => {
    if (consumeSwipeDirection(e)) e.preventDefault();
  }, { passive: false });
  gameShell.addEventListener('pointerup', e => clearSwipe(e, true));
  gameShell.addEventListener('pointercancel', e => clearSwipe(e, false));"""
game = game[:keyboard_start] + input_handlers + game[keyboard_end:]

# Avoid a second registration using an obsolete URL after install-gate already
# registered the current service worker for the same scope.
game = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.9-input-background1'",
    game,
    count=1,
)

GAME_PATH.write_text(game, encoding='utf-8')


index = INDEX_PATH.read_text(encoding='utf-8')
for filename in ('manifest.webmanifest', 'styles-v225.css', 'install-gate-v225.js', 'game.js'):
    index = re.sub(
        rf'{re.escape(filename)}\?v=[^"\']+',
        f'{filename}?v=2.2.9-input-background1',
        index,
        count=1,
    )
INDEX_PATH.write_text(index, encoding='utf-8')


install_gate = INSTALL_GATE_PATH.read_text(encoding='utf-8')
install_gate = re.sub(
    r"const SW_UPDATE_RELOAD_KEY = '[^']+';",
    "const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_input_background_v1';",
    install_gate,
    count=1,
)
install_gate = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.9-input-background1'",
    install_gate,
    count=1,
)
INSTALL_GATE_PATH.write_text(install_gate, encoding='utf-8')


sw = SW_PATH.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';",
    "const CACHE = 'snake-2.0-v2.2.9-input-background-20260814-v1';",
    sw,
    count=1,
)

# Terrain photographs are optional, lazy runtime assets. Keeping them in the
# atomic installation list made one slow image abort the whole new cache and
# competed with the page's own loader on a cold desktop visit.
sw, removed_backgrounds = re.subn(
    r"\n\s*'\./assets/backgrounds/[^']+',",
    '',
    sw,
)
if removed_backgrounds < 9:
    raise SystemExit(f'expected 9 service-worker background entries, removed {removed_backgrounds}')

SW_PATH.write_text(sw, encoding='utf-8')

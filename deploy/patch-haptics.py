from pathlib import Path
import re
import runpy
import subprocess

GAME_PATH = Path('dist/game.js')
INDEX_PATH = Path('dist/index.html')
INSTALL_GATE_PATH = Path('dist/install-gate-v225.js')
SW_PATH = Path('dist/sw.js')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor missing')
    return text.replace(old, new, 1)


game = GAME_PATH.read_text(encoding='utf-8')

game = re.sub(r"const VERSION = '[^']+';", "const VERSION = '2.2.10';", game, count=1)

game = replace_once(
    game,
    "    vibration: true,\n    grid: true,",
    "    vibration: true,\n    hapticsRuntimeVersion: 0,\n    grid: true,",
    'haptics save field',
)

game = replace_once(
    game,
    "  let save = { ...defaultSave, ...safeParse(storageGet(STORAGE)) };\n",
    """  let save = { ...defaultSave, ...safeParse(storageGet(STORAGE)) };
  if (Number(save.hapticsRuntimeVersion || 0) < 1) {
    save.vibration = true;
    save.hapticsRuntimeVersion = 1;
    storageSet(STORAGE, JSON.stringify(save));
  }
""",
    'haptics migration',
)

old_vibrate = """  function vibrate(ms = 25) {
    if (save.vibration && navigator.vibrate) navigator.vibrate(ms);
  }"""
new_vibrate = """  function vibrate(pattern = 25) {
    if (!save.vibration) return false;
    if (typeof navigator.vibrate !== 'function') return false;
    if (document.visibilityState && document.visibilityState !== 'visible') return false;
    if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return false;
    try {
      return navigator.vibrate(pattern) === true;
    } catch (error) {
      console.warn('[Snake 2.0] Vibration indisponible', error);
      return false;
    }
  }"""
game = replace_once(game, old_vibrate, new_vibrate, 'vibration runtime')

game = replace_once(
    game,
    "    vibrate(18);",
    "    vibrate(35);\n    window.setTimeout(() => vibrate(45), 55);",
    'green apple haptic',
)

game = replace_once(
    game,
    "vibrate(kind === 'gold' ? [20, 20, 30] : 16);",
    "vibrate(kind === 'gold' ? [45, 30, 70] : 35);\n      if (kind !== 'gold') window.setTimeout(() => vibrate(45), 55);",
    'bonus apple haptic',
)

old_toggle = """  function bindToggle(id, key) {
    $(id).addEventListener('click', async () => {
      save[key] = !save[key];
      persist();
      syncSettings();
      if (key === 'music' && save.music) await unlockAudio();
      beep('click');
    });
  }"""
new_toggle = """  function bindToggle(id, key) {
    $(id).addEventListener('click', async () => {
      save[key] = !save[key];
      persist();
      syncSettings();
      if (key === 'music' && save.music) await unlockAudio();
      if (key === 'vibration' && save.vibration) {
        const hapticOk = vibrate([70, 35, 110]);
        toast(hapticOk ? 'Vibrations activées' : 'Vibration indisponible sur cet appareil');
      }
      beep('click');
    });
  }"""
game = replace_once(game, old_toggle, new_toggle, 'vibration settings test')

game = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.10-haptics1'",
    game,
    count=1,
)
GAME_PATH.write_text(game, encoding='utf-8')

index = INDEX_PATH.read_text(encoding='utf-8')
for filename in ('manifest.webmanifest', 'styles-v225.css', 'install-gate-v225.js', 'game.js'):
    index = re.sub(
        rf'{re.escape(filename)}\?v=[^"\']+',
        f'{filename}?v=2.2.10-haptics1',
        index,
        count=1,
    )
INDEX_PATH.write_text(index, encoding='utf-8')

install_gate = INSTALL_GATE_PATH.read_text(encoding='utf-8')
install_gate = re.sub(
    r"const SW_UPDATE_RELOAD_KEY = '[^']+';",
    "const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_haptics_v1';",
    install_gate,
    count=1,
)
install_gate = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.10-haptics1'",
    install_gate,
    count=1,
)
INSTALL_GATE_PATH.write_text(install_gate, encoding='utf-8')

sw = SW_PATH.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = '[^']+';",
    "const CACHE = 'snake-2.0-v2.2.10-haptics-20260816-v1';",
    sw,
    count=1,
)
SW_PATH.write_text(sw, encoding='utf-8')

checks = {
    "const VERSION = '2.2.10'": game,
    'hapticsRuntimeVersion: 0': game,
    'save.hapticsRuntimeVersion = 1': game,
    "typeof navigator.vibrate !== 'function'": game,
    'navigator.userActivation.hasBeenActive': game,
    'return navigator.vibrate(pattern) === true': game,
    'vibrate(35);': game,
    "window.setTimeout(() => vibrate(45), 55);": game,
    "vibrate(kind === 'gold' ? [45, 30, 70] : 35)": game,
    "vibrate([70, 35, 110])": game,
    "toast(hapticOk ? 'Vibrations activées'": game,
    'game.js?v=2.2.10-haptics1': index,
    "serviceWorker.register('./sw.js?v=2.2.10-haptics1'": install_gate,
    "const CACHE = 'snake-2.0-v2.2.10-haptics-20260816-v1'": sw,
}
for needle, haystack in checks.items():
    if needle not in haystack:
        raise SystemExit(f'haptics build guard missing: {needle}')

# Apply the independent audio calibration after haptic changes. game.js is a
# network-first critical runtime, so the corrected curve is fetched on launch.
runpy.run_path('deploy/patch-audio-volume.py', run_name='__main__')
subprocess.run(['node', 'deploy/test-audio-volume.mjs'], check=True)

# Apply the relay gameplay after the core runtime patches, then validate the
# five relay missions and their transparent PNG assets before Pages can deploy.
runpy.run_path('deploy/patch-relay.py', run_name='__main__')
runpy.run_path('deploy/patch-relay-nest-size.py', run_name='__main__')
subprocess.run(['node', 'deploy/test-relay.mjs'], check=True)

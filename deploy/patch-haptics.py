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

# Release marker used both for diagnostics and cache invalidation.
game = re.sub(r"const VERSION = '[^']+';", "const VERSION = '2.2.10';", game, count=1)

# Add a one-time migration marker without resetting any progression. Existing
# users may carry vibration:false from an older release where haptics were not
# working, so this release re-enables it once and then respects future choices.
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

# A normal apple used only 18 ms, which can be imperceptible on many phones.
# Keep the first 35 ms pulse for compatibility, then add a short second pulse so
# every ordinary food pickup is unmistakable without feeling like a collision.
game = replace_once(
    game,
    "    vibrate(18);",
    "    vibrate(35);\n    window.setTimeout(() => vibrate(45), 55);",
    'green apple haptic',
)

# Every positive special food also gets a clear two-pulse eating signature.
# Gold keeps its stronger unique pattern; poison/scorpion retain their damage
# pattern in the negative-life branch below.
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

# Force installed devices and browsers to receive the corrected runtime.
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

# Build-time guards: deployment must fail if any haptic correction disappears.
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

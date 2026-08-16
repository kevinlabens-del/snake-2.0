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

# Volume calibration release. The previous 6% user setting is deliberately
# mapped to the new 75% position: 75 * 0.0008 == 0.06 effective user volume.
game = re.sub(r"const VERSION = '[^']+';", "const VERSION = '2.2.11';", game, count=1)

# Persist a one-time migration marker. Existing low-volume users keep the same
# audible level while their slider moves to the newly useful range (6% -> 75%).
game = replace_once(
    game,
    "    musicVolume: 100,\n",
    "    musicVolume: 100,\n    audioVolumeRuntimeVersion: 0,\n",
    'audio volume save field',
)

migration_anchor = """  if (Number(save.hapticsRuntimeVersion || 0) < 1) {
    save.vibration = true;
    save.hapticsRuntimeVersion = 1;
    storageSet(STORAGE, JSON.stringify(save));
  }
"""
migration_replacement = migration_anchor + """  if (Number(save.audioVolumeRuntimeVersion || 0) < 1) {
    const legacyMusicVolume = Math.max(0, Math.min(100, Number(save.musicVolume ?? 100)));
    save.musicVolume = Math.max(0, Math.min(100, legacyMusicVolume * 12.5));
    save.audioVolumeRuntimeVersion = 1;
    storageSet(STORAGE, JSON.stringify(save));
  }
"""
game = replace_once(game, migration_anchor, migration_replacement, 'audio volume migration')

sync_old = """  function syncAudio() {
    const musicVolume = Math.max(0, Math.min(100, Number(save.musicVolume ?? 100)));
    music?.setVolume(musicVolume / 100);
"""
sync_new = """  function effectiveMusicVolume(percent) {
    const displayVolume = Math.max(0, Math.min(100, Number(percent) || 0));
    return Math.max(0, Math.min(0.08, displayVolume * 0.0008));
  }

  function syncAudio() {
    const musicVolume = Math.max(0, Math.min(100, Number(save.musicVolume ?? 100)));
    music?.setVolume(effectiveMusicVolume(musicVolume));
"""
game = replace_once(game, sync_old, sync_new, 'audio synchronization curve')

game = replace_once(
    game,
    "    music?.setVolume(save.musicVolume / 100);\n    persist();",
    "    music?.setVolume(effectiveMusicVolume(save.musicVolume));\n    persist();",
    'live volume slider curve',
)

# Force browsers and installed devices onto the recalibrated audio runtime.
game = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.11-volume1'",
    game,
    count=1,
)
GAME_PATH.write_text(game, encoding='utf-8')

index = INDEX_PATH.read_text(encoding='utf-8')
for filename in ('manifest.webmanifest', 'styles-v225.css', 'install-gate-v225.js', 'game.js'):
    index = re.sub(
        rf'{re.escape(filename)}\?v=[^"\']+',
        f'{filename}?v=2.2.11-volume1',
        index,
        count=1,
    )
INDEX_PATH.write_text(index, encoding='utf-8')

install_gate = INSTALL_GATE_PATH.read_text(encoding='utf-8')
install_gate = re.sub(
    r"const SW_UPDATE_RELOAD_KEY = '[^']+';",
    "const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_volume_v1';",
    install_gate,
    count=1,
)
install_gate = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.11-volume1'",
    install_gate,
    count=1,
)
INSTALL_GATE_PATH.write_text(install_gate, encoding='utf-8')

sw = SW_PATH.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = '[^']+';",
    "const CACHE = 'snake-2.0-v2.2.11-volume-20260817-v1';",
    sw,
    count=1,
)
SW_PATH.write_text(sw, encoding='utf-8')

checks = {
    "const VERSION = '2.2.11'": game,
    'audioVolumeRuntimeVersion: 0': game,
    'legacyMusicVolume * 12.5': game,
    'function effectiveMusicVolume(percent)': game,
    'displayVolume * 0.0008': game,
    'Math.min(0.08': game,
    'music?.setVolume(effectiveMusicVolume(musicVolume))': game,
    'music?.setVolume(effectiveMusicVolume(save.musicVolume))': game,
    'game.js?v=2.2.11-volume1': index,
    "serviceWorker.register('./sw.js?v=2.2.11-volume1'": install_gate,
    "const CACHE = 'snake-2.0-v2.2.11-volume-20260817-v1'": sw,
}
for needle, haystack in checks.items():
    if needle not in haystack:
        raise SystemExit(f'audio volume build guard missing: {needle}')

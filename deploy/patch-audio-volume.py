from pathlib import Path

GAME_PATH = Path('dist/game.js')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label} anchor missing')
    return text.replace(old, new, 1)


game = GAME_PATH.read_text(encoding='utf-8')

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

GAME_PATH.write_text(game, encoding='utf-8')

checks = {
    'audioVolumeRuntimeVersion: 0': game,
    'legacyMusicVolume * 12.5': game,
    'function effectiveMusicVolume(percent)': game,
    'displayVolume * 0.0008': game,
    'Math.min(0.08': game,
    'music?.setVolume(effectiveMusicVolume(musicVolume))': game,
    'music?.setVolume(effectiveMusicVolume(save.musicVolume))': game,
}
for needle, haystack in checks.items():
    if needle not in haystack:
        raise SystemExit(f'audio volume build guard missing: {needle}')

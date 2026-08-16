from pathlib import Path

GAME_PATH = Path('dist/game.js')
COUNT = 150
THEMES = [
    'desert-dunes', 'volcanic-lava', 'snowfield', 'ice-cave', 'tropical-beach',
    'forest', 'toxic-swamp', 'crystal-cave', 'ancient-temple', 'night-cemetery',
    'industrial-factory', 'neon-cybercity', 'circuit-board', 'lunar-surface', 'alien-planet',
]

text = GAME_PATH.read_text(encoding='utf-8')
start_marker = '  const gameplayBackgroundCatalog = Object.freeze(['
end_marker = '\n  ]);'
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('Gameplay background catalog anchor missing')
end += len(end_marker)

entries = []
for index in range(COUNT):
    number = index + 1
    theme = THEMES[index // 10]
    entries.append(
        "    { id: 'bank-%03d', key: 'backgroundBank%03d', file: 'bank-%03d.webp', "
        "src: './assets/backgrounds/bank-%03d.webp', theme: '%s', fallback: '#101827' },"
        % (number, number, number, number, theme)
    )

catalog = start_marker + '\n' + '\n'.join(entries) + '\n  ]);'
text = text[:start] + catalog + text[end:]

old_loader = 'loadImageAsset(background.key, assetManifest[background.key], timeoutMs)'
new_loader = 'loadImageAsset(background.key, background.src || assetManifest[background.key], timeoutMs)'
if old_loader not in text:
    raise SystemExit('Lazy background loader anchor missing')
text = text.replace(old_loader, new_loader, 1)

GAME_PATH.write_text(text, encoding='utf-8')
print(f'Patched Snake 2.0 gameplay catalog with {COUNT} backgrounds across {len(THEMES)} themes.')

from pathlib import Path
import re

GAME_PATH = Path('dist/game.js')
INDEX_PATH = Path('dist/index.html')
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
        "src: './assets/backgrounds/bank-%03d.webp', theme: '%s', fallback: '#101827', overlay: 'rgba(0,0,0,0)' },"
        % (number, number, number, number, theme)
    )

catalog = start_marker + '\n' + '\n'.join(entries) + '\n  ]);'
text = text[:start] + catalog + text[end:]

old_loader = 'loadImageAsset(background.key, assetManifest[background.key], timeoutMs)'
new_loader = 'loadImageAsset(background.key, background.src || assetManifest[background.key], timeoutMs)'
if old_loader not in text:
    raise SystemExit('Lazy background loader anchor missing')
text = text.replace(old_loader, new_loader, 1)

# Never let an undefined overlay reuse a previous opaque Canvas fillStyle.
old_overlay = '    frameCtx.fillStyle = background.overlay;'
new_overlay = "    frameCtx.fillStyle = background.overlay || 'rgba(0,0,0,0)';"
if old_overlay not in text:
    raise SystemExit('Background overlay render anchor missing')
text = text.replace(old_overlay, new_overlay, 1)

# Grid removal is permanent. Do not merely switch the saved preference off:
# delete the renderer so old localStorage values cannot bring the lines back.
text = re.sub(r"(\n\s*grid:\s*)true,", r"\1false,", text, count=1)
grid_block = re.compile(
    r"\n\s*if \(save\.grid\) \{\s*\n"
    r"\s*ctx\.strokeStyle = 'rgba\(225,240,225,\.08\)';\s*\n"
    r"\s*ctx\.lineWidth = 1;[\s\S]*?\n\s*\}\s*(?=\n)",
    re.MULTILINE,
)
text, removed = grid_block.subn('\n', text, count=1)
if removed != 1:
    raise SystemExit('Gameplay grid renderer anchor missing')
text = text.replace("\n  bindToggle('#toggleGrid', 'grid');", '', 1)

index = INDEX_PATH.read_text(encoding='utf-8')
index, removed_row = re.subn(
    r"\s*<div class=\"settings-row\"><div><b>Grille du plateau</b><p>Repères visuels pendant la partie</p></div><button class=\"toggle\" id=\"toggleGrid\"><i></i></button></div>\s*",
    '\n',
    index,
    count=1,
)
if removed_row != 1:
    raise SystemExit('Grid settings row missing')

GAME_PATH.write_text(text, encoding='utf-8')
INDEX_PATH.write_text(index, encoding='utf-8')
print(f'Patched Snake 2.0 with {COUNT} visible natural-look backgrounds and no gameplay grid.')

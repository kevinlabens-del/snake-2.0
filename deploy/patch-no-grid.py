from pathlib import Path
import re

GAME_PATH = Path('dist/game.js')
INDEX_PATH = Path('dist/index.html')

game = GAME_PATH.read_text(encoding='utf-8')
index = INDEX_PATH.read_text(encoding='utf-8')

# The board grid is intentionally removed from Snake 2.0. Keeping a saved
# preference must never reactivate it on an installed device.
game = re.sub(r"(\n\s*grid:\s*)true,", r"\1false,", game, count=1)

# Remove the complete grid drawing block from the production renderer.
grid_block = re.compile(
    r"\n\s*if \(save\.grid\) \{\s*\n"
    r"\s*ctx\.strokeStyle = 'rgba\(225,240,225,\.08\)';\s*\n"
    r"\s*ctx\.lineWidth = 1;[\s\S]*?\n\s*\}\s*(?=\n)",
    re.MULTILINE,
)
game, removed = grid_block.subn('\n', game, count=1)
if removed != 1:
    raise SystemExit('Gameplay grid drawing block not found')

# Remove the obsolete toggle binding. The setting cannot come back from UI.
game = game.replace("\n  bindToggle('#toggleGrid', 'grid');", '', 1)

# Remove the Grid setting row itself from the settings menu.
index, removed_row = re.subn(
    r"\s*<div class=\"settings-row\"><div><b>Grille du plateau</b><p>Repères visuels pendant la partie</p></div><button class=\"toggle\" id=\"toggleGrid\"><i></i></button></div>\s*",
    '\n',
    index,
    count=1,
)
if removed_row != 1:
    raise SystemExit('Grid settings row not found')

GAME_PATH.write_text(game, encoding='utf-8')
INDEX_PATH.write_text(index, encoding='utf-8')
print('Removed Snake 2.0 gameplay grid and its settings control.')

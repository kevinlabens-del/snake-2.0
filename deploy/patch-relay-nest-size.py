from pathlib import Path

GAME = Path('dist/game.js')

if not GAME.exists():
    raise SystemExit('dist/game.js missing')

text = GAME.read_text(encoding='utf-8')
old_contain = "if (assets.relayNest) drawImageContain(assets.relayNest,x,y,size,size);"
old_crop = "if (assets.relayNest) ctx.drawImage(assets.relayNest,1,3,30,23,x,y,size,size);"
# The PNG contains faint anti-aliased pixels around the actual nest. Cropping
# to the clearly visible artwork (alpha > 8 bbox) makes the nest itself, not
# merely its transparent image box, occupy the full 2x2 gameplay footprint.
new = "if (assets.relayNest) ctx.drawImage(assets.relayNest,3,5,26,19,x,y,size,size);"

if new not in text:
    if old_crop in text:
        text = text.replace(old_crop, new, 1)
    elif old_contain in text:
        text = text.replace(old_contain, new, 1)
    else:
        raise SystemExit('relay nest draw anchor missing')

# Collision and visual footprint must both remain exactly 2x2 cells.
required = [
    'const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2',
    'ctx.drawImage(assets.relayNest,3,5,26,19,x,y,size,size)',
    'relayNestCells(nest = state.relayNest)',
    '{x:nest.x,y:nest.y}',
    '{x:nest.x+1,y:nest.y}',
    '{x:nest.x,y:nest.y+1}',
    '{x:nest.x+1,y:nest.y+1}',
]
for needle in required:
    if needle not in text:
        raise SystemExit(f'relay nest 2x2 guard missing: {needle}')

for forbidden in [
    'drawImageContain(assets.relayNest,x,y,size,size)',
    'ctx.drawImage(assets.relayNest,1,3,30,23,x,y,size,size)',
]:
    if forbidden in text:
        raise SystemExit(f'old undersized relay nest rendering is still active: {forbidden}')

GAME.write_text(text, encoding='utf-8')
print('Relay nest visible artwork now fills the exact 2x2-cell gameplay footprint')

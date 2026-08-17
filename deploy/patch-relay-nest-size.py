from pathlib import Path

GAME = Path('dist/game.js')

if not GAME.exists():
    raise SystemExit('dist/game.js missing')

text = GAME.read_text(encoding='utf-8')
old = "if (assets.relayNest) drawImageContain(assets.relayNest,x,y,size,size);"
new = "if (assets.relayNest) ctx.drawImage(assets.relayNest,1,3,30,23,x,y,size,size);"

if new not in text:
    if old not in text:
        raise SystemExit('relay nest draw anchor missing')
    text = text.replace(old, new, 1)

# The nest collision zone remains exactly 2x2 cells; this patch only ensures
# the visible PNG artwork fills that same 2x2 footprint instead of being
# reduced by aspect-ratio fitting and transparent margins.
required = [
    'const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2',
    'ctx.drawImage(assets.relayNest,1,3,30,23,x,y,size,size)',
    'relayNestCells(nest = state.relayNest)',
]
for needle in required:
    if needle not in text:
        raise SystemExit(f'relay nest 2x2 guard missing: {needle}')

if 'drawImageContain(assets.relayNest,x,y,size,size)' in text:
    raise SystemExit('old contained relay nest rendering is still active')

GAME.write_text(text, encoding='utf-8')
print('Relay nest visual now fills the exact 2x2-cell gameplay footprint')

from pathlib import Path
import struct
import zlib

PNG = Path('dist/assets/relay/nest.png')
GAME = Path('dist/game.js')

if not PNG.exists() or not GAME.exists():
    raise SystemExit('relay visual audit inputs missing')

raw = PNG.read_bytes()
if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
    raise SystemExit('relay nest is not a PNG')

pos = 8
idat = bytearray()
width = height = bit_depth = color_type = None
while pos < len(raw):
    length = struct.unpack('>I', raw[pos:pos+4])[0]
    kind = raw[pos+4:pos+8]
    data = raw[pos+8:pos+8+length]
    pos += 12 + length
    if kind == b'IHDR':
        width, height, bit_depth, color_type, _, _, _ = struct.unpack('>IIBBBBB', data)
    elif kind == b'IDAT':
        idat.extend(data)
    elif kind == b'IEND':
        break

if (width, height, bit_depth, color_type) != (32, 28, 8, 6):
    raise SystemExit(f'unexpected relay nest PNG format: {(width, height, bit_depth, color_type)}')

inflated = zlib.decompress(bytes(idat))
bpp = 4
stride = width * bpp
rows = []
offset = 0
prev = bytearray(stride)

def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

for _ in range(height):
    f = inflated[offset]
    offset += 1
    scan = bytearray(inflated[offset:offset+stride])
    offset += stride
    out = bytearray(stride)
    for i, x in enumerate(scan):
        a = out[i-bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i-bpp] if i >= bpp else 0
        if f == 0: val = x
        elif f == 1: val = (x + a) & 255
        elif f == 2: val = (x + b) & 255
        elif f == 3: val = (x + ((a+b)//2)) & 255
        elif f == 4: val = (x + paeth(a,b,c)) & 255
        else: raise SystemExit(f'unsupported PNG filter {f}')
        out[i] = val
    rows.append(out)
    prev = out

# Ignore only nearly transparent anti-aliasing. This bbox is the artwork the
# player can actually see, and it is the source rectangle used by game.js.
xs, ys = [], []
for y, row in enumerate(rows):
    for x in range(width):
        alpha = row[x*bpp + 3]
        if alpha > 8:
            xs.append(x); ys.append(y)
visible_bbox = (min(xs), min(ys), max(xs)+1, max(ys)+1)
expected_bbox = (3, 5, 29, 24)
if visible_bbox != expected_bbox:
    raise SystemExit(f'visible nest bbox changed: {visible_bbox}, expected {expected_bbox}')

text = GAME.read_text(encoding='utf-8')
required = [
    'const x=state.relayNest.x*cell, y=state.relayNest.y*cell, size=cell*2',
    'ctx.drawImage(assets.relayNest,3,5,26,19,x,y,size,size)',
    'relayNestCells(nest = state.relayNest)',
]
for needle in required:
    if needle not in text:
        raise SystemExit(f'2x2 visual renderer missing: {needle}')

# Source bbox is mapped edge-to-edge onto a destination exactly 2 cells wide
# and 2 cells tall. Therefore the visible artwork is 2.00 x 2.00 cells.
source_w = visible_bbox[2] - visible_bbox[0]
source_h = visible_bbox[3] - visible_bbox[1]
if (source_w, source_h) != (26, 19):
    raise SystemExit('relay source crop no longer matches visible artwork')

print('Relay visual audit PASS: visible nest artwork = exactly 2.00 x 2.00 cells')

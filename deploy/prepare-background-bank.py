from pathlib import Path
import base64
from PIL import Image

PART_GLOB = 'background-bank-compact.part-*.b64'
ATLAS_PATH = Path('dist/.background-bank-atlas.webp')
OUTPUT_DIR = Path('dist/assets/backgrounds')
TILE = 96
COLUMNS = 15
ROWS = 10
EXPECTED = COLUMNS * ROWS

parts = sorted(Path('deploy').glob(PART_GLOB))
if len(parts) != 5:
    raise SystemExit(f'Expected 5 background bank chunks, found {len(parts)}')

encoded = ''.join(part.read_text(encoding='utf-8').strip() for part in parts)
try:
    atlas_bytes = base64.b64decode(encoded, validate=True)
except Exception as exc:
    raise SystemExit(f'Background bank base64 is invalid: {exc}')

ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
ATLAS_PATH.write_bytes(atlas_bytes)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with Image.open(ATLAS_PATH) as atlas:
    atlas.load()
    expected_size = (COLUMNS * TILE, ROWS * TILE)
    if atlas.size != expected_size:
        raise SystemExit(f'Unexpected atlas size {atlas.size}, expected {expected_size}')
    if atlas.mode not in ('RGB', 'RGBA'):
        atlas = atlas.convert('RGB')

    for index in range(EXPECTED):
        col = index % COLUMNS
        row = index // COLUMNS
        box = (col * TILE, row * TILE, (col + 1) * TILE, (row + 1) * TILE)
        tile = atlas.crop(box)
        target = OUTPUT_DIR / f'bank-{index + 1:03d}.webp'
        tile.save(target, 'WEBP', quality=82, method=6)

ATLAS_PATH.unlink(missing_ok=True)
created = sorted(OUTPUT_DIR.glob('bank-*.webp'))
if len(created) != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} generated backgrounds, found {len(created)}')

print(f'Prepared {len(created)} lazy-loaded Snake 2.0 backgrounds.')

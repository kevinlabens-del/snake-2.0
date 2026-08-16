from pathlib import Path
import base64
from PIL import Image, ImageEnhance, ImageFilter

PART_GLOB = 'background-bank-compact.part-*.b64'
ATLAS_PATH = Path('dist/.background-bank-atlas.webp')
OUTPUT_DIR = Path('dist/assets/backgrounds')
SOURCE_TILE = 96
OUTPUT_TILE = 384
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

# The 150-bank catalog replaces the nine legacy photograph backgrounds entirely.
# Keeping them in Pages only wastes several megabytes and can confuse audits.
for old in list(OUTPUT_DIR.glob('*.jpg')) + list(OUTPUT_DIR.glob('*.jpeg')):
    old.unlink(missing_ok=True)
for old in OUTPUT_DIR.glob('bank-*.webp'):
    old.unlink(missing_ok=True)

with Image.open(ATLAS_PATH) as atlas:
    atlas.load()
    expected_size = (COLUMNS * SOURCE_TILE, ROWS * SOURCE_TILE)
    if atlas.size != expected_size:
        raise SystemExit(f'Unexpected atlas size {atlas.size}, expected {expected_size}')
    if atlas.mode not in ('RGB', 'RGBA'):
        atlas = atlas.convert('RGB')

    for index in range(EXPECTED):
        col = index % COLUMNS
        row = index // COLUMNS
        box = (
            col * SOURCE_TILE,
            row * SOURCE_TILE,
            (col + 1) * SOURCE_TILE,
            (row + 1) * SOURCE_TILE,
        )
        tile = atlas.crop(box).convert('RGB')
        tile = tile.resize((OUTPUT_TILE, OUTPUT_TILE), Image.Resampling.LANCZOS)
        tile = ImageEnhance.Contrast(tile).enhance(1.04)
        tile = tile.filter(ImageFilter.UnsharpMask(radius=1.15, percent=115, threshold=3))
        target = OUTPUT_DIR / f'bank-{index + 1:03d}.webp'
        tile.save(target, 'WEBP', quality=86, method=6)

ATLAS_PATH.unlink(missing_ok=True)
created = sorted(OUTPUT_DIR.glob('bank-*.webp'))
if len(created) != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} generated backgrounds, found {len(created)}')

for probe in (created[0], created[len(created) // 2], created[-1]):
    with Image.open(probe) as image:
        if image.size != (OUTPUT_TILE, OUTPUT_TILE):
            raise SystemExit(f'{probe.name} has size {image.size}, expected {(OUTPUT_TILE, OUTPUT_TILE)}')

legacy = list(OUTPUT_DIR.glob('*.jpg')) + list(OUTPUT_DIR.glob('*.jpeg'))
if legacy:
    raise SystemExit(f'Legacy terrain JPGs remain in build: {[p.name for p in legacy]}')

print(
    f'Prepared {len(created)} lazy-loaded Snake 2.0 backgrounds at '
    f'{OUTPUT_TILE}x{OUTPUT_TILE}; legacy JPG terrains removed.'
)

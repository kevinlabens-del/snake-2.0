from pathlib import Path
import base64
import io
import zipfile
from PIL import Image

PART_GLOB = 'background-bank-hd.part-*.b64'
OUTPUT_DIR = Path('dist/assets/backgrounds')
EXPECTED = 150
EXPECTED_SIZE = (384, 384)
THEMES = [
    '01-desert-dunes', '02-volcanic-lava', '03-snowfield', '04-ice-cave', '05-tropical-beach',
    '06-forest', '07-toxic-swamp', '08-crystal-cave', '09-ancient-temple', '10-night-cemetery',
    '11-industrial-factory', '12-neon-cybercity', '13-circuit-board', '14-lunar-surface', '15-alien-planet',
]

parts = sorted(Path('deploy').glob(PART_GLOB))
if not parts:
    raise SystemExit('No HD background-bank chunks found')

encoded = ''.join(part.read_text(encoding='utf-8').strip() for part in parts)
try:
    archive_bytes = base64.b64decode(encoded, validate=True)
except Exception as exc:
    raise SystemExit(f'HD background bank base64 is invalid: {exc}')

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Remove the old 96px generated bank and the nine legacy JPG terrains. The
# current catalog exclusively uses the 150 HD WebP files below.
for old in OUTPUT_DIR.glob('bank-*.webp'):
    old.unlink()
for old in OUTPUT_DIR.glob('*.jpg'):
    old.unlink()
for old in OUTPUT_DIR.glob('*.jpeg'):
    old.unlink()

try:
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
except Exception as exc:
    raise SystemExit(f'HD background ZIP is invalid: {exc}')

source_names = []
for theme in THEMES:
    prefix = theme + '/'
    theme_files = sorted(
        name for name in archive.namelist()
        if name.startswith(prefix) and name.lower().endswith('.webp')
    )
    if len(theme_files) != 10:
        raise SystemExit(f'Expected 10 backgrounds for {theme}, found {len(theme_files)}')
    source_names.extend(theme_files)

if len(source_names) != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} HD backgrounds, found {len(source_names)}')

for index, source_name in enumerate(source_names, start=1):
    raw = archive.read(source_name)
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        if image.size != EXPECTED_SIZE:
            raise SystemExit(f'{source_name} has size {image.size}, expected {EXPECTED_SIZE}')
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        target = OUTPUT_DIR / f'bank-{index:03d}.webp'
        image.save(target, 'WEBP', quality=82, method=6)

created = sorted(OUTPUT_DIR.glob('bank-*.webp'))
if len(created) != EXPECTED:
    raise SystemExit(f'Expected {EXPECTED} generated HD backgrounds, found {len(created)}')

with Image.open(created[0]) as first, Image.open(created[-1]) as last:
    if first.size != EXPECTED_SIZE or last.size != EXPECTED_SIZE:
        raise SystemExit('Generated HD background dimensions are invalid')

print(f'Prepared {len(created)} lazy-loaded Snake 2.0 HD backgrounds at {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}.')

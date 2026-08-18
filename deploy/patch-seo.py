from pathlib import Path
import re

INDEX = Path('dist/index.html')
ROBOTS = Path('dist/robots.txt')
SITEMAP = Path('dist/sitemap.xml')

BASE = 'https://kevinlabens-del.github.io/snake-2.0/'
TITLE = 'Snake 2.0 — Jeu Snake gratuit en ligne | 600+ niveaux'
DESCRIPTION = ('Jouez gratuitement à Snake 2.0 : un jeu Snake moderne avec plus de 600 niveaux, '
               'missions, obstacles, portails et progression infinie sur mobile et ordinateur.')

html = INDEX.read_text(encoding='utf-8')

# Title
if re.search(r'<title>.*?</title>', html, flags=re.I | re.S):
    html = re.sub(r'<title>.*?</title>', f'<title>{TITLE}</title>', html, count=1, flags=re.I | re.S)
else:
    html = html.replace('</head>', f'  <title>{TITLE}</title>\n</head>', 1)

# Replace generic description or insert one.
if re.search(r'<meta\s+name=["\']description["\'][^>]*>', html, flags=re.I):
    html = re.sub(r'<meta\s+name=["\']description["\'][^>]*>',
                  f'<meta name="description" content="{DESCRIPTION}">', html, count=1, flags=re.I)
else:
    html = html.replace('</head>', f'  <meta name="description" content="{DESCRIPTION}">\n</head>', 1)

seo_block = f'''\n  <!-- SEO Snake 2.0 -->
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="{BASE}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="fr_FR">
  <meta property="og:title" content="{TITLE}">
  <meta property="og:description" content="{DESCRIPTION}">
  <meta property="og:url" content="{BASE}">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "VideoGame",
    "name": "Snake 2.0",
    "url": "{BASE}",
    "description": "{DESCRIPTION}",
    "genre": ["Arcade", "Snake", "Casual"],
    "applicationCategory": "GameApplication",
    "operatingSystem": "Web, Android, Windows, macOS, iOS",
    "inLanguage": "fr-FR",
    "offers": {{"@type": "Offer", "price": "0", "priceCurrency": "EUR"}}
  }}
  </script>
'''

# Remove an older generated block if a later build reruns this patch.
html = re.sub(r'\n\s*<!-- SEO Snake 2\.0 -->.*?</script>\s*', '\n', html, count=1, flags=re.I | re.S)
html = html.replace('</head>', seo_block + '</head>', 1)

INDEX.write_text(html, encoding='utf-8')
ROBOTS.write_text('User-agent: *\nAllow: /\n\nSitemap: ' + BASE + 'sitemap.xml\n', encoding='utf-8')
SITEMAP.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{BASE}</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
''', encoding='utf-8')

# Build guards
final = INDEX.read_text(encoding='utf-8')
for needle in (TITLE, 'name="robots" content="index,follow,max-image-preview:large"',
               f'rel="canonical" href="{BASE}"', '"@type": "VideoGame"'):
    if needle not in final:
        raise SystemExit(f'SEO build guard missing: {needle}')
if not ROBOTS.exists() or not SITEMAP.exists():
    raise SystemExit('SEO files were not generated')

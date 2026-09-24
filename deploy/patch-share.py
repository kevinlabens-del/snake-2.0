from pathlib import Path

INDEX = Path("dist/index.html")
SW = Path("dist/sw.js")

html = INDEX.read_text(encoding="utf-8")

share_row = '''        <div class="settings-row share-settings-row">
          <div>
            <b>Partager Snake 2.0</b>
            <p id="shareAppStatus" role="status" aria-live="polite">Lien public uniquement · aucune progression envoyée</p>
          </div>
          <button class="secondary" id="shareAppBtn" type="button" aria-label="Partager Snake 2.0" title="Partager le jeu">↗ Partager</button>
        </div>
'''

if 'id="shareAppBtn"' not in html:
    anchor = '        <div class="settings-row"><div><b>Réinitialiser la progression</b><p>Efface niveaux, scores et succès</p></div><button class="secondary" id="resetBtn">Réinitialiser</button></div>'
    if anchor not in html:
        raise SystemExit("Snake share target missing: settings reset row not found")
    html = html.replace(anchor, share_row + anchor, 1)

if 'share-app.js' not in html:
    anchor = '<script src="game.js?v=2.2.10-haptics1"></script>'
    if anchor not in html:
        raise SystemExit("Snake share script target missing: game runtime tag not found")
    html = html.replace(anchor, anchor + '\n<script src="share-app.js?v=20260924-share1"></script>', 1)

INDEX.write_text(html, encoding="utf-8")

sw = SW.read_text(encoding="utf-8")
if "'./share-app.js'" not in sw:
    anchor = "  './snake2-stats.js',"
    if anchor not in sw:
        raise SystemExit("Snake share cache target missing")
    sw = sw.replace(anchor, anchor + "\n  './share-app.js',", 1)
SW.write_text(sw, encoding="utf-8")

final = INDEX.read_text(encoding="utf-8")
for needle in (
    'id="shareAppBtn"',
    'id="shareAppStatus"',
    'share-app.js?v=20260924-share1',
    'Lien public uniquement',
):
    if needle not in final:
        raise SystemExit(f"Snake share build guard missing: {needle}")

if "'./share-app.js'" not in SW.read_text(encoding="utf-8"):
    raise SystemExit("Snake share runtime missing from service worker core cache")

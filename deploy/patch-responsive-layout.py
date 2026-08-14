from pathlib import Path
import json
import re


INDEX_PATH = Path('dist/index.html')
STYLES_PATH = Path('dist/styles-v225.css')
GAME_PATH = Path('dist/game.js')
MANIFEST_PATH = Path('dist/manifest.webmanifest')
INSTALL_GATE_PATH = Path('dist/install-gate-v225.js')
SW_PATH = Path('dist/sw.js')


index = INDEX_PATH.read_text(encoding='utf-8')

# Do not advertise or render a portrait-only experience. The layout below adapts
# the same square board to portrait phones and landscape desktops/tablets.
index = re.sub(
    r'\s*<meta\s+name=["\']screen-orientation["\']\s+content=["\']portrait["\']\s*/?>',
    '',
    index,
    count=1,
    flags=re.IGNORECASE,
)
index, removed_guard = re.subn(
    r'\s*<div class="portrait-guard" id="portraitGuard"[^>]*>\s*'
    r'<div class="portrait-guard-card">.*?</div>\s*</div>\s*',
    '\n',
    index,
    count=1,
    flags=re.DOTALL,
)
if removed_guard != 1 and 'id="portraitGuard"' in index:
    raise SystemExit('portrait-only guard could not be removed')

old_tutorial = (
    '<article class="tutorial-card"><span>👆</span><div><h3>Commandes tactiles</h3>'
    '<p>Glisse simplement ton doigt sur le plateau vers le haut, le bas, la gauche ou la droite. '
    'Les boutons directionnels ne sont pas nécessaires.</p></div></article>'
)
new_tutorial = (
    '<article class="tutorial-card"><span>🎮</span><div><h3>Commandes tactiles et clavier</h3>'
    '<p>Sur mobile, glisse ton doigt sur le plateau. Sur ordinateur, utilise les flèches du clavier '
    'ou les touches ZQSD/WASD pour diriger le serpent.</p></div></article>'
)
if old_tutorial in index:
    index = index.replace(old_tutorial, new_tutorial, 1)
elif 'Commandes tactiles et clavier' not in index:
    raise SystemExit('tutorial controls anchor missing')

index = re.sub(
    r'href="manifest\.webmanifest(?:\?v=[^"]*)?"',
    'href="manifest.webmanifest?v=2.2.8-responsive1"',
    index,
    count=1,
)
index = re.sub(
    r'styles-v225\.css\?v=[^"\']+',
    'styles-v225.css?v=2.2.8-responsive1',
    index,
    count=1,
)
index = re.sub(
    r'install-gate-v225\.js\?v=[^"\']+',
    'install-gate-v225.js?v=2.2.8-responsive1',
    index,
    count=1,
)
index = re.sub(
    r'game\.js\?v=[^"\']+',
    'game.js?v=2.2.8-responsive1',
    index,
    count=1,
)
INDEX_PATH.write_text(index, encoding='utf-8')


game = GAME_PATH.read_text(encoding='utf-8')
portrait_lock = """    try {
      if (screen.orientation?.lock) await screen.orientation.lock('portrait-primary');
    } catch {}
"""
orientation_unlock = """    try {
      // Respect the player's current device orientation instead of forcing portrait.
      if (screen.orientation?.unlock) screen.orientation.unlock();
    } catch {}
"""
if portrait_lock in game:
    game = game.replace(portrait_lock, orientation_unlock, 1)
elif "screen.orientation.lock('portrait-primary')" in game:
    raise SystemExit('unexpected portrait orientation lock')
elif 'screen.orientation?.unlock' not in game:
    raise SystemExit('immersive orientation anchor missing')
GAME_PATH.write_text(game, encoding='utf-8')


styles = STYLES_PATH.read_text(encoding='utf-8')
responsive_marker = '/* Snake 2.0 v2.2.8 — portrait + paysage réellement jouables */'
responsive_styles = r'''

/* Snake 2.0 v2.2.8 — portrait + paysage réellement jouables */
.portrait-guard{display:none!important}

@media (orientation:landscape) and (min-width:520px){
  body.game-active .app{
    width:100%;
    max-width:1400px;
    padding:
      max(6px,env(safe-area-inset-top))
      max(10px,env(safe-area-inset-right))
      max(8px,env(safe-area-inset-bottom))
      max(10px,env(safe-area-inset-left));
  }
  body.game-active .topbar{
    position:relative;
    width:min(100%,1220px);
    margin:0 auto;
    padding:1px 0 5px;
    grid-template-columns:44px minmax(230px,380px) 44px;
  }
  body.game-active .icon-btn{width:40px;height:40px;border-radius:13px;font-size:18px}
  body.game-active .brand{padding:6px 14px 7px;border-radius:16px}
  body.game-active .brand::before{inset:4px;border-radius:13px}
  body.game-active .brand::after{width:8px;height:8px;right:12px;top:10px}
  body.game-active .brand strong{font-size:clamp(22px,4.2dvh,31px)}
  body.game-active .brand span{font-size:7px}
  body.game-active .quick-volume{width:min(280px,34vw);margin:-3px auto 3px;padding:1px 7px}
  body.game-active main{
    width:100%;
    height:calc(100dvh - 76px - max(6px,env(safe-area-inset-top)) - max(8px,env(safe-area-inset-bottom)));
    min-height:0;
  }
  body.game-active #gameScreen.active{
    display:grid;
    grid-template-columns:clamp(185px,26vw,330px) minmax(0,1fr);
    grid-template-rows:auto auto minmax(0,1fr) auto;
    grid-template-areas:
      "hud board"
      "progress board"
      "mission board"
      "tools board";
    column-gap:clamp(9px,2vw,28px);
    row-gap:5px;
    width:min(100%,1220px);
    height:100%;
    margin:0 auto;
    align-items:stretch;
    overflow:hidden;
  }
  body.game-active .game-hud{
    grid-area:hud;
    margin:0;
    gap:6px;
    align-self:start;
  }
  body.game-active .hud-box{padding:7px 5px;border-radius:13px}
  body.game-active .hud-box b{font-size:15px}
  body.game-active .hud-box span{font-size:7px;letter-spacing:.11em}
  body.game-active .progress{
    grid-area:progress;
    width:100%;
    height:6px;
    margin:0;
    align-self:start;
  }
  body.game-active .mission-strip{
    grid-area:mission;
    min-height:0;
    max-height:100%;
    margin:0;
    padding:10px 11px;
    align-self:start;
    overflow:auto;
    overscroll-behavior:contain;
  }
  body.game-active .mission-strip strong{font-size:12px}
  body.game-active .mission-strip span{font-size:10px}
  body.game-active .game-shell{
    grid-area:board;
    align-self:center;
    justify-self:center;
    width:min(100%,calc(100dvh - 88px),860px);
    max-width:100%;
    max-height:100%;
    margin:0;
    border-radius:clamp(18px,2.1vw,28px);
  }
  body.game-active .game-tools{
    grid-area:tools;
    width:100%;
    margin:0;
    gap:7px;
    align-self:end;
  }
  body.game-active .game-tools .secondary{padding:9px 8px;font-size:11px}
  body.game-active .game-tools .tutorial-tool{flex-basis:40px;min-width:40px;border-radius:12px;font-size:17px}
}

@media (orientation:landscape) and (min-width:520px) and (max-height:500px){
  body.game-active .topbar{
    padding:0 0 3px;
    grid-template-columns:38px minmax(210px,340px) 38px;
  }
  body.game-active .icon-btn{width:36px;height:36px;border-radius:11px;font-size:16px}
  body.game-active .brand{padding:4px 12px 5px}
  body.game-active .brand strong{font-size:20px}
  body.game-active .brand span{display:none}
  body.game-active .quick-volume{display:none}
  body.game-active main{
    height:calc(100dvh - 43px - max(6px,env(safe-area-inset-top)) - max(8px,env(safe-area-inset-bottom)));
  }
  body.game-active #gameScreen.active{
    grid-template-columns:clamp(170px,29vw,270px) minmax(0,1fr);
    column-gap:8px;
    row-gap:3px;
  }
  body.game-active .hud-box{padding:4px 3px;border-radius:10px}
  body.game-active .hud-box b{font-size:13px}
  body.game-active .hud-box span{font-size:6px}
  body.game-active .progress{height:4px}
  body.game-active .mission-strip{padding:6px 8px;border-radius:11px}
  body.game-active .mission-strip strong{font-size:10px;line-height:1.15}
  body.game-active .mission-strip span{font-size:8px;line-height:1.2}
  body.game-active .game-shell{width:min(100%,calc(100dvh - 51px),560px)}
  body.game-active .game-tools{gap:4px}
  body.game-active .game-tools .secondary{padding:6px 5px;font-size:9px;border-radius:10px}
  body.game-active .game-tools .tutorial-tool{flex-basis:32px;min-width:32px;border-radius:10px;font-size:14px}
}
'''
if responsive_marker not in styles:
    styles += responsive_styles
STYLES_PATH.write_text(styles, encoding='utf-8')


manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
manifest['orientation'] = 'any'
MANIFEST_PATH.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)


install_gate = INSTALL_GATE_PATH.read_text(encoding='utf-8')
install_gate = re.sub(
    r"const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_[^']+';",
    "const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_responsive_v20';",
    install_gate,
    count=1,
)
install_gate = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.8-responsive1'",
    install_gate,
    count=1,
)
INSTALL_GATE_PATH.write_text(install_gate, encoding='utf-8')


sw = SW_PATH.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';",
    "const CACHE = 'snake-2.0-v2.2.8-responsive-landscape-20260814-v20';",
    sw,
    count=1,
)
SW_PATH.write_text(sw, encoding='utf-8')

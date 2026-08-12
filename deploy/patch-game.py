from pathlib import Path
import re, json

game = Path('dist/game.js')
js = game.read_text(encoding='utf-8')

js = js.replace("    save.gamesPlayed++;\n    window.snake2TrackGameStart?.();", "    save.gamesPlayed++;")
needle = "    state.levelComplete = true; state.running = false;\n    recordMissionOutcome(true, snapshot);"
hook = "    state.levelComplete = true; state.running = false;\n    window.snake2TrackGameStart?.();\n    recordMissionOutcome(true, snapshot);"
if 'state.levelComplete = true; state.running = false;\n    window.snake2TrackGameStart?.();' not in js:
    if needle not in js:
        raise SystemExit('completeLevel hook point missing')
    js = js.replace(needle, hook, 1)

old_loop = """      state.acc += dt * 1000;
      const dynamicStep = missionDynamicStep();
      state.visualStepMs = dynamicStep;
      if (state.acc >= dynamicStep) {
        state.acc -= dynamicStep;
        step();
      }"""
new_loop = """      state.acc += dt * 1000;
      let dynamicStep = missionDynamicStep();
      state.visualStepMs = dynamicStep;
      let catchUpSteps = 0;
      while (state.running && state.acc >= dynamicStep && catchUpSteps < 5) {
        state.acc -= dynamicStep;
        step();
        catchUpSteps++;
        dynamicStep = missionDynamicStep();
        state.visualStepMs = dynamicStep;
      }
      if (catchUpSteps >= 5) state.acc = Math.min(state.acc, dynamicStep);"""
if old_loop not in js:
    raise SystemExit('game loop point missing')
js = js.replace(old_loop, new_loop, 1)

old_stride = "const detailStride = points.length > 120 ? 3 : points.length > 58 ? 2 : 1;"
if old_stride not in js:
    raise SystemExit('body detail stride point missing')
js = js.replace(old_stride, "const detailStride = points.length > 72 ? 4 : points.length > 36 ? 3 : points.length > 18 ? 2 : 1;", 1)

if "  let bodySpineGradient = null;" not in js:
    marker = "  const wavePointBuffer = [];"
    if marker not in js:
        raise SystemExit('wave buffer point missing')
    js = js.replace(marker, marker + "\n  let bodySpineGradient = null;", 1)
old_grad = """    const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    grad.addColorStop(0, '#080a0b');
    grad.addColorStop(.40, '#30363a');
    grad.addColorStop(.62, '#0b0e10');
    grad.addColorStop(1, '#020304');
    ctx.shadowBlur = 0;
    ctx.strokeStyle = grad;"""
new_grad = """    if (!bodySpineGradient) {
      bodySpineGradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
      bodySpineGradient.addColorStop(0, '#080a0b');
      bodySpineGradient.addColorStop(.40, '#30363a');
      bodySpineGradient.addColorStop(.62, '#0b0e10');
      bodySpineGradient.addColorStop(1, '#020304');
    }
    ctx.shadowBlur = 0;
    ctx.strokeStyle = bodySpineGradient;"""
if old_grad not in js:
    raise SystemExit('body gradient point missing')
js = js.replace(old_grad, new_grad, 1)
game.write_text(js, encoding='utf-8')

index = Path('dist/index.html')
html = index.read_text(encoding='utf-8')
html = re.sub(r'<script src="https://cdn\.jsdelivr\.net/npm/@supabase/supabase-js@2"(?: defer)?></script>\s*', '', html)
html = re.sub(r'<script src="\./snake2-stats\.js(?:\?v=[^"]*)?" defer></script>\s*', '', html)
html = re.sub(r'game\.js\?v=2\.2\.5(?:-stats\d+|-perf\d+)?', 'game.js?v=2.2.5-perf1', html)
html = re.sub(r'install-gate-v225\.js\?v=[^"]+', 'install-gate-v225.js?v=2.2.6-install6', html)
scripts = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" defer></script>\n  <script src="./snake2-stats.js?v=20260812h" defer></script>'
pos = html.lower().rfind('</body>')
html = html[:pos] + '  ' + scripts + '\n' + html[pos:] if pos >= 0 else html + '\n' + scripts
index.write_text(html, encoding='utf-8')

install_gate = Path('dist/install-gate-v225.js')
install_text = install_gate.read_text(encoding='utf-8')
old_launch = """    const launchUrl = new URL('./', location.href);
    launchUrl.searchParams.set('source', 'installed-open');
    launchUrl.searchParams.set('autostart', '1');
    launchUrl.searchParams.set('t', String(Date.now()));

    // Keep the user gesture synchronous so Android can hand the URL to the PWA
    // when link capture is supported. Failure simply leaves the browser page open.
    window.open(launchUrl.href, '_blank', 'noopener');

    // Refresh browser state once. No install state is persisted, so a browser reload
    // can never manufacture an \"installed\" status.
    setTimeout(() => {
      const clean = new URL(location.href);
      clean.searchParams.set('refresh', String(Date.now()));
      location.replace(clean.href);
    }, 350);"""
new_launch = """    const launchUrl = new URL('./', location.href);
    launchUrl.search = '';
    launchUrl.hash = '';
    launchUrl.searchParams.set('source', 'installed-open');
    launchUrl.searchParams.set('autostart', '1');
    launchUrl.searchParams.set('t', String(Date.now()));

    // One navigation only. Using _self avoids a competing browser tab plus reload.
    // On Android, an installed PWA that captures this scope can take over this URL;
    // otherwise the same page reloads cleanly and never creates a second tab.
    window.location.assign(launchUrl.href);"""
if old_launch not in install_text:
    raise SystemExit('refreshAndLaunch navigation block missing')
install_text = install_text.replace(old_launch, new_launch, 1)
install_text = install_text.replace("serviceWorker.register('./sw.js?v=2.2.6-install5'", "serviceWorker.register('./sw.js?v=2.2.6-install6'", 1)
install_gate.write_text(install_text, encoding='utf-8')

manifest_path = Path('dist/manifest.webmanifest')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['launch_handler'] = {'client_mode': ['navigate-existing', 'auto']}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

sw = Path('dist/sw.js')
if sw.exists():
    text = sw.read_text(encoding='utf-8')
    text = re.sub(r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';", "const CACHE = 'snake-2.0-v2.2.6-install-truth-20260812-v6';", text, count=1)
    if "'./snake2-stats.js'" not in text:
        text = text.replace("const CORE_ASSETS = [", "const CORE_ASSETS = [\n  './snake2-stats.js',")

    critical_fn = """
async function networkFirstCritical(request) {
  const cache = await caches.open(CACHE);
  const key = normalizedRequest(request);
  try {
    const response = await fetch(request, { cache: 'no-store' });
    if (!validResponse(request, response)) throw new Error('Réponse critique invalide');
    try { await cache.put(key, response.clone()); } catch (_) {}
    return response;
  } catch (_) {
    const cached = await cache.match(key);
    if (cached) return cached;
    throw new Error('Ressource critique indisponible');
  }
}

"""
    if 'async function networkFirstCritical' not in text:
        text = text.replace("self.addEventListener('fetch', event => {", critical_fn + "self.addEventListener('fetch', event => {")

    old_respond = "event.respondWith(request.mode === 'navigate' ? navigationFastStart(request) : (isAudio ? audioResponse(request) : staleWhileRevalidate(request)));"
    new_respond = """const isInstallGate = /\/install-gate-v225\.js$/i.test(url.pathname);
  event.respondWith(
    request.mode === 'navigate'
      ? navigationFastStart(request)
      : (isAudio ? audioResponse(request) : (isInstallGate ? networkFirstCritical(request) : staleWhileRevalidate(request)))
  );"""
    if old_respond in text:
        text = text.replace(old_respond, new_respond, 1)
    elif 'isInstallGate' not in text:
        raise SystemExit('service worker fetch routing point missing')
    sw.write_text(text, encoding='utf-8')

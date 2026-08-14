from pathlib import Path
import re, json

game = Path('dist/game.js')
js = game.read_text(encoding='utf-8')

js = js.replace("    save.gamesPlayed++;\n    window.snake2TrackGameStart?.();", "    save.gamesPlayed++;")

start_needle = """      onMissionStart: snapshot => {
        state.missionSnapshot = snapshot;
        state.mission = snapshot.mission;
        applyMissionSettings(snapshot.mission);
"""
start_hook = """      onMissionStart: snapshot => {
        state.missionSnapshot = snapshot;
        state.mission = snapshot.mission;
        window.snake2TrackLevelStart?.({ level: state.level, daily: state.isDaily });
        applyMissionSettings(snapshot.mission);
"""
if 'window.snake2TrackLevelStart?.({ level: state.level, daily: state.isDaily });' not in js:
    if start_needle not in js:
        raise SystemExit('level start statistics hook point missing')
    js = js.replace(start_needle, start_hook, 1)

complete_needle = "    state.levelComplete = true; state.running = false;\n    recordMissionOutcome(true, snapshot);"
complete_hook = "    state.levelComplete = true; state.running = false;\n    window.snake2TrackLevelComplete?.({ level: state.level, daily: state.isDaily });\n    recordMissionOutcome(true, snapshot);"
if 'window.snake2TrackLevelComplete?.({ level: state.level, daily: state.isDaily });' not in js:
    if complete_needle not in js:
        raise SystemExit('level completion statistics hook point missing')
    js = js.replace(complete_needle, complete_hook, 1)

abort_needle = "    state.outcomeRecorded = true;\n    if (state.isDaily) save.dailyAborts"
abort_hook = "    state.outcomeRecorded = true;\n    window.snake2TrackLevelEnd?.();\n    if (state.isDaily) save.dailyAborts"
if 'state.outcomeRecorded = true;\n    window.snake2TrackLevelEnd?.();\n    if (state.isDaily) save.dailyAborts' not in js:
    if abort_needle not in js:
        raise SystemExit('level abort statistics hook point missing')
    js = js.replace(abort_needle, abort_hook, 1)

loss_needle = "    state.running = false;\n    state.gameOver = true;\n    recordMissionOutcome(false, snapshot);"
loss_hook = "    state.running = false;\n    state.gameOver = true;\n    window.snake2TrackLevelEnd?.();\n    recordMissionOutcome(false, snapshot);"
if 'state.gameOver = true;\n    window.snake2TrackLevelEnd?.();\n    recordMissionOutcome(false, snapshot);' not in js:
    if loss_needle not in js:
        raise SystemExit('level loss statistics hook point missing')
    js = js.replace(loss_needle, loss_hook, 1)

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
html = re.sub(r'<script src="https://cdn\.jsdelivr\.net/npm/@supabase/supabase-js@[^\"]+"(?: defer)?></script>\s*', '', html)
html = re.sub(r'<script src="\./snake2-stats\.js(?:\?v=[^"]*)?" defer></script>\s*', '', html)
html = re.sub(r'game\.js\?v=2\.2\.5(?:-stats\d+|-perf\d+|-headsweep\d+)?', 'game.js?v=2.2.5-headsweep2', html)
html = re.sub(r'install-gate-v225\.js\?v=[^"]+', 'install-gate-v225.js?v=2.2.6-install14', html)
scripts = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.112.3" defer></script>\n  <script src="./snake2-stats.js?v=20260814-stats-secure1" defer></script>'
pos = html.lower().rfind('</body>')
html = html[:pos] + '  ' + scripts + '\n' + html[pos:] if pos >= 0 else html + '\n' + scripts
index.write_text(html, encoding='utf-8')

install_gate = Path('dist/install-gate-v225.js')
install_text = install_gate.read_text(encoding='utf-8')

persist_boot = """
  const INSTALL_CONFIRM_KEY = 'snake2_install_confirmed_v4';
  const AUTO_LAUNCH_GUARD_KEY = 'snake2_auto_launch_guard_v2';
  const AUTO_LAUNCH_GUARD_MS = 60000;
  const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_visual_v17';
  const HAD_SW_CONTROLLER_AT_BOOT = Boolean(navigator.serviceWorker?.controller);
  let persistedInstallConfirmedAt = 0;
  try {
    const raw = Number(localStorage.getItem(INSTALL_CONFIRM_KEY) || 0);
    if (Number.isFinite(raw) && raw > 0) persistedInstallConfirmedAt = raw;
  } catch (_) {}
"""
if "const INSTALL_CONFIRM_KEY = 'snake2_install_confirmed_v4';" not in install_text:
    marker = "  const state = {"
    if marker not in install_text:
        raise SystemExit('install state marker missing')
    install_text = install_text.replace(marker, persist_boot + "\n" + marker, 1)

install_text = install_text.replace('    installCompleted: false,', '    installCompleted: persistedInstallConfirmedAt > 0,', 1)
install_text = install_text.replace('    installConfirmedAt: 0,', '    installConfirmedAt: persistedInstallConfirmedAt,', 1)

state_marker = "    swReady: false,\n    startedAt: performance.now()"
if 'navigationInProgress: false' not in install_text:
    if state_marker not in install_text:
        raise SystemExit('navigation state marker missing')
    install_text = install_text.replace(state_marker, "    swReady: false,\n    navigationInProgress: false,\n    autoLaunchAttempted: false,\n    swUpdateReloaded: false,\n    startedAt: performance.now()", 1)

install_text = install_text.replace("    button = document.createElement('button');\n    button.id = 'installRefreshBtn';\n    button.type = 'button';", "    button = document.createElement('a');\n    button.id = 'installRefreshBtn';\n    button.href = './';\n    button.target = '_blank';\n    button.rel = 'noopener';\n    button.setAttribute('role', 'button');", 1)

show_marker = "    if (label) label.textContent = 'Rafraîchir et ouvrir l’application';\n  }"
show_replacement = """    if (label) label.textContent = 'Rafraîchir et ouvrir l’application';
    if (allowed) {
      const launchUrl = new URL('./', location.href);
      launchUrl.search = '';
      launchUrl.hash = '';
      launchUrl.searchParams.set('source', 'installed-open');
      launchUrl.searchParams.set('autostart', '1');
      launchUrl.searchParams.set('t', String(Date.now()));
      button.href = launchUrl.href;
      button.target = '_blank';
    }
  }"""
if show_marker in install_text:
    install_text = install_text.replace(show_marker, show_replacement, 1)

start = install_text.find('  function refreshAndLaunch(')
end = install_text.find('\n  function autoStartInstalledGame()', start)
if start < 0 or end < 0:
    raise SystemExit('refreshAndLaunch function missing')
new_launch_fn = """  function refreshAndLaunch(event) {
    if (!hasInstallConfirmation()) {
      event?.preventDefault();
      showRefreshButton(false);
      refreshGate();
      return;
    }
    if (state.navigationInProgress) {
      event?.preventDefault();
      return;
    }
    state.navigationInProgress = true;
    setAutoLaunchGuard();
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
    const link = ensureRefreshButton();
    if (link) {
      const label = link.querySelector('b');
      if (label) label.textContent = 'Ouverture de l’application…';
    }
  }

  function autoLaunchGuardIsActive() {
    try {
      const attemptedAt = Number(localStorage.getItem(AUTO_LAUNCH_GUARD_KEY) || 0);
      return Number.isFinite(attemptedAt) && Date.now() - attemptedAt < AUTO_LAUNCH_GUARD_MS;
    } catch (_) {
      return state.autoLaunchAttempted;
    }
  }

  function setAutoLaunchGuard() {
    state.autoLaunchAttempted = true;
    try { localStorage.setItem(AUTO_LAUNCH_GUARD_KEY, String(Date.now())); } catch (_) {}
  }

  async function scheduleAutomaticRefreshAndLaunch(source = 'browser', delayMs = 0) {
    if (!isAndroid() || isInstalledLaunch() || !hasInstallConfirmation() ||
        state.autoLaunchAttempted || autoLaunchGuardIsActive()) return;
    state.autoLaunchAttempted = true;

    setTimeout(async () => {
      if (isInstalledLaunch() || !hasInstallConfirmation() || state.deferredPrompt) {
        state.autoLaunchAttempted = false;
        return;
      }
      if (autoLaunchGuardIsActive()) return;

      if (typeof navigator.getInstalledRelatedApps === 'function') {
        try {
          const relatedApps = await navigator.getInstalledRelatedApps();
          if (Array.isArray(relatedApps) && relatedApps.length > 0 &&
              !relatedApps.some(app => app?.platform === 'webapp')) {
            state.autoLaunchAttempted = false;
            return;
          }
        } catch (_) {}
      }

      setAutoLaunchGuard();
      state.navigationInProgress = true;
      clearInterval(state.preparationTimer);
      state.preparationTimer = null;
      setStatus('Ouverture de Snake 2.0', 'Passage automatique du navigateur vers l’application…', 'installed');

      const launchUrl = new URL('./', location.href);
      launchUrl.search = '';
      launchUrl.hash = '';
      launchUrl.searchParams.set('source', source === 'install' ? 'installed-auto' : 'browser-auto');
      launchUrl.searchParams.set('handoff', '1');
      launchUrl.searchParams.set('t', String(Date.now()));
      location.replace(launchUrl.href);
    }, delayMs);
  }
"""
install_text = install_text[:start] + new_launch_fn + install_text[end:]

appinstalled_line = "    state.installConfirmedAt = Date.now();"
if appinstalled_line in install_text and 'localStorage.setItem(INSTALL_CONFIRM_KEY' not in install_text:
    install_text = install_text.replace(appinstalled_line, appinstalled_line + "\n    try { localStorage.setItem(INSTALL_CONFIRM_KEY, String(state.installConfirmedAt)); } catch (_) {}", 1)

appinstalled_start = install_text.find("  window.addEventListener('appinstalled'")
appinstalled_end = install_text.find("\n  window.addEventListener('DOMContentLoaded'", appinstalled_start)
if appinstalled_start < 0 or appinstalled_end < 0:
    raise SystemExit('appinstalled block missing')
appinstalled_block = install_text[appinstalled_start:appinstalled_end]
if "scheduleAutomaticRefreshAndLaunch('install', 450);" not in appinstalled_block:
    marker = "    showInstalledAction();"
    if marker not in appinstalled_block:
        raise SystemExit('appinstalled launch marker missing')
    appinstalled_block = appinstalled_block.replace(
        marker,
        marker + "\n    scheduleAutomaticRefreshAndLaunch('install', 450);",
        1,
    )
    install_text = install_text[:appinstalled_start] + appinstalled_block + install_text[appinstalled_end:]

before_marker = "  window.addEventListener('beforeinstallprompt', event => {\n    event.preventDefault();"
if before_marker in install_text and 'localStorage.removeItem(INSTALL_CONFIRM_KEY)' not in install_text.split("window.addEventListener('beforeinstallprompt'",1)[1].split("window.addEventListener('appinstalled'",1)[0]:
    install_text = install_text.replace(before_marker, before_marker + "\n    try { localStorage.removeItem(INSTALL_CONFIRM_KEY); } catch (_) {}\n    persistedInstallConfirmedAt = 0;", 1)

refresh_marker = "  function refreshGate() {\n"
segment = install_text.split('function refreshGate()',1)[1].split('function refreshAndLaunch()',1)[0]
if 'if (state.navigationInProgress) return;' not in segment:
    install_text = install_text.replace(refresh_marker, refresh_marker + "    if (state.navigationInProgress) return;\n", 1)

visibility_old = """  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') refreshGate();
  });"""
visibility_new = """  document.addEventListener('visibilitychange', () => {
    if (!state.navigationInProgress && document.visibilityState === 'visible') refreshGate();
  });

  window.addEventListener('pagehide', () => {
    state.navigationInProgress = true;
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
  });"""
if visibility_old in install_text:
    install_text = install_text.replace(visibility_old, visibility_new, 1)

autostart_marker = "  function autoStartInstalledGame() {\n    const params = new URLSearchParams(location.search);\n"
autostart_guard = """  function autoStartInstalledGame() {
    const params = new URLSearchParams(location.search);
    if (params.get('handoff') === '1') state.autoLaunchAttempted = true;
    if (params.get('autostart') === '1' && !isInstalledLaunch()) {
      const clean = new URL(location.href);
      ['autostart','source','handoff','t'].forEach(key => clean.searchParams.delete(key));
      history.replaceState(null, '', clean.href);
      state.navigationInProgress = false;
      if (hasInstallConfirmation()) showInstalledAction();
      return;
    }
"""
if autostart_marker in install_text:
    install_text = install_text.replace(autostart_marker, autostart_guard, 1)

boot_marker = "    refreshGate();\n    autoStartInstalledGame();"
boot_replacement = boot_marker + "\n    scheduleAutomaticRefreshAndLaunch('browser', 0);"
if boot_marker not in install_text:
    raise SystemExit('automatic browser launch marker missing')
if "scheduleAutomaticRefreshAndLaunch('browser', 0);" not in install_text:
    install_text = install_text.replace(boot_marker, boot_replacement, 1)

sw_reload_marker = "  if ('serviceWorker' in navigator) {"
sw_reload_listener = """  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!HAD_SW_CONTROLLER_AT_BOOT || state.navigationInProgress) return;
      try {
        if (sessionStorage.getItem(SW_UPDATE_RELOAD_KEY) === '1') return;
        sessionStorage.setItem(SW_UPDATE_RELOAD_KEY, '1');
      } catch (_) {
        if (state.swUpdateReloaded) return;
        state.swUpdateReloaded = true;
      }
      location.reload();
    });
  }

  if ('serviceWorker' in navigator) {"""
if "navigator.serviceWorker.addEventListener('controllerchange'" not in install_text:
    if sw_reload_marker not in install_text:
        raise SystemExit('service-worker registration marker missing')
    install_text = install_text.replace(sw_reload_marker, sw_reload_listener, 1)

install_text = re.sub(r"serviceWorker\.register\('\./sw\.js\?v=2\.2\.6-install\d+'", "serviceWorker.register('./sw.js?v=2.2.6-install14'", install_text, count=1)
install_gate.write_text(install_text, encoding='utf-8')

manifest_path = Path('dist/manifest.webmanifest')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['launch_handler'] = {'client_mode': ['navigate-existing', 'auto']}
self_related_app = {
    'platform': 'webapp',
    'url': './manifest.webmanifest',
}
if manifest.get('id'):
    self_related_app['id'] = manifest['id']
related_apps = [
    app for app in manifest.get('related_applications', [])
    if not (app.get('platform') == 'webapp' and app.get('url') in ('./manifest.webmanifest', 'manifest.webmanifest'))
]
manifest['related_applications'] = [self_related_app, *related_apps]
manifest['prefer_related_applications'] = False
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

sw = Path('dist/sw.js')
if sw.exists():
    text = sw.read_text(encoding='utf-8')
    text = re.sub(r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';", "const CACHE = 'snake-2.0-v2.2.6-head-sweep-slow-20260812-v11';", text, count=1)
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
    new_respond = r"""const isInstallGate = /\/install-gate-v225\.js$/i.test(url.pathname);
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

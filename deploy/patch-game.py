from pathlib import Path
import re

game = Path('dist/game.js')
js = game.read_text(encoding='utf-8')

# Public stats: count only a successfully completed level.
js = js.replace("    save.gamesPlayed++;\n    window.snake2TrackGameStart?.();", "    save.gamesPlayed++;")
needle = "    state.levelComplete = true; state.running = false;\n    recordMissionOutcome(true, snapshot);"
hook = "    state.levelComplete = true; state.running = false;\n    window.snake2TrackGameStart?.();\n    recordMissionOutcome(true, snapshot);"
if 'state.levelComplete = true; state.running = false;\n    window.snake2TrackGameStart?.();' not in js:
    if needle not in js:
        raise SystemExit('completeLevel hook point missing')
    js = js.replace(needle, hook, 1)

# Fixed-timestep catch-up: gameplay speed stays stable when rendering FPS drops.
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

# Keep the continuous body, but reduce expensive warped-sprite density on long snakes.
old_stride = "const detailStride = points.length > 120 ? 3 : points.length > 58 ? 2 : 1;"
if old_stride not in js:
    raise SystemExit('body detail stride point missing')
js = js.replace(old_stride, "const detailStride = points.length > 72 ? 4 : points.length > 36 ? 3 : points.length > 18 ? 2 : 1;", 1)

# Avoid allocating the same body gradient on every animation frame.
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
html = re.sub(r'install-gate-v225\.js\?v=[^"]+', 'install-gate-v225.js?v=2.2.6-install1', html)
scripts = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2" defer></script>\n  <script src="./snake2-stats.js?v=20260812h" defer></script>'
pos = html.lower().rfind('</body>')
html = html[:pos] + '  ' + scripts + '\n' + html[pos:] if pos >= 0 else html + '\n' + scripts
index.write_text(html, encoding='utf-8')

sw = Path('dist/sw.js')
if sw.exists():
    text = sw.read_text(encoding='utf-8')
    text = re.sub(r"const CACHE = 'snake-2\.0-v2\.2\.5[^']*';", "const CACHE = 'snake-2.0-v2.2.6-install-fix-20260812';", text, count=1)
    if "'./snake2-stats.js'" not in text:
        text = text.replace("const CORE_ASSETS = [", "const CORE_ASSETS = [\n  './snake2-stats.js',")
    sw.write_text(text, encoding='utf-8')

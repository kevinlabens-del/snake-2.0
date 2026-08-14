from pathlib import Path
import re


game_path = Path('dist/game.js')
game = game_path.read_text(encoding='utf-8')

draw_contain_marker = """  function drawImageContain(img, x, y, w, h) {
    if (!img) return;
    const iw = img.naturalWidth || img.width || w;
    const ih = img.naturalHeight || img.height || h;
    const scale = Math.min(w / iw, h / ih);
    const dw = iw * scale;
    const dh = ih * scale;
    const dx = x + (w - dw) / 2;
    const dy = y + (h - dh) / 2;
    ctx.drawImage(img, dx, dy, dw, dh);
  }
"""
draw_cropped_helper = draw_contain_marker + """

  function drawImageContainCropped(img, x, y, w, h, cropRatio = .0625) {
    if (!img) return;
    const iw = img.naturalWidth || img.width || w;
    const ih = img.naturalHeight || img.height || h;
    const cropX = iw * cropRatio;
    const cropY = ih * cropRatio;
    const sourceW = Math.max(1, iw - cropX * 2);
    const sourceH = Math.max(1, ih - cropY * 2);
    const scale = Math.min(w / sourceW, h / sourceH);
    const dw = sourceW * scale;
    const dh = sourceH * scale;
    const dx = x + (w - dw) / 2;
    const dy = y + (h - dh) / 2;
    ctx.drawImage(img, cropX, cropY, sourceW, sourceH, dx, dy, dw, dh);
  }
"""
if 'function drawImageContainCropped(' not in game:
    if draw_contain_marker not in game:
        raise SystemExit('image contain helper missing')
    game = game.replace(draw_contain_marker, draw_cropped_helper, 1)

old_hazard_wave = """          const sprite = assets.danger02 || assets.trap02; const px = x * cell + 3, py = wave.row * cell + 3;
          if (sprite) drawImageContain(sprite, px, py, cell - 6, cell - 6); else { ctx.fillStyle='rgba(255,73,91,.62)'; ctx.fillRect(px,py,cell-6,cell-6); }"""
new_hazard_wave = """          const sprite = assets.danger02 || assets.trap02;
          const hazardVisualSize = cell * 1.20;
          const px = x * cell + (cell - hazardVisualSize) / 2;
          const py = wave.row * cell + (cell - hazardVisualSize) / 2;
          if (sprite) drawImageContainCropped(sprite, px, py, hazardVisualSize, hazardVisualSize);
          else { ctx.fillStyle='rgba(255,73,91,.62)'; ctx.fillRect(px, py, hazardVisualSize, hazardVisualSize); }"""
if old_hazard_wave not in game:
    raise SystemExit('hazard-wave visual block missing')
game = game.replace(old_hazard_wave, new_hazard_wave, 1)

old_obstacles = """    for (const o of state.obstacles) {
      const x = o.x * cell + 2, y = o.y * cell + 2;
      const spriteKey = o.visualKey || obstacleVisualFor(settings, { moving: !!o.moving, dynamicWall: !!o.dynamicWall, collapsedTile: !!o.collapsedTile, index: o.x + o.y * cells });
      const sprite = assets[spriteKey];
      ctx.save();
      if (sprite) {
        ctx.shadowBlur = o.moving ? 10 : 6;
        ctx.shadowColor = o.moving ? 'rgba(255,76,94,.38)' : 'rgba(0,0,0,.24)';
        drawImageContain(sprite, x, y, cell - 4, cell - 4);
        if (o.moving) {
          ctx.shadowBlur = 0;
          ctx.strokeStyle = 'rgba(255,91,108,.42)';
          ctx.lineWidth = 1;
          roundRect(x + 1, y + 1, cell - 6, cell - 6, 5);
          ctx.stroke();
        }
      } else {
        const g = ctx.createLinearGradient(x, y, x + cell - 4, y + cell - 4);
        g.addColorStop(0, o.moving ? '#56333a' : '#30383d');
        g.addColorStop(1, '#101416');
        ctx.fillStyle = g;
        ctx.strokeStyle = o.moving ? 'rgba(255,91,108,.55)' : 'rgba(131,255,87,.24)';
        ctx.lineWidth = 1.2;
        roundRect(x, y, cell - 4, cell - 4, 5); ctx.fill(); ctx.stroke();
      }
      ctx.restore();
    }"""
new_obstacles = """    for (const o of state.obstacles) {
      const obstacleVisualSize = cell * 1.40;
      const x = o.x * cell + (cell - obstacleVisualSize) / 2;
      const y = o.y * cell + (cell - obstacleVisualSize) / 2;
      const spriteKey = o.visualKey || obstacleVisualFor(settings, { moving: !!o.moving, dynamicWall: !!o.dynamicWall, collapsedTile: !!o.collapsedTile, index: o.x + o.y * cells });
      const sprite = assets[spriteKey];
      ctx.save();
      if (sprite) {
        ctx.shadowBlur = o.moving ? 16 : 11;
        ctx.shadowColor = o.moving ? 'rgba(255,76,94,.62)' : 'rgba(0,0,0,.62)';
        drawImageContainCropped(sprite, x, y, obstacleVisualSize, obstacleVisualSize);
        if (o.moving) {
          ctx.shadowBlur = 0;
          ctx.strokeStyle = 'rgba(255,91,108,.42)';
          ctx.lineWidth = 1;
          roundRect(x + 1, y + 1, obstacleVisualSize - 2, obstacleVisualSize - 2, 5);
          ctx.stroke();
        }
      } else {
        const g = ctx.createLinearGradient(x, y, x + obstacleVisualSize, y + obstacleVisualSize);
        g.addColorStop(0, o.moving ? '#56333a' : '#30383d');
        g.addColorStop(1, '#101416');
        ctx.fillStyle = g;
        ctx.strokeStyle = o.moving ? 'rgba(255,91,108,.55)' : 'rgba(131,255,87,.24)';
        ctx.lineWidth = 1.2;
        roundRect(x, y, obstacleVisualSize, obstacleVisualSize, 5); ctx.fill(); ctx.stroke();
      }
      ctx.restore();
    }"""
if old_obstacles not in game:
    raise SystemExit('obstacle visual block missing')
game = game.replace(old_obstacles, new_obstacles, 1)

old_locked_portal = """    if (state.lockedPortal) {
      const x = state.lockedPortal.x * cell + 1, y = state.lockedPortal.y * cell + 1;
      const sprite = assets.portalLocked;
      ctx.save(); ctx.globalAlpha = .72 + Math.sin(time * .004) * .10;
      if (sprite) drawImageContain(sprite, x, y, cell - 2, cell - 2);
      else { ctx.strokeStyle='rgba(170,185,175,.7)'; ctx.lineWidth=3; ctx.beginPath(); ctx.arc(x+cell/2,y+cell/2,cell*.35,0,Math.PI*2); ctx.stroke(); }
      ctx.restore();
    }"""
new_locked_portal = """    if (state.lockedPortal) {
      const lockedPortalVisualSize = cell * 1.50;
      const x = state.lockedPortal.x * cell + (cell - lockedPortalVisualSize) / 2;
      const y = state.lockedPortal.y * cell + (cell - lockedPortalVisualSize) / 2;
      const sprite = assets.portalLocked;
      ctx.save(); ctx.globalAlpha = .72 + Math.sin(time * .004) * .10;
      if (sprite) {
        ctx.shadowBlur = 16; ctx.shadowColor = 'rgba(255,205,76,.58)';
        drawImageContainCropped(sprite, x, y, lockedPortalVisualSize, lockedPortalVisualSize);
      } else {
        const cx = state.lockedPortal.x * cell + cell / 2;
        const cy = state.lockedPortal.y * cell + cell / 2;
        ctx.strokeStyle='rgba(170,185,175,.7)'; ctx.lineWidth=3; ctx.beginPath(); ctx.arc(cx,cy,cell*.43,0,Math.PI*2); ctx.stroke();
      }
      ctx.restore();
    }"""
if old_locked_portal not in game:
    raise SystemExit('locked-portal visual block missing')
game = game.replace(old_locked_portal, new_locked_portal, 1)

old_portal_loop = """    for (const portal of portalsToDraw) {
      const x = portal.x * cell + 1, y = portal.y * cell + 1;
      const pulse = 1 + Math.sin(time * .008 + portal.x) * .08;
      const spriteKey = portal.correct === false ? 'portalFake' : 'portalExit';
      const sprite = assets[spriteKey];
      ctx.save();
      ctx.globalAlpha = portal.correct === false ? .86 : 1;
      if (sprite) {
        const pad = Math.max(0, (cell - 6) * (1 - pulse) * .5);
        drawImageContain(sprite, x + pad, y + pad, cell - 2 - pad * 2, cell - 2 - pad * 2);
      } else {
        const cx = portal.x * cell + cell / 2, cy = portal.y * cell + cell / 2;
        const hue = {green:110,blue:215,red:350,purple:285,gold:45}[portal.color] ?? 110;
        ctx.translate(cx, cy); ctx.scale(pulse, pulse);
        ctx.shadowBlur = 18; ctx.shadowColor = `hsla(${hue},95%,60%,.75)`;
        ctx.strokeStyle = `hsla(${hue},90%,65%,.92)`;
        ctx.lineWidth = 4;
        ctx.beginPath(); ctx.arc(0, 0, cell * .38, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = `hsla(${hue},90%,80%,.45)`; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(0, 0, cell * .25, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.restore();
    }"""
new_portal_loop = """    for (const portal of portalsToDraw) {
      const pulse = 1 + Math.sin(time * .008 + portal.x) * .08;
      const portalVisualSize = cell * 1.62 * pulse;
      const cx = portal.x * cell + cell / 2;
      const cy = portal.y * cell + cell / 2;
      const x = cx - portalVisualSize / 2;
      const y = cy - portalVisualSize / 2;
      const spriteKey = portal.correct === false ? 'portalFake' : 'portalExit';
      const sprite = assets[spriteKey];
      ctx.save();
      ctx.globalAlpha = portal.correct === false ? .86 : 1;
      if (sprite) {
        ctx.shadowBlur = portal.correct === false ? 18 : 22;
        ctx.shadowColor = portal.correct === false ? 'rgba(255,105,39,.74)' : 'rgba(53,209,255,.82)';
        drawImageContainCropped(sprite, x, y, portalVisualSize, portalVisualSize);
      } else {
        const hue = {green:110,blue:215,red:350,purple:285,gold:45}[portal.color] ?? 110;
        ctx.translate(cx, cy); ctx.scale(pulse, pulse);
        ctx.shadowBlur = 18; ctx.shadowColor = `hsla(${hue},95%,60%,.75)`;
        ctx.strokeStyle = `hsla(${hue},90%,65%,.92)`;
        ctx.lineWidth = 4;
        ctx.beginPath(); ctx.arc(0, 0, cell * .45, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = `hsla(${hue},90%,80%,.45)`; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(0, 0, cell * .30, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.restore();
    }"""
if old_portal_loop not in game:
    raise SystemExit('active-portal visual block missing')
game = game.replace(old_portal_loop, new_portal_loop, 1)
game_path.write_text(game, encoding='utf-8')


index_path = Path('dist/index.html')
index = index_path.read_text(encoding='utf-8')
index = re.sub(r'game\.js\?v=[^"\']+', 'game.js?v=2.2.5-visual-size2', index)
index_path.write_text(index, encoding='utf-8')


sw_path = Path('dist/sw.js')
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';",
    "const CACHE = 'snake-2.0-v2.2.6-larger-obstacles-portals-20260814-v17';",
    sw,
    count=1,
)

old_runtime_route = r"""  const isInstallGate = /\/install-gate-v225\.js$/i.test(url.pathname);
  event.respondWith(
    request.mode === 'navigate'
      ? navigationFastStart(request)
      : (isAudio ? audioResponse(request) : (isInstallGate ? networkFirstCritical(request) : staleWhileRevalidate(request)))
  );"""
new_runtime_route = r"""  const isCriticalRuntime = /\/(?:install-gate-v225|game|apple-snake-levels)\.js$/i.test(url.pathname);
  event.respondWith(
    request.mode === 'navigate'
      ? navigationFastStart(request)
      : (isAudio ? audioResponse(request) : (isCriticalRuntime ? networkFirstCritical(request) : staleWhileRevalidate(request)))
  );"""
if old_runtime_route in sw:
    sw = sw.replace(old_runtime_route, new_runtime_route, 1)
elif 'isCriticalRuntime' not in sw:
    raise SystemExit('service-worker runtime route missing')
sw_path.write_text(sw, encoding='utf-8')

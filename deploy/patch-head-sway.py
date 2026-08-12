from pathlib import Path
import re

path = Path('dist/game.js')
text = path.read_text(encoding='utf-8')

# Head animation is strictly visual. Logical coordinates, hitbox, collisions,
# movement speed and body path are never modified by this patch.
old_static = """    const headAngle = visualBodyAngle(0, points);\n    const renderedHead = drawImageRotated(\n      headImg, head.x, head.y, headAngle,"""

old_sway_v1 = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Mouvement visuel réaliste de la tête : oscillation rapide gauche/droite\n    // perpendiculaire à la direction du cou. La hitbox et les collisions ne bougent pas.\n    const headSwayPhase = time * 0.0185; // ~3 oscillations complètes par seconde\n    const headSway = Math.sin(headSwayPhase);\n    const headSwayPx = cell * 0.16 * scale * headSway;\n    const headAngle = baseHeadAngle + headSway * 0.16;\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const visualHeadX = head.x + swayNormalX * headSwayPx;\n    const visualHeadY = head.y + swayNormalY * headSwayPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

old_sway_v2 = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Oscillation visuelle rapide et nette de la tête, indépendante de la hitbox.\n    // 0.022 rad/ms = ~3.5 oscillations/s. L'amplitude est volontairement visible\n    // face à un sprite de tête large de 2.70 cellules.\n    const headSwayPhase = time * 0.022;\n    const headSway = Math.sin(headSwayPhase);\n    const headSwayPx = cell * 0.38 * headSway;\n    const headAngle = baseHeadAngle + headSway * 0.30;\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const visualHeadX = head.x + swayNormalX * headSwayPx;\n    const visualHeadY = head.y + swayNormalY * headSwayPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

old_sweep_fast = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Vrai balayage de tête gauche/droite autour du cou.\n    // Le centre de la tête décrit un petit arc latéral et le museau pivote fortement.\n    // Mouvement purement visuel : la position logique du serpent ne change jamais.\n    const headSweepPhase = time * 0.0265; // ~4.2 balayages complets par seconde\n    const rawHeadSweep = Math.sin(headSweepPhase);\n    const headSweep = rawHeadSweep * (0.88 + 0.12 * Math.cos(headSweepPhase * 2));\n    const headSweepPx = cell * 0.62 * headSweep;\n    const headAngle = baseHeadAngle + headSweep * 0.52; // environ +/-30 degres\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const forwardX = Math.cos(baseHeadAngle);\n    const forwardY = Math.sin(baseHeadAngle);\n    const forwardArcPx = cell * 0.10 * (1 - Math.abs(headSweep));\n    const visualHeadX = head.x + swayNormalX * headSweepPx + forwardX * forwardArcPx;\n    const visualHeadY = head.y + swayNormalY * headSweepPx + forwardY * forwardArcPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

old_sweep_slow_wide = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Balayage réaliste et lent de la tête autour du cou.\n    // Un trajet extrême gauche -> extrême droite dure environ 1,25 seconde\n    // (cycle complet gauche -> droite -> gauche ≈ 2,5 secondes).\n    // Mouvement purement visuel : hitbox, collisions et déplacement logique inchangés.\n    const headSweepPhase = time * 0.0025132741;\n    const rawHeadSweep = Math.sin(headSweepPhase);\n    const headSweep = rawHeadSweep * (0.88 + 0.12 * Math.cos(headSweepPhase * 2));\n    const headSweepPx = cell * 0.62 * headSweep;\n    const headAngle = baseHeadAngle + headSweep * 0.52; // environ +/-30 degres\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const forwardX = Math.cos(baseHeadAngle);\n    const forwardY = Math.sin(baseHeadAngle);\n    const forwardArcPx = cell * 0.10 * (1 - Math.abs(headSweep));\n    const visualHeadX = head.x + swayNormalX * headSweepPx + forwardX * forwardArcPx;\n    const visualHeadY = head.y + swayNormalY * headSweepPx + forwardY * forwardArcPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

new_sweep = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Balayage naturel de la tête autour du cou.\n    // Extrême gauche -> extrême droite ≈ 1,25 s (cycle complet ≈ 2,5 s).\n    // L'amplitude latérale est volontairement contenue pour garder la tête liée au cou.\n    // Animation 100 % visuelle : logique, hitbox, collisions et vitesse inchangées.\n    const headSweepPhase = time * 0.0025132741;\n    const headSweep = Math.sin(headSweepPhase);\n    const headSweepPx = cell * 0.22 * headSweep;\n    const headAngle = baseHeadAngle + headSweep * 0.30; // environ +/-17 degres\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const visualHeadX = head.x + swayNormalX * headSweepPx;\n    const visualHeadY = head.y + swayNormalY * headSweepPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

if old_sweep_slow_wide in text:
    text = text.replace(old_sweep_slow_wide, new_sweep, 1)
elif old_sweep_fast in text:
    text = text.replace(old_sweep_fast, new_sweep, 1)
elif old_sway_v2 in text:
    text = text.replace(old_sway_v2, new_sweep, 1)
elif old_sway_v1 in text:
    text = text.replace(old_sway_v1, new_sweep, 1)
elif old_static in text:
    text = text.replace(old_static, new_sweep, 1)
elif 'const headSweepPx = cell * 0.22 * headSweep;' not in text:
    raise SystemExit('Snake head render anchor not found')

# Keep the procedural fallback head aligned with the same visual head position.
text = text.replace('      ctx.translate(head.x, head.y);', '      ctx.translate(visualHeadX, visualHeadY);', 1)

# Preserve body-render performance protections.
old_stride = "const detailStride = points.length > 72 ? 4 : points.length > 36 ? 3 : points.length > 18 ? 2 : 1;"
new_stride = "const detailStride = Math.max(1, Math.ceil(Math.max(1, points.length - 2) / 13));"
if old_stride in text:
    text = text.replace(old_stride, new_stride, 1)

old_highlight = """    ctx.strokeStyle = 'rgba(255,255,255,.09)';\n    ctx.lineWidth = Math.max(1, width * .07);\n    ctx.stroke(path);"""
new_highlight = """    if (points.length <= 48) {\n      ctx.strokeStyle = 'rgba(255,255,255,.09)';\n      ctx.lineWidth = Math.max(1, width * .07);\n      ctx.stroke(path);\n    }"""
if old_highlight in text:
    text = text.replace(old_highlight, new_highlight, 1)

path.write_text(text, encoding='utf-8')

# Bust the game asset cache so installed versions receive the corrected animation immediately.
index = Path('dist/index.html')
html = index.read_text(encoding='utf-8')
html = re.sub(r'game\.js\?v=2\.2\.5(?:-headsweep\d+)?', 'game.js?v=2.2.5-headsweep3', html)
index.write_text(html, encoding='utf-8')

sw = Path('dist/sw.js')
if sw.exists():
    sw_text = sw.read_text(encoding='utf-8')
    sw_text = re.sub(
        r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';",
        "const CACHE = 'snake-2.0-v2.2.6-head-sweep-natural-20260813-v12';",
        sw_text,
        count=1,
    )
    sw.write_text(sw_text, encoding='utf-8')

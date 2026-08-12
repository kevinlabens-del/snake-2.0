from pathlib import Path

path = Path('dist/game.js')
text = path.read_text(encoding='utf-8')

# Replace the previous subtle sway (or the original static head) with a clearly
# visible but purely visual serpentine head motion. Logical coordinates/hitbox stay unchanged.
old_static = """    const headAngle = visualBodyAngle(0, points);\n    const renderedHead = drawImageRotated(\n      headImg, head.x, head.y, headAngle,"""
old_sway = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Mouvement visuel réaliste de la tête : oscillation rapide gauche/droite\n    // perpendiculaire à la direction du cou. La hitbox et les collisions ne bougent pas.\n    const headSwayPhase = time * 0.0185; // ~3 oscillations complètes par seconde\n    const headSway = Math.sin(headSwayPhase);\n    const headSwayPx = cell * 0.16 * scale * headSway;\n    const headAngle = baseHeadAngle + headSway * 0.16;\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const visualHeadX = head.x + swayNormalX * headSwayPx;\n    const visualHeadY = head.y + swayNormalY * headSwayPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""
new_sway = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Oscillation visuelle rapide et nette de la tête, indépendante de la hitbox.\n    // 0.022 rad/ms = ~3.5 oscillations/s. L'amplitude est volontairement visible\n    // face à un sprite de tête large de 2.70 cellules.\n    const headSwayPhase = time * 0.022;\n    const headSway = Math.sin(headSwayPhase);\n    const headSwayPx = cell * 0.38 * headSway;\n    const headAngle = baseHeadAngle + headSway * 0.30;\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const visualHeadX = head.x + swayNormalX * headSwayPx;\n    const visualHeadY = head.y + swayNormalY * headSwayPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

if old_sway in text:
    text = text.replace(old_sway, new_sway, 1)
elif old_static in text:
    text = text.replace(old_static, new_sway, 1)
elif 'const headSwayPx = cell * 0.38 * headSway;' not in text:
    raise SystemExit('Snake head render anchor not found')

# Keep the procedural fallback head on the same visual coordinates.
text = text.replace('      ctx.translate(head.x, head.y);', '      ctx.translate(visualHeadX, visualHeadY);', 1)

# Rendering performance: the continuous spine already guarantees a complete body.
# Decorative warped sprites are now capped to roughly 12-14 draws per frame instead
# of growing linearly with snake length. This prevents progressive FPS loss as apples
# increase the snake length while preserving every logical segment and collision.
old_stride = "const detailStride = points.length > 72 ? 4 : points.length > 36 ? 3 : points.length > 18 ? 2 : 1;"
new_stride = "const detailStride = Math.max(1, Math.ceil(Math.max(1, points.length - 2) / 13));"
if old_stride in text:
    text = text.replace(old_stride, new_stride, 1)
elif new_stride not in text:
    raise SystemExit('body detail stride anchor not found')

# Reduce expensive multi-stroke spine work for very long snakes. The visible shape
# remains identical; only the subtle highlight pass is skipped past 48 points.
old_highlight = """    ctx.strokeStyle = 'rgba(255,255,255,.09)';\n    ctx.lineWidth = Math.max(1, width * .07);\n    ctx.stroke(path);"""
new_highlight = """    if (points.length <= 48) {\n      ctx.strokeStyle = 'rgba(255,255,255,.09)';\n      ctx.lineWidth = Math.max(1, width * .07);\n      ctx.stroke(path);\n    }"""
if old_highlight in text:
    text = text.replace(old_highlight, new_highlight, 1)

path.write_text(text, encoding='utf-8')

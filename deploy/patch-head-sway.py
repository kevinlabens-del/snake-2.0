from pathlib import Path

path = Path('dist/game.js')
text = path.read_text(encoding='utf-8')

old = """    const headAngle = visualBodyAngle(0, points);\n    const renderedHead = drawImageRotated(\n      headImg, head.x, head.y, headAngle,"""
new = """    const baseHeadAngle = visualBodyAngle(0, points);\n    // Mouvement visuel réaliste de la tête : oscillation rapide gauche/droite\n    // perpendiculaire à la direction du cou. La hitbox et les collisions ne bougent pas.\n    const headSwayPhase = time * 0.0185; // ~3 oscillations complètes par seconde\n    const headSway = Math.sin(headSwayPhase);\n    const headSwayPx = cell * 0.16 * scale * headSway;\n    const headAngle = baseHeadAngle + headSway * 0.16;\n    const swayNormalX = -Math.sin(baseHeadAngle);\n    const swayNormalY = Math.cos(baseHeadAngle);\n    const visualHeadX = head.x + swayNormalX * headSwayPx;\n    const visualHeadY = head.y + swayNormalY * headSwayPx;\n    const renderedHead = drawImageRotated(\n      headImg, visualHeadX, visualHeadY, headAngle,"""

if old not in text:
    if 'const headSwayPhase = time * 0.0185;' in text:
        raise SystemExit(0)
    raise SystemExit('Snake head render anchor not found')

text = text.replace(old, new, 1)
text = text.replace('      ctx.translate(head.x, head.y);', '      ctx.translate(visualHeadX, visualHeadY);', 1)
path.write_text(text, encoding='utf-8')

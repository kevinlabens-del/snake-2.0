from pathlib import Path
import re


game_path = Path('dist/game.js')
game = game_path.read_text(encoding='utf-8')

# The mission preview is rendered through innerHTML because the existing modal
# supports rich reward markup. Escape every mission string before inserting it.
modal_marker = """  function modal(title, body, actions) {
"""
escape_helper = """  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>\"']/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#039;'
    })[character]);
  }

  function modal(title, body, actions) {
"""
if 'function escapeHtml(value)' not in game:
    if modal_marker not in game:
        raise SystemExit('modal helper anchor missing')
    game = game.replace(modal_marker, escape_helper, 1)

old_campaign_completion = """    modal(`Niveau ${state.level} terminé`, `<p><b>${mission?.title || 'Mission validée'}</b><br>${mission?.description || ''}<br><br>Score : <b>${state.score}</b> · Intensité : <b>${diff}/10</b></p>${rewardHtml}`, [
      ['Menu', () => { closeModal(); showScreen('home'); }],
      ['Niveau suivant', () => { closeModal(); launchLevel(state.level + 1, false); }]
    ]);
"""
new_campaign_completion = """    const nextLevel = state.level + 1;
    const nextMission = Levels?.getMission?.(nextLevel, playerProfile(), { adaptive: true, seed: nextLevel }) || null;
    const nextDifficulty = Math.max(1, Math.min(10, Number(nextMission?.difficulty) || 1));
    const nextObjectiveLabels = Array.isArray(nextMission?.objectives)
      ? nextMission.objectives.map(objective => objective?.label).filter(Boolean)
      : [];
    const nextObjectivesHtml = nextObjectiveLabels.length
      ? `<div class=\"next-mission-objectives\"><small>OBJECTIFS</small><ul>${nextObjectiveLabels.map(label => `<li>${escapeHtml(label)}</li>`).join('')}</ul></div>`
      : '';
    const nextMissionHtml = `
      <div class=\"level-complete-summary\">
        <strong>✓ Niveau ${state.level} réussi</strong>
        <span>Score : ${state.score}</span>
      </div>
      <section class=\"next-mission-preview\" aria-label=\"Mission du niveau ${nextLevel}\">
        <div class=\"next-mission-preview-head\">
          <small>PROCHAINE MISSION</small>
          <b>NIVEAU ${nextLevel}</b>
        </div>
        <h4>${escapeHtml(nextMission?.title || `Mission ${nextLevel}`)}</h4>
        <p>${escapeHtml(nextMission?.description || nextMission?.primaryObjective || 'Découvre la prochaine mission.')}</p>
        ${nextObjectivesHtml}
        <div class=\"next-mission-intensity\"><span>Intensité de la mission</span><strong>${nextDifficulty}/10</strong></div>
      </section>`;
    modal(`Niveau ${state.level} terminé`, `${nextMissionHtml}${rewardHtml}`, [
      ['Menu', () => { closeModal(); showScreen('home'); }],
      ['JOUER', () => { closeModal(); launchLevel(nextLevel, false); }]
    ]);
"""
if old_campaign_completion not in game:
    raise SystemExit('campaign completion modal anchor missing')
game = game.replace(old_campaign_completion, new_campaign_completion, 1)
game_path.write_text(game, encoding='utf-8')


# Give the next mission enough hierarchy to be understood at a glance on mobile.
styles_path = Path('dist/styles-v225.css')
styles = styles_path.read_text(encoding='utf-8')
next_mission_styles = """

.level-complete-summary{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:2px 0 12px;padding:10px 12px;border-radius:14px;background:rgba(125,255,49,.07);border:1px solid rgba(125,255,49,.13)}
.level-complete-summary strong{color:#cfffaa;font-size:13px}.level-complete-summary span{color:#91a88d;font-size:12px;font-weight:700}
.next-mission-preview{position:relative;overflow:hidden;margin:0;padding:16px;border-radius:20px;background:radial-gradient(circle at 100% 0,rgba(125,255,49,.13),transparent 44%),linear-gradient(145deg,rgba(17,31,20,.98),rgba(5,9,7,.98));border:1px solid rgba(125,255,49,.28);box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 14px 30px rgba(0,0,0,.25)}
.next-mission-preview-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}.next-mission-preview-head small{color:#8dff4c;font-size:10px;font-weight:900;letter-spacing:.14em}.next-mission-preview-head b{padding:5px 8px;border-radius:9px;background:#8dff4c;color:#071006;font-size:10px;letter-spacing:.08em}
.next-mission-preview h4{margin:0 0 6px;color:#f2ffec;font-size:19px;line-height:1.2}.next-mission-preview p{margin:0;color:#b4c8af;font-size:13px;line-height:1.5}
.next-mission-objectives{margin-top:13px;padding-top:11px;border-top:1px solid rgba(125,255,49,.12)}.next-mission-objectives small{color:#7f947c;font-size:9px;font-weight:900;letter-spacing:.12em}.next-mission-objectives ul{display:grid;gap:6px;margin:7px 0 0;padding:0;list-style:none}.next-mission-objectives li{position:relative;padding-left:17px;color:#d9efd3;font-size:12px;line-height:1.35}.next-mission-objectives li::before{content:'›';position:absolute;left:2px;top:-1px;color:#8dff4c;font-size:16px;font-weight:900}
.next-mission-intensity{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:13px;padding-top:11px;border-top:1px solid rgba(125,255,49,.12);color:#8fa58b;font-size:11px}.next-mission-intensity strong{color:#dfffcb;font-size:12px}
"""
if '.next-mission-preview{' not in styles:
    styles += next_mission_styles
styles_path.write_text(styles, encoding='utf-8')


# Bust every relevant cache so installed copies receive the new transition screen.
index_path = Path('dist/index.html')
index = index_path.read_text(encoding='utf-8')
index = re.sub(r'styles-v225\.css\?v=[^"\']+', 'styles-v225.css?v=2.2.7-nextmission1', index)
index = re.sub(r'install-gate-v225\.js\?v=[^"\']+', 'install-gate-v225.js?v=2.2.7-nextmission1', index)
index = re.sub(r'game\.js\?v=[^"\']+', 'game.js?v=2.2.7-nextmission1', index)
index_path.write_text(index, encoding='utf-8')

install_gate_path = Path('dist/install-gate-v225.js')
install_gate = install_gate_path.read_text(encoding='utf-8')
install_gate = re.sub(
    r"const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_[^']+';",
    "const SW_UPDATE_RELOAD_KEY = 'snake2_sw_update_next_mission_v18';",
    install_gate,
    count=1,
)
install_gate = re.sub(
    r"serviceWorker\.register\('\./sw\.js\?v=[^']+'",
    "serviceWorker.register('./sw.js?v=2.2.7-nextmission1'",
    install_gate,
    count=1,
)
install_gate_path.write_text(install_gate, encoding='utf-8')

sw_path = Path('dist/sw.js')
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE = 'snake-2\.0-v2\.2\.[^']*';",
    "const CACHE = 'snake-2.0-v2.2.7-next-mission-preview-20260814-v18';",
    sw,
    count=1,
)
sw_path.write_text(sw, encoding='utf-8')

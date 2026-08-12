(() => {
  'use strict';

  const SUPABASE_URL = 'https://kokmqcqlpkruoewhewcb.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_E1RKbaZU7DkVoiyJmFWvqQ_hKBcBG9h';
  const VISITOR_KEY = 'snake2_visitor_id_v1';
  const SESSION_KEY = 'snake2_session_id_v1';
  const FALLBACK_MS = 10000;

  const uuid = () => globalThis.crypto?.randomUUID
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 3 | 8);
        return v.toString(16);
      });

  const getStoredId = (key, session = false) => {
    const store = session ? sessionStorage : localStorage;
    let id = store.getItem(key);
    if (!id) {
      id = uuid();
      store.setItem(key, id);
    }
    return id;
  };

  const visitorId = getStoredId(VISITOR_KEY, false);
  const sessionId = getStoredId(SESSION_KEY, true);
  let realtimeChannel = null;
  let realtimeReady = false;
  let fallbackBusy = false;

  async function rpc(name, body = {}, keepalive = false) {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body),
      cache: 'no-store',
      keepalive
    });
    if (!response.ok) throw new Error(`stats ${name}: ${response.status}`);
    return response.json();
  }

  function ensurePanel() {
    let panel = document.getElementById('snake2-live-stats');
    if (panel) return panel;

    const style = document.createElement('style');
    style.textContent = `
      #snake2-live-stats{position:relative;z-index:35;display:flex;gap:5px;flex-wrap:nowrap;justify-content:center;align-items:center;width:max-content;max-width:94%;margin:-2px auto 2px;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;pointer-events:none;filter:drop-shadow(0 2px 8px rgba(0,0,0,.55))}
      #snake2-live-stats .s2stat{display:inline-flex;align-items:center;gap:4px;min-height:27px;padding:4px 8px;border:1px solid rgba(94,255,126,.5);border-radius:999px;background:rgba(3,10,7,.86);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);color:#effff2;font-size:10px;font-weight:800;letter-spacing:.1px;line-height:1;white-space:nowrap;box-shadow:0 0 10px rgba(80,255,120,.1)}
      #snake2-live-stats .s2num{color:#79ff98;font-variant-numeric:tabular-nums;font-weight:950}
      #snake2-live-stats .online-dot{width:7px;height:7px;border-radius:50%;background:#48ff74;box-shadow:0 0 8px #48ff74}
      @media(max-width:460px){#snake2-live-stats{gap:3px;margin:-1px auto 3px;max-width:96%}#snake2-live-stats .s2stat{font-size:9.5px;padding:4px 6px;min-height:26px}}
    `;
    document.head.appendChild(style);

    panel = document.createElement('div');
    panel.id = 'snake2-live-stats';
    panel.setAttribute('aria-label', 'Statistiques Snake 2.0');
    panel.innerHTML = '<span class="s2stat">👥 <span class="s2num" data-s2="visitors">—</span> visiteurs</span><span class="s2stat">🎮 <span class="s2num" data-s2="games">—</span> parties</span><span class="s2stat"><span class="online-dot"></span><span class="s2num" data-s2="online">—</span> en ligne</span>';

    const volume = document.getElementById('quickVolume');
    if (volume && volume.parentNode) volume.parentNode.insertBefore(panel, volume);
    else document.body.appendChild(panel);
    return panel;
  }

  function setNumber(key, value) {
    const node = document.querySelector(`[data-s2="${key}"]`);
    const number = Number(value);
    if (node && Number.isFinite(number)) node.textContent = number.toLocaleString('fr-FR');
  }

  function renderTotals(data) {
    if (!data || typeof data !== 'object') return;
    ensurePanel();
    setNumber('visitors', data.visitors ?? data.total_visitors);
    setNumber('games', data.games ?? data.total_games);
    if (!realtimeReady && data.online != null) setNumber('online', data.online);
  }

  function renderPresence() {
    if (!realtimeChannel) return;
    const state = realtimeChannel.presenceState();
    const uniqueVisitors = Object.keys(state || {}).length;
    setNumber('online', uniqueVisitors);
  }

  async function fallbackRefresh() {
    if (fallbackBusy || document.visibilityState === 'hidden' || !navigator.onLine) return;
    fallbackBusy = true;
    try {
      const data = await rpc('snake2_heartbeat', {
        p_session_id: sessionId,
        p_visitor_id: visitorId
      });
      renderTotals(data);
    } catch (error) {
      console.debug('[Snake2 stats fallback]', error.message);
    } finally {
      fallbackBusy = false;
    }
  }

  let lastCompletedAt = 0;
  async function trackCompletedLevel() {
    const now = Date.now();
    if (now - lastCompletedAt < 1500) return;
    lastCompletedAt = now;
    try {
      renderTotals(await rpc('snake2_game_started'));
    } catch (error) {
      console.debug('[Snake2 stats level]', error.message);
    }
  }
  window.snake2TrackGameStart = trackCompletedLevel;

  async function startRealtime() {
    if (!window.supabase?.createClient) {
      console.debug('[Snake2 stats] Supabase Realtime library unavailable; fallback active');
      return;
    }

    const client = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      realtime: { params: { eventsPerSecond: 20 } }
    });

    realtimeChannel = client.channel('snake2-live-players', {
      config: { presence: { key: visitorId } }
    });

    realtimeChannel
      .on('presence', { event: 'sync' }, renderPresence)
      .on('presence', { event: 'join' }, renderPresence)
      .on('presence', { event: 'leave' }, renderPresence)
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'snake2_stats',
        filter: 'id=eq.1'
      }, payload => {
        renderTotals(payload.new || {});
      })
      .subscribe(async status => {
        if (status === 'SUBSCRIBED') {
          realtimeReady = true;
          await realtimeChannel.track({ visitor_id: visitorId, online_at: new Date().toISOString() });
          renderPresence();
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          realtimeReady = false;
        }
      });

    const leaveRealtime = () => {
      try { realtimeChannel?.untrack(); } catch (_) {}
    };
    window.addEventListener('pagehide', leaveRealtime, { once: true });
  }

  function leaveFallbackPresence() {
    rpc('snake2_leave', {
      p_session_id: sessionId,
      p_visitor_id: visitorId
    }, true).catch(() => {});
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') fallbackRefresh();
  });
  window.addEventListener('online', fallbackRefresh);
  window.addEventListener('pagehide', leaveFallbackPresence);

  async function boot() {
    ensurePanel();
    try {
      renderTotals(await rpc('snake2_register_visitor', { p_visitor_id: visitorId }));
    } catch (error) {
      console.debug('[Snake2 stats visitor]', error.message);
    }
    await fallbackRefresh();
    await startRealtime();
    setInterval(fallbackRefresh, FALLBACK_MS);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
(() => {
  'use strict';

  const SUPABASE_URL = 'https://kokmqcqlpkruoewhewcb.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_E1RKbaZU7DkVoiyJmFWvqQ_hKBcBG9h';
  const VISITOR_KEY = 'snake2_visitor_id_v1';
  const SESSION_KEY = 'snake2_session_id_v1';
  const ACTIVE_RUN_KEY = 'snake2_active_run_v2';
  const PENDING_KEY = 'snake2_pending_completions_v2';
  const HEARTBEAT_MS = 15000;
  const RETRY_MS = 30000;
  const STATS_POLL_MS = 15000;
  const MAX_PENDING = 100;

  const uuid = () => globalThis.crypto?.randomUUID
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, character => {
        const random = Math.random() * 16 | 0;
        const value = character === 'x' ? random : (random & 3 | 8);
        return value.toString(16);
      });

  function safeStore(session = false) {
    try {
      const store = session ? window.sessionStorage : window.localStorage;
      const probe = '__snake2_storage_probe__';
      store.setItem(probe, '1');
      store.removeItem(probe);
      return store;
    } catch (_) {
      return null;
    }
  }

  const localStore = safeStore(false);
  const sessionStore = safeStore(true);

  function readJson(store, key, fallback) {
    if (!store) return fallback;
    try {
      const raw = store.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (_) {
      return fallback;
    }
  }

  function writeJson(store, key, value) {
    if (!store) return;
    try {
      if (value === null) store.removeItem(key);
      else store.setItem(key, JSON.stringify(value));
    } catch (_) {}
  }

  function getStoredId(key, store) {
    if (!store) return uuid();
    try {
      let id = store.getItem(key);
      if (!id) {
        id = uuid();
        store.setItem(key, id);
      }
      return id;
    } catch (_) {
      return uuid();
    }
  }

  const visitorId = getStoredId(VISITOR_KEY, localStore);
  const sessionId = getStoredId(SESSION_KEY, sessionStore);
  let activeRun = readJson(sessionStore, ACTIVE_RUN_KEY, null);
  let playing = false;
  let flushBusy = false;
  let presenceChain = Promise.resolve();
  let pollBusy = false;

  async function rpc(name, body = {}, keepalive = false) {
    const controller = !keepalive && globalThis.AbortController ? new AbortController() : null;
    const timeout = controller ? setTimeout(() => controller.abort(), 10000) : null;
    try {
      const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
        method: 'POST',
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`,
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify(body),
        cache: 'no-store',
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        keepalive: Boolean(keepalive),
        ...(controller ? { signal: controller.signal } : {})
      });
      if (!response.ok) throw new Error(`${name}: ${response.status}`);
      return response.json();
    } finally {
      if (timeout) clearTimeout(timeout);
    }
  }

  function ensurePanel() {
    let panel = document.getElementById('snake2-live-stats');
    if (panel) return panel;

    const style = document.createElement('style');
    style.textContent = `#snake2-live-stats{position:relative;z-index:35;display:flex;gap:5px;flex-wrap:nowrap;justify-content:center;align-items:center;width:max-content;max-width:94%;margin:-2px auto 2px;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;pointer-events:none;filter:drop-shadow(0 2px 8px rgba(0,0,0,.55))}#snake2-live-stats .s2stat{display:inline-flex;align-items:center;gap:4px;min-height:27px;padding:4px 8px;border:1px solid rgba(94,255,126,.5);border-radius:999px;background:rgba(3,10,7,.86);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);color:#effff2;font-size:10px;font-weight:800;line-height:1;white-space:nowrap}#snake2-live-stats .s2num{color:#79ff98;font-variant-numeric:tabular-nums;font-weight:950}#snake2-live-stats .online-dot{width:7px;height:7px;border-radius:50%;background:#48ff74;box-shadow:0 0 8px #48ff74}#snake2-live-stats.stats-unavailable{opacity:.78}#snake2-live-stats.stats-unavailable .online-dot{background:#ff6b6b;box-shadow:0 0 8px #ff6b6b}#snake2-live-stats.stats-unavailable .s2num{color:#ffd0d0}@media(max-width:460px){#snake2-live-stats{gap:3px;margin:-1px auto 3px;max-width:96%}#snake2-live-stats .s2stat{font-size:9.5px;padding:4px 6px;min-height:26px}}`;
    document.head.appendChild(style);

    panel = document.createElement('div');
    panel.id = 'snake2-live-stats';
    panel.setAttribute('aria-label', 'Statistiques Snake 2.0');
    panel.setAttribute('aria-live', 'polite');
    panel.innerHTML = '<span class="s2stat">👥 <span class="s2num" data-s2="visitors">—</span> visiteurs</span><span class="s2stat">🎮 <span class="s2num" data-s2="games">—</span> parties</span><span class="s2stat"><span class="online-dot"></span><span class="s2num" data-s2="online">—</span> en ligne</span>';
    const volume = document.getElementById('quickVolume');
    if (volume?.parentNode) volume.parentNode.insertBefore(panel, volume);
    else document.body.appendChild(panel);
    return panel;
  }

  function setAvailability(available) {
    const panel = ensurePanel();
    panel.classList.toggle('stats-unavailable', !available);
    panel.title = available ? '' : 'Statistiques temporairement indisponibles';
    panel.setAttribute('aria-label', available
      ? 'Statistiques Snake 2.0'
      : 'Statistiques Snake 2.0 temporairement indisponibles');
  }

  function render(data) {
    if (!data || typeof data !== 'object') return;
    const source = data.stats && typeof data.stats === 'object' ? { ...data, ...data.stats } : data;
    const values = {
      visitors: source.visitors ?? source.total_visitors,
      games: source.games ?? source.total_games,
      online: source.online ?? source.total_online
    };
    ensurePanel();
    for (const [key, value] of Object.entries(values)) {
      const target = document.querySelector(`[data-s2="${key}"]`);
      const number = Number(value);
      if (target && Number.isFinite(number)) target.textContent = number.toLocaleString('fr-FR');
    }
    setAvailability(true);
  }

  function runPayload(run) {
    return {
      p_run_id: run.runId,
      p_session_id: sessionId,
      p_visitor_id: visitorId,
      p_level: run.level,
      p_is_daily: run.daily,
      p_client_started_at: run.startedAt
    };
  }

  function createRun(level, daily, startedAt = Date.now()) {
    return {
      runId: uuid(),
      level: Math.max(1, Math.floor(Number(level) || 1)),
      daily: Boolean(daily),
      startedAt: new Date(startedAt).toISOString()
    };
  }

  function loadPending() {
    const value = readJson(localStore, PENDING_KEY, []);
    return Array.isArray(value) ? value.slice(-MAX_PENDING) : [];
  }

  function savePending(queue) {
    writeJson(localStore, PENDING_KEY, queue.length ? queue.slice(-MAX_PENDING) : null);
  }

  function enqueueCompletion(run) {
    const queue = loadPending();
    if (queue.some(item => item.runId === run.runId)) return;
    queue.push({
      ...run,
      eventId: uuid(),
      completedAt: new Date().toISOString()
    });
    savePending(queue);
  }

  async function flushPending() {
    if (flushBusy || !navigator.onLine) return;
    flushBusy = true;
    const queue = loadPending();
    try {
      while (queue.length) {
        const item = queue[0];
        const started = await rpc('snake2_level_started', {
          ...runPayload(item),
          p_mark_online: false
        });
        if (started?.accepted === false) throw new Error(`level start: ${started.reason || 'rejected'}`);

        const completed = await rpc('snake2_level_completed', {
          ...runPayload(item),
          p_event_id: item.eventId,
          p_client_completed_at: item.completedAt
        });
        if (completed?.accepted !== true && completed?.duplicate !== true) {
          throw new Error(`level completion: ${completed?.reason || 'rejected'}`);
        }
        render(completed);
        queue.shift();
        savePending(queue);
      }
    } catch (error) {
      setAvailability(false);
      console.debug('[Snake2 stats retry]', error?.message || error);
    } finally {
      flushBusy = false;
    }
  }

  function queuePresence(task) {
    presenceChain = presenceChain.catch(() => {}).then(task);
    return presenceChain;
  }

  function heartbeat() {
    if (!playing || document.visibilityState === 'hidden' || !navigator.onLine) return Promise.resolve();
    return queuePresence(async () => {
      try {
        render(await rpc('snake2_heartbeat', {
          p_session_id: sessionId,
          p_visitor_id: visitorId
        }));
      } catch (error) {
        setAvailability(false);
        console.debug('[Snake2 stats heartbeat]', error?.message || error);
      }
    });
  }

  function leavePresence(keepalive = false) {
    const task = async () => {
      try {
        render(await rpc('snake2_leave', {
          p_session_id: sessionId,
          p_visitor_id: visitorId
        }, keepalive));
      } catch (error) {
        console.debug('[Snake2 stats leave]', error?.message || error);
      }
    };
    return keepalive ? task() : queuePresence(task);
  }

  async function pollStats() {
    if (pollBusy || document.visibilityState === 'hidden' || !navigator.onLine) return;
    pollBusy = true;
    try {
      render(await rpc('snake2_get_stats'));
    } catch (error) {
      console.debug('[Snake2 stats poll]', error?.message || error);
    } finally {
      pollBusy = false;
    }
  }

  function trackLevelStart(details = {}) {
    const run = createRun(details.level, details.daily);
    activeRun = run;
    writeJson(sessionStore, ACTIVE_RUN_KEY, run);
    playing = true;

    queuePresence(async () => {
      try {
        const result = await rpc('snake2_level_started', {
          ...runPayload(run),
          p_mark_online: true
        });
        if (result?.accepted === false) throw new Error(result.reason || 'level rejected');
        render(result);
      } catch (error) {
        setAvailability(false);
        console.debug('[Snake2 stats level start]', error?.message || error);
      }
    });
  }

  function trackLevelComplete(details = {}) {
    const requestedLevel = Math.max(1, Math.floor(Number(details.level) || 1));
    const requestedDaily = Boolean(details.daily);
    if (!activeRun || activeRun.level !== requestedLevel || activeRun.daily !== requestedDaily) {
      console.debug('[Snake2 stats level] completion ignored without a matching active run');
      return;
    }
    const run = activeRun;
    enqueueCompletion(run);
    activeRun = null;
    writeJson(sessionStore, ACTIVE_RUN_KEY, null);
    playing = false;
    void flushPending();
    void leavePresence();
    void pollStats();
  }

  function trackLevelEnd() {
    activeRun = null;
    writeJson(sessionStore, ACTIVE_RUN_KEY, null);
    playing = false;
    void leavePresence();
    void pollStats();
  }

  window.snake2TrackLevelStart = trackLevelStart;
  window.snake2TrackLevelComplete = trackLevelComplete;
  window.snake2TrackLevelEnd = trackLevelEnd;

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      if (playing) void heartbeat();
      void flushPending();
      void pollStats();
    } else if (playing) {
      void leavePresence();
    }
  });

  window.addEventListener('online', () => {
    if (playing) void heartbeat();
    void flushPending();
    void pollStats();
  });
  window.addEventListener('offline', () => setAvailability(false));
  window.addEventListener('pagehide', () => {
    if (playing) void leavePresence(true);
  });
  window.addEventListener('pageshow', () => {
    if (playing) void heartbeat();
    void flushPending();
    void pollStats();
  });

  async function boot() {
    ensurePanel();
    try {
      render(await rpc('snake2_register_visitor', { p_visitor_id: visitorId }));
    } catch (error) {
      setAvailability(false);
      console.debug('[Snake2 stats visitor]', error?.message || error);
    }
    await flushPending();
    void pollStats();
    setInterval(() => { if (playing) void heartbeat(); }, HEARTBEAT_MS);
    setInterval(() => { void flushPending(); }, RETRY_MS);
    setInterval(() => { void pollStats(); }, STATS_POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    void boot();
  }
})();

// CR3@TIX ANALYTIX — central ecosystem tracker. snake2-stats.js is copied
// into the final GitHub Pages dist by the production workflow, so this loader
// is guaranteed to ship with the deployed game without touching gameplay.
(() => {
  if (document.querySelector('script[data-project-id="a0283201-3521-44ea-b1ff-3de1e311ec3b"]')) return;
  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://kevinlabens-del.github.io/CR3-TIX-ANALYTIX./analytics.js';
  if (typeof script.setAttribute === 'function') {
    script.setAttribute('data-project-id', 'a0283201-3521-44ea-b1ff-3de1e311ec3b');
    script.setAttribute('data-project-key', 'afd1eaaa-1f61-4f94-aee6-d1f79222a231');
  }
  document.head.appendChild(script);
})();

(() => {
  'use strict';

  const SUPABASE_URL = 'https://kokmqcqlpkruoewhewcb.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_E1RKbaZU7DkVoiyJmFWvqQ_hKBcBG9h';
  const VISITOR_KEY = 'snake2_visitor_id_v1';
  const SESSION_KEY = 'snake2_session_id_v1';
  const HEARTBEAT_MS = 15000;
  const GAME_CLICK_RE = /^(jouer|play|commencer|d[eé]marrer|nouvelle partie|rejouer|restart|start|new game)$/i;

  const uuid = () => globalThis.crypto?.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { const r=Math.random()*16|0,v=c==='x'?r:(r&3|8); return v.toString(16); });
  const getStoredId = (key, session=false) => { const store=session?sessionStorage:localStorage; let id=store.getItem(key); if(!id){id=uuid();store.setItem(key,id);} return id; };
  const visitorId=getStoredId(VISITOR_KEY), sessionId=getStoredId(SESSION_KEY,true);

  async function rpc(name,body={}){const response=await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`,{method:'POST',headers:{apikey:SUPABASE_KEY,'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});if(!response.ok)throw new Error(`stats ${name}: ${response.status}`);return response.json();}

  function ensurePanel(){
    let panel=document.getElementById('snake2-live-stats'); if(panel)return panel;
    const style=document.createElement('style');
    style.textContent=`
      #snake2-live-stats{position:absolute;z-index:2147483000;top:118px;left:50%;transform:translateX(-50%);display:flex;gap:5px;flex-wrap:nowrap;justify-content:center;width:max-content;max-width:94vw;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;pointer-events:none;filter:drop-shadow(0 2px 8px rgba(0,0,0,.55))}
      #snake2-live-stats .s2stat{display:inline-flex;align-items:center;gap:4px;min-height:27px;padding:4px 8px;border:1px solid rgba(94,255,126,.5);border-radius:999px;background:rgba(3,10,7,.86);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);color:#effff2;font-size:10px;font-weight:800;letter-spacing:.1px;line-height:1;white-space:nowrap;box-shadow:0 0 10px rgba(80,255,120,.1)}
      #snake2-live-stats .s2num{color:#79ff98;font-variant-numeric:tabular-nums;font-weight:950}
      #snake2-live-stats .online-dot{width:7px;height:7px;border-radius:50%;background:#48ff74;box-shadow:0 0 8px #48ff74}
      @media (max-width:460px){#snake2-live-stats{top:112px;gap:3px;max-width:96vw}#snake2-live-stats .s2stat{font-size:9.5px;padding:4px 6px;min-height:26px}}
      @media (min-width:700px){#snake2-live-stats{top:124px}}
    `;
    document.head.appendChild(style);
    panel=document.createElement('div'); panel.id='snake2-live-stats'; panel.setAttribute('aria-label','Statistiques Snake 2.0');
    panel.innerHTML=`<span class="s2stat">👥 <span class="s2num" data-s2="visitors">—</span> visiteurs</span><span class="s2stat">🎮 <span class="s2num" data-s2="games">—</span> parties</span><span class="s2stat"><span class="online-dot"></span><span class="s2num" data-s2="online">—</span> en ligne</span>`;
    document.body.appendChild(panel); return panel;
  }
  function render(data){if(!data||typeof data!=='object')return;ensurePanel();for(const key of ['visitors','games','online']){const node=document.querySelector(`[data-s2="${key}"]`),value=Number(data[key]);if(node&&Number.isFinite(value))node.textContent=value.toLocaleString('fr-FR');}}
  async function heartbeat(){if(document.visibilityState==='hidden')return;try{render(await rpc('snake2_heartbeat',{p_session_id:sessionId}));}catch(err){console.debug('[Snake2 stats]',err.message);}}
  let lastGameAt=0; async function trackGameStart(){const now=Date.now();if(now-lastGameAt<1200)return;lastGameAt=now;try{render(await rpc('snake2_game_started'));}catch(err){console.debug('[Snake2 stats]',err.message);}} window.snake2TrackGameStart=trackGameStart;
  document.addEventListener('click',event=>{const control=event.target.closest?.('button,a,[role="button"],input[type="button"],input[type="submit"]');if(!control)return;const text=String(control.innerText||control.value||control.getAttribute('aria-label')||'').trim().replace(/\s+/g,' ');if(GAME_CLICK_RE.test(text))trackGameStart();},true);
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')heartbeat();}); window.addEventListener('online',heartbeat);
  async function boot(){ensurePanel();try{render(await rpc('snake2_register_visitor',{p_visitor_id:visitorId}));}catch(err){console.debug('[Snake2 stats]',err.message);}await heartbeat();setInterval(heartbeat,HEARTBEAT_MS);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
'use strict';
(() => {
  const INSTALL_CONFIRMED_KEY = 'snake2_install_confirmed_v3';
  const state = {
    deferredPrompt: null,
    splashFinished: false,
    installCompleted: localStorage.getItem(INSTALL_CONFIRMED_KEY) === '1',
    installRequested: false,
    preparationTimer: null,
    swReady: false,
    startedAt: performance.now()
  };

  const INSTALL_READY_DELAY_MS = 32000;
  const qs = id => document.getElementById(id);
  const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isAndroid = () => /android/i.test(navigator.userAgent);

  const isInstalledLaunch = () => {
    try {
      return matchMedia('(display-mode: standalone)').matches ||
             matchMedia('(display-mode: fullscreen)').matches ||
             navigator.standalone === true ||
             document.referrer.startsWith('android-app://');
    } catch (_) { return false; }
  };

  function setStatus(title, text, mode = 'waiting') {
    const titleEl = qs('installGateTitle');
    const textEl = qs('installGateText');
    const gate = qs('installGate');
    if (titleEl) titleEl.textContent = title;
    if (textEl) textEl.textContent = text;
    if (gate) gate.dataset.mode = mode;
  }

  function setButton(label, disabled = false) {
    const button = qs('installGateBtn');
    if (!button) return;
    const labelEl = button.querySelector('b');
    if (labelEl) labelEl.textContent = label;
    else button.textContent = label;
    button.disabled = disabled;
  }

  function setHelp(html = '') {
    const help = qs('installGateHelp');
    if (!help) return;
    help.hidden = !html;
    if (html) help.innerHTML = html;
  }

  function ensureRefreshButton() {
    let button = qs('installRefreshBtn');
    if (button) return button;
    const primary = qs('installGateBtn');
    if (!primary || !primary.parentNode) return null;
    button = document.createElement('button');
    button.id = 'installRefreshBtn';
    button.type = 'button';
    button.hidden = true;
    button.innerHTML = '<span aria-hidden="true">↻</span><b>Rafraîchir et ouvrir l’application</b>';
    button.style.cssText = 'width:100%;margin-top:14px;min-height:58px;border:1px solid rgba(120,255,105,.55);border-radius:20px;background:rgba(21,54,20,.86);color:#efffe9;font:inherit;font-weight:800;display:flex;align-items:center;justify-content:center;gap:10px;padding:12px 18px;box-shadow:0 0 18px rgba(80,255,80,.12);';
    primary.insertAdjacentElement('afterend', button);
    button.addEventListener('click', refreshAndLaunch);
    return button;
  }

  function showRefreshButton(show) {
    const button = ensureRefreshButton();
    if (!button) return;
    button.hidden = !show;
    button.style.display = show ? 'flex' : 'none';
    button.disabled = false;
  }

  function showInstalledAction() {
    setStatus('Snake 2.0 est installé', 'L’installation est terminée. Tu peux maintenant rafraîchir et ouvrir le jeu.', 'installed');
    setButton('Installation terminée', true);
    setHelp('<strong>Installation terminée ✓</strong><span>Le bouton Installer reste validé. Appuie sur le bouton séparé ci-dessous pour tenter l’ouverture directe de Snake 2.0.</span><span>Si Android ne bascule pas automatiquement vers l’application, ouvre simplement l’icône Snake 2.0 depuis l’écran d’accueil.</span>');
    showRefreshButton(true);
  }

  function showIOSHelp() {
    showRefreshButton(false);
    setStatus('Installer Snake 2.0', 'Sur iPhone et iPad, l’installation se fait depuis le menu Partager de Safari.', 'ios');
    setButton('Voir les étapes iPhone', false);
    setHelp('<strong>Installation sur iPhone / iPad</strong><span>1. Ouvre cette page dans Safari.</span><span>2. Appuie sur Partager ⤴︎.</span><span>3. Choisis « Sur l’écran d’accueil » puis « Ajouter ».</span><span>4. Lance Snake 2.0 depuis sa nouvelle icône.</span>');
  }

  function showManualHelp() {
    showRefreshButton(false);
    const device = isAndroid()
      ? '<span>Android : menu ⋮ → « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>'
      : '<span>Menu du navigateur → « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>';
    setStatus('Installation via le navigateur', 'L’invite automatique n’est pas disponible. Utilise le menu du navigateur.', 'manual');
    setButton('Afficher les instructions', false);
    setHelp('<strong>Installation manuelle</strong>' + device + '<span>Si Snake 2.0 est déjà installé, lance-le depuis son icône.</span>');
  }

  function hideGate() {
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
    const gate = qs('installGate');
    document.documentElement.classList.remove('install-lock');
    document.body.classList.remove('install-required');
    document.body.classList.add('installed-app');
    if (gate) {
      gate.classList.remove('show');
      gate.setAttribute('aria-hidden', 'true');
    }
  }

  function showGate() {
    const gate = qs('installGate');
    if (!gate || !state.splashFinished) return;
    document.documentElement.classList.add('install-lock');
    document.body.classList.add('install-required');
    document.body.classList.remove('installed-app');
    gate.classList.add('show');
    gate.setAttribute('aria-hidden', 'false');
  }

  function remainingPreparationSeconds() {
    return Math.max(0, Math.ceil((INSTALL_READY_DELAY_MS - (performance.now() - state.startedAt)) / 1000));
  }

  function updatePreparation() {
    if (state.deferredPrompt || state.installCompleted || isInstalledLaunch()) {
      clearInterval(state.preparationTimer);
      state.preparationTimer = null;
      refreshGate();
      return;
    }
    const remaining = remainingPreparationSeconds();
    if (remaining > 0) {
      showRefreshButton(false);
      setStatus('Préparation de l’installation', `Chrome prépare l’installation${state.swReady ? '' : ' · vérification de l’application'}. Reste sur cette page encore ${remaining} s environ.`, 'preparing');
      setButton(`Préparation… ${remaining} s`, true);
    } else {
      clearInterval(state.preparationTimer);
      state.preparationTimer = null;
      showManualHelp();
    }
  }

  function beginPreparation() {
    state.installRequested = true;
    showRefreshButton(false);
    setHelp('');
    updatePreparation();
    if (!state.preparationTimer && !state.deferredPrompt) state.preparationTimer = setInterval(updatePreparation, 1000);
  }

  function refreshGate() {
    if (isInstalledLaunch()) {
      hideGate();
      return;
    }
    if (!state.splashFinished) return;
    showGate();
    if (state.installCompleted) return showInstalledAction();
    showRefreshButton(false);
    if (isIOS()) return showIOSHelp();
    if (state.deferredPrompt) {
      setHelp('');
      setStatus('Snake 2.0 est prêt', 'L’installation est prête. Appuie sur le bouton ci-dessous pour confirmer.', 'ready');
      setButton('Installer maintenant', false);
      return;
    }
    if (state.installRequested) return updatePreparation();
    setStatus('Installe Snake 2.0', 'Prépare l’installation de l’application sur cet appareil.', 'waiting');
    setButton('Préparer l’installation', false);
    setHelp('<strong>Pourquoi une préparation ?</strong><span>Le navigateur doit d’abord vérifier l’application avant d’autoriser son installation.</span>');
  }

  function refreshAndLaunch() {
    const button = ensureRefreshButton();
    if (button) {
      button.disabled = true;
      const b = button.querySelector('b');
      if (b) b.textContent = 'Ouverture…';
    }

    // This navigation is created synchronously from the user click so Chrome does not
    // treat it as a delayed popup. If installed-web-app link capture is available,
    // Android hands this same-origin URL to Snake 2.0.
    const launchUrl = new URL('./', location.href);
    launchUrl.searchParams.set('source', 'installed-open');
    launchUrl.searchParams.set('autostart', '1');
    launchUrl.searchParams.set('t', String(Date.now()));

    const opened = window.open(launchUrl.href, '_blank', 'noopener');

    // Refresh the browser page once, but never automatically loop.
    setTimeout(() => {
      const refreshUrl = new URL(location.href);
      refreshUrl.searchParams.set('refresh', String(Date.now()));
      location.replace(refreshUrl.href);
    }, opened ? 250 : 80);
  }

  function autoStartInstalledGame() {
    const params = new URLSearchParams(location.search);
    if (params.get('autostart') !== '1' || !isInstalledLaunch()) return;

    let attempts = 0;
    const timer = setInterval(() => {
      attempts++;
      const controls = [...document.querySelectorAll('button,a,[role="button"]')];
      const play = controls.find(el => /(^|\s)jouer(\s|$)/i.test((el.innerText || el.textContent || '').trim()));
      if (play && !play.disabled) {
        clearInterval(timer);
        play.click();
        const clean = new URL(location.href);
        clean.searchParams.delete('autostart');
        clean.searchParams.delete('source');
        clean.searchParams.delete('t');
        history.replaceState(null, '', clean.href);
      } else if (attempts >= 40) {
        clearInterval(timer);
      }
    }, 150);
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js?v=2.2.6-install4', { updateViaCache: 'none' })
      .then(reg => reg.update().then(() => navigator.serviceWorker.ready))
      .then(() => { state.swReady = true; refreshGate(); })
      .catch(error => { console.debug('[Snake2 install] service worker unavailable', error?.message || error); refreshGate(); });
  }

  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    state.deferredPrompt = event;
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
    refreshGate();
  });

  window.addEventListener('appinstalled', () => {
    state.installCompleted = true;
    state.deferredPrompt = null;
    localStorage.setItem(INSTALL_CONFIRMED_KEY, '1');
    showInstalledAction();
  });

  window.addEventListener('DOMContentLoaded', () => {
    ensureRefreshButton();
    const button = qs('installGateBtn');
    if (button) button.addEventListener('click', async () => {
      if (isInstalledLaunch()) return hideGate();
      if (state.installCompleted) return;
      if (isIOS()) return showIOSHelp();
      if (!state.deferredPrompt) {
        if (state.installRequested && remainingPreparationSeconds() <= 0) showManualHelp();
        else beginPreparation();
        return;
      }
      const promptEvent = state.deferredPrompt;
      state.deferredPrompt = null;
      setButton('Installation…', true);
      setHelp('');
      try {
        await promptEvent.prompt();
        const choice = await promptEvent.userChoice;
        if (choice?.outcome === 'accepted') {
          setStatus('Installation en cours', 'Attends la confirmation de ton appareil. Un bouton Rafraîchir apparaîtra ensuite sous le bouton Installer.', 'installing');
          setButton('Installation en cours…', true);
        } else {
          state.installRequested = false;
          setStatus('Installation annulée', 'Tu peux relancer l’installation.', 'cancelled');
          setButton('Préparer à nouveau', false);
        }
      } catch (error) {
        console.debug('[Snake2 install] prompt error', error?.message || error);
        showManualHelp();
      }
    });
    refreshGate();
    autoStartInstalledGame();
  });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') refreshGate();
  });

  try {
    const update = () => refreshGate();
    matchMedia('(display-mode: standalone)').addEventListener?.('change', update);
    matchMedia('(display-mode: fullscreen)').addEventListener?.('change', update);
  } catch (_) {}

  window.__SNAKE_INSTALL_GATE__ = {
    afterSplash() { state.splashFinished = true; refreshGate(); },
    refresh: refreshGate,
    isInstalledLaunch
  };
})();
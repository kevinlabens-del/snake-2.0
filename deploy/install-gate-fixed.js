'use strict';
(() => {
  const INSTALL_CONFIRMED_KEY = 'snake2_install_confirmed_v2';
  const SW_RELOAD_KEY = 'snake2_sw_reload_once_v2';
  const state = {
    deferredPrompt: null,
    splashFinished: false,
    installCompleted: localStorage.getItem(INSTALL_CONFIRMED_KEY) === '1' || new URLSearchParams(location.search).get('installed') === '1',
    installRequested: false,
    preparationTimer: null,
    swReady: false,
    startedAt: performance.now()
  };

  if (state.installCompleted) localStorage.setItem(INSTALL_CONFIRMED_KEY, '1');

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

  function showInstalledAction() {
    setStatus('Snake 2.0 est installé', 'Installation terminée. Appuie ci-dessous pour ouvrir le jeu dans l’application.', 'installed');
    setButton('▶ Ouvrir Snake 2.0', false);
    setHelp('<strong>Installation terminée ✓</strong><span>Snake 2.0 est maintenant installé sur cet appareil.</span><span>Appuie sur « Ouvrir Snake 2.0 ». Si Android ne bascule pas automatiquement dans l’application, ouvre son icône depuis l’écran d’accueil.</span>');
  }

  function showIOSHelp() {
    setStatus('Installer Snake 2.0', 'Sur iPhone et iPad, l’installation se fait depuis le menu Partager de Safari.', 'ios');
    setButton('Voir les étapes iPhone', false);
    setHelp('<strong>Installation sur iPhone / iPad</strong><span>1. Ouvre cette page dans Safari.</span><span>2. Appuie sur Partager ⤴︎.</span><span>3. Choisis « Sur l’écran d’accueil » puis « Ajouter ».</span><span>4. Lance Snake 2.0 depuis sa nouvelle icône.</span>');
  }

  function showManualHelp() {
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

  function hardRefreshAfterInstall() {
    const url = new URL(location.href);
    url.searchParams.set('installed', '1');
    url.searchParams.set('refresh', String(Date.now()));
    location.replace(url.href);
  }

  function openInstalledApp() {
    setButton('Ouverture…', true);
    setStatus('Ouverture de Snake 2.0', 'Tentative d’ouverture de l’application installée…', 'opening');
    const url = new URL('./', location.href);
    url.searchParams.set('source', 'installed-open');
    url.searchParams.set('t', String(Date.now()));
    const link = document.createElement('a');
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener';
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      link.remove();
      showInstalledAction();
    }, 1200);
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (sessionStorage.getItem(SW_RELOAD_KEY) === '1') return;
      sessionStorage.setItem(SW_RELOAD_KEY, '1');
      location.reload();
    });
    navigator.serviceWorker.register('./sw.js?v=2.2.6-install3', { updateViaCache: 'none' })
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
    setStatus('Installation terminée ✓', 'Actualisation automatique pour finaliser l’installation…', 'installed');
    setButton('Actualisation…', true);
    setTimeout(hardRefreshAfterInstall, 900);
  });

  window.addEventListener('DOMContentLoaded', () => {
    const button = qs('installGateBtn');
    if (button) button.addEventListener('click', async () => {
      if (isInstalledLaunch()) return hideGate();
      if (state.installCompleted) return openInstalledApp();
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
          setStatus('Installation en cours', 'Attends la confirmation de ton appareil. La page s’actualisera automatiquement ensuite.', 'installing');
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
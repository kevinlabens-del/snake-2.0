'use strict';
(() => {
  const state = {
    deferredPrompt: null,
    splashFinished: false,
    installCompleted: false,
    installRequested: false,
    preparationTimer: null,
    swReady: false,
    startedAt: performance.now()
  };

  const INSTALL_READY_DELAY_MS = 32000;

  const isInstalledLaunch = () => {
    try {
      return window.matchMedia('(display-mode: standalone)').matches ||
             window.matchMedia('(display-mode: fullscreen)').matches ||
             window.navigator.standalone === true ||
             document.referrer.startsWith('android-app://') ||
             new URLSearchParams(location.search).get('source') === 'installed';
    } catch (_) {
      return false;
    }
  };

  const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isAndroid = () => /android/i.test(navigator.userAgent);
  const qs = id => document.getElementById(id);

  // Register immediately. Do not wait for window.load or any third-party script.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js?v=2.2.6-install1', { updateViaCache: 'none' })
      .then(() => navigator.serviceWorker.ready)
      .then(() => {
        state.swReady = true;
        refreshGate();
      })
      .catch(error => {
        console.debug('[Snake2 install] service worker unavailable', error?.message || error);
        refreshGate();
      });
  }

  function setStatus(title, text, mode = 'waiting') {
    const titleEl = qs('installGateTitle');
    const textEl = qs('installGateText');
    const gate = qs('installGate');
    if (titleEl) titleEl.textContent = title;
    if (textEl) textEl.textContent = text;
    if (gate) gate.dataset.mode = mode;
  }

  function setButton(label = 'Installer Snake 2.0', disabled = false) {
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

  function showIOSHelp() {
    setHelp('<strong>Installation sur iPhone / iPad</strong><span>1. Ouvre cette page dans Safari.</span><span>2. Appuie sur Partager ⤴︎.</span><span>3. Choisis « Sur l’écran d’accueil » puis « Ajouter ».</span><span>4. Lance Snake 2.0 depuis sa nouvelle icône.</span>');
    setStatus('Installer Snake 2.0', 'Sur iPhone et iPad, l’installation se fait depuis le menu Partager de Safari.', 'ios');
    setButton('Voir les étapes iPhone', false);
  }

  function showManualHelp() {
    const deviceText = isAndroid()
      ? '<span>Android : ouvre le menu ⋮ de Chrome, Edge ou Samsung Internet puis choisis « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>'
      : '<span>Ouvre le menu de ton navigateur puis choisis « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>';
    setHelp('<strong>Installation manuelle</strong>' + deviceText + '<span>Si Snake 2.0 est déjà installé, lance-le directement depuis son icône.</span>');
    setStatus('Installation via le navigateur', 'L’invite automatique n’est pas disponible sur ce navigateur pour le moment. Utilise le menu du navigateur.', 'manual');
    setButton('Afficher les instructions', false);
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
    const elapsed = performance.now() - state.startedAt;
    return Math.max(0, Math.ceil((INSTALL_READY_DELAY_MS - elapsed) / 1000));
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
      const swText = state.swReady ? '' : ' · vérification de l’application';
      setStatus('Préparation de l’installation', `Chrome prépare l’installation${swText}. Reste sur cette page encore ${remaining} s environ.`, 'preparing');
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
    if (!state.preparationTimer && !state.deferredPrompt) {
      state.preparationTimer = setInterval(updatePreparation, 1000);
    }
  }

  function refreshGate() {
    if (isInstalledLaunch()) {
      hideGate();
      return;
    }
    if (!state.splashFinished) return;
    showGate();

    if (state.installCompleted) {
      setHelp('<strong>Installation terminée</strong><span>Ferme cette page puis ouvre Snake 2.0 depuis son icône sur l’écran d’accueil.</span>');
      setStatus('Snake 2.0 est installé', 'Lance maintenant le jeu depuis son icône.', 'installed');
      setButton('Installation terminée', true);
      return;
    }

    if (isIOS()) {
      showIOSHelp();
      return;
    }

    if (state.deferredPrompt) {
      setHelp('');
      setStatus('Snake 2.0 est prêt', 'L’installation est prête. Appuie sur le bouton ci-dessous pour confirmer avec ton navigateur.', 'ready');
      setButton('Installer maintenant', false);
      return;
    }

    if (state.installRequested) {
      updatePreparation();
      return;
    }

    setHelp('<strong>Pourquoi une préparation ?</strong><span>Le navigateur doit d’abord vérifier l’application avant d’autoriser l’installation. Appuie une fois ci-dessous pour commencer.</span>');
    setStatus('Installe Snake 2.0', 'Prépare l’installation de l’application sur cet appareil.', 'waiting');
    setButton('Préparer l’installation', false);
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
    refreshGate();
  });

  window.addEventListener('DOMContentLoaded', () => {
    const button = qs('installGateBtn');
    if (button) button.addEventListener('click', async () => {
      if (isInstalledLaunch()) {
        hideGate();
        return;
      }

      if (isIOS()) {
        showIOSHelp();
        return;
      }

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
          setStatus('Installation en cours', 'Confirme l’installation si ton appareil le demande, puis lance Snake 2.0 depuis son icône.', 'installing');
          setButton('Installation en cours…', true);
        } else {
          setStatus('Installation annulée', 'L’installation a été annulée. Tu peux réessayer lorsqu’elle sera de nouveau proposée.', 'cancelled');
          setButton('Préparer à nouveau', false);
          state.installRequested = false;
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
    afterSplash() {
      state.splashFinished = true;
      refreshGate();
    },
    refresh: refreshGate,
    isInstalledLaunch
  };
})();
'use strict';
(() => {
  // Never persist "installed" as a browser truth. Old versions did this and
  // could display a false positive after an uninstall or a failed install.
  try {
    ['snake2_install_confirmed_v1','snake2_install_confirmed_v2','snake2_install_confirmed_v3'].forEach(key => localStorage.removeItem(key));
  } catch (_) {}

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

  function setInstallButton() {
    setButton('Installer Snake 2.0', false);
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
    const label = button.querySelector('b');
    if (label) label.textContent = 'Rafraîchir et ouvrir l’application';
  }

  function showInstalledAction() {
    setStatus('Snake 2.0 est installé', 'L’installation vient d’être confirmée par ton appareil.', 'installed');
    setButton('Installation terminée', true);
    setHelp('<strong>Installation terminée ✓</strong><span>Cette confirmation provient directement de l’événement d’installation du navigateur.</span><span>Utilise le bouton séparé ci-dessous pour rafraîchir la page et tenter d’ouvrir Snake 2.0.</span>');
    showRefreshButton(true);
  }

  function showIOSHelp() {
    showRefreshButton(false);
    setStatus('Installer Snake 2.0', 'Sur iPhone et iPad, l’installation se fait depuis le menu Partager de Safari.', 'ios');
    setInstallButton();
    setHelp('<strong>Installation sur iPhone / iPad</strong><span>1. Ouvre cette page dans Safari.</span><span>2. Appuie sur Partager ⤴︎.</span><span>3. Choisis « Sur l’écran d’accueil » puis « Ajouter ».</span><span>4. Lance Snake 2.0 depuis sa nouvelle icône.</span>');
  }

  function showManualHelp() {
    showRefreshButton(false);
    const device = isAndroid()
      ? '<span>Android : menu ⋮ → « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>'
      : '<span>Menu du navigateur → « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>';
    setStatus('Installation via le navigateur', 'L’invite automatique n’est pas encore disponible. Le bouton Installer reste accessible et tu peux aussi utiliser le menu du navigateur.', 'manual');
    setInstallButton();
    setHelp('<strong>Installation manuelle</strong>' + device + '<span>Après installation, lance Snake 2.0 depuis son icône.</span>');
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
      setStatus('Préparation de l’installation', `Chrome prépare l’installation${state.swReady ? '' : ' · vérification de l’application'}. L’installation sera proposée automatiquement dès que Chrome sera prêt (${remaining} s environ).`, 'preparing');
      setInstallButton();
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
    // A real installed launch is the only persistent proof we accept.
    if (isInstalledLaunch()) {
      hideGate();
      return;
    }
    if (!state.splashFinished) return;
    showGate();

    // This state exists only in the current page lifetime after a real appinstalled event.
    if (state.installCompleted) return showInstalledAction();

    showRefreshButton(false);
    if (isIOS()) return showIOSHelp();
    if (state.deferredPrompt) {
      setHelp('');
      setStatus('Snake 2.0 est prêt', 'L’installation est prête. Appuie sur le bouton ci-dessous pour confirmer.', 'ready');
      setInstallButton();
      return;
    }
    if (state.installRequested) return updatePreparation();
    setStatus('Installe Snake 2.0', 'Installe l’application sur cet appareil pour lancer le jeu dans son mode dédié.', 'waiting');
    setInstallButton();
    setHelp('<strong>Installation requise</strong><span>Le bouton Installer reste disponible tant que le navigateur n’a pas confirmé l’installation.</span>');
  }

  function refreshAndLaunch() {
    // This button only exists after appinstalled fired in this page lifetime.
    if (!state.installCompleted) {
      refreshGate();
      return;
    }
    const button = ensureRefreshButton();
    if (button) {
      button.disabled = true;
      const label = button.querySelector('b');
      if (label) label.textContent = 'Ouverture…';
    }

    const launchUrl = new URL('./', location.href);
    launchUrl.searchParams.set('source', 'installed-open');
    launchUrl.searchParams.set('autostart', '1');
    launchUrl.searchParams.set('t', String(Date.now()));

    // Keep the user gesture synchronous so Android can hand the URL to the PWA
    // when link capture is supported. Failure simply leaves the browser page open.
    window.open(launchUrl.href, '_blank', 'noopener');

    // Refresh browser state once. No install state is persisted, so a browser reload
    // can never manufacture an "installed" status.
    setTimeout(() => {
      const clean = new URL(location.href);
      clean.searchParams.set('refresh', String(Date.now()));
      location.replace(clean.href);
    }, 350);
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
        ['autostart','source','t'].forEach(key => clean.searchParams.delete(key));
        history.replaceState(null, '', clean.href);
      } else if (attempts >= 40) clearInterval(timer);
    }, 150);
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js?v=2.2.6-install5', { updateViaCache: 'none' })
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
    // Current-page proof only. Deliberately never written to localStorage/sessionStorage.
    state.installCompleted = true;
    state.deferredPrompt = null;
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
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
      state.installRequested = true;
      const promptEvent = state.deferredPrompt;
      state.deferredPrompt = null;
      setInstallButton();
      setHelp('');
      try {
        await promptEvent.prompt();
        const choice = await promptEvent.userChoice;
        if (choice?.outcome === 'accepted') {
          setStatus('Installation en cours', 'Attends la confirmation réelle de ton appareil. Le bouton Installer restera disponible jusqu’à la confirmation finale.', 'installing');
          setInstallButton();
        } else {
          state.installRequested = false;
          setStatus('Installation annulée', 'Tu peux relancer l’installation immédiatement.', 'cancelled');
          setInstallButton();
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
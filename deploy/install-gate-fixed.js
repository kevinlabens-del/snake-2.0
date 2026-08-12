'use strict';
(() => {
  try {
    ['snake2_install_confirmed_v1','snake2_install_confirmed_v2','snake2_install_confirmed_v3'].forEach(key => localStorage.removeItem(key));
  } catch (_) {}

  const state = {
    deferredPrompt: null,
    splashFinished: false,
    installCompleted: false,
    installConfirmedAt: 0,
    installRequested: false,
    preparationTimer: null,
    browserPlayAllowed: false,
    swReady: false,
    startedAt: performance.now()
  };

  const INSTALL_READY_DELAY_MS = 8000;
  const qs = id => document.getElementById(id);
  const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isAndroid = () => /android/i.test(navigator.userAgent);
  const isFacebookWebView = () => /FBAN|FBAV|FB_IAB|FB4A|FBIOS|Messenger/i.test(navigator.userAgent);
  const isInstagramWebView = () => /Instagram/i.test(navigator.userAgent);
  const isSocialWebView = () => isFacebookWebView() || isInstagramWebView();

  const cleanAppUrl = () => {
    const url = new URL(location.href);
    ['autostart','source','t','refresh'].forEach(key => url.searchParams.delete(key));
    url.hash = '';
    return url;
  };

  const isInstalledLaunch = () => {
    try {
      return matchMedia('(display-mode: standalone)').matches ||
             matchMedia('(display-mode: fullscreen)').matches ||
             navigator.standalone === true ||
             document.referrer.startsWith('android-app://');
    } catch (_) { return false; }
  };

  const hasInstallConfirmation = () =>
    state.installCompleted === true &&
    Number.isFinite(state.installConfirmedAt) &&
    state.installConfirmedAt > 0;

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
    button.hidden = false;
    button.style.display = '';
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

  function ensureBrowserPlayButton() {
    let button = qs('browserPlayBtn');
    if (button) return button;
    const primary = qs('installGateBtn');
    if (!primary || !primary.parentNode) return null;
    button = document.createElement('button');
    button.id = 'browserPlayBtn';
    button.type = 'button';
    button.innerHTML = '<span aria-hidden="true">▶</span><b>Jouer dans le navigateur</b>';
    button.style.cssText = 'width:100%;margin-top:10px;min-height:54px;border:1px solid rgba(255,255,255,.18);border-radius:18px;background:rgba(8,14,10,.72);color:#eaffea;font:inherit;font-weight:800;display:flex;align-items:center;justify-content:center;gap:10px;padding:12px 18px;';
    primary.insertAdjacentElement('afterend', button);
    button.addEventListener('click', () => {
      state.browserPlayAllowed = true;
      hideGate();
    });
    return button;
  }

  function showBrowserPlayButton(show = true) {
    const button = ensureBrowserPlayButton();
    if (!button) return;
    button.hidden = !show;
    button.style.display = show ? 'flex' : 'none';
  }

  function ensureExternalBrowserButton() {
    let button = qs('externalBrowserBtn');
    if (button) return button;
    const primary = qs('installGateBtn');
    if (!primary || !primary.parentNode) return null;
    button = document.createElement('a');
    button.id = 'externalBrowserBtn';
    button.setAttribute('role', 'button');
    button.rel = 'noopener external';
    button.innerHTML = '<span aria-hidden="true">↗</span><b>Ouvrir dans Chrome</b>';
    button.style.cssText = 'width:100%;box-sizing:border-box;margin-top:12px;min-height:60px;border:1px solid rgba(120,255,105,.7);border-radius:20px;background:linear-gradient(180deg,rgba(35,93,31,.96),rgba(14,48,16,.96));color:#f2ffef;font:inherit;font-weight:900;text-decoration:none;display:flex;align-items:center;justify-content:center;gap:10px;padding:12px 18px;box-shadow:0 0 22px rgba(80,255,80,.14);';
    primary.insertAdjacentElement('afterend', button);
    return button;
  }

  function showExternalBrowserButton(show = true) {
    const button = ensureExternalBrowserButton();
    if (!button) return;
    button.hidden = !show;
    button.style.display = show ? 'flex' : 'none';
    if (!show) return;
    const url = cleanAppUrl();
    if (isAndroid()) {
      const intentPath = `${url.host}${url.pathname}${url.search}`;
      button.href = `intent://${intentPath}#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=${encodeURIComponent(url.href)};end`;
      button.querySelector('b').textContent = 'Ouvrir dans Chrome';
    } else {
      button.href = url.href;
      button.target = '_blank';
      button.querySelector('b').textContent = isIOS() ? 'Ouvrir dans Safari' : 'Ouvrir dans le navigateur';
    }
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
    const allowed = show === true && hasInstallConfirmation();
    button.hidden = !allowed;
    button.style.display = allowed ? 'flex' : 'none';
    button.disabled = !allowed;
    const label = button.querySelector('b');
    if (label) label.textContent = 'Rafraîchir et ouvrir l’application';
  }

  function showInstalledAction() {
    if (!hasInstallConfirmation()) {
      showRefreshButton(false);
      return;
    }
    showExternalBrowserButton(false);
    showBrowserPlayButton(false);
    setStatus('Snake 2.0 est installé', 'L’installation vient d’être confirmée par ton appareil.', 'installed');
    setButton('Installation terminée', true);
    setHelp('<strong>Installation terminée ✓</strong><span>Tu peux maintenant ouvrir Snake 2.0 depuis son icône ou avec le bouton ci-dessous.</span>');
    showRefreshButton(true);
  }

  function showSocialWebViewHelp() {
    showRefreshButton(false);
    showBrowserPlayButton(true);
    showExternalBrowserButton(true);
    setStatus('Ouvre Snake 2.0 dans ton navigateur', 'Facebook et Instagram limitent l’installation depuis leur navigateur intégré. Ouvre le jeu dans Chrome ou Safari pour installer l’application correctement.', 'social-browser');
    setButton('Installation indisponible ici', true);
    setHelp('<strong>Facebook / Instagram détecté</strong><span>Le jeu n’est pas en panne : c’est le navigateur intégré du réseau social qui bloque l’installation.</span><span>Appuie sur « Ouvrir dans Chrome » puis installe Snake 2.0 depuis ce navigateur.</span><span>Tu peux aussi jouer immédiatement dans le navigateur avec le bouton prévu.</span>');
  }

  function showIOSHelp() {
    showRefreshButton(false);
    showExternalBrowserButton(false);
    showBrowserPlayButton(true);
    setStatus('Installer Snake 2.0', 'Sur iPhone et iPad, l’installation se fait depuis le menu Partager de Safari.', 'ios');
    setInstallButton();
    setHelp('<strong>Installation sur iPhone / iPad</strong><span>1. Ouvre cette page dans Safari.</span><span>2. Appuie sur Partager ⤴︎.</span><span>3. Choisis « Sur l’écran d’accueil » puis « Ajouter ».</span><span>4. Lance Snake 2.0 depuis sa nouvelle icône.</span>');
  }

  function showManualHelp() {
    showRefreshButton(false);
    showExternalBrowserButton(false);
    showBrowserPlayButton(true);
    const device = isAndroid()
      ? '<span>Android : menu ⋮ → « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>'
      : '<span>Menu du navigateur → « Installer l’application » ou « Ajouter à l’écran d’accueil ».</span>';
    setStatus('Installation via le navigateur', 'L’invite automatique n’est pas disponible pour le moment. Tu peux installer Snake 2.0 depuis le menu du navigateur ou jouer immédiatement.', 'manual');
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
    if (state.deferredPrompt || hasInstallConfirmation() || isInstalledLaunch()) {
      clearInterval(state.preparationTimer);
      state.preparationTimer = null;
      refreshGate();
      return;
    }
    const remaining = remainingPreparationSeconds();
    if (remaining > 0) {
      showRefreshButton(false);
      showBrowserPlayButton(true);
      setStatus('Préparation de l’installation', `Chrome prépare l’installation${state.swReady ? '' : ' · vérification de l’application'} (${remaining} s environ). Tu peux aussi jouer immédiatement dans le navigateur.`, 'preparing');
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
    if (isInstalledLaunch() || state.browserPlayAllowed) {
      hideGate();
      return;
    }
    if (!state.splashFinished) return;
    showGate();

    if (hasInstallConfirmation()) return showInstalledAction();
    showRefreshButton(false);
    if (isSocialWebView()) return showSocialWebViewHelp();
    showExternalBrowserButton(false);
    showBrowserPlayButton(true);
    if (isIOS()) return showIOSHelp();
    if (state.deferredPrompt) {
      setHelp('<strong>Deux choix</strong><span>Installe Snake 2.0 pour une expérience plein écran, ou joue tout de suite dans le navigateur.</span>');
      setStatus('Snake 2.0 est prêt', 'Installe l’application ou lance directement le jeu dans le navigateur.', 'ready');
      setInstallButton();
      return;
    }
    if (state.installRequested) return updatePreparation();
    setStatus('Snake 2.0', 'Installe l’application pour le meilleur confort, ou joue immédiatement dans ton navigateur.', 'waiting');
    setInstallButton();
    setHelp('<strong>À toi de choisir</strong><span>L’installation n’est plus obligatoire pour jouer.</span>');
  }

  function refreshAndLaunch() {
    if (!hasInstallConfirmation()) {
      showRefreshButton(false);
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
    window.open(launchUrl.href, '_blank', 'noopener');

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
    state.installCompleted = false;
    state.installConfirmedAt = 0;
    state.deferredPrompt = event;
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
    showRefreshButton(false);
    refreshGate();
  });

  window.addEventListener('appinstalled', () => {
    state.installCompleted = true;
    state.installConfirmedAt = Date.now();
    state.deferredPrompt = null;
    clearInterval(state.preparationTimer);
    state.preparationTimer = null;
    showInstalledAction();
  });

  window.addEventListener('DOMContentLoaded', () => {
    ensureRefreshButton();
    ensureBrowserPlayButton();
    ensureExternalBrowserButton();
    showRefreshButton(false);
    showExternalBrowserButton(false);
    const button = qs('installGateBtn');
    if (button) button.addEventListener('click', async () => {
      if (isInstalledLaunch()) return hideGate();
      if (isSocialWebView()) return showSocialWebViewHelp();
      if (hasInstallConfirmation()) return showInstalledAction();
      if (isIOS()) return showIOSHelp();
      if (!state.deferredPrompt) {
        if (state.installRequested && remainingPreparationSeconds() <= 0) showManualHelp();
        else beginPreparation();
        return;
      }
      state.installRequested = true;
      const promptEvent = state.deferredPrompt;
      state.deferredPrompt = null;
      showRefreshButton(false);
      setInstallButton();
      setHelp('');
      try {
        await promptEvent.prompt();
        const choice = await promptEvent.userChoice;
        if (choice?.outcome === 'accepted') {
          setStatus('Installation en cours', 'L’appareil finalise l’installation. Tu peux aussi continuer à jouer dans le navigateur.', 'installing');
          showRefreshButton(false);
          showBrowserPlayButton(true);
          setInstallButton();
        } else {
          state.installRequested = false;
          state.installCompleted = false;
          state.installConfirmedAt = 0;
          setStatus('Installation annulée', 'Aucun souci : tu peux jouer dans le navigateur ou relancer l’installation.', 'cancelled');
          showRefreshButton(false);
          showBrowserPlayButton(true);
          setInstallButton();
        }
      } catch (error) {
        console.debug('[Snake2 install] prompt error', error?.message || error);
        state.installCompleted = false;
        state.installConfirmedAt = 0;
        showRefreshButton(false);
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
    isInstalledLaunch,
    isSocialWebView,
    hasInstallConfirmation
  };
})();
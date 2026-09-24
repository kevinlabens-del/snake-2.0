"use strict";

/* CR3ATIX_SHARE_V1 — partage public de Snake 2.0, sans progression ni état local. */
(() => {
  const button = document.getElementById("shareAppBtn");
  const status = document.getElementById("shareAppStatus");
  if (!button) return;

  const canonicalUrl = "https://kevinlabens-del.github.io/snake-2.0/";
  let statusTimer = 0;

  const setStatus = (message) => {
    if (!status) return;
    status.textContent = message;
    window.clearTimeout(statusTimer);
    statusTimer = window.setTimeout(() => {
      status.textContent = "Lien public uniquement · aucune progression envoyée";
    }, 2800);
  };

  const legacyCopy = () => {
    const field = document.createElement("textarea");
    field.value = canonicalUrl;
    field.readOnly = true;
    field.style.cssText = "position:fixed;opacity:0;pointer-events:none;inset:auto 0 0";
    document.body.appendChild(field);
    field.select();
    field.setSelectionRange(0, field.value.length);
    let copied = false;
    try { copied = document.execCommand("copy"); } catch {}
    field.remove();

    if (copied) setStatus("Lien de Snake 2.0 copié");
    else window.prompt("Copie ce lien pour partager Snake 2.0 :", canonicalUrl);
  };

  const copyFallback = async () => {
    try {
      if (window.isSecureContext && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(canonicalUrl);
        setStatus("Lien de Snake 2.0 copié");
        return;
      }
    } catch {}
    legacyCopy();
  };

  button.addEventListener("click", async () => {
    const data = {
      title: "Snake 2.0",
      text: "Viens jouer à Snake 2.0 : plus de 600 niveaux, missions, obstacles et progression infinie.",
      url: canonicalUrl
    };

    if (navigator.share) {
      try {
        await navigator.share(data);
        return;
      } catch (error) {
        if (error && error.name === "AbortError") return;
      }
    }

    await copyFallback();
  });
})();

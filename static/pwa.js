(() => {
  if (!('serviceWorker' in navigator)) return;

  const installButton = document.querySelector('#pwa-install');
  let installPrompt;
  const dismissed = () => {
    try { return localStorage.getItem('sylrix-install-dismissed') === '1'; } catch (_) { return false; }
  };
  const dismiss = () => { try { localStorage.setItem('sylrix-install-dismissed', '1'); } catch (_) {} };

  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    if (installButton && !dismissed()) installButton.hidden = false;
  });

  installButton?.addEventListener('click', async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = undefined;
    installButton.hidden = true;
    dismiss();
  });

  window.addEventListener('appinstalled', () => {
    installButton && (installButton.hidden = true);
    dismiss();
  });

  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      registration.update();
    } catch (_) {
      // The normal website remains fully usable when workers are unavailable.
    }
  });
})();

/**
 * PWA Service Worker Registration & Installation Manager
 */

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
};

let deferredPrompt: InstallPromptEvent | null = null;
const installListeners: Array<(canInstall: boolean) => void> = [];
const onlineListeners: Array<(isOnline: boolean) => void> = [];

export function initPWA() {
  if (typeof window === 'undefined') return;

  // 1. Register Service Worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.log('[PWA] Service Worker registered with scope:', registration.scope);

          registration.onupdatefound = () => {
            const installingWorker = registration.installing;
            if (installingWorker) {
              installingWorker.onstatechange = () => {
                if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('[PWA] New version available! Reloading or prompt.');
                }
              };
            }
          };
        })
        .catch((error) => {
          console.warn('[PWA] Service Worker registration failed:', error);
        });
    });
  }

  // 2. Intercept beforeinstallprompt for in-app install button
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e as InstallPromptEvent;
    notifyInstallListeners(true);
  });

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    notifyInstallListeners(false);
    console.log('[PWA] MK-Path app installed successfully!');
  });

  // 3. Online/Offline detection
  window.addEventListener('online', () => notifyOnlineListeners(true));
  window.addEventListener('offline', () => notifyOnlineListeners(false));
}

export function subscribeInstall(callback: (canInstall: boolean) => void) {
  installListeners.push(callback);
  callback(deferredPrompt !== null);
  return () => {
    const idx = installListeners.indexOf(callback);
    if (idx !== -1) installListeners.splice(idx, 1);
  };
}

export function subscribeOnline(callback: (isOnline: boolean) => void) {
  onlineListeners.push(callback);
  callback(navigator.onLine);
  return () => {
    const idx = onlineListeners.indexOf(callback);
    if (idx !== -1) onlineListeners.splice(idx, 1);
  };
}

function notifyInstallListeners(canInstall: boolean) {
  installListeners.forEach((cb) => {
    try {
      cb(canInstall);
    } catch (e) {
      console.error(e);
    }
  });
}

function notifyOnlineListeners(isOnline: boolean) {
  onlineListeners.forEach((cb) => {
    try {
      cb(isOnline);
    } catch (e) {
      console.error(e);
    }
  });
}

export async function promptInstallApp(): Promise<boolean> {
  if (!deferredPrompt) return false;
  try {
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    deferredPrompt = null;
    notifyInstallListeners(false);
    return choice.outcome === 'accepted';
  } catch (err) {
    console.error('[PWA] Install prompt failed:', err);
    return false;
  }
}

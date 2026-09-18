const CACHE_NAME = 'sylrix-public-{{ asset_version }}';
const PUBLIC_SHELL = [
  '/static/offline.html',
  '/static/style.css',
  '/static/marketing.css',
  '/static/training-cards.css',
  '/static/app-screens.css',
  '/static/sylrix-fit.css',
  '/static/mobile-nav.js',
  '/static/pwa.js',
  '/static/branding/sylrix-icon.png',
  '/static/branding/sylrix-wordmark.png',
  '/static/branding/favicon.png',
  '/static/branding/apple-touch-icon.png',
  '/static/branding/sylrix-icon-192.png',
  '/static/branding/sylrix-icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(PUBLIC_SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('sylrix-public-') && key !== CACHE_NAME).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/static/offline.html')));
    return;
  }
  const url = new URL(request.url);
  if (!url.pathname.startsWith('/static/')) return;
  // Versioned CSS and JavaScript must be refreshed while a PWA is installed.
  // The earlier ignoreSearch cache lookup could return an older asset even
  // after the HTML pointed at a newer ?v= URL.
  event.respondWith(fetch(request).then(response => {
    if (!response || !response.ok) return response;
    const copy = response.clone();
    caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
    return response;
  }).catch(() => caches.match(request).then(cached => cached || caches.match(url.pathname))));
});

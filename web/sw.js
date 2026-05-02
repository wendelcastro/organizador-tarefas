const CACHE_NAME = 'organizador-v4';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './design-tokens.css',
  './styles.css',
  './js/app-core.js',
  './js/views-main.js',
  './js/features-1.js',
  './js/features-2.js',
  './js/features-3.js',
  './js/features-4-init.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Skip Supabase API calls — always fetch fresh data
  if (e.request.url.includes('supabase.co')) return;

  // Network-first strategy: try network, fallback to cache
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

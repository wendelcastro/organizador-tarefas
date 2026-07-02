const CACHE_NAME = 'organizador-v5';
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
  // Só cacheia navegações e assets GET. Ignora Supabase (dados sempre frescos),
  // métodos não-GET e outros esquemas (ex.: chrome-extension).
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('supabase.co')) return;
  if (!e.request.url.startsWith('http')) return;

  // Network-first: tenta rede, cai para cache se offline.
  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Só cacheia respostas OK e "básicas/cors" — nunca 4xx/5xx, redirects
        // opacos ou portal cativo (evita servir página quebrada offline).
        if (res && res.ok && (res.type === 'basic' || res.type === 'cors')) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

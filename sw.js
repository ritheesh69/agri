// Cache name
const CACHE_NAME = 'agrimarket-v1';

// Files to cache
const urlsToCache = [
  '/',
  '/static/css/*',
  '/static/media/*',
  '/images/*'
];

// Install event - caches important files
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Fetch event - serves cached files when offline
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});

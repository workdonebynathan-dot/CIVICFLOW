const CACHE_NAME = 'civicflow-v1';
const ASSETS_TO_CACHE = [
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// 1. INSTALL: Cache assets & force activation
self.addEventListener('install', (e) => {
    console.log('✅ Service Worker: Installing...');
    
    // FORCE the new service worker to activate immediately (Fixes "Waiting" issue)
    self.skipWaiting(); 

    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// 2. ACTIVATE: Clean up old caches
self.addEventListener('activate', (e) => {
    console.log('✅ Service Worker: Activated');
    e.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
    return self.clients.claim();
});

// 3. FETCH: Smart Network-First Strategy
self.addEventListener('fetch', (e) => {
    // A. For HTML pages (Login, Dashboard), ALWAYS go to network first
    if (e.request.destination === 'document') {
        e.respondWith(
            fetch(e.request).catch(() => {
                // If offline, you could return a custom offline.html here
                return caches.match('/static/offline.html'); 
            })
        );
        return;
    }

    // B. For CSS/Images/Fonts, try Cache first, then Network
    e.respondWith(
        caches.match(e.request).then((response) => {
            return response || fetch(e.request);
        })
    );
});
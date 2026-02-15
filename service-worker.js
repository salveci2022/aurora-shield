// Nome do cache
const CACHE_NAME = 'aurora-cache-v1';

// Arquivos para cache inicial
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/panic.js',
    '/static/js/confidant.js',
    '/manifest.json'
];

// Instalação do Service Worker
self.addEventListener('install', event => {
    self.skipWaiting();
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Cache aberto');
                return cache.addAll(urlsToCache);
            })
    );
});

// Ativação - limpa caches antigos
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Removendo cache antigo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Intercepta requisições
self.addEventListener('fetch', event => {
    // Não fazer cache de chamadas API
    if (event.request.url.includes('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }
    
    // Estratégia: Network first, fallback para cache
    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Se a rede funcionar, atualiza o cache
                if (response && response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Se falhar, tenta pegar do cache
                return caches.match(event.request);
            })
    );
});

// Sincronização em background (para quando estiver offline)
self.addEventListener('sync', event => {
    if (event.tag === 'sync-alerts') {
        event.waitUntil(syncAlerts());
    }
});

async function syncAlerts() {
    try {
        // Recupera alertas pendentes do IndexedDB
        const db = await openDB();
        const pendingAlerts = await getPendingAlerts(db);
        
        for (const alert of pendingAlerts) {
            await fetch('/api/panic', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(alert)
            });
            
            await markAlertAsSynced(db, alert.id);
        }
    } catch (error) {
        console.log('Erro na sincronização:', error);
    }
}

// Funções auxiliares para IndexedDB (simplificado)
async function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('AuroraDB', 1);
        request.onerror = reject;
        request.onsuccess = () => resolve(request.result);
        request.onupgradeneeded = event => {
            const db = event.target.result;
            db.createObjectStore('pendingAlerts', { keyPath: 'id', autoIncrement: true });
        };
    });
}

async function getPendingAlerts(db) {
    return new Promise((resolve, reject) => {
        const tx = db.transaction('pendingAlerts', 'readonly');
        const store = tx.objectStore('pendingAlerts');
        const request = store.getAll();
        request.onerror = reject;
        request.onsuccess = () => resolve(request.result);
    });
}

async function markAlertAsSynced(db, id) {
    return new Promise((resolve, reject) => {
        const tx = db.transaction('pendingAlerts', 'readwrite');
        const store = tx.objectStore('pendingAlerts');
        const request = store.delete(id);
        request.onerror = reject;
        request.onsuccess = resolve;
    });
}

// Notificações push (para futuro)
self.addEventListener('push', event => {
    const data = event.data.json();
    
    const options = {
        body: data.body,
        icon: '/static/icon-192.png',
        badge: '/static/icon-192.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/confidant'
        }
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('fetch', e => e.respondWith(fetch(e.request)));
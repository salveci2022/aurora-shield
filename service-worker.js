// ===============================
// AURORA SERVICE WORKER - V1
// ===============================

const CACHE_NAME = "aurora-cache-v1";

const urlsToCache = [
  "/",
  "/static/css/style.css",
  "/static/js/panic.js",
  "/static/js/confidant.js",
  "/static/images/logo.png",
  "/manifest.json"
];

// INSTALAÇÃO
self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// ATIVAÇÃO
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(names => {
      return Promise.all(
        names.map(name => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    })
  );
});

// FETCH
self.addEventListener("fetch", event => {

  // Ignora APIs
  if (event.request.url.includes("/api/")) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

// PUSH (FUTURO)
self.addEventListener("push", event => {
  const data = event.data.json();

  const options = {
    body: data.body,
    icon: "/static/images/logo.png",
    badge: "/static/images/logo.png",
    vibrate: [200,100,200],
    data: {
      url: data.url || "/confidant"
    }
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// CLICK NOTIFICAÇÃO
self.addEventListener("notificationclick", event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});
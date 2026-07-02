---
recipe_id: "service-worker-offline-first"
title: "Service Worker: Offline-First Without Losing User Data"
file: "recipes/pwa/service-worker-offline-first.md"
primary_concept: "tooling/pwa"
related_concepts: ["reactivity/signals", "http/http", "dependency-injection/dependency-injection"]
demo_repo: null
angular_baseline: "22"
difficulty: "advanced"
status:
  upgraded: true
  reviewed: false
---

# Service Worker: Offline-First Without Losing User Data

> **What you'll build:** an offline-first Angular app using
> `@angular/service-worker` — asset caching so the app shell loads
> without a network, API caching with the freshness/performance
> strategies, a signal-based connection-state service that doesn't
> naively trust `navigator.onLine`, a mutation queue that persists
> pending POSTs across offline periods and reloads, and the
> "new version available" refresh UX. Real users on subways,
> flights, and flaky mobile networks stop losing their work.
>
> **Concepts you'll touch:** [PWA / Tooling](../../tooling/pwa.md), [Signals](../../reactivity/signals.md), [HTTP](../../http/http.md), [Dependency Injection](../../dependency-injection/dependency-injection.md)
>
> **Time:** ~40 minutes to read; ~1 day to retrofit a real app
> including testing the queue behavior under simulated offline
> conditions.

---

## The scenario

A user is buying concert tickets on their phone. They've spent 15 minutes picking seats, applying a discount code, filling in delivery info. They tap **Place order**. Their subway train enters a tunnel.

**What the naive app does**: the POST fails with a network error. A toast says "Please check your connection and try again." The user re-emerges above ground and the app is on the home page — their cart is empty, the discount code is gone, they lost the seats they had reserved.

**What the offline-first app does**: the tap works. The button shows "Order pending sync." The cart persists in localStorage. When the train exits the tunnel and connectivity returns, the queued POST fires automatically; the order lands; the user gets a "✓ Order placed" toast. They never notice they were offline.

The gap between these two apps is `@angular/service-worker` + one small service that owns the pending-mutation queue. This recipe walks through both.

---

## The three layers of "offline-first"

An offline-capable app has three concerns, each independent:

| Layer | What it caches | Package/API |
| --- | --- | --- |
| **App shell** | HTML, JS, CSS, fonts, images — the "static" bundle | `@angular/service-worker` `assetGroups` |
| **API responses** | GET responses from your backend | `@angular/service-worker` `dataGroups` |
| **Pending mutations** | POST/PUT/DELETE the user attempted while offline | Your own `OfflineMutationQueue` service |

**The service worker handles layers 1 and 2 declaratively** via JSON config. **The mutation queue is application code** because only your app knows how to combine it with optimistic UI, idempotency keys, and business rules.

Do all three, and the app is genuinely offline-capable. Skip any one and the user's experience breaks:

- No app shell caching → "This site can't be reached" when offline
- No API caching → app loads but content is missing (blank cards, empty lists)
- No mutation queue → user's actions get silently lost

---

## Setting up the Angular service worker

The fastest way is Angular's PWA schematic:

```bash
ng add @angular/pwa
```

This adds `@angular/service-worker` to `package.json`, generates `ngsw-config.json`, registers the service worker in `app.config.ts`, adds a `manifest.webmanifest`, and injects the PWA meta tags into `index.html`.

Or manually — install the package and register:

```typescript
// File: app.config.ts
import { ApplicationConfig, isDevMode } from '@angular/core';
import { provideServiceWorker } from '@angular/service-worker';

export const appConfig: ApplicationConfig = {
  providers: [
    // …other providers
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),   // SW off during dev; auto-reload conflicts
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ],
};
```

Then create `ngsw-config.json` at the project root — its structure is covered next. The build automatically picks it up.

**`enabled: !isDevMode()`** is critical. Development mode's live reload and the service worker fight each other; you get cached versions of code you just changed. Enable only for production builds.

**`registrationStrategy: 'registerWhenStable:30000'`** waits until the app is stable (or 30 seconds have passed) before registering, so the SW registration doesn't compete with initial render for network bandwidth.

---

## The `ngsw-config.json` — declarative caching

Two top-level arrays: `assetGroups` (static files) and `dataGroups` (API responses).

```json
{
  "$schema": "./node_modules/@angular/service-worker/config/schema.json",
  "index": "/index.html",
  "assetGroups": [
    {
      "name": "app-shell",
      "installMode": "prefetch",
      "updateMode": "prefetch",
      "resources": {
        "files": [
          "/favicon.ico",
          "/index.html",
          "/manifest.webmanifest",
          "/*.css",
          "/*.js"
        ]
      }
    },
    {
      "name": "assets",
      "installMode": "lazy",
      "updateMode": "prefetch",
      "resources": {
        "files": [
          "/assets/**",
          "/*.(svg|cur|jpg|jpeg|png|apng|webp|avif|gif|otf|ttf|woff|woff2)"
        ]
      }
    }
  ],
  "dataGroups": [
    {
      "name": "api-fresh",
      "urls": ["/api/products/**", "/api/categories/**"],
      "cacheConfig": {
        "strategy": "freshness",
        "maxSize": 100,
        "maxAge": "1h",
        "timeout": "5s"
      }
    },
    {
      "name": "api-perf",
      "urls": ["/api/static-content/**", "/api/config/**"],
      "cacheConfig": {
        "strategy": "performance",
        "maxSize": 50,
        "maxAge": "1d"
      }
    },
    {
      "name": "api-user-data",
      "urls": ["/api/user/**", "/api/orders/**"],
      "cacheConfig": {
        "strategy": "freshness",
        "maxSize": 30,
        "maxAge": "10m",
        "timeout": "3s"
      }
    }
  ]
}
```

### Asset groups — `installMode` and `updateMode`

- **`prefetch`**: download eagerly when the SW installs. Uses network on first visit, but subsequent loads are instant even offline.
- **`lazy`**: download on first request. Doesn't consume bandwidth for assets the user might not need.

**App shell (HTML/JS/CSS) → `prefetch`** — you always want the app to boot offline.
**Non-critical assets (images not on the home page) → `lazy`** — save bandwidth for users who never visit those pages.

`updateMode` controls what happens when the SW detects a new version:
- **`prefetch`** — download the new version immediately in the background
- **`lazy`** — download when the user next requests them (default if omitted)

For app-shell files, `prefetch` on updates too — you want the new version ready to activate.

### Data groups — `freshness` vs `performance` strategies

**`freshness`**: try network first, fall back to cache. Fresh data when online; cache is the offline safety net.

Use for: user-specific data, live content (product catalogs that change often), anything the user expects to be current.

The `timeout` field caps how long to wait for the network before serving the cache. `"5s"` is typical — 5 seconds of "connecting…" is the boundary between "app is loading" and "app is broken."

**`performance`**: try cache first, fall back to network. Fast reads; data can be slightly stale.

Use for: static reference data (list of countries, currencies), infrequently-changing content, config endpoints.

### `maxSize` and `maxAge`

- **`maxSize`**: how many responses to keep in this cache. Beyond this, oldest entries are evicted (LRU).
- **`maxAge`**: how long to keep responses at all. Beyond this, evict regardless of size.

Duration strings: `"1h"`, `"30m"`, `"7d"`, `"1u"` (microseconds), and so on.

**Set both.** Only `maxSize` and a huge, rarely-invalidated user might carry gigabytes of stale data. Only `maxAge` and a chatty API might blow past browser storage limits.

---

## Connection state — the signal-based service

Components need to know when the user is offline to show hints ("Working offline — changes will sync when you reconnect"). `navigator.onLine` is the browser's answer, but it lies:

- `navigator.onLine === true` when the device is on a wifi network — even if that wifi has no internet
- `navigator.onLine === false` fires when the physical adapter is disconnected — but doesn't fire for VPN drops, DNS failures, or captive-portal captures

For a real "am I reachable" check, ping your server periodically. Combine both signals:

```typescript
// File: services/connection.service.ts
import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { fromEvent, interval, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Injectable({ providedIn: 'root' })
export class ConnectionService {
  private readonly http = inject(HttpClient);
  private readonly _navigatorOnline = signal(navigator.onLine);
  private readonly _serverReachable = signal<boolean | null>(null);  // null = not yet checked

  /** True only if BOTH navigator says online AND we can reach the server. */
  readonly online = computed(() =>
    this._navigatorOnline() && (this._serverReachable() !== false),
  );

  readonly offline = computed(() => !this.online());

  /** Explicit "definitely offline per navigator" — no server check needed. */
  readonly navigatorOffline = computed(() => !this._navigatorOnline());

  constructor() {
    fromEvent(window, 'online').pipe(
      takeUntilDestroyed(),
    ).subscribe(() => {
      this._navigatorOnline.set(true);
      // Immediately verify the server is actually reachable
      this.pingServer();
    });

    fromEvent(window, 'offline').pipe(
      takeUntilDestroyed(),
    ).subscribe(() => {
      this._navigatorOnline.set(false);
      this._serverReachable.set(false);
    });

    // Periodic reachability check — catches VPN drops, DNS failures, etc.
    interval(30_000).pipe(
      switchMap(() => this.checkServer()),
      takeUntilDestroyed(),
    ).subscribe(reachable => this._serverReachable.set(reachable));

    // Initial check on startup
    this.pingServer();
  }

  /** Trigger a one-shot ping; useful after mutations succeed/fail. */
  pingServer(): void {
    this.checkServer().subscribe(reachable => {
      this._serverReachable.set(reachable);
    });
  }

  private checkServer() {
    return this.http.head('/api/health', { observe: 'response' }).pipe(
      map(response => response.status < 500),
      catchError(() => of(false)),
    );
  }
}
```

**Four things doing the work:**

- **`_navigatorOnline`** tracks `navigator.onLine`, updated via the `online`/`offline` events. Fast and cheap; catches the physical-adapter case.
- **`_serverReachable`** tracks whether an actual API call succeeds. Slower but authoritative for "can I actually reach the server."
- **`computed(() => nav && server)`** — the public `online` signal requires both. If either says "no," we're offline. If server hasn't been checked yet (`null`), we trust the navigator alone.
- **`HEAD /api/health`** — lightweight; server doesn't need to send a body. `< 500` status counts as reachable; a 4xx from a health endpoint is still "server is up but rejecting requests," which is a different problem than "no connection."

### Using it in components

```typescript
@Component({
  template: `
    @if (connection.offline()) {
      <div class="offline-banner">
        You're offline. Changes will sync when you reconnect.
      </div>
    }
    @if (queue.queueSize() > 0) {
      <div class="pending-banner">
        {{ queue.queueSize() }} pending action(s) waiting to sync
      </div>
    }
  `,
})
export class ShellComponent {
  protected readonly connection = inject(ConnectionService);
  protected readonly queue = inject(OfflineMutationQueue);
}
```

Reactive signal reads; no async pipe, no subscribe.

---

## The offline mutation queue

The heart of the recipe. When a user attempts a mutation while offline, don't fail — queue it. When connection returns, replay the queue. Combine with the optimistic-updates pattern so the UI feels instant even during the offline window.

```typescript
// File: services/offline-mutation-queue.service.ts
import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ConnectionService } from './connection.service';

export interface PendingMutation {
  id: string;
  type: string;           // human-readable label — "place-order", "update-profile"
  url: string;
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  createdAt: number;
  attempts: number;
  lastError?: string;
}

const STORAGE_KEY = 'offline-mutation-queue';
const MAX_ATTEMPTS = 5;

@Injectable({ providedIn: 'root' })
export class OfflineMutationQueue {
  private readonly http = inject(HttpClient);
  private readonly connection = inject(ConnectionService);

  private readonly _queue = signal<PendingMutation[]>([]);
  readonly queue = this._queue.asReadonly();
  readonly queueSize = computed(() => this._queue().length);
  readonly hasPending = computed(() => this._queue().length > 0);

  private processing = false;

  constructor() {
    this.restoreFromStorage();

    // Persist on every change
    effect(() => {
      const q = this._queue();
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(q));
      } catch (err) {
        // Storage may be full or in private mode; queue lives in memory only
        console.warn('Could not persist offline mutation queue', err);
      }
    });

    // When we come online AND have pending mutations, drain the queue
    effect(() => {
      if (this.connection.online() && this._queue().length > 0) {
        void this.processQueue();
      }
    });
  }

  /**
   * Enqueue a mutation. If online, it fires immediately; if offline, it waits.
   * Returns the mutation ID so callers can track it (e.g., for optimistic UI cleanup).
   */
  enqueue(mutation: Omit<PendingMutation, 'id' | 'createdAt' | 'attempts'>): string {
    const full: PendingMutation = {
      ...mutation,
      id: crypto.randomUUID(),
      createdAt: Date.now(),
      attempts: 0,
    };

    this._queue.update(current => [...current, full]);
    return full.id;
  }

  /** Remove a mutation from the queue (e.g., after user "gives up" on a stuck one). */
  cancel(id: string): void {
    this._queue.update(current => current.filter(m => m.id !== id));
  }

  clear(): void {
    this._queue.set([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  private async processQueue(): Promise<void> {
    if (this.processing) return;
    this.processing = true;

    try {
      // Process serially to preserve order (a PUT followed by a DELETE
      // should NOT run in parallel — order matters)
      while (this._queue().length > 0 && this.connection.online()) {
        const [next, ...rest] = this._queue();
        const success = await this.execute(next);

        if (success) {
          this._queue.set(rest);
        } else {
          // Failed with a retryable error — bump attempts, stop processing,
          // wait for the next connection change to retry
          this._queue.update(current =>
            current.map(m =>
              m.id === next.id
                ? { ...m, attempts: m.attempts + 1 }
                : m,
            ),
          );

          if (next.attempts + 1 >= MAX_ATTEMPTS) {
            // Give up on this specific mutation
            this._queue.update(current =>
              current.filter(m => m.id !== next.id),
            );
            this.emitFailure(next);
          }
          break;
        }
      }
    } finally {
      this.processing = false;
    }
  }

  private async execute(mutation: PendingMutation): Promise<boolean> {
    try {
      await firstValueFrom(
        this.http.request(mutation.method, mutation.url, {
          body: mutation.body,
          headers: mutation.headers,
        }),
      );
      return true;
    } catch (err) {
      if (err instanceof HttpErrorResponse) {
        // 4xx errors (except 408, 429) are NOT retryable — the request itself
        // is bad. Drop from queue.
        if (err.status >= 400 && err.status < 500 && err.status !== 408 && err.status !== 429) {
          this._queue.update(current => current.filter(m => m.id !== mutation.id));
          this.emitFailure(mutation, err);
          return true;  // "handled" — remove from queue
        }
      }
      return false;
    }
  }

  private emitFailure(mutation: PendingMutation, err?: unknown): void {
    // Emit an event so UI can show a toast / user notification
    // Could be a Subject<{mutation, error}> on this service
    console.error('Mutation failed permanently', mutation.type, err);
  }

  private restoreFromStorage(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return;
      const parsed = JSON.parse(stored) as PendingMutation[];
      if (Array.isArray(parsed)) {
        this._queue.set(parsed);
      }
    } catch (err) {
      // Corrupt data; discard
      localStorage.removeItem(STORAGE_KEY);
      console.warn('Could not restore offline mutation queue', err);
    }
  }
}
```

**Seven patterns worth absorbing:**

- **`localStorage` for queue persistence.** The queue survives page reloads. User can close the tab mid-offline and reopen it later; the pending mutations are still there.
- **`effect()` for auto-persist and auto-drain.** Whenever the queue signal changes, the effect writes to localStorage. Whenever the connection signal changes to online with pending items, another effect drains. No manual subscribe/unsubscribe.
- **Serial processing (`while` loop with `await`).** Mutations are processed in FIFO order. A PUT followed by a DELETE must not run in parallel — order matters for correctness. Contrast with the retry-with-backoff pattern where individual requests are independent.
- **Retryable-error taxonomy.** 5xx and network errors → keep in queue, retry. 4xx (except 408/429) → the request itself is invalid, dropping it. Same taxonomy as [`retry-with-backoff`](../http/retry-with-backoff.md).
- **`MAX_ATTEMPTS = 5`** with permanent-failure emission. If a mutation fails 5 times in a row despite the network being available, something is genuinely wrong; give up rather than looping forever. UI shows a "This action could not be completed" notification.
- **`this.processing` flag prevents concurrent drain calls.** Two connection-change events firing in quick succession would otherwise call `processQueue` twice; the flag ensures only one drainer runs at a time.
- **`Omit<PendingMutation, 'id' | 'createdAt' | 'attempts'>`** in `enqueue()`. Consumers pass the intent; the service assigns the ID, timestamp, and initial attempt count. Types stay clean.

### Usage — composing with optimistic UI

```typescript
@Injectable({ providedIn: 'root' })
export class OrderService {
  private readonly queue = inject(OfflineMutationQueue);
  private readonly cart = inject(CartService);
  private readonly notifications = inject(NotificationService);

  placeOrder(items: CartItem[]): void {
    const idempotencyKey = crypto.randomUUID();

    // Snapshot for potential rollback
    const cartBefore = this.cart.cartItems();

    // Optimistic: clear the cart immediately (feels instant to user)
    this.cart.clear();

    // Enqueue the actual API call
    this.queue.enqueue({
      type: 'place-order',
      url: '/api/orders',
      method: 'POST',
      body: { items, idempotencyKey },
      headers: {
        'Idempotency-Key': idempotencyKey,  // server dedupes retries
      },
    });

    this.notifications.info('Order queued — will be placed when online');
    // The queue picks up processing automatically when online.
  }
}
```

**The `Idempotency-Key` header is essential.** The queue might retry a POST several times (e.g., initial network error causes retry, but the request actually reached the server and processed the first time). Without the key, retries create duplicate orders. With the key, the server recognizes the retry and returns the previously-successful response. Covered in detail in the [retry-with-backoff recipe](../http/retry-with-backoff.md).

The composition is:

1. User taps "Place Order" → `OrderService.placeOrder()`
2. Cart clears optimistically → user sees "Order Placed" state
3. Queue enqueues the POST
4. If online → queue drains immediately → server responds → order confirmed
5. If offline → queue holds → user goes about their day
6. Connection returns → effect fires → queue drains → server responds → order lands with idempotency dedup ensuring no double-orders

---

## App version updates — the "Refresh to update" UX

When you deploy a new version, the service worker downloads it in the background but doesn't activate it until the user reloads. Without a UI cue, users can run on old code for days.

```typescript
// File: services/version-update.service.ts
import { Injectable, inject, signal } from '@angular/core';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter, interval } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Injectable({ providedIn: 'root' })
export class VersionUpdateService {
  private readonly updates = inject(SwUpdate);
  private readonly _updateAvailable = signal(false);

  readonly updateAvailable = this._updateAvailable.asReadonly();

  constructor() {
    if (!this.updates.isEnabled) return;

    // Listen for new versions
    this.updates.versionUpdates.pipe(
      filter((evt): evt is VersionReadyEvent => evt.type === 'VERSION_READY'),
      takeUntilDestroyed(),
    ).subscribe(() => {
      this._updateAvailable.set(true);
    });

    // Poll for updates every 6 hours — catches long-open tabs
    interval(6 * 60 * 60 * 1000).pipe(
      takeUntilDestroyed(),
    ).subscribe(() => {
      this.updates.checkForUpdate().catch(err =>
        console.warn('Update check failed', err),
      );
    });
  }

  async applyUpdate(): Promise<void> {
    try {
      await this.updates.activateUpdate();
      document.location.reload();
    } catch (err) {
      console.error('Could not activate update', err);
    }
  }
}
```

UI banner:

```html
@if (versionUpdate.updateAvailable()) {
  <div class="update-banner">
    A new version of the app is available.
    <button (click)="versionUpdate.applyUpdate()">Refresh to update</button>
  </div>
}
```

**Three things worth absorbing:**

- **`SwUpdate.isEnabled`** — false in dev or when SW isn't installed. Always check before subscribing.
- **`VERSION_READY` event** — the SW downloaded the new version and it's ready to activate. Different from `VERSION_DETECTED` (still downloading).
- **6-hour polling** — for users who leave the app open for days. Without an explicit `checkForUpdate` call, they only get notified when the SW happens to check on its own (which is unpredictable).

### The "force reload after N hours" variation

Some apps can't afford drift between clients. If two users are collaborating and one is on v1.4.0 while the other is on v1.5.0, the older client might send malformed data.

```typescript
// If the update has been available for > 24h without a user refresh, force it
private updateAvailableSince: number | null = null;

// In the versionUpdates subscription:
this._updateAvailable.set(true);
this.updateAvailableSince = Date.now();

interval(60 * 60 * 1000).pipe(  // check hourly
  takeUntilDestroyed(),
).subscribe(() => {
  if (
    this._updateAvailable() &&
    this.updateAvailableSince &&
    Date.now() - this.updateAvailableSince > 24 * 60 * 60 * 1000
  ) {
    // 24 hours passed — force reload
    this.applyUpdate();
  }
});
```

Aggressive; use sparingly. Users mid-form-fill lose their input when the page reloads. Weigh the drift risk against the disruption.

---

## Handling auth in cached responses

The service worker caches API responses. If a user logs out and another logs in, cached responses from the previous user could leak.

**Fix — clear the SW cache on logout:**

```typescript
// In AuthService.logout():
async logout(): Promise<void> {
  await firstValueFrom(this.http.post('/api/auth/logout', {}, { withCredentials: true }));

  // Clear service worker caches
  if ('caches' in window) {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
  }

  // Clear the offline mutation queue too — pending mutations were for the old user
  this.mutationQueue.clear();

  this.tokenService.clear();
  this.router.navigate(['/login']);
}
```

The `caches.keys()` / `caches.delete()` APIs are native browser APIs, not Angular-specific. They clear all SW caches, forcing fresh fetches for every subsequent request.

**For finer-grained control**, filter by cache name — Angular SW names its caches with a pattern like `ngsw:1:data:dynamic:api-user-data:cache`. Match the pattern and delete only user-specific caches.

---

## Trade-offs and common pitfalls

**Use service worker + offline queue when:**

- Users have real-world offline scenarios (mobile, field work, unreliable networks)
- Mutations are valuable enough to be worth retrying (orders, saves, key user actions)
- The app can meaningfully function with cached data (browsable content, personal data the user already has)

**Skip when:**

- The app is inherently online-only (real-time collab tool with no offline meaning, live trading)
- The user base is on stable networks with high bandwidth
- The engineering cost of testing offline flows exceeds the value

### Common pitfalls

- **Enabling the service worker in dev mode.** Live-reload and SW cache fight; you get maddeningly stale code. Always `enabled: !isDevMode()`.
- **Trusting `navigator.onLine` alone.** The device might be on wifi with no internet, on a VPN that just dropped, behind a captive portal. Ping the server periodically.
- **Missing `Idempotency-Key` on queued mutations.** The queue may retry; without the key, retries duplicate the action. Payments, sends, and any state-changing POST must include an idempotency key.
- **Caching auth tokens in localStorage alongside the queue.** Cross-user leaks. Store auth tokens in memory (per the [token-storage-security recipe](../auth/token-storage-security.md)); the queue can store whatever the request needed, but auth tokens should be re-attached at execute time from current state.
- **Not clearing SW cache on logout.** Cached responses for User A leak to User B on the same browser. The `caches.delete()` sweep is essential.
- **`performance` strategy on user-specific data.** Stale user data feels broken ("my new order isn't showing up!"). User data → `freshness` with a short `maxAge`.
- **`freshness` with no `timeout`.** The user sees a loading spinner for 30 seconds while a slow network hangs. Always set a reasonable `timeout` (3-5 seconds) so offline detection is fast.
- **No `maxSize` on data groups.** Cache grows unbounded over long sessions; browser eventually starts evicting other things. Always set both `maxSize` and `maxAge`.
- **Enqueueing without capping queue size.** A user offline for a week could accumulate 10,000 queued mutations. If your app has any risk of high-volume offline usage, cap the queue (say, 500 items) and warn the user when they hit the cap.
- **Applying updates without warning.** Force-reloading an active tab loses form input, scroll position, and open modals. Prefer the banner + user-triggered refresh, or check for unsaved work before force-reload.
- **Testing offline in dev.** Chrome DevTools' Network → Offline throttling works, but Angular DevTools' HMR interferes. Test offline behavior against production builds served locally.
- **Assuming the SW is registered.** `SwUpdate.isEnabled` is false if registration failed, if the file is missing, or if HTTPS is misconfigured. Always check before subscribing to `versionUpdates`.
- **Cache-Control conflicts.** The SW respects HTTP `Cache-Control` headers by default. A server sending `Cache-Control: no-store` on API responses will prevent the SW from caching them at all — even though your ngsw-config says to cache. Coordinate with the backend.
- **Not testing "app just deployed" scenarios.** A user has the app open when you deploy v1.5.0. The banner appears. They click Refresh. If the reload happens mid-mutation, the queue might drain to the new version's schema, which might be different. Test schema-migration scenarios explicitly.

---

## See also

- [Optimistic Updates](../forms-and-search/optimistic-updates.md) — the pending-operation queue pattern this recipe extends with persistence
- [Retry with Backoff](../http/retry-with-backoff.md) — the retryable-error taxonomy and idempotency-key pattern the queue depends on
- [Token Storage Security](../auth/token-storage-security.md) — token-handling context; the cache-clear-on-logout pattern comes from here
- [Race Conditions](../reactivity/race-conditions.md) — the queue's serial processing avoids many of these; still worth reading
- [Component Communication](../components/component-communication.md) — the `ConnectionService` pattern is a direct application of the "shared service with signals" pattern
- [HTTP](../../http/http.md) — `HttpClient` fundamentals

## References

- [Angular Service Worker (angular.dev)](https://angular.dev/ecosystem/service-workers) — the official documentation
- [`ngsw-config.json` schema (angular.dev)](https://angular.dev/ecosystem/service-workers/config)
- [`SwUpdate` API (angular.dev)](https://angular.dev/api/service-worker/SwUpdate) — the update service
- [`SwPush` API (angular.dev)](https://angular.dev/api/service-worker/SwPush) — for push notifications (separate topic from this recipe)
- [Cache API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Cache) — the browser primitive the SW uses internally
- [Background Sync (web.dev)](https://web.dev/articles/background-sync) — for even more robust offline mutation replay (browser-level, not just app-level)
- [Workbox](https://developer.chrome.com/docs/workbox/) — Google's more flexible SW library, if you outgrow the Angular SW's declarative model

## Demo source

Synthesized from common production PWA patterns rather than a single demo file. The three-layer architecture (app shell + API cache + mutation queue) reflects the structure most teams converge on once they hit "our users have real-world offline scenarios." The composition with idempotency keys, optimistic UI, and the retry taxonomy makes the offline queue robust enough for money-touching mutations, not just conveniences. All code is original.
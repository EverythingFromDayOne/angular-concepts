---
recipe_id: "request-deduplication"
title: "Request Deduplication: One Call When Five Would Fire"
file: "recipes/http/request-deduplication.md"
primary_concept: "http/http"
related_concepts: ["http/interceptors", "reactivity/rxjs/rxjs", "reactivity/signals"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Request Deduplication: One Call When Five Would Fire

> **What you'll build:** a deduplication layer that catches the case where
> multiple components, services, or guards independently request the same
> resource at the same time — and makes them share one HTTP call instead
> of firing five identical ones. Three implementation patterns (per-call
> helper, service-level methods, global interceptor) and the rules for
> when each one applies.
>
> **Concepts you'll touch:** [HTTP](../../http/http.md), [HTTP Interceptors](../../http/interceptors.md), [RxJS](../../reactivity/rxjs/rxjs.md), [Signals](../../reactivity/signals.md)
>
> **Time:** ~20 minutes to read; ~1 hour to identify the duplicated
> requests in your own app via the Network tab.

---

## The scenario

A user lands on the dashboard. You open Chrome DevTools' Network tab. You see five `GET /api/user/me` requests fire within the same 200ms.

What's happening: the header component reads the current user (for the avatar). The sidebar reads the current user (for the welcome message). The settings link reads the current user (for permission checks). A route guard reads the current user (for `canActivate`). An analytics service reads the current user (for the trace tag). Each one independently calls `this.userService.getCurrentUser()`. Each call hits `this.http.get('/api/user/me')`. Five identical round trips.

The data is the same. The server returns identical responses. The client could be smarter — let the first request finish, and let the other four read its result.

This recipe is about making the client smarter. It's a small architectural change (one shared service or one interceptor) with measurable wins: lower server load, faster page paint, reduced battery on mobile, and the elimination of a class of bugs that come from the responses arriving in different orders.

---

## The primitive — `shareReplay`

The RxJS operator that does the actual work is **`shareReplay`**. It turns a "cold" observable (each subscription triggers a new execution) into a "hot" multicast observable (subscriptions share the execution). The first subscriber triggers the work; subsequent subscribers receive the same emissions without re-triggering.

```typescript
const cached$ = this.http.get<User>('/api/user/me').pipe(
  shareReplay({ bufferSize: 1, refCount: true }),
);

// First subscription — triggers the HTTP call
cached$.subscribe(user => console.log('A', user));

// Second subscription within 10ms — receives the same response when it lands
cached$.subscribe(user => console.log('B', user));

// Network panel shows ONE /api/user/me request, not two.
```

Two config knobs matter:

- **`bufferSize: 1`** — replay the last value to late subscribers. For HTTP responses, the response is the only value emitted; `1` captures it.
- **`refCount: true`** — when all subscribers unsubscribe, the underlying source unsubscribes too. Set to `false` if you want the cache to persist after subscribers leave.

`shareReplay` alone gives you per-observable deduplication. To dedupe across components — same URL, different observables — you need a **registry** that maps from "request fingerprint" to a shared observable.

---

## Pattern 1 — per-call helper

The smallest implementation: a generic function plus a `Map` for the registry. Drop-in usage at the call site:

```typescript
// File: utils/dedupe.ts
import { Observable, finalize, shareReplay, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

const registry = new Map<string, Observable<unknown>>();

/**
 * Wrap an Observable so that concurrent calls for the same key share one execution.
 * The cache entry is automatically removed when:
 *   - all current subscribers unsubscribe (refCount: true)
 *   - the request errors (so a retry will re-fetch)
 *   - explicitly via `invalidate(key)`
 */
export function dedupe<T>(
  key: string,
  factory: () => Observable<T>,
): Observable<T> {
  const existing = registry.get(key);
  if (existing) {
    return existing as Observable<T>;
  }

  const shared = factory().pipe(
    shareReplay({ bufferSize: 1, refCount: true }),
    finalize(() => registry.delete(key)),
    catchError(err => {
      registry.delete(key);
      return throwError(() => err);
    }),
  );

  registry.set(key, shared);
  return shared;
}

export function invalidate(key: string): void {
  registry.delete(key);
}
```

Usage at any call site:

```typescript
@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);

  getCurrentUser(): Observable<User> {
    return dedupe('user:me', () => this.http.get<User>('/api/user/me'));
  }
}
```

Five components calling `userService.getCurrentUser()` within the same tick:
- The first call: registry miss, builds the shared observable, kicks off the HTTP request, stores in registry.
- Calls 2–5: registry hit, return the same observable. Each subscribes; `shareReplay` multicasts.
- All five receive the same response when it lands.
- After all five unsubscribe, `finalize` runs and deletes the registry entry. The next request triggers a fresh HTTP call.

**This is in-flight deduplication, not caching.** Once everyone leaves, the entry is gone. Same URL fetched a minute later → new request. For long-term caching, see Pattern 2.

---

## Pattern 2 — service-level methods with TTL caching

For data that's stable over short windows — user profile, configuration, lookup tables — dedup-plus-TTL gives you both "share concurrent calls" AND "skip the call entirely within the cache window":

```typescript
// File: services/user.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay, throwError, timer } from 'rxjs';
import { catchError, takeUntil } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);
  private readonly cache = new Map<string, Observable<unknown>>();
  private readonly DEFAULT_TTL_MS = 5 * 60 * 1000;  // 5 minutes

  getCurrentUser(): Observable<User> {
    return this.cached('user:me', () => this.http.get<User>('/api/user/me'));
  }

  getDepartments(): Observable<Department[]> {
    return this.cached(
      'departments',
      () => this.http.get<Department[]>('/api/departments'),
      60 * 60 * 1000,  // 1 hour — rarely changes
    );
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  invalidateAll(): void {
    this.cache.clear();
  }

  private cached<T>(
    key: string,
    factory: () => Observable<T>,
    ttlMs = this.DEFAULT_TTL_MS,
  ): Observable<T> {
    const existing = this.cache.get(key);
    if (existing) {
      return existing as Observable<T>;
    }

    const shared = factory().pipe(
      // refCount: false — keep the cache alive even after subscribers leave
      shareReplay({ bufferSize: 1, refCount: false, windowTime: ttlMs }),
      catchError(err => {
        // Don't cache errors — let the next attempt try fresh
        this.cache.delete(key);
        return throwError(() => err);
      }),
    );

    this.cache.set(key, shared);
    // Schedule manual eviction at TTL (windowTime above handles the data;
    // we also want to remove the Map entry so future subscribers re-run the factory)
    timer(ttlMs).subscribe(() => this.cache.delete(key));

    return shared;
  }
}
```

The key changes from Pattern 1:

- **`refCount: false`** — the cache survives when subscribers leave; subsequent calls within TTL hit the cache, no new request fires.
- **`windowTime: ttlMs`** — `shareReplay`'s built-in expiry; replays only emissions within the window.
- **Explicit `timer(ttlMs)` for Map cleanup** — `windowTime` keeps the data fresh but doesn't remove the Map entry; the timer does that so future calls hit `factory()` again.
- **`invalidate(key)` / `invalidateAll()`** — explicit eviction APIs for "the user just updated their profile, the cached `/api/user/me` is stale now."

### When to invalidate on mutations

The most common bug in cached-GET layers: the user does an action that changes server state, but the cached GET still returns the old data. The pattern: **invalidate the relevant cache key in the tap of the mutation**:

```typescript
updateProfile(updates: Partial<User>): Observable<User> {
  return this.http.patch<User>('/api/user/me', updates).pipe(
    tap(() => this.invalidate('user:me')),  // mutation forces re-fetch on next read
  );
}
```

This is more reliable than time-based invalidation for "I just changed it" cases — the user expects to see their change immediately. TTL is for "everyone else's changes might land eventually."

For sweeping invalidation: `logout()` should call `invalidateAll()` so no cached data leaks across sessions.

---

## Pattern 3 — global interceptor-level deduplication

For automatic deduplication across the entire app without touching individual services, an interceptor catches every GET and applies dedup based on URL + params:

```typescript
// File: interceptors/dedup.interceptor.ts
import {
  HttpEvent,
  HttpInterceptorFn,
  HttpRequest,
} from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, finalize, shareReplay, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class HttpDedupRegistry {
  private readonly inflight = new Map<string, Observable<HttpEvent<unknown>>>();

  share(
    key: string,
    request$: Observable<HttpEvent<unknown>>,
  ): Observable<HttpEvent<unknown>> {
    const existing = this.inflight.get(key);
    if (existing) return existing;

    const shared = request$.pipe(
      shareReplay({ bufferSize: 1, refCount: true }),
      finalize(() => this.inflight.delete(key)),
      catchError(err => {
        this.inflight.delete(key);
        return throwError(() => err);
      }),
    );

    this.inflight.set(key, shared);
    return shared;
  }
}

export const dedupInterceptor: HttpInterceptorFn = (req, next) => {
  // Only dedupe idempotent reads. POST/PUT/DELETE responses are typically
  // unique to the call and shouldn't be shared.
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    return next(req);
  }

  // Skip dedup for endpoints that need it bypassed (e.g., long-polling).
  if (req.headers.has('X-No-Dedup')) {
    return next(req.clone({ headers: req.headers.delete('X-No-Dedup') }));
  }

  const registry = inject(HttpDedupRegistry);
  const key = buildKey(req);

  return registry.share(key, next(req));
};

function buildKey(req: HttpRequest<unknown>): string {
  // URL + params + the auth token's user identity prevent cross-user collisions.
  // For simple apps, just URL + params is enough.
  return `${req.method}:${req.urlWithParams}`;
}
```

Registered alongside the other interceptors:

```typescript
// File: app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withInterceptors([
        dedupInterceptor,    // outer: dedup before retry kicks in
        retryInterceptor,
        authInterceptor,
      ]),
    ),
  ],
};
```

**Interceptor ordering matters** (covered in the [retry recipe](./retry-with-backoff.md)). `dedupInterceptor` outermost means: if five components ask for the same URL, the interceptor sees five separate calls but the registry returns the same observable. The retry interceptor (one layer in) sees only one — so retries are also shared. The auth interceptor (innermost) sees the actual HTTP request, fires once.

### The auth-token gotcha

If your app has multiple authenticated identities (account switcher, "impersonate user" tooling), the cache key needs to include the current user identity:

```typescript
function buildKey(req: HttpRequest<unknown>, tokenService: TokenService): string {
  const userIdentity = tokenService.getCurrentUserIdHash() ?? 'anonymous';
  return `${userIdentity}:${req.method}:${req.urlWithParams}`;
}
```

Otherwise: User A's `/api/user/me` response gets cached under a key. User A logs out, User B logs in. User B's request hits the same key and gets User A's response. Cross-user data leak.

For single-identity apps, this isn't a concern — but invalidate on logout regardless:

```typescript
// In AuthService.logout():
inject(HttpDedupRegistry).clear();  // expose a clear() method
```

---

## Dedup vs SWR vs simple caching — the decision matrix

The three patterns sound similar but solve different problems:

| Pattern | What it does | When to use |
| --- | --- | --- |
| **Dedup (no TTL)** | Multiple concurrent calls for the same key → one shared execution. After all subscribers leave, the next call is fresh. | Components on the same page each independently fetching the same data within the same tick. The "page-load thundering herd." |
| **Dedup + TTL** | Same as above, but the cache survives for a window. Calls within the window skip the HTTP entirely. | Data that's stable for minutes — user profile, department list, currency rates, app config. |
| **SWR (stale-while-revalidate)** | Always return cache immediately, then fetch in the background, then update. | Data where instant render matters more than freshness — feed, search results, dashboards visited often. See the [search-engine recipe](../forms-and-search/search-engine.md). |

You can layer them. The user-service in Pattern 2 already combines dedup (concurrent calls share) with TTL caching (skip the call entirely for N minutes). Adding SWR on top would mean: return cached data instantly, fire a background fetch, update reactively when fresh data arrives.

For most apps, the right starting point is **Pattern 2 — dedup + TTL — at the service level for stable data**, and **Pattern 3 — the interceptor — as a safety net**. Pattern 1 (the per-call helper) is for cases that don't naturally live in a service method.

---

## Composition with retry

The deduplication interceptor sits **outside** the retry interceptor — covered earlier in [retry recipe](./retry-with-backoff.md). The effect:

```text
5 components subscribe to /api/user/me
                ▼
[dedupInterceptor]  ← sees 5 calls, returns the SAME observable to all 5
                ▼
[retryInterceptor]  ← sees 1 call, applies retry policy
                ▼
[authInterceptor]   ← sees 1 call, attaches token
                ▼
   network         ← 1 actual HTTP request
```

If the request fails and the retry kicks in, **one retry chain runs for all five subscribers.** They all see the same retry attempts, the same delays, the same final result. Without dedup, each of the five would independently retry — five retry chains, with five attempts each, potentially 25 requests for what should be one.

---

## Variations

### Conditional dedup — opt out per call

Add a header to opt out for specific calls:

```typescript
this.http.get('/api/events/long-poll', {
  headers: { 'X-No-Dedup': '1' },
}).subscribe(/* … */);
```

The interceptor checks for the header and skips deduplication. Useful for long-poll endpoints (where the response is unique each time) or for endpoints that the developer knows shouldn't be shared.

### Selective TTL based on response cache headers

Some servers tell you how long their data is good for via `Cache-Control: max-age=N`. A more sophisticated interceptor reads the response headers and sets per-key TTL accordingly:

```typescript
const tap_set_ttl = tap<HttpResponse<unknown>>(response => {
  if (response.type !== HttpEventType.Response) return;
  const cacheControl = response.headers.get('Cache-Control') ?? '';
  const maxAge = parseMaxAge(cacheControl);
  if (maxAge !== null) {
    // Schedule eviction at the server-suggested TTL
    timer(maxAge * 1000).subscribe(() => registry.delete(key));
  }
});
```

Trade-off: respecting server hints is cleaner, but it makes the interceptor's behavior less predictable from the client side. For most apps, client-side TTL on stable endpoints is enough.

### Smart invalidation via tag-based eviction

For sophisticated apps with interrelated resources (Twitter-style), tags let you invalidate groups:

```typescript
@Injectable({ providedIn: 'root' })
export class CacheRegistry {
  private readonly entries = new Map<string, CacheEntry>();
  private readonly tagsToKeys = new Map<string, Set<string>>();

  put<T>(key: string, value$: Observable<T>, tags: string[]): void {
    // Add to entries
    this.entries.set(key, /* … */);
    // Track which tags this key belongs to
    for (const tag of tags) {
      if (!this.tagsToKeys.has(tag)) {
        this.tagsToKeys.set(tag, new Set());
      }
      this.tagsToKeys.get(tag)!.add(key);
    }
  }

  invalidateTag(tag: string): void {
    const keys = this.tagsToKeys.get(tag);
    if (!keys) return;
    for (const key of keys) {
      this.entries.delete(key);
    }
    this.tagsToKeys.delete(tag);
  }
}

// Usage:
this.cacheRegistry.put('user:me', userObs, ['user', 'user:me']);
this.cacheRegistry.put('users:list', usersObs, ['user', 'users:list']);

// User updates their profile:
this.cacheRegistry.invalidateTag('user');
// Both 'user:me' and 'users:list' are evicted
```

This is the React Query / RTK Query pattern. For Angular apps complex enough to need it, building a small layer like this is straightforward; for simpler apps, key-by-key invalidation is enough.

---

## Trade-offs and common pitfalls

**Use deduplication when:**

- The Network tab shows duplicate GETs for the same URL within the same tick
- Multiple components or guards independently call the same service method
- An interceptor-level optimization is reasonable (low risk of cross-call contamination)

**Skip dedup when:**

- The "duplicates" are actually different requests (different headers, different intent) that just happen to share a URL
- The data must be fresh on every read (live trading prices, lock acquisition)
- The endpoint is non-idempotent (POST/PUT/DELETE) — different requests should be distinct

### Common pitfalls

- **Caching error responses.** A failed call gets cached; subsequent calls return the cached failure instead of retrying. The fix: `catchError` deletes the cache entry. Both Pattern 1 and Pattern 2 above do this; don't omit it.
- **Stale data after mutations.** User updates their profile; the cached `/api/user/me` still shows old data. Fix: invalidate the relevant key in the `tap` of the mutation.
- **Cross-user cache leaks.** User A logs out, User B logs in. B's request for `/api/user/me` hits the cache and gets A's data. Fix: include the user identity in the cache key, AND invalidate the entire cache on logout.
- **Caching POST/PUT/DELETE.** Don't. They're not idempotent; each call has its own intent (place order #1, place order #2). The Pattern 3 interceptor explicitly checks `req.method !== 'GET'` to avoid this.
- **`shareReplay({ refCount: false })` with no TTL.** Cache entries never evict. Memory grows unbounded over a long session. Always pair `refCount: false` with either a TTL timer or an explicit invalidation API.
- **`bufferSize` larger than 1 for HTTP.** HTTP responses emit once. `bufferSize: 1` is the right value; larger wastes memory and complicates late-subscriber semantics.
- **Cache key that ignores params.** `/api/users?role=admin` and `/api/users?role=member` should not share. The interceptor uses `req.urlWithParams` (which includes the query string); custom builders need to do the same.
- **Cache key collision across body shapes.** For GETs you don't have a body; for POSTs you would, but we don't cache POSTs. If you somehow do, the body needs to be in the key (and you should think hard about whether you're solving the right problem).
- **Headers in the cache key when they shouldn't be.** `Authorization` is constant per session — fine to omit. `Accept-Language` varies per user preference — should be in the key if responses are locale-specific. Audit per-app.
- **Forgetting `finalize` cleanup in Pattern 1.** Without it, the Map grows over the session. The `finalize(() => registry.delete(key))` is the entry's "destructor" — load-bearing.

---

## See also

- [Retry with Backoff](./retry-with-backoff.md) — composes with dedup; the interceptor ordering story explains how one retry runs for N subscribers
- [Search Engine](../forms-and-search/search-engine.md) — the SWR pattern; complementary to dedup for different use cases
- [HTTP](../../http/http.md) — `HttpClient`, request configuration, interceptors overview
- [HTTP Interceptors](../../http/interceptors.md) — interceptor primitives in depth
- [RxJS — higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md) — `shareReplay`, multicast semantics

## References

- [`shareReplay` (RxJS)](https://rxjs.dev/api/operators/shareReplay) — the underlying primitive
- [RxJS Multicasting (RxJS guide)](https://rxjs.dev/guide/operators#multicasting-operators) — cold vs hot observables in depth
- [Stale-While-Revalidate (Vercel SWR docs)](https://swr.vercel.app/docs/getting-started) — the related-but-different pattern for comparison
- [TanStack Query (React)](https://tanstack.com/query/latest) — the reference implementation of cache + dedup + invalidation patterns; many ideas port directly

## Demo source

Synthesized from common production deduplication patterns rather than a single demo file. The three-tier architecture (per-call helper, service method with TTL, interceptor) reflects the structure most Angular apps converge on once they hit the "why is `/api/user/me` fetched five times" moment. All code is original.
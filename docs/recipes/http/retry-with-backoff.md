---
recipe_id: "retry-with-backoff"
title: "Retry with Backoff: Surviving Transient API Failures"
file: "recipes/http/retry-with-backoff.md"
primary_concept: "http/http"
related_concepts: ["http/interceptors", "reactivity/rxjs/rxjs-error-handling", "reactivity/signals"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Retry with Backoff: Surviving Transient API Failures

> **What you'll build:** a reusable `retryWithBackoff` operator and a
> safe-by-default HTTP interceptor that quietly retries failed requests
> when retrying might actually work — exponential delays with jitter, a
> hard cap on attempts, respect for the server's `Retry-After` header, and
> a strict policy on which errors are retryable vs which are terminal.
> Users only see an error toast after the system has genuinely given up.
>
> **Concepts you'll touch:** [HTTP](../../http/http.md), [HTTP Interceptors](../../http/interceptors.md), [RxJS error handling](../../reactivity/rxjs/rxjs-error-handling.md), [Signals](../../reactivity/signals.md)
>
> **Time:** ~25 minutes to read; ~1.5 hours to wire up and test against
> a real backend that you can artificially flake.

---

## The scenario

A user clicks "Refresh" on their dashboard. Five API calls fire in parallel. One of them gets unlucky — it lands on the API gateway during a deploy, returns 503. Your code surfaces "Something went wrong, please try again" as a toast.

The user clicks Refresh again three seconds later. Now everything works.

What just happened: a request that would have succeeded on retry **was treated as a permanent failure** because the code didn't know to try again. The user did the retrying manually. The toast was noise. The error metrics in your dashboard count this as a failure even though the system was working correctly two seconds later.

The fix is uniform across most apps: **retry transient failures automatically, surface terminal failures immediately, and never let the user notice a 503 that resolved itself.** The mechanics are simple; the policy choices are where the substance lives.

---

## The naive approach and why it fails

A first attempt at "just retry":

```typescript
this.http.get<User>('/api/me').pipe(
  retry(3),                       // try up to 3 more times
).subscribe(/* … */);
```

Three problems, each fatal in production:

1. **All errors are retried equally.** A `404 Not Found` is retried. A `400 Bad Request` from a validation error is retried. The retry can't fix either — but the user waits anyway, then sees the same error 3× later.

2. **No delay between retries.** All four attempts fire within milliseconds. If the failure was a rate-limited 429, this makes it worse. If the failure was a server restarting, it's still mid-restart on retry 3.

3. **The thundering-herd problem.** All five parallel requests retry simultaneously. The gateway that was struggling now gets 5× the load. Five users hitting refresh at the same instant amplifies further.

What's needed:

- **A retry decision** that distinguishes retryable from terminal errors
- **Backoff** — delay each retry, growing exponentially
- **Jitter** — randomize delays so parallel callers don't sync up
- **Respect for `Retry-After`** when the server explicitly says how long to wait
- **A cap** so we don't retry forever

---

## The retry decision — which errors are retryable

The policy isn't HTTP-status-based alone; it's about **whether retrying could plausibly help**. Some statuses are clearly transient; others are unambiguously the client's problem.

| Status | Retry? | Reason |
| --- | --- | --- |
| `0` (network error, CORS, abort) | Yes | Could be transient connectivity; worth retrying |
| `408` Request Timeout | Yes | Server didn't get the request in time; retry might land |
| `429` Too Many Requests | Yes | Rate-limited; respect `Retry-After`, but retry |
| `500` Internal Server Error | Yes | Generic 5xx; often transient |
| `502` Bad Gateway | Yes | Upstream blip; usually transient |
| `503` Service Unavailable | Yes | Often during deploys, restarts |
| `504` Gateway Timeout | Yes | Upstream too slow; retry might catch a healthier instance |
| `501` Not Implemented | No | Permanent — the server doesn't support this. Retrying won't change that. |
| `4xx` (other) | No | Client errors — 400, 401, 403, 404, 422. Retry won't fix the request itself. |
| `2xx` `3xx` | N/A | Not errors |

The decision function:

```typescript
// File: operators/retry-decision.ts
import { HttpErrorResponse } from '@angular/common/http';

const RETRYABLE_STATUSES = new Set([0, 408, 429, 500, 502, 503, 504]);

export function isRetryable(error: unknown): boolean {
  if (!(error instanceof HttpErrorResponse)) {
    // Non-HTTP errors (e.g., timeout from a downstream operator) — retry.
    // The caller can override this if they want stricter semantics.
    return true;
  }
  return RETRYABLE_STATUSES.has(error.status);
}
```

**Why 401 isn't in the retryable list.** Your auth interceptor handles 401 separately (the [JWT interceptor recipe](../auth/jwt-interceptor-circular-dep.md) walks through this). If a 401 surfaces past the auth interceptor's refresh-token machinery, it means the refresh itself failed — retrying won't help. Letting retry blindly retry a 401 would interfere with the auth flow.

**Why 403 isn't retryable.** Same reasoning: 403 either means lack of permission (won't change) or step-up required (handled by the [step-up recipe](../auth/step-up-authentication.md)). Either way, mechanical retry doesn't apply.

---

## Backoff math — exponential with jitter

The standard pattern is **exponential backoff with full jitter**: each attempt waits exponentially longer, plus a random offset to prevent multiple callers from syncing up after a shared failure event.

```typescript
// File: operators/backoff.ts

export interface BackoffConfig {
  baseDelayMs?: number;   // first retry waits this long
  maxDelayMs?: number;    // cap, regardless of attempt count
  jitterFactor?: number;  // 0 = no jitter; 0.5 = up to 50% added randomness
}

export function backoffDelay(
  attemptNumber: number,
  config: BackoffConfig = {},
): number {
  const { baseDelayMs = 200, maxDelayMs = 10_000, jitterFactor = 0.25 } = config;

  // Exponential: 200ms, 400ms, 800ms, 1600ms, …
  const exponential = baseDelayMs * Math.pow(2, attemptNumber);

  // Cap so a long-running retry chain doesn't end up waiting minutes
  const capped = Math.min(exponential, maxDelayMs);

  // Jitter: spread parallel callers out so they don't sync up on each retry
  const jitter = Math.random() * capped * jitterFactor;

  return capped + jitter;
}
```

A quick worked example with defaults (200ms base, 25% jitter):

| Attempt | Exponential | + Jitter (random 0–25%) | Actual delay |
| --- | --- | --- | --- |
| 1 | 200ms | 0–50ms | 200–250ms |
| 2 | 400ms | 0–100ms | 400–500ms |
| 3 | 800ms | 0–200ms | 800–1000ms |
| 4 | 1600ms | 0–400ms | 1600–2000ms |
| 5 | 3200ms | 0–800ms | 3200–4000ms |

Notice how each attempt's *range* widens. That's the jitter doing its job: even if 100 clients failed at the same millisecond, by attempt 3 they're spread across a 200ms window instead of all hitting the server simultaneously.

**Don't skip the jitter.** Without it, every client that failed at second 0 retries at second 0.2 exactly. The same gateway that was struggling now sees a synchronized retry storm at second 0.2. Jitter is the difference between "retry helps" and "retry causes a secondary outage."

---

## The operator

Wrap the decision and the backoff together using RxJS's modern `retry()` with the `delay` config — the delay function returns an Observable, which when it emits triggers a retry:

```typescript
// File: operators/retry-with-backoff.operator.ts
import {
  Observable,
  MonoTypeOperatorFunction,
  retry,
  timer,
  throwError,
} from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { isRetryable } from './retry-decision';
import { backoffDelay, type BackoffConfig } from './backoff';

export interface RetryConfig extends BackoffConfig {
  maxAttempts?: number;
  shouldRetry?: (error: unknown, attemptNumber: number) => boolean;
  onRetry?: (error: unknown, attemptNumber: number, delayMs: number) => void;
}

export function retryWithBackoff<T>(
  config: RetryConfig = {},
): MonoTypeOperatorFunction<T> {
  const {
    maxAttempts = 3,
    shouldRetry = isRetryable,
    onRetry,
    ...backoffConfig
  } = config;

  return source$ => source$.pipe(
    retry({
      count: maxAttempts,
      delay: (error, retryCount) => {
        // retryCount is 1-indexed: 1 on first retry, 2 on second, etc.
        if (!shouldRetry(error, retryCount)) {
          // Give up immediately — propagate the original error.
          return throwError(() => error);
        }

        // Honor Retry-After header if present (typically on 429).
        const headerDelay = getRetryAfterMs(error);
        const delayMs =
          headerDelay !== null
            ? headerDelay
            : backoffDelay(retryCount - 1, backoffConfig);

        onRetry?.(error, retryCount, delayMs);

        // timer emits once after delayMs, then completes — that emission
        // triggers the retry. If we returned EMPTY instead, retry would
        // give up; if we returned throwError, the error propagates.
        return timer(delayMs);
      },
    }),
  );
}

function getRetryAfterMs(error: unknown): number | null {
  if (!(error instanceof HttpErrorResponse)) return null;
  const value = error.headers.get('Retry-After');
  if (!value) return null;

  // Retry-After can be either a number of seconds or an HTTP-date
  const seconds = Number(value);
  if (!Number.isNaN(seconds)) return seconds * 1000;

  const dateMs = Date.parse(value);
  if (!Number.isNaN(dateMs)) return Math.max(0, dateMs - Date.now());

  return null;
}
```

**Three subtleties worth absorbing:**

- **`retry` with a `delay` function** is the modern (RxJS 7+) shape. The function receives `(error, retryCount)` and returns an Observable. If that Observable emits any value, the source is re-subscribed. If it errors, the error propagates without retrying. If it completes without emitting (e.g., `EMPTY`), retry gives up. `timer(ms)` is the right primitive — emit once after a delay, then complete.

- **The `onRetry` callback runs on every retry attempt**, before the delay starts. Components can use this to show "Retrying…" UI without coupling the operator to any UI framework. Pass `undefined` to opt out.

- **`Retry-After` takes precedence over backoff math.** When the server explicitly says "wait 30 seconds," we wait 30 seconds, not our calculated exponential. This matters for rate-limited APIs — backing off less than the server asked typically results in another 429.

---

## Using the operator

The operator composes with any HTTP call, anywhere in the codebase:

```typescript
@Component({ /* … */ })
export class DashboardComponent {
  private readonly http = inject(HttpClient);

  loadMetrics() {
    return this.http.get<Metrics>('/api/metrics').pipe(
      retryWithBackoff(),
    );
  }

  loadMetricsWithUIFeedback() {
    return this.http.get<Metrics>('/api/metrics').pipe(
      retryWithBackoff({
        maxAttempts: 5,
        onRetry: (err, attempt, delay) => {
          this.retryStatus.set({ attempt, willRetryInMs: delay });
        },
      }),
    );
  }

  readonly retryStatus = signal<{ attempt: number; willRetryInMs: number } | null>(null);
}
```

For one-off use, the inline form is clean. For app-wide application across all GET requests, an interceptor is cleaner.

---

## The interceptor — safe by default

For GET requests, retry is almost always safe — GETs are idempotent by HTTP spec. For POST/PUT/DELETE, retry **without an idempotency key** is unsafe: the user clicks "Pay," the request times out, the operator retries, you charge the card twice.

A safe-by-default interceptor: retry GET/HEAD/OPTIONS automatically; require explicit opt-in (via an `Idempotency-Key` header) for everything else.

```typescript
// File: interceptors/retry.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';
import { retryWithBackoff } from '../operators/retry-with-backoff.operator';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export const retryInterceptor: HttpInterceptorFn = (req, next) => {
  const isSafe = SAFE_METHODS.has(req.method);
  const hasIdempotencyKey = req.headers.has('Idempotency-Key');

  // Opt-in for non-safe methods: caller must send Idempotency-Key.
  // Safe methods retry by default.
  if (!isSafe && !hasIdempotencyKey) {
    return next(req);
  }

  return next(req).pipe(retryWithBackoff());
};
```

Registered alongside other interceptors:

```typescript
// File: app.config.ts
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { authInterceptor } from './auth/jwt.interceptor';
import { retryInterceptor } from './interceptors/retry.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withInterceptors([
        retryInterceptor,    // outer: retries the whole chain incl. auth refresh
        authInterceptor,     // inner: handles 401 refresh
      ]),
    ),
  ],
};
```

### Interceptor ordering matters

Interceptors run **in registration order on the way out**, **reverse order on the way back**. The order above produces:

```text
Request:  consumer → retryInterceptor → authInterceptor → network
Response: network → authInterceptor → retryInterceptor → consumer
```

So when a network error reaches `retryInterceptor`, the auth interceptor has already had its chance to handle 401s. If the auth interceptor's refresh succeeded and the retry succeeded, `retryInterceptor` never sees an error at all. If the auth interceptor's refresh failed (which propagates the 401 outward), `retryInterceptor` sees a 401 — and correctly chooses not to retry it (since 401 isn't in the retryable list).

If you reversed the order, the retry interceptor would retry the entire chain *including* the auth interceptor's refresh, which would cause auth bugs.

### Opting in for POST/PUT/DELETE

For sensitive non-idempotent endpoints that the server has made idempotent via an idempotency key:

```typescript
import { v4 as uuid } from 'uuid';

placeOrder(order: Order) {
  return this.http.post('/api/orders', order, {
    headers: {
      // Server uses this key to deduplicate retried requests at its end.
      // Retry triggers a second call with the same key; server returns the
      // cached result of the first call instead of placing a duplicate order.
      'Idempotency-Key': uuid(),
    },
  });
  // The retry interceptor sees the header and applies retryWithBackoff().
}
```

The server-side contract: when the server sees `Idempotency-Key: <uuid>`, it remembers the result of that operation for some window (e.g., 24 hours). A retry with the same key returns the cached result instead of placing a duplicate order. Stripe, AWS, and most modern payment APIs implement this pattern.

**Without server-side idempotency-key support, do not add this header.** The interceptor will retry; the server will treat each retry as a fresh request; the user gets charged N times.

---

## UI integration patterns

What should users see during retries? Three common patterns:

### Pattern 1 — silent (the default)

For fast retries (sub-second) on backgrounded data, the user shouldn't see anything. The original click was responsive ("Loading…"); the retry happens during the loading state; success arrives transparently.

```typescript
this.http.get<User>('/api/me').pipe(retryWithBackoff()).subscribe({
  next: user => this.user.set(user),
  error: err => this.error.set('Could not load profile.'),
});
```

Default behavior. No UI work needed.

### Pattern 2 — "Retrying…" indicator for long delays

If retries push the wait past a couple of seconds, users wonder if the app is broken. Surface "Retrying…" once you've started waiting:

```typescript
readonly status = signal<'loading' | 'retrying' | 'ready' | 'error'>('loading');

loadUser() {
  this.status.set('loading');
  this.http.get<User>('/api/me').pipe(
    retryWithBackoff({
      onRetry: () => this.status.set('retrying'),
    }),
  ).subscribe({
    next: user => {
      this.user.set(user);
      this.status.set('ready');
    },
    error: () => this.status.set('error'),
  });
}
```

```html
@switch (status()) {
  @case ('loading') { <p>Loading…</p> }
  @case ('retrying') { <p>Connection issue, retrying…</p> }
  @case ('ready') { <user-card [user]="user()!" /> }
  @case ('error') { <p>Could not load. <button (click)="loadUser()">Try again</button></p> }
}
```

### Pattern 3 — global retry status banner

For app-wide health visibility, expose retry state from a singleton service. The retry interceptor pushes events; a banner component reads them and shows "Network issues — retrying" across the top.

```typescript
@Injectable({ providedIn: 'root' })
export class RetryStatusService {
  private readonly inflight = signal(0);
  private readonly retrying = signal(0);

  readonly hasRetries = computed(() => this.retrying() > 0);

  trackAttempt() { this.inflight.update(n => n + 1); }
  trackRetry() { this.retrying.update(n => n + 1); }
  trackSuccess() {
    this.inflight.update(n => Math.max(0, n - 1));
    this.retrying.set(0);
  }
}
```

Then wire it through the interceptor's `onRetry` callback. The banner reads `retryStatusService.hasRetries()` and renders conditionally.

---

## Variations

### Circuit breaker — give up entirely after N consecutive failures

For some endpoints, you want to **stop trying after enough failures** to avoid hammering a service that's clearly down. A circuit breaker tracks consecutive failure counts and, after a threshold, fast-fails subsequent calls without even attempting them:

```typescript
@Injectable({ providedIn: 'root' })
export class CircuitBreaker {
  private readonly failures = signal(0);
  private readonly openUntil = signal<number | null>(null);
  private readonly THRESHOLD = 5;
  private readonly COOLDOWN_MS = 30_000;

  isOpen(): boolean {
    const until = this.openUntil();
    return until !== null && Date.now() < until;
  }

  recordSuccess(): void {
    this.failures.set(0);
    this.openUntil.set(null);
  }

  recordFailure(): void {
    const next = this.failures() + 1;
    this.failures.set(next);
    if (next >= this.THRESHOLD) {
      this.openUntil.set(Date.now() + this.COOLDOWN_MS);
    }
  }
}
```

The interceptor checks the breaker before allowing a retry:

```typescript
export const retryInterceptor: HttpInterceptorFn = (req, next) => {
  const breaker = inject(CircuitBreaker);

  if (breaker.isOpen()) {
    // Don't even try — fast-fail.
    return throwError(() => new HttpErrorResponse({
      status: 503,
      statusText: 'Circuit breaker open',
    }));
  }

  return next(req).pipe(
    retryWithBackoff({
      shouldRetry: (err, attempt) => {
        if (!isRetryable(err)) return false;
        if (breaker.isOpen()) return false;  // bail mid-retry-chain
        return true;
      },
    }),
    tap({
      next: () => breaker.recordSuccess(),
      error: () => breaker.recordFailure(),
    }),
  );
};
```

After 5 consecutive failures, subsequent calls fail instantly for 30 seconds. Then the breaker resets and tries again. This protects downstream services and avoids slow user experiences when a backend is genuinely down.

### Combine with `timeout()` to bound individual attempts

A request that hangs indefinitely defeats retry — you wait forever for the first attempt. Always pair with `timeout` to bound each attempt:

```typescript
this.http.get<User>('/api/me').pipe(
  timeout(5000),           // each attempt times out after 5s
  retryWithBackoff(),      // retry on the timeout
).subscribe(/* … */);
```

`timeout` emits a `TimeoutError` on the source stream. Our `isRetryable` returns `true` for non-HTTP errors by default, so it gets retried just like a network failure.

### Per-call override of the default policy

Some endpoints need different retry behavior — e.g., a long-poll endpoint that should retry many times, or a noisy endpoint where retry adds noise without value. Override per call:

```typescript
this.http.get<Notifications>('/api/notifications/long-poll').pipe(
  retryWithBackoff({
    maxAttempts: 10,
    baseDelayMs: 1000,
    maxDelayMs: 60_000,
  }),
);

this.http.post<Analytics>('/api/track/click', payload).pipe(
  retryWithBackoff({
    maxAttempts: 1,  // try once, give up — analytics losses are acceptable
  }),
);
```

---

## Trade-offs and common pitfalls

**Use retry-with-backoff when:**

- The API has known transient failure modes (deploys, rate limits, occasional 5xx blips)
- The cost of a false failure (user sees error toast for a recoverable issue) exceeds the cost of a real retry delay
- Your backend is multi-instance with rolling deploys (some requests will hit a restarting instance)

**Be cautious / skip retry when:**

- Requests are user-action-triggered AND non-idempotent without idempotency keys (payments, sends, mutations). Retrying duplicates the action.
- The endpoint is so slow that 3 retries push the user past their patience window. Better to fail fast and let them retry deliberately.
- You're calling an unreliable third party for fire-and-forget analytics — retries are wasted bandwidth on data that doesn't matter.
- The retry budget would compete with the user's clock — e.g., a single-page checkout flow with a 30-second session timeout.

### Common pitfalls

- **Putting `retryWithBackoff` outside a `switchMap`** in search-as-you-type:
  ```typescript
  // WRONG — retries the entire pipeline, including new keystrokes
  searchTerm$.pipe(
    switchMap(q => this.http.get('/search?q=' + q)),
    retryWithBackoff(),
  )

  // RIGHT — retries only the HTTP call
  searchTerm$.pipe(
    switchMap(q => this.http.get('/search?q=' + q).pipe(retryWithBackoff())),
  )
  ```
  The wrong form retries from the source observable, which re-emits intermediate values. For HTTP retry specifically, the operator must live inside the `switchMap`'s inner observable.

- **Retrying non-idempotent requests without idempotency keys.** Charges duplicated, emails sent twice, records created N times. The safe-by-default interceptor prevents this for routine usage; the danger is opt-in calls that forget the key.

- **Skipping jitter.** Synchronized retry storms turn one outage into a worse outage. Always include jitter — even 10% is enough to spread parallel callers.

- **Forgetting `timeout()`.** A request that hangs indefinitely never errors, so retry never kicks in. The combined pattern `timeout → retryWithBackoff` is what produces "fail fast, retry smart" behavior.

- **Retrying 401/403** — interferes with auth interceptor's refresh flow. The status set in `RETRYABLE_STATUSES` deliberately excludes these.

- **Setting `maxAttempts` too high.** Users won't wait 30 seconds. A sane upper bound: total possible wait time of 10–15 seconds. With base 200ms and exponential growth, 4 attempts maxes at ~3 seconds; 6 attempts at ~12 seconds.

- **Treating `Retry-After: 0` as "don't wait."** It means "you can retry immediately, but I'm telling you it's OK." `Math.max(0, …)` in the parsing function handles this — zero is fine; negative would be a server bug we'd want to floor at zero.

- **Wrong interceptor order.** If retry runs *inside* the auth interceptor's chain, retrying a request whose token just refreshed will retry the original (pre-refresh) request, not the refreshed one. The recommended ordering — `retryInterceptor` outside `authInterceptor` — produces the right composition.

- **Counting "given up" as success in error metrics.** A retry that eventually succeeds should not register as an error; a retry that gives up should. The metrics should hook into `next` for success, not the request fire-time.

---

## See also

- [HTTP](../../http/http.md) — `HttpClient`, error types, interceptors
- [HTTP Interceptors](../../http/interceptors.md) — functional interceptor primitives
- [RxJS error handling](../../reactivity/rxjs/rxjs-error-handling.md) — `retry`, `catchError`, `throwError`, modern RxJS error patterns
- [JWT Interceptor: Breaking the Circular Dependency](../auth/jwt-interceptor-circular-dep.md) — the auth interceptor whose order this recipe's interceptor depends on
- [Upload and Download Progress](./progress-tracking.md) — composes with retry; the `trackProgress` operator runs inside the retried HTTP call
- [Signals](../../reactivity/signals.md) — the storage primitive for retry-status UI state

## References

- [`retry` operator (RxJS)](https://rxjs.dev/api/operators/retry) — the underlying primitive with `delay` config support
- [`timer` (RxJS)](https://rxjs.dev/api/index/function/timer) — delay-then-emit primitive used in the backoff
- [`Retry-After` header (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After) — spec for the server-side hint
- [AWS Architecture Blog — Exponential Backoff And Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) — the canonical explainer of why jitter matters
- [Stripe API — Idempotent Requests](https://stripe.com/docs/api/idempotent_requests) — production reference for the `Idempotency-Key` pattern
- [Google SRE Book — Handling Overload (Ch. 21)](https://sre.google/sre-book/handling-overload/) — circuit breakers and load shedding in depth

## Demo source

Synthesized from production retry patterns in modern Angular apps rather than a single demo file. The retryable-status taxonomy, exponential-backoff-with-jitter math, and safe-by-default interceptor policy reflect the consensus across high-traffic apps that have measured what works. All code is original.
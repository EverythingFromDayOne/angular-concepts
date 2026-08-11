---
roadmap_node: "interceptors"
title: "Interceptors"
file: "http/interceptors.md"
source_days: []
original_authors: []
status:
  translated: false
  upgraded: true
  reviewed: false
angular_when_written: null
angular_baseline: "22"
---

> **Modern Angular only**
> No equivalent exists in the original 100 Days series.
> Written fresh for Angular v22.

# HTTP Interceptors

> **Lead with this:** Interceptors are middleware for `HttpClient` — every
> request and response passes through them in order, giving you one place to
> add auth headers, retry failed requests, show a loading spinner, or normalize
> errors across your entire app.

## What it is

Every call to `HttpClient` travels through a **pipeline of interceptors** before
reaching the backend, and every response travels back through them in reverse.
Each interceptor is a function that can:

- Inspect or modify the outgoing request (add headers, change the URL, attach context)
- Inspect or modify the incoming response (log timing, transform data, throw on errors)
- Short-circuit the pipeline entirely (return a cached response without hitting the network)
- Coordinate UI (increment a loading counter, decrement it when done)

You register interceptors once in `provideHttpClient(withInterceptors([...]))`.
They run for every request the whole app makes — no per-service wiring needed.

Angular v22 uses **functional interceptors** as the recommended form — plain
functions typed as `HttpInterceptorFn`. The older class-based form still works
via `withInterceptorsFromDi()` but is considered legacy.

## How it works under the hood

### Old mechanism — class-based interceptors and HTTP_INTERCEPTORS

The original interceptor system (Angular 4+) used the `HttpInterceptor` interface:

```typescript
// Old class-based interceptor (Angular 4–14)
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private authService: AuthService) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const token = this.authService.getToken();
    const cloned = req.clone({
      headers: req.headers.set('Authorization', `Bearer ${token}`)
    });
    return next.handle(cloned);  // next.handle() — method call on an object
  }
}
```

Registered via the `HTTP_INTERCEPTORS` multi-token:

```typescript
providers: [
  { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
  { provide: HTTP_INTERCEPTORS, useClass: LoggingInterceptor, multi: true },
]
```

Two problems with this approach:

**Ordering was fragile.** Interceptors registered across different NgModules or
providers could run in a non-obvious order depending on module import order.
In complex apps with lazy-loaded modules providing their own interceptors,
the actual execution order was hard to predict.

**Boilerplate.** Every interceptor required a class, `@Injectable()`, a
constructor for DI, and a `next.handle(req)` call (method on an object,
not a direct function call).

### New mechanism — functional interceptors and withInterceptors

Functional interceptors are plain TypeScript functions typed as `HttpInterceptorFn`:

```typescript
type HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => Observable<HttpEvent<unknown>>
```

- `req` — the outgoing request (immutable — must use `req.clone()` to modify)
- `next` — a function (not an object) representing the next interceptor in the
  chain, or the backend if no more interceptors remain
- Return — an `Observable<HttpEvent<unknown>>` that callers subscribe to

Because `HttpInterceptorFn`s run inside Angular's injection context, `inject()`
works directly inside them — no constructor, no `@Injectable()`, no class needed.

**Ordering is deterministic.** The interceptors run in the exact array order you
specify in `withInterceptors([...])`. For requests: left-to-right. For responses
(via the Observable pipe): right-to-left.

```
Request flow (outbound):
  withInterceptors([A, B, C])
  A → B → C → Backend

Response flow (inbound, via Observable chain):
  Backend → C → B → A → caller
```

This mirrors how Express middleware or Koa's compose pattern works — each
interceptor wraps the next one as a nested Observable.

### Why requests are immutable

`HttpRequest` objects are frozen — you cannot mutate `req.url`, `req.headers`,
or `req.body` directly. Every modification produces a new request via `req.clone()`.
This immutability means interceptors can't accidentally corrupt the request seen
by subsequent interceptors: each interceptor only sees what was passed to it.

## Basic usage

### Writing a functional interceptor

```typescript
// auth.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);  // inject() works here
  const token = authService.token();        // read the signal

  if (!token) {
    return next(req);                       // no token — pass through unchanged
  }

  // req is immutable — clone and add the header
  const authedReq = req.clone({
    setHeaders: { Authorization: `Bearer ${token}` }
  });

  return next(authedReq);
};
```

### Registering interceptors

```typescript
// app.config.ts
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { authInterceptor } from './auth.interceptor';
import { loggingInterceptor } from './logging.interceptor';
import { errorInterceptor } from './error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withInterceptors([
        loggingInterceptor,   // runs first on requests, last on responses
        authInterceptor,      // runs second on requests
        errorInterceptor,     // runs last on requests, first on responses
      ])
    ),
  ],
};
```

### req.clone() patterns

`req.clone()` accepts a partial override of any request property:

```typescript
// Add a header (without removing existing headers)
const newReq = req.clone({
  headers: req.headers.set('X-Request-ID', crypto.randomUUID()),
});

// Shorthand for setting multiple headers at once
const newReq = req.clone({
  setHeaders: {
    Authorization: `Bearer ${token}`,
    'X-Request-ID': crypto.randomUUID(),
  },
});

// Change the URL (e.g. prefix all requests with the API base URL)
const newReq = req.clone({
  url: `https://api.example.com${req.url}`,
});

// Replace the body
const newReq = req.clone({
  body: { ...req.body, timestamp: Date.now() },
});
```

### Class-based interceptors (legacy — still works)

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Old class-based approach — still supported via withInterceptorsFromDi()
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler } from '@angular/common/http';

@Injectable()
export class LegacyAuthInterceptor implements HttpInterceptor {
  constructor(private authService: AuthService) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler) {
    const token = this.authService.getToken();
    return next.handle(req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    }));
  }
}
```

```typescript
// Registration
provideHttpClient(
  withInterceptorsFromDi(),  // enables DI-based (class) interceptors
  withInterceptors([modernFunctionalInterceptor]),  // can mix both
),
providers: [
  { provide: HTTP_INTERCEPTORS, useClass: LegacyAuthInterceptor, multi: true }
]
```

Use `withInterceptorsFromDi()` only for gradual migration — prefer functional
interceptors for all new code. The Angular team has signaled that class-based
interceptors may be deprecated in a future release.

### HttpContextToken — per-request metadata for interceptors

Sometimes an interceptor needs per-request configuration — "skip auth for this
request," "cache this one," "use a 5-second timeout." `HttpContextToken` is a
typed key that can carry any metadata in the request's `.context` map:

```typescript
// tokens.ts — define tokens with a default value factory
import { HttpContextToken } from '@angular/common/http';

export const SKIP_AUTH = new HttpContextToken<boolean>(() => false);
export const CACHE_TTL_MS = new HttpContextToken<number>(() => 0);
```

```typescript
// caching.interceptor.ts — reads the token
export const cachingInterceptor: HttpInterceptorFn = (req, next) => {
  const ttl = req.context.get(CACHE_TTL_MS);

  if (ttl === 0) {
    return next(req);  // no caching requested for this request
  }

  const cache = inject(HttpCacheService);
  const hit = cache.get(req.urlWithParams);

  if (hit) {
    // Short-circuit — return cached response without hitting the network
    return of(new HttpResponse({ status: 200, body: hit }));
  }

  return next(req).pipe(
    tap(event => {
      if (event instanceof HttpResponse && event.ok) {
        cache.set(req.urlWithParams, event.body, ttl);
      }
    })
  );
};
```

```typescript
// Call site — attach context to the specific request
this.http.get<Product[]>('/api/products', {
  context: new HttpContext()
    .set(CACHE_TTL_MS, 60_000)  // cache for 60 seconds
    .set(SKIP_AUTH, true),      // don't add auth header to this request
});
```

Context is **mutable** (unlike the request itself). If a retried request
re-enters the interceptor chain, the same context object is passed — useful for
tracking retry count without cloning context.

## Real-world patterns

### Pattern 1 — Auth interceptor with token refresh

The most common interceptor: add the token to every request, catch 401
responses, refresh the token, and replay the original request:

```typescript
// auth.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  const addToken = (request: typeof req) => request.clone({
    setHeaders: { Authorization: `Bearer ${auth.accessToken()}` }
  });

  return next(addToken(req)).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401) {
        return throwError(() => error);
      }

      // Token expired — refresh and replay
      return auth.refreshToken().pipe(
        switchMap(() => next(addToken(req))),  // replay with new token
        catchError(refreshError => {
          auth.logout();  // refresh also failed — force logout
          return throwError(() => refreshError);
        })
      );
    })
  );
};
```

### Pattern 2 — Loading spinner with signals

A global loading indicator driven by an in-flight request counter:

```typescript
// http-ui.service.ts
@Injectable({ providedIn: 'root' })
export class HttpUiService {
  private _count = signal(0);
  readonly isLoading = computed(() => this._count() > 0);

  increment(): void { this._count.update(n => n + 1); }
  decrement(): void { this._count.update(n => Math.max(0, n - 1)); }
}

// spinner.interceptor.ts
import { finalize } from 'rxjs';

export const spinnerInterceptor: HttpInterceptorFn = (req, next) => {
  const ui = inject(HttpUiService);
  ui.increment();
  return next(req).pipe(finalize(() => ui.decrement()));
  // finalize fires on: complete, error, AND unsubscribe (cancel)
};
```

```html
<!-- app.component.html -->
@if (httpUi.isLoading()) {
  <app-global-spinner />
}
```

`finalize` is the right operator here — it fires on complete, error, AND when the
subscription is unsubscribed (request cancelled). `tap` would miss the cancel case.

### Pattern 3 — Retry with exponential backoff

```typescript
// retry.interceptor.ts
import { HttpContextToken, HttpInterceptorFn } from '@angular/common/http';
import { retry, timer } from 'rxjs';

export const RETRY_COUNT = new HttpContextToken<number>(() => 3);

export const retryInterceptor: HttpInterceptorFn = (req, next) => {
  const maxRetries = req.context.get(RETRY_COUNT);

  return next(req).pipe(
    retry({
      count: maxRetries,
      delay: (error, attempt) => {
        // Only retry on server errors, not client errors
        if (error.status >= 400 && error.status < 500) {
          throw error;  // don't retry 4xx
        }
        // Exponential backoff: 1s, 2s, 4s, 8s...
        return timer(Math.pow(2, attempt - 1) * 1000);
      },
    })
  );
};
```

```typescript
// Call site — override default retry count for critical requests
this.http.post('/api/critical-action', payload, {
  context: new HttpContext().set(RETRY_COUNT, 5),
});

// Skip retries for this request
this.http.get('/api/real-time', {
  context: new HttpContext().set(RETRY_COUNT, 0),
});
```

### Pattern 4 — API URL prefix interceptor

One interceptor replaces manual base-URL concatenation in every service:

```typescript
// api-prefix.interceptor.ts
export const apiPrefixInterceptor: HttpInterceptorFn = (req, next) => {
  // Only prefix relative URLs — don't prefix external calls (CDN, third-party)
  if (req.url.startsWith('http')) {
    return next(req);
  }

  return next(req.clone({
    url: `https://api.example.com/v2${req.url}`,
  }));
};
```

```typescript
// Services become much cleaner — no base URL management
@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);

  getUser(id: string) {
    return this.http.get<User>(`/users/${id}`);
    // Interceptor rewrites to: https://api.example.com/v2/users/123
  }
}
```

## Testing interceptors

Use `provideHttpClientTesting()` and `HttpTestingController` to test interceptors
in isolation:

```typescript
// auth.interceptor.spec.ts
import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let controller: HttpTestingController;
  const mockToken = signal<string | null>(null);

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { token: mockToken } },
      ],
    });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => controller.verify());  // no unexpected requests

  it('adds Authorization header when token is present', () => {
    mockToken.set('my-test-token');

    http.get('/api/users').subscribe();

    const req = controller.expectOne('/api/users');
    expect(req.request.headers.get('Authorization')).toBe('Bearer my-test-token');
    req.flush([]);
  });

  it('passes through unchanged when no token', () => {
    mockToken.set(null);

    http.get('/api/public').subscribe();

    const req = controller.expectOne('/api/public');
    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({});
  });
});
```

## Common mistakes

### Mistake 1 — Mutating the request directly

`HttpRequest` is immutable. Modifying properties directly throws at runtime:

```typescript
// ❌ Runtime error — HttpRequest is frozen
export const badInterceptor: HttpInterceptorFn = (req, next) => {
  req.headers.set('Authorization', token);  // no-op in some cases, throws in others
  return next(req);
};

// ✅ Always clone
export const goodInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req.clone({ setHeaders: { Authorization: token } }));
};
```

### Mistake 2 — Forgetting to return next(req) — silent hang

Every interceptor must either call `next(req)` or return a synthetic Observable.
Forgetting to return `next(req)` means the request chain stops — the HTTP call
never fires, and the caller's Observable never emits or errors:

```typescript
// ❌ Missing return — request silently hangs forever
export const brokenInterceptor: HttpInterceptorFn = (req, next) => {
  console.log('Request:', req.url);
  next(req);  // called but not returned — Observable is thrown away
};

// ✅ Always return next(req) or the pipe chain
export const fixedInterceptor: HttpInterceptorFn = (req, next) => {
  console.log('Request:', req.url);
  return next(req);
};
```

### Mistake 3 — Using tap instead of finalize for cleanup

`tap` fires on emissions, not on completion or cancellation. Use `finalize`
for cleanup that must run no matter how the Observable terminates:

```typescript
// ❌ tap misses cancellation (unsubscribe before response) and error paths
export const badSpinnerInterceptor: HttpInterceptorFn = (req, next) => {
  ui.increment();
  return next(req).pipe(tap(() => ui.decrement()));
};

// ✅ finalize fires on complete, error, AND unsubscribe
export const goodSpinnerInterceptor: HttpInterceptorFn = (req, next) => {
  ui.increment();
  return next(req).pipe(finalize(() => ui.decrement()));
};
```

### Mistake 4 — Ordering interceptors incorrectly

Request processing is left-to-right; response processing is right-to-left.
Putting the error handler before the auth interceptor means the error handler
sees requests that haven't been authenticated yet:

```typescript
// ❌ errorInterceptor runs before authInterceptor on requests
// This means it can't retry with a refreshed token from authInterceptor
withInterceptors([errorInterceptor, authInterceptor])

// ✅ Auth adds the token first, then error handler catches 401 and can retry
withInterceptors([authInterceptor, errorInterceptor])
```

Think through both directions when ordering: what order makes sense for
outgoing requests, AND what order makes sense for incoming responses?

## How this evolved

> - **Angular 4 (2017):** Class-based interceptors introduced — `HttpInterceptor`
>   interface, `HTTP_INTERCEPTORS` multi-token, `next.handle(req)`. Ordering
>   determined by provider declaration order, fragile across NgModules.
>
> - **Angular 15 (2022):** Functional interceptors introduced via
>   `withInterceptors([...])`. Deterministic ordering. `inject()` available
>   inside interceptor functions. The `HttpContextToken` API also stable here
>   (introduced alongside interceptors in Angular 12 but gained prominence
>   with functional interceptors).
>
> - **Angular 16 (2023):** `withRequestsMadeViaParent()` feature — lets a
>   child injector's `HttpClient` pass requests through the parent injector's
>   interceptor chain after its own. Enables scoped interceptors in
>   feature-level providers.
>
> - **Angular 20 (2025):** Class-based interceptors (`withInterceptorsFromDi`)
>   remain supported but documentation recommends functional interceptors
>   exclusively. `withFetch` deprecated; Fetch became default, exposing
>   redirect metadata on `HttpResponse` for Fetch-aware interceptors.
>
> - **Angular 22 (now):** Functional interceptors are the standard. All
>   Angular documentation examples use them. Class-based interceptors work via
>   `withInterceptorsFromDi()` for migration, but new code should never
>   use them. The interceptor pipeline is fully composable with signals —
>   `inject(MySignalService).someSignal()` inside an interceptor function
>   reads the signal value at request time.

## See also

- [HTTP Overview](./http.md) — setup, basic requests, and the request flow
  diagram that shows where interceptors fit
- [Error Handling](./error-handling.md) — catching `HttpErrorResponse`,
  retry strategies, and global error normalization via interceptors
- [Signals](../reactivity/signals.md) — signal services that interceptors
  can inject and react to
- [Dependency Injection](../dependency-injection/dependency-injection.md) —
  why `inject()` works inside functional interceptors (injection context)
- [Official docs — Interceptors](https://angular.dev/guide/http/interceptors)
- [Official docs — HttpInterceptorFn API](https://angular.dev/api/common/http/HttpInterceptorFn)

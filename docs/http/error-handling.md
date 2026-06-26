---
roadmap_node: "error-handling"
title: "HTTP Error Handling"
file: "http/error-handling.md"
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

# HTTP Error Handling

> **Lead with this:** Angular wraps every HTTP failure into a single
> `HttpErrorResponse` object — network outages and server errors alike — so
> you handle both in one place with `catchError`, using `status === 0` to
> tell them apart.

## What it is

When an HTTP request fails, Angular doesn't throw a raw browser error. It
catches both categories of failure and packages them into an `HttpErrorResponse`
object that lands in your Observable's error channel:

| Category | `status` value | When it happens |
| --- | --- | --- |
| **Network / client error** | `0` | No internet, CORS block, DNS failure, request timeout, browser cancelled |
| **Server error** | `4xx` or `5xx` | Backend returned an error status code |

Every error — no matter the category — is an `HttpErrorResponse`. You handle
them in one place with RxJS's `catchError` operator, at either the call site
(for request-specific handling) or in an interceptor (for app-wide handling).

## How it works under the hood

### Old approach — raw XHR and fetch errors

Without Angular's HTTP layer, error handling looked different for every approach:

```typescript
// XMLHttpRequest — check status manually
const xhr = new XMLHttpRequest();
xhr.onload = () => {
  if (xhr.status >= 200 && xhr.status < 300) {
    const data = JSON.parse(xhr.responseText);
  } else {
    console.error('Server error:', xhr.status, xhr.statusText);
  }
};
xhr.onerror = () => {
  console.error('Network error — no status available');
};

// Fetch API — two different error types to handle
fetch('/api/users')
  .then(res => {
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    return res.json();
  })
  .catch(err => {
    // Could be a network error OR the Error thrown above — ambiguous
    console.error(err);
  });
```

Problems: no standard error shape, network errors are opaque `TypeError`s,
no clear distinction between "request never reached server" and "server
returned 4xx/5xx", and each call site needs its own error shape logic.

### Angular's approach — HttpErrorResponse wraps everything

`HttpClient` intercepts both failure modes and packages them into one typed class:

```typescript
class HttpErrorResponse {
  readonly ok: false;                // always false
  readonly status: number;           // 0 = network/client; 4xx/5xx = server
  readonly statusText: string;       // 'Unknown Error' or HTTP status text
  readonly message: string;          // human-readable description
  readonly url: string | null;       // the request URL
  readonly headers: HttpHeaders;     // response headers (empty for status 0)
  readonly error: any;               // varies by error type — see below
}
```

The `error` property holds different content depending on the error type:

| Error type | `error` value |
| --- | --- |
| Network error (status 0) | A JavaScript `Error` or `ProgressEvent` from the browser |
| Server error with JSON body | The parsed JSON body (typed as `any`) |
| Server error with text body | The raw string |
| Server error with no body | `null` |

This predictable shape means one `catchError` handler in an interceptor can
handle all failures the same way — check `status === 0` to separate network
errors from server errors, then inspect `error` for the body.

## Basic usage

### catchError at the call site

For request-specific error handling — different UI for different endpoints:

```typescript
import { HttpClient, HttpErrorResponse, HttpStatusCode } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);

  getUser(id: string): Observable<User> {
    return this.http.get<User>(`/api/users/${id}`).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 0) {
          // Network error — no connection, CORS block, timeout
          return throwError(() => new Error('Network error. Check your connection.'));
        }

        switch (error.status) {
          case HttpStatusCode.NotFound:       // 404
            return throwError(() => new Error(`User ${id} not found.`));
          case HttpStatusCode.Forbidden:      // 403
            return throwError(() => new Error('You do not have permission to view this user.'));
          case HttpStatusCode.Unauthorized:   // 401
            return throwError(() => new Error('Please sign in to continue.'));
          default:
            return throwError(() => new Error(`Server error: ${error.status}`));
        }
      })
    );
  }
}
```

`throwError(() => error)` re-throws an error into the Observable pipeline —
the caller's `subscribe({ error: ... })` or a wrapping `catchError` will receive it.

### HttpStatusCode enum — avoid magic numbers

`HttpStatusCode` is a comprehensive Angular enum covering all standard status codes.
Use it instead of numeric literals:

```typescript
import { HttpStatusCode } from '@angular/common/http';

// ✅ Readable and refactoring-safe
if (error.status === HttpStatusCode.Unauthorized) { /* 401 */ }
if (error.status === HttpStatusCode.NotFound) { /* 404 */ }
if (error.status === HttpStatusCode.InternalServerError) { /* 500 */ }
if (error.status === HttpStatusCode.ServiceUnavailable) { /* 503 */ }

// Common status codes
// 200 Ok, 201 Created, 204 NoContent
// 301 MovedPermanently, 304 NotModified
// 400 BadRequest, 401 Unauthorized, 403 Forbidden, 404 NotFound
// 409 Conflict, 422 UnprocessableEntity, 429 TooManyRequests
// 500 InternalServerError, 502 BadGateway, 503 ServiceUnavailable
```

### Providing a fallback value instead of re-throwing

Sometimes the right response to a failure is a default value, not an error:

```typescript
import { catchError, of } from 'rxjs';

getFeatureFlags(): Observable<FeatureFlags> {
  return this.http.get<FeatureFlags>('/api/feature-flags').pipe(
    catchError(() => of(DEFAULT_FLAGS))  // silently fall back to defaults
  );
}

// In a component — the Observable always emits, never errors
flags = toSignal(this.featureService.getFeatureFlags(), {
  initialValue: DEFAULT_FLAGS
});
```

Use this for non-critical requests where degraded behavior is acceptable.
Don't use it for mutations or requests where silent failure would confuse the user.

## Centralized error handling in interceptors

For cross-cutting concerns that should apply to every request — logging,
user notifications, forced logout on 401 — handle errors in an interceptor:

```typescript
// error.interceptor.ts
import {
  HttpInterceptorFn, HttpErrorResponse, HttpStatusCode
} from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { NotificationService } from './notification.service';
import { AuthService } from './auth.service';
import { Router } from '@angular/router';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const notify = inject(NotificationService);
  const auth = inject(AuthService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 0) {
        notify.error('Network error — check your connection and try again.');
        return throwError(() => error);
      }

      switch (error.status) {
        case HttpStatusCode.Unauthorized:
          auth.clearSession();
          router.navigate(['/login'], {
            queryParams: { returnUrl: router.url }
          });
          break;

        case HttpStatusCode.Forbidden:
          notify.error('You do not have permission to perform this action.');
          break;

        case HttpStatusCode.TooManyRequests:       // 429
          notify.warn('Too many requests. Please slow down.');
          break;

        case HttpStatusCode.ServiceUnavailable:    // 503
        case HttpStatusCode.BadGateway:            // 502
          notify.error('Service is temporarily unavailable. Please try again shortly.');
          break;

        // 4xx client errors — let individual call sites handle these
        // (they have context the interceptor doesn't, e.g. which form field is invalid)
        default:
          if (error.status >= 500) {
            notify.error('An unexpected error occurred. Our team has been notified.');
          }
      }

      return throwError(() => error);  // re-throw so call-site handlers still run
    })
  );
};
```

**Re-throw after handling.** The interceptor notifies the user but still
re-throws the error. The call-site handler (if any) still sees it and can
do its own specific handling. If you swallow the error without re-throwing,
the call-site's `catchError` never runs and the Observable completes silently.

## Global ErrorHandler

Angular's `ErrorHandler` catches any uncaught errors — including `HttpErrorResponse`
objects that escaped `catchError` without being handled. Use it as a last resort
for logging, not as the primary error-handling mechanism:

```typescript
// error-handler.ts
import { ErrorHandler, Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { LoggingService } from './logging.service';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private logger = inject(LoggingService);

  handleError(error: unknown): void {
    if (error instanceof HttpErrorResponse) {
      // Unhandled HTTP error — logged but don't show generic toast
      // (interceptor should have shown a notification already)
      this.logger.logHttpError({
        status: error.status,
        url: error.url,
        message: error.message,
      });
    } else {
      // JavaScript runtime error
      this.logger.logError(error);
    }

    // Re-throw if you want the browser console to still see it
    // (during development)
    if (typeof ngDevMode !== 'undefined' && ngDevMode) {
      throw error;
    }
  }
}
```

```typescript
// app.config.ts — register the global handler
import { ErrorHandler } from '@angular/core';

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
  ],
};
```

## Real-world patterns

### Pattern 1 — Typed API error body

Many APIs return a structured error body. Type it and narrow to it in `catchError`:

```typescript
// api-error.types.ts
interface ApiError {
  code: string;
  message: string;
  field?: string;     // for validation errors
  details?: string[];
}

// product.service.ts
createProduct(data: CreateProductDto): Observable<Product> {
  return this.http.post<Product>('/api/products', data).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === HttpStatusCode.UnprocessableEntity) {  // 422
        // Type-narrow the error body
        const apiError = error.error as ApiError;
        return throwError(() => ({
          field: apiError.field,
          message: apiError.message,
        }));
      }

      return throwError(() => error);
    })
  );
}
```

```typescript
// Component — handle the typed validation error
this.productService.createProduct(formData).subscribe({
  next: product => this.router.navigate(['/products', product.id]),
  error: err => {
    if (err?.field) {
      this.form.get(err.field)?.setErrors({ serverError: err.message });
    }
  }
});
```

### Pattern 2 — Offline detection via status 0

Status 0 covers several distinct failure modes. Use `navigator.onLine` to
distinguish "definitely offline" from "connection exists but request failed
(CORS, timeout, etc.)":

```typescript
export const offlineAwareInterceptor: HttpInterceptorFn = (req, next) => {
  const notify = inject(NotificationService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 0) {
        if (!navigator.onLine) {
          notify.error('You are offline. Please check your internet connection.');
        } else {
          // Online but request failed — likely CORS, timeout, or blocked
          notify.error('Request failed. The server may be unreachable.');
        }
      }
      return throwError(() => error);
    })
  );
};
```

### Pattern 3 — Retry only on safe methods and transient errors

Only retry GET requests (idempotent) and only on transient server errors,
never on client errors:

```typescript
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { retry, timer } from 'rxjs';

export const smartRetryInterceptor: HttpInterceptorFn = (req, next) => {
  // Never retry mutations — not idempotent
  if (req.method !== 'GET') {
    return next(req);
  }

  return next(req).pipe(
    retry({
      count: 3,
      delay: (error: HttpErrorResponse, attempt: number) => {
        // Don't retry client errors — they won't resolve on retry
        if (error.status >= 400 && error.status < 500) {
          throw error;
        }

        // Don't retry if offline — will keep failing
        if (error.status === 0 && !navigator.onLine) {
          throw error;
        }

        // Retry server errors and unknown network errors with backoff
        const delayMs = Math.min(1000 * Math.pow(2, attempt - 1), 30_000);
        return timer(delayMs);  // 1s, 2s, 4s (capped at 30s)
      },
    })
  );
};
```

## Common mistakes

### Mistake 1 — Checking error.error instead of error.status for the category

`error.error` (the body) is a JavaScript `Error` object for network errors —
not an empty object or null. But checking `error.error instanceof Error` for
network detection is fragile because some server errors also set `error.error`
to an `Error` object. Always use `error.status === 0`:

```typescript
// ❌ Fragile — checking error.error type, not the canonical status code
if (error.error instanceof Error) {
  // might be a network error... or might not
}

// ✅ Definitive — status 0 is Angular's indicator for network/client errors
if (error.status === 0) {
  // network error, CORS block, timeout, browser cancelled
}
```

### Mistake 2 — Swallowing errors silently in catchError

`catchError` must return an Observable. Returning `of(undefined)` or `EMPTY`
silently completes the stream — the caller's error handler never fires:

```typescript
// ❌ Silent swallow — caller's error: callback never called
catchError(() => of(undefined))

// ❌ EMPTY also swallows — completes without emitting
catchError(() => EMPTY)

// ✅ If you want a fallback value, be deliberate and typed about it
catchError(() => of([] as User[]))  // typed fallback — intentional

// ✅ If you want the error to propagate, re-throw
catchError(err => throwError(() => err))
```

### Mistake 3 — Using retryWhen (deprecated in RxJS 7+)

`retryWhen` was the old retry operator — it's deprecated and removed in recent
RxJS versions. Use `retry({ count, delay })` instead:

```typescript
// ❌ Deprecated — retryWhen is removed in RxJS 8+
.pipe(retryWhen(errors => errors.pipe(delay(1000), take(3))))

// ✅ Modern retry with delay callback
.pipe(retry({
  count: 3,
  delay: () => timer(1000)
}))
```

### Mistake 4 — Not re-throwing after handling in an interceptor

If you show a notification in an interceptor and then return `of(null)` or
`EMPTY`, the call site never sees the error. The component's
`subscribe({ error })` or the caller's own `catchError` is bypassed:

```typescript
// ❌ Swallowed in interceptor — call site never knows about the error
return next(req).pipe(
  catchError((error: HttpErrorResponse) => {
    notify.error('Something went wrong');
    return of(null);  // caller's error handler won't fire
  })
);

// ✅ Notify AND re-throw — both the interceptor and call site get to act
return next(req).pipe(
  catchError((error: HttpErrorResponse) => {
    notify.error('Something went wrong');
    return throwError(() => error);  // propagates to call site
  })
);
```

## How this evolved

> - **Angular 2–3 (2016–2017):** The original `@angular/http` module returned
>   `Response` objects — you manually checked `response.ok` and parsed the
>   body. Errors were caught in `.catch()` on the Observable but had no
>   standard shape.
>
> - **Angular 4 (2017):** `HttpClient` introduced `HttpErrorResponse` as the
>   unified error shape. The `status === 0` convention for network errors
>   was established. `catchError` with `throwError` became the idiomatic
>   pattern.
>
> - **Angular 12 (2021):** `HttpStatusCode` enum introduced — named constants
>   for all standard HTTP status codes, replacing numeric literals.
>
> - **Angular 15 (2022):** Functional interceptors (`HttpInterceptorFn`) made
>   centralized error handling cleaner — no class needed, `inject()` available
>   directly in the interceptor function.
>
> - **Angular 22 (now):** The error-handling model is stable. `HttpErrorResponse`,
>   `catchError`, `HttpStatusCode`, and interceptor-level handling are unchanged.
>   The main modernization: `retry({ count, delay })` from RxJS 7 replaces
>   deprecated `retryWhen`, and `throwError(() => error)` (factory form) replaces
>   `throwError(error)` (deprecated value form).

## See also

- [HTTP Overview](./http.md) — setup and how errors flow through the pipeline
- [Interceptors](./interceptors.md) — where centralized error handling lives;
  the auth refresh + retry-on-401 pattern
- [RxJS Error Handling](../reactivity/rxjs/rxjs-error-handling.md) — `catchError`,
  `throwError`, `retry`, `EMPTY`, and the full RxJS error operator toolbox
- [Official docs — Handle request errors](https://angular.dev/guide/http/making-requests#handling-request-failure)
- [Official docs — HttpErrorResponse](https://angular.dev/api/common/http/HttpErrorResponse)
- [Official docs — HttpStatusCode](https://angular.dev/api/common/http/HttpStatusCode)

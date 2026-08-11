---
roadmap_node: "http"
title: "HTTP"
file: "http/http.md"
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

# HTTP

> **Lead with this:** `HttpClient` is Angular's typed HTTP layer — it wraps the
> browser's Fetch API, handles JSON serialization automatically, and plugs into
> a composable interceptor pipeline that can add auth headers, retry failed
> requests, or normalize errors across your entire app.

## What it is

Most Angular apps need to talk to a backend. `HttpClient` is the standard way
to do that — it lives in `@angular/common/http` and gives you typed,
Observable-based methods for every HTTP verb.

You get automatic JSON parsing, built-in XSRF protection, a clean interceptor
pipeline, request cancellation via `takeUntilDestroyed` or `AbortSignal`, and
a transfer cache that prevents duplicate requests during SSR hydration.

In v22, `HttpClient` uses the browser's **Fetch API** by default. The older
XMLHttpRequest backend is still available via `withXhr()` but is deprecated for
server use and will be removed in Angular 23.

For signal-based HTTP, see `httpResource()` in [Signals](../reactivity/signals.md).
This article covers `HttpClient` directly — the Observable-based API that
`httpResource` builds on, and which remains essential for non-GET requests,
interceptor pipelines, and migration paths.

## How it works under the hood

### Old Angular Http module (Angular 2–3)

The original Angular HTTP module (`@angular/http`, retired in Angular 8) used
XMLHttpRequest directly. Responses came back as `Response` objects you had to
manually parse. No interceptors. No typed responses. Configuration was
NgModule-based:

```typescript
// Old approach — @angular/http (Angular 2–3, completely removed in v8)
import { Http } from '@angular/http';
import { map } from 'rxjs/operators';

constructor(private http: Http) {}

getUsers() {
  return this.http.get('/api/users')
    .pipe(map(res => res.json()));  // manual JSON parsing every time
}
```

### Modern HttpClient (Angular 4+)

`HttpClient` replaced `@angular/http` in Angular 4. The core improvements:

- **Typed responses** — `.get<User[]>('/api/users')` returns `Observable<User[]>`,
  JSON parsed automatically
- **Interceptors** — a composable middleware pipeline for auth headers, logging,
  retry logic
- **Progress events** — granular upload/download progress reporting
- **Testing** — `HttpClientTestingModule` and `HttpTestingController` for
  deterministic unit tests

### XHR → Fetch transition

For most of its life, `HttpClient` used `XMLHttpRequest` under the hood via the
`xhr2` package. Angular v22 completes a multi-version migration to the browser's
native **Fetch API** as the default backend:

| Era | Backend | How to configure |
| --- | --- | --- |
| Angular 4–16 | XHR (default) | `provideHttpClient()` — XHR implicit |
| Angular 16.1–21 | XHR (default) | `provideHttpClient(withFetch())` to opt into Fetch (recommended for SSR) |
| Angular v22 | **Fetch (default)** | `provideHttpClient()` — Fetch implicit; `withFetch()` deprecated; `withXhr()` to opt back; server-side XHR deprecated (removal in v23) |

Fetch is more modern, has native abort support, works correctly in SSR (XHR's
underlying `xhr2` library doesn't handle SSR redirects safely), and is the basis
of `httpResource`. The only thing Fetch can't do that XHR can: **upload progress
events** — `xhr.upload.onprogress`. If you need upload progress, you must use
`withXhr()`, but know that XHR server support is removed in Angular 23.

### How a request flows through the system

```
Your service calls this.http.get<User[]>('/api/users')
          │
          ▼
HttpClient builds an HttpRequest object (method, url, headers, body)
          │
          ▼
Request passes through interceptors in ORDER (each can modify or short-circuit)
  interceptor 1: add Authorization header
  interceptor 2: log request timing
  interceptor 3: add correlation ID
          │
          ▼
FetchBackend (or XhrBackend) executes the actual network call
          │
          ▼
Response passes back through interceptors in REVERSE ORDER
  (each can transform, log, or throw on the response)
          │
          ▼
HttpClient emits the typed body as Observable<User[]>
          │
          ▼
Caller's .subscribe() or toSignal() receives User[]
```

## Basic usage

### Setup

```typescript
// app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(),
    // provideHttpClient(withFetch()) — withFetch() deprecated; Fetch is now default
    // provideHttpClient(withXhr())  — opt into XHR only if you need upload progress
  ],
};
```

Pre-standalone reference — the older NgModule approach (Angular 2–13):

```typescript
import { NgModule } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';

@NgModule({
  imports: [HttpClientModule],
})
export class AppModule {}
```

### Injecting HttpClient

Inject `HttpClient` in a service (or component). In Angular v22, the new
`@Service()` decorator is an ergonomic alternative to
`@Injectable({ providedIn: 'root' })` for the common root-singleton case.
Examples below use the broader-compatible `@Injectable` form — both work
identically at runtime:

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface User { id: number; name: string; email: string; }

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);
  private baseUrl = '/api/users';

  getAll(): Observable<User[]> {
    return this.http.get<User[]>(this.baseUrl);
  }

  getById(id: number): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/${id}`);
  }

  create(user: Omit<User, 'id'>): Observable<User> {
    return this.http.post<User>(this.baseUrl, user);
  }

  update(id: number, changes: Partial<User>): Observable<User> {
    return this.http.patch<User>(`${this.baseUrl}/${id}`, changes);
  }

  replace(id: number, user: User): Observable<User> {
    return this.http.put<User>(`${this.baseUrl}/${id}`, user);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
```

The `@Service()` equivalent is a one-line change at the top — drop the
configuration object since `providedIn: 'root'` is the default behavior:

```typescript
import { Service, inject } from '@angular/core';

@Service()
export class UserService {
  private http = inject(HttpClient);
  // ...identical body
}
```

### Using HttpClient in a component

```typescript
import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { UserService } from './user.service';

@Component({
  selector: 'app-user-list',
  standalone: true,
  template: `
    @if (users()) {
      @for (user of users(); track user.id) {
        <div>{{ user.name }} — {{ user.email }}</div>
      }
    } @else {
      <p>Loading…</p>
    }
  `,
})
export class UserListComponent {
  private userService = inject(UserService);

  // toSignal subscribes immediately; initialValue prevents undefined
  users = toSignal(this.userService.getAll(), { initialValue: null });
}
```

### Request options

Every `HttpClient` method accepts an options object:

```typescript
import { HttpParams, HttpHeaders } from '@angular/common/http';

// Query params
this.http.get<Product[]>('/api/products', {
  params: new HttpParams()
    .set('page', 2)
    .set('sort', 'name')
    .set('category', 'electronics'),
  // → /api/products?page=2&sort=name&category=electronics
});

// Or use a plain object — HttpClient converts it automatically
this.http.get<Product[]>('/api/products', {
  params: { page: '2', sort: 'name' },
});

// Custom headers
this.http.post<Order>('/api/orders', orderData, {
  headers: new HttpHeaders({
    'Content-Type': 'application/json',
    'X-Request-ID': crypto.randomUUID(),
  }),
});

// Observe the full HttpResponse (headers, status, body)
this.http.get<User>('/api/me', { observe: 'response' }).subscribe(res => {
  console.log(res.status);          // 200
  console.log(res.headers.get('X-Total-Count'));
  console.log(res.body);            // User
});

// Non-JSON response types
this.http.get('/api/report', { responseType: 'blob' });    // file download
this.http.get('/api/report', { responseType: 'text' });    // plain text
this.http.get('/api/data',   { responseType: 'arraybuffer' });
```

### Cancellation — takeUntilDestroyed

When a component that started a request is destroyed, cancel the in-flight
request to avoid memory leaks and stale updates:

```typescript
import { Component, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({ /* ... */ })
export class SearchComponent {
  private http = inject(HttpClient);
  private destroyRef = inject(DestroyRef);
  results = signal<Result[]>([]);

  search(query: string): void {
    this.http.get<Result[]>('/api/search', { params: { q: query } })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(res => this.results.set(res));
  }
}
```

For sequential requests (cancel the previous if a new one starts), use `switchMap`:

```typescript
this.query$.pipe(
  debounceTime(300),
  switchMap(q => this.http.get<Result[]>('/api/search', { params: { q } })),
  takeUntilDestroyed(this.destroyRef),
).subscribe(results => this.results.set(results));
```

## Real-world patterns

### Pattern 1 — Base service with shared configuration

A base class that handles the common API prefix and shared error handling,
extended by feature services:

```typescript
// api.service.ts — base service
@Injectable({ providedIn: 'root' })
export abstract class ApiService {
  protected http = inject(HttpClient);
  protected abstract path: string;

  protected get<T>(endpoint = ''): Observable<T> {
    return this.http.get<T>(`/api/${this.path}${endpoint}`);
  }

  protected post<T>(body: unknown, endpoint = ''): Observable<T> {
    return this.http.post<T>(`/api/${this.path}${endpoint}`, body);
  }

  protected patch<T>(body: unknown, endpoint = ''): Observable<T> {
    return this.http.patch<T>(`/api/${this.path}${endpoint}`, body);
  }

  protected delete<T>(endpoint = ''): Observable<T> {
    return this.http.delete<T>(`/api/${this.path}${endpoint}`);
  }
}

// products.service.ts — feature service
@Injectable({ providedIn: 'root' })
export class ProductsService extends ApiService {
  protected path = 'products';

  getAll() { return this.get<Product[]>(); }
  getById(id: string) { return this.get<Product>(`/${id}`); }
  create(data: CreateProductDto) { return this.post<Product>(data); }
  updateStock(id: string, stock: number) {
    return this.patch<Product>({ stock }, `/${id}/stock`);
  }
}
```

### Pattern 2 — File upload with progress tracking

```typescript
import { HttpEventType } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class UploadService {
  private http = inject(HttpClient);

  upload(file: File): Observable<{ progress: number; url?: string }> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post('/api/upload', formData, {
      // observe: 'events' gives granular progress + response events
      // reportProgress: true enables progress events for this request
      // Note: requires withXhr() since Fetch doesn't support upload progress
      observe: 'events',
      reportProgress: true,
    }).pipe(
      map(event => {
        switch (event.type) {
          case HttpEventType.UploadProgress:
            const progress = event.total
              ? Math.round(100 * event.loaded / event.total)
              : 0;
            return { progress };
          case HttpEventType.Response:
            return { progress: 100, url: (event.body as any).url };
          default:
            return { progress: 0 };
        }
      }),
    );
  }
}
```

> **Note:** Upload progress requires `withXhr()` because the Fetch API does
> not expose upload progress. For new projects, prefer chunked upload APIs
> or pre-signed URLs (S3, GCS) that eliminate the need for progress tracking.

### Pattern 3 — SSR transfer cache

Angular's HTTP transfer cache prevents double-fetching during hydration.
The server-rendered page embeds the HTTP response in a `<script>` tag;
the client reuses it instead of making a second request:

```typescript
// app.config.ts
import { provideHttpClient } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(), // transfer cache is automatic in SSR apps
  ],
};
```

```typescript
// product.service.ts — same service on server and client
@Injectable({ providedIn: 'root' })
export class ProductService {
  private http = inject(HttpClient);

  // This request runs on the SERVER during SSR.
  // The response is embedded in the HTML.
  // On the CLIENT, Angular returns the cached response instantly.
  // No second network request is made.
  getProduct(id: string): Observable<Product> {
    return this.http.get<Product>(`/api/products/${id}`);
  }
}
```

The transfer cache is enabled automatically when `provideClientHydration()`
and `provideHttpClient()` are both present. Opt individual requests out
with `transferCache: false` in the request options.

## Common mistakes

### Mistake 1 — Subscribing in a service instead of returning the Observable

A common misunderstanding: subscribing in the service means the caller can't
cancel, chain operators, or handle errors themselves:

```typescript
// ❌ Service subscribes — caller has no control
@Injectable({ providedIn: 'root' })
export class UserService {
  users: User[] = [];

  loadUsers(): void {
    this.http.get<User[]>('/api/users').subscribe(u => this.users = u);
  }
}

// ✅ Service returns Observable — caller decides how to consume
@Injectable({ providedIn: 'root' })
export class UserService {
  getUsers(): Observable<User[]> {
    return this.http.get<User[]>('/api/users');
  }
}
```

The returned Observable is lazy — the HTTP request doesn't fire until
`.subscribe()` or `toSignal()` is called by the consumer.

### Mistake 2 — Using withFetch() explicitly

`withFetch()` is deprecated as of Angular v22. Fetch is now the default:

```typescript
// ❌ Deprecated — withFetch() is no longer needed and will warn
provideHttpClient(withFetch())

// ✅ Fetch is the default — no option needed
provideHttpClient()

// ✅ If you need XHR (e.g. upload progress)
provideHttpClient(withXhr())
```

### Mistake 3 — Not unsubscribing from long-lived HTTP streams

Most HTTP requests complete after one emission, so leak risk is low. But if
you subscribe manually and the component is destroyed mid-request, you can
get stale updates or errors after the component is gone:

```typescript
// ❌ If the component is destroyed, the subscription is still alive
ngOnInit(): void {
  this.http.get<User[]>('/api/users').subscribe(users => {
    this.users = users;  // component might be destroyed by now
  });
}

// ✅ Use takeUntilDestroyed or toSignal — both auto-clean up
users = toSignal(this.http.get<User[]>('/api/users'), { initialValue: [] });
```

### Mistake 4 — Setting Content-Type manually for JSON

`HttpClient` sets `Content-Type: application/json` automatically when you
pass a JavaScript object as the body. Setting it manually is redundant and
can cause issues with certain CORS setups:

```typescript
// ❌ Redundant — HttpClient already sets application/json
this.http.post('/api/users', userData, {
  headers: { 'Content-Type': 'application/json' },
});

// ✅ Let HttpClient handle it
this.http.post('/api/users', userData);
```

The exception: `FormData` bodies should not have `Content-Type` set at all
(the browser must set it to include the multipart boundary).

## How this evolved

> - **Angular 2–3 (2016–2017):** `@angular/http` — XHR-based, no interceptors,
>   manual `res.json()` parsing, NgModule-only configuration.
>
> - **Angular 4 (2017):** `HttpClient` introduced in `@angular/common/http` —
>   typed responses, interceptor pipeline, testing utilities. `@angular/http`
>   deprecated. Both packages coexisted for migration.
>
> - **Angular 8 (2019):** `@angular/http` and `HttpModule` removed entirely.
>   `HttpClient` is the only option.
>
> - **Angular 15 (2022):** Functional interceptors introduced via
>   `withInterceptors([...])` — plain functions instead of classes.
>   Class-based interceptors (`withInterceptorsFromDi`) remain supported
>   but are no longer recommended.
>
> - **Angular 16.1 (2023):** `withFetch()` added as an opt-in Fetch backend.
>   Recommended for SSR for performance and Node-compatibility reasons.
>
> - **Angular 18 (2024):** HTTP transfer cache for SSR stabilized — automatic
>   when `provideClientHydration()` is present.
>
> - **Angular 21 (2025):** `HttpClient` provided in root by default —
>   `provideHttpClient()` becomes optional when no feature configuration is
>   needed.
>
> - **Angular v22 (now):** Fetch becomes the **default** HTTP backend.
>   `withFetch()` deprecated (no longer needed). `withXhr()` available to opt
>   back into XHR, but XHR server support deprecated (removal in v23).
>   `httpResource()` and `rxResource()` stable as signal-based alternatives for
>   GET requests. The recommended pipeline: `provideHttpClient()` with
>   functional interceptors via `withInterceptors()` for all new code.

## See also

- [Interceptors](./interceptors.md) — the full interceptor pipeline: auth
  headers, retry logic, caching, error normalization
- [Error Handling](./error-handling.md) — `catchError`, `HttpErrorResponse`,
  retry strategies, and global error handlers
- [Signals](../reactivity/signals.md) — `httpResource()` as the signal-based
  alternative for GET requests
- [SSR & Hydration](../rendering/ssr-hydration.md) — how the HTTP transfer
  cache works during hydration
- [Official docs — Setting up HttpClient](https://angular.dev/guide/http/setup)
- [Official docs — Making requests](https://angular.dev/guide/http/making-requests)

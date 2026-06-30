---
recipe_id: "jwt-interceptor-circular-dep"
title: "JWT Interceptor: Breaking the Circular Dependency"
file: "recipes/auth/jwt-interceptor-circular-dep.md"
primary_concept: "dependency-injection/dependency-injection"
related_concepts: ["http/http", "http/interceptors"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# JWT Interceptor: Breaking the Circular Dependency

> **What you'll build:** the canonical auth setup — a JWT interceptor that
> attaches `Authorization: Bearer …` to every outgoing request — without
> hitting the textbook circular-dependency error that bites everyone the
> first time they wire it up. Plus the architectural pivot (extract a
> `TokenService`) that fixes it for real, and the one runtime case where
> lazy injection is still the right tool.
>
> **Concepts you'll touch:** [Dependency Injection](../../dependency-injection/dependency-injection.md), [HTTP](../../http/http.md), [HTTP Interceptors](../../http/interceptors.md)
>
> **Time:** ~25 minutes to read; ~45 minutes to retrofit into an existing
> app that already has the bug.

---

## The scenario

You're building authentication for a new Angular app. You write:

```typescript
// auth.service.ts — first attempt
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  login(credentials: Credentials) {
    return this.http.post<LoginResponse>('/api/auth/login', credentials);
  }

  logout() {
    localStorage.removeItem('access_token');
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }
}
```

Then a JWT interceptor that reads the token from `AuthService` and attaches
it to every request:

```typescript
// jwt.interceptor.ts — first attempt (broken)
@Injectable()
export class JwtInterceptor implements HttpInterceptor {
  constructor(private readonly authService: AuthService) {}  // ← the trap

  intercept(req: HttpRequest<unknown>, next: HttpHandler) {
    const token = this.authService.getToken();
    if (token) {
      req = req.clone({
        setHeaders: { Authorization: `Bearer ${token}` },
      });
    }
    return next.handle(req);
  }
}
```

You wire it up, hit `ng serve`, and the console explodes:

```text
NG0200: Circular dependency in DI detected for AuthService.
```

What just happened:

- `AuthService` depends on `HttpClient`
- `HttpClient` is built from a chain that includes **all registered interceptors**
- `JwtInterceptor` is one of those interceptors, and it depends on `AuthService`
- To build `AuthService`, Angular needs `HttpClient`. To build `HttpClient`,
  it needs `JwtInterceptor`. To build `JwtInterceptor`, it needs
  `AuthService`. To build `AuthService`…

A perfect circle. Angular has no choice but to throw `NG0200`.

This isn't a beginner mistake — it's a structural property of how interceptors compose with `HttpClient`. Every team building auth from scratch hits it on day one or two.

---

## The Google-result fix — lazy injection via `Injector`

Search "Angular NG0200 JwtInterceptor" and the first answer you'll find is **lazy injection**: stop depending on `AuthService` directly; depend on `Injector` instead, and only resolve `AuthService` when a request actually flows through the interceptor.

```typescript
// jwt.interceptor.ts — the lazy-injection fix (v22 functional form)
import { HttpInterceptorFn } from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { AuthService } from './auth.service';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const injector = inject(Injector);

  // Resolved at REQUEST time, not at interceptor-registration time.
  // By the time a request flows through, AuthService is already constructed
  // and sitting in the injector cache.
  const authService = injector.get(AuthService);

  const token = authService.getToken();
  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }
  return next(req);
};
```

And the v22 registration in `app.config.ts`:

```typescript
import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { jwtInterceptor } from './auth/jwt.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([jwtInterceptor])),
  ],
};
```

The error goes away. Requests get tokens attached. Ship it, right?

### Why this works (and what it costs)

What broke the cycle: the interceptor no longer asks for `AuthService` at the moment it's *registered*. It asks for `Injector` (which always exists) and defers the `AuthService` lookup until the first HTTP request flows. By that time, `HttpClient` has been fully constructed, `AuthService` has been instantiated lazily, and `injector.get(AuthService)` returns the cached instance.

See [Dependency Injection — Lazy injection as an escape hatch](../../dependency-injection/dependency-injection.md#lazy-injection--injector-as-an-escape-hatch) for the full mechanism deep-dive.

What you pay:

- **The `AuthService` dependency is invisible to the analyzer.** Refactor `AuthService` away and the interceptor still type-checks; you find out at runtime.
- **You've masked an architectural problem with a tactical workaround.** The cycle exists because `AuthService` is doing too many things — it's both the "I make HTTP login calls" service AND the "I hold the token" service. Lazy injection lets you ship without confronting that.

The v22-functional-interceptor form is more idiomatic than the class-based version (covered below as legacy), but it doesn't address the structural smell. For that, we need a real refactor.

### The class-based legacy form (preserved for migration context)

If you're migrating an older codebase, you'll see the class-based variant of this pattern. Same idea, different shape:

<!-- legacy: pre-v15 class-based interceptor — modernized in the upgrade pass -->
```typescript
// Pre-v15: class-based interceptor with Injector for lazy lookup
@Injectable()
export class JwtInterceptor implements HttpInterceptor {
  constructor(private readonly injector: Injector) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler) {
    const authService = this.injector.get(AuthService);
    const token = authService.getToken();
    if (token) {
      req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
    }
    return next.handle(req);
  }
}
```

And the registration in the legacy `AppModule`:

<!-- legacy: pre-standalone NgModule registration — modernized in the upgrade pass -->
```typescript
@NgModule({
  imports: [HttpClientModule],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: JwtInterceptor,
      multi: true,
    },
  ],
})
export class AppModule {}
```

Both forms — functional and class-based — implement the same fix. The v22 functional form is shorter and doesn't need an `@Injectable()` decorator or a multi-provider registration. New code should use it.

---

## The architectural fix — extract `TokenService`

The cycle exists because `AuthService` is doing two things:

1. **Speaking to the auth API** (`login`, `logout`, `refreshToken`) — requires `HttpClient`
2. **Holding the token** (`getToken`, `saveToken`) — doesn't require anything

Those are two **different responsibilities**, glued together because they're conceptually about "auth." That's a Single Responsibility Principle violation. Split them, and the cycle disappears.

```typescript
// File: token.service.ts — depends on nothing
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TokenService {
  private readonly TOKEN_KEY = 'access_token';

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  saveToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  removeToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
  }
}
```

```typescript
// File: jwt.interceptor.ts — depends on TokenService (no cycle)
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { TokenService } from './token.service';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const tokenService = inject(TokenService);
  const token = tokenService.getToken();

  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }
  return next(req);
};
```

```typescript
// File: auth.service.ts — depends on HttpClient + TokenService (no cycle)
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs/operators';
import { TokenService } from './token.service';

interface LoginResponse { accessToken: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenService = inject(TokenService);

  login(credentials: Credentials) {
    return this.http.post<LoginResponse>('/api/auth/login', credentials).pipe(
      tap(response => {
        if (response?.accessToken) {
          this.tokenService.saveToken(response.accessToken);
        }
      }),
    );
  }

  logout() {
    this.tokenService.removeToken();
  }
}
```

### Why this fixes everything

The dependency graph is now **linear and acyclic**:

```text
            TokenService
            (depends on nothing)
              ▲         ▲
              │         │
   ┌──────────┘         └──────────┐
   │                               │
JwtInterceptor                AuthService
(uses TokenService)           (uses HttpClient + TokenService)
```

No service depends on something that depends on it. Angular can construct everything in topological order at startup. No `Injector` needed. No lazy lookups. No NG0200.

You've also **made the codebase honest about its responsibilities.** `TokenService` does one thing. `AuthService` does one thing. `JwtInterceptor` does one thing. Refactoring storage from localStorage to sessionStorage (or in-memory — see the [Token Storage Security](./token-storage-security.md) recipe) touches one file. Testing one piece doesn't require mocking another's HTTP dependencies.

### The rule of thumb

Whenever you're tempted to break a cycle with lazy injection, **first try to extract the shared concern into a third service.** The cycle is almost always a signal that two services have overlapping responsibilities. The architectural fix is cheaper than the workaround, and you write it once.

---

## When lazy injection is STILL necessary — the 401 refresh case

Even after the SRP refactor, there's one runtime case where the cycle genuinely re-emerges: **handling 401 Unauthorized by refreshing the token and retrying the request.**

The scenario: a request goes out → the access token has expired → the server returns 401 → the interceptor needs to call `authService.refreshToken()` (which fires another HTTP request) → wait for the new token → retry the original request with the new token.

That introduces a new cycle:

```text
JwtInterceptor ──needs──> AuthService.refreshToken()
                              │
                              │ uses
                              ▼
                          HttpClient
                              │
                              │ goes through
                              ▼
                          JwtInterceptor   ◄── cycle
```

This cycle is **only triggered at runtime, when a 401 actually fires** — not at construction time. So the SRP refactor doesn't help; the dependency *exists* (the interceptor genuinely needs to call into `AuthService` mid-request) and the *call* is what completes the loop.

This is precisely the case lazy injection is designed for:

```typescript
// File: jwt.interceptor.ts — happy path + 401 handling
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { TokenService } from './token.service';
import { AuthService } from './auth.service';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const tokenService = inject(TokenService);
  // Inject Injector — but DON'T call .get(AuthService) eagerly.
  // We only need AuthService if a 401 fires, which is rare and runtime-only.
  const injector = inject(Injector);

  const token = tokenService.getToken();
  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        return handle401(req, next, injector, tokenService);
      }
      return throwError(() => error);
    }),
  );
};

function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  injector: Injector,
  tokenService: TokenService,
) {
  // LAZY: resolve AuthService only now, at the moment of error.
  // HttpClient is fully wired up at this point; no construction-time cycle.
  const authService = injector.get(AuthService);

  return authService.refreshToken().pipe(
    switchMap(response => {
      tokenService.saveToken(response.accessToken);
      const retried = req.clone({
        setHeaders: { Authorization: `Bearer ${response.accessToken}` },
      });
      return next(retried);
    }),
    catchError(err => {
      authService.logout();
      return throwError(() => err);
    }),
  );
}
```

The pattern: **inject `TokenService` eagerly** (its construction has no cycle), but **inject `Injector` for the AuthService lookup** and defer that resolution to the error branch. By the time a 401 fires, the entire DI graph is already built and `injector.get(AuthService)` returns the cached instance.

### Why this matters

Two distinct uses of lazy injection live in the same codebase, but for different reasons:

| Scenario | Resolved by | Reason |
| --- | --- | --- |
| Reading the token to attach to every request | Direct `inject(TokenService)` | No cycle exists — SRP refactor eliminated it |
| Calling `refreshToken()` on 401 | `injector.get(AuthService)` in the error handler | The cycle is genuine at runtime; only deferred resolution avoids it |

That's the takeaway. Lazy injection isn't a blanket workaround for "anytime I see a cycle." It's the **right tool when the cycle is genuine and runtime-only** — and it's the **wrong tool when an SRP refactor would prevent the cycle from existing in the first place**.

### Production extension — the refresh queue

The 401 handler above has one production-relevant gap: if **multiple requests** fire 401 in parallel (which happens whenever a token expires while the user is on a page that loads several resources at once), each one will independently call `authService.refreshToken()`. You'll get N refresh calls when one would do.

The fix is a **refresh queue**: while a refresh is in flight, subsequent 401s wait for the new token instead of triggering their own refresh. The standard implementation uses a `BehaviorSubject` to broadcast the new token, and queued requests retry once it arrives.

That's covered in detail in the [Token Storage Security](./token-storage-security.md) recipe, since the queueing strategy and the token-storage strategy interact (where the token lives determines how easily multiple interceptor instances can read it).

---

## Trade-offs and when NOT to use each pattern

**Use functional interceptors + SRP refactor (the main path) when:**

- Building auth from scratch in a v22 project — this is the default
- Migrating an existing class-based interceptor — the SRP split also fixes long-standing testability problems
- You have any other services that depend on `AuthService` and might form their own cycles down the road

**Use lazy injection (`Injector.get`) when:**

- A genuine runtime cycle exists that no refactor can eliminate (the 401 refresh case)
- You're maintaining a class-based interceptor in a pre-v15 codebase and migrating to functional isn't yet on the schedule
- You're writing a library where the consumer's service shape is unknown and you need to optionally interact with services that may or may not be provided

**Don't use lazy injection when:**

- You haven't tried an SRP refactor first. The cycle is almost always a signal.
- The dependency relationship is genuinely uni-directional (Service A uses Service B; Service B uses nothing else). There's no cycle to break.
- You're attracted to the indirection because it "feels more flexible." It's not flexibility — it's invisibility to the type checker.

### Common pitfalls

- **Calling `injector.get(AuthService)` eagerly at the top of the interceptor** defeats the entire purpose. The resolution must happen *inside* the request-handling flow (or the error branch), not at interceptor setup.
- **Forgetting to register `withInterceptors([jwtInterceptor])`** silently means no auth header gets attached and every API call returns 401. Easy to miss because there's no compile error.
- **Mixing class-based and functional interceptors** in the same `app.config.ts` — use `withInterceptors` for functional, `withInterceptorsFromDi` for class-based. They can coexist but each needs its own feature function.
- **Storing the token in `AuthService` instead of `TokenService`** even after extracting the service. The refactor only works if the storage actually lives in the leaf service; otherwise you've just moved the file boundary, not the responsibility.
- **`throwError(error)` instead of `throwError(() => error)`** — the non-factory form is deprecated since RxJS 7. The factory form is the only one that works correctly with synchronous error reporting and stack-trace preservation.
- **Calling `tokenService.removeToken()` inside the interceptor on 401** instead of in `authService.logout()`. Keeps the interceptor stateless; centralizes the "what does logout mean" decision in one place.

---

## See also

- [Dependency Injection — Lazy injection as an escape hatch](../../dependency-injection/dependency-injection.md#lazy-injection--injector-as-an-escape-hatch) — the mechanism deep-dive: why `Injector.get()` breaks construction-time cycles
- [HTTP](../../http/http.md) — `HttpClient`, `HttpInterceptorFn`, `provideHttpClient`
- [HTTP Interceptors](../../http/interceptors.md) — concept-level coverage of interceptor primitives
- [Token Storage Security](./token-storage-security.md) — next recipe in this series: where tokens should actually live (RAM vs localStorage vs HttpOnly cookie), and the refresh queue for parallel 401s
- [App Initialization](./app-initialization.md) — handling F5 reload and silent token restoration
- [Step-up Authentication](./step-up-authentication.md) — scope-based re-auth for sensitive actions

## References

- [`provideHttpClient` API (angular.dev)](https://angular.dev/api/common/http/provideHttpClient)
- [`withInterceptors` API (angular.dev)](https://angular.dev/api/common/http/withInterceptors)
- [`HttpInterceptorFn` API (angular.dev)](https://angular.dev/api/common/http/HttpInterceptorFn)
- [Angular DI guide — Hierarchical injectors (angular.dev)](https://angular.dev/guide/di/hierarchical-dependency-injection)
- [NG0200 — Circular dependency in DI detected (angular.dev)](https://angular.dev/errors/NG0200)

## Demo source

This recipe is synthesized from a real-world Angular auth setup walkthrough rather than a single demo file. The patterns mirror what most production Angular apps implement once they pass the "ship it" phase — the SRP refactor is the single biggest improvement most auth codebases see when they're cleaned up.
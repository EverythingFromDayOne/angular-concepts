---
recipe_id: "token-storage-security"
title: "Token Storage: Where Tokens Should Actually Live"
file: "recipes/auth/token-storage-security.md"
primary_concept: "http/http"
related_concepts: ["dependency-injection/dependency-injection", "reactivity/signals", "http/interceptors"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Token Storage: Where Tokens Should Actually Live

> **What you'll build:** a token-storage architecture that survives the
> real-world threat model — short-lived access tokens in JS memory (signal),
> long-lived refresh tokens in HttpOnly cookies managed by the server, plus
> the refresh-queue coordination pattern that prevents N parallel 401s from
> triggering N parallel refresh calls.
>
> **Concepts you'll touch:** [HTTP](../../http/http.md), [Dependency Injection](../../dependency-injection/dependency-injection.md), [Signals](../../reactivity/signals.md), [HTTP Interceptors](../../http/interceptors.md)
>
> **Time:** ~25 minutes to read; ~2 hours to retrofit an existing localStorage-based auth system without breaking the login flow.

---

## The scenario

You built auth with the architecture from [JWT Interceptor: Breaking the Circular Dependency](./jwt-interceptor-circular-dep.md). `TokenService` reads and writes `localStorage`. `AuthService` calls login, gets a token, saves it. `JwtInterceptor` reads the token, attaches the header. Works.

Then someone on your team asks: "what happens if a malicious npm package gets into our build?"

You realize: any JavaScript running on your origin can read `localStorage.getItem('access_token')`. That includes:

- A compromised third-party library (`event-stream`, `node-ipc`, the `colors.js` incident)
- A typosquatted package someone in your team installed by accident
- An XSS payload via an unescaped user input
- A browser extension that runs content scripts
- A library that thinks logging "for debugging" includes localStorage values

If any of those exists, your tokens are exfiltrated. The attacker doesn't need a session cookie — they have a long-lived auth token they can replay from anywhere.

This recipe is about the architecture that survives that scenario. Not because XSS is common, but because **the attack surface is meaningfully different** depending on where you put the tokens.

## The threat model in three sentences

**Anything in `localStorage` or `sessionStorage` is readable by any JavaScript running on your origin.** That's the storage spec — there's no permission model, no scope, no access control. If a script runs, it can read.

**Anything in JavaScript variables (signals, Subjects, plain objects) is also reachable by any JavaScript on your origin**, but it's harder — the attacker has to find the reference (e.g., walking the component tree, accessing the global Angular ref). Friction is real defense even when it's not absolute.

**Anything in an `HttpOnly` cookie is genuinely invisible to JavaScript.** The cookie is sent automatically with HTTP requests but cannot be read via `document.cookie`. That's enforced by the browser, not by your code, so an attacker would need a browser bug to bypass it.

The architectural answer falls out of those three observations: **put the long-lived secret in an HttpOnly cookie; put the short-lived working token in JS memory.**

---

## The canonical hybrid architecture

| Token | Lifetime | Where it lives | Why |
| --- | --- | --- | --- |
| **Access token** | 5–15 minutes | JS memory (signal) | Used on every request; must be readable by JS to attach as a header. Short lifetime caps the blast radius if it's stolen. |
| **Refresh token** | days to weeks | HttpOnly cookie | Used only when access token expires; doesn't need JS access. Long lifetime → high value → must be invisible to JS. |

The flow at runtime:

1. **Login** — user submits credentials. Server validates, returns `accessToken` in the response body **and** sets a `Set-Cookie: refresh_token=…; HttpOnly; Secure; SameSite=Strict` header. The browser stores the cookie; JS never sees it. Angular stores the access token in memory.

2. **Normal requests** — interceptor reads the access token from memory, attaches `Authorization: Bearer …`. The HttpOnly cookie is also sent (browsers attach cookies automatically), but the server ignores it on normal API calls — it only checks the bearer token.

3. **Access token expires** — server returns `401 Unauthorized`. Interceptor catches it, fires a request to `POST /api/auth/refresh`. The browser **automatically attaches the HttpOnly cookie** to that request. Server validates the cookie, returns a fresh access token. Angular saves the new access token to memory, retries the original request.

4. **F5 / page reload** — JS memory is wiped. Access token is gone. The app fires the refresh call on startup; the cookie restores the session without the user re-entering credentials. (Covered in detail in [App Initialization](./app-initialization.md).)

5. **Logout** — Angular calls `POST /api/auth/logout`. Server clears the cookie via `Set-Cookie: refresh_token=; Max-Age=0`. Angular clears the in-memory token. Both layers cleaned up.

The user never sees the choreography. They log in once, browse for a month, and don't think about auth.

---

## Implementation — `TokenService` with in-memory storage

The token service uses a signal as the storage primitive. Synchronous reads (what the interceptor needs) are a one-line getter; reactive consumers (UI components that show "logged in as …") can convert to an observable or use the signal directly in templates.

```typescript
// File: token.service.ts
import { Injectable, computed, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TokenService {
  // Single source of truth — in-memory only. Wiped on reload, on tab close,
  // and on any process restart. Never written to localStorage.
  private readonly accessToken = signal<string | null>(null);

  /** Synchronous read for the interceptor. Returns null when logged out. */
  getToken(): string | null {
    return this.accessToken();
  }

  /** Reactive read for components ("logged in" indicator, header bar). */
  readonly isAuthenticated = computed(() => this.accessToken() !== null);

  saveToken(token: string): void {
    this.accessToken.set(token);
  }

  clear(): void {
    this.accessToken.set(null);
    // Note: no localStorage cleanup needed — we never wrote there.
    // The refresh token cookie is cleared server-side by /api/auth/logout.
  }
}
```

**Three things worth absorbing:**

- **The signal is `private`.** Consumers go through `getToken()` (sync) or `isAuthenticated` (reactive). The signal itself stays encapsulated — that way, swapping the storage primitive later (to a Subject, an in-memory cache with TTL, anything) touches only this file.
- **`computed(() => this.accessToken() !== null)`** gives every component a reactive `isAuthenticated` signal for free. No subscribing, no async pipe; just `{{ tokenService.isAuthenticated() ? '…' : '…' }}` in templates.
- **No localStorage anywhere.** Not even as a fallback. Once you decide tokens live in memory, the deletion of localStorage code is the deletion of an attack surface.

---

## Implementation — `AuthService` with cookie-aware HTTP

The auth service calls the server. Login and refresh both need `withCredentials: true` so the browser will send and accept cookies on the cross-origin call.

```typescript
// File: auth.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';
import { TokenService } from './token.service';

interface LoginResponse { accessToken: string; }
interface RefreshResponse { accessToken: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenService = inject(TokenService);
  private readonly router = inject(Router);

  login(credentials: { email: string; password: string }) {
    return this.http
      .post<LoginResponse>('/api/auth/login', credentials, {
        // Required so the browser ACCEPTS the Set-Cookie from the response.
        withCredentials: true,
      })
      .pipe(
        tap(response => {
          if (response?.accessToken) {
            this.tokenService.saveToken(response.accessToken);
          }
        }),
      );
  }

  refreshToken() {
    // No body needed — the refresh token rides in the HttpOnly cookie.
    return this.http.post<RefreshResponse>(
      '/api/auth/refresh',
      {},
      {
        // Required so the browser SENDS the HttpOnly cookie with the request.
        withCredentials: true,
      },
    );
  }

  logout() {
    return this.http
      .post('/api/auth/logout', {}, { withCredentials: true })
      .pipe(
        tap(() => {
          this.tokenService.clear();
          this.router.navigate(['/login']);
        }),
      );
  }
}
```

### The `withCredentials: true` gotcha

Three things must line up for cookies to work on cross-origin requests:

1. **The Angular call must set `withCredentials: true`** on the request options.
2. **The server must respond with `Access-Control-Allow-Credentials: true`** in the CORS preflight.
3. **The server's `Access-Control-Allow-Origin` must be a specific origin, not `*`.** Browsers explicitly forbid wildcard origins on credentialed requests.

If any one is missing, the browser silently drops the cookie. You get no error in the console — the request just doesn't carry the credential. Symptom: refresh always returns 401 even though it works in Postman.

For local development (`localhost:4200` Angular hitting `localhost:3000` API), set `withCredentials: true` and have the API echo back `Access-Control-Allow-Origin: http://localhost:4200`. Production typically runs same-origin behind a reverse proxy, so the CORS dance disappears entirely.

---

## Implementation — interceptor with 401 refresh

This is the v22-functional interceptor from the [previous recipe](./jwt-interceptor-circular-dep.md#when-lazy-injection-is-still-necessary--the-401-refresh-case), extended with the refresh-queue pattern.

```typescript
// File: jwt.interceptor.ts
import {
  HttpErrorResponse,
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { BehaviorSubject, throwError } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { TokenService } from './token.service';
import { AuthService } from './auth.service';
import { RefreshCoordinator } from './refresh-coordinator.service';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip the auth header on the refresh endpoint itself — sending an
  // expired token would cause this very call to loop into another 401.
  if (req.url.endsWith('/api/auth/refresh') || req.url.endsWith('/api/auth/login')) {
    return next(req.clone({ withCredentials: true }));
  }

  const tokenService = inject(TokenService);
  const injector = inject(Injector);
  const token = tokenService.getToken();

  const authedReq = token ? attachToken(req, token) : req;

  return next(authedReq).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        return handle401(req, next, injector);
      }
      return throwError(() => error);
    }),
  );
};

function attachToken(req: HttpRequest<unknown>, token: string) {
  return req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  });
}

function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  injector: Injector,
) {
  const coordinator = injector.get(RefreshCoordinator);
  const tokenService = injector.get(TokenService);

  // First 401 in this refresh window — kick off the refresh.
  if (!coordinator.isRefreshing()) {
    coordinator.startRefresh();
    const authService = injector.get(AuthService);

    return authService.refreshToken().pipe(
      switchMap(response => {
        tokenService.saveToken(response.accessToken);
        coordinator.completeRefresh(response.accessToken);
        return next(attachToken(req, response.accessToken));
      }),
      catchError(err => {
        coordinator.failRefresh();
        injector.get(AuthService).logout().subscribe();
        return throwError(() => err);
      }),
    );
  }

  // Subsequent 401s while a refresh is already in flight — queue and wait.
  return coordinator.waitForNewToken().pipe(
    switchMap(newToken => next(attachToken(req, newToken))),
  );
}
```

### Why the URL check at the top matters

`POST /api/auth/refresh` flows through the interceptor like any other request. If we attach an expired access token to it, two things can happen:

1. The server might reject the refresh call because the bearer token is malformed/expired, even though the cookie is valid.
2. The refresh response itself might return 401, which would trigger another refresh attempt, which would attach the same expired token, infinite loop.

The simplest fix: **skip the auth header on the refresh and login endpoints entirely.** Those endpoints don't need a bearer token — they're authenticated by the cookie (refresh) or the credentials in the body (login). The endpoint-specific check at the top of the interceptor is two lines and prevents a class of subtle bugs.

---

## The refresh queue — `RefreshCoordinator`

The pattern the interceptor leans on:

- **One refresh call at a time, regardless of how many 401s fire.**
- **Requests that 401 while a refresh is already in flight wait for it**, then retry with the new token.

This is coordination state, separate from the token storage itself. Living in its own service keeps `TokenService` focused on "what's the current token" and lets the coordinator focus on "is anyone refreshing right now."

```typescript
// File: refresh-coordinator.service.ts
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { filter, take } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class RefreshCoordinator {
  // Holds the latest token after a successful refresh. Starts null.
  // Subscribers wait for non-null emissions (a successful refresh).
  private readonly tokenStream = new BehaviorSubject<string | null>(null);
  private refreshing = false;

  isRefreshing(): boolean {
    return this.refreshing;
  }

  startRefresh(): void {
    this.refreshing = true;
    // Clear the previous value so subscribers wait for the NEW token,
    // not the (now stale) previous one.
    this.tokenStream.next(null);
  }

  completeRefresh(newToken: string): void {
    this.refreshing = false;
    this.tokenStream.next(newToken);
  }

  failRefresh(): void {
    this.refreshing = false;
    // Don't emit — subscribers will time out via their own mechanisms
    // or get killed by the logout that follows.
  }

  /** Wait for the in-flight refresh to complete, then emit the new token once. */
  waitForNewToken(): Observable<string> {
    return this.tokenStream.pipe(
      filter((t): t is string => t !== null),
      take(1),
    );
  }
}
```

### Why `BehaviorSubject` and not a signal here

The coordinator's job is "tell waiting requests when a new token arrives." That's an event-stream concern, not a value concern. `BehaviorSubject` is the right primitive for "broadcast to multiple subscribers, each gets the latest value once it lands."

A signal would work for the value but lacks the "subscribe-and-take(1)" semantics out of the box. You can build it with `toObservable(signal).pipe(skip(1), filter(...), take(1))`, but that's more code than the Subject for the same behavior. Signals are for sync reactive reads; this is a multi-consumer broadcast.

The `private refreshing: boolean` flag is intentionally a plain field rather than a signal — nothing watches it reactively, and a synchronous check in the interceptor is exactly what we want.

---

## The full app-config wiring

```typescript
// File: app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { jwtInterceptor } from './auth/jwt.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([jwtInterceptor])),
  ],
};
```

Three services (`TokenService`, `AuthService`, `RefreshCoordinator`) are all `providedIn: 'root'` so no further registration is needed.

---

## Decision matrix — when localStorage is actually fine

The hybrid architecture above is the **right answer for high-value applications**. But it's not free — there's API work (cookie endpoints), CORS configuration, and a more involved refresh flow. For some applications, plain localStorage is the appropriate trade-off.

| Application type | Storage choice | Rationale |
| --- | --- | --- |
| **Financial / fintech / banking** | Hybrid (memory + HttpOnly cookie) | Stolen tokens transfer money. Worst-case scenario is unacceptable; cost of hybrid is irrelevant. |
| **Medical / EHR / healthcare** | Hybrid | Regulatory requirements (HIPAA-class) often mandate it; patient data is similarly catastrophic to lose. |
| **E-commerce with stored payment methods, loyalty points, or wallet** | Hybrid | Stolen token = stolen wallet/saved cards. Industry standard for major platforms (Shopee, Amazon, Lazada). |
| **B2B SaaS handling business data** | Hybrid for production; localStorage acceptable in dev | Customer data exfiltration is a brand-ending event; competitive parity matters. |
| **Social / messaging / forums** | Hybrid for messaging apps; localStorage often acceptable for forums | Direct messages and contact lists are sensitive; public-by-default content less so. |
| **Internal tools behind a VPN** | localStorage usually acceptable | XSS attack surface is much smaller; convenience often outweighs marginal risk. |
| **Small B2C with no payments / no stored cards** | localStorage acceptable | Worst case is account recovery via email reset; impact is bounded. |
| **MVPs, prototypes, demos** | localStorage acceptable | Refactor when you know the product is real. The hybrid architecture is non-trivial to add; don't pay for it before you need it. |

### The e-commerce-specific story

E-commerce sits in a gray zone that's worth thinking about explicitly. A site with **only product browsing and cart, plus checkout via Stripe or VNPay redirect**, can legitimately use localStorage — the worst case is someone places fraudulent orders that the COD process catches, or the third-party payment gateway rejects.

A site with **stored payment methods (tokenized cards on file), loyalty points, or a wallet balance** *must* use the hybrid architecture. Stolen access tokens become stolen money. Even one incident wipes out the cost savings from skipping the hybrid setup, plus the reputational damage.

The decision point usually comes when you add the second tier of features — wallet, saved cards, one-click checkout. That's the migration moment. If you're building from scratch and you *know* those features are coming, build the hybrid from day one.

---

## Trade-offs and common pitfalls

**Use the hybrid architecture when:**

- The token, if stolen, allows actions you wouldn't reverse easily (money transfer, data export, identity actions)
- Your industry has compliance pressure (HIPAA, PCI-DSS, GDPR for sensitive data)
- The application has any feature that touches saved payment instruments

**Stay with localStorage when:**

- You're building an MVP and need to ship fast
- The app is internal, behind a VPN, with no public attack surface
- The worst-case theft impact is bounded (account reset solves it)
- You don't yet have backend support for HttpOnly cookies and refresh endpoints

**Common pitfalls:**

- **Forgetting `withCredentials: true` on the login call.** The server tries to set the cookie, the browser drops it (because credentials weren't enabled for the request), and the refresh endpoint returns 401 forever. Symptom: works in Postman, fails in the browser.
- **Setting `Access-Control-Allow-Origin: *`** on a credentialed endpoint. Browsers reject the response outright. The origin must be specific.
- **Cookie attributes**: `HttpOnly` blocks JS access (the security win). `Secure` requires HTTPS (always set in production). `SameSite=Strict` blocks cross-site requests (correct default; `Lax` if you need cross-site flows; never `None` without `Secure`).
- **Storing the refresh token in JS at any point**. If your refresh endpoint returns the refresh token in the body "for convenience," that defeats the entire architecture — the token is now JS-readable. The refresh token must only travel in the cookie.
- **No URL check at the top of the interceptor.** Attaching a stale bearer token to `/api/auth/refresh` causes hard-to-debug 401 loops.
- **Mutating the signal from inside an `effect` that also reads it.** If a UI effect reads `isAuthenticated` and reactively triggers something that updates the token, you get a cycle. Keep token mutations confined to service methods called from explicit events (login response, refresh response, logout).
- **Forgetting to clear the in-memory token on logout.** localStorage cleanup is obvious; in-memory cleanup is easier to miss. The `TokenService.clear()` call on logout is load-bearing.
- **The refresh queue subscribing too late.** If you start the refresh and then queue a request, but the refresh emits the new token *before* the queued request subscribes, the queued request waits forever for the next emission. `BehaviorSubject` handles this correctly because it replays the latest value to new subscribers — but only after the value is set. Always call `startRefresh()` (which emits `null`) before kicking off the refresh observable.

---

## See also

- [JWT Interceptor: Breaking the Circular Dependency](./jwt-interceptor-circular-dep.md) — the previous recipe; the SRP refactor and lazy-injection mechanics this recipe builds on
- [App Initialization](./app-initialization.md) — handling the F5/reload case where in-memory tokens are lost
- [Step-up Authentication](./step-up-authentication.md) — scope-based re-auth for sensitive actions like payment
- [HTTP](../../http/http.md) — `HttpClient`, request options, `withCredentials`
- [Signals](../../reactivity/signals.md) — `signal()`, `computed()`, when to reach for signals vs Subjects
- [Dependency Injection — Lazy injection](../../dependency-injection/dependency-injection.md#lazy-injection--injector-as-an-escape-hatch) — the mechanism for the `Injector.get(AuthService)` call in the 401 handler

## References

- [`HttpClient` request options (angular.dev)](https://angular.dev/api/common/http/HttpClient)
- [`withInterceptors` API (angular.dev)](https://angular.dev/api/common/http/withInterceptors)
- [HttpOnly cookies (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#restrict_access_to_cookies)
- [`SameSite` cookies (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)
- [`Access-Control-Allow-Credentials` (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Credentials)
- [OWASP — JWT Cheatsheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [OWASP — XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

## Demo source

Synthesized from real-world Angular auth setup walkthroughs rather than a single demo file. The threat model and architecture decisions reflect the consensus pattern across high-value applications (banks, fintechs, large e-commerce platforms). All code is original; Vietnamese-language conversation context that informed the recipe (including the e-commerce decision tiers) has been fully translated to English.
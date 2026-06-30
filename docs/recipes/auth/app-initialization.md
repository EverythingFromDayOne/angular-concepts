---
recipe_id: "app-initialization"
title: "App Initialization: Silent Token Restoration on Reload"
file: "recipes/auth/app-initialization.md"
primary_concept: "routing/routing"
related_concepts: ["dependency-injection/dependency-injection", "http/http", "reactivity/signals"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# App Initialization: Silent Token Restoration on Reload

> **What you'll build:** the missing piece that makes in-memory token
> storage actually usable in production — an `APP_INITIALIZER` hook that
> fires a silent refresh call before the UI renders, so users who press
> F5 (or revisit the tab) don't get kicked to login every time. Plus the
> companion auth guard and `returnUrl` flow that picks up where the
> initializer leaves off.
>
> **Concepts you'll touch:** [Routing](../../routing/routing.md), [Dependency Injection](../../dependency-injection/dependency-injection.md), [HTTP](../../http/http.md), [Signals](../../reactivity/signals.md)
>
> **Time:** ~20 minutes to read; ~1 hour to wire up and verify the no-flash UX.

---

## The scenario

You followed the [Token Storage Security](./token-storage-security.md) recipe. Access tokens live in a signal — JS memory, wiped on reload. Refresh tokens live in an HttpOnly cookie — JS-invisible, persists across sessions.

The architecture is sound. Then a user presses F5 on `/dashboard`. What happens?

1. Browser tears down the JS environment. Memory is wiped.
2. Browser reloads the page. Angular bootstraps. `TokenService.accessToken()` is `null` (fresh memory, no token).
3. Angular tries to render `/dashboard`. Whatever guards or interceptors run see "no access token" and either:
   - Redirect to `/login` (if you have an auth guard) — bad UX, the user *was* logged in two seconds ago
   - Render `/dashboard` with broken API calls (no auth guard) — worse UX, partial UI showing data fetches that all 401

Meanwhile, **the refresh cookie is still in the browser**. The server would happily issue a new access token if anyone asked. Nobody asks — because Angular went straight to rendering before checking.

The fix: **make Angular ask before rendering anything.** Block bootstrap on a silent refresh call. If the cookie is valid, restore the access token to memory and let the app render normally. If the cookie is gone or expired, render the public shell and let the auth guard handle the redirect to login.

That's what `provideAppInitializer` is for.

---

## The v22 implementation

Angular 19 added `provideAppInitializer` — a clean, function-based replacement for the legacy `APP_INITIALIZER` token. It accepts a function that runs in injection context and returns either `void`, an `Observable`, or a `Promise`. **Angular waits for the returned value to resolve/complete before rendering the first route.**

### Step 1 — the `initApp` function on `AuthService`

```typescript
// File: auth.service.ts (extending the version from the storage recipe)
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { TokenService } from './token.service';

interface RefreshResponse { accessToken: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly tokenService = inject(TokenService);

  // …login(), refreshToken(), logout() from the storage recipe…

  /**
   * Called once at app bootstrap by provideAppInitializer.
   * Tries to silently restore the session using the HttpOnly refresh cookie.
   * On success: saves the new access token to in-memory storage.
   * On failure: swallows the error and returns of(null) so bootstrap continues.
   * NEVER navigates — that's the guard's job (see below).
   */
  initApp(): Observable<unknown> {
    return this.http
      .post<RefreshResponse>('/api/auth/refresh', {}, { withCredentials: true })
      .pipe(
        tap(response => this.tokenService.saveToken(response.accessToken)),
        catchError(() => {
          // Cookie missing, expired, invalidated server-side, or any other
          // failure — render the app in a logged-out state and let routing
          // figure out where to go from there.
          return of(null);
        }),
      );
  }
}
```

The shape of `initApp` is deliberate:

- **`catchError` returning `of(null)` is load-bearing.** If `initApp` errors out, Angular treats bootstrap as failed and **the app never renders at all**. The user gets a blank page. The `catchError` ensures that a missing/expired cookie produces a normal logged-out app, not a broken one.
- **No `router.navigate()` call inside `initApp`.** Tempting, but wrong — covered in detail below.
- **`tap` for the side effect, not `subscribe`.** Returning the observable lets Angular subscribe; `subscribe` inside would fire-and-forget and bootstrap would race ahead before the token landed.

### Step 2 — wire it into `app.config.ts`

```typescript
// File: app.config.ts
import { ApplicationConfig, provideAppInitializer, inject } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { jwtInterceptor } from './auth/jwt.interceptor';
import { AuthService } from './auth/auth.service';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([jwtInterceptor])),
    provideAppInitializer(() => {
      // Runs in injection context — inject() works directly.
      const authService = inject(AuthService);
      return authService.initApp();
    }),
  ],
};
```

That's the whole modern setup. One function call, one `inject()`, one return. Compare with the legacy form for context:

<!-- legacy: pre-v19 APP_INITIALIZER token + factory + multi:true — modernized in the upgrade pass -->
```typescript
// Legacy (pre-v19): APP_INITIALIZER injection token with a factory provider
import { APP_INITIALIZER } from '@angular/core';

function appInitializerFactory(authService: AuthService) {
  return () => authService.initApp();
}

@NgModule({
  providers: [
    {
      provide: APP_INITIALIZER,
      useFactory: appInitializerFactory,
      deps: [AuthService],     // ← explicit dependency declaration
      multi: true,             // ← required: APP_INITIALIZER is a multi-provider
    },
  ],
})
export class AppModule {}
```

The legacy form needed a factory function, an explicit `deps` array, and `multi: true` (because `APP_INITIALIZER` is a multi-provider that accumulates initializers). `provideAppInitializer` collapses all of that into a single `inject()`-aware function. New code should use it; old code should migrate when convenient.

---

## Why NOT to navigate from inside the initializer

It's natural to think: *"If the refresh fails, just redirect the user to `/login` from inside `initApp` — save a round trip through the guard."* This is wrong, for one specific reason: **public routes exist.**

```typescript
// File: app.routes.ts — what routes look like in real apps
export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'about', component: AboutComponent },          // public
  { path: 'contact', component: ContactComponent },      // public
  { path: 'privacy', component: PrivacyComponent },      // public
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'orders', component: OrdersComponent, canActivate: [authGuard] },
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
];
```

If `initApp` calls `router.navigate(['/login'])` on every refresh failure, then:

- A user who shares a marketing link to `/about` and isn't logged in gets force-redirected to `/login` instead of seeing the about page. **Wrong behavior.**
- A user F5-ing `/privacy` to re-read terms of service gets booted to login. **Wrong behavior.**
- An SEO crawler hitting any public page sees a redirect to `/login`. **SEO problem.**

The right division of labor:

- **`initApp`** restores session state (or fails silently). It says *"I tried; here's the result, do what you want with it."*
- **The route guards** decide what to do about that state. They have route-level context (`canActivate`), so they only redirect users who tried to access protected routes.
- **The login component** uses `returnUrl` to send the user back to where they were headed after a successful login.

Each piece does one thing. The initializer doesn't try to be the router.

---

## The companion — `authGuard` with `CanActivateFn`

V22 idiom is the functional `CanActivateFn`, not class-based `CanActivate`. It runs in injection context, so `inject()` works directly.

```typescript
// File: auth.guard.ts
import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { TokenService } from './token.service';

export const authGuard: CanActivateFn = (route, state) => {
  const tokenService = inject(TokenService);
  const router = inject(Router);

  // Synchronous check — TokenService.getToken() reads the signal value.
  if (tokenService.getToken() !== null) {
    return true;
  }

  // Not authenticated — redirect to login, preserving where they were trying to go.
  // The login component reads queryParams['returnUrl'] and uses it on success.
  router.navigate(['/login'], {
    queryParams: { returnUrl: state.url },
  });
  return false;
};
```

Then attach it to the protected routes:

```typescript
// File: app.routes.ts
import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';

export const routes: Routes = [
  // Public — no guard.
  { path: 'login', component: LoginComponent },
  { path: 'about', component: AboutComponent },
  { path: 'contact', component: ContactComponent },
  { path: 'privacy', component: PrivacyComponent },

  // Protected — guard kicks in if no access token.
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'orders', component: OrdersComponent, canActivate: [authGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [authGuard] },

  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
];
```

<!-- legacy: pre-v15 class-based CanActivate guards — modernized in the upgrade pass -->
```typescript
// Legacy (pre-v15): class-based CanActivate guard with constructor injection
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(
    private tokenService: TokenService,
    private router: Router,
  ) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
    if (this.tokenService.getToken() !== null) return true;
    this.router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }
}
```

Both forms do the same job. The functional form is shorter, doesn't need an `@Injectable` decorator, and matches the pattern used by all the other v22 functional guards (`canActivateChild`, `canDeactivate`, `canMatch`, `resolve`).

---

## The `returnUrl` UX pattern

When the guard redirects to login, it stashes the originally requested URL in `queryParams.returnUrl`. The login component reads it on construction and uses it after a successful login — so users land on the page they intended, not the default landing page.

```typescript
// File: login.component.ts
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-login',
  template: `
    <form (submit)="onLogin($event)">
      <input [(ngModel)]="email" name="email" type="email" required />
      <input [(ngModel)]="password" name="password" type="password" required />
      <button type="submit" [disabled]="submitting()">Log in</button>
      @if (error()) {
        <p class="error">{{ error() }}</p>
      }
    </form>
  `,
})
export class LoginComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);

  // Read the returnUrl from the URL at construction time.
  // route.snapshot is fine here because we don't expect this to change mid-render.
  private readonly returnUrl =
    this.route.snapshot.queryParams['returnUrl'] ?? '/dashboard';

  email = '';
  password = '';
  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);

  onLogin(event: Event): void {
    event.preventDefault();
    this.submitting.set(true);
    this.error.set(null);

    this.authService.login({ email: this.email, password: this.password }).subscribe({
      next: () => this.router.navigateByUrl(this.returnUrl),
      error: (err) => {
        this.submitting.set(false);
        this.error.set('Login failed. Check your credentials.');
      },
    });
  }
}
```

The flow:

1. User clicks a link to `/orders/2026-03-invoice` (deep link from email).
2. They're not logged in. `authGuard` blocks the navigation, calls `router.navigate(['/login'], { queryParams: { returnUrl: '/orders/2026-03-invoice' } })`.
3. Login component renders. URL is now `/login?returnUrl=%2Forders%2F2026-03-invoice`.
4. User logs in. `onLogin` reads `this.returnUrl` (decoded by the router to `/orders/2026-03-invoice`) and calls `router.navigateByUrl(returnUrl)`.
5. User lands on the invoice page. Auth guard re-runs, sees the token, lets them through.

The user never sees an intermediate "you are now logged in" page. The deep link survives the auth detour.

---

## The complete lifecycle — what happens on F5

Stepping through the F5 sequence end-to-end clarifies how the pieces fit together.

```text
User on /dashboard presses F5
        ▼
Browser tears down JS environment. localStorage clean (never touched). 
HttpOnly cookie persists.
        ▼
Browser reloads. Angular bundles start parsing.
        ▼
Angular bootstrap begins.
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ provideAppInitializer holds bootstrap.                               │
│ authService.initApp() fires:                                         │
│   POST /api/auth/refresh (no body; HttpOnly cookie auto-attached)    │
└──────────────────────────────────────────────────────────────────────┘
        ▼
   ┌────┴────────────────────────────┐
   ▼                                 ▼
[A: Success]                      [B: Failure]
Server returns 200 with new       Server returns 401 (cookie
accessToken.                      missing/expired/invalidated).
  ▼                                 ▼
tap saves token to signal.        catchError returns of(null).
Initializer Observable            Initializer Observable
completes with the token.         completes with null.
   │                                 │
   └────────────┬────────────────────┘
                ▼
Angular bootstrap proceeds. UI renders.
                ▼
Router activates /dashboard (the URL the user F5'd on).
                ▼
authGuard runs:
  if (tokenService.getToken() !== null) → true → render dashboard ✓ (case A)
  else → false → router.navigate(['/login'], queryParams: returnUrl='/dashboard') (case B)
                ▼
[A] User sees dashboard. No flash. No reload visible to them.
[B] User sees login page with returnUrl=/dashboard. After login, lands on /dashboard.
```

Two paths, both clean. The user never sees a moment of broken state — either the session restores silently, or they're invited to log in and sent back where they were going.

---

## Variations

### Initializers that should NOT block bootstrap

`provideAppInitializer` blocks the UI until the function completes. That's what you want for auth — rendering pre-auth would flash broken state. But some initializers (analytics SDKs, telemetry pings, prefetch warmups) are nice-to-have and shouldn't gate the user's first paint.

For those, run them inside the initializer but don't return the observable — fire and forget:

```typescript
provideAppInitializer(() => {
  const auth = inject(AuthService);
  const analytics = inject(AnalyticsService);

  // Fire and forget — analytics init doesn't block UI.
  analytics.init().subscribe();

  // Return the auth init — Angular waits for THIS.
  return auth.initApp();
}),
```

### Multiple `provideAppInitializer` calls

Each `provideAppInitializer` adds a separate initializer. Angular runs them **in parallel** and waits for all to complete before rendering:

```typescript
providers: [
  provideAppInitializer(() => inject(AuthService).initApp()),
  provideAppInitializer(() => inject(ConfigService).loadServerConfig()),
  provideAppInitializer(() => inject(FeatureFlagsService).fetchFlags()),
],
```

If any single initializer rejects/errors (and doesn't catch), bootstrap fails and the app doesn't render. Apply `catchError` defensively to the ones that shouldn't be load-bearing.

### Initializer timeout

If your refresh endpoint takes too long, the user sees a stalled blank page. Add a timeout to bound the wait:

```typescript
import { timeout, catchError } from 'rxjs/operators';

initApp(): Observable<unknown> {
  return this.http
    .post<RefreshResponse>('/api/auth/refresh', {}, { withCredentials: true })
    .pipe(
      timeout(3000),   // 3-second wait, then fail through
      tap(response => this.tokenService.saveToken(response.accessToken)),
      catchError(() => of(null)),  // captures both 401 and timeout
    );
}
```

Rule of thumb: **set the timeout shorter than your patience for a blank page is.** 2-5 seconds is typical. Slow connections will still see a delay, but they'll see the logged-out app within the timeout — better than indefinite blank.

### Conditional initialization

You might want to skip the refresh call for users who've never logged in (no prior session). One option: a lightweight marker in `localStorage` ("user has logged in here before") that the initializer reads first. If absent, skip the network call entirely.

```typescript
initApp(): Observable<unknown> {
  const hasLoggedInBefore = localStorage.getItem('has_session') === '1';
  if (!hasLoggedInBefore) {
    return of(null);  // skip the refresh attempt entirely
  }
  return this.refreshSilently();
}
```

The marker isn't a security token — losing it just means an unnecessary refresh attempt that fails. Acceptable trade-off for saving a network call on first-time visitors.

---

## Trade-offs and common pitfalls

**Use `provideAppInitializer` for auth restoration when:**

- Access tokens live in memory (the only configuration that needs reload-time restoration)
- The refresh endpoint is fast and reliable (timeout-bounded; ideally <500ms p99)
- The UX cost of a logout-on-reload is unacceptable

**Skip it when:**

- Access tokens live in localStorage (they survive reload natively — see [Token Storage Security](./token-storage-security.md) for when that's acceptable)
- You're shipping an MVP and the "log in again after refresh" UX is acceptable until v2
- You don't have a refresh endpoint yet

**Common pitfalls:**

- **Forgetting `catchError`** — initializer errors propagate as bootstrap failures. The user sees a blank page with no Angular running. The `of(null)` fallback is mandatory, not stylistic.
- **`subscribe()` inside the initializer instead of returning the observable** — Angular doesn't wait. Bootstrap races ahead, UI renders before the token lands, guards fail, redirect to login. The whole feature does nothing.
- **Calling `router.navigate` inside `initApp`** — covered above. Breaks public routes; the guard exists for a reason.
- **`route.snapshot.queryParamMap` reads vs the observable form** — `snapshot` is captured at component creation. If the user navigates *between* login attempts without unmounting the login component, the snapshot is stale. For most login flows the snapshot is fine; if you support in-place URL changes, read `route.queryParamMap` as an observable.
- **No timeout on `initApp`** — slow refresh endpoints stall the entire app. Always set a timeout; 3-5 seconds is reasonable.
- **Initializer dependencies that aren't ready** — calling `inject(Router)` inside the initializer works (Router is provided before initializers run), but `inject(SomeComponent)` does not (components don't exist yet). Initializers can only inject services and tokens, not view-tree references.
- **Skipping the marker check on first-time visitors** — every first-time visitor makes a `/api/auth/refresh` call that's guaranteed to return 401. Wastes a round trip and bumps your auth-server error metrics. The `localStorage` marker (or equivalent) eliminates the call.
- **Mixing `APP_INITIALIZER` (legacy) and `provideAppInitializer` in the same app** — they both work, but split provider patterns are a maintenance smell. Pick one. New code: `provideAppInitializer`.

---

## See also

- [JWT Interceptor: Breaking the Circular Dependency](./jwt-interceptor-circular-dep.md) — the interceptor that handles ongoing auth after init
- [Token Storage Security](./token-storage-security.md) — the in-memory architecture this recipe restores. Specifically the `RefreshCoordinator` pattern composes with `initApp` (the initializer is "request 0" through that coordinator).
- [Step-up Authentication](./step-up-authentication.md) — scope-based re-auth for sensitive actions; runs *after* normal auth is established
- [Routing](../../routing/routing.md) — `provideRouter`, route guards, query parameters
- [Dependency Injection](../../dependency-injection/dependency-injection.md) — `inject()` in injection contexts (initializers are one)

## References

- [`provideAppInitializer` API (angular.dev)](https://angular.dev/api/core/provideAppInitializer)
- [`APP_INITIALIZER` token (angular.dev)](https://angular.dev/api/core/APP_INITIALIZER) — legacy form, still supported
- [`CanActivateFn` API (angular.dev)](https://angular.dev/api/router/CanActivateFn)
- [Angular release notes — v19 features](https://github.com/angular/angular/releases/tag/19.0.0) — where `provideAppInitializer` landed

## Demo source

Synthesized from real-world Angular auth bootstrap walkthroughs rather than a single demo file. The `provideAppInitializer` form is the v19+ canonical pattern; the legacy `APP_INITIALIZER` token + factory + `multi: true` form is preserved for migration context. All Vietnamese-language conversation context that informed the recipe (the F5/reload UX problem, the public-route navigation pitfall, the `returnUrl` flow) has been fully translated to English.
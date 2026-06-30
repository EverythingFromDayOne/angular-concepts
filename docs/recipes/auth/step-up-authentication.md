---
recipe_id: "step-up-authentication"
title: "Step-up Authentication: Re-auth for Sensitive Actions"
file: "recipes/auth/step-up-authentication.md"
primary_concept: "http/interceptors"
related_concepts: ["dependency-injection/dependency-injection", "reactivity/signals", "http/http"]
demo_repo: null
angular_baseline: "22"
difficulty: "advanced"
status:
  upgraded: true
  reviewed: false
---

# Step-up Authentication: Re-auth for Sensitive Actions

> **What you'll build:** the "you must re-enter your password to continue"
> flow that sits between normal browsing and high-stakes actions like
> placing an order, changing a saved card, or transferring funds. The
> interceptor catches a 403 SUDO_MODE response from the server, opens a
> modal at the app root, captures the password, exchanges it for an
> elevated-scope token, and quietly retries the original request — all
> without the calling component knowing any of this happened.
>
> **Concepts you'll touch:** [HTTP Interceptors](../../http/interceptors.md), [Dependency Injection](../../dependency-injection/dependency-injection.md), [Signals](../../reactivity/signals.md), [HTTP](../../http/http.md)
>
> **Time:** ~30 minutes to read; ~3 hours to wire up end-to-end and verify all the edge cases.

---

## The scenario

The user is logged in. They've been browsing the e-commerce app for 20 minutes. They click "Pay" on a $400 order.

What should happen? Two extremes are both wrong:

- **Just let the click go through.** If their phone was unattended for 30 seconds, anyone walking by can place orders with their saved card. Their account has been logged in for hours — the original login is no longer fresh enough to authorize a transaction.
- **Force them to log in again from scratch.** They lose their cart, their session, their place in the navigation. Conversion rate drops; users abandon the purchase.

The right answer is the middle: **make them prove freshly that they're still the account holder**, but only for sensitive actions, and only in a way that doesn't disrupt the flow they're in. A modal that asks for their password (or OTP, or fingerprint), confirms within the existing session, and lets the original action proceed.

This is **step-up authentication** — the pattern that GitHub uses when you change repo settings, that Amazon uses when you update your default payment method, that every banking app uses for every transfer. The mechanics are uniform: the server demands a fresher proof of identity for sensitive endpoints; the client provides it on demand.

## Two architectural approaches

The recipe focuses on the **scope-based** approach (one token, escalating scope) because it's simpler and more common. The **sudo-token** alternative is sketched at the end.

### Approach 1 — scope-based (recommended)

A single access token, but with a `scope` claim that determines what it can do. Normal scope is `"read:basic"`. After a successful step-up, the token's scope becomes `"write:secure"` for a short window (3–5 minutes). Sensitive endpoints require the elevated scope; if it's missing, the server returns 403.

```text
Token lifecycle:
  Login       → access token (scope: read:basic, TTL: 15 min)
  Browse      → uses access token normally
  Click Pay   → server returns 403 REQUIRE_SUDO_MODE
  Modal opens → user enters password
  Step-up API → server issues NEW access token (scope: write:secure, TTL: 5 min)
  Pay retry   → succeeds with elevated token
  After 5 min → next refresh issues regular access token (scope: read:basic)
```

One token mechanism, one storage location, one interceptor flow. The scope claim is a property of the token, not a separate credential.

### Approach 2 — sudo token (alternative)

A separate, short-lived "sudo token" sent as an additional header (e.g., `X-Sudo-Token`) for sensitive endpoints. Used once and discarded. The regular access token continues unchanged in parallel.

```text
Token lifecycle:
  Login       → access token (no scope distinction)
  Browse      → uses access token normally
  Click Pay   → server returns 403 REQUIRE_SUDO_MODE
  Modal opens → user enters password
  Sudo API    → server issues X-Sudo-Token (TTL: 5 min, single-use)
  Pay retry   → succeeds with both Authorization AND X-Sudo-Token headers
  Sudo token  → expires after one use or 5 min, whichever first
```

This is GitHub's approach. The advantage: clear separation; sudo-grants are auditable and can be revoked independently of the session. The disadvantage: two tokens to manage, more complex header logic in the interceptor.

For most apps, **scope-based is the right choice.** The recipe walks through it in detail; the sudo-token alternative needs ~20 extra lines and is covered at the end.

---

## Step 1 — the server contract

The recipe assumes the server follows a simple contract:

- Normal sensitive endpoints (`POST /api/orders`, `PUT /api/payment-methods`, etc.) check the token's `scope` claim. If it's not `write:secure`, return:
  ```http
  HTTP/1.1 403 Forbidden
  Content-Type: application/json

  { "code": "REQUIRE_SUDO_MODE", "message": "Re-authentication required" }
  ```
- A new endpoint `POST /api/auth/step-up` accepts `{ password }` and the current access token, validates the password against the user's account, and returns a new access token with `scope: write:secure` and a 5-minute TTL:
  ```http
  POST /api/auth/step-up
  Authorization: Bearer <current-token>
  Content-Type: application/json

  { "password": "********" }
  ```
  Response on success:
  ```json
  { "accessToken": "<new-elevated-token>" }
  ```
  Response on bad password: `401 Unauthorized`.

The recipe doesn't cover server implementation, but the client interceptor depends on this exact shape.

---

## Step 2 — the `SudoModalService`

The interceptor needs to **open a modal somewhere in the UI** to capture the password, then receive the result back. The cleanest way: a signal-based service that the modal component watches reactively, and an `Observable` channel that returns the user's input to whoever called the service.

```typescript
// File: sudo-modal.service.ts
import { Injectable, computed, signal } from '@angular/core';
import { Observable, Subject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SudoModalService {
  // Holds the current result Subject. null = no modal open; non-null = modal open.
  private readonly currentRequest = signal<Subject<string | null> | null>(null);

  /** Reactive read for the modal component: should I be showing right now? */
  readonly isOpen = computed(() => this.currentRequest() !== null);

  /**
   * Called from the interceptor when a 403 SUDO_MODE arrives.
   * Returns an Observable that emits the password (or null on cancel) exactly once.
   */
  openSudoModal(): Observable<string | null> {
    const result$ = new Subject<string | null>();
    this.currentRequest.set(result$);
    return result$.asObservable();
  }

  /** Called by the modal component when the user submits a password. */
  submit(password: string): void {
    const result = this.currentRequest();
    if (result) {
      result.next(password);
      result.complete();
      this.currentRequest.set(null);
    }
  }

  /** Called by the modal component when the user cancels. */
  cancel(): void {
    const result = this.currentRequest();
    if (result) {
      result.next(null);
      result.complete();
      this.currentRequest.set(null);
    }
  }
}
```

**Three things doing the work:**

- **`signal<Subject<string | null> | null>`** is the modal state. `null` means closed; a non-null Subject means "open, waiting for input on this channel." Conflating "is the modal open" with "where do I send the result" into one piece of state eliminates a class of bugs where the modal closes but the calling code is still waiting for a result.
- **`computed(() => currentRequest() !== null)`** gives the modal component an `isOpen` signal it can bind to in its template. No subscription, no async pipe.
- **`Subject` only emits once and then completes.** That's intentional — there's exactly one user response per modal open, and `complete()` signals to the interceptor's `take(1)` that no further values are coming.

---

## Step 3 — the modal component at the app root

The modal component lives at the application's top level (rendered from `app.component.html`) so it's always available regardless of which route is active.

```typescript
// File: sudo-confirm.component.ts
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SudoModalService } from './sudo-modal.service';

@Component({
  selector: 'app-sudo-confirm',
  imports: [FormsModule],
  template: `
    @if (sudoModalService.isOpen()) {
      <div class="modal-backdrop" (click)="cancel()">
        <div class="modal-content" (click)="$event.stopPropagation()">
          <h3>Re-authentication required</h3>
          <p>
            Please re-enter your password to confirm this sensitive action.
          </p>

          <form (submit)="submit($event)">
            <input
              type="password"
              [(ngModel)]="password"
              name="password"
              placeholder="Enter password"
              autofocus
              required
            />

            @if (error()) {
              <p class="error">{{ error() }}</p>
            }

            <div class="actions">
              <button type="submit" [disabled]="submitting()">
                {{ submitting() ? 'Verifying…' : 'Confirm' }}
              </button>
              <button type="button" (click)="cancel()">Cancel</button>
            </div>
          </form>
        </div>
      </div>
    }
  `,
  styles: `
    .modal-backdrop {
      position: fixed; inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex; align-items: center; justify-content: center;
      z-index: 1000;
    }
    .modal-content {
      background: white; padding: 24px; border-radius: 8px;
      min-width: 320px; max-width: 480px;
    }
    .error { color: #b91c1c; font-size: 14px; }
    .actions { display: flex; gap: 8px; margin-top: 16px; }
  `,
})
export class SudoConfirmComponent {
  protected readonly sudoModalService = inject(SudoModalService);

  password = '';
  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);

  submit(event: Event): void {
    event.preventDefault();
    if (!this.password) return;
    this.submitting.set(true);
    // Interceptor handles the actual /api/auth/step-up call;
    // we just hand off the password.
    this.sudoModalService.submit(this.password);
    this.password = '';
    this.submitting.set(false);
  }

  cancel(): void {
    this.sudoModalService.cancel();
    this.password = '';
  }
}
```

Then mount it once, at the app root, so it's always available:

```html
<!-- File: app.component.html -->
<router-outlet />
<app-sudo-confirm />
```

**Why mount at the app root** and not inside individual pages: the modal must survive route changes (a 403 might fire on a request that completes while the user is on a different page than they started). It must also be visible from any page (you don't know which page will trigger a sensitive request). One mount, one source of truth, available everywhere.

---

## Step 4 — extend the interceptor with 403 handling

The functional interceptor from the [token storage recipe](./token-storage-security.md) handles the bearer-token attachment and the 401 refresh flow. Extend it with a `catchError` branch that recognizes 403 SUDO_MODE:

```typescript
// File: jwt.interceptor.ts (extending earlier version)
import {
  HttpErrorResponse,
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject, Injector } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, switchMap, take } from 'rxjs/operators';
import { TokenService } from './token.service';
import { AuthService } from './auth.service';
import { RefreshCoordinator } from './refresh-coordinator.service';
import { SudoModalService } from './sudo-modal.service';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip auth-flow endpoints so we don't loop.
  if (isAuthFlowEndpoint(req.url)) {
    return next(req.clone({ withCredentials: true }));
  }

  const tokenService = inject(TokenService);
  const injector = inject(Injector);
  const token = tokenService.getToken();
  const authedReq = token ? attachToken(req, token) : req;

  return next(authedReq).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        // 401: refresh the access token (handled by the storage recipe).
        if (error.status === 401) {
          return handle401(req, next, injector);
        }
        // 403 with SUDO code: trigger step-up flow.
        if (error.status === 403 && isSudoModeError(error)) {
          return handleSudoMode(req, next, injector);
        }
      }
      return throwError(() => error);
    }),
  );
};

function isAuthFlowEndpoint(url: string): boolean {
  return (
    url.endsWith('/api/auth/login') ||
    url.endsWith('/api/auth/refresh') ||
    url.endsWith('/api/auth/step-up')
  );
}

function isSudoModeError(error: HttpErrorResponse): boolean {
  return error.error?.code === 'REQUIRE_SUDO_MODE';
}

function attachToken(req: HttpRequest<unknown>, token: string) {
  return req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  });
}

function handleSudoMode(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  injector: Injector,
) {
  const sudoModal = injector.get(SudoModalService);
  const tokenService = injector.get(TokenService);

  // Open the modal and wait for the user's password (or cancel).
  return sudoModal.openSudoModal().pipe(
    take(1),
    switchMap(password => {
      if (!password) {
        // User cancelled — propagate as a recognizable error.
        return throwError(() => new Error('USER_CANCELLED_STEP_UP'));
      }

      // LAZY: AuthService → step-up endpoint → elevated access token.
      const authService = injector.get(AuthService);
      return authService.stepUp(password).pipe(
        switchMap(response => {
          // Replace the in-memory token with the elevated one.
          tokenService.saveToken(response.accessToken);
          // Retry the original request with the new token.
          return next(attachToken(req, response.accessToken));
        }),
        catchError(err => {
          // Step-up failed (wrong password, etc.) — propagate.
          // The calling component decides whether to retry or give up.
          return throwError(() => err);
        }),
      );
    }),
  );
}

// (handle401 from the token storage recipe)
function handle401(/* … */) { /* … */ }
```

**Three patterns worth absorbing:**

- **Skip auth-flow endpoints at the top.** Just like with refresh: if the step-up call itself goes through the interceptor and gets a 403, you loop. The `isAuthFlowEndpoint` check exempts the three auth endpoints (login, refresh, step-up) from the interceptor's 401/403 handling.
- **`take(1)` on the modal Subject.** The Subject completes after one emission (the service does this on `submit`/`cancel`), but `take(1)` is defensive — if the Subject somehow emits twice, only the first response is acted on.
- **Cancellation propagates as a specific error string.** Components that initiate sensitive actions should `catchError` on their HTTP call and check for `'USER_CANCELLED_STEP_UP'`, treating it as "action cancelled" rather than "action failed." Otherwise you get scary error toasts when users politely decline.

---

## Step 5 — extend `AuthService` with `stepUp()`

```typescript
// File: auth.service.ts (adding to the existing service)
@Injectable({ providedIn: 'root' })
export class AuthService {
  // …login(), refreshToken(), logout(), initApp() from earlier recipes…

  stepUp(password: string) {
    // Sends the current access token (auto-attached by interceptor IF this
    // endpoint weren't in the auth-flow skip list — but it IS, so we attach
    // it manually here).
    const currentToken = this.tokenService.getToken();
    return this.http.post<{ accessToken: string }>(
      '/api/auth/step-up',
      { password },
      {
        withCredentials: true,
        headers: currentToken
          ? { Authorization: `Bearer ${currentToken}` }
          : {},
      },
    );
  }
}
```

The endpoint needs the current token (server uses it to identify the user) **and** the password (server verifies it before issuing the elevated token). The interceptor's auth-flow-skip means we attach the token manually here — explicit is better than the interceptor doing it implicitly.

---

## The full flow — what happens when the user clicks Pay

Stepping through end-to-end:

```text
1. User on /checkout. Token in memory: { scope: "read:basic", TTL: 15min }
   Component calls orderService.placeOrder(items).
2. HTTP POST /api/orders fires.
3. Interceptor attaches token. Server checks scope — needs write:secure, sees read:basic.
4. Server returns 403 { code: "REQUIRE_SUDO_MODE" }.
5. Interceptor's catchError branch fires.
   - Recognizes the SUDO_MODE error.
   - Calls sudoModalService.openSudoModal() — returns Observable<string|null>.
   - This synchronously updates the signal — SudoConfirmComponent re-renders, modal appears.
6. User sees modal. Enters password. Clicks Confirm.
   - SudoConfirmComponent calls sudoModalService.submit(password).
   - The result Subject emits the password and completes.
   - Modal closes (signal goes back to null).
7. Interceptor's switchMap receives the password.
   - Calls authService.stepUp(password).
   - Server validates password, returns { accessToken: <elevated-token> } with scope: write:secure.
8. Interceptor saves the new token via tokenService.saveToken().
9. Interceptor retries the original POST /api/orders with the elevated token.
10. Server sees write:secure scope, processes the order, returns 200.
11. The original orderService.placeOrder() call resolves with the order data.
    The component that initiated it has no idea any of steps 4-10 happened.
```

The calling component is completely unaware of step-up — it called `placeOrder()`, the observable resolved with the order, that's all it knows. The interceptor is the only place that knows about sudo mode. **One responsibility per layer, transparent to consumers.**

---

## Variations

### OTP instead of password

For phones / two-factor flows, replace the password input with an OTP entry. The modal sends `{ otp: '123456' }` instead; the server validates against the user's authenticator app or a recent SMS.

The only differences are in the modal's input field and the body sent to `/api/auth/step-up`. Everything else (interceptor, service, flow) is identical. The server's contract is the same — issue an elevated token in exchange for proof of identity.

### WebAuthn / biometric

For Face ID, Touch ID, or hardware keys, replace the password prompt with `navigator.credentials.get(...)`:

```typescript
async submitBiometric(): Promise<void> {
  this.submitting.set(true);
  try {
    const credential = await navigator.credentials.get({
      publicKey: {
        challenge: /* fetched from server */,
        // …
      },
    });
    this.sudoModalService.submitCredential(credential);
  } catch (err) {
    this.sudoModalService.cancel();
  }
}
```

The modal becomes "Tap to confirm with Face ID" instead of "Enter password." The service's `submit` method takes the credential payload instead of a string. The server validates the WebAuthn assertion and issues the elevated token. From the interceptor's perspective, the rest of the flow is unchanged.

### Sudo cooldown — "remember for 5 minutes"

The default behavior: every sensitive action prompts. For some apps that's too aggressive (a user paying for multiple items in sequence shouldn't be prompted five times). The fix: an in-memory flag in `SudoModalService` that remembers a recent successful step-up:

```typescript
private readonly sudoUntil = signal<number | null>(null);

submit(password: string): void {
  // …existing submit logic…
  this.sudoUntil.set(Date.now() + 5 * 60 * 1000);  // 5-min grace
}

isInSudoGrace(): boolean {
  const until = this.sudoUntil();
  return until !== null && Date.now() < until;
}
```

Then the interceptor checks the grace before opening the modal:

```typescript
function handleSudoMode(req, next, injector) {
  const sudoModal = injector.get(SudoModalService);
  if (sudoModal.isInSudoGrace()) {
    // Already authenticated recently — skip the modal, just retry.
    // (The server will accept because the elevated token from the previous
    // step-up is still in TokenService and still has write:secure scope.)
    return next(req);
  }
  return sudoModal.openSudoModal().pipe(/* … */);
}
```

**Subtle**: the grace window doesn't bypass the server's check; it bypasses **showing the modal**. The server still validates the token's scope. The grace works because the elevated token from the previous step-up is still in `TokenService` with `write:secure` scope. If the token has since refreshed back to `read:basic`, the server will reject and the modal will appear again — correct behavior.

### Sudo token (Approach 2) — sketch

If the server uses a separate sudo token instead of scope elevation:

```typescript
// SudoTokenService — separate from TokenService
@Injectable({ providedIn: 'root' })
export class SudoTokenService {
  private readonly sudoToken = signal<string | null>(null);

  getSudoToken(): string | null {
    return this.sudoToken();
  }

  setSudoToken(token: string): void {
    this.sudoToken.set(token);
    // One-shot: discard after the next use (or set a TTL timer here).
  }

  clearSudoToken(): void {
    this.sudoToken.set(null);
  }
}
```

The interceptor attaches it as an additional header (only when present) on every request — the server uses it on sensitive endpoints, ignores it on regular ones:

```typescript
const sudoToken = inject(SudoTokenService).getSudoToken();
const headers: Record<string, string> = {};
if (token) headers['Authorization'] = `Bearer ${token}`;
if (sudoToken) headers['X-Sudo-Token'] = sudoToken;
req = req.clone({ setHeaders: headers });
```

After a successful sensitive request, `SudoTokenService.clearSudoToken()` discards it (one-shot semantics) — or let it expire via a `setTimeout(() => clearSudoToken(), 5*60*1000)` set when the token is issued.

The trade-off vs scope-based: cleaner separation between regular and sudo state, but two tokens to manage, and the header logic adds branches throughout. Stick with scope-based unless your server architecture demands the separation.

---

## Trade-offs and common pitfalls

**Use step-up authentication when:**

- The app has actions that should require fresh authentication regardless of session age (payments, password changes, account deletion, data export)
- Your industry has compliance pressure for re-auth on sensitive operations (financial, healthcare, anything with audit requirements)
- The "long session, narrow re-auth" pattern matches your UX research (e-commerce, banking, B2B SaaS — almost any app with high-stakes actions)

**Skip step-up when:**

- The app has no actions where re-auth adds meaningful protection (forums, blogs, dashboards without irreversible operations)
- The session timeout is short enough (15 min) that the full session IS the fresh auth
- You're shipping an MVP and the "sensitive action" set is empty or small enough to handle with a one-off password prompt

**Common pitfalls:**

- **Mounting `SudoConfirmComponent` inside a route component instead of at the app root.** The modal disappears the moment the user navigates. Worse, it doesn't render when the 403 fires on a request issued from a different page than they're on now. Mount once at the app root.
- **Forgetting to skip the step-up endpoint in `isAuthFlowEndpoint`.** The step-up call itself goes through the interceptor; if it returns 403 (wrong password), the interceptor recursively opens another modal. Infinite loop until the user gives up.
- **Treating cancellation as an error toast.** Users politely declining shouldn't see "Order failed!" Catch the `USER_CANCELLED_STEP_UP` string in your component error handlers and treat it as a non-event (or as "Action cancelled.").
- **Storing the elevated token alongside the regular token, then forgetting to downgrade.** With the scope-based approach, the elevated token IS the regular token — it just has different scope. Subsequent refreshes naturally produce regular-scope tokens after the 5-minute window. No separate "downgrade" code needed. With the sudo-token approach, the separate token must be cleared after use; forgetting this leaves the user permanently in sudo mode (security regression).
- **Parallel sensitive requests triggering N modals.** Similar to the parallel-401 problem in the [storage recipe](./token-storage-security.md). The clean fix: a queue in `SudoModalService` — first request opens the modal, others wait for the same result. After the step-up completes, the elevated token is in `TokenService` and queued retries succeed without further prompts.
- **`autofocus` on the password input.** Mostly correct, but the modal must already be in the DOM when the autofocus attribute is set — the `@if` rendering ensures this in v22 (it's not just `display: none`). Verify in your particular setup; some modal libraries delay focus and the input is unreachable on keyboard until you click it.
- **Logging the password anywhere.** Not in a console.log, not in a network request body that hits an error logger, not in the `event.preventDefault()` proximity. One audit finding away from a serious incident.

---

## See also

- [JWT Interceptor: Breaking the Circular Dependency](./jwt-interceptor-circular-dep.md) — the interceptor foundation; this recipe extends its `catchError` chain
- [Token Storage Security](./token-storage-security.md) — token lifecycle, refresh coordinator, the 401 refresh flow that composes with step-up
- [App Initialization](./app-initialization.md) — silent token restoration; sudo mode kicks in after the user has been browsing for a while, which only happens once `initApp` has restored the session
- [HTTP](../../http/http.md) — `HttpInterceptorFn`, request cloning, error handling
- [Signals](../../reactivity/signals.md) — the modal-state pattern with `signal` + `computed`
- [Dependency Injection — Lazy injection](../../dependency-injection/dependency-injection.md#lazy-injection--injector-as-an-escape-hatch) — the `Injector.get(AuthService)` mechanism the interceptor uses

## References

- [`HttpInterceptorFn` API (angular.dev)](https://angular.dev/api/common/http/HttpInterceptorFn)
- [`signal` and `computed` (angular.dev)](https://angular.dev/api/core/signal)
- [WebAuthn (W3C spec)](https://www.w3.org/TR/webauthn-2/) — the standard behind biometric step-up
- [OWASP — Authentication Cheatsheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST 800-63B — Authentication and Lifecycle Management](https://pages.nist.gov/800-63-3/sp800-63b.html) — the assurance-level framework that justifies step-up auth in regulated industries
- [GitHub sudo mode (real-world example)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/sudo-mode) — production reference for the pattern

## Demo source

Synthesized from real-world Angular authentication walkthroughs rather than a single demo file. The architectural choice between scope-based and sudo-token approaches, and the modal-at-app-root pattern, reflect the consensus across high-stakes B2C applications (banking, e-commerce, fintech). The OTP and WebAuthn variations are common extensions in apps that support hardware-second-factor authentication. All Vietnamese-language conversation context that informed the recipe has been fully translated to English; the original two-approach analysis has been preserved as the recipe's architectural framing.
---
recipe_id: "async-validation"
title: "Async Validation: Username Availability Without the Flicker"
file: "recipes/forms-and-search/async-validation.md"
primary_concept: "forms/validation"
related_concepts: ["forms/reactive-forms", "reactivity/rxjs/rxjs-higher-order", "reactivity/signals", "http/http"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Async Validation: Username Availability Without the Flicker

> **What you'll build:** a username-availability validator that hits the
> server, doesn't fire on every keystroke, doesn't race on fast typers,
> doesn't leave the form stuck in PENDING forever, doesn't re-check the
> same value twice, and tells the user clearly whether the field is
> *checking*, *available*, *taken*, or *errored* — all in idiomatic v22
> reactive forms with functional async validators.
>
> **Concepts you'll touch:** [Validation](../../forms/validation.md), [Reactive Forms](../../forms/reactive-forms.md), [RxJS higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md), [Signals](../../reactivity/signals.md), [HTTP](../../http/http.md)
>
> **Time:** ~25 minutes to read; ~1 hour to add to a registration form
> with proper UX states.

---

## The scenario

A signup form has a username field. The product spec is simple: "tell the user if their chosen username is taken." You write:

```typescript
readonly form = this.fb.group({
  username: this.fb.control('', {
    validators: [Validators.required, Validators.minLength(3)],
    asyncValidators: [
      (control) => this.http
        .get<{ available: boolean }>(`/api/users/check?username=${control.value}`)
        .pipe(map(res => res.available ? null : { taken: true })),
    ],
  }),
});
```

Four bugs come out of testing:

1. **It fires on every keystroke.** Type "alice" → 5 HTTP calls. Server falls over for a 10-user testing session.
2. **Race condition.** Type "alice" (slow), then immediately "alicia" (fast). "alice"'s response (taken) lands AFTER "alicia"'s response. Field shows "taken" for a name the user isn't trying.
3. **Empty value still triggers a check.** User clears the field → HTTP call fires for an empty username → server returns an error → field shows "taken." Wrong.
4. **No UI feedback during the wait.** The form's submit button is disabled (because the control is `PENDING`), but the user sees nothing indicating *why*. They click Submit, nothing happens, they conclude the form is broken.

A fifth problem appears later in production: **the validator can leak into "pending forever."** If the observable doesn't complete, the form's `pending` state never clears. Submit button stays disabled. User gives up.

This recipe fixes all five, in order.

---

## The base validator — debounce + empty guard + complete

The minimum viable validator that doesn't have any of the bugs above:

```typescript
// File: validators/username-available.validator.ts
import { AbstractControl, AsyncValidatorFn, ValidationErrors } from '@angular/forms';
import { inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, timer } from 'rxjs';
import { catchError, first, map, switchMap } from 'rxjs/operators';

interface AvailabilityResponse {
  available: boolean;
}

/**
 * Async validator for username availability.
 * Called in an injection context (component field initializer) so
 * inject(HttpClient) works without an explicit parameter.
 */
export function usernameAvailable(): AsyncValidatorFn {
  const http = inject(HttpClient);

  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    const value = (control.value ?? '').trim();

    // Empty or too-short — sync validators will catch this; don't check the server.
    if (value.length < 3) {
      return of(null);
    }

    return timer(300).pipe(
      switchMap(() =>
        http.get<AvailabilityResponse>(`/api/users/check?username=${encodeURIComponent(value)}`),
      ),
      map(response => response.available ? null : { taken: true }),
      catchError(() => of({ checkFailed: true } as ValidationErrors)),
      first(),  // belt-and-suspenders: force completion after first emission
    );
  };
}
```

Wire it into the form:

```typescript
@Component({ /* … */ })
export class SignupComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    username: this.fb.control('', {
      validators: [Validators.required, Validators.minLength(3)],
      asyncValidators: [usernameAvailable()],
      updateOn: 'change',  // default; explicit for clarity
    }),
    password: this.fb.control('', [Validators.required, Validators.minLength(8)]),
  });
}
```

**Five things doing the work:**

- **`timer(300)` at the top of the pipe is the debounce.** Angular calls the validator function on every value change. Each call returns a fresh Observable. When a new value arrives, Angular unsubscribes the previous validator's Observable. The `timer(300)` of the previous call is cancelled before it emits — so the HTTP call only fires after 300ms of no new value changes.

- **`switchMap` to the HTTP call.** Even though Angular handles per-call cancellation, `switchMap` is the right primitive: when the inner timer completes, switch to the actual HTTP request. The HTTP request's natural completion propagates outward.

- **Empty/short guard returns `of(null)` synchronously.** No HTTP call, no PENDING state, no race. Empty fields shouldn't talk to the server.

- **`catchError(() => of({ checkFailed: true }))`** turns HTTP errors into a recognizable validation error (`checkFailed`) instead of propagating the error and breaking the form. Different from `taken` — UI can distinguish "we couldn't check" from "definitely taken."

- **`first()` at the end** — defensive completion. The chain SHOULD complete naturally (`http.get()` completes, `timer(300)` completes, everything cascades), but `first()` guarantees it. If a future refactor introduces a never-completing source, `first()` keeps the form unstuck.

### The "must complete" rule

The single most common async-validator bug: the form gets stuck in `pending` forever.

```typescript
// BUGGY — never completes
return interval(1000).pipe(
  map(/* … */),
);
```

`interval` emits every second and never completes. Angular waits for the validator's Observable to complete before clearing `pending`. The form stays in `pending`, submit stays disabled, user gives up.

The defensive pattern: **always end the chain with `first()` or `take(1)`.** Even if your chain "obviously" completes, a future maintainer's `tap`/`merge`/`scan` that doesn't complete can break the validator silently. `first()` is one line; it's cheap insurance.

---

## UI states — `checking`, `available`, `taken`, `errored`

The validator returns errors; the template shows them. But during the 300ms debounce + the network round-trip, the field is in `PENDING` state and there's no error to show. The user needs feedback.

Four states the UI distinguishes:

| State | Form control state | UI |
| --- | --- | --- |
| `idle` | `pristine && !touched` | nothing |
| `checking` | `pending` | "Checking…" with subtle spinner |
| `available` | `valid` after async resolved | ✓ green checkmark |
| `taken` | `invalid && errors.taken` | ✗ "Already in use" |
| `errored` | `invalid && errors.checkFailed` | ⚠ "Couldn't check — try again" |

In a v22 template:

```html
<label>
  Username
  <input formControlName="username" autocomplete="username" />

  @if (form.controls.username.pending) {
    <span class="hint">Checking availability…</span>
  } @else if (form.controls.username.touched) {
    @if (form.controls.username.errors?.['taken']) {
      <span class="error">✗ Already in use</span>
    } @else if (form.controls.username.errors?.['checkFailed']) {
      <span class="warning">⚠ Couldn't check — please try again</span>
    } @else if (form.controls.username.valid && form.controls.username.value) {
      <span class="success">✓ Available</span>
    }
  }
</label>

<button type="submit" [disabled]="form.invalid || form.pending">
  Sign up
</button>
```

**Three patterns doing the work:**

- **`pending` checked first, separately from `errors`.** While checking, we don't yet know if it's taken — don't show "Available" or "Taken" hints during the wait.
- **`touched` gates the error display.** Without it, the form shows "Available" or "Couldn't check" the moment the user types one character. Showing validation feedback before the user has finished interacting is annoying.
- **`form.invalid || form.pending` for submit-disable.** `invalid` alone misses the case where the form is pending validation. Both checks needed.

### The "available" hint problem

Showing "✓ Available" after the async resolves looks great in demos. In practice:

- The user pastes a long username. Field shows "Checking…" → 300ms later, fires the HTTP call → response → "✓ Available."
- Two seconds later, they delete a character. Field shows "Checking…" → fires → "✓ Available."

Lots of green checks for the same name as they iterate. **Some apps choose to only show "Available" when the form was about to be submitted** (e.g., after blur), not on every keystroke. The recipe shows the always-visible version; the always-on-blur version requires `updateOn: 'blur'` in the form config (which delays all validation until blur, not just the success indicator).

---

## Composing with sync validators — sync first

Angular runs async validators **only after sync validators pass.** This is the spec, and it's load-bearing for performance.

```typescript
this.fb.control('', {
  validators: [
    Validators.required,
    Validators.minLength(3),
    Validators.pattern(/^[a-z0-9_]+$/),
  ],
  asyncValidators: [usernameAvailable()],
});
```

If the value is empty → `Validators.required` fails → async validator never runs → no HTTP call. Same for too-short or invalid-pattern.

This means **expensive checks (the network) only fire when the cheap checks (sync) pass.** A user typing invalid characters never burns server cycles on availability.

The implication: **always pair sync validators with async ones for the same field.** A length check, a pattern check, sometimes a "not a reserved name" check — all sync. The async hit only fires once those pass.

### Multiple async validators

You can attach multiple async validators to the same control. They run in parallel; their errors merge into the `errors` object:

```typescript
this.fb.control('', {
  asyncValidators: [
    usernameAvailable(),
    notBannedWord(),       // server keeps a banned-words list
    matchesCorpStandard(), // checks against an external HR system
  ],
});
```

If `usernameAvailable` returns `{ taken: true }` and `notBannedWord` returns `{ banned: true }`, the resulting `errors` object is `{ taken: true, banned: true }`. The template displays whichever message is more useful (or both).

The trade-off: parallel async means N parallel HTTP calls per validation cycle. Three async validators = three round trips per check. For most apps, fine. For high-traffic forms, consider combining into a single endpoint that returns all errors at once.

---

## Caching — don't re-check the same value

If the user types "alice", waits, sees "taken", changes to "alicia", waits, sees "available", changes back to "alice"... the validator fires the same HTTP call again. The result is determined; we already knew.

Cache the most recent N checks. Service-scoped so cache is shared across multiple uses of the validator (e.g., username on signup form, username on edit-profile form):

```typescript
// File: services/availability-cache.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, shareReplay } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AvailabilityCache {
  private readonly http = inject(HttpClient);
  private readonly cache = new Map<string, Observable<boolean>>();
  private readonly TTL_MS = 30_000;  // 30 seconds — short enough to catch real changes

  checkUsername(username: string): Observable<boolean> {
    const key = `username:${username}`;

    if (!this.cache.has(key)) {
      const shared = this.http
        .get<{ available: boolean }>(`/api/users/check?username=${encodeURIComponent(username)}`)
        .pipe(
          // Multiple concurrent subscribers share one HTTP call
          shareReplay({ bufferSize: 1, refCount: false }),
        );
      this.cache.set(key, shared.pipe(map(r => r.available)));
      // Evict after TTL
      setTimeout(() => this.cache.delete(key), this.TTL_MS);
    }

    return this.cache.get(key)!;
  }
}
```

Updated validator using the cache:

```typescript
export function usernameAvailable(): AsyncValidatorFn {
  const cache = inject(AvailabilityCache);

  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    const value = (control.value ?? '').trim();
    if (value.length < 3) return of(null);

    return timer(300).pipe(
      switchMap(() => cache.checkUsername(value)),
      map(available => available ? null : { taken: true }),
      catchError(() => of({ checkFailed: true } as ValidationErrors)),
      first(),
    );
  };
}
```

The cache lives in a service, so:

- **Multiple components using the same validator share the cache.** Signup and edit-profile both checking "alice"? One HTTP call total.
- **Repeated checks within 30 seconds skip the network entirely.** User flipping between two candidates fast = 2 HTTP calls, not 10.
- **The cache TTL bounds staleness.** A username freed up on the server still appears taken to the client for up to 30 seconds — acceptable for this domain.

This is the same `shareReplay` deduplication pattern from the [request-deduplication recipe](../http/request-deduplication.md), specialized for availability checks.

### The "current value" case

A common subtlety: in an edit-profile form, the current user's existing username should be "available" (because it's theirs). A pure availability check would mark it as taken.

```typescript
export function usernameAvailable(currentValue?: string): AsyncValidatorFn {
  const cache = inject(AvailabilityCache);

  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    const value = (control.value ?? '').trim();

    // The user hasn't changed the field — no server check needed.
    if (value === currentValue) return of(null);

    if (value.length < 3) return of(null);

    return timer(300).pipe(
      switchMap(() => cache.checkUsername(value)),
      map(available => available ? null : { taken: true }),
      catchError(() => of({ checkFailed: true } as ValidationErrors)),
      first(),
    );
  };
}

// Usage in edit profile:
this.fb.control(currentUser.username, {
  validators: [Validators.required, Validators.minLength(3)],
  asyncValidators: [usernameAvailable(currentUser.username)],
});
```

The `currentValue` parameter is "their" value — if they don't change it, the validator passes immediately without hitting the server.

---

## Variations

### Showing the last-checked value

For long forms with multiple async checks, users sometimes want to see what's actually been validated:

```typescript
@Injectable({ providedIn: 'root' })
export class ValidationStatusService {
  readonly lastChecked = signal<{ field: string; value: string; timestamp: number } | null>(null);

  recordCheck(field: string, value: string): void {
    this.lastChecked.set({ field, value, timestamp: Date.now() });
  }
}
```

Validators call `recordCheck()` inside their `tap`; a debug panel reads `lastChecked()` to show "Last checked: username='alice' at 14:32:08." Useful in dev; can be hidden in production.

### Cross-field async validation

Some validations span multiple fields — e.g., "Card number + expiry + CVV must be a valid card per the payment processor." That's a single async check on the parent group, not on individual fields:

```typescript
// Attach to the FormGroup, not a control
readonly form = this.fb.group({
  cardNumber: this.fb.control(''),
  expiry: this.fb.control(''),
  cvv: this.fb.control(''),
}, {
  asyncValidators: [cardValid()],
});

function cardValid(): AsyncValidatorFn {
  const http = inject(HttpClient);
  return (group: AbstractControl) => {
    const { cardNumber, expiry, cvv } = group.value;
    if (!cardNumber || !expiry || !cvv) return of(null);

    return timer(500).pipe(
      switchMap(() => http.post<{ valid: boolean }>('/api/cards/validate', { cardNumber, expiry, cvv })),
      map(res => res.valid ? null : { invalidCard: true }),
      catchError(() => of({ checkFailed: true } as ValidationErrors)),
      first(),
    );
  };
}
```

The error appears on the parent group (`form.errors?.invalidCard`), not on any individual control. UI displays it as a top-of-form banner instead of next to a single field.

### Async validation with optimistic UI

For low-risk fields (e.g., "email opt-in preference is a valid free-tier limit"), you can show the user a "tentatively OK" state while waiting:

```html
@if (form.controls.username.pending) {
  <span class="hint">Looks good… (checking)</span>
} @else if (form.controls.username.invalid) {
  <span class="error">{{ getErrorMessage(form.controls.username) }}</span>
}
```

Trade-off: less correct (you're claiming validity before knowing), but smoother UX for fields where the async check is purely confirmatory.

---

## Trade-offs and common pitfalls

**Use async validation when:**

- The check genuinely requires server knowledge (uniqueness, banned lists, external integrations)
- The cost of a false-positive on the client (saying "available" then getting an error on submit) is high
- The latency for the check is acceptable (sub-second; if it's multi-second, consider on-blur-only or on-submit-only)

**Skip async validation when:**

- The check can be done client-side (regex match, length, pattern) — sync is faster and avoids network
- The server already validates on submit and returns a clean error — for low-stakes forms, "let the server say no on submit" is often enough
- The latency is too high — better to validate on submit than to leave the user staring at "Checking…" for 3 seconds per character

### Common pitfalls

- **Validator that never completes.** The `pending` state hangs forever, form is permanently invalid. Always end the chain with `first()` or `take(1)`. If you're using a Subject, make sure something completes it.
- **Firing on empty values.** Empty fields shouldn't talk to the server. Guard at the top: `if (!value || value.length < 3) return of(null);`.
- **No debounce.** Fires on every keystroke. Either inline `timer(300)` in the validator, or use `updateOn: 'blur'` to wait until the field loses focus.
- **Ignoring sync validators.** Sync validators are free; async ones cost a round trip. Pair them — sync catches the cheap cases (length, pattern, required); async fires only when sync passes.
- **Not handling errors.** A server outage → the validator throws → the form is in an undefined state. Always `catchError` to a recognizable error key (`checkFailed`); the template tells the user "we couldn't check."
- **No UI feedback during `pending`.** User clicks submit, nothing happens, they think the form is broken. Show "Checking…" hint and disable submit on `pending || invalid`.
- **Caching for too long.** A 5-minute cache means a name freed up on the server still appears taken for 5 minutes. Match the TTL to how quickly the data changes — usernames: 30 seconds; banned words: minutes; SKUs: seconds.
- **No cache for the "current value" in edit forms.** Every edit-profile load fires a check for the user's own username. Skip the check when value === current.
- **Multiple parallel async validators when one combined endpoint would do.** Three validators = three round trips per check. Combine when latency matters.
- **Using `Validators.composeAsync` to add validators later** — works but is rarely needed. The control's `asyncValidators` array at construction is enough for most cases.
- **Reading `control.value` synchronously inside the async pipeline.** By the time the inner HTTP call fires, `control.value` may have changed (the user kept typing). Capture the value at validator entry: `const value = control.value;` then close over it.

---

## See also

- [Validation](../../forms/validation.md) — sync and async validators, custom validator patterns, error message strategies
- [Reactive Forms](../../forms/reactive-forms.md) — typed forms, FormBuilder, control APIs
- [Dynamic Forms](./dynamic-forms.md) — the previous recipe; uses `updateValueAndValidity` for related validation-shape changes
- [Race Conditions](../reactivity/race-conditions.md) — the `switchMap` cancellation that the validator relies on
- [Request Deduplication](../http/request-deduplication.md) — the `shareReplay` pattern that backs the availability cache
- [Search Engine](./search-engine.md) — debounce + switchMap patterns; the search-as-you-type cousin of this recipe

## References

- [`AsyncValidatorFn` (angular.dev)](https://angular.dev/api/forms/AsyncValidatorFn)
- [`AbstractControl.statusChanges` (angular.dev)](https://angular.dev/api/forms/AbstractControl#statusChanges) — for reactive subscriptions to PENDING transitions
- [`updateOn` form control option (angular.dev)](https://angular.dev/guide/forms/reactive-forms#updateOn) — when to use `'blur'` to delay validation
- [`first` (RxJS)](https://rxjs.dev/api/operators/first) — the completion-forcer at the end of the chain
- [Form validation guide (angular.dev)](https://angular.dev/guide/forms/form-validation) — the canonical Angular validation primer

## Demo source

Synthesized from common production async-validation patterns rather than a single demo file. The username-availability scenario is the canonical example, but the patterns (empty-guard, debounce-inline, error categorization, cache with TTL, current-value bypass) generalize to email uniqueness, slug availability, coupon code validity, SKU lookup, and any other "ask the server before submitting" check. All code is original.
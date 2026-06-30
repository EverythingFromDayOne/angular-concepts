---
recipe_id: "race-conditions"
title: "Race Conditions: Picking the Right Higher-Order Operator"
file: "recipes/reactivity/race-conditions.md"
primary_concept: "reactivity/rxjs/rxjs-higher-order"
related_concepts: ["reactivity/rxjs/rxjs", "reactivity/signals", "http/http", "reactivity/to-signal"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Race Conditions: Picking the Right Higher-Order Operator

> **What you'll build:** working fixes for the five most common race-condition
> bugs in Angular apps — stale responses overwriting fresh state, out-of-order
> responses, double-submit duplication, cancellation against destroyed
> components, and multi-source coordination. The unifying tool is **picking
> the right higher-order operator**: `switchMap`, `exhaustMap`, `concatMap`,
> or `mergeMap`. Each has a use case where it's the only right answer; each
> has cases where it's a silent bug.
>
> **Concepts you'll touch:** [Higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md), [RxJS](../../reactivity/rxjs/rxjs.md), [Signals](../../reactivity/signals.md), [HTTP](../../http/http.md)
>
> **Time:** ~30 minutes to read; ~2 hours to audit your codebase for
> the bugs once you can recognize them.

---

## The scenario

A user fills in a profile form, hits Save. The save spinner shows for a second. They see "Profile updated." Two seconds later, the page silently reverts to their old name.

What happened: the user typed faster than they saved. Two save requests were in flight at once. The slower one returned an "older" response (containing the older name). It overwrote the newer name in the UI.

This is the easiest of five distinct race-condition bugs that every team writes at least once. The fix is rarely "add `await` somewhere" — it's **picking the right asynchronous operator** for the relationship between source events and side effects. RxJS gives you four to choose from. Three of them are wrong for any given case; the fourth is correct.

This recipe walks through the five bugs in order of how common they are, shows the fix for each, and ends with a decision tree for picking the right operator the first time.

---

## The cast — four higher-order operators

Before the bugs: the four operators that solve them. Each "flattens" an Observable-of-Observables — a stream where each emission produces another stream — into a single output stream. They differ in **how they handle the case where a new source emission arrives before the previous inner stream has finished.**

```text
Source:           ──A───B─────C────────
A produces:          ─x─x─x─x─x→
B produces:              ─y─y─y─y→
C produces:                       ─z─z→
```

| Operator | Behavior on new emission while previous inner is active | Mnemonic |
| --- | --- | --- |
| **`switchMap`** | Cancel previous inner; subscribe to new | "Latest wins" |
| **`mergeMap`** | Subscribe to new in parallel; both run | "All run" |
| **`concatMap`** | Queue new; wait for previous to complete | "FIFO" |
| **`exhaustMap`** | Drop new; keep previous running | "First wins" |

Each has exactly one canonical use case. Using the wrong one for that case is one of the most common sources of subtle async bugs in Angular apps.

| Operator | Canonical use | Wrong use |
| --- | --- | --- |
| `switchMap` | Search-as-you-type (latest query wins) | POST creation (cancelled request may have hit the server) |
| `mergeMap` | Independent parallel ops (upload 5 files concurrently) | Sequence-sensitive saves (order is lost) |
| `concatMap` | Sequence-sensitive ops (edits must apply in user order) | Search (slow query blocks the next one) |
| `exhaustMap` | Submit button (drop double-clicks) | Search (drops keystrokes silently) |

The rest of the recipe is about which case each row in that table actually shows up in real code.

---

## Race 1 — stale response overwrites fresh state

**The bug** (everyone writes this version first):

```typescript
@Component({ /* … */ })
export class ProfileComponent {
  private readonly http = inject(HttpClient);
  readonly profile = signal<Profile | null>(null);

  // The user can click Save many times in a session.
  save(updates: Partial<Profile>) {
    this.http
      .patch<Profile>('/api/profile', updates)
      .subscribe(response => this.profile.set(response));
  }
}

interface Profile { name: string; bio: string; updatedAt: string; }
```

**The race**: user types "Aliciaa" (typo), hits Save. Backspace to "Alicia", hits Save again before the first request returns. Both PATCHes are in flight. The first one's response (containing "Aliciaa") arrives second because the server happened to be slow on it. The component sets `profile` to the stale value.

**The fix** — promote the save into a stream, use `switchMap`. When a new save starts, the previous in-flight save is unsubscribed; its response (if it ever arrives) is ignored:

```typescript
@Component({ /* … */ })
export class ProfileComponent {
  private readonly http = inject(HttpClient);
  readonly profile = signal<Profile | null>(null);
  private readonly save$ = new Subject<Partial<Profile>>();

  constructor() {
    this.save$.pipe(
      switchMap(updates => this.http.patch<Profile>('/api/profile', updates)),
      takeUntilDestroyed(),
    ).subscribe(response => this.profile.set(response));
  }

  save(updates: Partial<Profile>) {
    this.save$.next(updates);
  }
}
```

**Why it works**: `switchMap` unsubscribes from the previous inner Observable when a new one arrives. Only the latest save's response can reach `.set(response)`. If two saves are in flight, the older one's response is discarded.

### The HTTP-cancellation footnote

`switchMap` unsubscribing the HTTP Observable triggers the underlying browser request to abort — `HttpClient` uses `AbortController` under the hood. **But the request may still have reached the server.** Cancellation is best-effort:

- If the server hasn't processed the request yet → cancellation works; no side effect occurs
- If the server processed and is mid-write → the cancellation arrives too late; the side effect happens; the response just doesn't reach the client

For a PATCH that the user intended to fire, this is fine — the side effect was wanted. For idempotent operations (PATCH/PUT/DELETE with stable IDs), retries also produce the same result, so the cancelled-but-landed request is harmless.

**Where this matters is `POST` creation** — covered in Race 3.

---

## Race 2 — out-of-order responses (the "B before A" problem)

Distinct from Race 1 in framing, identical in cause and fix. The bug:

```typescript
// Search-as-you-type without switchMap
searchTerm$.pipe(
  debounceTime(300),
  mergeMap(query => this.http.get<Result[]>(`/api/search?q=${query}`)),
  // ^^^ wrong — parallel requests, results arrive out of order
).subscribe(results => this.results.set(results));
```

User types "Java" (request fires), then "JavaScript" (second request). Server responds to "JavaScript" first (cache hit) and "Java" second (cache miss, slower). The component renders Java's results even though the user is now looking at "JavaScript."

**The fix is the same**: replace `mergeMap` with `switchMap`. New emission cancels old.

This pattern is covered in detail in the [Search Engine recipe](../forms-and-search/search-engine.md) — it's the load-bearing reason that recipe leads with `switchMap`. If you've already followed that recipe, you've already fixed this race.

---

## Race 3 — double-submit (the "two charges" bug)

A user clicks "Place Order." The button doesn't change visually. They click again, thinking it didn't register. **Two orders are placed.** The user gets two confirmation emails and a complaint to support.

**The buggy code**:

```typescript
@Component({ /* … */ })
export class CheckoutComponent {
  private readonly http = inject(HttpClient);

  submit(order: Order) {
    this.http.post<OrderConfirmation>('/api/orders', order)
      .subscribe(confirmation => {
        this.router.navigate(['/orders', confirmation.id]);
      });
  }
}
```

The user clicks the button N times → N parallel POSTs → N orders. The component eventually navigates to one of them but the others have all completed server-side.

### Three layered fixes

This race deserves all three; defense in depth matters when money is involved.

**Fix 1 — `exhaustMap`** — ignore subsequent clicks while one is in flight:

```typescript
@Component({ /* … */ })
export class CheckoutComponent {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly submit$ = new Subject<Order>();

  constructor() {
    this.submit$.pipe(
      exhaustMap(order => this.http.post<OrderConfirmation>('/api/orders', order)),
      takeUntilDestroyed(),
    ).subscribe(confirmation => {
      this.router.navigate(['/orders', confirmation.id]);
    });
  }

  submit(order: Order) {
    this.submit$.next(order);
  }
}
```

`exhaustMap` **drops** new emissions while the inner Observable is still active. The first click triggers the POST; subsequent clicks emit values that `exhaustMap` discards entirely. Once the first POST completes (success or error), the operator becomes "available" again.

This is the cleanest fix and the right default for any submit button.

**Fix 2 — disable the button visually**:

```typescript
@Component({
  template: `
    <button (click)="submit(order)" [disabled]="submitting()">
      {{ submitting() ? 'Placing order…' : 'Place Order' }}
    </button>
  `,
})
export class CheckoutComponent {
  readonly submitting = signal(false);

  submit(order: Order) {
    if (this.submitting()) return;  // belt-and-suspenders
    this.submitting.set(true);
    this.http.post(/* … */).subscribe({
      next: () => { /* navigate */ },
      error: () => this.submitting.set(false),
      // Note: don't reset on next() since navigate destroys the component anyway
    });
  }
}
```

`exhaustMap` handles the click-stream level; the disabled button handles the visual level. Use both. The visual disable tells the user "yes, your click registered, please wait" — they're less likely to click again. The `exhaustMap` is the actual guarantee.

**Fix 3 — idempotency keys on the server**:

```typescript
import { v4 as uuid } from 'uuid';

submit(order: Order) {
  const idempotencyKey = uuid();
  this.submit$.next({ order, idempotencyKey });
}

// In the exhaustMap:
exhaustMap(({ order, idempotencyKey }) =>
  this.http.post<OrderConfirmation>('/api/orders', order, {
    headers: { 'Idempotency-Key': idempotencyKey },
  }),
),
```

The third layer: even if a network glitch causes a request to be retried (e.g., by the `retryWithBackoff` from the [retry recipe](../http/retry-with-backoff.md)), the server uses the idempotency key to deduplicate — the second request returns the cached result of the first instead of placing another order. This is the same pattern Stripe, AWS, and most payment APIs use.

Use all three layers for any non-idempotent action that costs money or sends an email. Each catches a different class of failure.

---

## Race 4 — cancellation race (the "ghost setter" bug)

```typescript
@Component({ /* … */ })
export class UserDetailComponent {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  readonly user = signal<User | null>(null);

  constructor() {
    this.route.params.subscribe(({ id }) => {
      this.http.get<User>(`/api/users/${id}`).subscribe(user => {
        this.user.set(user);
      });
    });
  }
}
```

**The race**: user navigates from `/users/123` to `/users/456` quickly. The first GET (for 123) is in flight when the component is destroyed and a new one is created. When 123's response arrives, the subscription is still alive (it wasn't unsubscribed); it calls `.set(user)` on the destroyed component's signal. The new component shows wrong data, or — in older Angular — produces a "setting on destroyed view" error.

**The fix** — `takeUntilDestroyed()` on every component subscription:

```typescript
@Component({ /* … */ })
export class UserDetailComponent {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  readonly user = signal<User | null>(null);

  constructor() {
    this.route.params.pipe(
      switchMap(({ id }) => this.http.get<User>(`/api/users/${id}`)),
      takeUntilDestroyed(),
    ).subscribe(user => this.user.set(user));
  }
}
```

Two improvements layered together:

- **`switchMap` over nested `subscribe`** — when params change, the old GET is cancelled; only the latest GET's response reaches the component. Fixes both the "ghost setter" and the "stale-data-after-fast-nav" cases.
- **`takeUntilDestroyed()`** — when the component is destroyed, the outer pipeline (params → GET) is unsubscribed entirely. The HTTP request is aborted; no setter call can fire on the destroyed component.

This pattern is covered in detail in the [takeUntilDestroyed recipe](./take-until-destroyed.md) — it's the v22 cleanup primitive for any Observable that needs to die when the component dies. Use it on every subscription in a component or directive without exception.

### Nested subscribe is the bigger smell

The `route.params.subscribe(() => http.get().subscribe())` pattern in the original code is a yellow flag every time. It indicates **two separate streams that should be one stream connected by a higher-order operator**. The flat version (with `switchMap`) is shorter, automatically handles cancellation, and produces the same data flow without the nested-callback shape.

> **Linter signal**: if you see nested `.subscribe()` calls inside a `.subscribe()` callback, the answer is almost always `switchMap`, `mergeMap`, `concatMap`, or `exhaustMap` — pick the right one for the relationship. Nested subscriptions also leak more easily because the inner subscription's cleanup isn't connected to the outer's lifecycle.

---

## Race 5 — multi-source race (auto-save vs explicit save)

A document editor has two save triggers:

- **Auto-save** — fires 2 seconds after the user stops typing
- **Explicit save** — fires when the user clicks Save

Each is implemented as a separate stream:

```typescript
// BUGGY — two separate save pipelines
constructor() {
  // Auto-save
  toObservable(this.documentSignal).pipe(
    debounceTime(2000),
    switchMap(doc => this.http.put('/api/document', doc)),
    takeUntilDestroyed(),
  ).subscribe();

  // Explicit save (called from button click)
  this.saveClick$.pipe(
    switchMap(() => this.http.put('/api/document', this.documentSignal())),
    takeUntilDestroyed(),
  ).subscribe();
}
```

**The race**: user clicks Save 1.9 seconds after their last edit. The auto-save fires 100ms later. Both PUTs are now in flight, **each in its own `switchMap`-protected stream**. The fact that they're independent streams means neither one cancels the other. Two PUTs go to the server. Whichever returns later wins (and the response may overwrite a newer document state).

**The fix** — merge the two trigger streams into one, so `switchMap` covers both:

```typescript
constructor() {
  const autoSave$ = toObservable(this.documentSignal).pipe(
    debounceTime(2000),
  );

  const explicitSave$ = this.saveClick$.pipe(
    map(() => this.documentSignal()),
  );

  merge(autoSave$, explicitSave$).pipe(
    distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
    switchMap(doc => this.http.put('/api/document', doc)),
    takeUntilDestroyed(),
  ).subscribe();
}
```

Two pieces doing work:

- **`merge`** — combines both trigger streams into one. Now there's a single `switchMap`; any new save (from either source) cancels the previous.
- **`distinctUntilChanged`** — if the explicit save fires with the same document state as a recent auto-save, this prevents a redundant PUT. The deep-equals via JSON is a quick implementation; for large documents use a proper equality function or a version number.

The pattern generalizes. **Anytime two sources can independently trigger the same side effect, merge them into one stream first.** The race vanishes by construction.

---

## The decision tree — picking the right operator

When you reach for a higher-order operator, ask:

```text
                   "What relationship do source emissions have to inner streams?"
                              │
       ┌──────────────────────┼─────────────────────────┐
       │                      │                         │
"Only latest matters"   "All must run"           "First click wins;
 (search, switch nav)    (independent ops)        ignore double-clicks"
       │                      │                         │
       ▼                      ▼                         ▼
   switchMap              mergeMap                 exhaustMap
                              │
                  ┌───────────┴───────────┐
                  │                       │
            "Order matters"           "Order doesn't matter"
            (sequential edits)        (parallel uploads)
                  │                       │
                  ▼                       ▼
              concatMap                mergeMap
```

Or as a table indexed by use case:

| Use case | Right operator | Why |
| --- | --- | --- |
| Search-as-you-type | `switchMap` | Latest query is the only one that matters |
| Detail-view navigation | `switchMap` | When user navigates to user/456, abandon the in-flight load for user/123 |
| Submit button | `exhaustMap` | Drop double-clicks; first click wins until response arrives |
| Upload 5 files concurrently | `mergeMap` | Independent ops, parallelism wins |
| Apply a sequence of optimistic UI updates to the server | `concatMap` | Order matters — edit B can't apply before edit A |
| Auto-save throttled to once per N seconds | `exhaustMap` | First save in window wins; subsequent saves dropped |
| Auto-save that should always reflect latest state | `switchMap` | New state cancels old save mid-flight |
| Bulk operations with rate limit | `concatMap` + `delay` | Serial with explicit pacing |
| Send analytics event with retries | `mergeMap` | Fire and forget, each event independent |
| User triggers a "process this" action that may take minutes | `exhaustMap` with explicit UI feedback | Drop accidental re-clicks; show progress |

If you're unsure: **start with `switchMap`** and audit. `switchMap` is wrong if (a) you're firing non-idempotent POSTs that cancellation can't undo, or (b) you need every emission to produce a side effect (uploads, analytics). For those, switch to `mergeMap` or `exhaustMap`. Otherwise `switchMap` is the safe default.

---

## Variations and advanced patterns

### Sequence numbers when cancellation isn't an option

Some APIs can't be cancelled — e.g., long-running batch jobs, or third-party services where the request fires synchronously from the server side. For these, **manually track sequence numbers and ignore stale responses on arrival**:

```typescript
@Component({ /* … */ })
export class SequencedSaveComponent {
  private readonly http = inject(HttpClient);
  readonly profile = signal<Profile | null>(null);
  private sequenceNumber = 0;

  save(updates: Partial<Profile>) {
    const seq = ++this.sequenceNumber;

    this.http.patch<Profile>('/api/profile', updates).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(response => {
      // Ignore if a newer save has already been issued.
      if (seq === this.sequenceNumber) {
        this.profile.set(response);
      }
    });
  }
}
```

Each save increments the sequence number. When a response arrives, it's only applied if its sequence matches the latest. Older responses are silently discarded.

This is a manual implementation of what `switchMap` does for you automatically — use it only when `switchMap` can't apply (e.g., when the save mechanism doesn't fit the Observable shape).

### Optimistic locking via version field

The server includes a `version` field in each response. Updates include the version they're based on. The server rejects the update if the version doesn't match (someone else updated in between):

```typescript
save(updates: Partial<Profile>) {
  const current = this.profile();
  if (!current) return;

  this.http.patch<Profile>('/api/profile', {
    ...updates,
    version: current.version,
  }).subscribe({
    next: response => this.profile.set(response),
    error: err => {
      if (err.status === 409) {
        // Conflict — reload and ask the user to redo
        this.reload();
      }
    },
  });
}
```

This solves a different race entirely — between **different users** editing the same record. The recipe focuses on single-user races; cross-user races need optimistic locking or last-write-wins policy. The fix is server-side; the client just respects 409 responses.

### Bulk operations with rate limit

You have 100 records to update and the server rate-limits you to 10/second. Use `concatMap` + `delay`:

```typescript
const records$ = from(this.records);

records$.pipe(
  concatMap(record =>
    this.http.put(`/api/items/${record.id}`, record).pipe(
      delay(100),  // 10/sec = 100ms between requests
    ),
  ),
  takeUntilDestroyed(),
).subscribe();
```

`concatMap` serializes the operations; `delay` paces them. A `mergeMap` here would fire all 100 in parallel and trip the rate limiter.

For known rate limits, `mergeMap(record => ..., CONCURRENCY)` gives you N parallel requests at a time:

```typescript
records$.pipe(
  mergeMap(record => this.http.put(`/api/items/${record.id}`, record), 5),
  //                                                                  ^^^ max 5 in flight
).subscribe();
```

---

## Trade-offs and common pitfalls

**Use these operators when:**

- Stream sources can produce overlapping work (clicks, keystrokes, navigation events)
- The relationship between source emissions and effects has a clear "right way"
- You want cancellation/queueing/coalescing built into the data flow rather than written manually

**Be cautious when:**

- The "cancellation" is incomplete on non-HTTP operations (file writes, timers, third-party SDKs). Test that cancellation actually undoes what you think it undoes.
- The user is paying for parallel work you implicitly assume serial — e.g., `mergeMap` of paid API calls when the cost model expects pacing.

### Common pitfalls

- **Using `mergeMap` for search-as-you-type** — results arrive out of order. Always `switchMap`.
- **Using `switchMap` for non-idempotent POSTs** — the cancellation is client-side only. The server may still process the cancelled request. Use `exhaustMap` for submits.
- **Using `concatMap` for any user-triggered action that could backlog** — if the user clicks 20 times while the first is processing, you get 20 sequential operations they may not have wanted. `exhaustMap` is almost always the right choice for user-action streams.
- **Nesting `subscribe` calls** — fix with a higher-order operator. Nested subscribe is the smell; the operators are the cure.
- **Forgetting `takeUntilDestroyed()`** — every component subscription needs it. The `Race 4 — cancellation race` pattern is one of the most common production bugs from missing this.
- **Assuming `switchMap` is "free"** — it's not. The cancelled request may still have cost the server CPU; may still have sent a notification or modified a record. Cancellation is best-effort, not transactional.
- **Two parallel pipelines with their own `switchMap`s acting on the same resource** — each `switchMap` only sees its own stream. The Race 5 multi-source bug. Always merge first.
- **`distinctUntilChanged` with reference equality on objects** — JavaScript object equality is identity; `{a:1}` !== `{a:1}`. Use a custom equality function or convert to a primitive (JSON.stringify, version number, etc.) before comparing.
- **`mergeMap` with unbounded concurrency on a large source** — kicks off thousands of parallel requests. Use the second argument (`mergeMap(fn, n)`) to cap concurrency.

---

## See also

- [Search Engine](../forms-and-search/search-engine.md) — the canonical `switchMap` use case, with multi-stage progression
- [takeUntilDestroyed (custom operators)](./take-until-destroyed.md) — the cleanup primitive for component subscriptions
- [Retry with Backoff](../http/retry-with-backoff.md) — composes with these operators; the interceptor sits outside, the operator inside
- [Higher-order operators (concept article)](../../reactivity/rxjs/rxjs-higher-order.md) — the underlying RxJS primitives in depth
- [Signals](../../reactivity/signals.md) — `signal`, `computed`, `toObservable` for bridging into these operators

## References

- [`switchMap` (RxJS)](https://rxjs.dev/api/operators/switchMap)
- [`exhaustMap` (RxJS)](https://rxjs.dev/api/operators/exhaustMap)
- [`concatMap` (RxJS)](https://rxjs.dev/api/operators/concatMap)
- [`mergeMap` (RxJS)](https://rxjs.dev/api/operators/mergeMap)
- [`merge` (RxJS)](https://rxjs.dev/api/index/function/merge)
- [Stripe — Idempotent Requests](https://stripe.com/docs/api/idempotent_requests) — the production reference for idempotency keys
- [Designing for HTTP retries — Google Cloud](https://cloud.google.com/architecture/scalable-and-resilient-apps#use_idempotency) — cancellation semantics in distributed systems
- [Choosing the right RxJS operator (Angular University)](https://blog.angular-university.io/rxjs-higher-order-mapping/) — a longer-form treatment of the same decision tree

## Demo source

Synthesized from common production race-condition patterns rather than a single demo file. The five-race taxonomy reflects the bugs that account for the majority of "async behavior is weird" support tickets in real Angular apps. The decision tree is the recipe's lasting contribution: most teams know one or two operators by reflex and apply them everywhere; the table makes the right choice mechanical instead of intuitive.
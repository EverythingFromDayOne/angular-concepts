---
recipe_id: "take-until-destroyed"
title: "Custom RxJS Operators with takeUntilDestroyed"
file: "recipes/reactivity/take-until-destroyed.md"
primary_concept: "reactivity/rxjs/rxjs"
related_concepts: ["dependency-injection/dependency-injection", "reactivity/to-signal", "reactivity/signals"]
demo_repo: "https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/takeUntilDestroyed"
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Custom RxJS Operators with `takeUntilDestroyed`

> **What you'll build:** a reusable `autoRefresh` RxJS operator that polls a
> data source on an interval and **cleans itself up** when the consuming
> component is destroyed — no manual `Subject`, no `ngOnDestroy`, no
> remembering to unsubscribe. Then a tiny stock-ticker component that uses
> the operator in one line.
>
> **Concepts you'll touch:** [RxJS](../../reactivity/rxjs/rxjs.md), [Dependency Injection](../../dependency-injection/dependency-injection.md), [toSignal](../../reactivity/to-signal.md)
>
> **Time:** ~15 minutes to read; ~30 minutes to implement and wire up tests.

---

## The scenario

You have a stock ticker, a live order book, a system-health dashboard, or
anything else that needs to **poll an API every N seconds**. Two
requirements are non-negotiable:

1. When the component is destroyed (the user navigates away, the modal
   closes, the parent removes the child), the polling **stops immediately**.
   No zombie HTTP requests, no setting state on a dead component.
2. The polling logic should be **reusable** — every place that needs
   periodic refresh shouldn't re-invent the same `interval + switchMap +
   teardown` boilerplate.

The v22 way: build a custom operator that bundles the polling + cleanup
into one line at the call site. The cleanup leans on `takeUntilDestroyed`,
which knows about the component's lifecycle through Angular's DI.

---

## The naive approach (pre-v16)

Before `takeUntilDestroyed` existed, the canonical pattern was a private
`Subject` you `.next()`'d in `ngOnDestroy`, paired with a `takeUntil` at
the end of every subscription:

```typescript
// Pre-v16 — works, but boilerplate-heavy and easy to forget
@Component({ /* ... */ })
export class StockComponent implements OnInit, OnDestroy {
  private readonly destroy$ = new Subject<void>();
  price: StockPrice | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    interval(5000).pipe(
      startWith(0),
      switchMap(() => this.http.get<StockPrice>('/api/stock/AAPL')),
      takeUntil(this.destroy$),  // ← easy to forget; bug if you do
    ).subscribe(price => (this.price = price));
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

Three things go wrong with this pattern in practice:

- **It's easy to forget `takeUntil(destroy$)` on a new subscription.** The
  TypeScript compiler can't help here — the subscription compiles fine
  without it. You only find out at runtime when a destroyed component
  starts setting properties on `null`.
- **Three classes per cleanup-needing component** — the `Subject`, the
  `ngOnDestroy` hook, the `takeUntil` operator. That's a lot of ceremony
  for "do this until you go away."
- **The polling logic is tangled with the cleanup logic.** Every component
  that polls re-implements the same `interval + switchMap` pattern. There's
  no clean place to put a `pollEvery(5000)` abstraction.

## The v22 way — `takeUntilDestroyed`

Angular 16 added **`takeUntilDestroyed`** in `@angular/core/rxjs-interop`.
Called in an **injection context** (component constructor, field initializer,
factory provider), it reads the current `DestroyRef` and wires up cleanup
automatically. The `Subject` + `ngOnDestroy` dance disappears.

```typescript
import { Component, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { interval, switchMap, startWith } from 'rxjs';

@Component({
  selector: 'app-stock',
  template: `<p>Price: {{ price() | currency }}</p>`,
})
export class StockComponent {
  private readonly http = inject(HttpClient);

  // Field initializers run in injection context, so takeUntilDestroyed()
  // can grab DestroyRef from the current injector. No explicit DestroyRef.
  readonly price = toSignal(
    interval(5000).pipe(
      startWith(0),
      switchMap(() => this.http.get<StockPrice>('/api/stock/AAPL')),
      takeUntilDestroyed(),
    ),
    { initialValue: null },
  );
}

interface StockPrice { symbol: string; price: number; }
```

The whole class is one statement long. No `ngOnDestroy`, no `Subject`, no
implements clauses. When the component is destroyed, `takeUntilDestroyed`
completes the observable, RxJS unsubscribes the chain, and any in-flight
HTTP request is cancelled.

### When `takeUntilDestroyed` needs an explicit `DestroyRef`

If you call `takeUntilDestroyed` **outside** an injection context — inside
a method, inside an `effect`'s body, or anywhere reached after the
constructor has finished — Angular has no way to find the `DestroyRef`
implicitly. Pass it explicitly:

```typescript
@Component({ /* ... */ })
export class StockComponent {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  // Method called from a template (click handler) — not an injection context
  startPolling(symbol: string): void {
    interval(5000).pipe(
      switchMap(() => this.http.get<StockPrice>(`/api/stock/${symbol}`)),
      takeUntilDestroyed(this.destroyRef),  // ← explicit, required here
    ).subscribe(/* ... */);
  }
}
```

Rule of thumb: **field initializers and the constructor body are
injection contexts.** Method bodies are not. If TypeScript complains
`takeUntilDestroyed() must be called from an injection context`, that's
the cue to pass `DestroyRef` explicitly.

### The third cleanup primitive — `inject(DestroyRef).onDestroy()`

`takeUntilDestroyed` is for **Observable chains**. For non-Observable
teardown — closing a WebSocket, releasing a Wake Lock, removing a global
event listener — use `inject(DestroyRef).onDestroy(callback)`:

```typescript
@Component({ /* ... */ })
export class StockComponent {
  constructor() {
    const socket = new WebSocket('wss://stocks.example.com');

    inject(DestroyRef).onDestroy(() => {
      socket.close();
    });
  }
}
```

Three v22 cleanup primitives, three use cases:

| Primitive | When to use |
| --- | --- |
| `takeUntilDestroyed()` | Observable chains in an injection context |
| `takeUntilDestroyed(destroyRef)` | Observable chains outside an injection context |
| `inject(DestroyRef).onDestroy(fn)` | Non-Observable teardown (sockets, locks, event listeners) |

You can mix all three in the same component. `ngOnDestroy` is no longer
needed for any of them — and in fact removing `implements OnDestroy`
from your components is a small but real readability win.

---

## The custom operator — `autoRefresh`

The `StockComponent` above is clean, but the `interval + startWith +
switchMap` polling pattern repeats anywhere we need periodic refresh.
Let's package it as a reusable operator.

The operator's job: turn a single observable (e.g. `http.get<Stock>(url)`)
into a polling observable that re-fires every N milliseconds and **cleans
up via `takeUntilDestroyed`** when the consumer is destroyed.

```typescript
// File: operators/auto-refresh.operator.ts
import { DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Observable, interval, startWith, switchMap, type MonoTypeOperatorFunction } from 'rxjs';

/**
 * Polls the source observable every `intervalMs` and cleans up when the
 * consuming injection context is destroyed.
 *
 * Must be invoked in an injection context (component field initializer
 * or constructor) so that DestroyRef can be resolved automatically.
 */
export function autoRefresh<T>(intervalMs: number): MonoTypeOperatorFunction<T> {
  const destroyRef = inject(DestroyRef);

  return (source$: Observable<T>) =>
    interval(intervalMs).pipe(
      startWith(0),                          // emit immediately, then every intervalMs
      switchMap(() => source$),              // re-subscribe to source on each tick
      takeUntilDestroyed(destroyRef),        // cancel on component destroy
    );
}
```

A couple of subtleties worth pointing out:

- **`inject(DestroyRef)` is called inside the operator factory**, not
  inside the returned function. The factory runs when the consumer writes
  `.pipe(autoRefresh(5000))` — at that moment, the consumer is in an
  injection context (a component field initializer), so `inject()` resolves
  correctly. The returned function captures `destroyRef` in its closure;
  by the time RxJS calls it to apply the operator, the injection context
  no longer exists, but we don't need it anymore.

- **`MonoTypeOperatorFunction<T>` is the right signature.** The operator
  takes `Observable<T>` and returns `Observable<T>` — the type doesn't
  change, only the timing of emissions does. Using
  `MonoTypeOperatorFunction` (instead of `OperatorFunction<T, T>`) is the
  v22-idiomatic shorthand.

- **`startWith(0)` is what makes it emit immediately.** Without it, you'd
  wait `intervalMs` for the first value — usually not what you want for
  a dashboard that should show data on mount.

### Using the operator

Now the stock component reads like English:

```typescript
import { Component, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { autoRefresh } from './operators/auto-refresh.operator';

@Component({
  selector: 'app-stock',
  template: `
    @if (price(); as p) {
      <p>{{ p.symbol }}: {{ p.price | currency }}</p>
    } @else {
      <p>Loading…</p>
    }
  `,
})
export class StockComponent {
  private readonly http = inject(HttpClient);

  readonly price = toSignal(
    this.http.get<StockPrice>('/api/stock/AAPL').pipe(
      autoRefresh(5000),  // ← polls every 5s, auto-cleans on destroy
    ),
    { initialValue: null },
  );
}

interface StockPrice { symbol: string; price: number; }
```

Every other component that needs polling reuses the same operator:

```typescript
readonly metrics = toSignal(
  this.http.get<Metrics>('/api/metrics').pipe(autoRefresh(10_000)),
  { initialValue: null },
);
```

No `Subject`, no `ngOnDestroy`, no `takeUntil`, no manual unsubscribe. The
operator handles teardown silently and correctly.

### Variant — error recovery in the operator

The version above will stop refreshing if the source observable errors
(an HTTP 500, a network blip). For dashboards you usually want polling
to **keep going** through transient errors:

```typescript
// operators/auto-refresh-resilient.operator.ts
import { DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval, startWith, switchMap, catchError, of, type Observable, type MonoTypeOperatorFunction } from 'rxjs';

export function autoRefreshResilient<T>(
  intervalMs: number,
  onError: (err: unknown) => T,
): MonoTypeOperatorFunction<T> {
  const destroyRef = inject(DestroyRef);

  return (source$: Observable<T>) =>
    interval(intervalMs).pipe(
      startWith(0),
      switchMap(() =>
        source$.pipe(
          catchError(err => of(onError(err))),  // recover per-tick
        ),
      ),
      takeUntilDestroyed(destroyRef),
    );
}
```

```typescript
readonly price = toSignal(
  this.http.get<StockPrice>('/api/stock/AAPL').pipe(
    autoRefreshResilient(5000, () => ({ symbol: 'AAPL', price: NaN })),
  ),
  { initialValue: null },
);
```

The `catchError` lives **inside** the `switchMap` — that's load-bearing.
If you put it outside, a single error completes the outer stream and
polling stops. Inside, it only recovers the current tick, and the next
interval emission triggers a fresh attempt.

---

## Real-world considerations

### Combining with signal inputs

If the polled URL depends on a signal input (e.g. the symbol is bound
from a parent), bridge the signal to an observable with `toObservable`
and feed it through `switchMap`:

```typescript
import { Component, inject, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { switchMap } from 'rxjs';
import { autoRefresh } from './operators/auto-refresh.operator';

@Component({ /* ... */ })
export class StockComponent {
  readonly symbol = input.required<string>();
  private readonly http = inject(HttpClient);

  readonly price = toSignal(
    toObservable(this.symbol).pipe(
      switchMap(symbol =>
        this.http.get<StockPrice>(`/api/stock/${symbol}`).pipe(
          autoRefresh(5000),
        ),
      ),
    ),
    { initialValue: null },
  );
}
```

When the parent changes `symbol`, the outer `switchMap` cancels the
previous polling chain and starts a new one for the new symbol — and
`autoRefresh`'s `takeUntilDestroyed` handles the final cleanup when the
component itself is destroyed.

### Pausing when the tab is hidden

Production polling should usually stop when the user isn't looking — it
saves backend load and battery on mobile. Compose with another stream
gated on `document.visibilityState`:

```typescript
import { fromEvent, merge, startWith, filter, switchMap, of } from 'rxjs';

const visible$ = merge(
  fromEvent(document, 'visibilitychange'),
  of(null),
).pipe(
  startWith(null),
  filter(() => document.visibilityState === 'visible'),
);

// In the component:
readonly price = toSignal(
  visible$.pipe(
    switchMap(() =>
      this.http.get<StockPrice>('/api/stock/AAPL').pipe(
        autoRefresh(5000),
      ),
    ),
  ),
  { initialValue: null },
);
```

When the tab is hidden, `visible$` doesn't emit, so the outer `switchMap`
stays subscribed to nothing — no requests fire. When the tab returns,
`visible$` re-emits and polling resumes.

### Testing the operator

The operator is testable with `TestBed` + fake timers, since it depends
only on `DestroyRef` for cleanup:

```typescript
import { TestBed } from '@angular/core/testing';
import { fakeAsync, tick } from '@angular/core/testing';
import { Component, runInInjectionContext, Injector } from '@angular/core';
import { of } from 'rxjs';
import { autoRefresh } from './auto-refresh.operator';

describe('autoRefresh operator', () => {
  it('emits on each interval tick', fakeAsync(() => {
    const injector = TestBed.inject(Injector);
    const source$ = of('tick');
    const emissions: string[] = [];

    runInInjectionContext(injector, () => {
      source$.pipe(autoRefresh(1000)).subscribe(v => emissions.push(v));
    });

    tick(0);    // startWith emits immediately
    tick(1000);
    tick(1000);
    tick(1000);

    expect(emissions).toEqual(['tick', 'tick', 'tick', 'tick']);
  }));
});
```

`runInInjectionContext` is the v22 helper that opens an injection context
on demand — useful for tests where you'd otherwise need a full component
fixture just to call `inject(DestroyRef)`. See [Dependency Injection](../../dependency-injection/dependency-injection.md)
for the full injection-context story.

---

## Trade-offs and when NOT to use this

**Use `autoRefresh` (or write your own teardown-aware operator) when:**

- The component needs periodic refresh and you've written the
  `interval + switchMap + takeUntilDestroyed` triple in three or more
  components already
- You want one place to add cross-cutting polling behavior — visibility
  pausing, error recovery, telemetry — without revisiting every consumer
- The polling interval is reasonably stable (5s, 30s, 60s); for highly
  variable schedules, consider event-driven approaches instead

**Reach for a different approach when:**

- **You only have one polling site.** Inline the `interval +
  switchMap + takeUntilDestroyed` chain — abstraction isn't free, and
  one-off code is fine.
- **You need server-pushed updates, not polling.** Server-Sent Events
  (`EventSource`) or WebSockets are lower-latency and more efficient.
  `inject(DestroyRef).onDestroy(() => socket.close())` handles their
  teardown.
- **You're polling because the API doesn't support change subscriptions.**
  Consider building an SSE proxy in front of the API instead of
  polling on the client.
- **The polled data feeds a chart or animation that needs smooth
  interpolation.** Polling produces stepped values; for smooth visuals,
  fetch sparse data and interpolate client-side, or use a streaming API.

**Common pitfalls to avoid:**

- **Polling with `mergeMap` instead of `switchMap`.** If a tick fires
  while the previous request is still pending, `mergeMap` runs both in
  parallel — you can end up with stale responses overwriting fresh ones.
  `switchMap` cancels the previous, which is almost always what you want
  for polling.
- **Putting `catchError` outside the `switchMap`.** Errors complete the
  outer stream and polling dies. Always recover per-tick (inside the
  `switchMap`'s pipe).
- **Calling `takeUntilDestroyed()` from a method body.** It won't
  compile — pass an explicit `DestroyRef` instead, or restructure so
  the subscription is set up at construction time.
- **Forgetting that `inject()` in the operator factory runs at the
  *call site*.** If you reuse the operator across multiple call sites
  (different components), each call gets its own `DestroyRef`. That's
  what you want; just understand it's the call site's lifecycle that
  governs cleanup, not the operator file's.

---

## See also

- [RxJS](../../reactivity/rxjs/rxjs.md) — operator factories, higher-order observables, the operator anatomy
- [toSignal](../../reactivity/to-signal.md) — converting the observable result to a signal for templates
- [Dependency Injection](../../dependency-injection/dependency-injection.md) — `inject()`, `DestroyRef`, injection contexts, `runInInjectionContext`
- [HTTP](../../http/http.md) — `HttpClient` cancellation semantics that polling relies on
- [Signal Inputs](../../reactivity/signal-inputs.md) — bridging signal inputs to polling chains via `toObservable`

## References

- [`takeUntilDestroyed` API (angular.dev)](https://angular.dev/api/core/rxjs-interop/takeUntilDestroyed)
- [`DestroyRef` API (angular.dev)](https://angular.dev/api/core/DestroyRef)
- [`runInInjectionContext` API (angular.dev)](https://angular.dev/api/core/runInInjectionContext)
- [RxJS — Creating custom operators](https://rxjs.dev/guide/operators#creating-new-operators-from-scratch)

## Demo source

Adapted from [`AngularDemos/features/takeUntilDestroyed`](https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/takeUntilDestroyed) — `operators/autoRefresh.operator.ts` and `stock.component.ts`.
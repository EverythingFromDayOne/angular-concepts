---
roadmap_node: "to-signal-from-signal"
title: "toSignal & toObservable"
file: "reactivity/to-signal.md"
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
> Written fresh for Angular v16+, baseline v22.

# toSignal & toObservable

> **Lead with this:** `toSignal()` wraps an Observable as a signal you can
> read synchronously in templates and reactive contexts; `toObservable()`
> goes the other direction, turning a signal into an Observable you can pipe
> through RxJS operators. They are the bridge between Angular's two reactivity
> models.

## What it is

Angular has two reactivity models that co-exist:

| Model | Core primitive | Push or pull | When it emits |
| --- | --- | --- | --- |
| **RxJS** | `Observable` | Push | Source decides when |
| **Signals** | `Signal` | Pull | Consumer reads current value |

Most real-world Angular apps have both. `HttpClient` returns Observables.
Route params come through Observables. Form controls expose `valueChanges` as
an Observable. But components increasingly want to work with signals —
`computed()`, `effect()`, and template bindings that read synchronously.

`toSignal()` and `toObservable()` are the official bridge utilities,
both in `@angular/core/rxjs-interop`. They stabilized in v20 and are the
recommended way to cross the Observable/signal boundary in v22.

## How it works under the hood

### The fundamental mismatch

The problem both utilities solve is a mismatch in the reactivity contracts:

- **Observable** is lazy and push-based. It doesn't have a "current value"
  until a subscriber activates it. When the source emits, it pushes to
  subscribers. There may be zero emissions, one, or infinite. There's no
  way to read the latest value without subscribing and waiting.

- **Signal** is eager and pull-based. It always has a current value. Any
  reactive context can read it synchronously at any time. Changes propagate
  to consumers through the reactive graph, but the signal can always be
  queried for its present state.

You can't just wrap one in the other naively. If you try to read an
Observable in a computed signal, you'd have to subscribe inside the
computation — a side effect inside a pure derivation, which breaks the
glitch-free guarantee.

### How toSignal() bridges Observable → Signal

`toSignal()` resolves the mismatch by maintaining a **value slot**:

1. On construction, it subscribes to the Observable immediately (like
   `async` pipe does). This is an eager subscription — side effects in the
   Observable pipeline fire at construction time.
2. Every time the Observable emits, `toSignal` writes the new value into
   an internal signal slot.
3. The returned `Signal<T>` is a read-only view of that slot.
4. When the injection context is destroyed, the subscription is
   automatically cleaned up via `DestroyRef`.

The "initial value problem": Observables may not emit synchronously. But
signals must always have a value. Until the first emission, `toSignal`
returns either `undefined` (default), a provided `initialValue`, or throws
at construction time if you use `requireSync: true` and the Observable fails
to emit immediately.

```
Observable source
       │
       │  emits asynchronously
       ▼
toSignal internal value slot ← writes new value on each emission
       │
       │  reads synchronously
       ▼
Signal<T> (returned to caller) ← reactive graph can track reads here
```

### How toObservable() bridges Signal → Observable

`toObservable()` resolves the mismatch the other direction:

1. Internally it creates a `ReplaySubject(1)` — an Observable that
   caches and replays its most recent emission to new subscribers.
2. It registers an `effect()` that watches the signal. Whenever the signal
   changes (after settling), the effect calls `subject.next(newValue)`.
3. The returned Observable wraps the `ReplaySubject`.

Two key behaviors follow from this design:

**First subscription gets the current value synchronously.** Because
`ReplaySubject(1)` replays its last emission, subscribing immediately
receives the signal's current value without waiting.

**Rapid signal changes coalesce.** `effect()` runs after the current
synchronous block finishes. If you call `signal.set(1)`, `signal.set(2)`,
`signal.set(3)` in one synchronous operation, the effect only sees the
final settled value (3) and emits it once — not three separate emissions.

```
Signal<T>
       │
       │  effect() watches the signal
       ▼
effect fires after signal settles → calls ReplaySubject(1).next(value)
       │
       │  subscribers receive via Observable
       ▼
Observable<T> (returned to caller) ← can be piped through RxJS operators
```

### Old approach — manual subscription + markForCheck

Before these utilities, the common pattern for using an Observable in a
component was:

```typescript
// Old pattern — manual subscription lifecycle management
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OldComponent implements OnInit, OnDestroy {
  data: ApiData | null = null;
  private sub = new Subscription();

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.sub = this.api.getData().subscribe(result => {
      this.data = result;
      this.cdr.markForCheck();  // manually notify CD
    });
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();  // manually clean up
  }
}
```

`toSignal` eliminates all three pain points: the manual subscribe, the
`markForCheck()` call, and the unsubscribe in `ngOnDestroy`.

## Basic usage

### toSignal — Observable to Signal

```typescript
import { Component, inject, computed } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { interval } from 'rxjs';
import { UserService } from './user.service';

@Component({
  selector: 'app-ticker',
  standalone: true,
  template: `<p>Tick: {{ tick() }}</p>`,
})
export class TickerComponent {
  // interval() never emits synchronously → signal starts as undefined
  // initialValue prevents the undefined until first emission
  tick = toSignal(interval(1000), { initialValue: 0 });
}
```

#### Handling the initial undefined

Three strategies — pick the one that fits:

```typescript
// Strategy 1 — initialValue (most common for async sources)
userData = toSignal(this.userService.getUser(), { initialValue: null });
// Type: Signal<User | null>  — you handle the null in the template

// Strategy 2 — requireSync (for sources that ALWAYS emit synchronously)
// Works with: BehaviorSubject, of(), startWith(), ReplaySubject
count = toSignal(this.counterSubject$, { requireSync: true });
// Type: Signal<number>  — no undefined possible

// Strategy 3 — no option (for sources where undefined makes sense)
lastMessage = toSignal(this.websocket.messages$);
// Type: Signal<Message | undefined>  — handle undefined explicitly
```

#### Error handling

If the Observable errors, that error is stored and re-thrown every time the
signal is read. This is the default behavior:

```typescript
// Default: error rethrows on every read of the signal
users = toSignal(this.api.getUsers());

// Template reads users() → throws if the Observable errored
// Catch in an error boundary or use rejectErrors to route to global handler

// rejectErrors: true → errors go to Angular's global error handler,
// signal keeps returning the last successful value
users = toSignal(this.api.getUsers(), { rejectErrors: true });
```

#### Using toSignal outside an injection context

`toSignal()` needs to retrieve a `DestroyRef` to manage cleanup. By default
it looks for the current injection context (constructor, field initializer).
When you're outside one — inside `ngOnChanges`, a button handler, a service
method — pass the `injector` explicitly:

```typescript
import { Component, Injector, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

@Component({ /* ... */ })
export class FlexibleComponent {
  private injector = inject(Injector);

  // Called outside the constructor — needs explicit injector
  loadUserData(userId: string) {
    return toSignal(
      this.userService.getUser(userId),
      { injector: this.injector, initialValue: null }
    );
  }
}
```

Alternatively, wrap it in `runInInjectionContext` from the injector:

```typescript
import { runInInjectionContext } from '@angular/core';

loadUserData(userId: string) {
  return runInInjectionContext(this.injector, () =>
    toSignal(this.userService.getUser(userId), { initialValue: null })
  );
}
```

### toObservable — Signal to Observable

```typescript
import { Component, signal, computed } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { debounceTime, switchMap } from 'rxjs';

@Component({
  selector: 'app-search',
  standalone: true,
  template: `
    <input (input)="query.set($any($event.target).value)" />
    @for (result of results(); track result.id) {
      <li>{{ result.name }}</li>
    }
  `,
})
export class SearchComponent {
  query = signal('');
  results = signal<SearchResult[]>([]);

  constructor(private search: SearchService) {
    // Bridge signal → Observable to use RxJS operators
    toObservable(this.query).pipe(
      debounceTime(300),
      switchMap(q => q ? this.search.search(q) : of([]))
    ).subscribe(results => this.results.set(results));
    // Note: for this specific pattern, httpResource + debounced() is cleaner in v22
    // See signals.md for that approach
  }
}
```

Note that `toObservable` also requires an injection context — it creates an
`effect()` internally. Pass `{ injector }` when needed, same as `toSignal`.

## Real-world patterns

### Pattern 1 — Bridging route params into a signal chain

The most common real-world use: route params arrive as Observables from
`ActivatedRoute`, but you want to work with signals throughout the component.
(In v22, `withComponentInputBinding()` handles this automatically for simple
cases — this pattern covers when you need the full Observable pipeline.)

```typescript
import { Component, inject, computed } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { httpResource } from '@angular/common/http';

@Component({
  selector: 'app-product',
  standalone: true,
  template: `
    @if (product.isLoading()) {
      <app-spinner />
    } @else if (product.hasValue()) {
      <h1>{{ product.value().name }}</h1>
      <p>Category: {{ categoryName() }}</p>
    }
  `,
})
export class ProductComponent {
  private route = inject(ActivatedRoute);

  // Bridge route params Observable → signal
  productId = toSignal(
    this.route.paramMap.pipe(map(p => p.get('id') ?? '')),
    { initialValue: '' }
  );

  // Signal-based HTTP — driven by the productId signal
  product = httpResource<Product>(() =>
    this.productId() ? `/api/products/${this.productId()}` : undefined
  );

  // Derive more signals from the product data
  categoryName = computed(() =>
    this.product.hasValue() ? this.product.value().category.name : '—'
  );
}
```

### Pattern 2 — Using takeUntilDestroyed with toObservable

When you need the Observable stream from `toObservable()` and also want
automatic cleanup tied to the component lifecycle:

```typescript
import { Component, signal, inject } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { takeUntilDestroyed, DestroyRef } from '@angular/core/rxjs-interop';
import { switchMap } from 'rxjs';

@Component({ /* ... */ })
export class AnalyticsComponent {
  activeTab = signal<'overview' | 'detail'>('overview');
  private destroyRef = inject(DestroyRef);

  constructor(private analytics: AnalyticsService) {
    toObservable(this.activeTab).pipe(
      switchMap(tab => this.analytics.getTabData(tab)),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(data => this.updateChart(data));
  }

  private updateChart(data: ChartData): void { /* ... */ }
}
```

### Pattern 3 — Wrapping a BehaviorSubject service for migration

During migration from Observable-based services to signals, `toSignal` with
`requireSync` is the cleanest bridge because `BehaviorSubject` always has a
current value:

```typescript
// Legacy service with BehaviorSubject
@Injectable({ providedIn: 'root' })
export class CartService {
  private _items$ = new BehaviorSubject<CartItem[]>([]);
  items$ = this._items$.asObservable();

  add(item: CartItem): void {
    this._items$.next([...this._items$.value, item]);
  }
}

// Component uses toSignal — BehaviorSubject emits synchronously → no undefined
@Component({ /* ... */ })
export class CartComponent {
  private cartService = inject(CartService);

  // requireSync: true because BehaviorSubject always has a value
  items = toSignal(this.cartService.items$, { requireSync: true });
  itemCount = computed(() => this.items().length);
  total = computed(() =>
    this.items().reduce((sum, item) => sum + item.price * item.qty, 0)
  );
}
```

This works during a gradual migration — the `CartService` stays Observable-
based while new code consumes it as a signal.

## Common mistakes

### Mistake 1 — Forgetting that toSignal subscribes immediately

Unlike the `async` pipe (which subscribes when the view renders), `toSignal`
subscribes at the moment it's called — usually in the constructor. Observable
pipelines with side effects (logging, analytics, mutations) fire immediately:

```typescript
@Component({ /* ... */ })
export class MyComponent {
  // ❌ The HTTP request fires on construction, not when the view renders
  // If the component is created but never displayed, the request still fires
  data = toSignal(
    this.http.get('/api/data').pipe(
      tap(() => console.log('Request fired!'))  // fires in constructor
    ),
    { initialValue: null }
  );
}
```

This is usually fine for HTTP requests (you want the data as early as
possible), but surprises developers used to the `async` pipe's lazy
subscription behavior.

### Mistake 2 — Using requireSync with an async Observable

`requireSync: true` throws a runtime error if the Observable doesn't emit
immediately. It's only safe with synchronous sources:

```typescript
// ❌ Runtime error — HTTP is async, never emits synchronously
users = toSignal(this.http.get<User[]>('/api/users'), { requireSync: true });
// Error: NG0601: toSignal() called with requireSync but Observable did not emit synchronously

// ✅ Use initialValue instead for async sources
users = toSignal(this.http.get<User[]>('/api/users'), { initialValue: [] });

// ✅ requireSync is safe for: BehaviorSubject, of(), startWith(), ReplaySubject
count = toSignal(this.counter$, { requireSync: true });  // BehaviorSubject — safe
```

### Mistake 3 — Expecting toObservable to emit for every signal.set()

`toObservable` coalesces rapid signal changes. Multiple `.set()` calls in
the same synchronous block produce only one Observable emission:

```typescript
const counter = signal(0);
const counter$ = toObservable(counter);

counter$.subscribe(v => console.log('Emitted:', v));

counter.set(1);
counter.set(2);
counter.set(3);
// Logs: "Emitted: 3" — only once, not three times
```

This is by design and usually desirable (no duplicate network requests for
intermediate values). If you need every value, use a `Subject` and emit
manually instead.

### Mistake 4 — Memory leak from toSignal called outside injection context without injector

`toSignal` without an injection context and without `manualCleanup: true` or
an explicit `injector` throws an error. But if you pass `manualCleanup: true`
without cleaning up, you get a leak:

```typescript
// ❌ Memory leak — subscription never cleaned up
ngOnChanges(): void {
  this.data = toSignal(this.api.get(this.id), {
    manualCleanup: true,   // disables auto-cleanup
    injector: this.injector,
  });
  // subscription lives until the Observable completes — possibly forever
}

// ✅ Use explicit injector (auto-cleanup on component destroy)
ngOnChanges(): void {
  this.data = toSignal(this.api.get(this.id), {
    injector: this.injector,   // auto-cleanup via injector's DestroyRef
    initialValue: null,
  });
}
```

## How this evolved

> - **Angular 2–15 (2016–2022):** No bridge utilities. Developers manually
>   subscribed to Observables in `ngOnInit`, called `markForCheck()` in the
>   subscription callback, and unsubscribed in `ngOnDestroy`. The `async`
>   pipe was the idiomatic alternative — lazier but template-only. The
>   `takeUntilDestroyed` pattern (via community libraries) helped, but
>   required boilerplate.
>
> - **Angular 16 (May 2023):** `toSignal()` and `toObservable()` introduced
>   in `@angular/core/rxjs-interop` as **developer preview** alongside the
>   first signal release. `takeUntilDestroyed` operator also introduced here.
>
> - **Angular 17 (Nov 2023):** Bridge utilities improved with better
>   injection context handling and more predictable cleanup. `requireSync`
>   and error-propagation behavior stabilized.
>
> - **Angular 18 (May 2024):** The `equal` option added to `ToSignalOptions`,
>   letting you control when a new Observable emission is considered a change
>   (useful for objects where reference changes but content doesn't).
>
> - **Angular 20 (May 2025):** `toSignal()` and `toObservable()` graduated
>   to **stable**, along with the rest of the foundational signal APIs.
>   `debugName` option added to `ToSignalOptions` for DevTools visibility.
>
> - **Angular 22 (now):** Both utilities are stable and the standard bridge
>   between the two reactivity models. For new code, the Angular team
>   recommends preferring `httpResource()` over `toSignal(httpClient.get())`
>   where possible, since `resource()` handles loading state, errors, and
>   abort signals natively. `toSignal` remains essential for non-HTTP
>   Observable sources: form controls, router events, WebSockets, and
>   third-party Observable APIs.

## See also

- [Signals](./signals.md) — the full signal API, including `resource()` and
  `httpResource()` as alternatives to `toSignal` for HTTP
- [Signal Inputs](./signal-inputs.md) — how `input()` integrates with signal
  inputs (route params via `withComponentInputBinding()` often replaces
  `toSignal(route.paramMap)`)
- [RxJS](./rxjs/rxjs.md) — the Observable model `toSignal` bridges from
- [Official docs — RxJS interop](https://angular.dev/ecosystem/rxjs-interop)
- [Official docs — toSignal](https://angular.dev/api/core/rxjs-interop/toSignal)
- [Official docs — toObservable](https://angular.dev/api/core/rxjs-interop/toObservable)

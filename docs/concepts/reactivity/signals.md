---
roadmap_node: "signals"
title: "Signals"
file: "reactivity/signals.md"
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

# Signals

> **Lead with this:** Signals are values that notify Angular precisely when
> they change — replacing whole-tree change detection with surgical updates
> that touch only the components that actually read the changed data.

## What it is

A **signal** is a wrapper around a value that tracks every place that value is
read. When the value changes, Angular knows exactly which components,
computations, and effects depend on it — and updates only those, nothing else.

Signals are the foundation of modern Angular reactivity. They replace three
older patterns:

| Old pattern | New signal-based pattern |
| --- | --- |
| Component property + Zone.js detecting mutations | `signal()` |
| Getter that recalculates on every CD cycle | `computed()` |
| `ngOnChanges` + `ngOnDestroy` cleanup | `effect()` |
| `@Input()` decorator | `input()` |
| `BehaviorSubject` for state with sync access | `signal()` |
| `Observable` + `async` pipe for derived data | `computed()` |

The Angular team has been building toward signals as the default reactivity
model since v16. As of v22, the entire signal API surface is stable, and new
Angular projects are signal-first by default.

## How it works under the hood

Signals implement a **push-pull reactive graph**.

**The graph.** Every `signal`, `computed`, `effect`, `linkedSignal`, and
`resource` is a node. Edges connect producers to consumers: when a signal is
read inside a `computed`, an edge is recorded from the signal (producer) to
the computed (consumer). The same applies for templates — when a template
reads a signal during rendering, an edge connects the signal to that
component's view.

**The push half.** When you call `signal.set()` or `signal.update()`, Angular
walks the graph from that signal outward and **marks every dependent node as
"dirty"** — but does not yet recompute anything. This is cheap: it's a flag
flip, no derivations run, no DOM updates happen. Multiple `set()` calls in a
row only mark dirty once per affected node.

**The pull half.** Recomputation happens lazily, only when someone actually
reads the dirty node. Calling `computed()` checks if it's dirty: if yes, it
runs the derivation and caches the result; if no, it returns the cached value.
Templates pull during change detection. Effects are scheduled to run after the
current synchronous code finishes.

**Dynamic dependencies.** The set of dependencies for a `computed` is
recomputed every time the derivation runs. If your `computed` reads `count`
in one branch and `name` in another, only the signals actually read on the
current evaluation are tracked. This is fundamentally different from RxJS's
static operator pipelines — signals have no fixed "stream"; the graph rewires
itself per evaluation.

**Glitch-free guarantee.** Consider `a`, `b = computed(() => a() + 1)`, and
`c = computed(() => a() + b())`. If you set `a` to a new value, a naive
system might let `c` see the new `a` but the stale `b`. Angular prevents this:
when `c` is read after `a` changes, the system ensures `b` is up-to-date
first. You never observe an inconsistent intermediate state.

**Memoization.** `computed` caches its last value and skips re-running its
derivation if none of its dependencies actually changed. Crucially, "actually
changed" uses `Object.is` by default — not deep equality. You can override
this with a custom `equal` function.

**No zone.js needed.** This entire system is independent of Zone.js. In
zoneless apps (the v22 default for new projects), signals are the *only*
mechanism telling Angular when to re-render. Zone.js never enters the picture.

## Basic usage

### signal — writable state

Create a signal by calling `signal()` with an initial value. Read it by calling
it as a function. Write to it with `.set()` or `.update()`.

```typescript
import { signal } from '@angular/core';

const count = signal(0);

console.log(count());         // 0 — calling the signal reads it

count.set(5);                  // direct write
console.log(count());         // 5

count.update(c => c + 1);      // compute from previous value
console.log(count());         // 6
```

Signals can hold any value type — primitives, objects, arrays. For object
values, `.set()` requires a new reference (Angular detects changes by
reference identity, not deep comparison):

```typescript
const user = signal({ name: 'Alice', age: 30 });

// ❌ Mutating the existing object does NOT notify consumers
user().age = 31;

// ✅ Create a new object reference
user.set({ ...user(), age: 31 });

// ✅ Or use update() for cleaner ergonomics
user.update(u => ({ ...u, age: u.age + 1 }));
```

#### Read-only signals

`WritableSignal` has an `asReadonly()` method that returns a read-only view —
useful when you want to expose state without letting consumers mutate it:

```typescript
import { Component, signal, inject } from '@angular/core';

@Component({ /* ... */ })
export class CounterStateService {
  private readonly _count = signal(0);

  readonly count = this._count.asReadonly();   // public read-only

  increment() {
    this._count.update(v => v + 1);
  }
}
```

> **Note:** `asReadonly()` prevents calling `.set()` and `.update()`. It does
> **not** prevent deep mutation of an object value. For deep immutability,
> use `readonly` types and discipline.

### computed — derived state

`computed()` creates a read-only signal whose value is derived from other
signals. The derivation re-runs only when one of its dependencies actually
changes.

```typescript
import { signal, computed } from '@angular/core';

const firstName = signal('Ada');
const lastName  = signal('Lovelace');

const fullName = computed(() => `${firstName()} ${lastName()}`);

console.log(fullName());        // "Ada Lovelace"

firstName.set('Grace');
console.log(fullName());        // "Grace Lovelace" — re-derived
```

Two important properties:

**Lazy.** A `computed`'s derivation does not run until someone reads it. If
you create a `computed` but never call it, its derivation never executes.

**Memoized.** Once read, the result is cached. Reading the same `computed`
twice with no upstream changes returns the cached value — the derivation
runs once.

Combine them and you can safely write expensive derivations in `computed` —
they run at most once per dependency change, and only if anyone is listening.

### effect — synchronizing with non-reactive code

An `effect()` runs whenever the signals it reads change. Use it to bridge from
the reactive graph to the outside world: logging, DOM APIs that don't accept
signals, third-party libraries, localStorage, analytics events.

```typescript
import { Component, signal, effect } from '@angular/core';

@Component({ /* ... */ })
export class ThemeComponent {
  theme = signal<'light' | 'dark'>('light');

  constructor() {
    // Runs once immediately, then re-runs whenever theme() changes
    effect(() => {
      document.body.classList.toggle('dark-mode', this.theme() === 'dark');
      localStorage.setItem('theme', this.theme());
    });
  }
}
```

`effect()` must be called within an injection context — typically the
constructor — or you must pass an `injector` explicitly.

#### When NOT to use effect

`effect()` is for **side effects to the outside world**. It is not for
deriving values from other signals — use `computed` for that. The official
Angular docs explicitly warn against using effects for state synchronization
between signals, because it leads to fragile update orderings and harder-to-
trace bugs. If you're tempted to call `signal.set()` inside an `effect()`,
you almost certainly want a `computed` or `linkedSignal` instead.

### linkedSignal — writable state that resets when its source changes

Sometimes you need a writable signal whose initial value depends on another
signal — and that should reset when the source changes:

```typescript
import { signal, linkedSignal } from '@angular/core';

const shippingOptions = signal(['Ground', 'Air', 'Sea']);

// Initialize to the first option, but allow user to change it
const selectedOption = linkedSignal(() => shippingOptions()[0]);

console.log(selectedOption());           // 'Ground'

selectedOption.set('Sea');
console.log(selectedOption());           // 'Sea' — user choice respected

// When the source list changes, selectedOption resets to the new first option
shippingOptions.set(['Email', 'Will Call', 'Postal']);
console.log(selectedOption());           // 'Email' — reset
```

For the case where you want to preserve the user's selection when possible
(rather than always resetting), `linkedSignal` accepts a `{ source, computation }`
options form where the computation receives the previous value and can decide
what to do.

### resource — async data as a signal

`resource()` lets you wrap an async operation as a signal-based reactive value.
When the inputs change, the loader re-runs. The result is a signal you can
read synchronously.

```typescript
import { Component, signal, computed, resource } from '@angular/core';

@Component({ /* ... */ })
export class UserProfileComponent {
  userId = signal<string>('123');

  userResource = resource({
    // Reactive params — re-runs loader when any read signal changes
    params: () => ({ id: this.userId() }),

    // Async loader — Angular passes params and an abortSignal automatically
    loader: ({ params, abortSignal }) =>
      fetch(`/api/users/${params.id}`, { signal: abortSignal })
        .then(r => r.json()),
  });

  // The resource exposes a value signal you can read synchronously
  firstName = computed(() => {
    if (this.userResource.hasValue()) {
      return this.userResource.value().firstName;
    }
    return undefined;
  });
}
```

Resources automatically abort in-flight requests when their params change — no
manual `switchMap`-equivalent boilerplate. They also expose `isLoading()`,
`error()`, and status signals so you can build loading and error UIs cleanly.

For HTTP specifically, `httpResource()` is a shortcut that wraps `HttpClient`:

```typescript
import { httpResource } from '@angular/common/http';

userResource = httpResource<User>(() => `/api/users/${this.userId()}`);
```

It sends a GET request whenever the URL-returning function's read signals
change. See [HTTP](../http/typed-requests.md) for the full picture.

### untracked — reading without subscribing

Inside a `computed` or `effect`, you sometimes want to read a signal *without*
creating a dependency on it — e.g. log the current counter value when the
user changes, but don't re-run when the counter alone changes:

```typescript
import { signal, effect, untracked } from '@angular/core';

const currentUser = signal('alice');
const counter = signal(0);

effect(() => {
  // Re-runs when currentUser changes, but NOT when counter alone changes
  const user = currentUser();
  console.log(`User: ${user}, counter: ${untracked(counter)}`);
});
```

### Signals in templates

In templates, you read a signal the same way as in code — by calling it as a
function. Angular automatically subscribes the template to the signal during
rendering:

```html
<!-- count() is called during template rendering — Angular tracks the read -->
<p>Count is: {{ count() }}</p>
<button (click)="count.set(count() + 1)">Increment</button>

@if (count() > 10) {
  <p>That's a lot!</p>
}

@for (item of items(); track item.id) {
  <li>{{ item.name }}</li>
}
```

You don't need the `async` pipe — signals are already synchronous. Reading
them directly in the template is the idiomatic style.

## Real-world patterns

### Pattern 1 — Service-level state with read-only public API

A canonical pattern for shared state — a service exposes a read-only signal
and methods that mutate the private writable one:

```typescript
import { Injectable, signal, computed } from '@angular/core';

interface Todo { id: number; text: string; done: boolean; }

@Injectable({ providedIn: 'root' })
export class TodoStore {
  // Private writable — only this service can mutate
  private readonly _todos = signal<Todo[]>([]);

  // Public read-only view
  readonly todos = this._todos.asReadonly();

  // Derived signals — automatically stay in sync
  readonly remaining = computed(() =>
    this._todos().filter(t => !t.done).length
  );

  readonly completed = computed(() =>
    this._todos().filter(t => t.done).length
  );

  add(text: string): void {
    this._todos.update(list => [
      ...list,
      { id: Date.now(), text, done: false },
    ]);
  }

  toggle(id: number): void {
    this._todos.update(list =>
      list.map(t => t.id === id ? { ...t, done: !t.done } : t)
    );
  }

  remove(id: number): void {
    this._todos.update(list => list.filter(t => t.id !== id));
  }
}
```

Consumers read `todos()`, `remaining()`, `completed()` in templates and never
need to know whether the underlying state is signal-based, RxJS-based, or
anything else. The public surface is a stable signal API.

### Pattern 2 — Search-as-you-type with resource

A live search field that fetches as the user types, debouncing and aborting
stale requests automatically:

```typescript
import { Component, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { debounced } from '@angular/core';   // Angular 22+

@Component({
  selector: 'app-product-search',
  standalone: true,
  template: `
    <input [value]="query()" (input)="query.set($any($event.target).value)" />

    @if (search.isLoading()) {
      <p>Searching…</p>
    } @else if (search.error()) {
      <p>Error: {{ search.error().message }}</p>
    } @else if (search.hasValue()) {
      <ul>
        @for (item of search.value(); track item.id) {
          <li>{{ item.name }}</li>
        }
      </ul>
    }
  `,
})
export class ProductSearchComponent {
  query = signal('');
  debouncedQuery = debounced(this.query, 300);  // 300ms debounce

  search = httpResource<Product[]>(() => {
    const q = this.debouncedQuery();
    return q ? `/api/products?q=${encodeURIComponent(q)}` : undefined;
  });
}
```

When the URL function returns `undefined`, the resource sits idle — no
request is sent. When `debouncedQuery()` settles on a non-empty value, the
resource fires the request. If the user types again before the request
finishes, Angular aborts the in-flight request automatically.

### Pattern 3 — Bridging RxJS streams into signals

Most real codebases have existing Observables — from `HttpClient`, router
events, `FormGroup.valueChanges`, third-party libraries. `toSignal()` bridges
them in:

```typescript
import { Component, inject, computed } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

@Component({ /* ... */ })
export class ArticleDetailComponent {
  private route = inject(ActivatedRoute);

  // Bridge the route params Observable into a signal
  params = toSignal(this.route.paramMap, { initialValue: null });

  slug = computed(() => this.params()?.get('slug'));
}
```

The reverse direction is `toObservable()` — wrap a signal as an Observable.
See [toSignal & toObservable](./to-signal.md) for details.

## Common mistakes

### Mistake 1 — Mutating an object signal in place

Signals detect changes by reference identity. Mutating a held object does not
trigger updates:

```typescript
// ❌ Mutation — signal doesn't notify consumers
const user = signal({ name: 'Alice', age: 30 });
user().age = 31;  // direct mutation; no notification

// ✅ New reference — signal notifies all dependents
user.update(u => ({ ...u, age: u.age + 1 }));
```

This applies to arrays too: `array().push(x)` doesn't notify, but
`array.update(a => [...a, x])` does. Tools like Immer can help if you find
this repetitive.

### Mistake 2 — Calling .set() inside an effect

`effect()` is for side effects to the outside world. Writing to a signal
inside an effect creates fragile update orderings and is explicitly warned
against in the Angular docs. If you find yourself doing this, you almost
certainly want `computed` or `linkedSignal`:

```typescript
// ❌ Effect that writes to another signal — fragile, hard to reason about
effect(() => {
  fullName.set(`${firstName()} ${lastName()}`);
});

// ✅ Use computed — derivation is the right pattern for this
const fullName = computed(() => `${firstName()} ${lastName()}`);
```

If you genuinely must write a signal from an effect (rare), Angular requires
you to set `allowSignalWrites: true` explicitly — a signal that you should
stop and reconsider the design.

### Mistake 3 — Reading signals after an await inside an effect

The reactive context is **synchronous only**. Once you `await`, the context
is lost — any signal reads after the await are not tracked as dependencies:

```typescript
// ❌ theme() read after await is NOT tracked
effect(async () => {
  const data = await fetchUserData();
  console.log(`User: ${data.name}, Theme: ${theme()}`);
  //                                       ^^^^^^^ — not a dependency
});

// ✅ Read all signals synchronously, before any await
effect(async () => {
  const currentTheme = theme();  // tracked
  const data = await fetchUserData();
  console.log(`User: ${data.name}, Theme: ${currentTheme}`);
});
```

This is the most common signals pitfall for developers coming from RxJS,
where streams handle async transparently.

### Mistake 4 — Calling a signal in a non-reactive context expecting tracking

Reading a signal in `ngOnInit`, a button handler, or any other one-shot
callback works — but does not subscribe that callback to future changes.
Signal tracking only happens inside `computed`, `effect`, `linkedSignal`,
`resource`, or a template:

```typescript
// ❌ This reads count() once on init — doesn't re-run when count changes
ngOnInit(): void {
  console.log(`Initial count: ${this.count()}`);
}

// ✅ Use effect() if you want to react to changes
constructor() {
  effect(() => {
    console.log(`Count: ${this.count()}`);  // re-runs on every change
  });
}
```

### Mistake 5 — Expecting equality checks beyond Object.is

Signals use `Object.is` for change detection by default. Two structurally
equal but referentially distinct objects are considered different:

```typescript
const data = signal({ x: 1 });

data.set({ x: 1 });   // NEW reference, even though shape is identical
// — signal notifies all dependents, even though "nothing changed" semantically
```

If this is a problem, provide a custom `equal` function:

```typescript
const data = signal({ x: 1 }, {
  equal: (a, b) => a.x === b.x,  // custom equality
});

data.set({ x: 1 });   // signal does NOT notify — equal returns true
```

The same `equal` option works on `computed` and `linkedSignal`.

## How this evolved

> - **Angular 1–15 (2010–2022):** No signals. Reactivity worked through Zone.js
>   monkey-patching async APIs and running full-tree change detection on every
>   event. Fine-grained reactivity was only available through RxJS Observables
>   with the `async` pipe, third-party stores (NgRx, Akita), or `OnPush` +
>   manual `markForCheck` calls.
>
> - **Angular 16 (May 2023):** `signal`, `computed`, and `effect` introduced
>   as **developer preview**. First time Angular shipped a built-in
>   fine-grained reactivity primitive.
>
> - **Angular 17.1 (Jan 2024):** Signal inputs (`input()`, `input.required()`,
>   `input.transform()`) and signal queries (`viewChild()`, `contentChild()`)
>   landed.
>
> - **Angular 17.3 (Mar 2024):** Signal-based model inputs (`model()`)
>   landed — replacing two-way binding's banana-in-a-box plumbing.
>
> - **Angular 19 (Nov 2024):** `linkedSignal` and the `resource` API landed
>   in developer preview. First time Angular had a built-in answer to "how
>   do I do async data with signals?"
>
> - **Angular 20 (May 2025):** `effect`, `linkedSignal`, `toSignal` graduated
>   to **stable**. Signal inputs and view queries had already graduated. All
>   the foundational primitives are now production-ready. Zoneless graduated
>   to developer preview.
>
> - **Angular 20.2 (Q4 2025):** Zoneless graduated to **stable**, with
>   improvements in error handling and SSR.
>
> - **Angular 22 (now):** `resource`, `rxResource`, `httpResource` stable.
>   `OnPush` becomes the **default change detection strategy** for new
>   components. New apps run zoneless by default. The signal API surface is
>   complete and the recommended state primitive for all new Angular code.

## See also

- [Signal Inputs](./signal-inputs.md) — `input()` replacing `@Input()`
- [toSignal & toObservable](./to-signal.md) — bridging with RxJS
- [Change Detection](../components/change-detection.md) — how signals replace
  Zone.js-driven CD; what zoneless really means
- [RxJS](./rxjs/rxjs.md) — when to reach for RxJS vs signals
- [HTTP](../http/typed-requests.md) — `httpResource` for signal-driven HTTP
- [Signal Forms](../forms/signal-forms.md) — forms built on signals
- [Official docs — Signals overview](https://angular.dev/guide/signals)
- [Official docs — linkedSignal](https://angular.dev/guide/signals/linked-signal)
- [Official docs — resource](https://angular.dev/guide/signals/resource)

---
roadmap_node: "signal-inputs"
title: "Signal Inputs"
file: "reactivity/signal-inputs.md"
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
> Written fresh for Angular v17.1+, baseline v22.

# Signal Inputs

> **Lead with this:** Signal inputs (`input()`) replace `@Input()` with a
> version that is natively reactive — the parent's bound value arrives as a
> signal you can use directly in `computed()`, `effect()`, and templates
> without any lifecycle hook plumbing.

## What it is

Every Angular component accepts data from its parent through inputs. Before
signal inputs, you used the `@Input()` decorator: a property that Angular
writes to when the parent passes a value down. Signal inputs replace that
with `input()` — a function that returns a **read-only signal** whose value
Angular updates when the parent binding changes.

The shift is deeper than syntax. With `@Input()`, your component reacts to
input changes through `ngOnChanges` — a lifecycle hook that hands you a
`SimpleChanges` object. With `input()`, you react the same way you react to
any other signal: via `computed()` for derived values or `effect()` for side
effects. No `SimpleChanges`, no manual diffing, no change object to unwrap.

The return type of `input()` is `InputSignal<T>` — a read-only signal that
extends Angular's base `Signal<T>`. This means it works everywhere a signal
works: in templates (by calling it), in `computed()`, in `effect()`, in
`linkedSignal()`, in `resource()`.

Signal inputs stabilized in Angular v20 and are the recommended pattern for
all new components and directives in v22.

## How it works under the hood

### Old mechanism — @Input() and the decorator reflection system

`@Input()` is a TypeScript decorator that attaches metadata to a class
property using `Reflect.metadata`. At compile time, Angular reads this
metadata to know which properties are inputs, what their public aliases are,
and what transforms to apply.

At runtime, when a parent component binds `[userId]="id"`, Angular's change
detection writes to the child component's class instance directly:
`childInstance.userId = newValue`. This is a plain property assignment. The
property carries no intrinsic reactivity — it's just a value sitting on the
object.

To let the component react to that write, Angular calls `ngOnChanges` with a
`SimpleChanges` map describing what changed. The component must implement this
hook, check which input changed (`if (changes['userId'])`), and manually
trigger whatever reaction is needed. If the reaction is deriving another
value, you do that computation inside `ngOnChanges` and store the result in
another property. If it's a side effect, you run it there directly.

The lifecycle also has a timing constraint: `@Input()` values are `undefined`
in the constructor — they're set between construction and `ngOnInit`. Reading
an input in the constructor is a common source of bugs.

```
Parent binds [userId]="currentId"
         │
         ▼
Angular CD runs → writes childInstance.userId = currentId
         │
         ▼
Angular calls ngOnChanges({ userId: SimpleChange { previousValue, currentValue } })
         │
         ▼
Component manually reacts inside ngOnChanges:
  if (changes['userId']) this.loadUser(this.userId);
```

### New mechanism — input() and the signal graph

`input()` creates an `InputSignal<T>` — a specialized read-only signal backed
by Angular's reactive graph. The signal's internal slot holds the current
input value. When the parent binds a new value, Angular writes it into the
signal's slot.

The write to the signal's slot triggers the same notification chain as any
other signal write: all reactive consumers (computed signals, effects,
template views) that previously read this input signal are marked dirty and
scheduled for re-evaluation. No lifecycle hook is called. No `SimpleChanges`
object is constructed. The reaction is driven entirely by the reactive graph.

A key difference from `@Input()`: the signal slot exists at construction time.
Reading `this.userId()` in the constructor is safe — it returns the initial
value (or `undefined` for optional inputs before the first binding). This
eliminates the `undefined` in constructor bug class entirely.

```
Parent binds [userId]="currentId"
         │
         ▼
Angular CD runs → writes userId signal's internal slot = currentId
         │
         ▼
Signal notifies all its consumers:
  • computed(() => ...) that read userId() → marked dirty
  • effect(() => ...) that read userId() → scheduled to re-run
  • Template view that read userId() → RefreshView flag set
         │
         ▼
Consumers re-evaluate lazily:
  • computed() re-runs its derivation on next read
  • effect() re-runs after current synchronous block
  • Template view re-renders on next CD tick
```

No `ngOnChanges`. No `SimpleChanges`. No manual `if (changes['userId'])`.
The reactive graph does the wiring automatically.

## Basic usage

### Optional input with a default value

```typescript
import { Component, input, computed } from '@angular/core';

@Component({
  selector: 'app-counter',
  standalone: true,
  template: `
    <p>Count: {{ count() }}</p>
    <p>Double: {{ double() }}</p>
  `,
})
export class CounterComponent {
  // Optional input — defaults to 0 if parent doesn't bind it
  count = input(0);

  // Derive from the input signal directly — no ngOnChanges needed
  double = computed(() => this.count() * 2);
}
```

```html
<!-- Parent -->
<app-counter [count]="myCount" />
<app-counter />  <!-- count defaults to 0 -->
```

### Required input

```typescript
import { Component, input } from '@angular/core';

interface User { id: string; name: string; email: string; }

@Component({
  selector: 'app-user-card',
  standalone: true,
  template: `
    <h2>{{ user().name }}</h2>
    <p>{{ user().email }}</p>
  `,
})
export class UserCardComponent {
  // Required — parent MUST bind this; TypeScript enforces it at the call site
  user = input.required<User>();
}
```

```html
<!-- ✅ Correct — required input provided -->
<app-user-card [user]="currentUser" />

<!-- ❌ Compile error — required input missing -->
<app-user-card />
```

### Both NgModule and standalone patterns

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach with @Input() decorator (Angular 2–17)
import { Component, Input, OnChanges, SimpleChanges, NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

@Component({
  selector: 'app-badge',
  template: `<span [class]="badgeClass">{{ label }}</span>`,
})
export class BadgeComponent implements OnChanges {
  @Input() label = '';
  @Input() variant: 'primary' | 'danger' = 'primary';

  badgeClass = '';

  ngOnChanges(changes: SimpleChanges): void {
    // Must manually react to input changes
    if (changes['label'] || changes['variant']) {
      this.badgeClass = `badge badge--${this.variant}`;
    }
  }
}

@NgModule({
  declarations: [BadgeComponent],
  imports: [BrowserModule],
})
export class AppModule {}
```

```typescript
// Standalone + signal inputs (Angular 17.1+ — recommended)
import { Component, input, computed } from '@angular/core';

@Component({
  selector: 'app-badge',
  standalone: true,
  template: `<span [class]="badgeClass()">{{ label() }}</span>`,
})
export class BadgeComponent {
  label   = input('');
  variant = input<'primary' | 'danger'>('primary');

  // Reactive derivation — no ngOnChanges, no manual diffing
  badgeClass = computed(() => `badge badge--${this.variant()}`);
}
```

### Input with alias

When the public binding name needs to differ from the internal property name:

```typescript
@Component({ selector: 'app-slider', standalone: true, template: `...` })
export class SliderComponent {
  // Public binding: [sliderValue]
  // Internal property: value
  value = input(0, { alias: 'sliderValue' });
}
```

```html
<app-slider [sliderValue]="50" />
```

### Input with transform

Transform runs on every incoming value before the signal stores it. Use it
for coercion (string attribute → boolean/number), not for complex derivations:

```typescript
import { Component, input, booleanAttribute, numberAttribute } from '@angular/core';

@Component({
  selector: 'app-toggle',
  standalone: true,
  template: `<button [disabled]="disabled()">{{ label() }}</button>`,
})
export class ToggleComponent {
  label = input('Toggle');

  // booleanAttribute is a built-in transform:
  // <app-toggle disabled> (string "true" or "") → true
  // <app-toggle [disabled]="false"> → false
  disabled = input(false, { transform: booleanAttribute });

  // numberAttribute coerces string attributes to numbers with an optional default
  size = input(16, { transform: numberAttribute });
}
```

```html
<!-- All of these work cleanly with booleanAttribute -->
<app-toggle disabled />
<app-toggle [disabled]="isDisabled" />
<app-toggle [disabled]="false" />
```

Angular ships two built-in transform utilities: `booleanAttribute` (coerces
truthy string attributes and booleans to `boolean`) and `numberAttribute`
(coerces to `number`). The Angular team's guidance: keep transforms about
coercion and light parsing — not about changing what the input is about.
Complex derivations belong in `computed()`.

### model() — two-way binding

`model()` is the signal-input companion for two-way binding. It creates a
`ModelSignal<T>` — a **writable** signal where the component can both read
the parent's value and write back to it:

```typescript
import { Component, model } from '@angular/core';

@Component({
  selector: 'app-rating',
  standalone: true,
  template: `
    @for (star of stars; track $index) {
      <button (click)="rating.set($index + 1)">
        {{ $index < rating() ? '★' : '☆' }}
      </button>
    }
  `,
})
export class RatingComponent {
  rating = model(0);        // writable — component can call .set() and .update()
  stars = [0, 1, 2, 3, 4]; // five stars
}
```

```html
<!-- Parent — two-way binding with [()] syntax -->
<app-rating [(rating)]="productRating" />
```

When `rating.set(3)` fires inside the component, the parent's `productRating`
updates automatically — no manual `EventEmitter.emit()` needed. Model inputs
do not support `transform`.

## Real-world patterns

### Pattern 1 — Deriving multiple values from one input signal

With `@Input()`, you'd compute derived values inside `ngOnChanges` and store
them in separate properties. With `input()`, all derivations are `computed()`
signals that auto-update:

```typescript
import { Component, input, computed } from '@angular/core';

interface Product { id: string; name: string; price: number; stock: number; }

@Component({
  selector: 'app-product-card',
  standalone: true,
  template: `
    <h3>{{ product().name }}</h3>
    <p [class.discounted]="hasDiscount()">
      {{ displayPrice() }}
    </p>
    @if (!inStock()) {
      <span class="badge">Out of stock</span>
    }
  `,
})
export class ProductCardComponent {
  product = input.required<Product>();

  // All derivations live in computed() — no ngOnChanges anywhere
  inStock    = computed(() => this.product().stock > 0);
  hasDiscount = computed(() => this.product().price < 50);
  displayPrice = computed(() =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
      .format(this.product().price)
  );
}
```

### Pattern 2 — Reacting to an input change with a side effect

The `effect()` replacement for `ngOnChanges` + side effects:

```typescript
import { Component, input, effect, inject } from '@angular/core';
import { AnalyticsService } from './analytics.service';

@Component({
  selector: 'app-article',
  standalone: true,
  template: `<article>{{ article().content }}</article>`,
})
export class ArticleComponent {
  article = input.required<{ id: string; title: string; content: string }>();
  private analytics = inject(AnalyticsService);

  constructor() {
    effect(() => {
      // Re-runs every time article() changes
      // No ngOnChanges, no firstChange guard, no SimpleChanges unwrapping
      this.analytics.trackView(this.article().id, this.article().title);
    });
  }
}
```

### Pattern 3 — Route params as signal inputs

With `withComponentInputBinding()`, route parameters and query params flow
directly into signal inputs — no need to inject `ActivatedRoute`:

```typescript
// app.config.ts
import { provideRouter, withComponentInputBinding } from '@angular/router';

export const appConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
  ],
};
```

```typescript
// Route: /products/:id?tab=details
@Component({
  selector: 'app-product-detail',
  standalone: true,
  template: `
    <h1>Product {{ id() }}</h1>
    <p>Tab: {{ tab() }}</p>
  `,
})
export class ProductDetailComponent {
  // Route param ':id' flows in as a signal
  id = input.required<string>();

  // Query param '?tab=...' flows in as a signal (optional)
  tab = input('details');
}
```

When the route param changes (e.g. navigating from `/products/1` to
`/products/2`), `id()` updates and all its dependents automatically re-derive.

## Common mistakes

### Mistake 1 — Expecting ngOnChanges to fire for signal inputs

`input()` does not trigger `ngOnChanges`. If you implement `ngOnChanges` in
a component that uses signal inputs, it will never be called for those inputs:

```typescript
// ❌ ngOnChanges never fires for signal inputs
@Component({ /* ... */ })
export class MyComponent implements OnChanges {
  userId = input.required<string>();  // signal input

  ngOnChanges(changes: SimpleChanges): void {
    // This never runs for userId — signal inputs don't go through ngOnChanges
    if (changes['userId']) this.loadUser(this.userId());
  }
}

// ✅ Use effect() to react to signal input changes
@Component({ /* ... */ })
export class MyComponent {
  userId = input.required<string>();
  private userService = inject(UserService);

  constructor() {
    effect(() => {
      this.loadUser(this.userId());  // re-runs whenever userId changes
    });
  }
}
```

### Mistake 2 — Trying to write to a signal input

`InputSignal<T>` is read-only. It doesn't have `.set()` or `.update()`:

```typescript
@Component({ /* ... */ })
export class MyComponent {
  count = input(0);

  // ❌ Compile error — InputSignal has no .set()
  increment() { this.count.set(this.count() + 1); }
}
```

If you need a writable value that the parent initializes but the component
also modifies, use `model()` for two-way binding, or maintain a separate
internal signal initialized from the input:

```typescript
@Component({ /* ... */ })
export class CounterComponent {
  initialCount = input(0);

  // Internal writable state — seeded from the input on first render
  count = linkedSignal(() => this.initialCount());

  increment() { this.count.update(c => c + 1); }  // ✅ writable
}
```

### Mistake 3 — Mixing @Input() and signal inputs on the same property

A property can only be one or the other. Using both decorates the same slot
twice with conflicting metadata:

```typescript
// ❌ Both decorators on the same property — undefined behavior
@Component({ /* ... */ })
export class BadComponent {
  @Input() title = input('');  // the input() call already creates the signal
}

// ✅ Pick one — for new code, always pick input()
@Component({ /* ... */ })
export class GoodComponent {
  title = input('');
}
```

### Mistake 4 — Using transform for complex derivations instead of computed

`transform` runs synchronously on every value that comes in — it's for light
coercion, not business logic. Heavy computation in a transform blocks the
input pipeline and is harder to test:

```typescript
// ❌ Complex logic in transform — hard to test, runs for every bind
price = input(0, {
  transform: (v: number) => {
    const discounted = v > 100 ? v * 0.9 : v;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
      .format(discounted);
  }
});

// ✅ Coerce in transform, derive in computed — clean separation
rawPrice = input(0, { transform: numberAttribute });

displayPrice = computed(() => {
  const discounted = this.rawPrice() > 100 ? this.rawPrice() * 0.9 : this.rawPrice();
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
    .format(discounted);
});
```

## How this evolved

> - **Angular 2–17 (2016–2023):** `@Input()` was the only input mechanism.
>   Inputs were plain class properties with decorator metadata. Angular set
>   them by direct property assignment during change detection. Components
>   reacted to changes via `ngOnChanges` and the `SimpleChanges` map. Inputs
>   were `undefined` until after construction.
>
> - **Angular 16 (May 2023):** Signals launched in developer preview. The
>   reactive graph existed, but inputs were still `@Input()` — no native
>   signal integration for component communication.
>
> - **Angular 17.1 (Jan 2024):** `input()` and `input.required()` launched
>   as **developer preview**. Signal queries (`viewChild()`, `contentChild()`,
>   `viewChildren()`, `contentChildren()`) launched alongside them. Also
>   introduced: `model()` for two-way binding.
>
> - **Angular 17.3 (Mar 2024):** `model()` graduated out of initial
>   experimentation with improvements to the two-way binding protocol.
>
> - **Angular 19 (Nov 2024):** `withComponentInputBinding()` updated to
>   support signal inputs for route params — route parameters flow directly
>   into signal inputs without `ActivatedRoute` injection.
>
> - **Angular 20 (May 2025):** Signal inputs, signal queries, and `model()`
>   graduated to **stable**. `input()` is now the recommended pattern for all
>   new components and directives.
>
> - **Angular 22 (now):** `@Input()` remains fully supported but is considered
>   legacy for new code. `ng update` does not auto-migrate existing `@Input()`
>   decorators — migration is opt-in via
>   `ng generate @angular/core:signal-input-migration`. The Angular team's
>   guidance is clear: use `input()` for all new code, migrate `@Input()` as
>   part of modernization passes.

## See also

- [Signals](./signals.md) — the reactive primitive `input()` builds on;
  understanding `computed()` and `effect()` is prerequisite
- [Component Interactions](../components/component-interactions.md) — the
  parent-to-child, child-to-parent, and two-way data flow story end to end
- [Lifecycle](../components/lifecycle.md) — why `ngOnChanges` no longer fires
  for signal inputs, and what to use instead
- [Change Detection](../components/change-detection.md) — how signal input
  writes plug into the CD scheduler
- [toSignal & toObservable](./to-signal.md) — bridging signal inputs with
  existing Observable-based code
- [Official docs — Signal inputs](https://angular.dev/guide/components/inputs)
- [Migration schematic](https://angular.dev/reference/migrations/signal-inputs)

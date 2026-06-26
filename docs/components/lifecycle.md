---
roadmap_node: "lifecycle"
title: "Component Lifecycle"
file: "components/lifecycle.md"
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

# Component Lifecycle

> **Lead with this:** Angular calls a predictable sequence of methods on your
> component from creation to destruction — knowing *when* each fires is the
> difference between subtle bugs and bulletproof components.

## What it is

Every Angular component goes through a defined lifecycle: it is created, renders
its template, responds to input changes, renders its children, and is eventually
destroyed. Angular notifies your component at each of these moments by calling
**lifecycle hook methods** — ordinary class methods with special names that Angular
looks for and calls automatically.

You don't have to implement every hook. You only add the ones you actually need.
The most common ones in everyday Angular are `ngOnInit` (run setup logic once),
`ngOnChanges` (react to input changes), and `ngOnDestroy` (clean up subscriptions
and timers). The rest exist for specific, less frequent needs.

Think of lifecycle hooks as Angular tapping you on the shoulder at the right
moment: "the component just mounted — do you need to fetch data?", "an input
just changed — do you need to recalculate?", "the component is about to be
removed — do you need to clean up?"

## How it works under the hood

Angular's change detection engine is what drives the lifecycle. Each time change
detection runs — triggered by a user event, a timer, an HTTP response, or (in
zoneless mode) a signal notification — Angular walks the component tree and
evaluates each component's state. The lifecycle hooks are callbacks wired into
this walk at specific points.

The lifecycle splits into two distinct phases:

**Initialization phase** (fires once, in this order):
1. Constructor — the class is instantiated; DI runs; no inputs are set yet
2. `ngOnChanges` — first call, with all current input values
3. `ngOnInit` — inputs are now set; safe to read them
4. `ngDoCheck` — Angular's own change detection just ran
5. `ngAfterContentInit` — projected content (`<ng-content>`) is initialized
6. `ngAfterContentChecked` — projected content was checked
7. `ngAfterViewInit` — the component's own view and *all child views* are initialized
8. `ngAfterViewChecked` — the view was checked

**Update phase** (fires on every subsequent change detection cycle):
- `ngOnChanges` — if any `@Input()` reference changed
- `ngDoCheck` — always
- `ngAfterContentChecked` — always
- `ngAfterViewChecked` — always

**Destruction phase** (fires once):
9. `ngOnDestroy` — just before Angular removes the component from the DOM

The critical insight is the **constructor vs ngOnInit distinction**. Angular's
injector runs the constructor to build the class — but at that point, `@Input()`
bindings have not been applied yet. They are set between the constructor and
`ngOnInit`. This is why you almost never read inputs in the constructor; you read
them in `ngOnInit`.

A second critical insight: `ngAfterViewInit` fires only after the *entire view
subtree* is initialized — not just the component itself, but all its children
and their children. This is why `@ViewChild` queries are safe to read in
`ngAfterViewInit` but not in `ngOnInit`. The child element simply does not exist
in the DOM yet when `ngOnInit` fires.

> **Signal inputs change this picture.** If you use `input()` instead of
> `@Input()`, the signal is always available — including in the constructor. And
> `input()` signals do **not** trigger `ngOnChanges`. You react to them with
> `effect()` or `computed()` instead. See
> [Signal Inputs](../reactivity/signal-inputs.md) for the full picture.

## Basic usage

### Implementing lifecycle interfaces

Angular provides TypeScript interfaces for each hook (`OnInit`, `OnChanges`,
`OnDestroy`, etc.). You don't *have* to implement them — Angular will call the
method regardless — but implementing the interface makes your intent explicit
and lets the TypeScript compiler catch typos.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13)
import { Component, OnInit, OnDestroy, Input, NgModule } from '@angular/core';
import { Subscription } from 'rxjs';
import { DataService } from './data.service';
import { BrowserModule } from '@angular/platform-browser';

@Component({
  selector: 'app-user-card',
  template: `<p>{{ user?.name }}</p>`,
})
export class UserCardComponent implements OnInit, OnDestroy {
  @Input() userId!: string;

  user: User | null = null;
  private sub!: Subscription;

  constructor(private dataService: DataService) {}

  ngOnInit(): void {
    // Safe to read this.userId here — inputs are set
    this.sub = this.dataService.getUser(this.userId).subscribe(u => {
      this.user = u;
    });
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe(); // Clean up to prevent memory leaks
  }
}

@NgModule({
  declarations: [UserCardComponent],
  imports: [BrowserModule],
})
export class AppModule {}
```

```typescript
// Standalone approach (Angular 14+ — recommended)
import {
  Component, OnInit, OnDestroy, OnChanges,
  SimpleChanges, input, inject, DestroyRef
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DataService } from './data.service';

@Component({
  selector: 'app-user-card',
  standalone: true,
  template: `<p>{{ user?.name }}</p>`,
})
export class UserCardComponent implements OnInit {
  // Signal input — reactive, available immediately
  readonly userId = input.required<string>();

  user: User | null = null;

  private dataService = inject(DataService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.dataService.getUser(this.userId())
      .pipe(takeUntilDestroyed(this.destroyRef)) // Auto-unsubscribes on destroy
      .subscribe(u => { this.user = u; });
  }
  // No ngOnDestroy needed — takeUntilDestroyed handles cleanup
}
```

### Reacting to input changes with ngOnChanges

`ngOnChanges` fires before `ngOnInit` on the first run, then again whenever a
bound `@Input()` reference changes. It receives a `SimpleChanges` object mapping
input names to their previous and current values.

```typescript
import { Component, OnChanges, SimpleChanges, Input } from '@angular/core';

@Component({
  selector: 'app-chart',
  standalone: true,
  template: `<canvas #chartCanvas></canvas>`,
})
export class ChartComponent implements OnChanges {
  @Input() data: number[] = [];
  @Input() label = '';

  ngOnChanges(changes: SimpleChanges): void {
    // Check which specific input changed
    if (changes['data'] && !changes['data'].firstChange) {
      // Don't re-render on the first change — ngAfterViewInit hasn't fired yet
      this.renderChart();
    }
  }

  private renderChart(): void { /* ... */ }
}
```

> **Important:** `ngOnChanges` only fires for `@Input()` decorated properties.
> It does **not** fire for `input()` signal properties. If you migrate to signal
> inputs, replace `ngOnChanges` logic with a `effect(() => { ... this.myInput() ... })`.

### Safe DOM access in ngAfterViewInit

```typescript
import {
  Component, AfterViewInit,
  ViewChild, ElementRef, inject
} from '@angular/core';

@Component({
  selector: 'app-canvas',
  standalone: true,
  template: `<canvas #myCanvas width="400" height="300"></canvas>`,
})
export class CanvasComponent implements AfterViewInit {
  // ViewChild is null until ngAfterViewInit fires
  @ViewChild('myCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  ngAfterViewInit(): void {
    // Safe — the DOM element exists now
    const ctx = this.canvasRef.nativeElement.getContext('2d')!;
    ctx.fillStyle = 'steelblue';
    ctx.fillRect(0, 0, 400, 300);
  }
}
```

### Cleanup with DestroyRef (modern approach)

Angular 16+ gives you `DestroyRef` — an injectable that lets you register cleanup
callbacks without implementing `ngOnDestroy`. This works anywhere in the injection
context, including inside services and helper functions.

```typescript
import { Component, OnInit, inject, DestroyRef } from '@angular/core';

@Component({
  selector: 'app-timer',
  standalone: true,
  template: `<p>Elapsed: {{ elapsed }}s</p>`,
})
export class TimerComponent implements OnInit {
  elapsed = 0;

  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    const intervalId = setInterval(() => this.elapsed++, 1000);

    // Register cleanup — fires when the component is destroyed
    this.destroyRef.onDestroy(() => clearInterval(intervalId));
  }
}
```

## Real-world patterns

### Pattern 1 — Lazy data fetch on navigation

The most common `ngOnInit` pattern: read a route parameter and fetch data. The
component is re-created each time the user navigates to a new user profile, so
`ngOnInit` is the right place — not the constructor.

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserService } from './user.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { switchMap } from 'rxjs';

@Component({
  selector: 'app-profile',
  standalone: true,
  template: `
    @if (user) {
      <h1>{{ user.name }}</h1>
      <p>{{ user.bio }}</p>
    } @else {
      <p>Loading…</p>
    }
  `,
})
export class ProfileComponent implements OnInit {
  user: User | null = null;

  private route = inject(ActivatedRoute);
  private userService = inject(UserService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => this.userService.getUser(params.get('id')!)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(user => { this.user = user; });
  }
}
```

### Pattern 2 — Third-party library initialization in ngAfterViewInit

When wrapping a library that needs a real DOM element (a chart library, a map,
a rich text editor), `ngAfterViewInit` is the correct hook — the element exists
in the DOM and has its final dimensions.

```typescript
import {
  Component, AfterViewInit, OnDestroy,
  ViewChild, ElementRef, inject, NgZone
} from '@angular/core';
import * as L from 'leaflet';

@Component({
  selector: 'app-map',
  standalone: true,
  template: `<div #mapContainer style="height: 400px"></div>`,
})
export class MapComponent implements AfterViewInit, OnDestroy {
  @ViewChild('mapContainer') container!: ElementRef<HTMLDivElement>;
  private map!: L.Map;
  private zone = inject(NgZone);

  ngAfterViewInit(): void {
    // Run outside Angular's zone — Leaflet fires many internal events
    // that don't need to trigger Angular change detection
    this.zone.runOutsideAngular(() => {
      this.map = L.map(this.container.nativeElement).setView([51.5, -0.1], 13);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(this.map);
    });
  }

  ngOnDestroy(): void {
    this.map?.remove(); // Leaflet cleanup
  }
}
```

## Modern lifecycle APIs (Angular 16+)

These newer APIs cover two gaps the classic hooks leave open: running logic
after *every* render (not just the first), and reacting to signal input changes
without `ngOnChanges`. They don't replace the classic hooks — they complement them.

### afterRender and afterNextRender

`ngAfterViewInit` fires once after the first render. `afterRender` fires after
*every* render — useful for reading DOM measurements that change as the component
updates. `afterNextRender` is a one-shot version: it fires exactly once after
the very next render, then stops.

```typescript
import {
  Component, signal, inject,
  afterRender, afterNextRender, ElementRef
} from '@angular/core';

@Component({
  selector: 'app-responsive-box',
  standalone: true,
  template: `
    <div>Content here</div>
    <p>Measured width: {{ width() }}px</p>
  `,
})
export class ResponsiveBoxComponent {
  width = signal(0);
  private el = inject(ElementRef);

  constructor() {
    // Runs after every render — reads DOM, updates signal
    afterRender(() => {
      this.width.set(this.el.nativeElement.offsetWidth);
    });

    // Runs once after the very next render, then never again
    afterNextRender(() => {
      console.log('First paint done, width:', this.el.nativeElement.offsetWidth);
    });
  }
}
```

> **When to use which:**
> `ngAfterViewInit` — one-time setup (chart, map, third-party widget).
> `afterRender` — read/write DOM on every render cycle (resize, scroll measurements).
> `afterNextRender` — one-time deferred setup that must happen after the next paint,
> not the current one (e.g. measuring an element before animating it).

### afterRenderEffect (Angular 18+)

`afterRenderEffect` is `afterRender` with signal awareness built in. It tracks
which signals you read inside it and only re-runs when those signals change
*and* a render has completed — skipping unnecessary runs when unrelated state changes.

```typescript
import { Component, signal, input, afterRenderEffect } from '@angular/core';

@Component({
  selector: 'app-highlight',
  standalone: true,
  template: `<p>{{ text() }}</p>`,
})
export class HighlightComponent {
  text = input('');
  highlightColor = signal('yellow');

  constructor() {
    // Only re-runs when highlightColor changes AND after a render
    // — not on every render cycle regardless of whether color changed
    afterRenderEffect(() => {
      const el = document.querySelector('p');
      if (el) el.style.backgroundColor = this.highlightColor();
    });
  }
}
```

### Signal inputs + effect() replacing ngOnChanges

`input()` signals don't trigger `ngOnChanges`. The replacement is `effect()` —
it re-runs automatically whenever any signal it reads changes.

```typescript
// ❌ Old pattern — @Input() + ngOnChanges (still works, just not for input() signals)
import { Component, OnChanges, SimpleChanges, Input } from '@angular/core';

export class OldChartComponent implements OnChanges {
  @Input() data: number[] = [];

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && !changes['data'].firstChange) {
      this.renderChart(changes['data'].currentValue);
    }
  }
  private renderChart(data: number[]): void { /* ... */ }
}
```

```typescript
// ✅ Modern pattern — input() signal + effect()
import { Component, input, effect } from '@angular/core';

export class NewChartComponent {
  data = input<number[]>([]);

  constructor() {
    effect(() => {
      // Re-runs automatically whenever this.data() changes
      // No firstChange check needed — effect() skips the first run
      // only if you set { allowSignalWrites: true } for write-back scenarios
      this.renderChart(this.data());
    });
  }
  private renderChart(data: number[]): void { /* ... */ }
}
```

### Zoneless components (Angular 18+)

In zoneless mode you remove Zone.js entirely. Angular updates only when signals
notify it — no more event monkey-patching. Lifecycle hooks still fire; the trigger
mechanism changes, not the hooks themselves.

Enable it once at the app level:

```typescript
// main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { provideZonelessChangeDetection } from '@angular/core';
import { AppComponent } from './app.component';

bootstrapApplication(AppComponent, {
  providers: [
    provideZonelessChangeDetection(), // Angular 18+ (stable in Angular 20)
  ],
});
```

A zoneless component looks identical to any other standalone component.
The only requirement: use signals for all state so Angular knows when to re-render.

```typescript
import { Component, signal, inject, OnInit } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { UserService } from './user.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  template: `
    @if (user()) {
      <h1>{{ user()!.name }}</h1>
      <p>{{ user()!.bio }}</p>
    } @else {
      <p>Loading…</p>
    }
  `,
})
export class ProfileComponent {
  private userService = inject(UserService);

  // toSignal converts Observable → Signal; Angular re-renders when it emits
  // No NgZone, no markForCheck(), no manual CD needed
  user = toSignal(this.userService.getCurrentUser(), { initialValue: null });

  // ngOnInit still works in zoneless — lifecycle hooks are unchanged
  ngOnInit(): void {
    console.log('Component initialized');
  }
}
```

## Common mistakes

### Mistake 1 — Reading inputs in the constructor

```typescript
// ❌ Wrong — @Input() values are not set yet in the constructor
export class WrongComponent {
  @Input() title = '';

  constructor() {
    console.log(this.title); // Always logs '' — inputs aren't bound yet
    this.doSetup(this.title); // Bug: receives empty string every time
  }
}

// ✅ Right — read inputs in ngOnInit
export class CorrectComponent implements OnInit {
  @Input() title = '';

  ngOnInit(): void {
    console.log(this.title); // Correct value
    this.doSetup(this.title);
  }
}
```

### Mistake 2 — Accessing ViewChild in ngOnInit

```typescript
// ❌ Wrong — child view not initialized yet
export class WrongComponent implements OnInit {
  @ViewChild('myInput') inputRef!: ElementRef;

  ngOnInit(): void {
    this.inputRef.nativeElement.focus(); // TypeError: cannot read nativeElement of undefined
  }
}

// ✅ Right — child view exists in ngAfterViewInit
export class CorrectComponent implements AfterViewInit {
  @ViewChild('myInput') inputRef!: ElementRef;

  ngAfterViewInit(): void {
    this.inputRef.nativeElement.focus(); // Works — element is in the DOM
  }
}
```

### Mistake 3 — Forgetting to unsubscribe (without takeUntilDestroyed)

```typescript
// ❌ Wrong — interval fires forever, even after the component is destroyed
export class LeakyComponent implements OnInit {
  ngOnInit(): void {
    interval(1000).subscribe(() => this.refresh()); // Memory leak
  }
}

// ✅ Right — use takeUntilDestroyed to auto-clean up
export class CleanComponent implements OnInit {
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.refresh()); // Auto-unsubscribes on destroy
  }
}
```

### Mistake 4 — Triggering change detection in ngAfterViewChecked

`ngAfterViewChecked` fires on every change detection cycle. If you update state
inside it, you trigger another cycle — infinite loop, `ExpressionChangedAfterItHasBeenCheckedError` in dev mode.

```typescript
// ❌ Wrong — updates state during the check, causing infinite CD loop
export class WrongComponent implements AfterViewChecked {
  title = '';

  ngAfterViewChecked(): void {
    this.title = 'updated'; // Triggers another CD run → infinite loop
  }
}

// ✅ Right — defer state changes with a microtask if you truly need AfterViewChecked
export class CorrectComponent implements AfterViewChecked {
  title = '';

  ngAfterViewChecked(): void {
    Promise.resolve().then(() => { this.title = 'updated'; });
  }
}
```

## How this evolved

> - **Angular 2 (2016):** All hooks introduced: `ngOnChanges`, `ngOnInit`,
>   `ngDoCheck`, `ngAfterContentInit`, `ngAfterContentChecked`, `ngAfterViewInit`,
>   `ngAfterViewChecked`, `ngOnDestroy`. This API has been stable ever since.
>
> - **Angular 14 (2022):** Standalone components introduced. Lifecycle hooks
>   unchanged — they work identically in standalone and NgModule components.
>
> - **Angular 16 (2023):** `DestroyRef` and `takeUntilDestroyed` introduced,
>   giving a cleaner alternative to `ngOnDestroy` for subscription cleanup.
>   `afterRender` and `afterNextRender` introduced as alternatives to
>   `ngAfterViewInit` for render-aware side effects.
>
> - **Angular 17.1 (2024):** Signal inputs (`input()`) landed stable. They do
>   **not** trigger `ngOnChanges` — a behavioral shift that catches developers
>   migrating from `@Input()`. Use `effect()` to react to signal input changes.
>
> - **Angular 18 (2024):** `afterRenderEffect` introduced — an effect that runs
>   after rendering, replacing manual `afterRender` + cleanup patterns.
>
> - **Angular 22 (now):** Zoneless is the recommended default for new projects.
>   Lifecycle hooks still fire in zoneless — but they are now driven by the
>   signal graph and explicit `markForCheck()` calls rather than Zone.js monkey-
>   patching. The hook names and interfaces are unchanged.

## See also

- [Change Detection](./change-detection.md) — how the CD engine drives hook timing
- [Signal Inputs](../reactivity/signal-inputs.md) — why `input()` doesn't trigger `ngOnChanges`
- [Component Interactions](./component-interactions.md) — `@Input`, `@Output`, and the parent–child data flow
- [Templates Architecture](./templates/templates-architecture.md) — `@ViewChild`, `@ContentChild` query timing
- [Official docs — Lifecycle hooks](https://angular.dev/guide/components/lifecycle)

---
recipe_id: "preloading-strategy"
title: "Hover- and Viewport-Triggered Route Preloading"
file: "recipes/routing/preloading-strategy.md"
primary_concept: "routing/routing"
related_concepts: ["routing/lazy-loading", "routing/router-configuration", "dependency-injection/dependency-injection"]
demo_repo: "https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/preloading-strategy"
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Hover- and Viewport-Triggered Route Preloading

> **What you'll build:** a multi-trigger preloading system. Lazy-loaded
> routes start downloading when (a) they're explicitly marked eager,
> (b) their link enters the viewport, or (c) the user hovers over the link
> — whichever happens first. All gated by a network-quality check that
> skips preloading on slow connections or when Data Saver is on.
>
> **Concepts you'll touch:** [Routing](../../routing/routing.md), [Lazy Loading](../../routing/lazy-loading.md), [Router Configuration](../../routing/router-configuration.md), [Dependency Injection](../../dependency-injection/dependency-injection.md)
>
> **Time:** ~20 minutes to read; ~1 hour to wire up and test against your routes.

---

## The scenario

Lazy loading is one of those features that's great until your users feel
it. Routes are split into chunks, the initial bundle stays small, and the
app loads fast. Then a user clicks "Admin Dashboard," and there's a
half-second pause while the chunk downloads. Then a spinner. Then the
route renders.

The UX gap: **lazy loading optimizes initial load at the cost of
click-then-wait.** Preloading bridges that gap by downloading lazy chunks
**after** the initial page is ready, **before** the user actually clicks.

Angular ships two built-in preloading strategies — `NoPreloading` (the
default, don't preload anything) and `PreloadAllModules` (after initial
load, eagerly fetch everything). Both are blunt instruments. `NoPreloading`
gives you the click-wait. `PreloadAllModules` wastes bandwidth on routes
users will never visit, and is rude on metered connections.

A custom `PreloadingStrategy` lets you preload **smartly** — only the
routes the user is likely to visit, and only when network conditions
allow it.

## The preloading strategy landscape

A `PreloadingStrategy` is a class with one method:

```typescript
preload(route: Route, load: () => Observable<any>): Observable<any>;
```

The router calls `preload()` for **every lazy route** after the initial
navigation finishes. The strategy decides whether to call `load()` (which
fetches and registers the chunk) or to return `of(null)` (which means
"skip"). The returned observable's completion signals the router that
the strategy is done with this route.

The built-in `NoPreloading` always returns `of(null)`. The built-in
`PreloadAllModules` always returns `load()`. Anything else is a custom
strategy.

The pattern we'll build is more interesting: **defer the decision.**
Instead of calling `load()` immediately during `preload()`, **stash the
`load` function in a registry**, then trigger it later — when a directive
on the page tells us "this route is about to be needed."

---

## The architecture

Three files cooperate. Each has a single responsibility:

```
preloading-strategy/
└── on-hover-strategy/
    ├── preload-on-hover-strategy.service.ts   # PreloadingStrategy implementation
    ├── preload-on-hover.service.ts            # Registry + network-quality gate
    └── preload-on-hover.directive.ts          # Triggers: viewport + hover
```

```
                       Router calls preload() per lazy route
                                         │
                                         ▼
              ┌─────────────────────────────────────────────┐
              │  PreloadOnHoverStrategy                     │
              │  - if route.data.preload === true: load now │
              │  - else: register(path, loadFn)             │
              │  - return of(null) so the router moves on   │
              └─────────────────────────────────────────────┘
                                         │ registers
                                         ▼
              ┌─────────────────────────────────────────────┐
              │  PreloadOnHoverService (registry)           │
              │  - Map<path, loadFn>                        │
              │  - shouldPreload() — network gate           │
              │  - triggerPreload(path) — runs loadFn       │
              └─────────────────────────────────────────────┘
                                         ▲ triggers
                                         │
              ┌─────────────────────────────────────────────┐
              │  PreloadOnHoverDirective                    │
              │  - IntersectionObserver: link visible       │
              │  - host (mouseenter): hover                 │
              │  - executePreload() → service.triggerPreload│
              └─────────────────────────────────────────────┘
```

The split matters. The **strategy** speaks to the router. The **service**
owns the registry and the network policy. The **directive** owns the user
interactions. Each is independently testable, and you can swap any of
them — replace the directive with a focus-based trigger, swap the service
for one that hits an analytics endpoint, write a stricter strategy that
requires both `data.preload` flag and a hover before loading. Loose
coupling, clear seams.

---

## Step 1 — the custom `PreloadingStrategy`

The strategy bridges the router to the registry service. It runs once
per lazy route, decides whether to load immediately or defer, and either
way returns an observable so the router knows the strategy is finished.

```typescript
// File: preload-on-hover-strategy.service.ts
import { Injectable, inject } from '@angular/core';
import { PreloadingStrategy, Route } from '@angular/router';
import { Observable, of } from 'rxjs';
import { PreloadOnHoverService } from './preload-on-hover.service';

@Injectable({ providedIn: 'root' })
export class PreloadOnHoverStrategy implements PreloadingStrategy {
  private readonly preloadService = inject(PreloadOnHoverService);

  preload(route: Route, load: () => Observable<unknown>): Observable<unknown> {
    // If the route is explicitly marked eager, load it now.
    if (route.data?.['preload'] === true) {
      return load();
    }

    // Otherwise, stash the load function in the registry and wait until
    // the directive signals us to trigger it (hover or viewport).
    if (route.path) {
      this.preloadService.register(route.path, load);
    }

    // Tell the router: "Don't auto-load this — I'll handle it later."
    return of(null);
  }
}
```

Two things worth absorbing:

- **The `route.data['preload']` flag is the escape hatch.** Some routes
  you want eager — your most-visited dashboard, the route immediately
  downstream of login. Set `data: { preload: true }` in those route
  definitions and the strategy honors it instantly, bypassing the
  hover-trigger path entirely.

- **Returning `of(null)` is how a strategy says "skip."** The router uses
  the observable's completion (not its emitted value) to know the
  strategy is done with this route. If you return the actual `load()`
  observable, the chunk downloads now; if you return `of(null)`, the
  router moves on and never asks again. The "defer" trick is that we
  return `of(null)` but keep a reference to `load` in the registry.

---

## Step 2 — the registry service with network gating

The service holds two things: a map of `path → loadFn`, and a policy
about when it's acceptable to actually call those load functions. The
policy reads from the [Network Information API](https://developer.mozilla.org/en-US/docs/Web/API/Network_Information_API)
(`navigator.connection`), which exposes the user's effective bandwidth
class and their Data Saver preference.

```typescript
// File: preload-on-hover.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class PreloadOnHoverService {
  private readonly registry = new Map<string, () => Observable<unknown>>();

  register(path: string, loadFn: () => Observable<unknown>) {
    if (!this.registry.has(path)) {
      this.registry.set(path, loadFn);
    }
  }

  /**
   * Check whether the network is good enough to preload.
   * Returns false on slow connections (2g/slow-3g) or when the user has
   * enabled Data Saver — both signals that bandwidth is precious.
   */
  private shouldPreload(): boolean {
    // The Network Information API isn't in the standard DOM types yet,
    // so we cast to access it. Falls back gracefully if unavailable.
    const connection =
      (navigator as any).connection ??
      (navigator as any).mozConnection ??
      (navigator as any).webkitConnection;

    if (connection) {
      // 1. Data Saver is on — respect the user's bandwidth preference.
      if (connection.saveData) {
        return false;
      }

      // 2. Slow effective connection — don't make it worse.
      const slowConnections = ['2g', '3g'];
      if (slowConnections.includes(connection.effectiveType)) {
        return false;
      }
    }

    // No connection info, or fast connection without Data Saver — go ahead.
    return true;
  }

  triggerPreload(path: string): void {
    // Network gate first — never call loadFn if conditions are bad.
    if (!this.shouldPreload()) {
      console.log(
        `Skipping preload of "${path}" — network is slow or Data Saver is enabled.`,
      );
      return;
    }

    const loadFn = this.registry.get(path);
    if (loadFn) {
      loadFn().subscribe({
        next: () => {
          console.log(`Preloaded code for "${path}".`);
          // One-shot: once loaded, remove from registry so subsequent
          // hover events don't re-fire the network call.
          this.registry.delete(path);
        },
        error: (err) => {
          console.warn(`Preload failed for "${path}":`, err);
          // Leave the entry in the registry so a retry on next trigger
          // can succeed when the network recovers.
        },
      });
    }
  }
}
```

A few production-relevant points:

- **`register()` is idempotent.** The strategy may run multiple times
  per route if the router re-evaluates lazy boundaries. We guard against
  duplicate registration with `if (!this.registry.has(path))` so we
  never replace a registered function unnecessarily.

- **`registry.delete(path)` after successful load is critical.** Without
  it, every subsequent hover re-runs `loadFn`. The webpack runtime is
  smart enough to recognize the chunk is already loaded and return
  immediately, but we save the work entirely by removing the entry.

- **The error branch leaves the entry in place.** If preload failed
  (bad network blip, CDN hiccup), we want the next trigger to retry.
  This is the opposite of the success path. Subtle but important.

- **`(navigator as any).connection`** — the Network Information API
  is widely supported in Chromium browsers (~75%+ of users) but absent
  in Safari and Firefox. The fallback chain checks `mozConnection`
  and `webkitConnection` for legacy reasons, but in 2026 those are
  vestigial — `connection` is what you'll actually find. The
  `as any` cast is necessary because TypeScript's `lib.dom.d.ts`
  doesn't include the API. When the property is absent, `shouldPreload()`
  returns `true` — we assume good network when we have no info, since
  the user has no way to signal otherwise.

---

## Step 3 — the directive: viewport + hover triggers

The directive attaches to anchor tags that already have `[routerLink]`.
Its job: detect when the user is **about to** click on the link — either
because they're hovering over it, or because the link just scrolled into
their viewport — and call `triggerPreload()` on the service.

```typescript
// File: preload-on-hover.directive.ts
import {
  Directive,
  DestroyRef,
  ElementRef,
  Input,
  inject,
} from '@angular/core';
import { PreloadOnHoverService } from './preload-on-hover.service';

@Directive({
  selector: '[routerLink][preloadOnHover]',
  // host {} object — the v22 idiom replacing @HostListener
  host: {
    '(mouseenter)': 'executePreload()',
  },
})
export class PreloadOnHoverDirective {
  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly preloadService = inject(PreloadOnHoverService);

  // Shared with the RouterLink directive on the same element — both
  // directives see the same input value. Decorator @Input here matches
  // RouterLink's current interface; signal-input version shown below.
  @Input() routerLink!: string | unknown[];

  constructor() {
    // The constructor runs in injection context, so inject(DestroyRef)
    // works here without ngOnInit / ngOnDestroy ceremony.
    if (!('IntersectionObserver' in window)) {
      // Old browsers: no viewport trigger, but mouseenter still works.
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          // Fire as soon as the link is even slightly visible.
          if (entry.isIntersecting) {
            this.executePreload();
            // One-shot: stop observing this element to save CPU on scroll.
            observer.unobserve(this.el.nativeElement);
          }
        }
      },
      {
        // Preload when the element is within 50px of the viewport —
        // gets ahead of fast scroll behavior.
        rootMargin: '50px',
      },
    );

    observer.observe(this.el.nativeElement);

    // Clean up the observer when the directive is destroyed.
    // No ngOnDestroy hook needed — DestroyRef handles the lifecycle.
    inject(DestroyRef).onDestroy(() => observer.disconnect());
  }

  /**
   * Extract the route path from the routerLink input and ask the service
   * to preload it. Handles both string ('/admin') and array (['/admin'])
   * forms of routerLink.
   */
  protected executePreload(): void {
    const path = Array.isArray(this.routerLink)
      ? (this.routerLink[0] as string)
      : this.routerLink;

    if (!path) return;

    // Router config paths don't include the leading slash —
    // '/admin' on a link maps to path: 'admin' on a Route.
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    this.preloadService.triggerPreload(cleanPath);
  }
}
```

**v22 changes from the original demo code:**

| Demo (works fine) | v22-idiomatic |
| --- | --- |
| `@HostListener('mouseenter')` on a method | `host: { '(mouseenter)': 'executePreload()' }` on the decorator |
| `implements OnInit, OnDestroy` + `ngOnInit` / `ngOnDestroy` | Logic in `constructor`, cleanup via `inject(DestroyRef).onDestroy()` |
| `inject(ElementRef)` | `inject<ElementRef<HTMLElement>>(ElementRef)` for the typed element |

Both styles produce identical behavior. The v22 form is shorter and one
less interface to implement. The locked convention says use `host: {}`
over `@HostListener`, and `inject(DestroyRef).onDestroy()` over manual
`ngOnDestroy`.

### Signal-input variant

If you're standardizing on signal inputs across the codebase, the
directive can use `input.required()` instead of `@Input`:

```typescript
import { input } from '@angular/core';

@Directive({
  selector: '[routerLink][preloadOnHover]',
  host: { '(mouseenter)': 'executePreload()' },
})
export class PreloadOnHoverDirective {
  readonly routerLink = input.required<string | unknown[]>();
  // ...

  protected executePreload(): void {
    const link = this.routerLink();  // signal read
    const path = Array.isArray(link) ? (link[0] as string) : link;
    if (!path) return;
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    this.preloadService.triggerPreload(cleanPath);
  }
}
```

`RouterLink` itself still uses decorator inputs internally in v22, so the
two will coexist on the element. Both directives receive the same input
value.

---

## Step 4 — wiring it up with `provideRouter`

The router needs to be told which strategy to use. In v22, this is one
line in `app.config.ts`:

```typescript
// File: app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideRouter, withPreloading } from '@angular/router';
import { routes } from './app.routes';
import { PreloadOnHoverStrategy } from './on-hover-strategy/preload-on-hover-strategy.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(
      routes,
      withPreloading(PreloadOnHoverStrategy),
    ),
  ],
};
```

`withPreloading()` is a feature function for `provideRouter()` — see
[Router Configuration](../../routing/router-configuration.md) for the
full set. It registers your strategy as the one the router will call
`preload()` on after every navigation.

### Route definitions — `data.preload` for eager hints

In your routes, mark the high-priority ones as `data: { preload: true }`:

```typescript
// File: app.routes.ts
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'dashboard',
    loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent),
    data: { preload: true },  // ← eager: load right after initial nav
  },
  {
    path: 'admin',
    loadComponent: () => import('./admin/admin.component').then(m => m.AdminComponent),
    // No data.preload — wait for hover/viewport trigger.
  },
  {
    path: 'reports',
    loadComponent: () => import('./reports/reports.component').then(m => m.ReportsComponent),
  },
];
```

---

## Step 5 — using it in templates

Add `preloadOnHover` next to `routerLink` on any link that should benefit
from the directive. Don't add it everywhere — only where preloading is
worth the bandwidth.

```html
<!-- Eager-loaded (data.preload: true) — directive is harmless here -->
<a routerLink="/dashboard">Dashboard</a>

<!-- Hover/viewport-triggered preloading -->
<a routerLink="/admin" preloadOnHover>Admin</a>
<a routerLink="/reports" preloadOnHover>Reports</a>

<!-- Array-form routerLink also works -->
<a [routerLink]="['/admin']" preloadOnHover>Admin</a>
```

That's the whole user-facing surface. Each `preloadOnHover` link will
start downloading its target chunk **when** it scrolls into view or
**when** the user hovers — whichever happens first — provided the
network gate allows it.

---

## Variations

### Focus-triggered preloading for keyboard users

The current directive triggers on mouseenter and viewport visibility.
Neither helps keyboard users who navigate via Tab. Add a `focus` handler:

```typescript
host: {
  '(mouseenter)': 'executePreload()',
  '(focus)': 'executePreload()',
},
```

Now Tab-focusing the link also triggers preloading. Useful for
accessibility-first apps where keyboard navigation is the primary mode.

### Slower throttling for low-priority routes

If you're on the edge of "eager but not too eager," debounce the trigger.
Wait, say, 200ms of hover before deciding the user really means to
preload (vs. mousing past on the way somewhere else):

```typescript
import { fromEvent, debounceTime } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

constructor() {
  fromEvent(this.el.nativeElement, 'mouseenter').pipe(
    debounceTime(200),  // wait 200ms before triggering
    takeUntilDestroyed(),
  ).subscribe(() => this.executePreload());

  // ... IntersectionObserver setup
}
```

Trade-off: slower to start preloading, but fewer wasted requests on
"mousing past" hovers.

### Multiple strategies on different route subtrees

A single `withPreloading()` call registers one global strategy, but you
can route around this by **composing** strategies. Make the global
strategy a dispatcher that delegates to others based on `route.data`:

```typescript
@Injectable({ providedIn: 'root' })
export class CompositeStrategy implements PreloadingStrategy {
  private readonly hoverStrategy = inject(PreloadOnHoverStrategy);
  private readonly allModules = inject(PreloadAllModules);

  preload(route: Route, load: () => Observable<unknown>): Observable<unknown> {
    if (route.data?.['preloadAll'] === true) {
      return this.allModules.preload(route, load);
    }
    return this.hoverStrategy.preload(route, load);
  }
}
```

Then `withPreloading(CompositeStrategy)`. Routes opt into all-modules
preloading via `data: { preloadAll: true }`; everything else goes through
the hover strategy.

---

## Trade-offs and when NOT to use this

**Use this pattern when:**

- Your app has 10+ lazy routes and not all are equally likely to be visited
- Initial page load is fast enough that you have idle bandwidth to spare
- You ship to a global audience including mobile networks where Data
  Saver matters
- The first-time-to-route metric matters more than absolute initial
  bundle size

**Reach for something simpler when:**

- **Your app has 1–3 lazy routes.** Just preload all of them with
  `withPreloading(PreloadAllModules)` after initial load. The complexity
  isn't worth it.
- **Your audience is on broadband by default** (internal tools, B2B
  desktop apps). Skip the network gate, use `PreloadAllModules`.
- **Routes are deeply contextual.** A flow where the user must complete
  step 1 before they can even see step 2's link — preload at the end of
  step 1 imperatively (`router.preloadAllModules()` isn't exposed
  directly; use the strategy by triggering manually via the service).
- **You have a route-level data dependency that's expensive.** If route
  R also needs to load a 5MB JSON dataset on mount, preloading the code
  doesn't help much — the bottleneck is the data, not the chunk.

**Common pitfalls:**

- **Forgetting `data.preload` and the directive — neither one fires.**
  If you write `preloadOnHover` on links but the route has no `path`
  (an empty-path child route), the strategy can't register it. Always
  add `data: { preload: true }` as the fallback for empty-path routes
  you actually want preloaded.
- **Registry leaks if `loadFn` errors silently.** The `next` handler
  deletes from the registry; the `error` handler leaves it. If your
  HTTP/chunk-loading errors aren't surfacing through the observable
  (some bundlers swallow them), the registry can grow unboundedly.
  Verify error handling end-to-end.
- **The Network Information API can lie.** `connection.effectiveType`
  is a coarse classifier — a user on 4G in a basement might be slower
  than a user on 3G in the open. The gate is a heuristic, not a
  guarantee. Accept that some preloads will land on slow networks
  anyway.
- **Eager preload + hover preload race.** A route with `data.preload:
  true` AND `preloadOnHover` on its link: the strategy loads it
  immediately, the directive's later trigger calls `triggerPreload()`
  which finds nothing in the registry. No bug, but no useful behavior
  either — just remove the directive from eager-route links.

---

## See also

- [Routing](../../routing/routing.md) — `provideRouter()` and feature functions
- [Router Configuration](../../routing/router-configuration.md) — the full `withX()` feature catalogue including `withPreloading`
- [Lazy Loading](../../routing/lazy-loading.md) — `loadComponent` and `loadChildren` patterns
- [Dependency Injection](../../dependency-injection/dependency-injection.md) — `inject()`, `DestroyRef`, service registries
- [`takeUntilDestroyed`](../reactivity/take-until-destroyed.md) — the v22 cleanup primitive used in the debounced-hover variant

## References

- [`PreloadingStrategy` API (angular.dev)](https://angular.dev/api/router/PreloadingStrategy)
- [`withPreloading` API (angular.dev)](https://angular.dev/api/router/withPreloading)
- [Network Information API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Network_Information_API)
- [IntersectionObserver API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [Web.dev — Route-based code splitting in Angular](https://web.dev/route-level-code-splitting-in-angular/)

## Demo source

Adapted from [`AngularDemos/features/preloading-strategy/on-hover-strategy`](https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/preloading-strategy/on-hover-strategy).
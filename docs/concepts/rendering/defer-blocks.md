---
roadmap_node: "defer-blocks"
title: "@defer Blocks"
file: "rendering/defer-blocks.md"
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
> Written fresh for Angular v17+, baseline v22.

# @defer Blocks

> **Lead with this:** `@defer` lets you split a template into a part that loads
> immediately and parts that load lazily — the browser downloads those lazy parts
> only when a trigger fires, such as the user scrolling them into view.

## What it is

Route-level lazy loading (`loadComponent`, `loadChildren`) defers entire pages
until navigation. `@defer` goes further — it defers **parts of a page** within
a single template. You wrap any block of template in `@defer`, and Angular
automatically code-splits its dependencies (components, directives, pipes) into
a separate bundle that the browser won't download until the trigger fires.

The trigger can be a viewport intersection, a user interaction, a hover, a
timer, an idle moment, or a custom condition. Until then, Angular shows an
optional `@placeholder`. While loading, it shows an optional `@loading` block.
If the download fails, it shows an optional `@error` block.

This is purely declarative — no dynamic imports, no `IntersectionObserver`
boilerplate, no loading state management. The Angular compiler and runtime
handle all of it.

## How it works under the hood

**At compile time**, Angular's compiler scans every `@defer` block and collects
its direct dependencies — the components, directives, and pipes referenced
inside it. It then emits those dependencies into a **separate JavaScript chunk**,
completely removed from the main bundle. The main bundle contains only a small
stub that knows how to load the chunk on demand.

**At runtime**, Angular renders the `@placeholder` block immediately (it is
always eagerly loaded — never deferred). It then sets up the trigger you
specified. For `on viewport`, it creates an `IntersectionObserver` on the
placeholder element. For `on idle`, it calls `requestIdleCallback`. For `on
interaction` or `on hover`, it attaches event listeners to the placeholder.

When the trigger fires, Angular calls a dynamic `import()` for the lazy chunk.
During that network request, it swaps the placeholder for the `@loading` block
(if you defined one). When the import resolves and the dependencies are
registered, Angular renders the actual deferred content and discards the
loading block.

The two browser APIs Angular relies on for triggers are:

**[`IntersectionObserver`](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)**
(used by `on viewport`) — a browser API that fires a callback when a target
element enters or exits the visible viewport. Angular attaches an observer to
the placeholder element; when it becomes visible, the trigger fires. No scroll
event listeners or `getBoundingClientRect()` polling needed — the browser
handles the detection natively.

**[`requestIdleCallback`](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestIdleCallback)**
(used by `on idle`) — a browser API that schedules a callback to run during
the browser's next idle period, after the current frame has been painted and no
input events are pending. Angular uses it to load deferred content without
competing with user interaction or critical rendering work.

The other triggers map to simpler browser mechanisms: `on interaction` listens
for `click` and `keydown` events on the placeholder; `on hover` listens for
`mouseenter` and `focusin`; `on timer` uses `setTimeout`.

The `@placeholder`, `@loading`, and `@error` blocks are always part of the
**main bundle** — they are rendered synchronously and must not contain deferred
dependencies. Only the content inside the bare `@defer { ... }` block is split.

**Prefetching** is a separate mechanism: `prefetch on idle` (or any other
prefetch trigger) downloads the chunk eagerly into the browser cache while the
placeholder is still showing — so when the real trigger eventually fires, the
content appears instantly.

## Basic usage

### The four blocks

```html
@defer {
  <!-- Content here is lazy — its dependencies are in a separate bundle -->
  <app-heavy-chart [data]="analyticsData()" />
}
@placeholder {
  <!-- Shown immediately, before the trigger fires — always in main bundle -->
  <div class="chart-skeleton" aria-hidden="true"></div>
}
@loading {
  <!-- Shown after trigger fires, while bundle downloads -->
  <app-spinner />
}
@error {
  <!-- Shown if the bundle download or component initialization fails -->
  <p>Chart could not be loaded. <button (click)="retry()">Retry</button></p>
}
```

All four blocks are optional. The minimum valid `@defer` is just:

```html
@defer {
  <app-comments [postId]="postId()" />
}
```

### Triggers

All trigger options with examples:

```html
<!-- on idle: loads when the browser reports it has free time -->
<!-- Best for non-critical content that shouldn't compete with first paint -->
@defer (on idle) {
  <app-analytics-widget />
}

<!-- on viewport: loads when the placeholder enters the visible area -->
<!-- Best for below-the-fold content -->
@defer (on viewport) {
  <app-product-reviews [productId]="id()" />
} @placeholder {
  <div style="height: 400px"></div>  <!-- Give it height so scroll triggers correctly -->
}

<!-- on interaction: loads when user clicks or touches the placeholder -->
@defer (on interaction) {
  <app-rich-text-editor />
} @placeholder {
  <div class="editor-placeholder" tabindex="0">Click to open editor</div>
}

<!-- on hover: loads when user hovers over the placeholder -->
@defer (on hover) {
  <app-tooltip-content />
} @placeholder {
  <span class="tooltip-trigger">ⓘ</span>
}

<!-- on timer: loads after a fixed delay regardless of user action -->
@defer (on timer(2s)) {
  <app-chat-widget />
}

<!-- on immediate: loads right away but still lazy (not blocking first paint) -->
@defer (on immediate) {
  <app-secondary-nav />
}

<!-- when: loads when a custom expression becomes truthy -->
@defer (when isAuthenticated()) {
  <app-user-dashboard />
}
```

### Controlling the loading experience

`@loading` accepts two timing parameters to prevent bad UX:

```html
@defer (on viewport) {
  <app-map [location]="location()" />
}
@placeholder (minimum 200ms) {
  <!-- minimum: keep placeholder visible for at least 200ms -->
  <!-- prevents a flash if the bundle loads instantly (cached) -->
  <div class="map-skeleton"></div>
}
@loading (after 100ms; minimum 500ms) {
  <!-- after: wait 100ms before showing loading — don't flash for fast loads -->
  <!-- minimum: once shown, keep it for at least 500ms — prevents jarring flicker -->
  <app-spinner message="Loading map…" />
}
```

**`after`** — if the download completes within this window, the `@loading`
block is never shown at all. Prevents a flash of spinner for fast connections.

**`minimum`** — once `@loading` is shown, keep it visible for at least this
long. Prevents the spinner disappearing so quickly that it looks like a glitch.

Both parameters accept `ms` or `s` units.

### Prefetching

Prefetch downloads the bundle eagerly while still showing the placeholder.
When the display trigger eventually fires, the content appears instantly:

```html
<!-- Prefetch while idle, display on viewport -->
<!-- Bundle is cached by the time the user scrolls to it -->
@defer (on viewport; prefetch on idle) {
  <app-recommended-products />
} @placeholder {
  <div class="products-skeleton"></div>
}

<!-- Prefetch immediately, but only show when user interacts -->
@defer (on interaction; prefetch on immediate) {
  <app-video-player [src]="videoUrl()" />
} @placeholder {
  <img [src]="thumbnail()" alt="Play video" />
}
```

## Real-world patterns

### Pattern 1 — Deferring below-the-fold content on a long page

A product detail page: hero + price are critical; reviews + recommendations
are below the fold and loaded lazily:

```html
<!-- app-product-detail.component.html -->

<!-- Critical above-the-fold content — always in main bundle -->
<app-product-hero [product]="product()" />
<app-add-to-cart [productId]="product().id" />

<!-- Reviews — deferred until scrolled into view, prefetched on idle -->
@defer (on viewport; prefetch on idle) {
  <app-product-reviews [productId]="product().id" />
} @placeholder {
  <section class="reviews-placeholder" aria-busy="true">
    <h2>Customer Reviews</h2>
    <div class="skeleton-lines"></div>
  </section>
} @loading (after 200ms; minimum 400ms) {
  <app-reviews-skeleton />
}

<!-- Recommendations — load when browser is idle -->
@defer (on idle) {
  <app-recommended-products [categoryId]="product().categoryId" />
} @placeholder {
  <div style="min-height: 300px"></div>
}
```

### Pattern 2 — Feature-gating expensive components by auth state

Load a heavy dashboard only after authentication is confirmed. No wasted
download for unauthenticated visitors:

```typescript
@Component({
  selector: 'app-shell',
  standalone: true,
  template: `
    <app-public-header />

    @defer (when authService.isAuthenticated()) {
      <app-user-dashboard />
    } @placeholder {
      <app-sign-in-prompt />
    } @error {
      <p>Dashboard failed to load.
        <a routerLink="/support">Contact support</a>
      </p>
    }
  `,
})
export class ShellComponent {
  authService = inject(AuthService);
}
```

### Pattern 3 — Deferring a heavy editor behind an interaction

Rich text editors are some of the heaviest dependencies in a web app (ProseMirror,
Quill, TipTap). Defer them until the user actually wants to edit:

```html
@defer (on interaction; prefetch on hover) {
  <app-rich-text-editor
    [initialValue]="content()"
    (valueChange)="content.set($event)"
  />
} @placeholder {
  <!-- Looks like the editor — user clicks to activate -->
  <div
    class="editor-preview"
    tabindex="0"
    role="button"
    aria-label="Click to edit"
  >
    <div [innerHTML]="content()"></div>
    <span class="edit-hint">Click to edit</span>
  </div>
}
```

`prefetch on hover` means the editor bundle starts downloading the moment the
user hovers — by the time they click, it's likely already cached.

## Common mistakes

### Mistake 1 — Putting non-standalone components inside @defer

`@defer` requires that all components, directives, and pipes inside the block
are **standalone**. NgModule-based dependencies cannot be code-split this way:

```html
<!-- ❌ LegacyChartComponent is declared in an NgModule — compiler error -->
@defer {
  <app-legacy-chart [data]="data()" />
}

<!-- ✅ StandaloneChartComponent has standalone: true -->
@defer {
  <app-standalone-chart [data]="data()" />
}
```

If a dependency isn't standalone yet, migrate it first with
`ng generate @angular/core:standalone`, or wrap it in a standalone adapter
component.

### Mistake 2 — Forgetting height on the @placeholder for viewport triggers

`on viewport` uses an `IntersectionObserver` on the placeholder element. If the
placeholder has zero height, it may be considered "in the viewport" immediately
— defeating the lazy loading entirely. Or the trigger never fires because the
element collapses:

```html
<!-- ❌ Zero-height placeholder — trigger fires immediately or never -->
@defer (on viewport) {
  <app-comments />
} @placeholder {
  <span></span>
}

<!-- ✅ Give the placeholder roughly the expected height of the content -->
@defer (on viewport) {
  <app-comments />
} @placeholder {
  <div style="min-height: 600px; background: #f5f5f5; border-radius: 8px;"></div>
}
```

### Mistake 3 — Using @defer for components that don't meaningfully impact bundle size

The official Angular docs describe `@defer` as being for "code that is not
strictly necessary for the initial rendering of a page" and "heavy components
that may not ever be loaded until a later time." The pattern is most valuable
when the deferred component has significant dependencies of its own — a chart
library, a map SDK, a rich text editor, a video player.

For small, self-contained components with no heavy third-party dependencies,
the added complexity of managing placeholder and loading states is not worth it:

```html
<!-- ❌ A simple icon or label component adds negligible bundle weight -->
@defer (on idle) {
  <app-status-label [status]="status()" />
}

<!-- ✅ A data visualization library with heavy dependencies is a good candidate -->
@defer (on viewport) {
  <app-sales-chart [data]="salesData()" />
}
```

A practical signal: if you open your bundle analyzer and the component's chunk
barely registers, `@defer` is not worth the placeholder/loading state overhead.
If it pulls in a sizable third-party library, `@defer` is likely worth it.

### Mistake 4 — Importing deferred dependencies in the main component

If you import a deferred component in the `imports` array of the parent, Angular
includes it in the **main bundle**, not the lazy chunk. The compiler can only
split what it knows is exclusive to the `@defer` block:

```typescript
// ❌ HeavyChartComponent is in imports[] — it's in the main bundle
@Component({
  standalone: true,
  imports: [HeavyChartComponent],  // forces it into main bundle
  template: `
    @defer {
      <app-heavy-chart />  // no longer lazy — already bundled
    }
  `,
})

// ✅ Don't import deferred dependencies in imports[] — let @defer own them
@Component({
  standalone: true,
  imports: [],  // HeavyChartComponent NOT here
  template: `
    @defer {
      <app-heavy-chart />  // compiler can now split this into a lazy chunk
    }
  `,
})
```

## How this evolved

> - **Angular 2–16 (2016–2023):** No template-level lazy rendering. The only
>   lazy loading mechanism was route-level `loadChildren`/`loadComponent`.
>   Developers who wanted deferred content had to wire up `IntersectionObserver`,
>   dynamic `import()`, `ViewContainerRef.createComponent()`, and loading state
>   manually.
>
> - **Angular 17 (2023):** `@defer` introduced as **stable** — one of the
>   headline features of Angular 17 alongside the new control flow syntax.
>   All triggers (`on idle`, `on viewport`, `on interaction`, `on hover`,
>   `on timer`, `on immediate`, `when`) shipped at launch. `prefetch` triggers
>   also shipped at launch.
>
> - **Angular 18 (2024):** `@defer` extended with `@placeholder (minimum)` and
>   `@loading (after; minimum)` timing parameters, addressing the
>   common flicker problems with fast connections.
>
> - **Angular 22 (now):** `@defer` is fully stable and the recommended approach
>   for any non-critical content on content-heavy pages. Works in both zone.js
>   and zoneless apps. Works with signals. The Angular DevTools profiler shows
>   deferred block boundaries in the component tree.

## See also

- [Control Flow](../components/templates/control-flow.md) — `@if`, `@for`,
  `@switch` — the other `@`-block template syntax
- [Lazy Loading](../routing/lazy-loading.md) — route-level lazy loading with
  `loadComponent` and `loadChildren`
- [SSR & Hydration](./ssr-hydration.md) — how `@defer` interacts with
  server-side rendering and incremental hydration
- [Angular DevTools](../developer-tools/angular-devtools.md) — visualizing
  deferred block boundaries in the component tree
- [Official docs — @defer](https://angular.dev/guide/defer)

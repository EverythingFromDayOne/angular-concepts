---
roadmap_node: "ssr-hydration"
title: "SSR & Hydration"
file: "rendering/ssr-hydration.md"
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

# SSR & Hydration

> **Lead with this:** Server-side rendering produces HTML the browser can show
> instantly; hydration is the process of turning that static HTML into a live,
> interactive Angular app — and in v22, Angular does it incrementally by
> default, so you only ship the JavaScript for the parts of the page that
> actually need to wake up.

## What it is

A plain Angular app (CSR — client-side rendering) sends an empty HTML shell to
the browser and lets JavaScript build the entire page after the bundle loads.
Fast for the developer, slow for the user: blank screen until the JS executes,
poor SEO, bad Core Web Vitals.

**Server-side rendering (SSR)** runs your Angular components on a Node server
(or at build time for SSG), produces a real HTML document, and sends that to
the browser. The user sees content immediately. But the HTML is static — no
event listeners are attached yet.

**Hydration** is the bridge. When the JavaScript bundle loads on the client,
Angular reuses the existing server-rendered DOM rather than throwing it away
and rebuilding it. It attaches event listeners, wires up reactivity, and
turns the page interactive — without a flash, layout shift, or full re-render.

Three render modes coexist:

| Mode | When the HTML is produced | When to use |
| --- | --- | --- |
| **`RenderMode.Server`** (SSR) | Per-request, on the Node server | Personalized pages, dashboards, content that varies per user |
| **`RenderMode.Prerender`** (SSG) | At build time, once per route | Static content: docs, blogs, marketing pages |
| **`RenderMode.Client`** (CSR) | In the browser, after JS loads | Routes behind auth, admin panels, low-traffic interactive pages |

You configure rendering **per route** — different routes in the same app can
use different modes.

In Angular v22, hydration is opinionated and modern:

- `provideClientHydration()` enables hydration **and** incremental hydration
  by default
- Event replay is automatic
- New apps generated with `ng new --ssr` ship with full hybrid rendering wired
  up
- Zoneless and SSR are fully supported together

## How it works under the hood

### The two-render problem (and why hydration solves it)

Before hydration existed, SSR worked like this: the server renders the page;
the browser displays it; Angular bootstraps; Angular **throws away the
server-rendered DOM** and re-renders from scratch. The user saw content
flicker — sometimes for hundreds of milliseconds — as the server's DOM was
replaced by a structurally identical client-rendered version.

That flicker hurt LCP and CLS metrics. It also wasted bandwidth: the server
sent HTML the client immediately discarded.

**Non-destructive hydration**, stable since Angular 17, fixes this. When the
client bootstraps an app rendered on the server, Angular **walks the existing
DOM tree** instead of creating new nodes. For each component, it matches its
template against the existing DOM, attaches event listeners, sets up signal
subscriptions, and registers the component in the change detection tree.
The DOM nodes are never replaced; they are reused.

This requires the server-rendered DOM and the client-side template to produce
**identical structures** — Angular relies on positional matching during the
walk. Direct DOM manipulation outside Angular (e.g. via `document.querySelector`)
breaks this assumption and is the most common cause of hydration errors.

### Event replay — capturing clicks before hydration finishes

The window between "user sees HTML" and "Angular finishes hydrating" can be
hundreds of milliseconds. Without event replay, any clicks during that window
are lost — the listener wasn't attached yet.

Angular v18+ ships **event replay** built on JSAction. A tiny script attached
to the server-rendered page captures native browser events (`click`,
`mouseover`, `focusin`, etc.) into a queue. When hydration completes, Angular
attaches the real listeners and **replays** the queued events in order, so
none of the user's interactions are lost.

As of v22, event replay is enabled automatically by `provideClientHydration()`
— you don't add `withEventReplay()` separately.

### Incremental hydration — the v19+ improvement

Full-application hydration loads and hydrates the entire app's JavaScript on
page load, regardless of which parts the user actually interacts with first.
For content-heavy pages, this still means shipping a large bundle and walking
a deep tree before anything becomes interactive.

**Incremental hydration** (stable since v20, default in v22) defers hydration
of specific blocks until a trigger fires. It builds on `@defer` blocks:

- The server **renders the deferred content** into HTML normally
- The client **does NOT load the JavaScript** for that block on page load
- The block sits "dehydrated" in the DOM — visible but not interactive
- When a hydrate trigger fires (viewport, interaction, timer, etc.), Angular
  fetches the chunk, hydrates that subtree, and replays any queued events
  for it

This decouples "what HTML do I send" from "what JavaScript do I ship." The
user gets a complete page immediately; the JavaScript loads in pieces as
needed.

**The hydration hierarchy.** A child cannot be hydrated inside a dehydrated
parent — the parent owns change detection and input bindings. If a user
interacts with a child whose parent is dehydrated, Angular automatically
hydrates the parent first to provide the context. This affects how you
design defer block boundaries: they should be self-contained subtrees.

## Basic usage

### Setting up SSR in a new project

```bash
ng new my-app --ssr
```

This generates a project with:

- `src/server.ts` — Node Express server entry point
- `src/main.server.ts` — server-side Angular bootstrap
- `src/app/app.config.server.ts` — server-only providers
- `src/app/app.routes.server.ts` — per-route render mode configuration

### Adding SSR to an existing project

```bash
ng add @angular/ssr
```

The schematic creates the server files above and wires up `provideClientHydration()`
in your existing `app.config.ts`.

### The client config — hydration providers

In Angular v22, this single call enables hydration, incremental hydration, and
event replay together:

```typescript
// src/app/app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideClientHydration(),       // v22: incremental hydration + event replay are automatic
  ],
};
```

To opt out of incremental hydration (e.g. for debugging, or if you have
existing direct DOM manipulation that breaks under it):

```typescript
import {
  provideClientHydration,
  withNoIncrementalHydration,
} from '@angular/platform-browser';

provideClientHydration(withNoIncrementalHydration())
```

### The server config — render modes per route

```typescript
// src/app/app.routes.server.ts
import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  {
    path: '',                       // "/" — static marketing page
    renderMode: RenderMode.Prerender,
  },
  {
    path: 'blog/:slug',             // dynamic blog posts — prerender each one
    renderMode: RenderMode.Prerender,
    async getPrerenderParams() {
      return [{ slug: 'first-post' }, { slug: 'second-post' }];
    },
  },
  {
    path: 'dashboard/**',           // logged-in only — client-render
    renderMode: RenderMode.Client,
  },
  {
    path: 'product/:id',            // dynamic but personalized — SSR
    renderMode: RenderMode.Server,
  },
  {
    path: '**',                     // fallback
    renderMode: RenderMode.Server,
  },
];
```

```typescript
// src/app/app.config.server.ts
import { ApplicationConfig, mergeApplicationConfig } from '@angular/core';
import { provideServerRendering, withRoutes } from '@angular/ssr';
import { appConfig } from './app.config';
import { serverRoutes } from './app.routes.server';

const serverConfig: ApplicationConfig = {
  providers: [
    provideServerRendering(withRoutes(serverRoutes)),
  ],
};

export const config = mergeApplicationConfig(appConfig, serverConfig);
```

### Adding incremental hydration triggers to @defer

Without incremental hydration, a `@defer` block renders its placeholder on
the server and the real content is downloaded and rendered entirely on the
client. With incremental hydration, the block can be **rendered on the
server** and then hydrated later based on triggers:

```html
<!-- Critical content — fully hydrated on page load -->
<app-header />
<app-product-hero [product]="product()" />
<app-add-to-cart [productId]="product().id" />

<!-- Reviews — server-rendered in HTML, hydration deferred until visible -->
@defer (hydrate on viewport) {
  <app-product-reviews [productId]="product().id" />
}

<!-- Comparison widget — server-rendered, hydrates on user interaction -->
@defer (hydrate on interaction) {
  <app-comparison-tool [products]="related()" />
}

<!-- Static article body — render on server, never hydrate -->
@defer (hydrate never) {
  <app-article-content [article]="article()" />
}

<!-- Recommendations — render on server, hydrate after a delay -->
@defer (hydrate on timer(3s)) {
  <app-recommended-products />
}
```

The hydrate triggers mirror the regular `@defer` triggers:

| Trigger | Hydrates when |
| --- | --- |
| `hydrate on viewport` | Block scrolls into the viewport |
| `hydrate on interaction` | User clicks or interacts with the block |
| `hydrate on hover` | Mouse enters or block receives focus |
| `hydrate on idle` | Browser reports idle time |
| `hydrate on timer(2s)` | After a fixed delay |
| `hydrate when expression()` | A signal-based expression becomes true |
| `hydrate never` | Block stays static forever — no JS shipped for it |

`hydrate never` is the most aggressive optimization. Use it for content that
is genuinely never interactive — long-form prose, footers, static metadata —
and you eliminate that JavaScript from your bundle entirely.

### Detecting the platform

Code that uses browser-only APIs (`window`, `document`, `localStorage`) must
not run during SSR. Use `isPlatformBrowser`:

```typescript
import { Component, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({ /* ... */ })
export class AnalyticsComponent {
  private platformId = inject(PLATFORM_ID);

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      // Safe: only runs on the client
      window.analytics?.track('page_view');
    }
  }
}
```

Or use `afterNextRender` (Angular 16+), which guarantees the callback runs
only on the client:

```typescript
import { Component, afterNextRender } from '@angular/core';

@Component({ /* ... */ })
export class AnalyticsComponent {
  constructor() {
    afterNextRender(() => {
      // Runs only on the client, after the first render
      window.analytics?.track('page_view');
    });
  }
}
```

## Real-world patterns

### Pattern 1 — Mixed-mode site (the typical e-commerce setup)

A real production site usually has all three render modes:

```typescript
// app.routes.server.ts
export const serverRoutes: ServerRoute[] = [
  // Marketing pages — prerender at build time, blazing fast
  { path: '', renderMode: RenderMode.Prerender },
  { path: 'about', renderMode: RenderMode.Prerender },
  { path: 'contact', renderMode: RenderMode.Prerender },

  // Product pages — SSR (inventory, prices change per request)
  { path: 'products/:id', renderMode: RenderMode.Server },
  { path: 'category/:slug', renderMode: RenderMode.Server },

  // Logged-in account area — client-render (per-user, no SEO value)
  { path: 'account/**', renderMode: RenderMode.Client },
  { path: 'checkout/**', renderMode: RenderMode.Client },

  // Search — SSR for SEO
  { path: 'search', renderMode: RenderMode.Server },

  // Catch-all
  { path: '**', renderMode: RenderMode.Server },
];
```

### Pattern 2 — Heavy below-the-fold content with incremental hydration

A long product page where the hero and buy box must be instantly interactive,
but reviews, comparisons, and recommendations don't need their JavaScript
upfront:

```html
<!-- Above the fold — full hydration -->
<app-product-hero [product]="product()" />
<app-buy-box [product]="product()" [variants]="variants()" />

<!-- Below the fold — server-render, hydrate on demand -->
@defer (hydrate on viewport) {
  <section class="reviews">
    <h2>Customer Reviews</h2>
    <app-reviews [productId]="product().id" />
  </section>
}

@defer (hydrate on viewport) {
  <section class="comparisons">
    <app-comparison-table [products]="related()" />
  </section>
}

@defer (hydrate on interaction) {
  <!-- Only hydrate when user clicks the FAQ accordion -->
  <app-faq [items]="faqItems()" />
}

@defer (hydrate never) {
  <!-- Static legal text, never interactive -->
  <app-terms-and-conditions />
}
```

The initial bundle ships only the hero, buy box, and the small JSAction
event-replay runtime. Everything else is HTML on the server side and lazy JS
on the client side.

### Pattern 3 — Using SSR's HttpClient cache

Angular's `HttpClient` caches outgoing requests during SSR and transfers the
cache to the client, so the same request isn't made twice (once on server,
once on client during hydration):

```typescript
// app.config.ts — enable the transfer cache
import { provideHttpClient, withFetch } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideClientHydration(),
    provideHttpClient(withFetch()),  // required for SSR; uses fetch under the hood
  ],
};
```

When a component calls `HttpClient.get()` on the server during SSR, the
response is serialized into the HTML as a `<script type="ng/state">` payload.
On the client, when the same component hydrates and makes the same request,
Angular returns the cached value instantly — no second network round trip.

## Common mistakes

### Mistake 1 — Direct DOM manipulation that breaks hydration

The most common hydration error. Hydration assumes the server's DOM structure
matches what Angular's template would produce on the client. Manipulating the
DOM directly (via `nativeElement`, `document.querySelector`, jQuery, etc.)
breaks that invariant:

```typescript
// ❌ Direct DOM manipulation — hydration mismatch error
@Component({ /* ... */ })
export class ChartComponent implements AfterViewInit {
  ngAfterViewInit(): void {
    document.querySelector('#chart')!.innerHTML = renderChart(this.data());
    // Server's DOM doesn't have this content; hydration walks into a mismatch
  }
}

// ✅ Use Angular's APIs so server and client agree
@Component({
  template: `<div [innerHTML]="chartHtml()"></div>`,
})
export class ChartComponent {
  chartHtml = computed(() => renderChart(this.data()));
}

// ✅ Or skip hydration for components that genuinely need raw DOM access
@Component({
  selector: 'app-third-party-widget',
  template: `<div #widget></div>`,
  host: { ngSkipHydration: 'true' },
})
export class ThirdPartyWidgetComponent { /* ... */ }
```

`ngSkipHydration` is the escape hatch for components that fundamentally
cannot match server output (third-party libraries that mutate the DOM, legacy
code being migrated). Apply it sparingly — every skipped component loses the
SSR performance benefit for that subtree.

### Mistake 2 — Reading window/document at module top level

Code that runs during module evaluation runs on the server. If it touches
browser globals, it throws:

```typescript
// ❌ Runs during SSR — crashes because `window` doesn't exist on the server
const isMobile = window.innerWidth < 768;

@Component({ /* ... */ })
export class HeaderComponent {
  showMobileMenu = isMobile;
}

// ✅ Defer the check to a client-only context
@Component({ /* ... */ })
export class HeaderComponent {
  showMobileMenu = signal(false);

  constructor() {
    afterNextRender(() => {
      this.showMobileMenu.set(window.innerWidth < 768);
    });
  }
}
```

### Mistake 3 — Hydrating a third-party component that mutates the DOM after render

Charting libraries, map libraries, and rich text editors typically write to
their host element after initialization. If the server renders an empty
container and the client tries to hydrate the same container after the library
has already populated it, the structures don't match:

```typescript
// ❌ Library writes to the canvas after mount — hydration sees foreign nodes
@Component({
  template: `<div id="map"></div>`,
})
export class MapComponent implements AfterViewInit {
  ngAfterViewInit(): void {
    new MapLibrary('#map', { ... });
  }
}

// ✅ Skip hydration for the third-party island
@Component({
  template: `<div id="map" #mapEl></div>`,
  host: { ngSkipHydration: 'true' },   // hydration leaves this subtree alone
})
export class MapComponent implements AfterViewInit { /* ... */ }
```

### Mistake 4 — Expecting incremental hydration to work without standalone components

Like `@defer` itself, incremental hydration requires **standalone components**
for the deferred content. NgModule-declared components inside a `@defer
(hydrate ...)` block cause a compiler error:

```html
<!-- ❌ ReviewsComponent is declared in an NgModule -->
@defer (hydrate on viewport) {
  <app-reviews />
}

<!-- ✅ ReviewsComponent has standalone: true -->
@defer (hydrate on viewport) {
  <app-reviews />
}
```

Migrate to standalone first (`ng generate @angular/core:standalone`) before
adopting incremental hydration.

### Mistake 5 — Forgetting that `hydrate never` makes the block truly static

`hydrate never` means **the JavaScript is never shipped**. Any event handlers,
signal subscriptions, or `routerLink` directives inside the block won't work:

```html
<!-- ❌ This routerLink won't work — block is never hydrated -->
@defer (hydrate never) {
  <a [routerLink]="['/products', id()]">View product</a>
}

<!-- ✅ Use a plain anchor tag (browser handles the navigation) -->
@defer (hydrate never) {
  <a [attr.href]="'/products/' + id()">View product</a>
}
```

`<a href>` inside a `hydrate never` block triggers a full browser navigation
(not SPA navigation), but the link itself works. `routerLink` requires
JavaScript and silently does nothing.

## How this evolved

> - **Angular 4–15 (2017–2022):** Angular Universal provided SSR as a separate
>   library. No built-in hydration — the framework rendered HTML on the server
>   and then **destroyed and rebuilt** the DOM on the client. Significant
>   layout flash and wasted compute.
>
> - **Angular 16 (May 2023):** **Non-destructive hydration** introduced in
>   developer preview. First time Angular could reuse server-rendered DOM
>   instead of throwing it away. 40–50% LCP improvements observed in
>   production apps.
>
> - **Angular 17 (Nov 2023):** Full-application hydration graduated to
>   **stable**. `provideClientHydration()` shipped as the standard API.
>   Angular Universal was renamed to `@angular/ssr` and folded into the main
>   framework.
>
> - **Angular 18 (May 2024):** **Event replay** introduced via `withEventReplay()`.
>   Built on Google's JSAction library, it captures pre-hydration events and
>   replays them once hydration completes.
>
> - **Angular 19 (Nov 2024):** **Incremental hydration** shipped in developer
>   preview. **Route-level render mode configuration** (`RenderMode.Server`,
>   `Prerender`, `Client`) shipped in developer preview. Both built on top of
>   `@defer` blocks and `provideServerRendering(withRoutes(...))`.
>
> - **Angular 20 (May 2025):** Incremental hydration and route-level render
>   modes graduated to **stable**. Event replay graduated to stable and was
>   enabled by default in new projects.
>
> - **Angular 22 (June 2026):** `provideClientHydration()` now enables
>   **incremental hydration automatically**. Opt out with
>   `withNoIncrementalHydration()`. Event replay is on by default. The SSR
>   story is opinionated and complete for v22: enable hydration with one line,
>   configure render modes per route, opt into hydrate triggers where the
>   page benefits.

## See also

- [@defer Blocks](./defer-blocks.md) — the foundation incremental hydration
  builds on
- [Routing](../routing/routing.md) — how server routes coexist with client
  routes
- [Lazy Loading](../routing/lazy-loading.md) — route-level bundle splitting
  works hand-in-hand with route-level render modes
- [Lifecycle](../components/lifecycle.md) — `afterNextRender` for client-only
  side effects
- [Change Detection](../components/change-detection.md) — how zoneless and
  SSR interact
- [HTTP](../http/typed-requests.md) — the SSR transfer cache for HTTP requests
- [Official docs — Hydration](https://angular.dev/guide/hydration)
- [Official docs — Incremental Hydration](https://angular.dev/guide/incremental-hydration)
- [Official docs — Server-side rendering](https://angular.dev/guide/ssr)
- [Official docs — Hybrid rendering](https://angular.dev/best-practices/performance/ssr)

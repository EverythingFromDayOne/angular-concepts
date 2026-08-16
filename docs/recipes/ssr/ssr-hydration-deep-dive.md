---
recipe_id: "ssr-hydration-deep-dive"
description: "Most hydration bugs trace back to server and client rendering different markup, and the console warning usually names the mismatch"
primary_concept: "ssr/ssr-hydration"
related_concepts: ["reactivity/signals", "http/http", "components/change-detection"]
demo_repo: null
angular_baseline: "22.1.1"
difficulty: "advanced"
status:
  upgraded: true
  reviewed: false
---

# SSR + Hydration: Debugging the Mismatches

> **What you'll build:** working solutions for the six most common
> hydration bugs teams hit after enabling SSR — `window is not defined`,
> "Hello, undefined" text mismatches, DOM structure mismatches, double
> API fetches, third-party libraries that touch DOM at construction,
> and the "clicks don't work for 3 seconds after page load" bug. Plus
> the modern APIs — `provideClientHydration`, `withEventReplay`,
> `afterNextRender`, `TransferState` — with concrete usage patterns
> and the specific console warning messages you'll see when things go
> wrong.
>
> **Concepts you'll touch:** [SSR & Hydration](../../concepts/rendering/ssr-hydration.md), [Signals](../../concepts/reactivity/signals.md), [HTTP](../../concepts/http/http.md), [Change Detection](../../concepts/components/change-detection.md)
>
> **Time:** ~35 minutes to read; days-to-weeks to debug real hydration
> mismatches in a production codebase.

---

## The scenario

You enabled SSR on a marketing page (`ng add @angular/ssr`). Lighthouse LCP dropped from 3.2s to 0.9s. SEO improved noticeably. Product-page load feels instant.

Then production reports come in:

- **"The site shows `Hello, undefined` for half a second, then flips to `Hello, Alice`."** The server rendered without knowing the user; the client hydrated with the real name.
- **"Clicking Buy immediately after landing does nothing for 3 seconds."** The button rendered from server HTML but Angular hadn't hydrated yet, so no click handler fired.
- **"Chrome shows `NG05000` warnings in the console on every page load."** The DOM the client tries to hydrate doesn't match what the server rendered.
- **"The map on the location page throws `window is not defined` during server render."** A third-party maps library accessed `window` in its constructor; the Node.js server has no window.
- **"The API is being called twice on every page load — once server-side, once client-side."** No transfer of the server's fetch to the client, so the client re-fetches.
- **"After navigating away and back, the previous page's data flickers into view for a moment."** Hydration is re-reading stale state.

Every one of these is a specific class of bug with a specific fix. Enabling SSR is table stakes; making it robust is where teams stall for weeks. This recipe walks through each bug, the console signature that identifies it, and the pattern that resolves it.

---

## The SSR + hydration model

The mental model, in three sentences:

1. **The server renders full HTML** using Angular's platform-server. It runs your components, resolves your data, and produces the initial page markup. The user sees content immediately when the HTML arrives.

2. **The client bootstraps Angular** on top of the existing HTML. Instead of clearing and re-rendering, Angular walks the DOM, matches it against the component tree, and attaches event listeners and state. This is "hydration."

3. **Mismatches happen when server-rendered HTML differs from what the client would render.** Angular can't cleanly attach to DOM it didn't expect; it warns, throws, or (in the worst case) silently corrupts state.

Every hydration bug is a variation on #3. The debugging discipline is: **what did the server compute, what does the client compute, why are they different, how do I make them match.**

### The lifecycle

```text
1. Browser → GET /product/123
        ▼
2. Node.js (Angular server)
   - Bootstraps app
   - Runs guards, resolvers, effects
   - Renders components → HTML string
   - Serializes into initial HTML response
        ▼
3. Browser receives HTML
   - Renders visually (fast — no JS needed yet)
   - Downloads app bundle
        ▼
4. Browser executes app bundle
   - provideClientHydration() kicks in
   - Angular walks the DOM, matches components to elements
   - Attaches event handlers, restores state
   - Now interactive
        ▼
5. Steady-state app running (no more SSR)
```

The bugs cluster around step 4. Something the client computes differently from step 2 causes Angular's DOM walk to fail.

---

## Setting up SSR + hydration

The v22 approach — one schematic, one provider:

```bash
ng add @angular/ssr
```

This generates:
- `server.ts` — the Node.js Express server
- `src/main.server.ts` — server bootstrap entry
- Updated `angular.json` with SSR build target
- `app.config.server.ts` — server-only providers

For the client, add hydration to `app.config.ts`:

```typescript
// File: app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideClientHydration, withEventReplay, withI18nSupport } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withFetch } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withFetch()),  // fetch backend works better with SSR
    provideClientHydration(
      withEventReplay(),   // capture events during hydration; replay after
      withI18nSupport(),   // hydrate content inside i18n blocks (v18+)
    ),
  ],
};
```

**Three things matter in that snippet:**

- **`provideClientHydration()`** — the switch. Without this, the browser clears the server HTML and re-renders from scratch (destructive hydration; slower).
- **`withEventReplay()`** — v18+ feature. Events fired during the hydration window (before handlers are attached) are captured and replayed once hydration completes. Fixes the "clicks don't work for 3 seconds" bug.
- **`withFetch()`** — switches `HttpClient` to use the Fetch API backend instead of XHR. Better SSR integration; Angular's server has fetch support built-in.

---

## Bug 1 — `window is not defined` during server render

**Console signature (server-side)**:

```text
ReferenceError: window is not defined
    at MapService (/dist/server/main.js:1234:5)
    at NodeInjectorFactory.factory
```

**What's happening**: `window`, `document`, `localStorage`, `navigator`, etc. exist only in browsers. On the Node.js server, they're `undefined`. Any code that references them at construction time (before hydration) crashes the server render.

**Fix — `isPlatformBrowser` guard**:

```typescript
// File: services/map.service.ts
import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Injectable({ providedIn: 'root' })
export class MapService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);
  private mapInstance: MapLibrary | null = null;

  initMap(elementId: string): void {
    if (!this.isBrowser) return;   // no-op on server

    // Only runs in the browser — `window` is defined here
    this.mapInstance = new MapLibrary(document.getElementById(elementId), {
      center: [0, 0],
      zoom: 2,
    });
  }

  destroyMap(): void {
    if (!this.isBrowser) return;
    this.mapInstance?.destroy();
    this.mapInstance = null;
  }
}
```

**Two things worth absorbing:**

- **`inject(PLATFORM_ID)` in the field initializer** — runs at construction. The `isBrowser` boolean is cached; subsequent checks are free.
- **Every browser-only method starts with `if (!this.isBrowser) return;`**. Even one missed method call from the server crashes the render.

### Alternative — `afterNextRender` for one-shot browser work

If the code should run **once, after the browser has hydrated**, use `afterNextRender`:

```typescript
import { Component, afterNextRender } from '@angular/core';

@Component({ /* … */ })
export class MapPageComponent {
  constructor() {
    // Skips entirely on server; runs after client hydration completes
    afterNextRender(() => {
      // window/document available here — no isPlatformBrowser needed
      const map = new MapLibrary(document.getElementById('map')!, { /* … */ });
    });
  }
}
```

`afterNextRender` is v17+. It's the preferred pattern for "run this browser-only initialization once after the DOM is ready" — cleaner than the platform-check pattern for one-shot cases. Use it when:

- The work needs to happen once, after render
- The code manipulates the DOM directly
- The service doesn't need to work in a fallback mode on the server

`isPlatformBrowser` is preferred when:

- The check runs many times
- The service needs a server-side no-op fallback
- You want to catch missed calls at development time

---

## Bug 2 — "Hello, undefined" text mismatch

**Console signature (client-side)**:

```text
NG05000: Angular hydration expected the following node to be created
by the server, but got:
  Client: <span>Hello, Alice</span>
  Server: <span>Hello, undefined</span>
```

**What's happening**: The server didn't know the user's name (auth state isn't available server-side by default). It rendered `Hello, undefined`. The client hydrated with the real user; Angular sees the text is different; warns and diverges.

**The fix depends on WHERE the data comes from.**

### Server-known data → resolve it server-side

If the data is available on the server (from a cookie, request header, or query param):

```typescript
// File: server.ts (Express server)
import { CommonEngine } from '@angular/ssr';
import express from 'express';

const app = express();

app.get('*', (req, res) => {
  const engine = new CommonEngine();
  const userId = req.cookies['userId'] ?? null;

  engine.render({
    bootstrap: bootstrap,
    documentFilePath: /* … */,
    url: req.url,
    providers: [
      { provide: 'USER_ID', useValue: userId },  // pass to Angular
    ],
  }).then(html => res.send(html));
});
```

The Angular app injects `USER_ID` and uses it in server rendering. Same value the client will read from the same cookie means matching HTML.

### Client-only data → don't render it server-side

If the data literally can't be known server-side (localStorage-based settings, browser-specific state), don't render placeholders server-side. Render conditionally:

```typescript
@Component({
  template: `
    @if (userName()) {
      <span>Hello, {{ userName() }}</span>
    } @else {
      <span>Hello, guest</span>
    }
  `,
})
export class GreetingComponent {
  private readonly platformId = inject(PLATFORM_ID);
  readonly userName = signal<string | null>(null);

  constructor() {
    afterNextRender(() => {
      // Only after hydration: read localStorage
      this.userName.set(localStorage.getItem('userName'));
    });
  }
}
```

**The key move**: `@if (userName())` renders a stable "Hello, guest" on both server and client initially. After hydration, `afterNextRender` fires, reads localStorage, updates the signal, and the "Hello, Alice" appears. **No mismatch** — Angular hydrates matching content, then updates it via signal reactivity.

If a brief "Hello, guest" flicker isn't acceptable, the answer is to pass the user identity in a cookie readable server-side (previous section) — not to render `Hello, undefined` server-side.

---

## Bug 3 — DOM structure mismatch

**Console signature**:

```text
NG05001: An extra <div> node was found in the DOM but no matching node
was created by the server.
```

Or:

```text
NG05002: The server rendered <div> node that has no matching client
node — hydration cannot continue.
```

**What's happening**: The server and client generated different DOM trees. Common causes:

- **Random or time-based content**: `<div>{{ Math.random() }}</div>` — different value each render
- **Conditional rendering on window features**: `@if (window.innerWidth > 768)` — server has no window, client's condition varies
- **Third-party libraries mutating DOM before hydration**: A GA snippet in `<head>` inserted extra nodes that Angular doesn't know about

**Fix — deterministic rendering**:

```typescript
// BUGGY: Math.random() produces different values on server vs client
@Component({
  template: `<div>ID: {{ generateId() }}</div>`,
})
export class WidgetComponent {
  generateId(): string {
    return Math.random().toString(36);
  }
}

// FIX 1: compute at construction (once, deterministic per instance)
@Component({
  template: `<div>ID: {{ id }}</div>`,
})
export class WidgetComponent {
  readonly id = Math.random().toString(36);
  // Note: on server, this random value goes into the HTML.
  // On client hydration, WidgetComponent is instantiated fresh with a NEW random value.
  // Still a mismatch! You need option 2.
}

// FIX 2: use TransferState to send the server's value to the client
@Component({
  template: `<div>ID: {{ id }}</div>`,
})
export class WidgetComponent {
  private readonly state = inject(TransferState);
  private readonly key = makeStateKey<string>('widget-id-' + this.instanceId);

  readonly id: string;

  constructor() {
    const existing = this.state.get(this.key, null);
    if (existing) {
      this.id = existing;  // client: use the value the server rendered
    } else {
      this.id = Math.random().toString(36);
      this.state.set(this.key, this.id);  // server: store for the client
    }
  }
}
```

Fix 2 is the general pattern for "server needs to communicate a computed value to the client." Covered in more detail in Bug 4.

### Media queries — render server-safe defaults

```typescript
// BUGGY on server (no window.matchMedia)
@Component({
  template: `
    @if (isDesktop()) {
      <app-desktop-nav />
    } @else {
      <app-mobile-nav />
    }
  `,
})
export class NavComponent {
  isDesktop = signal(window.matchMedia('(min-width: 768px)').matches);
}

// FIX: default to a stable choice server-side, update after hydration
@Component({ /* … */ })
export class NavComponent {
  private readonly platformId = inject(PLATFORM_ID);
  readonly isDesktop = signal(true);  // assume desktop server-side

  constructor() {
    afterNextRender(() => {
      const matches = window.matchMedia('(min-width: 768px)').matches;
      this.isDesktop.set(matches);
    });
  }
}
```

Server renders the desktop version. Client hydrates matching HTML. After hydration, the signal updates based on real viewport size; navigation swaps if needed.

**Pick the default that will be right for most users.** For a marketing site, desktop is often the safe bet (SEO crawlers behave like desktop). For a mobile-first app, mobile might be right. Use analytics to decide.

---

## Bug 4 — double API fetch (server + client)

**What's happening**: The server-rendered page called `/api/products`. The response was rendered into HTML. The client hydrated and — because Angular re-runs component initialization — called `/api/products` **again**.

**Fix — `TransferState` to pass the server's response to the client**:

```typescript
// File: services/products.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TransferState, makeStateKey } from '@angular/core';
import { Observable, of, tap } from 'rxjs';

const PRODUCTS_KEY = makeStateKey<Product[]>('products');

@Injectable({ providedIn: 'root' })
export class ProductsService {
  private readonly http = inject(HttpClient);
  private readonly transferState = inject(TransferState);

  getProducts(): Observable<Product[]> {
    // On client: check if the server already stashed the data
    const cached = this.transferState.get(PRODUCTS_KEY, null);
    if (cached) {
      // One-shot: consume and remove; subsequent calls fetch normally
      this.transferState.remove(PRODUCTS_KEY);
      return of(cached);
    }

    return this.http.get<Product[]>('/api/products').pipe(
      tap(products => {
        // On server: stash the response for the client to read
        this.transferState.set(PRODUCTS_KEY, products);
      }),
    );
  }
}
```

**Four things doing the work:**

- **`makeStateKey<T>(name)`** creates a typed key. The name must be unique across the app.
- **`transferState.set(key, value)`** on the server stores the value. Angular serializes it into the HTML as a `<script>` block, base64-encoded.
- **`transferState.get(key, default)`** on the client reads what the server stored.
- **`remove(key)` after reading** — one-shot semantics. Subsequent calls (e.g., after navigation) fetch fresh from the API. Without `remove`, the "cached" value would persist forever, causing stale data bugs.

The server does the HTTP call once. The client reads the cached response instead of firing a duplicate call. **Total round trips: 1, not 2.**

### With `HttpClient` — `withHttpTransferCache`

For simpler cases, Angular provides an automatic HTTP transfer cache. Configure once, and all GET requests are automatically stashed and replayed:

```typescript
import { provideHttpClient, withFetch, withHttpTransferCacheOptions } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withFetch(),
      withHttpTransferCacheOptions({
        includeHeaders: [],           // headers to include in cache key (careful with auth)
        includePostRequests: false,   // rarely wanted; POSTs are usually mutations
      }),
    ),
    // …
  ],
};
```

**All GET requests fired during SSR are auto-cached** and replayed on the client with no code changes. This handles 80% of double-fetch cases automatically. Use manual `TransferState` for the remaining 20% — non-HTTP data, transformed responses, computed values.

**Warning**: the auto-cache doesn't filter by user identity. If your API returns user-specific data via cookies, and multiple users share a cache tier (unusual but possible), you have a data-leak risk. For production, prefer explicit `TransferState` where you control what's cached and when.

---

## Bug 5 — third-party library initialization

**What's happening**: A charting library, analytics SDK, or map plugin accesses `window`, `document`, or global objects in its constructor or immediately-executed module code. The server render blows up:

```text
ReferenceError: document is not defined
    at Chart.initialize (/node_modules/some-chart-lib/dist/index.js:...)
```

**Fix 1 — defer to `afterNextRender`**:

```typescript
@Component({ /* … */ })
export class ChartComponent {
  @ViewChild('canvas') canvas!: ElementRef<HTMLCanvasElement>;
  private chart: Chart | null = null;

  constructor() {
    afterNextRender(() => {
      // Dynamic import — the library isn't loaded on the server at all
      import('some-chart-lib').then(module => {
        this.chart = new module.Chart(this.canvas.nativeElement, {
          data: this.chartData(),
        });
      });
    });
  }
}
```

**Two things worth absorbing:**

- **Dynamic `import()`** — the chart library bundle is only downloaded and executed in the browser. The server never sees it. No `window is not defined` because the code doesn't run server-side.
- **`afterNextRender`** — runs after the browser has hydrated. The `@ViewChild` reference is populated; the library initializes against a real DOM element.

### Fix 2 — the library provides an SSR-safe entry point

Some libraries have separate entry points for SSR:

```typescript
import { Chart } from 'some-chart-lib/browser';  // browser-only entry
```

Or expose a "isomorphic" build that no-ops on the server. Check the library's docs — many popular libraries (Sentry, PostHog, LogRocket) have SSR-aware initialization.

### Fix 3 — mock the library server-side via DI

For libraries that can't be conditionally imported, provide a mock on the server:

```typescript
// File: app.config.ts
export const appConfig: ApplicationConfig = { providers: [ /* real providers */ ] };

// File: app.config.server.ts
import { CHART_LIB_TOKEN } from './tokens';

export const serverConfig: ApplicationConfig = {
  providers: [
    { provide: CHART_LIB_TOKEN, useValue: null },  // stub for SSR
  ],
};
```

Components inject `CHART_LIB_TOKEN`; on the server it's `null`, and the code checks for it before use. More work than the dynamic-import approach; use when the library can't be dynamically imported.

---

## Bug 6 — "clicks don't work for 3 seconds after load"

**What's happening**: The user sees the page (server HTML rendered), clicks a button, nothing happens. Three seconds later (or however long the JS bundle takes to download and execute), hydration completes and clicks start working. The first few taps were lost.

**Fix — `withEventReplay()`**:

```typescript
import { provideClientHydration, withEventReplay } from '@angular/platform-browser';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withEventReplay()),
    // …
  ],
};
```

**What it does**: during the pre-hydration window, a small script (injected into the SSR HTML) captures user events (`click`, `keydown`, focus, form submission). After hydration completes, the captured events are replayed in order to the now-attached Angular handlers.

Result: the user taps Buy, sees no immediate response (button doesn't flash), hydration completes ~1 second later, the tap fires the buy handler as if it had been immediate. The perceived latency drops from "broken" to "briefly slow."

**Requirements**:

- v18+ Angular
- `provideClientHydration(withEventReplay())` in the config
- No manual `preventDefault` needed — the replay is handled internally

**Caveat**: events on elements Angular doesn't own (a raw HTML `<a>` link, e.g.) aren't captured — because Angular has no handler to replay to. Navigation happens as normal (the browser follows the link). For Angular-owned interactions, replay works.

---

## Debugging hydration mismatches — the console signatures

The messages Angular emits during a mismatch, decoded:

| Code | Meaning | Common cause |
| --- | --- | --- |
| **NG05000** | Text node content differs | `Math.random`, dates, browser-only state |
| **NG05001** | Client has extra node | Third-party lib inserted a node; `@if` toggled based on browser-only state |
| **NG05002** | Server has extra node | Same but reverse; server rendered something client doesn't |
| **NG05003** | Element type mismatch | `<span>` server, `<div>` client; usually template expression differs |
| **NG05104** | Component input mismatch | `@Input()` value differs between server and client render |

Development mode shows these; production mode suppresses them but the DOM corruption still happens.

**Enable verbose hydration debugging**:

```typescript
provideClientHydration(withEventReplay()),

// In development builds only:
// The debug info is emitted at info-level to console
```

**The debug workflow**:

1. Open DevTools on a page where you see the warning
2. Click the warning to expand
3. Angular shows the diff: `Client rendered X, server rendered Y`
4. Find the component template producing the diff
5. Apply one of the patterns above (afterNextRender / isPlatformBrowser / TransferState / stable default)
6. Reload and verify no warnings

---

## `@defer` blocks and hydration

`@defer` blocks are lazy-loaded on the client. With SSR, they present a choice:

**Default (`prefetch on idle` or similar)**: server doesn't render the deferred content. Client shows placeholder until the trigger fires. Works but delays interactivity of the deferred content.

**With `on hover` / `on interaction`**: the block is truly not rendered until the user does the trigger. SSR renders the placeholder; hydration matches; the block loads only when triggered.

**With `on immediate` (Angular 17+)**: block loads as soon as bundle downloads. Effectively the same as regular content.

For SEO-critical content, `@defer` is often the wrong tool — search crawlers may not fire the trigger. Use lazy loading of the **whole route** instead if the content isn't needed on initial render, so the URL/route determines what gets SSR'd.

---

## Trade-offs and common pitfalls

**Use SSR + hydration when:**

- SEO matters (marketing pages, e-commerce catalogs, content sites)
- LCP or FCP metrics are important for conversion
- Users have slow devices where client-only rendering feels laggy
- Social sharing needs OG tags and preview images

**Skip SSR when:**

- The app is behind a login (SEO doesn't matter for private data)
- All content is user-personalized (server can't render meaningful HTML without knowing the user)
- The team can't afford the operational complexity (Node.js server, caching layer, etc.)
- The rest of the stack isn't SSR-friendly (e.g., third-party dashboards, heavy WebSocket integration)

### Common pitfalls

- **Enabling SSR without hydration.** Server renders HTML; client clears and re-renders. Slower than not enabling SSR at all (extra work with no benefit). Always include `provideClientHydration()`.
- **`window` access at module load time.** Even conditional `if (typeof window !== 'undefined')` isn't enough if the code is at module top-level; the check needs to be inside a function. Server crashes during module evaluation are the worst — no useful stack trace.
- **`localStorage` reads during initialization.** Same as window; not available server-side. Use `afterNextRender` or `isPlatformBrowser`.
- **Assuming `Math.random` produces stable values.** It doesn't — each render is independent. Use `TransferState` to pass the server's random value to the client.
- **Time-based rendering (`new Date()`).** Server time and client time differ (timezone, actual clock). Render server-provided timestamps deterministically, or defer rendering until `afterNextRender`.
- **Ignoring the transfer cache warning.** The auto-HTTP-cache doesn't filter by identity. If your API returns different data for different users based on cookies, the cache can leak. Use explicit `TransferState` for user-specific data.
- **Skipping event replay.** Without `withEventReplay()`, the "clicks don't work for 3 seconds" bug is real. Almost always want event replay.
- **Third-party libraries at module top-level.** `import { Chart } from 'some-lib'` runs on the server too. If the library touches `window` in its module code, the server crashes. Dynamic-import to defer loading.
- **`@ViewChild` in `ngOnInit` for server code.** `@ViewChild` populates after the view is rendered — server-side, this is fine, but you don't have a `nativeElement` in a useful way. Use `afterNextRender` for DOM measurements.
- **Forgetting `remove()` after `TransferState.get()`.** The cached value persists forever; navigation returns stale data. Always `remove` after consuming.
- **HTTP requests without `withFetch()`.** XHR works but has quirks in SSR (some polyfills don't cover it fully). `withFetch()` is more reliable server-side.
- **Not testing SSR in development.** `ng serve` runs client-only; SSR bugs only appear with `ng serve:ssr` or after building and running Node. Have a `dev:ssr` script in your workflow.
- **Cookies for auth in SSR without careful handling.** The server needs to read cookies to render authenticated content. The client reads them via `document.cookie`. If the auth cookie is `HttpOnly` (correct for security), it's not readable by JS on the client — so the client needs the server to have passed the auth state through TransferState.
- **Signals updated inside `afterNextRender` triggering full re-render.** If the signal is read broadly, updating it on hydration causes an immediate re-render of many components. Use OnPush + local signals to bound the impact.

---

## See also

- [SSR & Hydration (concept article)](../../concepts/rendering/ssr-hydration.md) — the deeper conceptual coverage
- [Performance Auditing](../performance/performance-auditing.md) — LCP, FCP, TBT are the metrics SSR improves; this recipe covers measuring
- [Signals](../../concepts/reactivity/signals.md) — the primitives used in `afterNextRender` patterns
- [HTTP](../../concepts/http/http.md) — `provideHttpClient(withFetch())` for SSR-friendly HTTP
- [Change Detection](../../concepts/components/change-detection.md) — hydration + zoneless composition
- [Component Communication](../components/component-communication.md) — patterns that need adaptation for SSR (avoid module-level side effects, use signal-based services)

## References

- [Angular Hydration guide (angular.dev)](https://angular.dev/guide/hydration) — the canonical reference
- [`provideClientHydration` API (angular.dev)](https://angular.dev/api/platform-browser/provideClientHydration)
- [`withEventReplay` API (angular.dev)](https://angular.dev/api/platform-browser/withEventReplay) — v18+
- [`withI18nSupport` API (angular.dev)](https://angular.dev/api/platform-browser/withI18nSupport) — v18+
- [`TransferState` API (angular.dev)](https://angular.dev/api/core/TransferState)
- [`afterNextRender` API (angular.dev)](https://angular.dev/api/core/afterNextRender)
- [Angular Universal → SSR migration guide](https://angular.dev/guide/ssr) — for teams upgrading from the older Universal package

## Demo source

Synthesized from real-world SSR debugging sessions rather than a single demo file. The six-bug taxonomy (window undefined, text mismatch, DOM mismatch, double fetch, third-party init, click-during-hydration) reflects the patterns that account for the majority of hydration issues in production Angular apps. The console-signature table is the recipe's practical shortcut — most teams don't know that NG05000 vs NG05001 vs NG05002 mean specific different things. All code is original.
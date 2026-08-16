---
recipe_id: "bundle-splitting-strategies"
description: "Lazy routes alone rarely shrink the initial bundle, because the weight usually sits in libraries the entry point still imports"
primary_concept: "tooling/ng-cli"
related_concepts: ["routing/lazy-loading", "components/components", "performance/performance-auditing"]
demo_repo: null
angular_baseline: "22.1.1"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Bundle Splitting: Beyond Lazy Routes

> **What you'll build:** a working bundle-splitting strategy that
> gets an 800KB initial bundle down to 150KB while keeping the app
> feeling fast — analysis workflow using esbuild-visualizer, four
> splitting patterns (route-based lazy loading, `@defer` blocks for
> below-the-fold, dynamic imports for heavy libraries used
> conditionally, network-aware preloading), the concrete fixes for
> the five most common bloat sources (moment.js, lodash, icon
> libraries, RxJS deep imports, Angular Material), and the
> debugging workflow for "why isn't this chunk actually being
> split?"
>
> **Concepts you'll touch:** Angular CLI / Tooling, [Lazy Loading](../../concepts/routing/lazy-loading.md), Components, [Performance Auditing](./performance-auditing.md)
>
> **Time:** ~30 minutes to read; ~1 day for a real bundle audit and
> the resulting refactors.

---

## The scenario

Your marketing homepage's Lighthouse LCP is 4.2 seconds. The bundle analyzer shows the initial JS at 812KB gzipped. Users on 4G leave before the page becomes interactive.

You've already done the obvious thing — lazy-loaded routes. `loadChildren` on every route except the home page. And yet the main bundle is still huge.

**The gap**: lazy routes only defer *route-specific code*. Everything shared — libraries, services, shared components — ends up in the main bundle by default. If your home page imports a chart library "just for the hero section," that library is in the main bundle. If a shared service uses moment.js, moment.js is in the main bundle. If your icon library isn't tree-shakeable, all icons are in the main bundle.

**The strategy**: analyze first (know what's actually there), then split at the right boundaries — routes for whole sections, `@defer` for below-the-fold, dynamic imports for conditional heavy libraries, network-aware preloading to hide the cost of subsequent loads. This recipe walks through the workflow.

---

## The v22 bundling model

Angular 17+ ships the `@angular/build:application` builder by default — it uses **esbuild** instead of Webpack, is ~5-10x faster to build, and has different bundle-splitting behavior worth understanding.

Check your `angular.json`:

```json
{
  "projects": {
    "my-app": {
      "architect": {
        "build": {
          "builder": "@angular/build:application",
          "options": {
            "outputPath": "dist/my-app",
            "browser": "src/main.ts"
          }
        }
      }
    }
  }
}
```

The old `@angular-devkit/build-angular:browser` (Webpack) still works, but new apps default to the esbuild-based builder. Some patterns work slightly differently between them — this recipe focuses on the modern one.

### What the builder does automatically

Even without explicit configuration:

- **Route lazy loading** (`loadComponent` / `loadChildren`) → separate chunks per lazy route
- **`@defer` blocks** → separate chunks per deferred component
- **Dynamic `import()`** → separate chunks per dynamic import
- **Vendor code** → automatically split from application code (in modern builder, mixed into per-chunk vendor extraction)

**What it does NOT do automatically**:

- Detect "this heavy library is only used on the reports page" — you have to structure the imports so it's clear
- Split shared services that are used in multiple lazy chunks (they go into main bundle to avoid duplication)
- Warn you that you're importing all of Lodash when you use one function

---

## Step 1 — analysis (the mandatory first step)

Build with stats:

```bash
ng build --configuration=production
# Stats are generated automatically in modern builder;
# for the older builder, add --stats-json
```

Visualize with esbuild-visualizer (works with modern builder):

```bash
npm install --save-dev esbuild-visualizer
npx esbuild-visualizer --metadata dist/my-app/stats.json --template treemap
```

Or for the Webpack-based builder:

```bash
ng build --configuration=production --stats-json
npx webpack-bundle-analyzer dist/my-app/stats.json
```

Both produce a treemap showing what's in each chunk. Look for:

- **Chunks larger than 100KB gzipped** — investigate whether their contents belong there
- **Duplicate dependencies** across chunks (e.g., moment.js in three lazy chunks that should share)
- **Small "leaf" dependencies pulled in via one function** (e.g., `date-fns/format` alone would be 5KB; importing all of `date-fns` pulls in 200KB)
- **Barrel files re-exporting entire libraries** — a common tree-shaking blocker

**Set specific size budgets in `angular.json`**:

```json
"budgets": [
  {
    "type": "initial",
    "maximumWarning": "500kB",
    "maximumError": "1MB"
  },
  {
    "type": "anyComponentStyle",
    "maximumWarning": "6kB"
  }
]
```

The `initial` bucket is what the browser downloads before the app becomes interactive. Setting a warning at 500KB means every PR that pushes past this gets flagged. Enforce during CI to prevent gradual bloat.

---

## Strategy 1 — route-based lazy loading

The foundation. Every route that isn't the home page (or a super-critical entry point) should be lazy:

```typescript
// File: app.routes.ts
import { Routes } from '@angular/router';

export const routes: Routes = [
  // Eager: in main bundle, loaded on initial page visit
  { path: '', component: HomeComponent },

  // Lazy standalone component: separate chunk
  {
    path: 'products/:id',
    loadComponent: () =>
      import('./products/product-detail.component').then(c => c.ProductDetailComponent),
  },

  // Lazy child routes: separate chunk with its own routing subtree
  {
    path: 'admin',
    loadChildren: () =>
      import('./admin/admin.routes').then(m => m.adminRoutes),
  },

  // Lazy with data resolver: resolver runs before the chunk is downloaded
  {
    path: 'reports/:id',
    loadComponent: () =>
      import('./reports/report.component').then(c => c.ReportComponent),
    resolve: {
      report: reportResolver,
    },
  },
];
```

**Three patterns worth absorbing:**

- **`loadComponent`** for a single standalone component. The v22 default; simpler than `loadChildren` for cases where you don't need nested routing.
- **`loadChildren`** for whole feature areas with their own routing. Admin sections, dashboards, wizard flows.
- **Data resolvers run before the chunk downloads** — the resolver's fetch happens in parallel with the chunk download, so both complete about the same time. Component renders immediately when both are ready.

### Nested lazy routes

For deep feature areas, lazy-load recursively:

```typescript
// File: admin/admin.routes.ts
export const adminRoutes: Routes = [
  { path: '', component: AdminDashboardComponent },
  {
    path: 'users',
    loadComponent: () => import('./users/users.component').then(c => c.UsersComponent),
  },
  {
    path: 'billing',
    loadChildren: () =>
      import('./billing/billing.routes').then(m => m.billingRoutes),
  },
];
```

Only downloading `AdminDashboardComponent` when the user visits `/admin`. Only downloading `UsersComponent` when they navigate to `/admin/users`. Bundle shrinks proportional to how much the user actually uses.

---

## Strategy 2 — `@defer` blocks for below-the-fold

`@defer` is the v17+ answer to "the top of the page is critical; the bottom isn't loaded until visible":

```html
<header>
  <h1>Welcome</h1>
  <nav>...</nav>
</header>

<main>
  <section class="hero">...critical above-the-fold content...</section>

  @defer (on viewport) {
    <app-testimonials />
  } @loading (minimum 500ms) {
    <div class="skeleton">Loading testimonials…</div>
  } @error {
    <p>Could not load testimonials</p>
  }

  @defer (on interaction; prefetch on hover) {
    <app-video-player [src]="videoUrl" />
  } @placeholder {
    <img [src]="videoPoster" alt="Play video" />
  }
</main>
```

**Six things worth absorbing:**

- **`on viewport`** — the block loads when the placeholder scrolls into view. Perfect for below-the-fold content.
- **`on interaction`** — waits for a user event (click, focus, keydown) on the placeholder. The video player only downloads when the user actually clicks Play.
- **`prefetch on hover`** — starts downloading when the mouse hovers, before the click. The click feels instant even though the actual load hadn't happened before.
- **`@placeholder`** shows before the trigger fires — a static preview or thumbnail. If the trigger requires user action, the placeholder is what the user sees.
- **`@loading (minimum 500ms)`** — once the trigger fires, show a loading state. `minimum 500ms` prevents flash if the network is fast; the loading UI shows for at least that long, so users perceive it as "loading" instead of "flicker."
- **`@error`** — fallback if the chunk fails to download.

### `@defer` triggers — the full menu

| Trigger | When | Best for |
| --- | --- | --- |
| `on idle` | Browser idle time | Nice-to-have below-fold content |
| `on viewport` | Placeholder scrolls into view | Content below the initial screen |
| `on interaction` | User event on placeholder | Videos, dialogs, complex widgets |
| `on hover` | Pointer hover on placeholder | Tooltips, dropdowns |
| `on timer(2s)` | After N seconds | Non-critical analytics, banners |
| `on immediate` | ASAP after bundle downloads | Effectively "normal" — not really deferred |
| `when expr` | When a boolean expression becomes true | Programmatic control |

Combined with `prefetch on X` for preloading before the actual trigger, this gives fine-grained control.

**Not the right tool for SSR-critical content** — content behind `@defer` triggers may not render server-side (unless `on immediate`). Search engine crawlers may not fire the trigger. If SEO matters, use a lazy route (the whole route is SSR-able) not `@defer`.

---

## Strategy 3 — dynamic library imports

Sometimes a heavy library is used only in specific situations — a chart on the dashboard, a rich text editor on the profile page, a PDF renderer for exports. Route-level lazy loading helps but only if the library isn't imported by other code paths too.

**The pattern**: import the library dynamically inside the code that actually uses it:

```typescript
// File: dashboard/dashboard.component.ts
import { Component, ElementRef, ViewChild, afterNextRender, inject, signal } from '@angular/core';

@Component({ /* … */ })
export class DashboardComponent {
  @ViewChild('chart') chartElement!: ElementRef<HTMLCanvasElement>;
  private chartInstance: unknown = null;
  readonly loading = signal(false);

  constructor() {
    afterNextRender(async () => {
      this.loading.set(true);

      // Dynamic import: the chart library becomes a separate chunk
      // that only downloads when this component runs
      const { Chart, registerables } = await import('chart.js');
      Chart.register(...registerables);

      this.chartInstance = new Chart(this.chartElement.nativeElement, {
        type: 'line',
        data: this.chartData,
        options: { /* … */ },
      });

      this.loading.set(false);
    });
  }
}
```

**Three things worth absorbing:**

- **`import('chart.js')` returns a Promise** — the browser downloads the library at this point, not at app bootstrap.
- **`afterNextRender` (v17+)** ensures the dynamic import doesn't fire during SSR (where the library likely uses `document` and would crash). Same pattern from the [SSR / hydration recipe](../ssr/ssr-hydration-deep-dive.md).
- **A separate chunk is emitted** for `chart.js`. On rebuild, esbuild recognizes the dynamic import and splits automatically.

### Dynamic imports for conditional features

For features that only some users need:

```typescript
async exportPdf(data: unknown) {
  // 400KB PDF library only downloads when the user clicks Export
  const jsPDF = (await import('jspdf')).default;
  const doc = new jsPDF();
  doc.text(JSON.stringify(data), 10, 10);
  doc.save('export.pdf');
}
```

The user who never clicks Export never downloads the PDF library. This is the "pay for what you use" pattern.

---

## Strategy 4 — network-aware preloading

Once you've lazy-loaded routes, subsequent navigation feels slower ("loading dashboard…"). Preloading fixes this: after the main bundle is done, download the lazy chunks in the background while the user reads the home page. When they click Dashboard, the chunk is already cached.

The trade-off: preloading uses bandwidth. On slow connections or metered mobile, it's harmful.

### Custom preload strategy — network-aware

```typescript
// File: preload/network-aware-preload.strategy.ts
import { Injectable } from '@angular/core';
import { PreloadingStrategy, Route } from '@angular/router';
import { EMPTY, Observable, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class NetworkAwarePreloadStrategy implements PreloadingStrategy {
  preload(route: Route, load: () => Observable<unknown>): Observable<unknown> {
    // Route explicitly opts out of preload
    if (route.data?.['preload'] === false) return EMPTY;

    // Check the Network Information API
    const connection = (navigator as any).connection;

    // Don't preload on slow/expensive connections
    if (connection) {
      if (connection.saveData) return EMPTY;
      if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
        return EMPTY;
      }
    }

    // Preload after a small delay so the initial page finishes loading first
    return timer(2000).pipe(switchMap(() => load()));
  }
}
```

Register in the router:

```typescript
// File: app.config.ts
import { provideRouter, withPreloading } from '@angular/router';
import { NetworkAwarePreloadStrategy } from './preload/network-aware-preload.strategy';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withPreloading(NetworkAwarePreloadStrategy)),
    // …
  ],
};
```

**Three things worth absorbing:**

- **`navigator.connection`** (Network Information API) tells you about the connection type. Not supported in all browsers (Safari at time of writing); the `if (connection)` guard handles the absent case.
- **`saveData`** flag is set when the user has enabled "Data Saver" in their browser. Respect it — this user is explicitly asking for less bandwidth usage.
- **`timer(2000)`** delays preloading until 2 seconds after route activation, giving the initial page time to fully load and become interactive before background downloads start.

This pattern is expanded on more thoroughly in the [preloading strategies recipe](../routing/preloading-strategy.md).

### `PreloadAllModules` — the easy option

For simpler needs, Angular ships with a built-in strategy:

```typescript
import { PreloadAllModules } from '@angular/router';

provideRouter(routes, withPreloading(PreloadAllModules)),
```

Downloads every lazy chunk after the initial route is stable. Aggressive; use only if your total bundle size is small or you don't care about mobile users. For most apps, the network-aware strategy above is better.

---

## Common bloat sources with concrete fixes

The five libraries that most commonly show up as unexpected bloat in bundle analyzers:

### Moment.js (~70KB gzipped)

**Symptom**: `node_modules/moment/moment.js` in your main bundle.

**Fix — replace with date-fns or Temporal**:

```typescript
// BEFORE (all of moment)
import moment from 'moment';
const formatted = moment(date).format('YYYY-MM-DD');

// AFTER (tree-shakeable date-fns; only pulls in what's used, ~2KB)
import { format } from 'date-fns';
const formatted = format(date, 'yyyy-MM-dd');
```

Or use the browser-native `Intl.DateTimeFormat`:

```typescript
const formatted = new Intl.DateTimeFormat('sv-SE').format(date);  // ISO-like output
```

Zero-cost when the browser already supports it.

**If migrating is too expensive**, at minimum use `moment/min/moment-with-locales-filter` or exclude unused locales via webpack ignore-plugin (Webpack builder only).

### Lodash full import

**Symptom**: `node_modules/lodash` at 25-70KB depending on how much is used.

**Fix — deep imports from `lodash-es`**:

```typescript
// BEFORE — pulls in all of Lodash
import _ from 'lodash';
_.debounce(fn, 300);

// AFTER — pulls in only debounce (~2KB)
import debounce from 'lodash-es/debounce';
debounce(fn, 300);
```

The `-es` suffix is important — it's the ESM build, tree-shakeable. Plain `lodash` is CommonJS and doesn't tree-shake well.

Or **use native alternatives**:
- `_.debounce` → RxJS `debounceTime` or a 5-line native implementation
- `_.throttle` → RxJS `throttleTime` or `requestAnimationFrame`
- `_.cloneDeep` → `structuredClone(obj)` (native, browser-supported)
- `_.isEqual` → JSON.stringify comparison (for simple cases) or a 20-line native
- `_.get` / `_.set` → optional chaining `?.` and nullish coalescing `??`

Most Lodash usage in modern codebases is redundant with native JS. Audit before assuming you need it.

### Icon libraries

**Symptom**: 200KB+ from `@fortawesome/fontawesome-free` or similar; you use ~10 icons.

**Fix — tree-shakeable icon imports**:

```typescript
// BEFORE — pulls in all Font Awesome
import '@fortawesome/fontawesome-free/js/all.min.js';

// AFTER — Angular-specific tree-shakeable icons
// Install: @fortawesome/angular-fontawesome + specific icon packages
import { FaIconLibrary, FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { faUser, faCog, faSignOut } from '@fortawesome/free-solid-svg-icons';

@Component({
  imports: [FontAwesomeModule],
  template: `<fa-icon [icon]="faUser" />`,
})
export class HeaderComponent {
  readonly faUser = faUser;
  readonly faCog = faCog;
}
```

Only the icons you explicitly import get bundled.

**For more control**, use `lucide-angular` or similar — modern, fully tree-shakeable icon libraries designed for the ESM era.

### RxJS deep imports

**Symptom**: bundle analyzer shows `rxjs/internal/...` deep-import paths.

**Fix — use the main entry**:

```typescript
// BEFORE — bypasses tree-shaking; may pull unrelated internal modules
import { Observable } from 'rxjs/internal/Observable';
import { map } from 'rxjs/internal/operators/map';

// AFTER — the main entry is properly tree-shakeable
import { Observable, map } from 'rxjs';
```

RxJS's main entry `rxjs` exports everything, but the ESM build tree-shakes correctly. `rxjs/internal/...` is not a public API and doesn't guarantee tree-shakability. If your imports look like this, someone was following outdated advice — fix them.

### Angular Material — module import bloat

**Symptom**: `@angular/material` at 300KB+ in main bundle even though you use 3 components.

**Fix — standalone component imports only what you use**:

```typescript
// BEFORE (module-based, pulls in more than needed if not careful)
import { MaterialModule } from './material.module';  // barrel importing 20 modules

// AFTER (v22 standalone imports)
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

@Component({
  imports: [MatButtonModule, MatCardModule],
  // ...
})
```

Each Material submodule is a separate npm subpath — treeshakeable by design. The bloat comes from barrel files (`material.module.ts` importing everything). Delete the barrel; import only what you use in each component.

### Barrel exports (`index.ts` re-exporting everything)

**Symptom**: importing one thing from a folder pulls in twenty.

**Fix — direct imports**:

```typescript
// BEFORE — pulls in everything the barrel exports
import { UserService } from './services';  // ./services/index.ts re-exports all

// AFTER — pulls in only UserService
import { UserService } from './services/user.service';
```

Modern bundlers can tree-shake barrels **if the barrel is `sideEffect: false` in its package.json and all imports are ESM**. In practice, this often fails silently. Direct imports are more predictable.

For monorepos with well-configured tree-shaking, barrels can work. For the general case, prefer direct imports in your app code (barrels are fine at library-package boundaries).

---

## Debugging — "why isn't this chunk being split?"

You set up `loadComponent` but the analyzer shows the component's code is still in the main bundle. Common causes:

### 1. Static import elsewhere

Somewhere in your codebase, a file imports the lazy component eagerly:

```typescript
// In some completely unrelated file:
import { DashboardComponent } from './dashboard/dashboard.component';
// Now DashboardComponent is ALWAYS in the main bundle,
// even though app.routes.ts uses loadComponent for it.
```

The bundler sees the static import and includes the code in whatever chunk the importing file lives in. The lazy load in `app.routes.ts` is redundant.

**Fix**: search the codebase for the static import; remove it. Common culprit is dev-only debug utilities that "just want to reference the type."

If the import is only for the type:

```typescript
// Types-only import doesn't affect bundling
import type { DashboardComponent } from './dashboard/dashboard.component';
```

The `import type` syntax is erased at compile time — no runtime import, no bundle inclusion.

### 2. Shared service pulling in the whole module

```typescript
// File: shared/user.service.ts
import { PermissionsHelper } from '../admin/permissions.helper';  // eager

@Injectable({ providedIn: 'root' })
export class UserService { /* uses PermissionsHelper */ }
```

`UserService` is used everywhere, so it's in the main bundle. It imports `PermissionsHelper`, so `PermissionsHelper` is in the main bundle. If `PermissionsHelper` is in the `admin/` folder and imports other admin files, the whole admin module ends up in main.

**Fix**: refactor so shared services don't depend on lazy-loaded modules. Move `PermissionsHelper` out of `admin/` if it's genuinely shared, or invert the dependency (admin depends on shared, not vice versa).

### 3. Barrel file with side effects

```typescript
// File: shared/index.ts
export * from './user.service';
export * from './admin/permissions.helper';  // ← pulls in admin transitively
```

Any file importing from `shared/` pulls in `admin/permissions.helper`, which pulls in more admin code, defeating the lazy load.

**Fix**: direct imports. Or restructure the barrel to only export truly-shared things.

### 4. Provider registered on a shared route

```typescript
// File: app.routes.ts
export const routes: Routes = [
  {
    path: '',
    providers: [AdminService],  // ← eager instantiation of admin service
    // ...
    children: [
      { path: 'admin', loadComponent: () => import('./admin/...') },
    ],
  },
];
```

`AdminService` is provided at the app level; it's instantiated eagerly. Its imports pull in admin code.

**Fix**: move providers into the lazy child's own configuration.

### 5. Detecting the issue proactively

The modern builder emits warnings when it detects lazy imports being defeated:

```text
Warning: 'AdminComponent' is dynamically imported by AppComponent, but also statically imported by SomeSharedFile.
Prefer only dynamic imports to enable code splitting.
```

If you see this warning during build, hunt down the static import path. The warning tells you which file to look at.

---

## Trade-offs and common pitfalls

**Use bundle splitting when:**

- Initial bundle exceeds 200KB gzipped for a marketing site or 500KB for an application
- Users are on mobile / slow networks (measure with WebPageTest)
- Lighthouse LCP > 2.5 seconds on your target device

**Skip aggressive splitting when:**

- The app is small and the entire bundle is < 100KB (splitting overhead exceeds savings)
- The app is behind a login (initial-render performance often matters less)
- The team can't maintain the discipline (lazy imports get accidentally converted to eager over time)

### Common pitfalls

- **Optimizing without measuring.** Same rule as [performance-auditing](./performance-auditing.md). Bundle analyzer first; assumptions second.
- **Splitting too aggressively.** Splitting every component into a separate chunk means many small HTTP requests, HTTP/2 negotiation overhead, and worse cache hit rates. Split at natural boundaries (routes, below-fold sections, conditional features).
- **Static imports defeating lazy loads.** Covered above. The single most common cause of "the chunk exists but is empty" is a static import somewhere.
- **`import type` vs `import`.** Non-type imports pull code into the bundle even if you only use the type. Use `import type` for type-only references.
- **Barrel exports without `sideEffect: false`.** If your monorepo uses barrels, ensure `package.json` has `"sideEffects": false` (or a specific list) so tree-shaking can work.
- **Testing in dev mode.** Dev builds don't tree-shake or minify. Bundle sizes are always higher than production. Test with `ng build --configuration=production` and serve with `http-server`.
- **Not using `import type`.** Modern TS best practice; erases at compile time; free bundle savings.
- **Preloading everything.** `PreloadAllModules` is the easy button but downloads code the user may never use, using their bandwidth. Prefer network-aware or explicit-per-route preload data.
- **Assuming Angular Material treeshakes automatically.** It does, but only if you import from specific subpaths (`@angular/material/button`, not `@angular/material`). Some Material features (theming utilities) always pull in more than you expect.
- **Deferred content that shouldn't be deferred.** SEO-critical content behind `@defer` may not render server-side. If content matters for search rankings, lazy-load the whole route, don't `@defer` inside a rendered route.
- **Signal-based components that use heavy libraries in `computed`.** A `computed()` that calls into `moment` runs during change detection cycles. Heavy libraries in tight loops kill performance. Import once, use, cache.
- **Old rxjs deep-import paths.** `import { Observable } from 'rxjs/Observable'` (v5 style) doesn't tree-shake in modern rxjs. Modernize to `import { Observable } from 'rxjs'`.

---

## See also

- [Performance Auditing](./performance-auditing.md) — LCP diagnosis (which drives the "why are we bundling") question
- [Preloading Strategies](../routing/preloading-strategy.md) — network-aware preloading in depth
- [Lazy Loading](../../concepts/routing/lazy-loading.md) — `loadComponent`, `loadChildren`, resolver patterns
- [SSR + Hydration](../ssr/ssr-hydration-deep-dive.md) — `@defer` and SSR interaction; `afterNextRender` for browser-only dynamic imports
- Angular CLI / Tooling — the `application` builder, build configurations
- [Signals](../../concepts/reactivity/signals.md) — the reactivity model that composes with lazy loading

## References

- [`@defer` block (angular.dev)](https://angular.dev/guide/templates/defer) — the deferred loading directive
- [Application builder (angular.dev)](https://angular.dev/tools/cli/build) — the modern esbuild-based builder
- [Bundle budgets (angular.dev)](https://angular.dev/reference/configs/workspace-config#configuring-size-budgets)
- [`PreloadingStrategy` (angular.dev)](https://angular.dev/api/router/PreloadingStrategy)
- [esbuild-visualizer](https://www.npmjs.com/package/esbuild-visualizer) — treemap for modern Angular builds
- [webpack-bundle-analyzer](https://www.npmjs.com/package/webpack-bundle-analyzer) — the classic analyzer for older builds
- [date-fns](https://date-fns.org/) — modern alternative to Moment.js
- [Network Information API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Network_Information_API) — the API behind network-aware preload

## Demo source

Synthesized from real-world Angular bundle-audit patterns rather than a single demo file. The five-bloat-source list (moment, lodash, icons, rxjs, Material) reflects the libraries that most consistently show up as unexpected bloat in production audits. The "why isn't this chunk being split?" debugging section is the recipe's practical contribution — most developers don't know that static imports elsewhere defeat lazy loading. All code is original.
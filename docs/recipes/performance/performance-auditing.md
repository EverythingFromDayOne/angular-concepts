---
recipe_id: "performance-auditing"
title: "Performance Auditing: \"The App Is Slow, Where Do I Look?\""
file: "recipes/performance/performance-auditing.md"
primary_concept: "components/change-detection"
related_concepts: ["reactivity/signals", "components/components", "routing/lazy-loading"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Performance Auditing: "The App Is Slow, Where Do I Look?"

> **What you'll build:** a working answer to the most common
> performance question — "the app feels slow, but where?" Five
> symptom-driven diagnostic paths (slow initial render, sluggish
> typing, janky scroll, slow clicks, memory growth), four tools
> with specific instructions for each, and the v22 change-detection
> mental model (Zone vs OnPush vs Signals vs Zoneless) you need to
> interpret what the tools show.
>
> **Concepts you'll touch:** [Change Detection](../../concepts/components/change-detection.md), [Signals](../../concepts/reactivity/signals.md), Components, [Lazy Loading](../../concepts/routing/lazy-loading.md)
>
> **Time:** ~30 minutes to read; ~half a day for a real audit
> against a production app.

---

## The scenario

A user reports: *"The app feels slow."*

You open the app. It loads in… 3 seconds? Maybe? Hard to tell. Scrolling through a long list feels fine. Typing in the search bar feels a bit laggy, but you're not sure if it's the network or the UI. The product owner is asking for "performance improvements" by next sprint.

The temptation is to start optimizing — switch components to `OnPush`, add `trackBy`, lazy-load some routes. **Don't.** Every optimization has a cost (more complex code, more places to make mistakes); blind optimization wastes the budget on things that don't matter and misses the things that do.

**The first rule is measure.** Pick a specific symptom (not "slow" — "the search bar lags when I type fast"), reproduce it under controlled conditions, profile it with the right tool, then fix what the profile actually shows.

This recipe is a flowchart from symptoms to tools to fixes, mapped to v22 idioms. It's not exhaustive — performance is a deep topic — but it covers the patterns that handle ~80% of real-world Angular performance bugs.

---

## The four tools (and when to use each)

| Tool | Best for | How to open |
| --- | --- | --- |
| **Angular DevTools** profiler | Change-detection cost, component-by-component breakdown | Chrome extension → Angular tab → Profiler |
| **Chrome Performance** | Frame-level performance, layout/paint, frame-rate drops | DevTools → Performance tab → Record |
| **Lighthouse** | Initial load metrics (LCP, FCP, TBT), accessibility, best-practices | DevTools → Lighthouse tab |
| **Bundle analyzer** | What's in your JS bundle, where the weight is | `ng build --stats-json && npx webpack-bundle-analyzer dist/stats.json` |

Each tool answers different questions. Using Lighthouse to diagnose janky scrolling is like using a thermometer to weigh yourself — wrong instrument.

### Angular DevTools profiler

The most important tool. Records change-detection runs and shows the time spent in each component. Steps:

1. Install the [Angular DevTools Chrome extension](https://chrome.google.com/webstore/detail/angular-devtools/ienfalfjdbdpebioblfackkekamfmbnh)
2. Open DevTools → **Angular** tab → **Profiler** sub-tab
3. Click **Record**
4. Reproduce the slow action (type in the search, click a button, scroll)
5. Click **Stop**
6. Inspect the bar chart — each bar is a change-detection cycle; height is total time

**What to look for:**

- **Bars taller than 16ms** (60 fps frame budget) on user interactions — frames being dropped
- **A specific component dominating** time — that's the optimization target
- **Many CD cycles for one user action** — Zone.js is over-triggering; consider signals or zoneless
- **Bars on actions that "shouldn't" cause CD** (e.g., scrolling) — something is over-eagerly subscribing

The profiler also has a **change detection cycle reason** display — it tells you *why* each cycle ran (input change, signal update, event, etc.). This is often the smoking gun.

### Chrome Performance tab

Lower-level than Angular DevTools — it sees browser layout, paint, GPU compositing, network. Use when you need to know about:

- Frame drops during scroll (look at the FPS meter at the top)
- Layout thrash (red bars in the rendering track)
- Forced reflows from JS reading layout properties
- Network bottlenecks during initial load

Steps:

1. Open DevTools → **Performance** tab
2. Click **Settings** (gear icon) → enable **CPU: 4× slowdown** (to simulate lower-end devices)
3. Click **Record**
4. Reproduce the slow action
5. Click **Stop**
6. Look at the **Main** track for long tasks (red triangles), check the **Frames** track for jank

Filter by category — flame chart can show only "Scripting" (your JS), only "Rendering" (layout/paint), only "System" (garbage collection, parsing). Often the actual cost is in Rendering, not Scripting — meaning the JS isn't slow, but it's triggering unnecessary layout work.

### Lighthouse

For initial-load metrics only. Run on a production build:

```bash
ng build --configuration=production
# Serve the production build:
npx http-server dist/your-app/browser -p 8080
# Open http://localhost:8080 in Chrome
# DevTools → Lighthouse → Analyze
```

Key metrics:

- **LCP (Largest Contentful Paint)** — when the main content is visible. Target < 2.5s.
- **FCP (First Contentful Paint)** — when anything paints. Target < 1.8s.
- **TBT (Total Blocking Time)** — how long the main thread was blocked. Target < 200ms.
- **CLS (Cumulative Layout Shift)** — how much content jumps around. Target < 0.1.

**Don't run Lighthouse on the dev server** (`ng serve`). Numbers will be wildly off — dev build is unminified, lacks tree-shaking, includes debugging assets. Always production build.

### Bundle analyzer

Tells you what's in the JS files the browser downloads. Useful when LCP is bad and you suspect bundle size:

```bash
ng build --configuration=production --stats-json
npx webpack-bundle-analyzer dist/your-app/stats.json
```

Or for the esbuild builder (v17+):

```bash
ng build --configuration=production
# Use the output's stats summary, or install:
npx esbuild-visualizer --metadata=dist/stats.json
```

What to look for:

- **Single large chunks** that should be split — large libraries in the main bundle that aren't needed on first paint
- **Duplicate dependencies** — moment.js included by both your app and a transitive dep
- **Unused exports** — code that's bundled but never reached (rare with modern bundlers but worth checking)

---

## The change-detection mental model

To interpret what the profiler shows, you need a model of when Angular re-renders. The model has changed significantly across v16-v18; here's the v22 view:

### Default (Zone.js + traditional CD)

Zone.js patches every async browser API — `setTimeout`, `Promise`, `addEventListener`, `XMLHttpRequest`, etc. When any patched API fires, Zone.js notifies Angular, which runs change detection on **every component in the tree**.

```text
User clicks button
        ▼
Zone.js sees the click event
        ▼
Notifies Angular
        ▼
Change detection runs on:
  AppComponent → checks bindings
    HeaderComponent → checks bindings
    NavbarComponent → checks bindings
    ...
    DeeplyNestedComponent#1 → checks bindings
    DeeplyNestedComponent#2 → checks bindings
    ... (every component, every binding)
```

The cost scales with the size of the component tree. Most CD runs do nothing visible — they re-check bindings that haven't changed. Old apps with 500+ components routinely spend 10–50ms per click on CD alone.

### OnPush (`ChangeDetectionStrategy.OnPush`)

A component with `OnPush` is **skipped during CD** unless one of the following triggers:

- An `@Input()` reference changes (note: reference, not value — mutating an array doesn't trigger)
- An event handler on the component fires
- A `signal()` read by the template updates
- An async pipe emits in the template
- The component or an ancestor is explicitly marked for check

Adding `OnPush` to a leaf component is a big win — Zone-triggered CDs no longer touch it. The component re-renders only when something it cares about changes.

```typescript
@Component({
  selector: 'app-deeply-nested',
  changeDetection: ChangeDetectionStrategy.OnPush,
  // …
})
export class DeeplyNestedComponent { /* … */ }
```

`OnPush` is now the **recommended default** for all components in v22 — even the Angular team's example code uses it routinely.

### Signal-based components

When a component's template reads a `signal()`, Angular tracks the dependency. Updates to that signal mark just that component dirty — not the whole tree.

```typescript
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div>{{ count() }}</div>`,
})
export class CounterComponent {
  readonly count = signal(0);
}
```

When `count.set(5)` runs, only `CounterComponent`'s view re-renders. No other component in the tree is touched. This is the **fine-grained reactivity** model — the same idea behind Solid.js, Svelte's runes, Vue 3 refs.

### Zoneless (v18+, currently `provideExperimentalZonelessChangeDetection()`)

Opt out of Zone.js entirely. Zone.js stops patching APIs; nothing triggers CD automatically. The only triggers are:

- Signal updates (read by templates)
- Event listeners (from `(click)`, etc.)
- Explicit `ChangeDetectorRef.markForCheck()`
- Async pipes
- `setInput()` on a component reference

```typescript
// File: main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, {
  providers: [
    provideExperimentalZonelessChangeDetection(),
    // …other providers
  ],
});
```

**No more app-wide CD on every `setTimeout`.** The performance gains are significant; the cost is that any third-party library that assumed Zone.js will trigger CD (e.g., a non-signal-aware data store) will silently fail to update the UI. Migration is per-app — not all apps are ready, hence "experimental."

### Putting it together

| Strategy | CD trigger | Granularity |
| --- | --- | --- |
| Zone.js + default CD | Every patched async API | Full tree |
| Zone.js + OnPush | Patched async + inputs changed / events / signals on the component | Subtree of dirty components |
| Zone.js + signals | Patched async + signal updates | Per-component (where signal is read) |
| Zoneless + signals | Signal updates + events + explicit markForCheck | Per-component, no implicit triggers |

The progression is one of decreasing implicit work. The v22 "best practice" stack is: **standalone components + OnPush + signals + (ideally) zoneless.**

---

## Symptom 1 — slow initial render (LCP > 2.5s)

**What the user sees**: the page loads, they wait a few seconds, eventually things appear.

**Diagnose with**: Lighthouse (LCP, TBT), Chrome Performance (Network track), bundle analyzer.

**Common causes and fixes:**

### Large initial bundle

The main JS chunk is too big; the browser spends seconds parsing and executing before anything paints.

**Fix 1 — lazy-load routes**:

```typescript
// File: app.routes.ts
export const routes: Routes = [
  { path: '', component: HomeComponent },
  {
    path: 'admin',
    loadChildren: () => import('./admin/admin.routes').then(m => m.adminRoutes),
  },
  {
    path: 'reports',
    loadComponent: () => import('./reports/reports.component').then(c => c.ReportsComponent),
  },
];
```

The admin section's code isn't downloaded until the user navigates there. The initial bundle stays small. For most apps, this is the highest-impact single fix.

**Fix 2 — `@defer` for below-the-fold content**:

```html
<header>...</header>
<main>...above-the-fold content...</main>

@defer (on viewport) {
  <app-recommendations />
}
```

`@defer` defines a deferred block — its component isn't downloaded until the trigger condition fires (in this case, "when the section scrolls into view"). Other triggers: `on idle`, `on interaction`, `on hover`, `on timer(2s)`.

**Fix 3 — audit dependencies**:

Run the bundle analyzer. Common culprits:

- **Moment.js (~70KB gzipped)** — replace with `date-fns` (tree-shakeable, ~5KB for typical usage) or native `Intl.DateTimeFormat`
- **Lodash full import** — `import _ from 'lodash'` pulls all of Lodash; use `import debounce from 'lodash-es/debounce'` or just write the function
- **Large icon libraries** — switch to individual SVG imports or a tree-shakeable library like `lucide-angular`
- **Polyfills you don't need** — check `tsconfig` `target` and remove polyfills for already-supported browsers

### Slow critical path

The initial bundle is fine, but the browser is waiting for something (CSS, fonts, API calls) before painting.

**Fix — render-blocking resources**:

- **CSS**: inline critical CSS into the HTML; load non-critical CSS async (`media="print"` then JS-flip to `media="all"`)
- **Fonts**: `font-display: swap` — browser uses a fallback font while the custom font loads
- **Images**: above-the-fold images should be preloaded; below-the-fold should be `loading="lazy"`

### No SSR for SEO/social-share critical pages

If the page is publicly indexable, server-side rendering with hydration paints the HTML before the JS even arrives. For consumer-facing apps, this is often essential. Angular's hydration via `provideClientHydration()` makes this relatively low-effort:

```typescript
// File: app.config.ts
import { provideClientHydration } from '@angular/platform-browser';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(),
    // …
  ],
};
```

(SSR setup is itself a larger topic — see the SSR concept article.)

---

## Symptom 2 — sluggish typing in forms or search

**What the user sees**: they type fast, the input feels laggy, characters appear with delay.

**Diagnose with**: Angular DevTools profiler.

Record the profiler while typing. You'll see CD cycles firing on every keystroke. If those cycles are taking >16ms, the UI can't keep up with input.

**Common causes and fixes:**

### Default CD on a large tree

Every keystroke triggers Zone.js, which triggers CD on every component in the app. Even at 1ms per component, 50 components × 50 keystrokes per second = 2500ms/s of CD overhead.

**Fix — switch to OnPush + signals**:

```typescript
// BEFORE: zone-triggered CD on every keystroke runs through the whole app
@Component({
  template: `<input [(ngModel)]="search" /> <span>{{ results.length }}</span>`,
})
export class SearchComponent {
  search = '';
  results: Result[] = [];
}

// AFTER: only this component is dirty on each keystroke;
// sibling components don't re-check
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<input [(ngModel)]="search" /> <span>{{ results().length }}</span>`,
})
export class SearchComponent {
  readonly search = signal('');
  readonly results = signal<Result[]>([]);
}
```

`OnPush` alone helps significantly. Combined with signals, the rest of the app is fully insulated from typing.

### Expensive work in event handlers

The input's `keyup` handler does heavy work synchronously — running a complex filter on a large list, recomputing aggregates.

**Fix — move work into `computed()`**:

```typescript
@Component({ /* … */ })
export class SearchComponent {
  readonly search = signal('');
  readonly allItems = signal<Item[]>([]);

  // Computed: re-runs only when its inputs change; memoizes the result.
  readonly filteredItems = computed(() => {
    const term = this.search().toLowerCase();
    return this.allItems().filter(item =>
      item.name.toLowerCase().includes(term)
    );
  });
}
```

`computed()` re-runs only when `search` or `allItems` change. Reading `filteredItems()` 5 times in a template costs nothing — it returns the memoized result.

### Subscriptions re-firing for unrelated changes

A long-running `valueChanges.subscribe` that does heavy work on every emission. Even with `OnPush`, the work itself blocks the main thread.

**Fix — debounce + distinctUntilChanged**:

```typescript
this.form.controls.search.valueChanges.pipe(
  debounceTime(300),
  distinctUntilChanged(),
  switchMap(term => this.http.get('/api/search?q=' + term)),
  takeUntilDestroyed(),
).subscribe(/* … */);
```

Covered in detail in the [Search Engine recipe](../form-and-search/search-engine.md). The keystroke-by-keystroke firing becomes a per-stable-input firing.

---

## Symptom 3 — janky scroll (FPS drops < 30)

**What the user sees**: scrolling stutters, especially on long lists or pages with many elements.

**Diagnose with**: Chrome Performance tab → look at the FPS meter at the top.

A smooth 60 FPS is 16.67 ms/frame. If frames are taking >33ms, FPS drops below 30, scrolling feels janky.

**Common causes and fixes:**

### Too many DOM nodes

The page renders thousands of nodes; the browser can't lay them out fast enough during scroll.

**Fix — virtual scrolling** (see the [Virtual Scrolling recipe](../components/virtual-scrolling.md) for the full pattern):

```html
<cdk-virtual-scroll-viewport itemSize="60" class="viewport">
  <div *cdkVirtualFor="let item of items(); trackBy: trackById">
    {{ item.name }}
  </div>
</cdk-virtual-scroll-viewport>
```

Only ~20 items render at once instead of all 10,000. The browser has much less to lay out.

### Scroll handler doing heavy work

A `(scroll)` handler that reads layout properties, computes derived state, or triggers re-renders on every scroll event.

**Fix — throttle and avoid layout reads**:

```typescript
import { fromEvent, throttleTime } from 'rxjs';

constructor() {
  fromEvent(window, 'scroll').pipe(
    throttleTime(16),  // max once per frame
    takeUntilDestroyed(),
  ).subscribe(() => {
    // Use requestAnimationFrame for any DOM reads
    requestAnimationFrame(() => {
      // It's safe to read offsetWidth/scrollTop here;
      // the browser has already done layout for this frame
    });
  });
}
```

Don't read layout properties (`offsetWidth`, `getBoundingClientRect()`, etc.) in the scroll handler synchronously — they force the browser to flush pending layouts, causing "layout thrash."

### CSS containment helps

For complex item layouts, `contain` lets the browser optimize:

```css
.list-item {
  contain: layout style;
}
```

Tells the browser "changes inside this element can't affect anything outside it." Layout for one item no longer triggers layout of the entire list.

### `track` semantics on `@for`

Already covered in dynamic-forms and virtual-scrolling — `track item.id` instead of default index tracking is the difference between buttery scroll and stuttery scroll when the data updates.

---

## Symptom 4 — slow click → action

**What the user sees**: they click a button; there's a perceptible delay before the UI responds.

Even 100ms feels slow on click; 200ms feels broken.

**Diagnose with**: Chrome Performance, recording during the click.

Look for:
- Long tasks (>50ms continuous JS execution) in the Main track immediately after the click event
- Garbage collection pauses
- Long synchronous computations

**Common causes and fixes:**

### Heavy work synchronously in the handler

```typescript
// BEFORE: blocks main thread for 200ms doing serialization
onSave() {
  const serialized = JSON.stringify(this.largeObject);  // 100ms+ for huge objects
  this.localStorage.setItem('saved', serialized);       // synchronous I/O
  this.recomputeDerivedState();                          // 50ms+ if expensive
  this.router.navigate(['/next']);
}

// AFTER: defer non-blocking work; navigate first
onSave() {
  this.router.navigate(['/next']);  // navigate immediately — feels instant

  setTimeout(() => {
    // Heavy work happens after the navigation transition starts
    const serialized = JSON.stringify(this.largeObject);
    this.localStorage.setItem('saved', serialized);
    this.recomputeDerivedState();
  }, 0);
}
```

The `setTimeout(fn, 0)` defers the work to the next event loop tick, after the browser has had a chance to paint the response to the click.

### Optimistic UI

For network-bound clicks (Like, save, etc.), the [Optimistic Updates recipe](../form-and-search/optimistic-updates.md) reduces perceived latency to zero. The UI flips immediately; the HTTP call fires in the background; rollback on failure.

### Use `afterNextRender` for post-render work

If the work needs the new state to be rendered first (measuring a newly-shown element, scrolling to a position):

```typescript
import { afterNextRender, inject, DestroyRef } from '@angular/core';

@Component({ /* … */ })
export class ResultsComponent {
  private readonly destroyRef = inject(DestroyRef);

  onSearch() {
    this.results.set(/* … */);

    afterNextRender(() => {
      // Runs after the new results are in the DOM
      const list = document.querySelector('.results');
      list?.scrollTo({ top: 0 });
    });
  }
}
```

`afterNextRender` is v17+. It's preferred over `setTimeout` for DOM-dependent post-render work because it integrates with the change-detection lifecycle properly.

---

## Symptom 5 — memory growth over time

**What the user sees**: app is fine after first opening, but after 30 minutes of use, scrolling becomes janky, switching tabs is slow, the tab itself starts to drag.

**Diagnose with**: Chrome DevTools → Memory tab → Heap snapshot.

Take a snapshot. Use the app for 5 minutes. Take another snapshot. Compare:

- **Detached DOM nodes** — DOM elements held in JS memory after being removed from the document. Often subscription leaks.
- **Growing array sizes** — caches that never evict.
- **Listener counts** — event listeners added but never removed.

**Common causes and fixes:**

### Subscription leaks

The single most common cause. A subscription in a component lacks `takeUntilDestroyed()`; the component is destroyed; the subscription stays alive; references it holds are pinned in memory.

**Fix — universal `takeUntilDestroyed()` rule**:

```typescript
@Component({ /* … */ })
export class MyComponent {
  constructor() {
    someService.events$.pipe(
      takeUntilDestroyed(),
    ).subscribe(/* … */);
  }
}
```

Covered in the [takeUntilDestroyed recipe](../reactivity/take-until-destroyed.md). The rule is uniform: every Observable subscription in a component or directive gets `takeUntilDestroyed()`. No exceptions.

### Unbounded caches

A service holds a `Map<string, Data>` that grows without limit.

**Fix — TTL or LRU**:

The [Request Deduplication recipe](../http/request-deduplication.md) covers TTL eviction. For LRU, the pattern is: track access order, evict the least recently used when size exceeds the cap.

```typescript
class BoundedCache<K, V> {
  private readonly map = new Map<K, V>();
  constructor(private readonly maxSize = 100) {}

  set(key: K, value: V): void {
    // Move to most-recently-used by re-inserting
    this.map.delete(key);
    this.map.set(key, value);

    // Evict oldest if over capacity
    if (this.map.size > this.maxSize) {
      const oldest = this.map.keys().next().value;
      this.map.delete(oldest);
    }
  }

  get(key: K): V | undefined {
    return this.map.get(key);
  }
}
```

`Map`'s iteration order is insertion order, so `keys().next().value` is the oldest entry. Get/set both touch order, so frequently-used keys stay alive.

### Singleton services accumulating per-instance state

A service `providedIn: 'root'` holds state that should be per-component-instance. Each component navigation adds to the state; it never cleans up.

**Fix — subtree-scoped services** (covered in the [Component Communication recipe](../components/component-communication.md) Pattern 4). Provide the service on the component instead of root; it's destroyed when the component is destroyed.

### Closures pinning DOM

A `setTimeout` or RxJS subscription captures `this` or DOM references. Even if the component is destroyed, the timer's callback (and everything it captures) is pinned.

**Fix — always use `takeUntilDestroyed` or explicit cleanup**:

For setTimeout:

```typescript
private timer?: ReturnType<typeof setTimeout>;

ngOnInit() {
  this.timer = setTimeout(/* … */, 5000);
}

ngOnDestroy() {
  if (this.timer) clearTimeout(this.timer);
}
```

Or wrap in an RxJS timer that takeUntilDestroyed can clean up:

```typescript
timer(5000).pipe(takeUntilDestroyed()).subscribe(/* … */);
```

The second form is shorter and follows the universal rule.

---

## The decision tree

```text
                    "What's the symptom?"
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
"Slow to first paint"  "Sluggish typing"  "Janky scroll"
   (LCP > 2.5s)        (input lag)        (FPS < 30)
        │                   │                   │
        ▼                   ▼                   ▼
    Lighthouse        Angular DevTools     Chrome Performance
        │                   │                   │
    Bundle big?         OnPush + signals      Virtual scroll
    Slow network?      computed() for         CSS containment
    No code splitting? heavy derivations      Scroll throttle
        │                   │                   │
    Add lazy routes;   Move work to           See virtual-scrolling
    audit deps;        @defer or              recipe
    add @defer         setTimeout
                            │
                  ┌─────────┴─────────┐
                  │                   │
            "Click → action lag"  "Memory growth"
                  │                   │
                  ▼                   ▼
        Chrome Performance      Chrome Memory tab
                  │                   │
        Heavy work in handler?  Subscription leaks?
        Synchronous I/O?        Unbounded cache?
                  │                   │
            Defer work;         takeUntilDestroyed;
            optimistic UI;      LRU caps;
            afterNextRender     subtree-scoped
                                services
```

---

## Trade-offs and common pitfalls

**Use this audit process when:**

- A user reports specific slowness (don't audit blindly — wait for evidence)
- Lighthouse score drops noticeably between releases (you have a regression)
- The app is reaching a scale where casual fixes aren't enough (10K+ active items, 50+ component tree depth, etc.)

**Skip aggressive optimization when:**

- The app is small and feels fine on target devices
- The user complaint is "looks slow" but profiling shows the actual times are sub-200ms (it's a UX issue, not a performance issue — add a loading indicator)
- The cost of complexity outweighs the gain (over-using OnPush in places it doesn't help)

### Common pitfalls

- **Optimizing without measuring.** "I'll switch this component to OnPush just in case." It might help, might hurt (OnPush + non-immutable updates cause subtle bugs), might be irrelevant. Profile first; the data tells you what to fix.
- **Measuring on dev builds.** Dev builds are 2-10× slower than production. Always run Lighthouse and bundle audits on production builds.
- **Switching to OnPush without immutable updates.** OnPush only re-renders when input *references* change. Mutating `this.items.push(x)` instead of `this.items = [...this.items, x]` means the input reference is the same, no re-render, broken UI.
- **Reaching for zoneless before being ready.** Third-party libraries (some date pickers, some chart libs, some i18n libraries) assume Zone.js. Zoneless breaks them silently. Migrate carefully; check every dep.
- **Adding `trackBy` only to one `@for` and forgetting the others.** Track functions are per-`@for`; one optimized loop next to ten un-optimized ones doesn't help much.
- **Heavy `computed()` chains.** Each `computed()` runs on every read of its dependencies. If A is read by B is read by C, updating A triggers all three computations. Profile the chain; for very expensive derivations, cache results explicitly.
- **`requestIdleCallback` instead of `requestAnimationFrame` for visual work.** `requestIdleCallback` is fine for non-visual work; for anything that affects the screen, use `requestAnimationFrame`.
- **Reading `localStorage` synchronously on app start.** `localStorage` access is fast in the steady state but slow on cold start (the browser has to read from disk). Defer non-critical reads.
- **Production audit on cached resources.** First Lighthouse run loads everything fresh; second run uses cached resources. Always run in incognito or clear cache for accurate "new user" metrics.
- **Bundle analyzer noise.** A 1MB bundle isn't necessarily bad if 800KB of it is lazy-loaded chunks. Look at *initial bundle* size, not total. The analyzer's chunk colors help — focus on the green/blue "main" chunks.
- **Confusing TBT with TTI.** Total Blocking Time measures main-thread blocking; Time To Interactive measures when the page is fully responsive. They're related but different. TBT is usually the more actionable metric.
- **Excessive memo / OnPush / change detection wrangling.** Some apps over-optimize and end up with complex `markForCheck` chains that are themselves bugs. Modern v22 advice: use signals for state; signals + OnPush handle 99% of cases without manual CD wrangling.

---

## See also

- [Virtual Scrolling](../components/virtual-scrolling.md) — for janky-scroll cases with large lists
- [takeUntilDestroyed](../reactivity/take-until-destroyed.md) — the memory-leak prevention rule
- [Optimistic Updates](../form-and-search/optimistic-updates.md) — for perceived-latency improvements on user actions
- [Request Deduplication](../http/request-deduplication.md) — for "5 components fetch the same URL" performance bugs
- [Search Engine](../form-and-search/search-engine.md) — for the debounce + switchMap pattern for typing-triggered work
- [Change Detection](../../concepts/components/change-detection.md) — the concept article with deeper coverage of OnPush, Zone.js, and zoneless internals
- [Signals](../../concepts/reactivity/signals.md) — the underlying reactivity model
- [Lazy Loading](../../concepts/routing/lazy-loading.md) — `loadChildren`, `loadComponent`, preload strategies

## References

- [Angular DevTools (chrome web store)](https://chrome.google.com/webstore/detail/angular-devtools/ienfalfjdbdpebioblfackkekamfmbnh) — the profiler extension
- [Chrome Performance Insights (web.dev)](https://web.dev/articles/performance-insights) — the modern Chrome performance tooling
- [Core Web Vitals (web.dev)](https://web.dev/articles/vitals) — LCP, INP, CLS metrics canonical reference
- [`provideExperimentalZonelessChangeDetection` (angular.dev)](https://angular.dev/api/core/provideExperimentalZonelessChangeDetection) — the zoneless API
- [`@defer` block (angular.dev)](https://angular.dev/guide/templates/defer) — deferred loading syntax
- [`afterNextRender` (angular.dev)](https://angular.dev/api/core/afterNextRender) — post-render hook
- [Angular performance checklist (Minko Gechev)](https://github.com/mgechev/angular-performance-checklist) — community-maintained reference

## Demo source

Synthesized from common production performance-audit patterns rather than a single demo file. The symptom-driven structure (start with what the user observes, not with optimization techniques) reflects the workflow most senior Angular developers actually follow. The Zone → OnPush → Signals → Zoneless mental model is the v22 framing that makes performance choices interpretable rather than mystical. All code is original.
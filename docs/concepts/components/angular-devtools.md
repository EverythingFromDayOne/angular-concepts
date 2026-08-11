---
roadmap_node: "angular-devtools"
title: "Angular DevTools"
file: "components/angular-devtools.md"
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

# Angular DevTools

> **Lead with this:** Angular DevTools is the official browser extension that
> lets you inspect your component tree, profile change detection, trace your
> DI hierarchy, and visualize your router config — all without leaving the
> browser.

## What it is

Angular DevTools is an official browser extension developed by the Angular team
that adds an "Angular" tab to your browser's developer tools. It works in both
Chrome (and Chromium-based browsers) and Firefox.

It has four main tabs, each targeting a different debugging concern:

| Tab | What it does |
| --- | --- |
| **Components** | Inspect the component and directive tree, view and edit inputs/outputs, navigate to source |
| **Profiler** | Record and visualize change detection cycles; identify slow components |
| **Injector Tree** | Browse the environment and element injector hierarchy |
| **Router Tree** | Visualize your app's routing configuration |

> **Important:** Angular DevTools only works with apps running in **development
> mode** — that is, built without the `optimization` flag
> (`optimization: false`). It will show "Angular application not detected" on
> production builds.

## Basic usage

### Installation

Install from the official stores:

- **Chrome / Chromium:** [Chrome Web Store](https://chrome.google.com/webstore/detail/angular-developer-tools/ienfalfjdbdpebioblfackkekamfmbnh)
- **Firefox:** [Firefox Add-ons](https://addons.mozilla.org/firefox/addon/angular-devtools/)

Open browser DevTools with `F12` (Windows/Linux) or `Cmd+Option+I` (Mac). Once
your Angular app is running in dev mode, you'll see the **Angular** tab appear.

> **Tip:** The Angular tab does not appear on Chrome's new tab page because
> extensions don't run there. Navigate to any other page first.

### Components tab

The Components tab shows the full component and directive tree of your running
app. Clicking any node in the tree shows its properties, inputs, outputs, and
metadata in the right panel.

**Key things you can do here:**

**Inspect and live-edit component state.** Click a component in the tree and
you'll see all its properties on the right. You can edit values directly in the
panel — Angular re-renders immediately, no code change needed. This is useful
for testing how a component responds to different input values.

**Inspect directives on any element.** The tree includes not just components
but the directives applied to each element. Click any element to see which
directives are active on it.

**Inspect `@defer` block state.** `@defer` blocks appear as nodes in the tree.
Clicking one shows its configured triggers (defer triggers, prefetch triggers,
hydrate triggers), the optional blocks defined (`@loading`, `@placeholder`,
`@error`), and timing options (`minimum`, `after`).

**Hydration status.** When SSR with hydration is enabled, each component shows
whether it has been hydrated or not, with an error message if hydration failed.

**Navigate to source.** Select a component and click the icon in the top-right
of the properties panel to jump directly to its source file in the browser's
Sources (Chrome) or Debugger (Firefox) tab.

**Inspect element in DOM.** Double-click any component in the tree to jump to
its host element in the browser's Elements / Inspector tab.

**Inspect a specific element on the page.** Click the inspect icon (top-left of
the Components tab) and hover over any element on the page — DevTools
highlights the corresponding component in the tree.

### Profiler tab

The Profiler records change detection activity while you interact with your app,
then visualizes it so you can pinpoint performance bottlenecks.

**How to use it:**

1. Click the **record** button (circle, top-left of the Profiler tab) to start.
2. Interact with your app — click buttons, type in inputs, navigate between
   routes. Each interaction that triggers change detection will be captured.
3. Click the record button again to stop.

**What you see after recording:**

A sequence of bars along the top — each bar is one change detection cycle. The
taller the bar, the longer that cycle took. Clicking a bar shows two views:

**Bar chart view** — lists every component and directive checked in that cycle
and how long each one took. Sort by time to find the slowest component.

**Flame graph view** — shows the component tree as a heat map. The more intense
the color of a tile, the more time Angular spent there relative to the slowest
component in that cycle. Double-click any tile to zoom in on its children.

A useful checkbox: **"Change detection"** — when ticked, the flame graph only
shows components that actually ran change detection in that cycle, filtering out
`OnPush` components that were skipped. This makes it easier to see where the
real work is happening.

You can **save a profile** as a JSON file and share it — useful for reporting
performance issues or reviewing recordings async with a teammate.

### Injector Tree tab

The Injector Tree tab (Angular v17+) visualizes your app's entire DI hierarchy
as two trees side by side:

- **Environment injector tree** — the chain from the root environment injector
  down through any router-created environment injectors (lazy-loaded routes each
  get their own)
- **Element injector tree** — the per-component injector chain, from the root
  component down through the tree

Click any injector node to highlight the resolution path Angular would take to
satisfy a dependency from that injector — from the clicked injector up through
environment injectors to the root. This makes it immediately clear why a service
is or isn't receiving the instance you expect.

### Router Tree tab

The Router Tree tab renders your full routing configuration as a tree, showing
every defined route, its path, the component it maps to, and any child routes.
Useful for auditing large routing configs or verifying that lazy-loaded routes
are wired up correctly.

### Chrome Performance panel integration (v20+)

Starting with Angular v20, Angular integrates directly with Chrome's built-in
Performance panel. Angular-specific events — component rendering, change
detection cycles, event listener execution — appear as annotated entries in the
same timeline as other browser performance metrics.

This means you can correlate an Angular change detection cycle directly with
network requests, paint events, and JavaScript execution in one view, without
switching between tools. This integration is available in Chromium-based
browsers only.

To use it: open Chrome DevTools → Performance tab → record as normal. Angular
events appear in the timeline automatically when DevTools is installed.

## Real-world patterns

### Pattern 1 — Finding an unexpectedly slow component

You notice a button click feels sluggish. Open the Profiler, record a few
clicks, then stop.

Look at the bar chart for the tallest bars — those are the longest change
detection cycles. Click one. In the flame graph, look for the most intensely
colored tile. That component is taking the most time relative to everything else
in that cycle. Click through to its source. Common findings: a heavy `ngOnChanges`
recomputing unnecessarily, a pure pipe that isn't actually pure, or an `OnPush`
component that somehow keeps getting checked.

### Pattern 2 — Diagnosing a wrong service instance

You injected `UserService` but it has different state than you expected —
probably because it's not the same instance you think it is. Open the Injector
Tree tab. Find the component in the element tree. Click it. The highlighted path
shows which injector is providing `UserService` to it. If a component-level
provider is intercepting the resolution before it reaches the root, you'll see
it immediately.

### Pattern 3 — Verifying OnPush components skip correctly

You added `OnPush` to a component to reduce change detection overhead. But you
want to confirm it's actually being skipped. Open the Profiler, record an
interaction that shouldn't affect that component. Open the flame graph for that
cycle and tick the **"Change detection"** checkbox. If the component doesn't
appear in the filtered view, it was correctly skipped.

## Common mistakes

### Mistake 1 — Opening DevTools on a production build

Production builds have optimization enabled, which removes the Angular debug
API that DevTools relies on. You'll see "Angular application not detected":

```bash
# ❌ Production build — DevTools shows "Angular application not detected"
ng build  # optimization: true by default

# ✅ Development build — DevTools works
ng serve             # always serves in dev mode
ng build --configuration development
```

If you need to profile a production-like build locally, use
`ng build --configuration development` — it disables optimization but still
goes through the full build pipeline.

### Mistake 2 — Misreading the flame graph color intensity

The flame graph colors are **relative to the current cycle** — the most
expensive component in that cycle gets the most intense color, and everything
else scales from there. A dark tile does not mean the component is slow in
absolute terms — it means it was slow *relative to everything else in that one
cycle*. Always check the actual millisecond values in the bar chart panel on
the right before drawing conclusions.

### Mistake 3 — Profiling with DevTools open constantly during development

Angular DevTools adds some overhead when it's actively watching the component
tree. For normal development, this is negligible. But if you're trying to
measure precise timings, close DevTools during your app interaction and only
open it to review a recording — or use the Chrome Performance panel integration
which has lower overhead (it uses `console.timeStamp` internally).

## How this evolved

> - **2016–2021:** [Augury](https://augury.rangle.io/) was the community-built
>   Angular debugging extension. It was the standard tool but was developed
>   independently, lagged behind Angular releases, and is no longer maintained.
>
> - **Angular 12 (2021):** Angular DevTools launched as the official replacement
>   for Augury. Shipped with the Component and Profiler tabs. Built and
>   maintained directly by the Angular team.
>
> - **Angular 17 (2023):** Injector Tree tab added — letting developers visualize
>   the full DI hierarchy for the first time. Essential for debugging
>   `providedIn` scope issues and multi-level injector chains.
>
> - **Angular 18 (2024):** Debugging support for apps inside iframes. `@defer`
>   block state and triggers visible in the Components tab.
>
> - **Angular 20 (2025):** Router Tree tab added. Chrome Performance panel
>   integration launched — Angular-specific events appear directly in Chrome's
>   built-in Performance timeline. Signal debugging UI completed.
>
> - **Angular 22 (now):** Four stable tabs: Components, Profiler, Injector Tree,
>   Router Tree. Chrome Performance panel integration is the recommended
>   profiling approach for Chromium users. Augury is fully retired.

## See also

- [Dependency Injection](../dependency-injection/dependency-injection.md) —
  understanding the injector hierarchy that the Injector Tree tab visualizes
- [Change Detection](../components/change-detection.md) — the mechanism the
  Profiler measures
- [@defer Blocks](../rendering/defer-blocks.md) — defer block state visible in
  the Components tab
- [Official docs — Angular DevTools](https://angular.dev/tools/devtools)
- [Chrome Performance panel integration](https://angular.dev/best-practices/profiling-with-chrome-devtools)

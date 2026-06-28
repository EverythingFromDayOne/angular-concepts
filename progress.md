# angular-concepts — Project Progress

> **Status as of:** Phase 2 modernization in progress; orphan migration complete; recipes track started.

## Overview

This repo translates and modernizes the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) tutorial series into American-English Angular v22 concept docs, with original gap articles where the source series had no equivalent.

| Track | Count | Status |
| --- | --- | --- |
| Phase 1 — Translation (Cursor) | 33 articles | ✅ Complete |
| Phase 3 — Gap articles (Claude, written for v22) | 36 articles | ✅ Complete |
| Phase 2 — Modernization of Phase 1 to v22 (Claude) | 33 articles | 🟡 In progress (~7/33) |
| Orphan migration | 5 files | ✅ Complete |
| Recipes (real-world scenarios) | 4 planned | 🟡 In progress (1/4) |

---

## Phase 2 — Modernization status

Translated articles needing Angular 9 → v22 upgrade. Each gets the standard Phase 2 treatment: callout box at top with deltas, side-by-side legacy/v22 code blocks, cross-references to gap articles, mechanism reflection where the topic mechanism changed across versions.

### Tier 1 — Opus · Max · Thinking ON (foundational, biggest mechanism deltas)

| Article | Status | Notes |
| --- | --- | --- |
| `dependency-injection/dependency-injection.md` | ✅ Done | `inject()` mechanism + injection context |
| `routing/routing.md` | ✅ Done | `provideRouter` + `withComponentInputBinding` |
| `forms/reactive-forms.md` | ✅ Done | Typed forms mapped-types mechanism |
| `state-management/ngrx.md` | ✅ Done (polish) | Was a Phase 3 gap article; polished imports + legacy marker |
| `http/http.md` | ✅ Done (polish) | Was a Phase 3 gap article; polished Fetch-default timeline |

### Tier 2 — Sonnet 4.6 · High · Thinking ON (high-impact core)

| Article | Status | Notes |
| --- | --- | --- |
| `monorepo/module-federation.md` | ✅ Done | Webpack MF → Native Federation v4 (deep mechanism contrast per user ask) |
| `components/dynamic-components.md` | ✅ Done | CFR removal in v22 + `setInput` + bindings API |
| `directives/structural-directives.md` |  | `*ngIf` / `*ngFor` → `@if` / `@for` |
| `directives/attribute-directives.md` |  | `host: {}` replaces `@HostBinding` / `@HostListener` |
| `http/interceptors.md` |  | Functional interceptors over class-based |
| `http/error-handling.md` |  | `tapResponse` over `catchError` in rxMethod |
| `routing/guards-resolvers.md` |  | Functional `CanActivateFn` / `ResolveFn` |
| `routing/lazy-loading.md` |  | `loadComponent` over `loadChildren` modules |
| `routing/router-configuration.md` |  | `provideRouter()` feature functions |
| `forms/template-driven-forms.md` |  | Signal model bindings, standalone `FormsModule` |
| `forms/control-value-accessor.md` |  | CVA + `inject()` |
| `forms/validation.md` |  | Typed validators, async signal validators |
| `components/component-interactions.md` |  | `input()` / `output()` / `model()` / `viewChild()` |
| `components/animations.md` |  | `provideAnimationsAsync()`, View Transitions API |
| `pipes/pipes.md` |  | Standalone pipes, `inject()` in pipes |

### Tier 3 — Sonnet 4.6 · High · Thinking ON (important, lower delta)

| Article | Status | Notes |
| --- | --- | --- |
| `directives/ng-template-ng-container.md` |  | `@let` and deferred-template story |
| `directives/directive-composition.md` |  | `hostDirectives` is v15+; may be partly gap-flavored |
| `routing/router-link.md` |  | `withComponentInputBinding()` route params |
| `routing/router-outlets.md` |  | Named outlets, hydration interplay |
| `components/templates/data-binding.md` |  | Signal reads `value()`, `@let` declarations |
| `components/templates/content-projection.md` |  | Mostly stable |
| `components/templates/templates-architecture.md` |  | Built-in control flow, deferrable views |
| `components/styling/angular-material.md` |  | Material 3 tokens, signal inputs |
| `components/styling/ui-library-comparison.md` |  | Refresh library landscape |
| `components/angular-devtools.md` |  | Signal graph inspector, hydration tab |
| `state-management/ngxs.md` |  | NGXS signal selectors |
| `testing/integration-tests.md` |  | `await fixture.whenStable()`, `TestBed.tick()` |
| `testing/e2e-testing.md` |  | Playwright recommended; Protractor gone |
| `rendering/view-ref.md` |  | `afterRender` / `afterNextRender` |

### Tier 4 — RxJS family · Sonnet 4.6 · High · Thinking ON

Light touch — RxJS as a library is stable, but Angular's relationship to it has changed (`toSignal()`, `toObservable()`, `takeUntilDestroyed()`, `inject(DestroyRef)`, `rxMethod` from NgRx Signals).

| Article | Status |
| --- | --- |
| `reactivity/rxjs/rxjs.md` |  |
| `reactivity/rxjs/rxjs-creation.md` |  |
| `reactivity/rxjs/rxjs-transformation.md` |  |
| `reactivity/rxjs/rxjs-filtering.md` |  |
| `reactivity/rxjs/rxjs-combination.md` |  |
| `reactivity/rxjs/rxjs-error-handling.md` |  |
| `reactivity/rxjs/rxjs-higher-order.md` |  |
| `reactivity/rxjs/rxjs-subjects.md` |  |

### Tier 5 — Tooling · Sonnet 4.6 · High · Thinking ON

| Article | Status | Notes |
| --- | --- | --- |
| `tooling/builders.md` |  | **Possibly Opus-worthy** — Application Builder (esbuild + Vite) is the biggest tooling shift since Ivy. Mirror the Native Federation deep-dive treatment if so. |
| `tooling/schematics.md` |  | `ng update` migrations |
| `tooling/built-in-i18n.md` |  | i18n with esbuild builder |
| `tooling/nx.md` |  | Nx 19+ alignment |
| `tooling/pwa.md` |  | Service worker + zoneless + SSR |
| `tooling/angular-elements.md` |  | Standalone components as elements |
| `tooling/sass.md` |  | Modern Sass module syntax |
| `tooling/ionic.md` |  | Ionic 8+ + standalone |
| `tooling/ngx-translate.md` |  | External lib; lighter touch |

---

## Orphan migration

| Original | New location | Status |
| --- | --- | --- |
| `_orphans/jira-clone.md` | *(dropped — stack obsolete, partial coverage)* | ✅ |
| `_orphans/typescript-prereqs.md` | `typescript-prereqs.md` | ✅ |
| `_orphans/getting-started.md` | `getting-started.md` | ✅ |
| `_orphans/cdk-coercion.md` | `tooling/cdk-coercion.md` | ✅ |
| `_orphans/js-widget-embedding.md` | `recipes/elements/widget-deployment.md` | ✅ |

`_orphans/` folder is empty and can be deleted.

---

## Recipes — real-world practical scenarios

Sourced from [`EverythingFromDayOne/AngularDemos`](https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features). Different content shape from concept articles — scenario-driven, code-heavy, no mechanism reflection (links out to concept articles for that).

| Recipe | Source demo | Status | Notes |
| --- | --- | --- | --- |
| `recipes/elements/widget-deployment.md` | (orphan migration) | ✅ Done | First recipe — established the template |
| `recipes/reactivity/take-until-destroyed.md` | `features/takeUntilDestroyed` | 🔜 Queued | Warm-up — most self-contained, v22-locked convention |
| `recipes/routing/preloading-strategy.md` | `features/preloading-strategy` | 🔜 Queued | Builds on Routing article |
| `recipes/forms-and-search/search-engine.md` | `features/search-engine` | 🔜 Queued | Forms + RxJS + signals, most cross-cutting |
| `recipes/advanced/self-rewrite-code.md` | `features/self-rewrite-code` | 🔜 Queued | Scope TBD — needs repo read first |

---

## Locked editorial conventions

Apply to every Phase 2 modernized article. Recipes inherit most of these except mechanism reflections.

- American English, friendly tutorial voice
- `data-testid` over `ng-reflect-*` selectors
- `await fixture.whenStable()` over `fixture.detectChanges()` in new test code
- `withFetch()` deprecated — Fetch is the default in v22
- `TestBed.tick()` over deprecated `flushEffects()`
- Functional interceptors over class-based
- `store.selectSignal()` for NgRx state reads
- `tapResponse` over `catchError` inside `rxMethod` pipelines
- Legacy NgModule-pattern code blocks get `<!-- legacy: written for Angular X (YEAR) — modernized in the upgrade pass -->`
- Each article opens with a "What changed since the original" callout box (deltas specific to that article — not boilerplate)
- v22 equivalents shown alongside legacy patterns
- Cross-reference links to gap articles
- Mechanism reflection section for topics that changed across Angular versions
- Frontmatter: `status.upgraded: true` on completion

## Workflow conventions

- **One article per Claude turn** in normal cadence
- **"Roll" / "keep rolling"** — continue to next article with less ceremony
- **"Modernize this"** — start a new article
- **"Go check on it, if it is ok then leave it otherwise polish it if truly necessary"** — light review pass on gap articles (HTTP, NgRx style)
- **"Continue on this"** — modernize the article just uploaded
- Outputs land in `/mnt/user-data/outputs/` for the user to retrieve
- Working dir at `/home/claude/angular-concepts/docs/` (Claude scratchpad)
- Source articles at `E:\linh tinh\EverythingFromDayOne\experimental-projects\angular-concepts\docs\` (user's local)

## Open questions / pending decisions

- [ ] Should the attribution footer pattern on completed articles be slimmed? (User raised; proposed: drop "Phase 2 upgrade pass" terminology, keep original author credit only)
- [ ] Recipe-template details — is the current structure (scenario → walkthrough → comparisons → legacy ref → trade-offs → see also) right for all four queued recipes, or should some have variations?
- [ ] `tooling/builders.md` — Opus or Sonnet? (Application Builder esbuild migration is mechanically substantial — could warrant the Native Federation deep-dive treatment)
- [ ] README.md content shape — TBD, drafting next

---

## Quick stats

- **Articles total:** 70+ (33 Phase 1 + 36 Phase 3 + orphans/recipes)
- **Phase 2 completion:** ~7 / 33 (~21%)
- **Recipes completion:** 1 / 4 + (others as scoped)
- **Last updated:** [fill in date when committing]
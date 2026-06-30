# angular-concepts — progress

Maintainer-facing tracking document. See [`README.md`](README.md) for the reader-facing entry point.

## Legend

- ✅ Complete and reviewed
- 🟢 Drafted (v22 idioms applied; awaiting review)
- 🟡 In progress
- ⚪ Queued
- ❌ Dropped / out of scope

---

## Phase 1 — translation (✅ complete)

All 33 articles from the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) series translated to English. Completed via Cursor; located across the concept-folder structure.

---

## Phase 2 — v22 modernization

Modernizing Phase 1 translations to v22 idioms: signals, `inject()`, functional interceptors/guards/resolvers, `takeUntilDestroyed()`, `@if`/`@for`/`@switch`, standalone components, `provideAppInitializer`, `input()`/`output()`/`model()`.

### Foundation / high-complexity (Opus tier)

| Article | Status | Notes |
| --- | --- | --- |
| `dependency-injection/dependency-injection.md` | 🟢 | Includes the lazy-injection escape-hatch section (~75 lines added) for the `Injector.get()` pattern referenced by all 4 auth recipes |
| `routing/routing.md` | 🟢 | `provideRouter`, functional guards (`CanActivateFn`, `CanMatchFn`), functional resolvers |
| `forms/reactive-forms.md` | 🟢 | `NonNullableFormBuilder`, typed forms, `inject(FormBuilder)` |
| `reactivity/signals.md` | ⚪ | Tier 1 priority; underpins almost every recipe |
| `components/change-detection.md` | ⚪ | Zone.js → signals → zoneless evolution narrative |
| `components/components.md` | ⚪ | Standalone-by-default; `input()`/`output()`/`model()` signal-based component I/O |
| `ssr/ssr-hydration.md` | ⚪ | Modern hydration; `provideClientHydration` |

### Application architecture (mixed tier)

| Article | Status | Notes |
| --- | --- | --- |
| `http/http.md` | 🟢 | Polished during Phase 3 — `HttpClient`, `provideHttpClient(withInterceptors())` |
| `state-management/ngrx.md` | 🟢 | Polished during Phase 3 — includes Signal Store framing |
| `monorepo/module-federation.md` | 🟢 | Modern federation patterns; standalone-aware |
| `components/dynamic-components.md` | 🟢 | `ViewContainerRef.createComponent()` (v14+); `ComponentFactoryResolver` legacy |
| `forms/forms.md` | ⚪ | Template-driven forms overview |
| `forms/validation.md` | ⚪ | Sync + async validator patterns |
| `routing/lazy-loading.md` | ⚪ | `loadComponent`, `loadChildren` with standalone |
| `routing/route-guards.md` | ⚪ | Functional `CanActivateFn`, `CanMatchFn`, `CanDeactivateFn` |

### Common patterns (Sonnet tier)

| Article | Status | Notes |
| --- | --- | --- |
| `directives/structural-directives.md` | ⚪ | New control-flow syntax (`@if`/`@for`/`@switch`) + custom structural directives |
| `directives/attribute-directives.md` | ⚪ | `host: {}` object over `@HostListener`/`@HostBinding` |
| `pipes/pipes.md` | ⚪ | Built-in pipes; pure vs impure |
| `pipes/custom-pipes.md` | ⚪ | Custom pipe authoring |
| `components/component-interactions.md` | ⚪ | Updated to point to `recipes/components/component-communication.md` as the canonical decision tree |
| `components/lifecycle-hooks.md` | ⚪ | Hooks vs effects vs signals |
| `styling/style-binding.md` | ⚪ | Class/style binding modern patterns |
| `styling/view-encapsulation.md` | ⚪ | Encapsulation modes |
| `styling/ng-content.md` | ⚪ | Content projection; multi-slot |
| `testing/component-testing.md` | ⚪ | Modern testing patterns; `TestBed` with standalone |
| `testing/service-testing.md` | ⚪ | Mocking with `inject()`, `HttpTestingController` |

### Tooling (Sonnet tier)

| Article | Status | Notes |
| --- | --- | --- |
| `tooling/built-in-i18n.md` | ⚪ | i18n with lazy locale loading |
| `tooling/cdk-coercion.md` | ✅ | Migrated from orphans; reframed around `booleanAttribute`/`numberAttribute` |
| `tooling/ng-cli.md` | ⚪ | Modern Angular CLI commands |

---

## Phase 3 — gap articles (✅ complete)

36 articles covering topics absent from the original series. All drafted by Claude (Opus for high-complexity, Sonnet for the rest). Organized into the concept-folder structure during the Cursor migration.

Topics included: change detection internals, SSR/hydration, RxJS deep-dive, control flow blocks (`@if`/`@for`/`@switch`), signals + `toSignal`/`toObservable`, dynamic forms primer, custom directives, route guards / resolvers (functional), HttpInterceptor patterns, NgRx patterns, Nx workspaces, deferred views (`@defer`), and others.

---

## Recipes — problem-solving content (🟡 growing)

Real-world problem-solving recipes. Each leads with a concrete symptom ("user types fast, results jump") rather than a concept name. Designed to compose with each other and with concept articles.

### Original recipes (✅ complete)

Sourced from the Vietnamese series' demos at [`EverythingFromDayOne/AngularDemos`](https://github.com/EverythingFromDayOne/AngularDemos).

| Recipe | File | Lines |
| --- | --- | --- |
| Widget deployment | `recipes/elements/widget-deployment.md` | 534 |
| takeUntilDestroyed | `recipes/reactivity/take-until-destroyed.md` | 516 |
| Preloading strategy | `recipes/routing/preloading-strategy.md` | 636 |
| Search engine (multi-stage) | `recipes/forms-and-search/search-engine.md` | 885 |
| Progress tracking (uploads/downloads) | `recipes/http/progress-tracking.md` | 562 |

### Auth series (✅ complete)

Tightly composed chain — each recipe builds on the previous.

| # | Recipe | File | Lines |
| --- | --- | --- | --- |
| 1 | JWT interceptor: breaking the circular dependency | `recipes/auth/jwt-interceptor-circular-dep.md` | 456 |
| 2 | Token storage: where tokens should live | `recipes/auth/token-storage-security.md` | 452 |
| 3 | App initialization: silent restoration on F5 | `recipes/auth/app-initialization.md` | 491 |
| 4 | Step-up authentication: sudo mode | `recipes/auth/step-up-authentication.md` | 601 |

### Problem-solving track (✅ complete — 8 recipes)

Each frames a concrete symptom and walks through the v22-idiomatic fix.

| Recipe | File | Lines | Cross-references |
| --- | --- | --- | --- |
| Retry with backoff | `recipes/http/retry-with-backoff.md` | 612 | progress-tracking, race-conditions |
| Race conditions (operator decision tree) | `recipes/reactivity/race-conditions.md` | 552 | search-engine, take-until-destroyed |
| Request deduplication | `recipes/http/request-deduplication.md` | 495 | retry-with-backoff, race-conditions |
| Dynamic forms | `recipes/forms-and-search/dynamic-forms.md` | 748 | race-conditions, request-deduplication |
| Async validation | `recipes/forms-and-search/async-validation.md` | 467 | dynamic-forms, request-deduplication, search-engine |
| Optimistic updates | `recipes/forms-and-search/optimistic-updates.md` | 603 | race-conditions, request-deduplication, retry-with-backoff |
| Virtual scrolling | `recipes/components/virtual-scrolling.md` | 566 | request-deduplication, race-conditions |
| Component communication | `recipes/components/component-communication.md` | 705 | dependency-injection (lazy injection), signals, ngrx |

### Composition map

The 8 problem-solving recipes form a dense reference graph. Foundational recipes referenced by many others:

- `race-conditions` — referenced by 5 (request-deduplication, dynamic-forms, optimistic-updates, virtual-scrolling, component-communication)
- `request-deduplication` — referenced by 4 (retry-with-backoff, optimistic-updates, virtual-scrolling, component-communication)
- `retry-with-backoff` — referenced by 3 (request-deduplication via interceptor ordering, optimistic-updates, virtual-scrolling)

### Future recipe candidates (⚪ queued)

Topics that have surfaced as natural extensions but aren't yet drafted:

| Recipe | Notes |
| --- | --- |
| WebSocket integration | Bridging Subject ↔ WebSocket; protocol-agnostic patterns |
| Service worker / offline-first | PWA patterns; offline queue with `pending-operation queue` from optimistic-updates |
| i18n with lazy locale loading | Companion to `tooling/built-in-i18n.md` concept article |
| Performance auditing (zoneful vs zoneless) | OnPush, signals, `provideExperimentalZonelessChangeDetection()` |
| State management migration (NgRx → Signal Store) | Speculative; depends on the source NgRx shape |
| Bidirectional infinite scroll | Extends virtual-scrolling for "load up" cases (chat history) |

---

## Orphan migration (✅ complete)

5 files from `_orphans/` were placed during the cleanup pass.

| Source | Destination | Outcome |
| --- | --- | --- |
| `_orphans/jira-clone.md` | — | ❌ Dropped (partial coverage, obsolete stack) |
| `_orphans/typescript-prereqs.md` | `typescript-prereqs.md` | ✅ Top-level (435 lines) |
| `_orphans/getting-started.md` | `getting-started.md` | ✅ Top-level (483 lines) |
| `_orphans/cdk-coercion.md` | `tooling/cdk-coercion.md` | ✅ Reframed to lead with `booleanAttribute`/`numberAttribute` (367 lines) |
| `_orphans/js-widget-embedding.md` | `recipes/elements/widget-deployment.md` | ✅ Established recipe template (534 lines) |

`_orphans/` folder can be deleted.

---

## Locked editorial conventions

Conventions established across the recipes; apply to all new content unless explicitly noted.

### Article structure (concept articles)

1. Frontmatter (recipe_id, related concepts, baseline version)
2. "Lead with this" callout (one-paragraph hook)
3. What it is
4. How it works under the hood (with old-vs-new mechanism shifts)
5. Basic usage (NgModule legacy + standalone modern)
6. Real-world patterns
7. Common mistakes
8. How this evolved
9. See also

### Recipe structure

1. Frontmatter
2. "What you'll build" callout (scenario summary)
3. The scenario (concrete failure mode)
4. Walkthrough (multi-stage if complex)
5. Variations
6. Trade-offs and common pitfalls
7. See also
8. References
9. Demo source

### Code conventions

- Functional interceptors over class-based (`HttpInterceptorFn` + `provideHttpClient(withInterceptors())`)
- `inject()` field initializers over constructor injection
- `signal()` + `computed()` for component state; `BehaviorSubject` only where multi-subscriber broadcast semantics matter
- `takeUntilDestroyed()` on every Observable subscription in components/directives
- `host: {}` object over `@HostListener` / `@HostBinding`
- `@if` / `@for` / `@switch` control flow; `track item` (reference) over `track $index`
- `throwError(() => error)` (RxJS 7+ factory form)
- `provideAppInitializer()` (v19+) over `APP_INITIALIZER` token
- `CanActivateFn` over class-based `CanActivate`
- Functional guards and resolvers throughout
- `input.required<T>()` / `input(default)` / `output<T>()` / `model<T>()` over decorator-based component I/O
- `data-testid` attributes over `ng-reflect-*`
- `await fixture.whenStable()` over sync `detectChanges()` for async tests

### Legacy code preservation

When showing old vs new patterns side by side, prefix the legacy block with the marker comment:

```typescript
<!-- legacy: pre-v19 APP_INITIALIZER token + factory + multi:true — modernized in the upgrade pass -->
```

### Cross-referencing

Recipes cross-reference liberally:
- "See also" section at the end of each recipe lists at least 3 related items
- Inline links use the form `[link text](../path/to/file.md#section-anchor)`
- The composition map is part of the content — recipes that compose explicitly reference each other in the walkthrough, not just in "see also"

---

## Open questions / TODOs

- [ ] `CREDITS.md` — referenced from README but not yet created. Should contain per-day author attribution mapped to the original Vietnamese series authors.
- [ ] `LICENSE` — MIT text + copyright not yet at the repo root.
- [ ] Footer slim sweep — Cursor regex prompt handed off; status unknown (was running across 9 files with verbose Phase 2 footers, target was the slim `*Translated from the Vietnamese "100 Days of Angular" series. MIT licensed.*` form).
- [ ] Phase 2 Sonnet-tier tail — ~24 articles still queued (see tables above).
- [ ] Phase 2 `reactivity/signals.md` — should be the next priority modernization given how many recipes lean on it.
- [ ] Possibly: a "recipes/index.md" that re-renders the table-by-symptom from README.md but with longer descriptions per recipe.
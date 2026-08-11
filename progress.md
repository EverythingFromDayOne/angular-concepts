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

## Phase 2 — v22 modernization (🟡 in progress)

Modernizing Phase 1 translations to v22 idioms: signals, `inject()`, functional interceptors/guards/resolvers, `takeUntilDestroyed()`, `@if`/`@for`/`@switch`, standalone components, `provideAppInitializer`, `input()`/`output()`/`model()`.

### Foundation / high-complexity (Opus tier)

| Article | Status | Notes |
| --- | --- | --- |
| `dependency-injection/dependency-injection.md` | 🟢 | Includes lazy-injection escape-hatch section — referenced by all 4 auth recipes and the interceptor recipes |
| `routing/routing.md` | 🟢 | `provideRouter`, functional guards, functional resolvers |
| `forms/reactive-forms.md` | 🟢 | `NonNullableFormBuilder`, typed forms, `inject(FormBuilder)` |
| `reactivity/signals.md` | ⚪ | **Highest-priority queued** — recipes across the project lean on it |
| `components/change-detection.md` | ⚪ | Zone.js → signals → zoneless evolution |
| `components/components.md` | ⚪ | Standalone-by-default; `input()`/`output()`/`model()` |
| `ssr/ssr-hydration.md` | ⚪ | Complements the `recipes/ssr/ssr-hydration-deep-dive.md` recipe |

### Application architecture (mixed tier)

| Article | Status | Notes |
| --- | --- | --- |
| `http/http.md` | 🟢 | Polished during Phase 3 |
| `state-management/ngrx.md` | 🟢 | Polished during Phase 3; Signal Store framing included |
| `monorepo/module-federation.md` | 🟢 | Modern federation; standalone-aware |
| `components/dynamic-components.md` | 🟢 | `ViewContainerRef.createComponent()` (v14+) |
| `forms/forms.md` | ⚪ | Template-driven overview |
| `forms/validation.md` | ⚪ | Sync + async patterns |
| `routing/lazy-loading.md` | ⚪ | `loadComponent`, `loadChildren` |
| `routing/route-guards.md` | ⚪ | Functional guards |

### Common patterns (Sonnet tier)

| Article | Status |
| --- | --- |
| `directives/structural-directives.md` | ⚪ |
| `directives/attribute-directives.md` | ⚪ |
| `pipes/pipes.md` | ⚪ |
| `pipes/custom-pipes.md` | ⚪ |
| `components/component-interactions.md` | ⚪ (point to `recipes/components/component-communication.md` as canonical decision tree) |
| `components/lifecycle-hooks.md` | ⚪ |
| `styling/style-binding.md` | ⚪ |
| `styling/view-encapsulation.md` | ⚪ |
| `styling/ng-content.md` | ⚪ |
| `testing/component-testing.md` | ⚪ (complements `recipes/testing/testing-signal-components.md`) |
| `testing/service-testing.md` | ⚪ |

### Tooling (Sonnet tier)

| Article | Status |
| --- | --- |
| `tooling/built-in-i18n.md` | ⚪ |
| `tooling/cdk-coercion.md` | ✅ (from orphan migration; reframed around `booleanAttribute`/`numberAttribute`) |
| `tooling/ng-cli.md` | ⚪ |
| `tooling/pwa.md` | ⚪ (complements `recipes/pwa/service-worker-offline-first.md`) |

---

## Phase 3 — gap articles (✅ complete)

36 articles covering topics absent from the original series. All drafted by Claude. Organized into concept folders during the Cursor migration.

---

## Recipes — problem-solving content (🟢 rich)

27 recipes total. Each leads with a concrete symptom rather than a concept name. Designed to compose with each other and with concept articles.

### Original recipes (✅ complete — 5)

Sourced from the Vietnamese series' demos.

| Recipe | File | Lines |
| --- | --- | --- |
| Widget deployment | `recipes/elements/widget-deployment.md` | 534 |
| takeUntilDestroyed | `recipes/reactivity/take-until-destroyed.md` | 516 |
| Preloading strategy | `recipes/routing/preloading-strategy.md` | 636 |
| Search engine (multi-stage) | `recipes/form-and-search/search-engine.md` | 885 |
| Progress tracking | `recipes/http/progress-tracking.md` | 562 |

### Auth series (✅ complete — 4)

Tightly composed chain — each recipe builds on the previous.

| # | Recipe | Lines |
| --- | --- | --- |
| 1 | JWT interceptor: circular dependency | 456 |
| 2 | Token storage security | 452 |
| 3 | App initialization (silent restore) | 491 |
| 4 | Step-up authentication (sudo mode) | 601 |

### Async coordination / HTTP resilience (✅ complete — 3)

| Recipe | File | Lines |
| --- | --- | --- |
| Retry with backoff | `recipes/http/retry-with-backoff.md` | 612 |
| Race conditions (operator decision tree) | `recipes/reactivity/race-conditions.md` | 552 |
| Request deduplication | `recipes/http/request-deduplication.md` | 495 |

### Forms & UX (✅ complete — 4)

| Recipe | File | Lines |
| --- | --- | --- |
| Dynamic forms | `recipes/form-and-search/dynamic-forms.md` | 748 |
| Async validation | `recipes/form-and-search/async-validation.md` | 467 |
| Optimistic updates | `recipes/form-and-search/optimistic-updates.md` | 603 |
| Multi-step wizards | `recipes/form-and-search/multi-step-wizards.md` | 725 |

### Components at scale (✅ complete — 2)

| Recipe | File | Lines |
| --- | --- | --- |
| Virtual scrolling | `recipes/components/virtual-scrolling.md` | 566 |
| Component communication | `recipes/components/component-communication.md` | 705 |

### Real-time / connectivity (✅ complete — 2)

| Recipe | File | Lines |
| --- | --- | --- |
| WebSocket / real-time integration | `recipes/http/websocket-real-time.md` | 614 |
| Service worker / offline-first | `recipes/pwa/service-worker-offline-first.md` | 729 |

### Performance track (✅ complete — 4)

| Recipe | File | Lines |
| --- | --- | --- |
| Performance auditing | `recipes/performance/performance-auditing.md` | 750 |
| Bundle splitting strategies | `recipes/performance/bundle-splitting-strategies.md` | 686 |
| Image optimization | `recipes/performance/image-optimization.md` | 554 |
| Web Worker integration | `recipes/performance/web-worker-integration.md` | 698 |

### Architecture (✅ complete — 2)

| Recipe | File | Lines |
| --- | --- | --- |
| SSR + hydration deep-dive | `recipes/ssr/ssr-hydration-deep-dive.md` | 676 |
| NgRx → Signal Store migration | `recipes/state-management/ngrx-to-signal-store-migration.md` | 876 |

### Testing (🟡 starting — 1 of ~4 planned)

| Recipe | File | Lines |
| --- | --- | --- |
| Testing signal-based components | `recipes/testing/testing-signal-components.md` | 808 |

### Composition map

Recipes cross-reference densely. Foundational recipes (heaviest in-degree):

- **`race-conditions`** — referenced by 6+ others (dedup, dynamic-forms, optimistic-updates, virtual-scrolling, component-communication, testing)
- **`request-deduplication`** — referenced by 5+ (retry, optimistic-updates, virtual-scrolling, component-communication, service-worker)
- **`retry-with-backoff`** — referenced by 5+ (dedup via interceptor order, optimistic-updates, service-worker, websocket reconnect, virtual-scrolling)
- **`component-communication`** — referenced by 4+ (websocket, wizards, ngrx migration, testing)
- **`signals` (concept)** — referenced by every recipe in the project
- **`performance-auditing`** — hub for the entire performance track (bundle splitting, images, workers)

### Rough by-track totals

| Track | Recipes | Approx lines |
| --- | --- | --- |
| Original | 5 | 3,133 |
| Auth | 4 | 2,000 |
| Async coordination | 3 | 1,659 |
| Forms & UX | 4 | 2,543 |
| Components | 2 | 1,271 |
| Real-time / connectivity | 2 | 1,343 |
| Performance | 4 | 2,688 |
| Architecture | 2 | 1,552 |
| Testing | 1 | 808 |
| **Total** | **27** | **~17,000** |

### Queued recipe candidates (⚪)

| Recipe | Notes |
| --- | --- |
| Testing HTTP with HttpTestingController | Completes the testing pair |
| Testing reactive forms | Composes with dynamic-forms + async-validation |
| Testing route guards + RouterTestingHarness | Composes with app-initialization |
| OAuth/SSO integration | Extends auth series with third-party providers |
| Drag-and-drop reordering | CDK drag-drop with FormArray; composes with dynamic-forms |
| Undo/redo with signal stack | Editor-style history without memory explosion |
| Bidirectional infinite scroll | Extends virtual-scrolling for chat-history "load up" |
| Breadcrumb generation | Router-data-driven with signal composition |
| i18n with lazy locale loading | Companion to `tooling/built-in-i18n.md` |
| Confirm-on-leave deep-dive | Beyond `CanDeactivate` — unload events, tab-close vs navigation |
| Image / file upload with chunking + resume | Extends progress-tracking for large uploads |

---

## Orphan migration (✅ complete)

5 files from `_orphans/` placed during cleanup. `_orphans/` folder can be deleted.

---

## Locked editorial conventions

### Article structure (concept articles)

1. Frontmatter (recipe_id, related concepts, baseline version)
2. Lead-with-this callout (one-paragraph hook)
3. What it is
4. How it works under the hood (old-vs-new mechanism)
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
- `data-testid` attributes over `ng-reflect-*` in tests
- `componentRef.setInput()` in tests, not direct assignment to signal inputs
- `await fixture.whenStable()` over sync `detectChanges()` for async tests

### Legacy code preservation

Show old vs new patterns side by side with the marker comment:

```typescript
<!-- legacy: pre-v19 APP_INITIALIZER token + factory + multi:true — modernized in the upgrade pass -->
```

### Cross-referencing

- "See also" section at each recipe's end lists ≥3 related items
- Inline links use `[link text](../path/to/file.md#section-anchor)`
- Composition IS content — recipes that compose reference each other in the walkthrough, not just in "see also"

---

## Open questions / TODOs

- [ ] `CREDITS.md` — referenced from README, not yet created; needs per-day author attribution mapped to the original Vietnamese series authors
- [ ] `LICENSE` — MIT text + copyright not yet at the repo root
- [ ] Footer slim sweep — Cursor regex prompt was handed off; status unknown across the 9 target files
- [ ] Phase 2 Sonnet-tier tail — ~24 articles queued (see tables above)
- [ ] **`reactivity/signals.md` is the highest-priority Phase 2 target** — the entire recipe library leans on it; modernizing it earliest maximizes leverage
- [ ] `tooling/pwa.md` and `ssr/ssr-hydration.md` concept articles pair with their new recipe counterparts
- [ ] Consider a `recipes/index.md` with longer-form recipe descriptions (bigger than README's symptom table)
- [ ] Testing recipe series still has 3 planned entries queued (HTTP, forms, routing) — biggest gap in the recipe library
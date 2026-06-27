# Progress Tracker

Single source of truth. Update this file the moment any status changes.

## Legend

**Origin**
- `translated` — article exists with teaching content from the original series
- `gap` — written fresh for Angular v22 (no prior article)

**Translated**
- `–` not started · `done` complete

**Upgraded**
- `–` not started · `done` modernized to Angular v22 with "What changed" callout

**Reviewed**
- `–` not started · `done` approved by Huy

**Model** (for upgrade/gap work)
- `S` = Sonnet 4.6 Max + Thinking ON
- `O` = Opus 4.7 Max + Thinking ON

---

## Roadmap articles

| Roadmap node ID | File | Source days | Merge type | Translated | Upgraded | Reviewed | Model |
| --- | --- | --- | --- | --- | --- | --- | --- |
| *(getting-started)* | `_orphans/getting-started.md` | 1, 2 | merge | done | – | – | S |
| `data-binding` | `components/templates/data-binding.md` | 3 | 1:1 | done | – | – | S |
| `structural-directives` | `directives/structural-directives.md` | 4, 5 | merge | done | – | – | S |
| `attribute-directives` | `directives/attribute-directives.md` | 6 | 1:1 | done | – | – | S |
| `component-interactions-input-output` | `components/component-interactions.md` | 7, 8, 9, 44 | merge | done | – | – | S |
| `templates-architecture` | `components/templates/templates-architecture.md` | 10, 17 | merge | done | – | – | S |
| `content-projection` | `components/templates/content-projection.md` | 13 | 1:1 | done | – | – | S |
| `ng-template-ng-container` | `directives/ng-template-ng-container.md` | 14 | 1:1 | done | – | – | S |
| `dependency-injection` | `dependency-injection/dependency-injection.md` | 15, 16, 48 | merge | done | done | – | O |
| `pipes` | `pipes/pipes.md` | 18 | 1:1 → 2 sections | done | – | – | S |
| `rxjs` | `reactivity/rxjs/rxjs.md` | 19 | seed | done | – | – | S |
| (rxjs-creation) | `reactivity/rxjs/rxjs-creation.md` | 20 | sub | done | – | – | S |
| (rxjs-transformation) | `reactivity/rxjs/rxjs-transformation.md` | 21 | sub | done | – | – | S |
| (rxjs-filtering) | `reactivity/rxjs/rxjs-filtering.md` | 22 | sub | done | – | – | S |
| (rxjs-combination) | `reactivity/rxjs/rxjs-combination.md` | 23 | sub | done | – | – | S |
| (rxjs-error-handling) | `reactivity/rxjs/rxjs-error-handling.md` | 24 | sub | done | – | – | S |
| (rxjs-higher-order) | `reactivity/rxjs/rxjs-higher-order.md` | 25 | sub | done | – | – | S |
| (rxjs-subjects) | `reactivity/rxjs/rxjs-subjects.md` | 26, 45 | merge | done | – | – | S |
| `routing` | `routing/routing.md` | 27 | 1:1 | done | – | – | S |
| `configuration` | `routing/router-configuration.md` | 28 | 1:1 | done | – | – | S |
| `lazy-loading` | `routing/lazy-loading.md` | 29 | 1:1 | done | – | – | S |
| `guards-resolvers` | `routing/guards-resolvers.md` | 30, 31, 32 | merge | done | – | – | S |
| `template-driven-forms` | `forms/template-driven-forms.md` | 33, 34 | merge | done | – | – | S |
| `reactive-forms` | `forms/reactive-forms.md` | 35, 36 | merge | done | – | – | S |
| `validation` | `forms/validation.md` | 37 | 1:1 | done | – | – | S |
| `dynamic-components` | `components/dynamic-components.md` | 38 | 1:1 | done | – | – | S |
| `module-federation` | `monorepo/module-federation.md` | 39 | 1:1 | done | done | – | S |
| `control-value-accessor` | `forms/control-value-accessor.md` | 43 | 1:1 | done | – | – | S |
| `directive-composition` | `directives/directive-composition.md` | 47 | 1:1 | done | – | – | S |

**Orphans** (no roadmap node yet)

| File | Source days | Translated | Upgraded | Reviewed |
| --- | --- | --- | --- | --- |
| `_orphans/typescript-prereqs.md` | 11, 12 | done | – | – |
| `_orphans/jira-clone.md` | 40, 41 | done | – | – |
| `_orphans/cdk-coercion.md` | 42 | done | – | – |
| `_orphans/js-widget-embedding.md` | 46 | done | – | – |

---

## Gap articles (written fresh for v22)

| Roadmap node ID | File | Depends on | Upgraded | Reviewed | Model |
| --- | --- | --- | --- | --- | --- |
| `lifecycle` | `components/lifecycle.md` | components | done | – | S |
| `view-encapsulation` | `components/styling/view-encapsulation.md` | components | done | – | S |
| `sass` | `tooling/sass.md` | — | done | – | S |
| `angular-material` | `components/styling/angular-material.md` | — | done | – | S |
| `ui-library-comparison` | `components/styling/ui-library-comparison.md` | — | done | – | S |
| `animations` | `components/animations.md` | lifecycle | done | – | S |
| `control-flow` | `components/templates/control-flow.md` | templates | done | – | S |
| `change-detection` | `components/change-detection.md` | lifecycle, signals | done | – | **O** |
| `angular-devtools` | `components/angular-devtools.md` | — | done | – | S |
| `signals` | `reactivity/signals.md` | — | done | – | **O** |
| `signal-inputs` | `reactivity/signal-inputs.md` | signals | done | – | S |
| `to-signal-from-signal` | `reactivity/to-signal.md` | signals, rxjs | done | – | S |
| `router-link` | `routing/router-link.md` | routing | done | – | S |
| `router-outlets` | `routing/router-outlets.md` | routing | done | – | S |
| `http` | `http/http.md` | — | done | – | S |
| `interceptors` | `http/interceptors.md` | http | done | – | S |
| `error-handling` | `http/error-handling.md` | http, rxjs | done | – | S |
| `unit-tests` | `testing/unit-tests.md` | DI | done | – | S |
| `integration-tests` | `testing/integration-tests.md` | unit-tests | done | – | S |
| `component-harnesses` | `testing/component-harnesses.md` | integration-tests | done | – | S |
| `e2e-testing` | `testing/e2e-testing.md` | — | done | – | S |
| `ngrx` | `state-management/ngrx.md` | rxjs, signals | done | – | S |
| `ngrx-signal-store` | `state-management/ngrx-signal-store.md` | signals, ngrx | done | – | S |
| `ngxs` | `state-management/ngxs.md` | — | done | – | S |
| `defer-blocks` | `rendering/defer-blocks.md` | — | done | – | S |
| `ssr-hydration` | `rendering/ssr-hydration.md` | change-detection | done | – | **O** |
| `view-ref` | `rendering/view-ref.md` | DI | done | – | S |
| `signal-forms` | `forms/signal-forms.md` | signals, reactive-forms | done | – | S |
| `nx` | `tooling/nx.md` | — | done | – | S |
| `angular-elements` | `tooling/angular-elements.md` | DI | done | – | S |
| `pwa` | `tooling/pwa.md` | — | done | – | S |
| `ionic` | `tooling/ionic.md` | — | done | – | S |
| `schematics` | `tooling/schematics.md` | — | done | – | S |
| `builders` | `tooling/builders.md` | — | done | – | S |
| `built-in-i18n` | `tooling/built-in-i18n.md` | — | done | – | S |
| `ngx-translate` | `tooling/ngx-translate.md` | — | done | – | S |

---

## Summary counts

| Category | Count | Translated | Upgraded | Reviewed |
| --- | --- | --- | --- | --- |
| Roadmap articles | 29 | 29 | 2 | 0 |
| Orphan articles | 4 | 4 | 0 | 0 |
| Gap articles | 36 | — | 36 | 0 |
| **Total** | **69** | **33** | **38** | **0** |

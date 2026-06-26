# Progress Tracker

Single source of truth. Update this file the moment any status changes.

## Legend

**Origin**
- `translated` — came from 100 Days source (Cursor handles it)
- `gap` — no source day; Claude writes from scratch (Phase 3)

**Translated**
- `–` not started · `cursor` in Cursor queue · `done` complete · `src-EN` official EN exists (Days 1–3, adapt don't re-translate)

**Upgraded**
- `–` not started · `done` modernized to Angular v22 with "What changed" callout

**Reviewed**
- `–` not started · `done` approved by Huy

**Model** (for Claude's upgrade/gap work)
- `S` = Sonnet 4.6 Max + Thinking ON
- `O` = Opus 4.7 Max + Thinking ON

---

## Translated articles (34 nodes — Cursor does Phase 1)

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
| `dependency-injection` | `dependency-injection/dependency-injection.md` | 15, 16, 48 | merge | done | – | – | O |
| `pipes` | `pipes/pipes.md` | 18 | 1:1 → 2 sections | done | – | – | S |
| `rxjs` (intro) | `reactivity/rxjs/rxjs.md` | 19 | seed | done | – | – | S |
| *(rxjs-creation)* | `reactivity/rxjs/rxjs-creation.md` | 20 | sub | done | – | – | S |
| *(rxjs-transformation)* | `reactivity/rxjs/rxjs-transformation.md` | 21 | sub | done | – | – | S |
| *(rxjs-filtering)* | `reactivity/rxjs/rxjs-filtering.md` | 22 | sub | done | – | – | S |
| *(rxjs-combination)* | `reactivity/rxjs/rxjs-combination.md` | 23 | sub | done | – | – | S |
| *(rxjs-error-handling)* | `reactivity/rxjs/rxjs-error-handling.md` | 24 | sub | done | – | – | S |
| *(rxjs-higher-order)* | `reactivity/rxjs/rxjs-higher-order.md` | 25 | sub | done | – | – | S |
| *(rxjs-subjects)* | `reactivity/rxjs/rxjs-subjects.md` | 26, 45 | merge | done | – | – | S |
| `routing` | `routing/routing.md` | 27 | 1:1 | done | – | – | S |
| `configuration` | `routing/router-configuration.md` | 28 | 1:1 | done | – | – | S |
| `lazy-loading` | `routing/lazy-loading.md` | 29 | 1:1 | done | – | – | S |
| `guards-resolvers` | `routing/guards-resolvers.md` | 30, 31, 32 | merge | done | – | – | S |
| `template-driven-forms` | `forms/template-driven-forms.md` | 33, 34 | merge | done | – | – | S |
| `reactive-forms` | `forms/reactive-forms.md` | 35, 36 | merge | done | – | – | S |
| `validation` | `forms/validation.md` | 37 | 1:1 | done | – | – | S |
| `dynamic-components` | `components/dynamic-components.md` | 38 | 1:1 | done | – | – | S |
| `module-federation` | `monorepo/module-federation.md` | 39 | 1:1 | done | – | – | S |
| `control-value-accessor` | `forms/control-value-accessor.md` | 43 | 1:1 | done | – | – | S |
| `directive-composition` | `directives/directive-composition.md` | 47 | 1:1 | done | – | – | S |

*Day 3 has an official EN translation in `translations/EN/` — adapt that, don't re-translate from Vietnamese.

**Orphans (holding pen — translated but no roadmap node)**

| File | Source days | Translated | Upgraded | Reviewed |
| --- | --- | --- | --- | --- |
| `_orphans/typescript-prereqs.md` | 11, 12 | done | – | – |
| `_orphans/jira-clone.md` | 40, 41 | done | – | – |
| `_orphans/cdk-coercion.md` | 42 | done | – | – |
| `_orphans/js-widget-embedding.md` | 46 | done | – | – |

---

## Gap articles (~20 nodes — Claude writes from scratch, Phase 3)

Suggested write order: foundational nodes first.

| Roadmap node ID | File | Depends on | Upgraded | Reviewed | Model |
| --- | --- | --- | --- | --- | --- |
| `lifecycle` | `components/lifecycle.md` | components | – | – | S |
| `view-encapsulation` | `components/styling/view-encapsulation.md` | components | – | – | S |
| `sass` | `components/styling/sass.md` | — | – | – | S |
| `angular-material` | `components/styling/angular-material.md` | — | – | – | S |
| `animations` | `components/animations.md` | lifecycle | – | – | S |
| `control-flow` | `components/templates/control-flow.md` | templates | – | – | S |
| `change-detection` | `components/change-detection.md` | lifecycle, signals | – | – | **O** |
| `signals` | `reactivity/signals.md` | — | – | – | **O** |
| `signal-inputs` | `reactivity/signal-inputs.md` | signals | – | – | S |
| `to-signal-from-signal` | `reactivity/to-signal.md` | signals, rxjs | – | – | S |
| `router-link` | `routing/router-link.md` | routing | – | – | S |
| `router-outlets` | `routing/router-outlets.md` | routing | – | – | S |
| `typed-requests` | `http/typed-requests.md` | http | – | – | S |
| `interceptors` | `http/interceptors.md` | http | – | – | S |
| `error-handling` (http) | `http/error-handling.md` | http, rxjs | – | – | S |
| `unit-tests` | `testing/unit-tests.md` | DI | – | – | S |
| `integration-tests` | `testing/integration-tests.md` | unit-tests | – | – | S |
| `component-harnesses` | `testing/component-harnesses.md` | integration-tests | – | – | S |
| `e2e-testing` | `testing/e2e-testing.md` | — | – | – | S |
| `ngrx` | `state-management/ngrx.md` | rxjs, signals | – | – | S |
| `ngrx-signal-store` | `state-management/ngrx-signal-store.md` | signals, ngrx | – | – | S |
| `ngxs` | `state-management/ngxs.md` | — | – | – | S |
| `defer-blocks` | `rendering/defer-blocks.md` | — | – | – | S |
| `ssr-hydration` | `rendering/ssr-hydration.md` | change-detection | – | – | **O** |
| `view-ref` | `rendering/view-ref.md` | DI | – | – | S |
| `signal-forms` | `forms/signal-forms.md` | signals, reactive-forms | – | – | S |
| `nx` | `monorepo/nx.md` | — | – | – | S |
| `angular-elements` | `web-components/angular-elements.md` | DI | – | – | S |
| `pwa` | `cross-platform/pwa.md` | — | – | – | S |
| `ionic` | `cross-platform/ionic.md` | — | – | – | S |
| `angular-devtools` | `developer-tools/angular-devtools.md` | — | – | – | S |
| `schematics` | `angular-cli/schematics.md` | — | – | – | S |
| `builders` | `angular-cli/builders.md` | — | – | – | S |
| `built-in-i18n` | `internationalization/built-in-i18n.md` | — | – | – | S |
| `ngx-translate` | `internationalization/ngx-translate.md` | — | – | – | S |

---

## Summary counts

| Category | Count | Done |
| --- | --- | --- |
| Translated articles (Cursor) | 29 | 29 |
| Orphan articles (Cursor) | 4 | 4 |
| Gap articles (Claude) | 35 | 0 |
| **Total** | **68** | **33** |

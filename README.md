# Angular Concepts

English translation and Angular v22 modernization of the
[100 Days of Angular](https://github.com/angular-vietnam/100-days-of-angular)
series by **Angular Vietnam** — restructured around a learning roadmap tree
rather than the original day-by-day format.

**Targets Angular v22.** Concept articles assume v22 as the baseline; legacy
patterns from Angular 9–15 are preserved with explicit `<!-- legacy -->`
markers and side-by-side modern equivalents for migration context.

---

## Where to start

- **New to Angular?** Start with [`getting-started.md`](./docs/getting-started.md), then [`typescript-prereqs.md`](./docs/typescript-prereqs.md), then pick a topic that interests you.
- **Coming from Angular 9–15?** Every concept article opens with a "What changed since the original" callout showing the v22 deltas. Jump straight to whichever topic concerns you.
- **Looking for practical patterns?** Check [`recipes/`](./docs/recipes/) — scenario-driven walkthroughs that combine multiple concepts end-to-end.
- **Maintainer / contributor?** See [`progress.md`](./progress.md) for the full status tracker, locked editorial conventions, and the per-tier modernization queue.

---

## Structure

Two content types live side by side:

- **Concepts** — `docs/*/` organized by [Angular roadmap](https://nxhhuy.tech/roadmap) node. Answer *"what is X and how does it work."*
- **Recipes** — `docs/recipes/` organized by domain. Answer *"how do I solve scenario Y end-to-end,"* with links back to concept articles for the underlying mechanics.

```
docs/
  getting-started.md
  typescript-prereqs.md

  components/
    lifecycle.md
    animations.md
    change-detection.md
    angular-devtools.md
    dynamic-components.md
    component-interactions.md
    templates/
      data-binding.md
      control-flow.md
      content-projection.md
      templates-architecture.md
    styling/
      view-encapsulation.md
      angular-material.md
      ui-library-comparison.md
  directives/
    structural-directives.md
    attribute-directives.md
    ng-template-ng-container.md
    directive-composition.md
  pipes/
    pipes.md
  routing/
    routing.md
    router-configuration.md
    lazy-loading.md
    guards-resolvers.md
    router-link.md
    router-outlets.md
  dependency-injection/
    dependency-injection.md
  forms/
    template-driven-forms.md
    reactive-forms.md
    validation.md
    control-value-accessor.md
    signal-forms.md
  reactivity/
    signals.md
    signal-inputs.md
    to-signal.md
    rxjs/
      rxjs.md
      rxjs-creation.md
      rxjs-transformation.md
      rxjs-filtering.md
      rxjs-combination.md
      rxjs-error-handling.md
      rxjs-higher-order.md
      rxjs-subjects.md
  http/
    http.md
    interceptors.md
    error-handling.md
  testing/
    unit-tests.md
    integration-tests.md
    component-harnesses.md
    e2e-testing.md
  state-management/
    ngrx.md
    ngrx-signal-store.md
    ngxs.md
  rendering/
    defer-blocks.md
    ssr-hydration.md
    view-ref.md
  monorepo/
    module-federation.md
  tooling/
    nx.md
    sass.md
    angular-elements.md
    pwa.md
    ionic.md
    schematics.md
    builders.md
    built-in-i18n.md
    ngx-translate.md
    cdk-coercion.md

  recipes/
    elements/
      widget-deployment.md
    # more recipes planned — see progress.md
```

---

## Three phases

| Phase | Who | What |
| --- | --- | --- |
| 1 — Translate | Cursor | Vietnamese → English, roadmap-node files |
| 2 — Modernize | Claude (Sonnet/Opus) | Upgrade code to v22, add "What changed" callouts |
| 3 — Fill gaps | Claude (Sonnet/Opus) | Write ~35 nodes with no source day |

See [`progress.md`](./progress.md) for full status tracking, per-article tier
recommendations, and the locked editorial conventions every article follows.

---

## Credits

All teaching and examples originate with the Angular Vietnam authors.
See [`CREDITS.md`](./CREDITS.md) for full attribution and per-day author map.

**Original series:** https://github.com/angular-vietnam/100-days-of-angular

If this project is useful, please support the original authors:
- Chau Tran — https://github.com/sponsors/nartc
- Trung Vo — https://www.buymeacoffee.com/trungvose
- Tiep Phan — https://www.facebook.com/pttiep

---

## License

MIT. See [`LICENSE`](./LICENSE).
Original © 2020 Angular Vietnam · Derivative © 2026 angular-concepts contributors.
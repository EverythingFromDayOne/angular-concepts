# Angular Concepts

English translation and Angular v22 modernization of the
[100 Days of Angular](https://github.com/angular-vietnam/100-days-of-angular)
series by **Angular Vietnam** — restructured around a learning roadmap tree
rather than the original day-by-day format.

---

## Structure

Content is organized by **roadmap node**, not by day number. Each file maps to
one node on the [Angular roadmap](https://nxhhuy.tech/roadmap) so articles
slot directly into the tree when they're ready.

```
docs/
  components/
    lifecycle.md              ← gap (Claude)
    animations.md             ← gap (Claude)
    change-detection.md       ← gap (Claude, Opus)
    dynamic-components.md     ← Day 38
    component-interactions.md ← Days 7, 8, 9, 44
    templates/
      data-binding.md         ← Day 3
      control-flow.md         ← gap (Claude)
      content-projection.md   ← Day 13
      templates-architecture.md ← Days 10, 17
    styling/
      view-encapsulation.md   ← gap (Claude)
      sass.md                 ← gap (Claude)
      angular-material.md     ← gap (Claude)
  directives/
    structural-directives.md  ← Days 4, 5
    attribute-directives.md   ← Day 6
    ng-template-ng-container.md ← Day 14
    directive-composition.md  ← Day 47
  pipes/
    pipes.md                  ← Day 18 (built-in + custom sections)
  routing/
    routing.md                ← Day 27
    router-configuration.md   ← Day 28
    lazy-loading.md           ← Day 29
    guards-resolvers.md       ← Days 30, 31, 32
    router-link.md            ← gap (Claude)
    router-outlets.md         ← gap (Claude)
  dependency-injection/
    dependency-injection.md   ← Days 15, 16, 48 (Opus)
  forms/
    template-driven-forms.md  ← Days 33, 34
    reactive-forms.md         ← Days 35, 36
    validation.md             ← Day 37
    control-value-accessor.md ← Day 43
    signal-forms.md           ← gap (Claude)
  reactivity/
    signals.md                ← gap (Claude, Opus)
    signal-inputs.md          ← gap (Claude)
    to-signal.md              ← gap (Claude)
    rxjs/
      rxjs.md                 ← Day 19 (intro + overview)
      rxjs-creation.md        ← Day 20
      rxjs-transformation.md  ← Day 21
      rxjs-filtering.md       ← Day 22
      rxjs-combination.md     ← Day 23
      rxjs-error-handling.md  ← Day 24
      rxjs-higher-order.md    ← Day 25
      rxjs-subjects.md        ← Days 26, 45
  http/
    typed-requests.md         ← gap (Claude)
    interceptors.md           ← gap (Claude)
    error-handling.md         ← gap (Claude)
  testing/
    unit-tests.md             ← gap (Claude)
    integration-tests.md      ← gap (Claude)
    component-harnesses.md    ← gap (Claude)
    e2e-testing.md            ← gap (Claude)
  state-management/
    ngrx.md                   ← gap (Claude)
    ngrx-signal-store.md      ← gap (Claude)
    ngxs.md                   ← gap (Claude)
  rendering/
    defer-blocks.md           ← gap (Claude)
    ssr-hydration.md          ← gap (Claude, Opus)
    view-ref.md               ← gap (Claude)
  monorepo/
    nx.md                     ← gap (Claude)
    module-federation.md      ← Day 39
  web-components/
    angular-elements.md       ← gap (Claude)
  cross-platform/
    pwa.md                    ← gap (Claude)
    ionic.md                  ← gap (Claude)
  _orphans/                   ← source days with no roadmap node
    getting-started.md        ← Days 1, 2
    typescript-prereqs.md     ← Days 11, 12
    jira-clone.md             ← Days 40, 41
    cdk-coercion.md           ← Day 42
    js-widget-embedding.md    ← Day 46
```

---

## Three phases

| Phase | Who | What |
| --- | --- | --- |
| 1 — Translate | Cursor | Vietnamese → English, roadmap-node files |
| 2 — Modernize | Claude (Sonnet/Opus) | Upgrade code to v22, add "What changed" callouts |
| 3 — Fill gaps | Claude (Sonnet/Opus) | Write ~35 nodes with no source day |

See [`progress.md`](./progress.md) for full status tracking.

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

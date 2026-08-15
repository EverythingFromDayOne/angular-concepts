# angular-concepts

A modern, opinionated Angular learning resource — English translation and Angular v22 modernization of the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) tutorial series, structured around the [nxhhuy.tech](https://nxhhuy.tech) roadmap.

**Targets Angular v22** with the modern idioms throughout: signals (`signal`/`computed`/`effect`), `inject()`, functional interceptors/guards/resolvers, `takeUntilDestroyed()`, `@if`/`@for`/`@switch` control flow, standalone components, `provideAppInitializer`, `input()`/`output()`/`model()` signal-based component I/O.

## Where to start

- **New to Angular** → `getting-started.md` and `typescript-prereqs.md`
- **Existing Angular dev** → pick a concept article (`signals`, `routing`, `dependency-injection`, `http`) or jump straight to a recipe that matches a real-world problem you're hitting
- **Looking for a specific bug fix** → `recipes/` is organized by problem domain; the recipes lead with the symptom

## Structure

```
docs/
├── concepts/
│   ├── foundations/           getting-started.md, typescript-prereqs.md
│   ├── components/               concepts: components, lifecycle, change detection, dynamic components
│   ├── dependency-injection/     concepts: providers, hierarchical DI, lazy injection escape hatch
│   ├── directives/               concepts: structural + attribute directives
│   ├── forms/                    concepts: reactive forms, template-driven forms, validation
│   ├── http/                     concepts: HttpClient, interceptors, error handling
│   ├── monorepo/                 concepts: Nx, module federation
│   ├── pipes/                    concepts: built-in + custom pipes
│   ├── reactivity/               concepts: signals, RxJS, toSignal, takeUntilDestroyed
│   ├── routing/                  concepts: provideRouter, guards (functional), resolvers
│   ├── ssr/                      concepts: SSR, hydration, TransferState
│   ├── state-management/         concepts: NgRx, Signal Store
│   ├── styling/                  concepts: ng-content, view encapsulation, host bindings
│   ├── testing/                  concepts: TestBed, component testing, mocking
│   └── tooling/                  concepts: CLI, builders, i18n, CDK utilities, PWA
│
└── recipes/                  problem-solving — concrete bugs, concrete fixes
    ├── auth/                 4 recipes — the auth-flow composition story
    ├── components/           2 recipes — virtual scroll, component communication
    ├── elements/             1 recipe  — Angular Elements deployment
    ├── form-and-search/     5 recipes — search, dynamic forms, async validation, optimistic UI, wizards
    ├── http/                 4 recipes — progress, retry, deduplication, WebSocket
    ├── performance/          4 recipes — auditing, bundle splitting, images, Web Workers
    ├── pwa/                  1 recipe  — service worker / offline-first
    ├── reactivity/           2 recipes — takeUntilDestroyed, race conditions
    ├── routing/              1 recipe  — preloading strategies
    ├── ssr/                  1 recipe  — SSR / hydration debugging
    ├── state-management/     1 recipe  — NgRx → Signal Store migration
    └── testing/              1 recipe  — testing signal-based components
```

## Recipes index — quick lookup by symptom

### User-facing / UX symptoms
| Problem | Recipe |
| --- | --- |
| "User clicks Like, sees nothing for 400ms, clicks again" | [`form-and-search/optimistic-updates`](./docs/recipes/form-and-search/optimistic-updates.md) |
| "Users lose form data when navigating back through wizard steps" | [`form-and-search/multi-step-wizards`](./docs/recipes/form-and-search/multi-step-wizards.md) |
| "Form fields lose data when user toggles a section" | [`form-and-search/dynamic-forms`](./docs/recipes/form-and-search/dynamic-forms.md) |
| "Search results jump as user types fast" | [`form-and-search/search-engine`](./docs/recipes/form-and-search/search-engine.md) |
| "Username availability check stuck in pending forever" | [`form-and-search/async-validation`](./docs/recipes/form-and-search/async-validation.md) |
| "10,000-row list and Chrome dies" | [`components/virtual-scrolling`](./docs/recipes/components/virtual-scrolling.md) |
| "The app freezes when I import a large CSV / generate a PDF" | [`performance/web-worker-integration`](./docs/recipes/performance/web-worker-integration.md) |
| "Users lose data when they go offline (subway, flights)" | [`pwa/service-worker-offline-first`](./docs/recipes/pwa/service-worker-offline-first.md) |
| "F5 reload logs the user out" | [`auth/app-initialization`](./docs/recipes/auth/app-initialization.md) |
| "Sensitive action needs re-authentication ('sudo mode')" | [`auth/step-up-authentication`](./docs/recipes/auth/step-up-authentication.md) |
| "File upload needs a progress bar" | [`http/progress-tracking`](./docs/recipes/http/progress-tracking.md) |

### Performance / scaling symptoms
| Problem | Recipe |
| --- | --- |
| "The app feels slow — where do I even look?" | [`performance/performance-auditing`](./docs/recipes/performance/performance-auditing.md) |
| "Main JS bundle is 800KB, lazy loading isn't enough" | [`performance/bundle-splitting-strategies`](./docs/recipes/performance/bundle-splitting-strategies.md) |
| "LCP is bad because of heavy hero images" | [`performance/image-optimization`](./docs/recipes/performance/image-optimization.md) |
| "Five components on the page fetch the same URL" | [`http/request-deduplication`](./docs/recipes/http/request-deduplication.md) |
| "API blips and user sees error toast for nothing" | [`http/retry-with-backoff`](./docs/recipes/http/retry-with-backoff.md) |
| "User saves twice fast, old response overwrites new state" | [`reactivity/race-conditions`](./docs/recipes/reactivity/race-conditions.md) |
| "Subscription cleanup boilerplate in every component" | [`reactivity/take-until-destroyed`](./docs/recipes/reactivity/take-until-destroyed.md) |
| "Lazy modules — when to preload, when not to" | [`routing/preloading-strategy`](./docs/recipes/routing/preloading-strategy.md) |

### Architecture / integration
| Problem | Recipe |
| --- | --- |
| "Where should shared state live? NgRx or not?" | [`components/component-communication`](./docs/recipes/components/component-communication.md) |
| "I want less NgRx boilerplate, incremental migration" | [`state-management/ngrx-to-signal-store-migration`](./docs/recipes/state-management/ngrx-to-signal-store-migration.md) |
| "I need real-time server updates (chat, live data)" | [`http/websocket-real-time`](./docs/recipes/http/websocket-real-time.md) |
| "SSR shows 'Hello, undefined' or NG05000 warnings" | [`ssr/ssr-hydration-deep-dive`](./docs/recipes/ssr/ssr-hydration-deep-dive.md) |
| "Embed Angular as a widget in a non-Angular site" | [`elements/widget-deployment`](./docs/recipes/elements/widget-deployment.md) |

### Auth / security
| Problem | Recipe |
| --- | --- |
| "JWT interceptor needs AuthService, AuthService needs HttpClient → cycle" | [`auth/jwt-interceptor-circular-dep`](./docs/recipes/auth/jwt-interceptor-circular-dep.md) |
| "Where do auth tokens belong — localStorage, cookie, memory?" | [`auth/token-storage-security`](./docs/recipes/auth/token-storage-security.md) |

### Testing
| Problem | Recipe |
| --- | --- |
| "How do I test signal-based v22 components?" | [`testing/testing-signal-components`](./docs/recipes/testing/testing-signal-components.md) |

## Phases

| Phase | Status | Description |
| --- | --- | --- |
| Phase 1 | ✅ Complete | English translation of the original 33-day Vietnamese series |
| Phase 2 | 🟡 In progress | Modernization of Phase 1 articles to v22 idioms |
| Phase 3 | ✅ Complete | 36 gap articles — topics absent from the original series |
| Recipes | 🟢 Rich | 27 real-world problem-solving recipes; composes concept articles |

See [`progress.md`](progress.md) for detailed status.

## License

Prose (articles and recipes) is licensed under CC BY 4.0; code is licensed under MIT — see [`LICENSE`](LICENSE).
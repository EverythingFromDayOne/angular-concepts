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
├── getting-started.md
├── typescript-prereqs.md
│
├── components/               concepts: components, lifecycle, change detection, dynamic components
├── dependency-injection/     concepts: providers, hierarchical DI, lazy injection escape hatch
├── directives/               concepts: structural + attribute directives
├── forms/                    concepts: reactive forms, template-driven forms, validation
├── http/                     concepts: HttpClient, interceptors, error handling
├── monorepo/                 concepts: Nx, module federation
├── pipes/                    concepts: built-in + custom pipes
├── reactivity/               concepts: signals, RxJS, toSignal, takeUntilDestroyed
├── routing/                  concepts: provideRouter, guards (functional), resolvers
├── state-management/         concepts: NgRx, signal store
├── styling/                  concepts: ng-content, view encapsulation, host bindings
├── testing/                  concepts: TestBed, component testing, mocking
├── tooling/                  concepts: CLI, builders, i18n, CDK utilities
│
└── recipes/                  problem-solving — concrete bugs, concrete fixes
    ├── auth/                 4 recipes — the auth-flow composition story
    ├── components/           2 recipes — virtual scroll, component communication
    ├── elements/             1 recipe  — Angular Elements deployment
    ├── forms-and-search/     4 recipes — search, dynamic forms, async validation, optimistic UI
    ├── http/                 3 recipes — progress tracking, retry, deduplication
    ├── reactivity/           2 recipes — takeUntilDestroyed, race conditions
    └── routing/              1 recipe  — preloading strategies
```

## Recipes index — quick lookup by symptom

| Problem | Recipe |
| --- | --- |
| "User clicks Like, sees nothing for 400ms, clicks again" | [`forms-and-search/optimistic-updates`](recipes/forms-and-search/optimistic-updates.md) |
| "Five components on the page fetch the same URL" | [`http/request-deduplication`](recipes/http/request-deduplication.md) |
| "API blips and user sees error toast for nothing" | [`http/retry-with-backoff`](recipes/http/retry-with-backoff.md) |
| "User saves twice fast, old response overwrites new state" | [`reactivity/race-conditions`](recipes/reactivity/race-conditions.md) |
| "10,000-row list and Chrome dies" | [`components/virtual-scrolling`](recipes/components/virtual-scrolling.md) |
| "Where should this shared state live? NgRx or not?" | [`components/component-communication`](recipes/components/component-communication.md) |
| "Form fields lose data when user toggles a section" | [`forms-and-search/dynamic-forms`](recipes/forms-and-search/dynamic-forms.md) |
| "Username availability check stuck in pending forever" | [`forms-and-search/async-validation`](recipes/forms-and-search/async-validation.md) |
| "Search results jump as user types fast" | [`forms-and-search/search-engine`](recipes/forms-and-search/search-engine.md) |
| "JWT interceptor needs AuthService, AuthService needs HttpClient → cycle" | [`auth/jwt-interceptor-circular-dep`](recipes/auth/jwt-interceptor-circular-dep.md) |
| "Where do auth tokens belong — localStorage, cookie, memory?" | [`auth/token-storage-security`](recipes/auth/token-storage-security.md) |
| "F5 reload logs the user out" | [`auth/app-initialization`](recipes/auth/app-initialization.md) |
| "Sensitive action needs re-authentication ('sudo mode')" | [`auth/step-up-authentication`](recipes/auth/step-up-authentication.md) |
| "File upload needs a progress bar" | [`http/progress-tracking`](recipes/http/progress-tracking.md) |
| "Lazy modules — when to preload, when not to" | [`routing/preloading-strategy`](recipes/routing/preloading-strategy.md) |
| "Subscription cleanup boilerplate in every component" | [`reactivity/take-until-destroyed`](recipes/reactivity/take-until-destroyed.md) |
| "Embed Angular as a widget in a non-Angular site" | [`elements/widget-deployment`](recipes/elements/widget-deployment.md) |

## Phases

| Phase | Status | Description |
| --- | --- | --- |
| Phase 1 | ✅ Complete | English translation of the original 33-day Vietnamese series |
| Phase 2 | 🟡 In progress | Modernization of Phase 1 articles to v22 idioms |
| Phase 3 | ✅ Complete | 36 gap articles — topics absent from the original series |
| Recipes | 🟡 Growing | Real-world problem-solving recipes; composes concept articles |

See [`progress.md`](progress.md) for detailed status.

## Credits

This project is an English translation and modernization of ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) by Angular Vietnam. Original authors: Tiep Phan, Chau Tran, Trung Vo, Tuan Le, Khanh Tiet, Hien Pham. Released under MIT license.

See [`CREDITS.md`](CREDITS.md) for per-day attribution.

## License

MIT — see [`LICENSE`](LICENSE).
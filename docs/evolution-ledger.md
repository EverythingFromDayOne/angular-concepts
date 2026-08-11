# Evolution ledger

This is the repo spine: every place Angular changed *mechanism* between the
original series' baseline (Angular 9, 2020) and the current pinned baseline
(`@angular/core@22.1.1`). Articles' "How this evolved" sections link back
here.

Only rows supportable from content already written in this repo are seeded
below — do not add a row you cannot cite to an owning article. `Status`
mirrors that owning article's own frontmatter `status` field
(`draft` / `needs-upgrade` / `reviewed`).

| Old surface | New surface | Kind of change | Owning article | Status |
| --- | --- | --- | --- | --- |
| `@NgModule` declarations + `bootstrapModule` | Standalone components + `bootstrapApplication` | default inversion — standalone is now the default, `NgModule` is the opt-in escape hatch | [`foundations/getting-started`](concepts/foundations/getting-started.md) | draft |
| `RouterModule.forRoot(routes)` | `provideRouter(routes)` | module-based → provider-based router bootstrap | [`routing/routing`](concepts/routing/routing.md) | draft |
| Class-based guards (`implements CanActivate`) | Functional guards (`CanActivateFn` + `inject()`) | class → function; DI via injection context instead of constructor | [`routing/guards-resolvers`](concepts/routing/guards-resolvers.md) | needs-upgrade |
| `CanLoad` | `CanMatch` | renamed and broadened — matches routes (not just gates lazy-chunk loading), so it also participates in route selection | [`routing/guards-resolvers`](concepts/routing/guards-resolvers.md) | needs-upgrade |
| Zone.js-based change detection | Signals + zoneless change detection | default inversion — new apps run zoneless by default; CD triggers on signal/notification instead of patched async APIs | [`components/change-detection`](concepts/components/change-detection.md) | draft |

## Notes for authors

- Do not add rows you cannot cite to an owning article already in this repo.
- `article_id` in an owning-article link must match the linked file's own
  frontmatter `article_id`.
- This ledger is seeded, not exhaustive — most of the corpus (see
  `progress.md`) has not yet been reconciled against it.

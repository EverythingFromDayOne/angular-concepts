---
roadmap_node: "configuration"
title: "Angular Router — Feature Modules, Child Routes, and Services"
file: "routing/router-configuration.md"
source_days: [28]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Router — Feature Modules, Child Routes, and Services

Building on [Angular Router](routing.md), today we'll look at feature modules, child routes, redirects, routing modules, and key router services.

## Feature modules

With the [Day 27 sample app](https://stackblitz.com/edit/angular-100-days-of-code-day-27-router-basic), can we split the app into multiple `NgModule`s instead of one monolithic module — and still use the Router? Yes: use `RouterModule.forChild` in feature modules.

### Extract ArticleModule

Create a module and move related declarations into it:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ArticleListComponent } from './article-list/article-list.component';
import { ArticleDetailComponent } from './article-detail/article-detail.component';

@NgModule({
  imports: [CommonModule],
  declarations: [ArticleListComponent, ArticleDetailComponent],
})
export class ArticleModule {}
```

Configure routes with `forChild` instead of `forRoot` (see [routing intro](routing.md) for why):

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Routes, RouterModule } from '@angular/router';
import { ArticleListComponent } from './article-list/article-list.component';
import { ArticleDetailComponent } from './article-detail/article-detail.component';

const routes: Routes = [
  {
    path: 'article',
    component: ArticleListComponent,
  },
  {
    path: 'article/:slug',
    component: ArticleDetailComponent,
  },
];

@NgModule({
  imports: [CommonModule, RouterModule.forChild(routes)],
  declarations: [ArticleListComponent, ArticleDetailComponent],
})
export class ArticleModule {}
```

Import the feature module in `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { ArticleModule } from './article/article.module';

@NgModule({
  imports: [
    BrowserModule,
    FormsModule,
    ArticleModule, // note import order
    AppRoutingModule,
  ],
  declarations: [AppComponent],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

Navigate to `article` to see the list.

![App Feature Route](assets/day28-router-1.gif) <!-- TODO: asset -->

## Route redirects

Redirect one path to another:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: '',
    redirectTo: 'article',
    pathMatch: 'full',
  },
];
```

For redirects, `pathMatch: 'full'` is usually what you want.

### pathMatch strategies

- **`full`** — the entire URL path must match (like `==`). User wants `tiepphan.com/abc/xyz` → path `abc/xyz`; `abc/cde` does not match.
- **`prefix`** (default) — matching prefix is enough. For `tiepphan.com/abc/xyz`, path `abc` matches.

Sample: https://stackblitz.com/edit/angular-100-days-of-code-day-28-router-feature-1?file=src%2Fapp%2Farticle%2Farticle.module.ts

## Routing module pattern

Split routing into its own module — like `AppRoutingModule`. For a feature:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleListComponent,
  },
  {
    path: 'article/:slug',
    component: ArticleDetailComponent,
  },
];

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
  ],
  declarations: [],
  exports: [RouterModule],
})
export class ArticleRoutingModule {}
```

`ArticleModule` imports `ArticleRoutingModule` instead of calling `RouterModule.forChild` directly:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { ArticleRoutingModule } from './article-routing.module';

@NgModule({
  imports: [CommonModule, ArticleRoutingModule],
  declarations: [ArticleListComponent, ArticleDetailComponent],
})
export class ArticleModule {}
```

Full code: https://stackblitz.com/edit/angular-100-days-of-code-day-28-router-feature-2?file=src%2Fapp%2Farticle%2Farticle-routing.module.ts

## Child routes

These routes share a prefix:

**Flat style**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleListComponent,
  },
  {
    path: 'article/:slug',
    component: ArticleDetailComponent,
  },
];
```

**Parent–child style** (equivalent):

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: 'article',
    children: [
      {
        path: '',
        component: ArticleListComponent,
      },
      {
        path: ':slug',
        component: ArticleDetailComponent,
      },
    ],
  },
];
```

A parent route can also activate a **layout component** that contains a `router-outlet` for children:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleComponent, // layout component
    children: [
      {
        path: '',
        component: ArticleListComponent,
      },
      {
        path: ':slug',
        component: ArticleDetailComponent,
      },
    ],
  },
];
```

Full code: https://stackblitz.com/edit/angular-100-days-of-code-day-28-router-feature-3?file=src%2Fapp%2Farticle%2Farticle-routing.module.ts

## ActivatedRoute service

> Provides access to information about a route associated with a component that is loaded in an outlet. [ActivatedRoute](https://angular.io/api/router/ActivatedRoute)

Use it to read params, query strings, and route data.

### Retrieve params

From [routing.md](routing.md) — snapshot approach:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
export class ArticleDetailComponent implements OnInit {
  article$: Observable<Article>;
  constructor(private _route: ActivatedRoute, private _api: ArticleService) {}

  ngOnInit(): void {
    let slug = this._route.snapshot.paramMap.get('slug');
    this.article$ = this._api.getArticleBySlug(slug);
  }
}
```

Observable approach (better when the same component instance is reused):

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
export class ArticleDetailComponent implements OnInit {
  article$: Observable<Article>;
  constructor(private _route: ActivatedRoute, private _api: ArticleService) {}

  ngOnInit(): void {
    this.article$ = this._route.paramMap.pipe(
      map((params) => params.get('slug')),
      switchMap((slug) => this._api.getArticleBySlug(slug))
    );
  }
}
```

> New to RxJS? See the [RxJS articles](../reactivity/rxjs/rxjs.md).

**Why Observable instead of snapshot?**

By default the router tries to **reuse** a component when configuration matches. Navigating from `/article` to `/article/bai-viet-1` creates a new `ArticleDetailComponent` — snapshot and `paramMap` agree.

Navigating from `/article/bai-viet-1` to `/article/bai-viet-2` reuses the same instance. **Snapshot is frozen** at creation time; **`paramMap` emits** the new `slug`.

Choose based on whether params can change without recreating the component.

![paramMap Observable](assets/day28-router-5.gif) <!-- TODO: asset -->

![paramMap snapshot](assets/day28-router-6.gif) <!-- TODO: asset -->

Samples:

- https://stackblitz.com/edit/angular-100-days-of-code-day-28-router-feature-4?file=src/app/article/article-detail/article-detail.component.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-28-router-feature-5?file=src%2Fapp%2Farticle%2Farticle-detail%2Farticle-detail.component.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-28-router-feature-6?file=src%2Fapp%2Farticle%2Farticle-detail%2Farticle-detail.component.ts

### Query params, route data, and more

Besides `paramMap`, use `queryParamMap` for query strings. For URL `tiepphan.com/page/2?sort=createdDate`:

```ts
this._route.snapshot.queryParamMap.get('sort');
```

Or observe:

```ts
queryParamMap.subscribe((query) => {
  console.log(query.get('sort'));
});
```

Route `data` and other APIs are documented on [ActivatedRoute](https://angular.io/api/router/ActivatedRoute).

## Router service

> A service that provides navigation and URL manipulation capabilities. [Router](https://angular.io/api/router/Router)

Navigate programmatically after an action succeeds:

```ts
navigateByUrl(url: string | UrlTree, extras: NavigationExtras = { skipLocationChange: false }): Promise<boolean>;
navigate(commands: any[], extras: NavigationExtras = { skipLocationChange: false }): Promise<boolean>;
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
class SomeComponent {
  constructor(private router: Router) {}
  onClick() {
    // do something
    this.router.navigate(['/article']);
  }
}
```

Listen to navigation events:

```ts
this.router.events
  .pipe(filter((e) => e instanceof NavigationEnd))
  .subscribe((e) => {
    console.log(e);
  });
```

## Summary

Feature modules with `forChild`, redirects, routing modules, child routes, `ActivatedRoute`, and `Router` are essential for real Angular apps. Read the official docs and router source when you need deeper detail.

## References

- [Angular Router guide](https://angular.io/guide/router)
- [Angular Router series — Tiep Phan (Vietnamese)](https://www.tiepphan.com/angular-router-series/)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

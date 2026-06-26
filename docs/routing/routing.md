---
roadmap_node: "routing"
title: "Angular Router"
file: "routing/routing.md"
source_days: [27]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Router

In the old server-rendered web model, opening a site meant the server sent a full HTML page. Navigating — say from a shop homepage to a shoes category — triggered another full page load: `<html>`, `<head>`, scripts, and body content. Every click refreshed the entire site (postback in some stacks).

![Postback](assets/day-27-router-01.gif) <!-- TODO: asset -->

That spinner on the tab often meant a full server round-trip.

**Single Page Applications** changed that. The shell ships once in JavaScript; navigation usually fetches data via APIs and updates part of the view (AJAX). In an Angular SPA you rarely see the browser tab spinner on each interaction.

How does Angular know which view to show? **[Angular Router](https://angular.io/guide/router)**.

As users move through the app, they visit different views you configure. Open `tiepphan.com`, see a post list; open `tiepphan.com/bai-nay-hay-lam` and the correct article must appear when you share that link.

The app must:

- Support URLs like `tiepphan.com/bai-nay-hay-lam`
- Show an article layout — not the home list
- Load the **same** article you viewed, not a random one

Let's build that.

## Final result

When you finish this walkthrough, the app looks like this:

![Step 6](assets/day-27-router-06.gif) <!-- TODO: asset -->

Requirements:

- Home shows a list of articles
- Clicking an article opens its detail view
- Copying the detail URL works in another browser
- Invalid URLs show an error (covered in later articles)

## Before you start

Helpful background:

- Component
- Template
- Angular CLI

## Create an app with routing

```bash
ng new day27-routing --routing
```

Note:

- `day27-routing`: project name
- `--routing`: enables the Router scaffold

The CLI may ask about styles — pick SCSS, CSS, or your preference. This guide uses SCSS.

![Step 2](assets/day-27-router-02.png) <!-- TODO: asset -->

### Add components for routing

We need a list component and a detail component.

```bash
ng generate component article-list
```

```bash
ng generate component article-detail
```

![Step 3](assets/day-27-router-03.png) <!-- TODO: asset -->

### Basic router configuration

With `--routing`, the CLI creates `AppRoutingModule` and imports it into `AppModule`.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    AppRoutingModule, // created automatically by the CLI
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

Three main pieces when working with the Router:

1. Import `RouterModule` and `Routes` in your routing module (`AppRoutingModule`):

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
```

`AppRoutingModule` imports and re-exports `RouterModule`, so feature modules that import `AppRoutingModule` get router directives without importing `RouterModule` again.

`RouterModule` provides `forRoot` and `forChild`:

- `forRoot` — call **once** in the root routing module; configures and initializes the router and its singleton services ([see dependency injection](../../dependency-injection/dependency-injection.md)).
- `forChild` — use in feature modules for child route tables.

Calling `forRoot` multiple times can create duplicate router services and unpredictable behavior. [More on Stack Overflow](https://stackoverflow.com/a/44680396/3375906).

2. Define `routes`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: 'detail',
    component: ArticleDetailComponent,
  },
  {
    path: '',
    component: ArticleListComponent,
  },
];
```

Each `Route` needs `path` and `component`. Empty `path` is the default; `/detail` loads `ArticleDetailComponent`.

3. Use routes in the app:

```html
<ul class="nav nav-pills card-header-pills">
  <li class="nav-item">
    <a class="nav-link" routerLink="/">Home</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" routerLink="detail">Detail</a>
  </li>
</ul>
<router-outlet></router-outlet>
```

`routerLink` sets the URL; `router-outlet` is where the matched component renders.

![Step 4](assets/day-27-router-04.gif) <!-- TODO: asset -->

### Route order matters

Put more specific routes before generic ones. Example:

- `/detail/123/edit` — edit form for item 123
- `/detail/123` — detail for item 123

Configure `/detail/123/edit` **before** `/detail/123`.

## Reading data from the route

Real apps pass data via the URL — e.g. article `id` or `slug` for the detail view.

Sample data and service:

```ts
const Articles: Article[] = [
  {
    id: '1',
    slug: 'bai-viet-1',
    title: 'Bai viet 1',
    content: 'Day la noi dung bai viet 1',
    updateAt: '2020-07-06T13:26:31.785Z',
  },
  {
    id: '2',
    slug: 'bai-viet-2',
    title: 'Bai viet 2',
    content: 'Day la noi dung bai viet 2 nhe',
    updateAt: '2020-07-15:00:00.000Z',
  },
];
@Injectable({
  providedIn: 'root',
})
export class ArticleService {
  getArticles(): Observable<Article[]> {
    return of(Articles).pipe(delay(500));
  }
}
```

List component:

```ts
export class ArticleListComponent implements OnInit {
  articles$: Observable<Article[]>;
  constructor(private _api: ArticleService) {}

  ngOnInit(): void {
    this.articles$ = this._api.getArticles();
  }
}
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div class="row" *ngIf="articles$ | async as articles">
  <div class="col-md-3" *ngFor="let article of articles">
    <div class="card text-center">
      <div class="card-header">{{ article.title }}</div>
      <div class="card-body">
        <p class="card-text">{{ article.content }}</p>
        <a [routerLink]="article.slug" class="btn btn-primary">
          View {{ article.title }}
        </a>
      </div>
    </div>
  </div>
</div>
```

![Step 5](assets/day-27-router-05.png) <!-- TODO: asset -->

Buttons won't work until we add a parameterized route:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
const routes: Routes = [
  {
    path: ':slug',
    component: ArticleDetailComponent,
  },
  {
    path: '',
    component: ArticleListComponent,
  },
];
```

`:slug` is route parameter syntax. In the detail component, inject `ActivatedRoute` and read the snapshot:

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

Reloading the detail page still resolves `slug` and loads the correct article. Error handling for missing articles comes in later guides.

![Step 6](assets/day-27-router-06.gif) <!-- TODO: asset -->

## Summary

You should now understand:

- How to configure the router
- How to read route parameters
- Why route order in the `Routes` array matters

## References

- [Angular Router guide](https://angular.io/guide/router)
- [Angular Router series — Tiep Phan (Vietnamese)](https://www.tiepphan.com/angular-router-series/)

## Code example

https://stackblitz.com/edit/angular-100-days-of-code-day-27-router-basic

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

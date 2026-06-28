---
roadmap_node: "routing"
title: "Angular Router"
file: "routing/routing.md"
source_days: [27]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Router

> **⚡ What changed since the original**
>
> This article was first written for Angular 9 (2020). The Router's **mental model** — routes as a config tree, `<router-outlet>` as the rendering slot, `routerLink` for navigation — is unchanged in v22. What changed is **how you configure and consume the router**:
>
> - **`provideRouter(routes)` replaces `RouterModule.forRoot(routes)`.** Routes now live in a plain `app.routes.ts` file and are wired up in `bootstrapApplication()`'s providers array — no `AppRoutingModule`, no `forRoot` / `forChild` split.
> - **`AppModule` is gone.** Standalone components are the default; `bootstrapApplication(AppComponent, appConfig)` replaces `platformBrowserDynamic().bootstrapModule(AppModule)`.
> - **`*ngIf` / `*ngFor` → `@if` / `@for`** in templates.
> - **`constructor(private _route: ActivatedRoute)` → `private _route = inject(ActivatedRoute)`** at the class field.
> - **Component input binding (v16+)** — with `withComponentInputBinding()` enabled, route params, query params, and resolver data flow directly as `input()` signals on the routed component. No more `ActivatedRoute.snapshot.paramMap.get('slug')` boilerplate in most cases.
> - **Functional guards, resolvers, and matchers** replaced class-based ones — covered in detail in [Guards & Resolvers](../routing/guards-resolvers.md).
> - **Lazy loading uses `loadComponent`** for standalone components — covered in [Lazy Loading](../routing/lazy-loading.md).
>
> Each Angular 9 code block below is preserved with its `<!-- legacy -->` marker and followed by a v22 equivalent. The mechanism reflection at the end focuses on the one change that touches everything else: routes used to be configured by a module that owned both declarations and providers; they're now configured by a function call that returns environment providers.
>
> **See also**: [Router Configuration](../routing/router-configuration.md) · [Lazy Loading](../routing/lazy-loading.md) · [Guards & Resolvers](../routing/guards-resolvers.md) · [Router Link](../routing/router-link.md) · [Router Outlets](../routing/router-outlets.md) · [Dependency Injection](../dependency-injection/dependency-injection.md)

---

In the old server-rendered web model, opening a site meant the server sent a full HTML page. Navigating — say from a shop homepage to a shoes category — triggered another full page load: `<html>`, `<head>`, scripts, and body content. Every click refreshed the entire site (postback in some stacks).

![Postback](assets/day-27-router-01.gif) <!-- TODO: asset -->

That spinner on the tab often meant a full server round-trip.

**Single Page Applications** changed that. The shell ships once in JavaScript; navigation usually fetches data via APIs and updates part of the view (AJAX). In an Angular SPA you rarely see the browser tab spinner on each interaction.

How does Angular know which view to show? **[Angular Router](https://angular.dev/guide/routing)**.

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

The Angular 9 scaffold and the v22 scaffold look very different on disk. In v22, `ng new --routing` produces:

```
src/
├── app/
│   ├── app.component.ts       # Standalone component with RouterOutlet imported
│   ├── app.config.ts          # ApplicationConfig with provideRouter(routes)
│   ├── app.routes.ts          # The Routes array — just a plain TS file
│   └── ...
└── main.ts                    # bootstrapApplication(AppComponent, appConfig)
```

No `app.module.ts`, no `app-routing.module.ts`. The pieces that used to live in `AppRoutingModule` are now plain data (`app.routes.ts`) and a provider call (in `app.config.ts`).

### Add components for routing

```bash
ng generate component article-list
```

```bash
ng generate component article-detail
```

In v22, `ng g component` produces standalone components by default — no flag needed.

![Step 3](assets/day-27-router-03.png) <!-- TODO: asset -->

### Basic router configuration

With `--routing`, the CLI does the wiring for you. In Angular 9 it generated an `AppRoutingModule` and imported it into `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// app.module.ts (Angular 9)
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

In v22 the CLI generates a flat config object and a routes file — no modules:

```ts
// ── v22 equivalent: app.config.ts + main.ts ───────────────────────────────
// app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    // Other app-wide providers (HttpClient, animations, etc.) go here.
  ],
};

// main.ts
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

bootstrapApplication(AppComponent, appConfig)
  .catch(err => console.error(err));
```

The Angular 9 article identified three main pieces when working with the Router. The v22 pieces are different — let's compare both.

**1. Wire up the router with providers** (legacy required a routing module):

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// app-routing.module.ts (Angular 9)
const routes: Routes = [];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
```

`AppRoutingModule` imported and re-exported `RouterModule`, so feature modules that imported `AppRoutingModule` got router directives without importing `RouterModule` again.

`RouterModule` provided `forRoot` and `forChild`:

- `forRoot` — called **once** in the root routing module; configured and initialized the router and its singleton services ([see dependency injection](../dependency-injection/dependency-injection.md)).
- `forChild` — used in feature modules for child route tables.

Calling `forRoot` multiple times could create duplicate router services and unpredictable behavior.

```ts
// ── v22 equivalent: provideRouter() in app.config.ts ──────────────────────
import { ApplicationConfig } from '@angular/core';
import { provideRouter, withComponentInputBinding, withViewTransitions } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(
      routes,
      // Feature functions — opt-in capabilities, replacing what used to be
      // configuration flags on RouterModule.forRoot()'s second argument.
      withComponentInputBinding(),  // route params flow as @Input() signals
      withViewTransitions(),        // use the browser's View Transitions API
    ),
  ],
};

// app.routes.ts
import { Routes } from '@angular/router';
export const routes: Routes = [];
```

A few things shifted here:

- **`forRoot` / `forChild` are gone.** `provideRouter()` is called once at bootstrap. Child route trees for lazy-loaded features are now just `Routes` arrays passed via `loadChildren` — see [Lazy Loading](../routing/lazy-loading.md).
- **Feature functions replace config flags.** `withComponentInputBinding()`, `withViewTransitions()`, `withHashLocation()`, `withInMemoryScrolling()`, `withPreloading()`, `withDebugTracing()` — each is a tree-shakable opt-in. If you don't call `withDebugTracing()`, none of its code ships. Compare to `RouterModule.forRoot(routes, { enableTracing: true })` where the flag flipped a value but the supporting code was always bundled.
- **No re-export gymnastics.** Components that want `routerLink` and `<router-outlet>` just import `RouterLink` and `RouterOutlet` directly. We'll see that in the next step.

**2. Define `routes` (this part barely changed):**

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

```ts
// ── v22 equivalent: identical shape, just lives in app.routes.ts ──────────
import { Routes } from '@angular/router';
import { ArticleListComponent } from './article-list/article-list.component';
import { ArticleDetailComponent } from './article-detail/article-detail.component';

export const routes: Routes = [
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

Each `Route` still needs `path` and `component` (or `loadComponent` for lazy loading). Empty `path` is still the default; `/detail` still loads `ArticleDetailComponent`. The route config object is essentially the same — what changed is its surroundings, not the data itself.

**3. Use routes in the app:**

```html
<!-- app.component.html — template unchanged -->
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

`routerLink` still sets the URL; `router-outlet` is still where the matched component renders. What changed is how the component declares its dependencies on those directives:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// app.component.ts (Angular 9) — RouterModule wired up via AppRoutingModule
@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {}
```

```ts
// ── v22 equivalent: standalone component imports the directives it uses ───
import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  imports: [RouterLink, RouterOutlet],
})
export class AppComponent {}
```

The Angular 9 version worked because `AppRoutingModule` (transitively imported into `AppModule`) re-exported `RouterModule`, which declared `RouterLink` and `RouterOutlet`. In v22 the component imports them directly — no module-level plumbing, no implicit re-exports.

![Step 4](assets/day-27-router-04.gif) <!-- TODO: asset -->

### Route order matters

Put more specific routes before generic ones. Example:

- `/detail/123/edit` — edit form for item 123
- `/detail/123` — detail for item 123

Configure `/detail/123/edit` **before** `/detail/123`. This rule hasn't changed in v22 — the router still uses a first-match strategy, so the more specific pattern needs to be defined first.

## Reading data from the route

Real apps pass data via the URL — e.g. article `id` or `slug` for the detail view.

Sample data and service:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
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

`@Injectable({ providedIn: 'root' })` is unchanged in v22 — services still register against the root injector and stay tree-shakable.

### Article list component

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// article-list.component.ts (Angular 9)
export class ArticleListComponent implements OnInit {
  articles$: Observable<Article[]>;
  constructor(private _api: ArticleService) {}

  ngOnInit(): void {
    this.articles$ = this._api.getArticles();
  }
}
```

```ts
// ── v22 equivalent: inject() + standalone + signal read ───────────────────
import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { ArticleService } from './article.service';

@Component({
  selector: 'app-article-list',
  templateUrl: './article-list.component.html',
  styleUrl: './article-list.component.scss',
  imports: [RouterLink, AsyncPipe], // AsyncPipe only if you keep the | async path
})
export class ArticleListComponent {
  private readonly _api = inject(ArticleService);

  // Option A: keep the observable + async pipe (still valid in v22).
  readonly articles$ = this._api.getArticles();

  // Option B (recommended in v22): convert to a signal and read it as articles().
  readonly articles = toSignal(this._api.getArticles(), { initialValue: [] });
}
```

The signal version drops the `AsyncPipe` import and lets the template read `articles()` like any other signal — no pipe, no `| async`, no nullable.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<!-- article-list.component.html (Angular 9) -->
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

```html
<!-- v22 equivalent: @if / @for, signal read with the toSignal version -->
@if (articles(); as list) {
  <div class="row">
    @for (article of list; track article.id) {
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-header">{{ article.title }}</div>
          <div class="card-body">
            <p class="card-text">{{ article.content }}</p>
            <a [routerLink]="article.slug" class="btn btn-primary" [attr.data-testid]="'article-link-' + article.id">
              View {{ article.title }}
            </a>
          </div>
        </div>
      </div>
    }
  </div>
}
```

Three things to notice:

- `@for` requires a `track` expression. The Angular 9 `*ngFor` defaulted to object identity tracking; `@for` makes the choice explicit. Use the stable id (`article.id`) — never the index — for reliable item reuse.
- `@if (articles(); as list)` is the new syntax for "evaluate this expression, alias the result, render this block if truthy."
- `data-testid` replaces the old `ng-reflect-*` selectors that tests used to scrape (those reflection attributes were removed in Angular 20).

![Step 5](assets/day-27-router-05.png) <!-- TODO: asset -->

### Add the parameterized route

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

```ts
// ── v22 equivalent: identical shape, plus a `title` for the browser tab ───
export const routes: Routes = [
  {
    path: ':slug',
    component: ArticleDetailComponent,
    title: 'Article detail', // v15+ — sets document.title automatically
  },
  {
    path: '',
    component: ArticleListComponent,
    title: 'Articles',
  },
];
```

`:slug` is still the route parameter syntax. The router still uses a first-match strategy, so `:slug` (which matches almost any single segment) must come **before** the empty path or it'll swallow the home route.

### Article detail component — two ways to read the param

This is where v22 changes the most. In Angular 9, every routed component injected `ActivatedRoute` and pulled values out of `paramMap`. In v22, that still works — but if you've enabled `withComponentInputBinding()`, you can just declare an `input()` and the router will fill it in.

**Approach A: read via `ActivatedRoute` (works in every Angular version)**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// Angular 9: constructor injection, snapshot read
export class ArticleDetailComponent implements OnInit {
  article$: Observable<Article>;
  constructor(private _route: ActivatedRoute, private _api: ArticleService) {}

  ngOnInit(): void {
    let slug = this._route.snapshot.paramMap.get('slug');
    this.article$ = this._api.getArticleBySlug(slug);
  }
}
```

```ts
// ── v22 variant: inject(), reactive paramMap, no ngOnInit ─────────────────
import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { switchMap } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-article-detail',
  templateUrl: './article-detail.component.html',
})
export class ArticleDetailComponent {
  private readonly _route = inject(ActivatedRoute);
  private readonly _api = inject(ArticleService);

  // Reactive read — if the router navigates between two different :slug
  // values without destroying the component (rare but possible), this
  // re-runs. snapshot.paramMap doesn't.
  readonly article = toSignal(
    this._route.paramMap.pipe(
      switchMap(params => this._api.getArticleBySlug(params.get('slug')!))
    ),
  );
}
```

The snapshot read still works in v22, but the observable-pipe read is more correct because the router can reuse a component instance across navigations when only the param changes. If you read the snapshot once in `ngOnInit`, you'll show stale data on the second navigation. The observable version sidesteps that class of bug entirely.

**Approach B: receive the param as a signal input** (v22 idiomatic, requires `withComponentInputBinding()`)

```ts
// ── v22 idiom: route params flow as @Input() / input() signals ────────────
import { Component, computed, inject, input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { switchMap } from 'rxjs';
import { ArticleService } from './article.service';

@Component({
  selector: 'app-article-detail',
  templateUrl: './article-detail.component.html',
})
export class ArticleDetailComponent {
  private readonly _api = inject(ArticleService);

  // The router fills this in from the :slug path segment.
  // No ActivatedRoute, no paramMap.get(), no ngOnInit.
  readonly slug = input.required<string>();

  // React to slug changes: build an observable from the signal, then convert
  // back to a signal for the template.
  readonly article = toSignal(
    toObservable(this.slug).pipe(
      switchMap(slug => this._api.getArticleBySlug(slug))
    ),
  );
}

// Don't forget the import:
import { toObservable } from '@angular/core/rxjs-interop';
```

This is the same flow that resolver data, query params, and the matrix params take — they all map to `input()` signals on the routed component. Enable it once in `provideRouter(routes, withComponentInputBinding())` and every routed component gets the capability. This eliminates the most repetitive bit of router code in Angular: the inject-the-route-then-read-the-paramMap dance.

Whichever approach you use, reloading the detail page resolves `slug` and loads the correct article. Error handling for missing articles is covered in [Guards & Resolvers](../routing/guards-resolvers.md).

![Step 6](assets/day-27-router-06.gif) <!-- TODO: asset -->

---

## Mechanism reflection — how router configuration evolved

The Router's runtime behavior — URL matching, outlet rendering, navigation lifecycle, guard ordering — is essentially unchanged since Angular 9. What changed substantially is **how the router gets configured into your app**, and that change is one expression of a much broader shift: configuration moved from NgModule providers to environment providers.

### The Angular 9 model — `RouterModule.forRoot()` and `ModuleWithProviders`

In Angular 9, you couldn't just hand the router a list of routes. You had to wrap them in a module:

```ts
@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
```

The mechanism is worth unpacking. `RouterModule.forRoot(routes)` is a **static method** that returns a `ModuleWithProviders<RouterModule>` — a small object literal containing two fields:

```ts
// Approximate shape, simplified for clarity
{
  ngModule: RouterModule,           // the module to import
  providers: [                       // the providers to register
    Router,
    UrlSerializer,
    { provide: ROUTES, multi: true, useValue: routes },
    // ... lots more
  ]
}
```

When `AppModule` imported `AppRoutingModule`, which itself imported the `ModuleWithProviders` from `forRoot(routes)`, Angular's compiler:

1. Hoisted the providers up to `AppModule`'s injector (because that's where `forRoot` providers always landed — see the `forRoot` rule about calling it exactly once)
2. Registered `Router` and friends as singletons in the root injector
3. Made the `routes` value available via the `ROUTES` multi-provider token, which the `Router` then read at startup

The `forRoot` vs `forChild` distinction existed because `forRoot` returned the **services + the routes**, while `forChild` returned **only the routes** (no Router instance, because there must be only one). Calling `forRoot` from a lazy-loaded module created a second Router instance with its own state — hence the warning in the original article.

This pattern — a module exposing static `forRoot` / `forSomething` methods that return `ModuleWithProviders` — was Angular's way of giving libraries a configurable entry point. `HttpClientModule`, `NgxsModule`, `MatPaginatorModule`, `EffectsModule` all used it. It worked, but it had downsides:

- **Couples configuration to module imports.** The only way to provide router config was to import a module.
- **Easy to misuse.** Calling `forRoot` twice was a silent bug; calling `forChild` outside a lazy boundary was another.
- **Bad for tree-shaking.** Features were bundled inside the module whether you opted into them or not. `enableTracing: true` flipped a flag, but the tracing infrastructure was always there.

### The v22 model — `provideRouter()` and `EnvironmentProviders`

In v22, `provideRouter(routes)` is just a function. It returns an `EnvironmentProviders` value — a typed bundle of providers that the framework knows how to install into an environment injector:

```ts
// Approximate shape, simplified for clarity
function provideRouter(routes: Routes, ...features: RouterFeatures[]): EnvironmentProviders {
  return makeEnvironmentProviders([
    Router,
    UrlSerializer,
    { provide: ROUTES, multi: true, useValue: routes },
    ...features.flatMap(f => f.providers),  // only the features you opted into
  ]);
}
```

You pass that bundle to `bootstrapApplication(AppComponent, { providers: [provideRouter(routes)] })`. The framework calls `makeEnvironmentInjector()`, sees the `EnvironmentProviders` token, and installs everything into the root environment injector — same end state as Angular 9's "providers hoisted to AppModule's injector," but reached by a function call instead of a module import.

This sounds like a cosmetic change, but it unlocks several things:

- **Feature functions are tree-shakable.** `withDebugTracing()`, `withViewTransitions()`, `withComponentInputBinding()` each contribute their own providers. If you don't call them, their code doesn't ship.
- **Configuration composes with normal JavaScript.** Want to assemble providers conditionally based on environment? Just use an `if` statement, push into an array, and pass it to `provideRouter`. There's no module import that has to be statically resolvable.
- **No `forRoot` / `forChild` ambiguity.** `provideRouter` is called once at bootstrap. Lazy routes are just `Routes` arrays passed via `loadChildren` — they don't have to invoke a special "child" form.
- **Same pattern across the framework.** `provideHttpClient()`, `provideAnimationsAsync()`, `provideStore()` (NgRx 16+), `provideStoreDevtools()`, `provideClientHydration()`, `provideRouterStore()` — they all return `EnvironmentProviders`. Once you understand the pattern, every Angular library uses it.

### Component input binding — what changed mechanically

`withComponentInputBinding()` is the v22 feature that maps route data onto component inputs. The mechanism is small and elegant:

1. When the router activates a route, it constructs the component instance.
2. With `withComponentInputBinding` enabled, the router inspects the component's input metadata — the same `input()` declarations the template binder uses.
3. For each input name (`slug`, `id`, etc.), the router checks the current `ActivatedRoute` for:
   - A path parameter with that name
   - A query parameter with that name
   - A resolver data key with that name
   - A static `data` key with that name
4. The first match wins, and the value is written to the input — same as if a parent template had bound `[slug]="..."`.
5. The router subscribes to changes in the `ActivatedRoute` and re-pushes new values whenever they change, so signal inputs update reactively across navigations.

The pre-v16 alternative was the boilerplate every routed component carried: inject `ActivatedRoute`, subscribe to `paramMap`, manually thread the value into a state property, unsubscribe on destroy. Component input binding compresses all of that into `slug = input.required<string>()`. The router does the rest.

This is also why `input()` matters even for routed components that don't have a parent template — the binding contract is the same, and the router is "just another caller" of the input setter from the framework's perspective.

### What stayed the same

The Router's runtime behavior is essentially identical to Angular 9:

- URL matching is the same first-match-wins algorithm
- Guard ordering (`canMatch`, `canActivate`, `canActivateChild`, `canDeactivate`, `canLoad`) is the same
- `RouterEvent` lifecycle (`NavigationStart`, `RoutesRecognized`, `NavigationEnd`, `NavigationError`, `NavigationCancel`) is unchanged
- `ActivatedRoute`, `Router`, `UrlTree`, `Routes` — all the same types, same APIs
- `<router-outlet>` and `routerLink` work exactly the same in templates

If you understood routing in Angular 9, you understand routing in v22. The wiring is what changed, not the engine.

### What got removed or deprecated

- **`canLoad` is deprecated** in favor of `canMatch`. `canMatch` runs earlier in the navigation pipeline and handles more edge cases correctly.
- **Class-based guards (`CanActivate`, `CanDeactivate`, `Resolve` interfaces)** are deprecated in favor of functional `CanActivateFn`, `CanDeactivateFn<T>`, `ResolveFn<T>`. The functional forms can call `inject()` directly — no class needed. See [Guards & Resolvers](../routing/guards-resolvers.md).
- **`loadChildren` returning a string path** was removed years ago — it now returns a function that returns a Promise of `Routes` or a standalone component.
- **`RouterModule.forRoot()` / `RouterModule.forChild()`** are not deprecated, but they're considered legacy. New code should use `provideRouter()`.

---

## Summary

You should now understand:

- How to configure the router with `provideRouter()` in v22, or `RouterModule.forRoot()` in older Angular
- How standalone components import `RouterLink` and `RouterOutlet` directly
- How to read route parameters two ways — `inject(ActivatedRoute)` (works everywhere) or `input()` with `withComponentInputBinding()` (v16+, less boilerplate)
- Why route order in the `Routes` array still matters — first match wins
- How `provideRouter()` returning `EnvironmentProviders` is part of the broader move from NgModule-as-configuration-scope to function-call-as-configuration

## See also

- [Router Configuration](../routing/router-configuration.md) — `provideRouter()` feature functions in depth
- [Lazy Loading](../routing/lazy-loading.md) — `loadComponent` and `loadChildren` for standalone routes
- [Guards & Resolvers](../routing/guards-resolvers.md) — functional `CanActivateFn`, `CanMatchFn`, `ResolveFn`
- [Router Link](../routing/router-link.md) — `[routerLink]`, `[queryParams]`, `routerLinkActive`
- [Router Outlets](../routing/router-outlets.md) — named outlets, multiple outlets, hydration interplay

## References

- [Angular Routing guide (angular.dev)](https://angular.dev/guide/routing)
- [`provideRouter` API reference](https://angular.dev/api/router/provideRouter)
- [Component input binding (angular.dev)](https://angular.dev/api/router/withComponentInputBinding)
- [Angular Router series — Tiep Phan (Vietnamese)](https://www.tiepphan.com/angular-router-series/)

## Code example

https://stackblitz.com/edit/angular-100-days-of-code-day-27-router-basic

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project. Modernized to Angular v22 in the Phase 2 upgrade pass.*

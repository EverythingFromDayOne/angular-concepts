---
roadmap_node: "guards-resolvers"
title: "Angular Router — Guards and Resolvers"
file: "routing/guards-resolvers.md"
source_days: [30, 31, 32]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Router — Guards and Resolvers

Most websites are split into pages, and some pages require permission before you can open them.

On traditional server-rendered apps, the user navigates to a URL and the server checks whether the request is valid before returning the page.

On Single Page Apps (SPAs) built with Angular (or React, Vue, and so on), resources are loaded once; the app calls data sources and renders the matching component/view without a full page reload. That means **frontend code** participates in access checks before a route is shown.

## Angular Router navigation cycle

![Angular Router Navigation Cycle](assets/router-navigation-cycle.png) <!-- TODO: asset -->

Angular Router performs five core operations. When it receives a URL, it:

1. Applies redirects
2. Recognizes router states
3. Runs guards and resolves data
4. Activates the needed components
5. Manages navigation

Our demo app uses this routing setup:

**app-routing.module.ts**

```ts
const routes: Routes = [
  {
    path: 'admin',
    loadChildren: () =>
      import('./admin/admin.module').then((m) => m.AdminModule),
  },
  {
    path: '',
    redirectTo: 'article',
    pathMatch: 'full',
  },
];
```

**article-routing.module.ts**

```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleComponent,
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

**admin-routing.module.ts**

```ts
const routes: Routes = [
  {
    path: '',
    component: AdminComponent,
    children: [
      {
        path: '',
        component: AdminArticleListComponent,
      },
    ],
  },
];
```

### Navigation

The first operation is **navigation** (applying redirects).

A plain `<a href>` sends a request to the URL. Angular Router provides `routerLink` as a declarative alternative. You can also navigate imperatively with `Router.navigate()` or `Router.navigateByUrl()`.

Navigation usually happens by changing the URL through one of those mechanisms.

In our demo (https://stackblitz.com/edit/angular-100-days-of-code-day-30), navigation happens when you go from Article List `/article` to Article Detail `/article/:slug`.

![Demo navigation](assets/day30-router-01.gif) <!-- TODO: asset -->

After this step the Router emits **NavigationStart**.

### Recognizing router states

The second operation is **recognizing router states**. The Router runs algorithms such as backtracking and depth-first matching to find a route that fits the target URL. See [The Powerful URL Matching Engine of Angular Router](https://vsavkin.com/the-powerful-url-matching-engine-of-angular-router-775dad593b03).

You may be redirected to another URL, but you end in one of two cases: no matching route (error), or a recognized route.

For example, navigating to `/` redirects to `/article` and is recognized. Navigating to `/something-not-present` yields `Error: Cannot match any routes. URL Segment: 'something-not-present'`.

When matching finishes, you get a `RouterState` with activated route info — linked component, params, data, and more. See [ActivatedRoute](https://angular.io/api/router/ActivatedRoute).

The Router then emits **RoutesRecognized**.

### Running guards

This is the operation we'll focus on first.

At this point you have a _future router state_. The Router checks whether you're allowed to go there.

You can attach multiple guards. Navigation continues only if **every** guard returns `true`, `Promise<true>`, or `Observable<true>`. If any guard returns `false`, `Promise<false>`, `Observable<false>`, or a [`UrlTree`](https://angular.io/api/router/UrlTree), access is denied — or a new navigation starts to the `UrlTree` the guard returned.

The Router emits **GuardsCheckStart** and **GuardsCheckEnd**.

In our app, guards make sense for `/admin`, for editing an article, or for leaving an edit page while unsaved changes exist.

### Resolving data

After guards pass, the Router runs **resolvers** so you can prefetch data before anything renders.

Events: **ResolveStart**, **ResolveEnd**.

Resolver output is merged into the `data` property of `ActivatedRoute`.

When all resolvers finish, the Router activates components in the configured outlets.

### Activating components

The Router activates components bound to activated routes — creating or reusing instances and rendering them in the matching `router-outlet` (default: primary `<router-outlet>` without a `name`).

Events: **ActivationStart**, **ActivationEnd**, **ChildActivationStart**, **ChildActivationEnd**.

When navigation completes, **NavigationEnd** fires — useful for post-navigation side effects.

The Router updates the browser address bar unless `skipLocationChange = true`.

### Managing navigation

From here the Router keeps listening. The next URL change starts the cycle again.

![Navigation Logs](assets/day30-router-03.png) <!-- TODO: asset -->

## Route guards

Route guards answer: **Am I allowed to navigate to this URL?**

> If all guards return true, navigation will continue. If any guard returns false, navigation will be cancelled. If any guard returns a UrlTree, current navigation will be cancelled and a new navigation will be kicked off to the UrlTree returned from the guard.

Angular Router provides:

**Activate components:**

```ts
interface CanActivate {
  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ):
    | Observable<boolean | UrlTree>
    | Promise<boolean | UrlTree>
    | boolean
    | UrlTree;
}
```

```ts
interface CanActivateChild {
  canActivateChild(
    childRoute: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ):
    | Observable<boolean | UrlTree>
    | Promise<boolean | UrlTree>
    | boolean
    | UrlTree;
}
```

**Deactivate components:**

```ts
interface CanDeactivate<T> {
  canDeactivate(
    component: T,
    currentRoute: ActivatedRouteSnapshot,
    currentState: RouterStateSnapshot,
    nextState?: RouterStateSnapshot
  ):
    | Observable<boolean | UrlTree>
    | Promise<boolean | UrlTree>
    | boolean
    | UrlTree;
}
```

**Load children (lazy routes):**

```ts
interface CanLoad {
  canLoad(
    route: Route,
    segments: UrlSegment[]
  ):
    | Observable<boolean | UrlTree>
    | Promise<boolean | UrlTree>
    | boolean
    | UrlTree;
}
```

### CanActivate

Suppose only the article author may edit their post. Routing might look like:

```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleComponent,
    children: [
      {
        path: '',
        component: ArticleListComponent,
      },
      {
        path: ':slug',
        component: ArticleDetailComponent,
      },
      {
        path: ':slug/edit',
        component: ArticleEditComponent,
      },
    ],
  },
];
```

Without a guard, any user can open the edit page for any article.

![App Navigation without guards](assets/day30-router-02.gif) <!-- TODO: asset -->

Create a service that checks permissions:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Injectable } from '@angular/core';
import {
  CanActivate,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root', // you can change to any level if needed
})
export class CanEditArticleGuard implements CanActivate {
  canActivate(
    next: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ):
    | Observable<boolean | UrlTree>
    | Promise<boolean | UrlTree>
    | boolean
    | UrlTree {
    return true; // replace with actual logic
  }
}
```

Register the guard on the route:

```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleComponent,
    children: [
      // other configurations
      {
        path: ':slug/edit',
        component: ArticleEditComponent,
        canActivate: [CanEditArticleGuard], // array — multiple guards allowed
      },
    ],
  },
];
```

Assume a `UserService` that knows the current user:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  currentUser = {
    username: 'TiepPhan',
  };
  constructor() {}
}
```

Guard logic:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@Injectable({
  providedIn: 'root',
})
export class CanEditArticleGuard implements CanActivate {
  constructor(
    private userService: UserService,
    private articleService: ArticleService
  ) {}
  canActivate(
    next: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ):
    | Observable<boolean | UrlTree>
    | Promise<boolean | UrlTree>
    | boolean
    | UrlTree {
    return this.articleService
      .getArticleBySlug(next.paramMap.get('slug'))
      .pipe(
        map(
          (article) => article.author === this.userService.currentUser.username
        )
      );
  }
}
```

You can no longer open the edit page for `bai-viet-2` when you're not the author.

![Apply Guard](assets/day30-router-04.gif) <!-- TODO: asset -->

`CanActivateChild` works like `CanActivate`, but applies to child routes of a parent route.

### CanDeactivate

A common requirement: if the user edited something and hasn't saved, confirm before they leave.

Starting from the guarded edit route:

```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleComponent,
    children: [
      {
        path: '',
        component: ArticleListComponent,
      },
      {
        path: ':slug',
        component: ArticleDetailComponent
      },
      {
        path: ':slug/edit',
        component: ArticleEditComponent,
        canActivate: [CanEditArticleGuard]
      }
    ]
  },
];
```

Add a `CanDeactivate` guard:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, RouterStateSnapshot, CanDeactivate, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { ArticleEditComponent } from './article-edit/article-edit.component';

@Injectable({
  providedIn: 'root'
})
export class CanLeaveEditGuard implements CanDeactivate<ArticleEditComponent> {
  canDeactivate(component: ArticleEditComponent, currentRoute: ActivatedRouteSnapshot, currentState: RouterStateSnapshot, nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return true; // replace with actual logic
  }
}
```

Register it alongside `canActivate`:

```ts
{
  path: ':slug/edit',
  component: ArticleEditComponent,
  canActivate: [CanEditArticleGuard],
  canDeactivate: [CanLeaveEditGuard],
}
```

Whenever the user leaves the edit screen, `CanLeaveEditGuard.canDeactivate` runs.

```ts
@Injectable({
  providedIn: 'root'
})
export class CanLeaveEditGuard implements CanDeactivate<ArticleEditComponent> {
  canDeactivate(component: ArticleEditComponent, currentRoute: ActivatedRouteSnapshot, currentState: RouterStateSnapshot, nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return !component.isEditing;
  }
}
```

![CanDeactivate Guard](assets/day31-router-01.gif) <!-- TODO: asset -->

For reuse, extract a component contract:

```ts
import { ActivatedRouteSnapshot, RouterStateSnapshot, CanDeactivate, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';

export interface CheckDeactivate {
  checkDeactivate(currentRoute: ActivatedRouteSnapshot, currentState: RouterStateSnapshot, nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree;
}
```

The component implements the logic:

```ts
@Injectable({
  providedIn: 'root'
})
export class CanLeaveEditGuard implements CanDeactivate<CheckDeactivate> {
  canDeactivate(component: CheckDeactivate, currentRoute: ActivatedRouteSnapshot, currentState: RouterStateSnapshot, nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return component.checkDeactivate(currentRoute, currentState, nextState);
  }
}
```

```ts
export class ArticleEditComponent implements OnInit, CheckDeactivate {
  slug$ = this.activatedRoute.paramMap.pipe(
    map(params => params.get('slug'))
  );

  isEditing = false;
  
  constructor(private activatedRoute: ActivatedRoute) { }

  ngOnInit() {
  }

  checkDeactivate(currentRoute: ActivatedRouteSnapshot, currentState: RouterStateSnapshot, nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return !this.isEditing;
  }

}
```

Full code: https://stackblitz.com/edit/angular-100-days-of-code-day-31-01?file=src%2Fapp%2Farticle%2Farticle-edit%2Farticle-edit.component.ts

You can show a confirm dialog:

```ts
export class ArticleEditComponent implements OnInit, CheckDeactivate {
  slug$ = this.activatedRoute.paramMap.pipe(
    map(params => params.get('slug'))
  );

  isEditing = false;
  
  constructor(private activatedRoute: ActivatedRoute, private dialog: MatDialog) { }

  ngOnInit() {
  }

  openDialog() {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Do you want to leave this page?'
      }
    });
    return ref.afterClosed();
  }

  checkDeactivate(currentRoute: ActivatedRouteSnapshot, currentState: RouterStateSnapshot, nextState?: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return !this.isEditing || this.openDialog();
  }

}
```

Full code: https://stackblitz.com/edit/angular-100-days-of-code-day-31-02?file=src%2Fapp%2Farticle%2Farticle-edit%2Farticle-edit.component.ts

![CanDeactivate with ConfirmDialog](assets/day31-router-02.gif) <!-- TODO: asset -->

### CanLoad

For lazy-loaded routes, check permissions **before** downloading the chunk. Regular users don't need the `/admin` code at all — `CanLoad` helps here.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Injectable } from '@angular/core';
import { CanLoad, UrlSegment, Route, RouterStateSnapshot, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class CanLoadAdminGuard implements CanLoad {
  canLoad(route: Route, segments: UrlSegment[]): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return true;
  }
}
```

```ts
const routes: Routes = [
  {
    path: 'admin',
    loadChildren: () =>
      import('./admin/admin.module').then((m) => m.AdminModule),
    canLoad: [CanLoadAdminGuard],
  },
  {
    path: '',
    redirectTo: 'article',
    pathMatch: 'full'
  }
];
```

Example implementation:

```ts
@Injectable({
  providedIn: 'root'
})
export class CanLoadAdminGuard implements CanLoad {
  constructor(private userService: UserService) {}
  canLoad(route: Route, segments: UrlSegment[]): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return this.userService.currentUser.isAdmin;
  }
}
```

![CanLoad Guard](assets/day31-router-03.gif) <!-- TODO: asset -->

## Route resolvers

After guards pass, **route resolvers** run. This is where you prepare data for the component that's about to activate.

### Do you really need resolvers?

Often you fetch in `ngOnInit`:

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

When the component activates, it connects to a data source — usually asynchronously. You show a loading indicator while waiting.

![Routing with loading](assets/day32-router-01.gif) <!-- TODO: asset -->

Full demo: https://stackblitz.com/edit/angular-100-days-of-code-day-32-01

For simple cases that's enough. Resolvers let you prefetch some data first — middleware on the Router.

> Interface that classes can implement to be a data provider. A data provider class can be used with the router to resolve data during navigation. The interface defines a `resolve()` method that will be invoked when the navigation starts. The router will then wait for the data to be resolved before the route is finally activated.

```ts
interface Resolve<T> {
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<T> | Promise<T> | T;
}
```

A resolver is a service implementing `Resolve`. The Router calls `resolve()` and waits before activating the route.

Article resolver example:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@Injectable({
  providedIn: 'root',
})
export class ArticleResolver implements Resolve<Article> {
  constructor(private articleService: ArticleService) {}

  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<Article> | Promise<Article> | Article {
    const slug = route.paramMap.get('slug');
    return this.articleService.getArticleBySlug(slug);
  }
}
```

Route config:

```ts
const routes: Routes = [
  {
    path: 'article',
    component: ArticleComponent,
    children: [
      {
        path: '',
        component: ArticleListComponent,
      },
      {
        path: ':slug',
        component: ArticleDetailComponent,
        resolve: {
          article: ArticleResolver, // key: value (service or DI token)
        },
      },
    ],
  },
];
```

Read resolved data from `ActivatedRoute.data`:

```ts
export class ArticleDetailComponent implements OnInit {
  article$: Observable<Article>;
  constructor(private _route: ActivatedRoute, private _api: ArticleService) {}

  ngOnInit(): void {
    // this.article$ = this._route.paramMap.pipe(
    //   map(params => params.get('slug')),
    //   switchMap(slug => this._api.getArticleBySlug(slug))
    // );
    this.article$ = this._route.data.pipe(map((data) => data.article));
  }
}
```

Data is fetched before activation, so you won't see the in-component loading spinner.

![Routing with resolver](assets/day32-router-02.gif) <!-- TODO: asset -->

Full demo: https://stackblitz.com/edit/angular-100-days-of-code-day-32-02?file=src%2Fapp%2Farticle-resolver.service.ts

### Note

Keep these trade-offs in mind:

- If a resolver never completes, the component never renders. An `Observable` that never completes blocks navigation.

- Don't share state between multiple resolvers casually.

Example service that emits five values:

```ts
getArticleBySlug(slug: string): Observable<Article> {
  let article = Articles.find(x => x.slug === slug)
  return interval(1000).pipe(
    switchMap(() => of(article)),
    take(5)
  );
}
```

In a component that's fine. In a resolver, navigation waits until the `Observable` **completes**.

Full demo: https://stackblitz.com/edit/angular-100-days-of-code-day-32-03?file=src%2Fapp%2Farticle%2Farticle.service.ts

Don't use multi-value streams (e.g. WebSocket) in resolvers. Use resolvers for one-shot prefetch; let the component handle ongoing connections.

## Summary

You now have the Router navigation lifecycle, the main guard types (`CanActivate`, `CanActivateChild`, `CanDeactivate`, `CanLoad`), and route resolvers with their trade-offs. Try applying them in a real project route.

## Code sample

- https://stackblitz.com/edit/angular-100-days-of-code-day-30?file=src%2Fapp%2Farticle%2Farticle.service.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-30-01?file=src%2Fapp%2Farticle%2Farticle-routing.module.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-31-01?file=src%2Fapp%2Farticle%2Farticle-edit%2Farticle-edit.component.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-31-02?file=src%2Fapp%2Farticle%2Farticle-edit%2Farticle-edit.component.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-31-03?file=src%2Fapp%2Fcan-load-admin.guard.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-32-01
- https://stackblitz.com/edit/angular-100-days-of-code-day-32-02?file=src%2Fapp%2Farticle-resolver.service.ts
- https://stackblitz.com/edit/angular-100-days-of-code-day-32-03?file=src%2Fapp%2Farticle%2Farticle.service.ts

## Youtube Video

[![Day 30](https://img.youtube.com/vi/STzxk1vOGqw/0.jpg)](https://youtu.be/STzxk1vOGqw) <!-- TODO: asset -->
[![Day 31](https://img.youtube.com/vi/VsUjev5-pTU/0.jpg)](https://youtu.be/VsUjev5-pTU) <!-- TODO: asset -->
[![Day 32](https://img.youtube.com/vi/YAAv4f85s7A/0.jpg)](https://youtu.be/YAAv4f85s7A) <!-- TODO: asset -->

## References

- https://angular.io/guide/router
- https://vsavkin.com/angular-2-router-d9e30599f9ea
- [Angular Router series (Vietnamese)](https://www.tiepphan.com/angular-router-series/)
- [Angular route resolver (Vietnamese)](https://www.tiepphan.com/angular-route-resolver/)
- https://indepth.dev/angular-router-series-pillar-2-understanding-the-routers-navigation-cycle/
- https://vsavkin.com/the-powerful-url-matching-engine-of-angular-router-775dad593b03

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

---
roadmap_node: "lazy-loading"
title: "Angular Router — Lazy Loading Modules"
file: "routing/lazy-loading.md"
source_days: [29]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Router — Lazy Loading Modules

Continuing from Angular Router in [the router configuration article](router-configuration.md), you already know how to split routing into feature modules. Your code is nicely isolated — if you need to reuse a module, you can copy that chunk into another Angular app and import it into `AppModule`. We'll keep using the article-list app from the previous lesson, but now we'll add an `/admin` area for managing articles. That code lives in `AdminModule`.

A regular user who is not an admin will never need to open the admin page to manage articles (unless a hacker is poking around — but let's not go there). Say your deployed JS bundle is about 1 MB. On a slow connection, loading that file can take several seconds and leave users waiting for no good reason. If you import both `ArticleModule` and `AdminModule` into `AppModule`, both chunks load when the user opens any page. In theory, when someone visits the home page to read articles, the app only needs `ArticleModule`.

**`AdminModule` should load only when the user clicks the admin link and navigates to `/admin`.** That's what the Router's [lazy-loading modules](https://angular.io/guide/lazy-loading-ngmodules) are for. Let's see how it works.

## Day 28 recap: feature module

Quick refresher: in [the router configuration article](router-configuration.md), Tiep showed how to configure a feature module called `ArticleModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@NgModule({
  imports: [CommonModule, ArticleRoutingModule],
  declarations: [
    ArticleComponent,
    ArticleListComponent,
    ArticleDetailComponent,
  ],
})
export class ArticleModule {}
```

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

@NgModule({
  imports: [CommonModule, RouterModule.forChild(routes)],
  declarations: [],
  exports: [RouterModule],
})
export class ArticleRoutingModule {}
```

Finally, import that module into `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@NgModule({
  imports: [BrowserModule, FormsModule, ArticleModule, AppRoutingModule],
  declarations: [AppComponent],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

Now run `npm run build` and inspect the JS bundle with [source-map-explorer](https://www.npmjs.com/package/source-map-explorer). There are other tools — [webpack-bundle-analyzer](https://www.npmjs.com/package/webpack-bundle-analyzer) is popular and more visual — but `source-map-explorer` is what I'm used to. Install it globally with `npm i -g source-map-explorer` if you don't have it yet.

After `npm run build`, open the `dist` folder and analyze `main.js` with `source-map-explorer main.js`. That's the main bundle loaded when the page opens.

![Step 1](assets/day-29-01.png) <!-- TODO: asset -->

You'll see what's inside `main.js`. When it loads, both `AppModule` and `ArticleModule` come along — exactly what we expect.

![Step 2](assets/day-29-02.png) <!-- TODO: asset -->

## Adding another feature module

Next we'll add `AdminModule`: articles in a table with edit/delete buttons. This is a demo, so the buttons are placeholders — we won't implement those actions.

The UI will look roughly like this:

![Step 3](assets/day-29-03.gif) <!-- TODO: asset -->

Let's code. We'll create `AdminModule` with two components:

- `AdminComponent` — layout shell, like `ArticleComponent`
- `AdminArticleListComponent` — table view for admin tasks

`AdminRoutingModule`:

```ts
const routes: Routes = [
  {
    path: 'admin',
    component: AdminComponent,
    children: [
      {
        path: '',
        component: AdminArticleListComponent,
      },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AdminRoutingModule {}
```

Because we'll render a table and edit articles, we also import `ReactiveFormsModule` in `AdminModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@NgModule({
  declarations: [AdminComponent, AdminArticleListComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule, // <-- Import for forms later
    AdminRoutingModule,
  ],
})
export class AdminModule {}
```

Import `AdminRoutingModule` into `AdminModule`, then import `AdminModule` into `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@NgModule({
  imports: [BrowserModule, AdminModule, ArticleModule, AppRoutingModule],
  declarations: [AppComponent],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

Run `npm start` and you'll see the UI from the animation above. The interesting part is the JS bundle again. With `source-map-explorer` on `main.js`, `AdminModule` is now included. Where did Angular Core and `ReactiveFormsModule` go? In `vendor.js`. Run `source-map-explorer vendor.js`:

![Step 4](assets/day-29-04.png) <!-- TODO: asset -->

Forms live there — the red highlighted section.

![Step 5](assets/day-29-05.png) <!-- TODO: asset -->

**Takeaway:** with feature modules, everything you use across **all** feature modules still loads when the app starts. Fine for small apps; painful for large ones and user experience.

Now for the main topic — **lazy loading**. Once it works, `AdminModule` and its `ReactiveFormsModule` dependency load only when you open `/admin`.

## Lazy load module

To lazy-load a module in Angular:

1. **Remove `AdminModule` from `AppModule`'s `imports` array.** Importing it there bundles `AdminModule` with `AppModule`, as we saw above.
   Note: remove the top-level `import` statement too, or nothing changes.

![Step 6](assets/day-29-06.gif) <!-- TODO: asset -->

2. **Adjust routes in `AdminModule`.** Drop the `admin` path segment from `AdminRoutingModule` — step 3 below shows why.

![Step 7](assets/day-29-07.gif) <!-- TODO: asset -->

3. **In `AppRoutingModule`, configure lazy loading for the `/admin` path.**

![Step 8](assets/day-29-08.gif) <!-- TODO: asset -->

The path is still `admin`, but instead of a `component`, use `loadChildren` with `() => import('./admin/admin.module').then((m) => m.AdminModule)` — a function that returns a dynamic `import()` of the module.

> Notice that the lazy-loading syntax uses loadChildren followed by a function that uses the browser's built-in `import('...')` syntax for dynamic imports. The import path is the relative path to the module.

Done. Run `npm run build` again. The CLI now emits a separate chunk for `AdminModule`: `admin-admin-module.js`.

![Step 9](assets/day-29-09.png) <!-- TODO: asset -->

Open the app and watch the network tab:

![Step 10](assets/day-29-10.gif) <!-- TODO: asset -->

On first load, the app fetches the usual files and `main.js`. When you click Admin and go to `/admin`, **then** `admin-admin-module.js` loads. That's lazy loading — not upfront, only when needed.

Analyze both bundles:

```
source-map-explorer main.js
source-map-explorer admin-admin-module.js
```

![Step 11](assets/day-29-11.png) <!-- TODO: asset -->

`main.js` no longer contains `AdminModule` — only `ArticleModule`.

![Step 12](assets/day-29-12.gif) <!-- TODO: asset -->

And here's `admin-admin-module.js` — Forms and admin components live in this chunk. Excellent.

## Lazy load syntax

The `import('...')` syntax is recommended from Angular 8 onward.

Before that (Angular 7 and below), you could write `loadChildren: './admin/admin.module#AdminModule'` — a magic string pointing at the `NgModule` file that exports the module with routing.

### Preloading lazy modules

Splitting lazy modules helps the **first** page load: smaller JS means faster time-to-interactive. But a lazy chunk can still be large, so clicking a link may stall while it downloads. Even our small `AdminModule` example can feel slow on a throttled mobile network:

![Step 13](assets/day-29-13.gif) <!-- TODO: asset -->

Ten seconds from click to UI is rough.

Some modules are almost always visited right after launch. **Preloading** lets you fetch those chunks in the background.

To preload **all** lazy-loaded modules, import `PreloadAllModules` from `@angular/router` and pass it to `RouterModule.forRoot`:

```ts
import { PreloadAllModules } from '@angular/router';

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

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {
      preloadingStrategy: PreloadAllModules,
    }),
  ],
  exports: [RouterModule],
})
export class AppRoutingModule {}
```

Run the app again:

![Step 14](assets/day-29-14.gif) <!-- TODO: asset -->

Right after the home page loads, `admin-admin-module.js` downloads automatically. I didn't use `ng build` with `--prod=true` here, so the file is chunky; production builds are much smaller.

For selective preloading instead of all lazy routes, see [route preloading in Angular](https://web.dev/route-preloading-in-angular/). We won't cover custom strategies in this article — follow that link if you need them.

## Summary

You should now see why lazy loading matters and how to configure a lazy-loaded route in Angular Router. For practice, try converting `ArticleModule` to lazy loading as well.

## Code example

https://stackblitz.com/edit/angular-100-days-of-code-day-29-router-lazy

## Youtube Video

[![Day 29](https://img.youtube.com/vi/D0Tv5BaNTa8/0.jpg)](https://youtu.be/D0Tv5BaNTa8) <!-- TODO: asset -->

## References

- https://angular.io/guide/router
- https://angular.io/guide/lazy-loading-ngmodules#preloading-modules
- [Angular Router series (Vietnamese)](https://www.tiepphan.com/angular-router-series/)
- https://web.dev/route-preloading-in-angular/

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

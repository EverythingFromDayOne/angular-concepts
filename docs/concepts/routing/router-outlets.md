---
roadmap_node: "router-outlets"
title: "Router Outlets"
file: "routing/router-outlets.md"
source_days: []
original_authors: []
status:
  translated: false
  upgraded: true
  reviewed: false
angular_when_written: null
angular_baseline: "22"
---

> **Modern Angular only**
> No equivalent exists in the original 100 Days series.
> Written fresh for Angular v22.

# Router Outlets

> **Lead with this:** `<router-outlet>` is the placeholder where Angular inserts
> the component matched by the current URL. You can have more than one — named
> outlets let independent sections of the page update simultaneously from the
> same URL.

## What it is

Angular's router maps URLs to components. The `<router-outlet>` directive marks
the spot in the template where the matched component should appear. Angular
inserts the activated component as a sibling element immediately after the
outlet tag — the outlet itself stays in the DOM as a reference point.

A single app can have multiple outlets. The primary outlet (unnamed) renders
the main route. Additional named outlets can render secondary routes
independently — a sidebar, a chat panel, a notification tray — all controlled
by different segments of the same URL.

Angular's routing API also lets outlets pass data down to their routed
components without requiring global state or complex route configuration,
via the `routerOutletData` input and `ROUTER_OUTLET_DATA` injection token.

## How it works under the hood

### Old model — one URL, one document

In traditional multi-page web apps, the relationship between URL and content
is straightforward: one URL maps to exactly one complete HTML document.
Navigating changes the entire page:

```
URL: /dashboard
  → Server returns dashboard.html (the full document)
  → Browser renders it

URL: /settings
  → Server returns settings.html (entirely different document)
  → Browser replaces the current page
```

There's no concept of "slots" or "panels" in this model. If you want a
sidebar and a main content area to navigate independently, you'd need iframes —
a legacy approach with well-known limitations.

### Angular's outlet tree model

Angular models the page as a **tree of activated routes**, each occupying a
named outlet. The URL encodes the state of all outlets simultaneously using
a compact syntax:

```
/dashboard(sidebar:notifications)
  │             └── 'sidebar' named outlet renders 'notifications' route
  └── primary outlet renders 'dashboard' route

/products/123(chat:support//right:help)
  │                 │           └── 'right' outlet renders 'help'
  │                 └── 'chat' outlet renders 'support'
  └── primary outlet renders products/:id
```

When the router parses this URL it builds a route state tree. Each node
in the tree identifies which outlet it targets and which component to render
there. The router then walks the tree and tells each `<router-outlet>` which
component to show.

Crucially, updating one outlet's segment in the URL doesn't affect others.
Navigating to `(sidebar:settings)` changes only the sidebar outlet — the
primary outlet stays on whatever route it was showing. This is the
"independent sections" capability that auxiliary routes enable.

The outlet directive itself is lightweight: it stores a reference to the
current component instance, listens to the router's events, and when
activation changes, it destroys the old component and creates the new one
in its place using `ViewContainerRef`.

### NgModule vs standalone

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13)
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';

@NgModule({
  imports: [RouterModule],  // RouterOutlet included in RouterModule
})
export class AppModule {}
```

```typescript
// Standalone approach (Angular 14+ — recommended)
import { RouterOutlet } from '@angular/router';

@Component({
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class AppComponent {}
```

## Basic usage

### The primary outlet

The most common case — one unnamed outlet in the root component:

```typescript
// app.component.ts
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <app-header />
    <main>
      <router-outlet />
      <!-- Router inserts the matched component as a sibling
           right after this element — the outlet tag stays in the DOM -->
    </main>
    <app-footer />
  `,
})
export class AppComponent {}
```

Route config:

```typescript
// app.routes.ts
import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '',        component: HomeComponent },
  { path: 'about',  component: AboutComponent },
  { path: 'products', loadComponent: () =>
      import('./products/products.component').then(m => m.ProductsComponent) },
];
```

### Named outlets and auxiliary routes

Step 1 — add named outlets to the template:

```typescript
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <app-top-nav />
    <div class="layout">
      <aside>
        <!-- Named outlet — renders auxiliary routes -->
        <router-outlet name="sidebar" />
      </aside>
      <main>
        <!-- Primary outlet — renders main navigation -->
        <router-outlet />
      </main>
    </div>
  `,
})
export class ShellComponent {}
```

Step 2 — define routes that target specific outlets:

```typescript
export const routes: Routes = [
  // Primary outlet routes — no outlet property
  { path: '',          component: DashboardComponent },
  { path: 'products',  component: ProductsComponent },
  { path: 'settings',  component: SettingsComponent },

  // Named outlet routes — outlet property must match the outlet's name
  { path: 'help',          component: HelpPanelComponent,     outlet: 'sidebar' },
  { path: 'notifications', component: NotificationsComponent,  outlet: 'sidebar' },
  { path: 'filters',       component: FiltersComponent,        outlet: 'sidebar' },
];
```

Step 3 — navigate to named outlets using the `outlets` object:

```html
<!-- Navigating a named outlet with routerLink -->
<!-- Opens 'help' in the sidebar outlet, leaving primary route unchanged -->
<a [routerLink]="[{ outlets: { sidebar: ['help'] } }]">Help</a>

<!-- Opening both primary and named outlets at once -->
<a [routerLink]="[{ outlets: { primary: ['products'], sidebar: ['filters'] } }]">
  Products with Filters
</a>

<!-- Closing a named outlet (navigate to null) -->
<a [routerLink]="[{ outlets: { sidebar: null } }]">Close Sidebar</a>
```

Programmatically:

```typescript
// Open the sidebar outlet
this.router.navigate([{ outlets: { sidebar: ['notifications'] } }]);

// Close the sidebar outlet
this.router.navigate([{ outlets: { sidebar: null } }]);

// Open two outlets simultaneously
this.router.navigate([{ outlets: { primary: ['settings'], sidebar: ['help'] } }]);
```

### Nested outlets — child routes

Child routes render in an outlet declared inside the parent component, not
the root outlet. This is how master-detail layouts work:

```typescript
// Routes with nested children
export const routes: Routes = [
  {
    path: 'products',
    component: ProductsComponent,     // renders in root <router-outlet>
    children: [
      { path: '',           component: ProductListComponent },  // renders in ProductsComponent's outlet
      { path: ':id',        component: ProductDetailComponent },
      { path: ':id/edit',   component: ProductEditComponent },
    ],
  },
];
```

```typescript
// products.component.ts — must have its own outlet for children
@Component({
  selector: 'app-products',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <h1>Products</h1>
    <router-outlet />  <!-- Children render here, not in root outlet -->
  `,
})
export class ProductsComponent {}
```

### Passing data to outlet contents — routerOutletData

`routerOutletData` lets the component hosting an outlet pass contextual data
down to whatever the outlet renders — without global state or extra route
configuration. The routed component reads it via the `ROUTER_OUTLET_DATA`
injection token as a signal:

```typescript
// Parent component — passes data through the outlet
@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <router-outlet [routerOutletData]="outletContext()" />
  `,
})
export class AdminComponent {
  currentUser = inject(AuthService).currentUser;

  outletContext = computed(() => ({
    user: this.currentUser(),
    permissions: this.currentUser()?.permissions ?? [],
  }));
}
```

```typescript
// Routed child component — reads from the outlet via DI
import { ROUTER_OUTLET_DATA } from '@angular/router';

@Component({ /* ... */ })
export class AdminDashboardComponent {
  // Typed as Signal<{ user: User; permissions: string[] }> — updates reactively
  context = inject<Signal<{ user: User; permissions: string[] }>>(ROUTER_OUTLET_DATA);

  canEdit = computed(() => this.context().permissions.includes('edit'));
}
```

`ROUTER_OUTLET_DATA` is available on the routed component and all its
descendants via DI — they can inject it without being directly inside the
outlet template.

### Outlet lifecycle events

Four events let the parent component react to what happens inside the outlet:

```html
<router-outlet
  (activate)="onComponentActivated($event)"
  (deactivate)="onComponentDestroyed($event)"
  (attach)="onComponentReattached($event)"
  (detach)="onComponentDetached($event)"
/>
```

| Event | Fires when | `$event` value |
| --- | --- | --- |
| `activate` | A new component is instantiated in the outlet | The new component instance |
| `deactivate` | The component is destroyed (navigated away) | The destroyed component instance |
| `attach` | `RouteReuseStrategy` reattaches a cached component | The reattached component instance |
| `detach` | `RouteReuseStrategy` detaches a component for caching | The detached component instance |

`attach` and `detach` only fire when you have a custom `RouteReuseStrategy`
that caches route component trees. In a standard app without a custom
strategy, you'll only see `activate` and `deactivate`.

```typescript
@Component({ /* ... */ })
export class ShellComponent {
  onComponentActivated(component: unknown): void {
    console.log('Route activated:', component?.constructor.name);
    // Useful for: scroll-to-top on navigation, analytics page views
  }

  onComponentDestroyed(component: unknown): void {
    console.log('Route deactivated:', component?.constructor.name);
  }
}
```

## Real-world patterns

### Pattern 1 — Side panel that opens via URL

A common admin pattern: clicking a list item opens a detail panel without
leaving the list. The panel is a named outlet. Deep linking works — the URL
encodes both the list state and the panel state:

```typescript
// Routes
{ path: 'users',           component: UserListComponent },
{ path: 'user-detail/:id', component: UserDetailComponent, outlet: 'panel' },
```

```typescript
// Shell template
@Component({
  template: `
    <div class="split-layout">
      <div class="list-pane">
        <router-outlet />
      </div>
      <aside class="detail-pane" [class.open]="panelOpen()">
        <router-outlet name="panel" (activate)="panelOpen.set(true)"
                                   (deactivate)="panelOpen.set(false)" />
      </aside>
    </div>
  `,
})
export class AdminShellComponent {
  panelOpen = signal(false);
}
```

```typescript
// User list — clicking opens the panel outlet
@Component({
  template: `
    @for (user of users(); track user.id) {
      <div
        class="user-row"
        [routerLink]="[{ outlets: { panel: ['user-detail', user.id] } }]"
        routerLinkActive="selected"
      >
        {{ user.name }}
      </div>
    }
  `,
})
export class UserListComponent {
  users = toSignal(inject(UserService).getAll(), { initialValue: [] });
}
```

The URL becomes something like `/users(panel:user-detail/42)` — shareable,
bookmarkable, and browser-back-button aware.

### Pattern 2 — Scroll to top on primary navigation

Using the `activate` event to reset scroll position on every primary route
change — a common UX requirement:

```typescript
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <router-outlet (activate)="scrollToTop()" />
  `,
})
export class AppComponent {
  scrollToTop(): void {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
}
```

### Pattern 3 — Nested master-detail with breadcrumb

A three-level hierarchy: category → product list → product detail — each level
rendered in its own outlet:

```typescript
// Routes
export const routes: Routes = [
  { path: 'catalog', component: CatalogComponent, children: [
    { path: '', component: CategoryListComponent },
    { path: ':categoryId', component: CategoryComponent, children: [
      { path: '', component: ProductListComponent },
      { path: ':productId', component: ProductDetailComponent },
    ]},
  ]},
];
```

```typescript
// CatalogComponent — hosts the category outlet
@Component({
  template: `
    <app-breadcrumb />
    <router-outlet />   <!-- CategoryListComponent or CategoryComponent renders here -->
  `,
})
export class CatalogComponent {}

// CategoryComponent — hosts the product outlet
@Component({
  template: `
    <h2>{{ categoryName() }}</h2>
    <router-outlet />   <!-- ProductListComponent or ProductDetailComponent renders here -->
  `,
})
export class CategoryComponent {
  categoryName = toSignal(
    inject(ActivatedRoute).data.pipe(map(d => d['category'].name)),
    { initialValue: '' }
  );
}
```

## Common mistakes

### Mistake 1 — Forgetting RouterOutlet in standalone imports

In standalone components, `<router-outlet>` is a directive that must be
imported explicitly. Omitting it silently renders nothing:

```typescript
// ❌ RouterOutlet not imported — template compiles but outlet does nothing
@Component({
  standalone: true,
  imports: [],                 // RouterOutlet missing
  template: `<router-outlet />`,
})
export class AppComponent {}

// ✅ RouterOutlet imported — outlet works
@Component({
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class AppComponent {}
```

Angular will show a warning in dev mode but not throw an error — the outlet
tag is treated as an unknown element and silently ignored.

### Mistake 2 — Trying to set the name attribute dynamically

The `name` attribute on `<router-outlet>` is **not** a property binding.
It's a static attribute read once at directive initialization. You cannot
change it at runtime:

```html
<!-- ❌ Will NOT work — Angular reads name once, [name] binding is ignored -->
<router-outlet [name]="outletName" />

<!-- ✅ Static name attribute — set once and stays -->
<router-outlet name="sidebar" />
```

If you need conditional outlets, use `@if` to conditionally render the outlet
elements rather than trying to rename them:

```html
@if (showSidebar()) {
  <router-outlet name="sidebar" />
}
```

### Mistake 3 — Navigating to a named outlet without the outlets syntax

Named outlets require the `{ outlets: { ... } }` navigation syntax. Plain
`routerLink` strings only target the primary outlet:

```html
<!-- ❌ Wrong — navigates the PRIMARY outlet to 'help', not the sidebar -->
<a routerLink="help">Help</a>

<!-- ✅ Correct — navigates the SIDEBAR outlet to 'help' -->
<a [routerLink]="[{ outlets: { sidebar: ['help'] } }]">Help</a>
```

### Mistake 4 — Expecting child routes to render in the root outlet

Child routes render in their parent component's `<router-outlet>`, not the
root one. Forgetting to add an outlet to the parent component means child
routes have nowhere to render:

```typescript
// ❌ ProductsComponent has no outlet — child routes never render
@Component({
  template: `<h1>Products</h1>`,   // no <router-outlet> here
})
export class ProductsComponent {}

// ✅ Parent outlet hosts child routes
@Component({
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <h1>Products</h1>
    <router-outlet />   <!-- ProductListComponent / ProductDetailComponent render here -->
  `,
})
export class ProductsComponent {}
```

## How this evolved

> - **Angular 2 (2016):** `<router-outlet>` introduced. Named outlets and
>   auxiliary routes with the parenthesis URL syntax shipped at launch.
>   `activate` and `deactivate` events shipped at launch.
>
> - **Angular 13 (2021):** `attach` and `detach` events added to
>   `RouterOutlet`, aligned with `RouteReuseStrategy` for component caching.
>
> - **Angular 14 (2022):** Standalone components. `RouterOutlet` became
>   individually importable without `RouterModule`.
>
> - **Angular 16 (2023):** `routerOutletData` input and `ROUTER_OUTLET_DATA`
>   injection token introduced — letting parent components pass contextual
>   data to routed components through the outlet without route config changes.
>   The data is exposed as a `Signal<T>`.
>
> - **Angular 22 (now):** `<router-outlet>` API is stable and unchanged.
>   Outlet data (`routerOutletData` / `ROUTER_OUTLET_DATA`) is the
>   recommended pattern for passing outlet-specific context — use it instead
>   of route `data` when the data depends on the hosting component's own
>   state rather than the route definition.

## See also

- [Routing](./routing.md) — how `Routes` are configured and matched
- [Router Configuration](./router-configuration.md) — feature modules, child
  routes, and `loadComponent` / `loadChildren` for lazy loading
- [Lazy Loading](./lazy-loading.md) — using `loadChildren` with nested outlet
  hierarchies
- [routerLink & Directives](./router-link.md) — the `{ outlets: { ... } }`
  navigation syntax for named outlets
- [Official docs — Router outlets](https://angular.dev/guide/routing/show-routes-with-outlets)
- [Official docs — RouterOutlet API](https://angular.dev/api/router/RouterOutlet)

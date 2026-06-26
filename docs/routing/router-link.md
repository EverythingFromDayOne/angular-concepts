---
roadmap_node: "router-link"
title: "routerLink & Directives"
file: "routing/router-link.md"
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

# routerLink & Directives

> **Lead with this:** `routerLink` is Angular's replacement for `<a href>` — it
> navigates within the SPA without a page reload, and `routerLinkActive`
> automatically adds a CSS class when the linked route is active.

## What it is

In a traditional multi-page website, clicking `<a href="/about">` asks the
browser to make a new HTTP GET request. The server returns a fresh HTML document.
The browser reloads the page, losing all JavaScript state in the process.

Angular Router intercepts navigation so none of that happens. Instead of a
server round-trip, it updates the component tree, runs guards and resolvers,
and swaps the content inside `<router-outlet>` — all within the same page.
To make this work, links in Angular templates use `routerLink` instead of
`href`.

Three directives cover the common cases:

| Directive | What it does |
| --- | --- |
| `RouterLink` | Makes an element navigate to a route when clicked |
| `RouterLinkActive` | Adds a CSS class to an element when its linked route is active |
| `RouterLinkActive` with `[routerLinkActiveOptions]` | Fine-grained control over what "active" means |

Angular v22 also ships a standalone `isActive()` function that returns a
computed signal — useful for programmatic active-state checks outside templates.

## How it works under the hood

### Old web model — full page navigation

In a plain HTML/server-rendered site, every link is a GET request:

```
User clicks <a href="/about">
    │
    ▼
Browser sends GET /about to the server
    │
    ▼
Server returns new HTML document
    │
    ▼
Browser destroys current page, renders new HTML
(All JavaScript state lost — component instances, form values, scroll position)
```

This is simple but expensive. Every navigation pays a full network round-trip,
and the user sees a flash as the browser repaints the new document.

### How Angular Router intercepts this

`RouterLink` replaces the browser's default link behavior with Angular's
navigation system. When you click a `routerLink` element:

```
User clicks element with [routerLink]="/about"
    │
    ▼
RouterLink directive intercepts the click event
    │
    ▼
Calls Router.navigate(['/about']) — no server request
    │
    ▼
Router runs the navigation pipeline:
  1. Apply redirects
  2. Recognize target router state
  3. Run guards (canActivate, canMatch, canDeactivate)
  4. Run resolvers — prefetch data
  5. Activate matched routes, create/reuse component instances
  6. Call History API: window.history.pushState({ }, '', '/about')
    │
    ▼
<router-outlet> swaps its content — old component destroyed, new one created
    │
    ▼
Browser URL bar updates to /about — no reload, no GET request
```

This is why Angular apps feel instant on navigation: there's no network
round-trip for the HTML, no full repaint, and component state persists
across navigations (unless the route config destroys it).

`RouterLinkActive` hooks into the router's navigation events. After each
navigation, it compares the current URL against the `routerLink` target using
Angular's `Router.isActive()` API and adds or removes the configured CSS
class accordingly.

### NgModule vs standalone imports

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13) — RouterModule bundles all directives
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';

@NgModule({
  imports: [RouterModule],  // RouterLink, RouterLinkActive etc. all come in
})
export class AppModule {}
```

```typescript
// Standalone approach (Angular 14+ — recommended)
// Import only what you use — tree-shakeable
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `...`,
})
export class NavComponent {}
```

## Basic usage

### routerLink — declarative navigation

Use a plain string for static paths, or an array for dynamic segments:

```html
<!-- Static path — string shorthand -->
<a routerLink="/about">About</a>
<a routerLink="/products">Products</a>

<!-- Dynamic path — array with segments and params -->
<a [routerLink]="['/user', userId, 'profile']">My Profile</a>
<!-- Generates: /user/123/profile when userId = 123 -->

<!-- Root-relative vs relative — no leading slash = relative -->
<!-- (from /dashboard, relative 'settings' → /dashboard/settings) -->
<a routerLink="settings">Settings</a>

<!-- Explicit relative navigation -->
<a [routerLink]="['../sibling']">Sibling route</a>
```

#### With query params and fragment

```html
<!-- Query params: [queryParams]="{ page: 2, sort: 'name' }" -->
<!-- Generates: /products?page=2&sort=name -->
<a
  routerLink="/products"
  [queryParams]="{ page: 2, sort: 'name' }"
>
  Products (page 2)
</a>

<!-- Fragment: #section → /about#team -->
<a routerLink="/about" fragment="team">Meet the Team</a>

<!-- Preserve existing query params across navigation -->
<a routerLink="/settings" queryParamsHandling="preserve">Settings</a>
```

#### Passing navigation state (not visible in the URL)

```html
<a
  routerLink="/checkout"
  [state]="{ returnUrl: '/cart', itemCount: 3 }"
>
  Checkout
</a>
```

Read it in the target component via `Router.getCurrentNavigation().extras.state`
or via `location.getState()`.

### routerLinkActive — marking the active route

```html
<!-- Single class string -->
<a routerLink="/home" routerLinkActive="active">Home</a>
<a routerLink="/about" routerLinkActive="active">About</a>

<!-- Multiple classes -->
<a routerLink="/dashboard" routerLinkActive="active font-bold">Dashboard</a>

<!-- Array syntax -->
<a routerLink="/profile" [routerLinkActive]="['active', 'current']">Profile</a>
```

By default, `routerLinkActive` uses **subset matching** — the class is added
when the current URL *starts with* the linked path. This means `/products`
stays active when you navigate to `/products/123`:

```html
<!-- At /products/123, this link IS marked active (subset match) -->
<a routerLink="/products" routerLinkActive="active">Products</a>

<!-- At /products/123, this link is NOT marked active (different path) -->
<a routerLink="/cart" routerLinkActive="active">Cart</a>
```

#### Exact matching with routerLinkActiveOptions

For the home route or any route where subset matching causes false positives:

```html
<!-- At /products, "/" would be marked active without exact matching -->
<a
  routerLink="/"
  routerLinkActive="active"
  [routerLinkActiveOptions]="{ exact: true }"
>
  Home
</a>
```

`{ exact: true }` is shorthand for the full `IsActiveMatchOptions` object.
For fine-grained control over what "match" means:

```html
<a
  routerLink="/search"
  routerLinkActive="active"
  [routerLinkActiveOptions]="{
    paths: 'exact',
    queryParams: 'ignored',
    fragment: 'ignored',
    matrixParams: 'ignored'
  }"
>
  Search
</a>
```

| Option | Values | What it controls |
| --- | --- | --- |
| `paths` | `'exact'` \| `'subset'` | Must URL segments match exactly or just start with? |
| `queryParams` | `'exact'` \| `'subset'` \| `'ignored'` | How strict is query param matching? |
| `fragment` | `'exact'` \| `'ignored'` | Does the `#fragment` matter? |
| `matrixParams` | `'exact'` \| `'subset'` \| `'ignored'` | How strict are matrix params (`;key=value`)? |

The most common real-world combination is `paths: 'exact', queryParams: 'ignored'` — 
active on the exact path regardless of what query params are present.

#### Reading isActive in the template

For showing content conditionally based on active state — without adding a
CSS class to the element itself:

```html
<a
  routerLink="/settings"
  routerLinkActive
  #settingsLink="routerLinkActive"
>
  Settings
  @if (settingsLink.isActive) {
    <span class="badge">Current</span>
  }
</a>
```

#### Applying routerLinkActive on a parent element

The active class can go on a wrapper, not the `<a>` itself — common in nav
components where the `<li>` should receive the class:

```html
<ul>
  <li routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">
    <a routerLink="/">Home</a>
  </li>
  <li routerLinkActive="active">
    <a routerLink="/products">Products</a>
  </li>
  <li routerLinkActive="active">
    <a routerLink="/account">Account</a>
  </li>
</ul>
```

#### Accessibility — ariaCurrentWhenActive

`RouterLinkActive` has an `ariaCurrentWhenActive` input for screen readers.
When the route is active, it sets `aria-current` on the element:

```html
<a
  routerLink="/home"
  routerLinkActive="active"
  ariaCurrentWhenActive="page"
>
  Home
</a>
<!-- When active: <a aria-current="page" class="active">Home</a> -->
```

Valid values: `'page'` (most common for nav links), `'step'`, `'location'`,
`'date'`, `'time'`, `true`, `false`.

### Programmatic navigation — Router.navigate()

For navigation driven by logic rather than a click:

```typescript
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

@Component({ /* ... */ })
export class LoginComponent {
  private router = inject(Router);

  async onLoginSuccess(userId: string): Promise<void> {
    // Navigate to an absolute path
    await this.router.navigate(['/dashboard', userId]);

    // Navigate with options
    await this.router.navigate(['/products'], {
      queryParams: { page: 1, sort: 'name' },
      fragment: 'list',
      replaceUrl: true,             // replaces history entry (no back button)
      skipLocationChange: false,    // default — URL updates in the bar
    });

    // Navigate by URL string
    await this.router.navigateByUrl('/home');
  }
}
```

### isActive() — reactive signal for active state (v22)

The standalone `isActive()` function returns a **computed signal** that tracks
whether a given URL is currently active. Useful for programmatic active-state
checks in component logic, outside of `routerLinkActive` directives:

```typescript
import { Component, inject } from '@angular/core';
import { Router, isActive } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  template: `
    <aside [class.collapsed]="isSettingsPage()">
      <nav><!-- ... --></nav>
    </aside>
  `,
})
export class SidebarComponent {
  private router = inject(Router);

  // Returns a computed Signal<boolean> — auto-updates on navigation
  isSettingsPage = isActive('/settings', this.router, {
    paths: 'subset',
    queryParams: 'ignored',
    fragment: 'ignored',
    matrixParams: 'ignored',
  });
}
```

## Real-world patterns

### Pattern 1 — Navigation bar with active states

A complete, accessible nav bar with correct active highlighting:

```typescript
@Component({
  selector: 'app-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav aria-label="Main navigation">
      <ul>
        @for (link of navLinks; track link.path) {
          <li
            routerLinkActive="active"
            [routerLinkActiveOptions]="link.exact ? { exact: true } : { exact: false }"
          >
            <a
              [routerLink]="link.path"
              ariaCurrentWhenActive="page"
            >
              {{ link.label }}
            </a>
          </li>
        }
      </ul>
    </nav>
  `,
})
export class NavComponent {
  navLinks = [
    { path: '/',         label: 'Home',     exact: true  },
    { path: '/products', label: 'Products', exact: false },
    { path: '/account',  label: 'Account',  exact: false },
    { path: '/about',    label: 'About',    exact: false },
  ];
}
```

### Pattern 2 — Guard-aware back navigation

After a form submission or wizard step, navigate back to the previous route
preserving query params:

```typescript
@Component({ /* ... */ })
export class CheckoutComponent {
  private router = inject(Router);

  cancel(): void {
    // Navigate back preserving any query params the user had
    this.router.navigate(['/cart'], { queryParamsHandling: 'preserve' });
  }

  async submit(orderData: Order): Promise<void> {
    const orderId = await this.orderService.create(orderData);

    // Navigate to confirmation, passing state (not visible in URL)
    this.router.navigate(['/order-confirmation', orderId], {
      state: { order: orderData, fromCheckout: true },
    });
  }
}
```

### Pattern 3 — Dynamic breadcrumbs from route params

Building a breadcrumb trail using `routerLink` arrays constructed from route data:

```typescript
@Component({
  selector: 'app-breadcrumb',
  standalone: true,
  imports: [RouterLink],
  template: `
    <nav aria-label="Breadcrumb">
      <ol>
        @for (crumb of crumbs(); track crumb.path) {
          <li>
            @if (!$last) {
              <a [routerLink]="crumb.path">{{ crumb.label }}</a>
            } @else {
              <span aria-current="page">{{ crumb.label }}</span>
            }
          </li>
        }
      </ol>
    </nav>
  `,
})
export class BreadcrumbComponent {
  private route = inject(ActivatedRoute);

  crumbs = toSignal(
    this.route.data.pipe(map(data => data['breadcrumbs'] ?? [])),
    { initialValue: [] }
  );
}
```

## Common mistakes

### Mistake 1 — Using href alongside routerLink

Using `href` on the same anchor element overrides `routerLink` — the browser
treats it as a plain link and reloads the page:

```html
<!-- ❌ href wins — full page reload happens -->
<a href="/about" routerLink="/about">About</a>

<!-- ✅ routerLink only — Angular handles the navigation -->
<a routerLink="/about">About</a>
```

### Mistake 2 — Forgetting the leading slash (absolute vs relative)

A missing `/` makes the link relative to the current route:

```html
<!-- ✅ Absolute — always goes to /products -->
<a routerLink="/products">Products</a>

<!-- ⚠️  Relative — from /dashboard goes to /dashboard/products -->
<a routerLink="products">Products</a>

<!-- This is useful intentionally for relative navigation: -->
<!-- From /products, goes to /products/featured -->
<a routerLink="featured">Featured</a>
```

If you're unsure whether you need absolute or relative, prefer absolute paths
(`/`) for primary nav links to avoid surprising behavior when the component is
reused in different route contexts.

### Mistake 3 — Exact matching on the home route forgotten

`routerLinkActive` uses subset matching by default. The home route `/` is a
prefix of every other route — without exact matching, it's always "active":

```html
<!-- ❌ "/" is a subset of every URL — always marked active -->
<a routerLink="/" routerLinkActive="active">Home</a>

<!-- ✅ exact: true — only active when URL is exactly "/" -->
<a
  routerLink="/"
  routerLinkActive="active"
  [routerLinkActiveOptions]="{ exact: true }"
>
  Home
</a>
```

### Mistake 4 — Calling Router.navigate() without await in a sequence

`Router.navigate()` returns a Promise. If you call it without `await` and
then read route state immediately, you may read stale values:

```typescript
// ❌ Fires and forgets — the navigation may not have completed
this.router.navigate(['/products']);
console.log(this.router.url); // still shows old URL

// ✅ Await the navigation before reading state
await this.router.navigate(['/products']);
console.log(this.router.url); // '/products'
```

## How this evolved

> - **Angular 2 (2016):** `RouterLink`, `RouterLinkActive`, and
>   `RouterLinkActiveOptions` introduced. Required `RouterModule` import in
>   NgModule. `routerLinkActiveOptions` accepted only `{ exact: boolean }`.
>
> - **Angular 12 (2021):** `IsActiveMatchOptions` introduced — granular
>   control over path, queryParams, fragment, and matrixParams matching
>   separately. `routerLinkActiveOptions` now accepts either `{ exact: boolean }`
>   or the full `IsActiveMatchOptions` object.
>
> - **Angular 14 (2022):** Standalone components landed; `RouterLink` and
>   `RouterLinkActive` became individually importable without `RouterModule`.
>
> - **Angular 15 (2022):** `ariaCurrentWhenActive` input added to
>   `RouterLinkActive` — Angular now manages `aria-current` automatically on
>   active links.
>
> - **Angular 22 (now):** The standalone `isActive()` function added — returns
>   a computed signal that updates reactively as the router state changes.
>   Complements `RouterLinkActive` for programmatic active-state tracking in
>   component logic.

## See also

- [Routing](./routing.md) — route configuration and how `<router-outlet>` works
- [Router Configuration](./router-configuration.md) — `Routes` array, lazy
  loading, and `withComponentInputBinding()`
- [Guards & Resolvers](./guards-resolvers.md) — what runs between the click
  and the component activation
- [Router Outlets](./router-outlets.md) — named outlets and auxiliary routes
- [toSignal](../reactivity/to-signal.md) — bridging `ActivatedRoute` Observables
  into signals
- [Official docs — RouterLink](https://angular.dev/api/router/RouterLink)
- [Official docs — RouterLinkActive](https://angular.dev/api/router/RouterLinkActive)
- [Official docs — Read route state](https://angular.dev/guide/routing/read-route-state)

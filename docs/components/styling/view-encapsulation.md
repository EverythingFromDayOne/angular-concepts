---
roadmap_node: "view-encapsulation"
title: "View Encapsulation"
file: "components/styling/view-encapsulation.md"
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

# View Encapsulation

> **Lead with this:** Angular's view encapsulation controls whether a
> component's styles stay private to it or leak out — understanding the three
> modes tells you exactly why your CSS is or isn't applying where you expect.

## What it is

In a component-based app, every component has its own styles. The question is:
do those styles affect only that component's template, or do they bleed into
the rest of the page?

Angular gives each component an `encapsulation` setting with three options:

| Mode | What it does |
| --- | --- |
| `Emulated` | Default. Angular scopes styles to this component by adding unique attributes. Other components are unaffected. |
| `None` | No scoping. Styles become global and affect the whole page. |
| `ShadowDom` | Uses the browser's native Shadow DOM. True, browser-enforced style isolation. |

Most components use `Emulated` and never think about it. You reach for the
others in specific situations: `None` for global theme components, `ShadowDom`
for web components or truly hermetic UI widgets.

## How it works under the hood

### Emulated — Angular's attribute trick

`Emulated` encapsulation doesn't use any browser feature. Angular implements
it entirely in the compiler by injecting unique attributes into your HTML and
rewriting your CSS selectors to include those attributes.

Given a component with selector `app-card`, Angular generates a unique ID for
it — something like `c1a2b3`. It then:

1. Adds `_nghost-c1a2b3` to the **component's host element**
2. Adds `_ngcontent-c1a2b3` to **every element inside its template**
3. Rewrites every CSS rule you wrote to include `[_ngcontent-c1a2b3]`

So your CSS:
```css
p { color: steelblue; }
.title { font-size: 1.5rem; }
```

Becomes (in the compiled output):
```css
p[_ngcontent-c1a2b3] { color: steelblue; }
.title[_ngcontent-c1a2b3] { font-size: 1.5rem; }
```

Those styles now only match `<p>` elements that have `_ngcontent-c1a2b3` —
which are only the `<p>` elements inside *this* component's template. Other
components' `<p>` elements have different attribute IDs and are unaffected.

This is why Emulated "works like" true encapsulation for almost all cases, but
it is not actual Shadow DOM — the styles are still in the document's global
stylesheet, just with narrow selectors.

### ShadowDom — Browser-native isolation

`ShadowDom` attaches a native [Shadow Root](https://developer.mozilla.org/en-US/docs/Web/API/ShadowRoot)
to the component's host element. The component's template lives inside this
shadow tree, and the browser enforces two rules:

- Styles defined inside the shadow root don't leak out
- Global page styles don't pierce in (unless they use CSS custom properties or
  `::part()`)

This is true isolation — not attribute tricks, but a browser-enforced boundary.
The cost: it makes integrating with global CSS libraries (like Tailwind or
Bootstrap) harder, because their classes don't reach inside shadow roots by
default.

### None — Your styles become global

`None` skips all scoping. Angular injects your component's styles into the
document `<head>` as a plain `<style>` block. They become global styles that
can affect any element on the page, in any component. Use this intentionally
and sparingly.

## Basic usage

Set `encapsulation` in the `@Component` decorator. If you omit it, `Emulated`
is the default.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13)
import { Component, ViewEncapsulation, NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

@Component({
  selector: 'app-card',
  template: `
    <div class="card">
      <p class="title">{{ title }}</p>
    </div>
  `,
  styles: [`
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; }
    .title { font-size: 1.2rem; font-weight: 600; }
  `],
  encapsulation: ViewEncapsulation.Emulated, // default — can be omitted
})
export class CardComponent {
  title = 'Hello';
}

@NgModule({
  declarations: [CardComponent],
  imports: [BrowserModule],
})
export class AppModule {}
```

```typescript
// Standalone approach (Angular 14+ — recommended)
import { Component, ViewEncapsulation } from '@angular/core';

@Component({
  selector: 'app-card',
  standalone: true,
  template: `
    <div class="card">
      <p class="title">{{ title }}</p>
    </div>
  `,
  styles: [`
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; }
    .title { font-size: 1.2rem; font-weight: 600; }
  `],
  // encapsulation: ViewEncapsulation.Emulated  ← default, safe to omit
})
export class CardComponent {
  title = 'Hello';
}
```

### The three modes side by side

```typescript
import { Component, ViewEncapsulation } from '@angular/core';

// Mode 1 — Emulated (default): styles scoped to this component
@Component({
  selector: 'app-scoped',
  standalone: true,
  styles: [`.box { background: lightblue; }`],
  template: `<div class="box">Scoped</div>`,
  encapsulation: ViewEncapsulation.Emulated,
})
export class ScopedComponent {}

// Mode 2 — None: styles become global
@Component({
  selector: 'app-global-theme',
  standalone: true,
  styles: [`
    :root { --primary: #6750a4; }
    body { font-family: 'Inter', sans-serif; }
  `],
  template: `<ng-content />`,
  encapsulation: ViewEncapsulation.None, // intentional — setting global tokens
})
export class GlobalThemeComponent {}

// Mode 3 — ShadowDom: native browser isolation
@Component({
  selector: 'app-widget',
  standalone: true,
  styles: [`.box { background: coral; }`],
  template: `<div class="box">Isolated</div>`,
  encapsulation: ViewEncapsulation.ShadowDom,
})
export class WidgetComponent {}
```

### Styling the host element with :host

The `:host` pseudo-selector targets the component's own host element — the
element Angular puts in the DOM when it renders this component:

```typescript
@Component({
  selector: 'app-badge',
  standalone: true,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
    }

    :host(.success) { background: #d4edda; color: #155724; }
    :host(.warning) { background: #fff3cd; color: #856404; }
    :host(.error)   { background: #f8d7da; color: #721c24; }
  `],
  template: `<ng-content />`,
})
export class BadgeComponent {}
```

```html
<!-- Usage -->
<app-badge class="success">Active</app-badge>
<app-badge class="warning">Pending</app-badge>
<app-badge class="error">Failed</app-badge>
```

`:host` works in all three encapsulation modes.

### Styling based on ancestor context with :host-context

`:host-context()` applies styles to the host when a specified ancestor matches.
Useful for theme switching:

```typescript
@Component({
  selector: 'app-card',
  standalone: true,
  styles: [`
    :host { background: white; color: black; }

    /* When any ancestor has .dark-theme, flip the card's colors */
    :host-context(.dark-theme) {
      background: #1e1e1e;
      color: #f0f0f0;
    }
  `],
  template: `<div class="card"><ng-content /></div>`,
})
export class CardComponent {}
```

```html
<!-- Light theme: white card -->
<app-card>Content</app-card>

<!-- Dark theme: dark card — the class is on an ancestor, not the component -->
<div class="dark-theme">
  <app-card>Content</app-card>
</div>
```

> **Note:** `:host-context()` is not supported in `ShadowDom` mode and has
> limited browser support for native shadow DOM. It works reliably in `Emulated`
> mode only.

## Real-world patterns

### Pattern 1 — Global design token component (ViewEncapsulation.None)

A common pattern in design systems: one root component sets CSS custom
properties for the whole app, using `None` intentionally:

```typescript
// theme.component.ts
@Component({
  selector: 'app-theme',
  standalone: true,
  template: `<ng-content />`,
  styles: [`
    :root {
      --color-primary:    #6750a4;
      --color-secondary:  #958da5;
      --color-surface:    #fffbfe;
      --color-on-surface: #1c1b1f;
      --radius-sm: 4px;
      --radius-md: 8px;
      --radius-lg: 16px;
      --font-sans: 'Inter', system-ui, sans-serif;
    }
  `],
  encapsulation: ViewEncapsulation.None, // tokens need to be global
})
export class ThemeComponent {}
```

```typescript
// app.component.ts — wrap the whole app
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ThemeComponent, RouterOutlet],
  template: `
    <app-theme>
      <router-outlet />
    </app-theme>
  `,
})
export class AppComponent {}
```

Every component in the app can now reference `var(--color-primary)` in its
own scoped styles.

### Pattern 2 — Styling a third-party component

Third-party components render their own DOM that your Emulated styles can't
reach — your `_ngcontent-xxx` attributes aren't on their elements. The modern
solution is CSS custom properties if the library supports them. If not, you
need to go global:

```typescript
// Option A — CSS custom properties (preferred, if the library supports them)
@Component({
  selector: 'app-datepicker-wrapper',
  standalone: true,
  styles: [`
    :host {
      --datepicker-primary: var(--color-primary);
      --datepicker-border-radius: var(--radius-md);
    }
  `],
  template: `<third-party-datepicker />`,
})
export class DatepickerWrapperComponent {}

// Option B — ViewEncapsulation.None for a wrapper component
//            (use sparingly — styles leak globally)
@Component({
  selector: 'app-datepicker-wrapper',
  standalone: true,
  styles: [`
    /* These selectors reach inside the third-party component */
    third-party-datepicker .calendar-cell { border-radius: 50%; }
    third-party-datepicker .selected { background: var(--color-primary); }
  `],
  template: `<third-party-datepicker />`,
  encapsulation: ViewEncapsulation.None,
})
export class DatepickerWrapperComponent {}
```

## Common mistakes

### Mistake 1 — Using ::ng-deep (it's deprecated and leaks globally)

`::ng-deep` was the old way to pierce encapsulation — reach into child
component styles. It works, but it makes styles global from the point of
application downward. It's been deprecated since Angular 7.

```css
/* ❌ Deprecated — leaks styles globally, hard to maintain */
::ng-deep .mat-button { border-radius: 999px; }

/* ✅ Better — wrap in :host to limit the leak to this component's subtree */
:host ::ng-deep .mat-button { border-radius: 999px; }

/* ✅ Best — use CSS custom properties if the library supports them */
:host { --mdc-text-button-container-shape: 999px; }
```

Even with `:host ::ng-deep`, you're depending on the child component's internal
class names — which can change between library versions. CSS custom properties
are stable public API; internal class names are not.

### Mistake 2 — Setting ViewEncapsulation.None on a general-purpose component

`None` means your styles are global. If you use it on a reusable component
that gets rendered many times, those styles affect the entire app:

```typescript
// ❌ Wrong — .card styles now apply to every .card on the page
@Component({
  selector: 'app-card',
  styles: [`.card { background: white; }`],
  encapsulation: ViewEncapsulation.None, // styles leak everywhere
})

// ✅ Right — keep Emulated (default) for scoped component styles
@Component({
  selector: 'app-card',
  styles: [`.card { background: white; }`],
  // encapsulation omitted → Emulated by default
})
```

Reserve `None` for components that are intentionally setting global styles —
theme providers, CSS reset components, and similar.

### Mistake 3 — Expecting ShadowDom to work with utility CSS frameworks

Tailwind classes live in a global stylesheet. Shadow DOM's encapsulation
boundary blocks them from reaching inside your component:

```typescript
// ❌ ShadowDom + Tailwind — Tailwind classes don't work inside shadow root
@Component({
  selector: 'app-card',
  standalone: true,
  template: `<div class="p-4 rounded-lg shadow">...</div>`,
  encapsulation: ViewEncapsulation.ShadowDom, // Tailwind's p-4 etc. won't apply
})

// ✅ Emulated (default) + Tailwind — classes reach through attribute scoping
@Component({
  selector: 'app-card',
  standalone: true,
  template: `<div class="p-4 rounded-lg shadow">...</div>`,
  // Emulated by default — Tailwind works fine
})
```

Use `ShadowDom` when you genuinely need the browser-enforced boundary — typically
when building Angular Elements or design system primitives shipped as web
components. Don't use it in regular app components.

## How this evolved

> - **Angular 2 (2016):** All three encapsulation modes introduced at launch:
>   `Emulated` (default), `Native` (native Shadow DOM), `None`. The API has
>   been stable since.
>
> - **Angular 6 (2018):** `Native` renamed to `ShadowDom` to better reflect
>   what it actually does and align with the Shadow DOM v1 spec. `Native` was
>   deprecated and eventually removed.
>
> - **Angular 7 (2018):** `::ng-deep` officially deprecated. The Angular team
>   encouraged using CSS custom properties instead, but no replacement selector
>   was introduced — the guidance was to redesign the approach.
>
> - **Angular 14 (2022):** Standalone components arrived but encapsulation
>   behavior is identical — the `encapsulation` field in `@Component` works the
>   same in both standalone and NgModule components.
>
> - **Angular 22 (now):** The three modes are unchanged and no new mode is
>   planned. The recommended approach for all new code: use `Emulated` (default)
>   for all regular components, CSS custom properties for cross-component theming,
>   and `None` only for deliberate global style injection. `::ng-deep` still
>   works but should not appear in new code.

## See also

- [Sass](./sass.md) — preprocessing component styles with variables, mixins,
  and partials
- [Angular Material](./angular-material.md) — how Material's theming system
  uses CSS custom properties to work across encapsulation boundaries
- [Directive Composition](../../directives/directive-composition.md) — composing
  host-level behaviors without needing to pierce encapsulation
- [Official docs — View encapsulation](https://angular.dev/guide/components/styling#view-encapsulation)
- [Official docs — :host and :host-context](https://angular.dev/guide/components/host-elements)

---
roadmap_node: "sass"
title: "Sass & SCSS"
file: "tooling/sass.md"
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

# Sass & SCSS

> **Lead with this:** Angular has first-class SCSS support out of the box —
> no extra webpack config needed. The real skill is combining SCSS's authoring
> power (variables, mixins, nesting, `@use`/`@forward`) with Angular's
> encapsulation system (`:host`, CSS custom properties) to keep styles
> both reusable and properly scoped.

## What it is

**Sass** is a CSS preprocessor — it adds variables, nesting, mixins, functions,
and a module system on top of CSS, then compiles down to plain CSS at build
time. Angular projects use the **SCSS** syntax (the `.scss` extension), which
is a superset of CSS: every valid `.css` file is also valid `.scss`.

Angular's CLI and build tooling process `.scss` files automatically via
`esbuild`'s built-in Sass support — no `webpack` config, no extra loaders,
no extra packages to install when you choose SCSS as your style format.

## How it works under the hood

### Old approach — global CSS with specificity wars

In traditional multi-page websites, all CSS is global. To style a `.card`
inside a specific section, you write:

```css
.admin-section .card { border: 2px solid red; }
```

Specificity fights between component teams are common. A button style from
one team overwrites another team's button with a more specific selector.
The solution — `!important` — makes things worse. Global CSS is effectively
shared mutable state that every stylesheet in the app writes to.

SCSS helped (variables, nesting, partials) but didn't solve the global
scoping problem — compiled SCSS is still global CSS.

### Angular's emulated encapsulation — the real isolation

Angular solves global CSS pollution at the component boundary, not at the
preprocessor level. When you write SCSS for a component, Angular adds a
unique **attribute selector** to every rule at build time, scoping it to
that component's DOM:

```scss
// component.scss (what you write)
h1 { color: red; }
.card { padding: 16px; }
```

```css
/* Compiled output Angular ships to the browser */
h1[_ngcontent-abc-c42] { color: red; }
.card[_ngcontent-abc-c42] { padding: 16px; }
```

The `_ngcontent-abc-c42` attribute is added to every element in the
component's template. The rule only matches when an element has BOTH the
class/tag AND this unique attribute — so it only affects this component's
DOM, never leaking to siblings or children.

This is **emulated** encapsulation — Angular emulates Shadow DOM scoping
with attribute selectors, making it work on all browsers without requiring
native Shadow DOM.

### Sass compiles first, Angular scopes second

The build pipeline is sequential:

```
component.scss
      ↓
esbuild's Sass compiler processes @use, @forward, variables, mixins, nesting
      ↓
plain CSS (with specificity from nesting, variables replaced with values)
      ↓
Angular's compiler adds [_ngcontent-xxx] to every rule
      ↓
Scoped CSS sent to the browser
```

This means all SCSS features work normally — Angular sees the compiled CSS,
not the SCSS source.

## Setup

### New project with SCSS

```bash
ng new my-app --style=scss
```

### Set SCSS as default for an existing project

```bash
# Set default style for future ng generate commands
ng config schematics.@schematics/angular:component.style scss

# Or edit angular.json directly:
# "schematics": {
#   "@schematics/angular:component": {
#     "style": "scss"
#   }
# }
```

```json
// angular.json — global styles
"styles": [
  "src/styles.scss"      // your global SCSS entry point
]
```

### Component style setup

Angular 17+ uses `styleUrl` (singular string) instead of the old `styleUrls`
(array). Both work, but the singular form is the current convention:

```typescript
// Modern (v17+ convention — styleUrl singular)
@Component({
  selector: 'app-card',
  standalone: true,
  templateUrl: './card.component.html',
  styleUrl: './card.component.scss',     // singular string
})
export class CardComponent {}

// Also valid — inline styles
@Component({
  selector: 'app-badge',
  standalone: true,
  template: `<span class="badge">{{ label }}</span>`,
  styles: [`
    .badge {
      padding: 4px 8px;
      border-radius: 4px;
      background: var(--badge-bg, #e0e0e0);
    }
  `],
})
export class BadgeComponent {}
```

## Basic SCSS in Angular components

### Variables and nesting

```scss
// card.component.scss
$card-radius: 8px;
$card-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);

.card {
  border-radius: $card-radius;
  box-shadow: $card-shadow;
  overflow: hidden;

  // Nesting — compiles to .card .card__header
  .card__header {
    padding: 16px;
    border-bottom: 1px solid #e0e0e0;

    h2 {
      margin: 0;
      font-size: 1.25rem;
    }
  }

  .card__body {
    padding: 16px;
  }

  // Modifier — compiles to .card.card--elevated
  &--elevated {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  }
}
```

### Mixins

```scss
// _mixins.scss (partial — leading underscore means "not compiled standalone")
@mixin flex-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

@mixin responsive-grid($min-width: 280px) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax($min-width, 1fr));
  gap: 16px;
}

@mixin button-variant($bg, $color: white) {
  background: $bg;
  color: $color;

  &:hover {
    background: darken($bg, 10%);   // Sass color function
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
```

```scss
// button.component.scss
@use './mixins' as m;

.btn-primary {
  @include m.button-variant(#1976d2);
  padding: 8px 24px;
  border-radius: 4px;
}
```

### The @use / @forward module system

Sass deprecated `@import` — it pollutes the global namespace and causes all
imported members to be visible everywhere. The replacement is `@use` and
`@forward`, which create a proper module system.

**`@use`** — import a module for use in the current file only:

```scss
// component.scss
@use './variables' as vars;       // access as vars.$color-primary
@use './mixins' as *;              // access without prefix (careful with collisions)
@use 'sass:math';                  // built-in Sass math module
@use 'sass:color';                 // built-in Sass color module

.container {
  color: vars.$color-primary;
  padding: math.div(32px, 2);     // 16px — use math.div() not /
}
```

**`@forward`** — re-export members from other files (for building index files):

```scss
// styles/_index.scss — exposes everything to consumers
@forward './variables';
@forward './mixins';
@forward './breakpoints';
```

```scss
// component.scss — import everything through the index
@use '../styles' as s;

.card {
  color: s.$primary-color;
  @include s.flex-center;
}
```

**Why not `@import`?**

```scss
// ❌ @import — deprecated, global namespace pollution
@import './variables';      // $primary-color now globally available, may clash

// ✅ @use — explicit, scoped, controlled
@use './variables' as vars;   // only accessible as vars.$primary-color in this file
```

## Angular-specific selectors

### :host — style the component element itself

The `:host` selector targets the component's own host element (the
`<app-card>` tag in the parent's DOM). Use it for display properties,
positioning, or base styles that apply to the component's outermost wrapper:

```scss
// card.component.scss
:host {
  display: block;              // Custom elements are inline by default
  container-type: inline-size; // CSS container queries on the host
}

:host(.expanded) {             // :host with a class condition
  max-height: none;
}

:host([disabled]) {            // :host with an attribute condition
  opacity: 0.5;
  pointer-events: none;
}
```

### :host-context — style based on ancestor theme

`:host-context()` applies styles when an ancestor matches the selector.
Useful for dark mode or theme-aware components. **Note:** `:host-context` is
deprecated in native browser CSS, but Angular's emulated encapsulation
implements it via attribute selectors so it works reliably:

```scss
// card.component.scss
:host-context(.dark-theme) {
  background: #1e1e1e;
  color: #ffffff;
  border-color: #333;
}

:host-context([data-theme="compact"]) {
  .card__body {
    padding: 8px;   // tighter padding in compact theme
  }
}
```

### ::ng-deep — breaking encapsulation (deprecated, use sparingly)

`::ng-deep` stops Angular's encapsulation scoping at that point in the
selector, making the rule global beyond that point. Deprecated, but won't
be removed until CSS `@scope` reaches full browser support (Angular v22:
still functional):

```scss
// ❌ Dangerous — fully global, leaks everywhere
::ng-deep .mat-button { color: red; }

// ❌ Still leaks outside the component — Angular only checks the :host part
:host ::ng-deep .mat-button { color: red; }
// Actually: :host limits the match to elements inside this component's
// host subtree — that IS the right pattern. Use this form, not bare ::ng-deep.

// ✅ The correct ::ng-deep pattern — scoped to this component's subtree
:host {
  ::ng-deep .mat-mdc-form-field {
    width: 100%;
  }
}
```

The decision flow for styling child/third-party components:

```
Does the component expose CSS custom properties? → Use them (best)
Does the component expose ::part()? → Use ::part() (second)
Is it your own component? → Add a CSS custom property hook
Is it a third-party component? → Consider ViewEncapsulation.None
Last resort: :host { ::ng-deep { ... } }
```

## CSS custom properties — the modern theming approach

CSS custom properties (variables) pierce Shadow DOM and emulated encapsulation
naturally — they're inherited by all descendants without `::ng-deep`:

```scss
// Parent component defines the theme
:host {
  --card-bg: #ffffff;
  --card-border-color: #e0e0e0;
  --card-padding: 16px;
}

:host(.elevated) {
  --card-bg: #f8f8f8;
}
```

```scss
// card.component.scss — reads values provided by parent or design system
.card {
  background: var(--card-bg, #ffffff);          // fallback if not set
  border: 1px solid var(--card-border-color, #e0e0e0);
  padding: var(--card-padding, 16px);
}
```

This is how Angular Material v3 themes work — Material components expose CSS
custom properties like `--mat-sys-primary` and `--mdc-filled-button-container-color`
that you override from your component's `:host` block.

## Global styles vs component styles

```scss
// src/styles.scss — global styles (applies everywhere)
// ✅ Good uses: resets, typography scale, CSS custom property definitions, utility classes

:root {
  --color-primary: #1976d2;
  --color-primary-dark: #115293;
  --spacing-unit: 8px;
}

body {
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  line-height: 1.5;
  margin: 0;
}

// Utility classes used throughout the app
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  clip: rect(0, 0, 0, 0);
  overflow: hidden;
}
```

```scss
// component.component.scss — component-scoped styles
// ✅ Anything that only applies to this component's DOM

:host { display: block; }

.inner-layout { /* ... */ }
```

Keep global styles to: CSS custom property definitions, typography, resets,
utility classes, and third-party overrides. Everything else belongs in
component files.

## Real-world patterns

### Pattern 1 — Design token file structure

```
src/
└── styles/
    ├── _tokens.scss       ← CSS custom property definitions + Sass variables
    ├── _typography.scss   ← font scales, heading styles
    ├── _mixins.scss       ← reusable mixins
    ├── _breakpoints.scss  ← responsive breakpoint helpers
    ├── _index.scss        ← @forward all of the above
    └── styles.scss        ← global entry point (uses _index.scss)
```

```scss
// styles/_tokens.scss
$primary: #1976d2;
$on-primary: #ffffff;

:root {
  --color-primary: #{$primary};
  --color-on-primary: #{$on-primary};
  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-4: 16px;
  --spacing-8: 32px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;
}
```

### Pattern 2 — Responsive component with container queries

```scss
// product-card.component.scss
:host {
  display: block;
  container-type: inline-size;   // enables container queries on the host
}

.card {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-2);
}

@container (min-width: 320px) {
  .card {
    grid-template-columns: 120px 1fr;  // image + content side by side

    .image { grid-row: 1 / 3; }
  }
}
```

Container queries let a component respond to its OWN size — not the
viewport. This is the correct tool for reusable cards and widgets that
appear in different layout contexts.

## Common mistakes

### Mistake 1 — Forgetting :host for display properties

Custom HTML elements (`<app-card>`) are `display: inline` by default. Without
setting `display: block` (or `flex`, `grid`) on `:host`, the component won't
occupy space as you expect:

```scss
// ❌ Not set — app-card renders as inline, margin/width don't work as expected
// component.component.scss empty or missing :host { display }

// ✅ Always set a display value on :host for block-level components
:host {
  display: block;     // or flex, grid, contents — whatever fits
}
```

### Mistake 2 — Using bare ::ng-deep without :host prefix

Bare `::ng-deep` without `:host` creates fully global styles — they leak out
of the component and affect matching elements anywhere in the app:

```scss
// ❌ Global — affects ALL .mat-button elements in the ENTIRE app
::ng-deep .mat-button { font-weight: bold; }

// ✅ Scoped to this component's subtree
:host {
  ::ng-deep .mat-button { font-weight: bold; }
}
```

### Mistake 3 — Using @import instead of @use

Sass deprecated `@import`. In Sass 3.0 (future), it will be removed. Switch
to `@use`:

```scss
// ❌ Deprecated
@import './variables';
@import './mixins';

// ✅ Modern module system
@use './variables' as vars;
@use './mixins' as m;
```

### Mistake 4 — Deeply nested SCSS that defeats encapsulation intent

Deeply nesting selectors in SCSS creates high-specificity CSS that's hard to
override and breaks encapsulation semantics:

```scss
// ❌ 4-level nesting — compiled to .card .header .title span { ... }
// High specificity, hard to override, not Angular's intended component pattern
.card {
  .header {
    .title {
      span {
        font-size: 0.875rem;
      }
    }
  }
}

// ✅ Flat BEM-style or direct element selectors
.card__title-note {
  font-size: 0.875rem;
}

// ✅ Or use CSS custom properties and let child components define their own styles
```

## How this evolved

> - **Angular 2–5 (2016–2017):** SCSS support via `angular-cli.json` and
>   webpack-sass-loader. Encapsulation worked but required explicit plugin
>   setup and was configured separately from the rest of the build.
>
> - **Angular 6 (2018):** `angular.json` replaced `.angular-cli.json`.
>   SCSS style support consolidated. `styleUrls` as an array was the norm.
>
> - **Angular 17 (2023):** `styleUrl` (singular) introduced alongside the
>   esbuild migration. Built-in Sass processing via esbuild — no webpack
>   sass-loader, significantly faster SCSS compilation.
>
> - **Angular 17+ (2023–present):** Container queries encouraged as the
>   modern responsive tool for components. CSS custom properties became the
>   standard theming API (Angular Material v3 adopted them fully).
>   `::ng-deep` guidance strengthened — use CSS custom properties instead.
>
> - **Angular 22 (now):** `styleUrl` is the standard. esbuild handles SCSS
>   natively. Sass `@use`/`@forward` module system is the standard (`@import`
>   deprecated by Sass). `::ng-deep` remains deprecated but functional.
>   The recommended theming architecture is: CSS custom properties at the
>   `:root` or `:host` level, consumed via `var()` in component styles.

## See also

- [View Encapsulation](../components/styling/view-encapsulation.md) — deep
  dive into Emulated vs ShadowDom vs None encapsulation modes
- [Angular Material](../components/styling/angular-material.md) — theming
  Material components with CSS custom properties
- [Official docs — Component styles](https://angular.dev/guide/components/styling)
- [Sass @use and @forward docs](https://sass-lang.com/documentation/at-rules/use/)
- [CSS custom properties — MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

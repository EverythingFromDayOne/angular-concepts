---
roadmap_node: "angular-elements"
title: "Angular Elements"
file: "tooling/angular-elements.md"
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

# Angular Elements

> **Lead with this:** Angular Elements packages any Angular component as a
> browser-native Custom Element — a self-bootstrapping HTML tag that works in
> React apps, Vue apps, plain HTML pages, or server-rendered Django templates
> without any Angular knowledge at the host.

## What it is

Angular components normally live inside an Angular application tree. They
need Angular's DI, change detection, and lifecycle management — all of which
require an Angular bootstrap to exist. If you want to use an Angular component
in a non-Angular page, you're stuck: you can't just copy the template and
styles into a React app.

**Angular Elements** solves this by wrapping a component in the browser's
native **Custom Elements** API (part of the Web Components standard). The
wrapped component registers itself with the browser as a new HTML tag.
Whoever embeds `<my-rating-widget stars="4"></my-rating-widget>` gets the
full Angular component — DI, CD, lifecycle hooks, signals — without knowing
Angular exists.

**Primary use cases:**

| Scenario | Why Elements helps |
| --- | --- |
| **Design system across frameworks** | Build once in Angular, consume in React/Vue/plain HTML |
| **Micro-frontends** | Different teams own different widgets; host doesn't dictate the framework |
| **Server-rendered pages** | Embed Angular widgets into Django, Rails, WordPress templates |
| **Legacy migration** | Incrementally replace jQuery widgets with Angular components |
| **CMS embeds** | Non-technical authors drop `<my-widget>` tags into CMS content |

## How it works under the hood

### Old constraint — Angular components need an Angular host

A regular Angular component is defined in TypeScript, compiled by the Angular
compiler, and can only run inside an Angular application tree:

```
Browser visits page
    ↓
Angular's bootstrapApplication() creates the root injector + app tree
    ↓
<app-root> component is instantiated by Angular
    ↓
Child components instantiated, DI resolved, lifecycle hooks called
    ↓
Zone.js or signals schedule CD cycles
```

Every step depends on Angular's runtime being present and having been
bootstrapped. You can't drop `<my-component>` into a React page and have it
work — there's no Angular runtime to boot the component, no injector to resolve
its dependencies.

### How Custom Elements breaks this constraint

The **Web Components Custom Elements API** lets JavaScript register new HTML
tag names with the browser. Once registered, the browser automatically creates
an instance of the custom element class whenever that tag appears in the DOM,
and destroys it when the tag is removed:

```javascript
// Any JS (not Angular-specific) can register a custom element
class MyElement extends HTMLElement {
  connectedCallback() { /* tag added to DOM */ }
  disconnectedCallback() { /* tag removed from DOM */ }
}
customElements.define('my-element', MyElement);

// Browser now handles <my-element> like <div> or <span>
```

`createCustomElement()` from `@angular/elements` converts an Angular component
into a class that extends `HTMLElement` and implements `connectedCallback` /
`disconnectedCallback`. When the browser calls `connectedCallback`, Angular
boots the component — resolves its DI, instantiates it, attaches it to the
DOM, runs `ngOnInit`, starts CD. When the browser calls `disconnectedCallback`,
Angular runs `ngOnDestroy` and cleans up.

The result: the Angular component is a fully self-booting HTML element.
No Angular bootstrap call is needed by the host page. The Angular runtime is
bundled into the element's JavaScript file and activates on demand.

```
Browser encounters <rating-widget stars="4">
    ↓
customElements callback fires (browser native)
    ↓
createCustomElement wrapper:
  - Creates Angular injector (or reuses app-level one)
  - Boots the RatingWidgetComponent
  - Connects inputs (stars="4" → @Input() stars)
  - Listens for @Output() EventEmitters → dispatches DOM CustomEvents
    ↓
Angular CD + lifecycle hooks run normally
    ↓
When <rating-widget> is removed from DOM:
  ngOnDestroy called, subscriptions cleaned up
```

### Inputs and outputs mapping

Angular Elements maps the Angular component's interface to the HTML element's:

| Angular | HTML Custom Element |
| --- | --- |
| `@Input() title = ''` or `title = input('')` | `element.title = 'x'` or `<el title="x">` |
| `@Output() clicked = new EventEmitter()` | `element.addEventListener('clicked', handler)` |
| Signal inputs (`input()`) | Same attribute mapping as `@Input()` |

Attribute names are automatically kebab-cased: `@Input() userName` becomes
the attribute `user-name`.

## Basic usage

### Setup

```bash
ng add @angular/elements
```

### Pattern A — Minimal setup with createApplication (recommended for standalone)

The modern pattern for registering Angular Elements without a root app component:

```typescript
// main.ts
import { createApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';
import { createCustomElement } from '@angular/elements';
import { RatingWidgetComponent } from './app/rating-widget.component';
import { TooltipComponent } from './app/tooltip.component';

(async () => {
  // Create a minimal Angular application — no root component
  const app = await createApplication({
    providers: [
      provideHttpClient(),          // shared services for all custom elements
    ],
  });

  // Register one or more custom elements using the shared injector
  const RatingElement = createCustomElement(RatingWidgetComponent, {
    injector: app.injector,
  });
  customElements.define('rating-widget', RatingElement);

  const TooltipElement = createCustomElement(TooltipComponent, {
    injector: app.injector,
  });
  customElements.define('app-tooltip', TooltipElement);
})();
```

A single `createApplication()` call provides the root injector for all
elements. This means services like `HttpClient`, `Router`, and state stores
are shared across all elements on the page.

### Pattern B — Inside an existing Angular app

If you already have an Angular application and want to also expose some
components as custom elements (for embedding into non-Angular parts of
the same page or for use in micro-frontends):

```typescript
// app.component.ts
import { Component, Injector, inject } from '@angular/core';
import { createCustomElement } from '@angular/elements';
import { RatingWidgetComponent } from './rating-widget.component';

@Component({
  selector: 'app-root',
  standalone: true,
  template: `<router-outlet />`,
})
export class AppComponent {
  private injector = inject(Injector);

  constructor() {
    // Guard against re-registration (e.g. hot module reload)
    if (!customElements.get('rating-widget')) {
      const RatingElement = createCustomElement(RatingWidgetComponent, {
        injector: this.injector,
      });
      customElements.define('rating-widget', RatingElement);
    }
  }
}
```

### The component itself

An Angular Elements component is a perfectly ordinary Angular component — no
special base class, no special decorator. The only considerations are:

```typescript
import { Component, input, output, signal, computed } from '@angular/core';
import { ViewEncapsulation } from '@angular/core';

@Component({
  selector: 'rating-widget',    // selector matters less — tag name comes from customElements.define
  standalone: true,
  // ShadowDom gives true CSS isolation — styles can't leak in or out
  encapsulation: ViewEncapsulation.ShadowDom,
  template: `
    <div class="stars">
      @for (star of stars; track $index) {
        <button
          (click)="setRating($index + 1)"
          [class.filled]="$index < currentRating()"
          aria-label="Rate {{ $index + 1 }} stars"
        >★</button>
      }
    </div>
  `,
  styles: [`
    .stars { display: flex; gap: 4px; }
    .filled { color: gold; }
    button { border: none; background: none; cursor: pointer; font-size: 1.5rem; }
  `],
})
export class RatingWidgetComponent {
  // Signal inputs work — map to attributes
  maxStars = input(5);
  initialRating = input(0);

  // Outputs map to DOM CustomEvents
  rated = output<number>();

  stars = computed(() => Array(this.maxStars()).fill(0));
  currentRating = signal(this.initialRating());

  setRating(n: number): void {
    this.currentRating.set(n);
    this.rated.emit(n);
  }
}
```

### Using the custom element outside Angular

Once registered and bundled, the element works in any HTML context:

```html
<!-- Plain HTML page — no Angular knowledge needed -->
<script src="rating-widget-bundle.js"></script>

<rating-widget max-stars="5" initial-rating="3"></rating-widget>

<script>
  const widget = document.querySelector('rating-widget');

  // Read and set inputs via DOM properties
  console.log(widget.currentRating); // 3
  widget.initialRating = 4;          // set programmatically

  // Listen for outputs as native DOM events
  widget.addEventListener('rated', (event) => {
    console.log('User rated:', event.detail); // event.detail = the emitted value
  });
</script>
```

In a React app:

```jsx
// React — custom elements are native HTML so React renders them fine
// @Output() events become native DOM events — add listener via ref
function ProductPage() {
  const widgetRef = useRef(null);

  useEffect(() => {
    const el = widgetRef.current;
    const handler = (e) => console.log('Rated:', e.detail);
    el.addEventListener('rated', handler);
    return () => el.removeEventListener('rated', handler);
  }, []);

  return <rating-widget max-stars="5" initial-rating="3" ref={widgetRef} />;
}
```

### Building a self-contained bundle

To use an Angular Element on a non-Angular page, you need a single JS file
that includes Angular's runtime, the component, and all its dependencies:

```json
// angular.json — configure a dedicated build target
{
  "projects": {
    "my-elements": {
      "targets": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser-esbuild",
          "options": {
            "outputHashing": "none",   // predictable filenames
            "singleBundle": true       // all in one file
          }
        }
      }
    }
  }
}
```

```bash
ng build my-elements --configuration=production
```

Output: a single `main.js` file you can drop-ship to any page.

## Common mistakes

### Mistake 1 — Re-registering the same custom element

`customElements.define()` throws if the same tag name is registered twice
(e.g. during hot-reload development). Guard every registration:

```typescript
// ❌ Throws on second call — "DOMException: already defined"
customElements.define('my-widget', createCustomElement(MyComponent, { injector }));

// ✅ Guard with customElements.get()
if (!customElements.get('my-widget')) {
  customElements.define('my-widget', createCustomElement(MyComponent, { injector }));
}
```

### Mistake 2 — Using camelCase attribute names instead of kebab-case

Angular Elements automatically kebab-cases input names for HTML attributes.
Your HTML must use kebab-case; JavaScript property access uses camelCase:

```typescript
// Component input
@Input() userName = '';
// or: userName = input('');
```

```html
<!-- ✅ HTML attribute — kebab-case -->
<my-widget user-name="Alice"></my-widget>

<!-- ❌ HTML attribute — camelCase doesn't work in HTML -->
<my-widget userName="Alice"></my-widget>
```

```javascript
// ✅ JavaScript property — camelCase works on the DOM object
document.querySelector('my-widget').userName = 'Alice';
```

### Mistake 3 — Expecting @Output() values in event.data instead of event.detail

Angular Elements wraps `@Output()` EventEmitter emissions in a native
`CustomEvent`. The emitted value is in `event.detail`, not `event.data`:

```typescript
// Component
@Output() userSelected = new EventEmitter<User>();
```

```javascript
// ❌ event.data is undefined
element.addEventListener('userSelected', e => console.log(e.data));

// ✅ Emitted value is in event.detail
element.addEventListener('userSelected', e => console.log(e.detail));
```

### Mistake 4 — Missing ViewEncapsulation.ShadowDom when styles conflict

Without Shadow DOM, your component's styles and the host page's styles can
bleed into each other. This is acceptable for small internal use but becomes
a problem in micro-frontends or third-party embeds:

```typescript
// ❌ Default encapsulation — styles can bleed
@Component({ encapsulation: ViewEncapsulation.Emulated, ... })

// ✅ Shadow DOM — true isolation; host page styles can't affect internals
@Component({ encapsulation: ViewEncapsulation.ShadowDom, ... })
```

Note: `ViewEncapsulation.ShadowDom` means CSS custom properties (variables)
still pierce the shadow boundary (intentionally). Use them for theming
your elements from the host page.

## How this evolved

> - **Angular 6 (2018):** `@angular/elements` and `createCustomElement()`
>   introduced. Required NgModule-based setup with `entryComponents`. Fairly
>   verbose and the output bundles were large.
>
> - **Angular 9 (2020):** Ivy compiler dramatically reduced bundle sizes for
>   Angular Elements — some reports of 40-50% reduction in element bundle
>   size. NgModule requirement eased.
>
> - **Angular 13 (2021):** `entryComponents` removed (Ivy rendered it
>   unnecessary). Simpler setup with no special NgModule configuration.
>
> - **Angular 14 (2022):** Standalone components. `createCustomElement()` now
>   works directly with standalone components — no `NgModule` at all.
>   `createApplication()` introduced as a cleaner bootstrap for element-only
>   scenarios (no root app component needed).
>
> - **Angular 17+ (2023–2024):** Signal inputs (`input()`) supported by
>   Angular Elements — they map to attributes just like `@Input()`. The element
>   API stabilized; no breaking changes.
>
> - **Angular 22 (now):** Angular Elements is stable and unchanged from v17.
>   All Angular v22 features (signals, zoneless, signal forms) work inside
>   custom elements. For zoneless elements, note that the `createApplication()`
>   pattern should include `provideZonelessChangeDetection()` in providers.

## See also

- [View Encapsulation](../components/styling/view-encapsulation.md) — Shadow
  DOM encapsulation and why it matters for elements used outside Angular
- [Signals](../reactivity/signals.md) — signal inputs work inside Angular
  Elements components
- [Change Detection](../components/change-detection.md) — zoneless change
  detection in custom elements
- [Official docs — Angular Elements](https://angular.dev/guide/elements)
- [Web Components MDN — Custom Elements](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_custom_elements)

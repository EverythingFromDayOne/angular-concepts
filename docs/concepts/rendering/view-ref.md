---
roadmap_node: "view-ref"
title: "ViewRef & Renderer2"
file: "rendering/view-ref.md"
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

# ViewRef & Renderer2

> **Lead with this:** Angular's template syntax handles 95% of DOM work
> declaratively. `ViewContainerRef`, `ViewRef`, `EmbeddedViewRef`, and
> `Renderer2` are the lower-level APIs for the 5% that needs programmatic
> control — dynamic components, portal-style rendering, and safe imperative
> DOM manipulation.

## What it is

Angular maintains an internal **view tree** — a data structure that tracks
every component instance, its template bindings, and its position in the DOM.
The rendering APIs let you interact with this tree directly:

| API | What it does |
| --- | --- |
| `ViewContainerRef` | A slot where views can be dynamically inserted, moved, or removed |
| `ViewRef` | A handle to any view (component host view or embedded template view) |
| `EmbeddedViewRef<C>` | A rendered `ng-template` instance with a typed context object |
| `ComponentRef<C>` | A dynamically created component instance + its host view |
| `TemplateRef<C>` | A reference to an `<ng-template>` — the blueprint before rendering |
| `ElementRef<T>` | A wrapper around a native DOM element |
| `Renderer2` | Platform-agnostic DOM manipulation API |

## How it works under the hood

### Old approach — direct DOM manipulation

Before Angular's rendering APIs were well understood, developers wrote
directives and components that reached into the DOM directly:

```typescript
// ❌ Direct DOM manipulation — breaks SSR, bypasses Angular's security pipeline
@Component({ template: `<div #host></div>` })
export class OldComponent {
  @ViewChild('host') host!: ElementRef;

  showMessage(): void {
    const div = document.createElement('div');
    div.className = 'toast';
    div.innerHTML = `<strong>Success!</strong>`;     // XSS risk
    this.host.nativeElement.appendChild(div);
    setTimeout(() => div.remove(), 3000);
  }
}
```

Problems: no SSR support (`document` doesn't exist on the server), bypasses
Angular's DomSanitizer (XSS risk with `innerHTML`), untracked by Angular's
view tree (no CD, no destroy cleanup), incompatible with Web Workers.

### Angular's rendering model

Angular's rendering APIs route all DOM operations through abstractions:

**`Renderer2`** replaces `document.createElement` / `element.setAttribute`
with platform-agnostic calls that work in browser, SSR, Web Workers, and
NativeScript. The renderer knows which platform it's on and executes the
right operation.

**`ViewContainerRef`** replaces manual `appendChild`/`removeChild` with
view-level operations. When Angular inserts a view, it:
1. Adds the view to its internal view tree
2. Registers the view for change detection
3. Calls lifecycle hooks (`ngOnInit`, `ngAfterViewInit`) at the right time
4. Cleans up automatically when the container is destroyed

This means dynamically created components participate in the full Angular
lifecycle — they get CD, they get `ngOnDestroy`, they get DI — without extra
manual wiring.

### NgModule vs standalone — creating dynamic components

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Old approach (Angular 2–12) — required ComponentFactoryResolver
// Still works but deprecated — ComponentFactory is no longer needed
import { ComponentFactoryResolver, ViewContainerRef } from '@angular/core';

@Component({ template: `<ng-container #host></ng-container>` })
export class OldParent {
  @ViewChild('host', { read: ViewContainerRef }) host!: ViewContainerRef;
  private resolver = inject(ComponentFactoryResolver);  // deprecated

  show(): void {
    const factory = this.resolver.resolveComponentFactory(ToastComponent);
    this.host.createComponent(factory);   // factory-based — deprecated
  }
}
```

```typescript
// Modern approach (Angular 13+ — recommended)
// Pass the component class directly — no factory needed
import { ViewContainerRef, inject } from '@angular/core';

@Component({ template: `<ng-container #host></ng-container>` })
export class ModernParent {
  @ViewChild('host', { read: ViewContainerRef }) host!: ViewContainerRef;

  show(): void {
    this.host.createComponent(ToastComponent);   // class directly — clean
  }
}
```

## Basic usage

### ViewContainerRef — inserting components dynamically

```typescript
import {
  Component, ViewContainerRef, ViewChild,
  inject, Type, ComponentRef, signal
} from '@angular/core';

@Component({
  selector: 'app-toast-host',
  standalone: true,
  template: `<ng-container #toastContainer />`,
})
export class ToastHostComponent {
  @ViewChild('toastContainer', { read: ViewContainerRef })
  private container!: ViewContainerRef;

  private refs = new Map<string, ComponentRef<ToastComponent>>();

  show(message: string, type: 'success' | 'error'): void {
    const ref = this.container.createComponent(ToastComponent, {
      // Optional: pass a custom injector so the toast can DI app services
      injector: this.container.injector,
    });

    // Set inputs on the dynamically created component
    ref.setInput('message', message);
    ref.setInput('type', type);

    const id = crypto.randomUUID();
    this.refs.set(id, ref);

    // Auto-remove after 3 seconds
    setTimeout(() => this.dismiss(id), 3000);
  }

  dismiss(id: string): void {
    const ref = this.refs.get(id);
    if (ref) {
      ref.destroy();          // destroys the component and removes its DOM
      this.refs.delete(id);
    }
  }
}
```

**`ViewContainerRef` management methods:**

```typescript
const vcr: ViewContainerRef = ...;

vcr.createComponent(MyComp)           // create + insert at end
vcr.createComponent(MyComp, { index: 0 })  // create + insert at position 0
vcr.insert(viewRef)                   // insert an existing ViewRef
vcr.insert(viewRef, 0)                // insert at specific index
vcr.move(viewRef, 2)                  // move an existing view to index 2
vcr.detach(0)                         // remove from CD tree but KEEP DOM
vcr.remove(0)                         // remove and DESTROY the view
vcr.clear()                           // destroy all views in this container
vcr.length                            // number of views currently hosted
vcr.get(index)                        // get ViewRef at index
```

**`detach` vs `remove`:**
- `detach()` removes the view from Angular's view tree (stops CD) but leaves
  the DOM nodes in place. You can later `insert()` the detached `ViewRef` back
  in — the DOM nodes reappear.
- `remove()` calls `destroy()` on the view — DOM nodes removed, lifecycle
  hooks called, subscriptions cleaned up. Permanent.

Use `detach`/`insert` for show/hide optimization (avoid recreating expensive
components on toggle). Use `remove` when the component is no longer needed.

### EmbeddedViewRef — rendering ng-template programmatically

`ng-template` defines a lazy DOM fragment. `createEmbeddedView()` instantiates
it into actual DOM, optionally with a typed context:

```typescript
@Component({
  selector: 'app-conditional-renderer',
  standalone: true,
  template: `
    <ng-template #loadingTmpl>
      <div class="spinner">Loading…</div>
    </ng-template>

    <ng-template #errorTmpl let-message="message">
      <div class="error">{{ message }}</div>
    </ng-template>

    <ng-container #outlet />
  `,
})
export class ConditionalRendererComponent {
  @ViewChild('loadingTmpl') loadingRef!: TemplateRef<void>;
  @ViewChild('errorTmpl') errorRef!: TemplateRef<{ message: string }>;
  @ViewChild('outlet', { read: ViewContainerRef }) outlet!: ViewContainerRef;

  showLoading(): void {
    this.outlet.clear();
    this.outlet.createEmbeddedView(this.loadingRef);
  }

  showError(message: string): void {
    this.outlet.clear();
    // Context object provides values for `let-message` in the template
    this.outlet.createEmbeddedView(this.errorRef, { message });
  }

  clear(): void {
    this.outlet.clear();
  }
}
```

### ComponentRef — interacting with dynamically created components

`createComponent()` returns a `ComponentRef<T>` that gives you access to the
created component and its view:

```typescript
const ref: ComponentRef<DialogComponent> = vcr.createComponent(DialogComponent);

// Set inputs (works for both @Input() and input() signal inputs)
ref.setInput('title', 'Confirm deletion');
ref.setInput('message', 'Are you sure?');

// Read the component instance
ref.instance.confirmClicked.subscribe(() => { /* ... */ });

// Manually trigger CD (needed if you changed instance properties directly)
ref.changeDetectorRef.detectChanges();

// Get the host element
const el: ElementRef = ref.location;

// Destroy when done — removes DOM, calls ngOnDestroy
ref.destroy();
```

### Renderer2 — safe imperative DOM manipulation

Use `Renderer2` instead of raw DOM APIs in directives and components that need
to manipulate DOM imperatively:

```typescript
import { Directive, ElementRef, Renderer2, inject, HostListener } from '@angular/core';

@Directive({
  selector: '[appTooltip]',
  standalone: true,
})
export class TooltipDirective {
  private el = inject(ElementRef);
  private renderer = inject(Renderer2);
  private tooltipEl: HTMLElement | null = null;

  @HostListener('mouseenter')
  onEnter(): void {
    this.tooltipEl = this.renderer.createElement('div');
    this.renderer.addClass(this.tooltipEl, 'tooltip');
    this.renderer.setStyle(this.tooltipEl, 'position', 'absolute');
    this.renderer.setProperty(this.tooltipEl, 'textContent', 'Tooltip text');
    this.renderer.appendChild(this.el.nativeElement, this.tooltipEl);
  }

  @HostListener('mouseleave')
  onLeave(): void {
    if (this.tooltipEl) {
      this.renderer.removeChild(this.el.nativeElement, this.tooltipEl);
      this.tooltipEl = null;
    }
  }
}
```

**`Renderer2` method reference:**

```typescript
const r: Renderer2 = inject(Renderer2);

// Create / destroy elements
const el = r.createElement('div');       // creates <div>
const txt = r.createText('Hello');       // creates text node
const comment = r.createComment('...');  // creates <!-- --> node
r.destroyNode(el);                       // marks for cleanup

// Tree structure
r.appendChild(parent, child);
r.insertBefore(parent, child, refNode);
r.removeChild(parent, child);

// Attributes and properties
r.setAttribute(el, 'aria-label', 'Close');
r.removeAttribute(el, 'aria-label');
r.setProperty(el, 'textContent', 'Hello');    // DOM property (not attribute)

// Classes and styles
r.addClass(el, 'active');
r.removeClass(el, 'active');
r.setStyle(el, 'color', 'red');
r.setStyle(el, 'color', 'red', RendererStyleFlags2.Important);
r.removeStyle(el, 'color');

// Event listeners
const unlisten = r.listen(el, 'click', (e) => console.log(e));
unlisten();   // unregister the listener
```

## Real-world patterns

### Pattern 1 — Global portal service (toasts, dialogs)

A service that renders components outside the current component tree — at the
document level — via `ApplicationRef`:

```typescript
// overlay.service.ts
import { Injectable, ApplicationRef, inject, Type, ComponentRef, createComponent, EnvironmentInjector } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class OverlayService {
  private appRef = inject(ApplicationRef);
  private injector = inject(EnvironmentInjector);

  open<T>(component: Type<T>): ComponentRef<T> {
    // Create component outside any ViewContainerRef
    const ref = createComponent(component, {
      environmentInjector: this.injector,
    });

    // Attach to ApplicationRef so it participates in CD
    this.appRef.attachView(ref.hostView);

    // Insert native element into document body
    const domEl = (ref.hostView as any).rootNodes[0] as HTMLElement;
    document.body.appendChild(domEl);

    ref.onDestroy(() => {
      this.appRef.detachView(ref.hostView);
      domEl.remove();
    });

    return ref;
  }
}

// Usage
const toastRef = overlay.open(ToastComponent);
toastRef.setInput('message', 'Saved!');
setTimeout(() => toastRef.destroy(), 3000);
```

### Pattern 2 — Cached view pool for performance

`detach` + `insert` lets you reuse expensive views without destroying and
recreating them — useful for virtual scrolling or tab panels:

```typescript
@Component({ /* ... */ })
export class TabPanelComponent {
  @ViewChild('outlet', { read: ViewContainerRef }) outlet!: ViewContainerRef;

  private viewCache = new Map<string, EmbeddedViewRef<any>>();

  @ContentChildren(TabComponent) tabs!: QueryList<TabComponent>;

  activate(tab: TabComponent): void {
    // Detach all currently active views
    this.outlet.detach();

    if (this.viewCache.has(tab.id)) {
      // Re-insert the cached view — no recreation overhead
      this.outlet.insert(this.viewCache.get(tab.id)!);
    } else {
      // First activation — create and cache
      const ref = this.outlet.createEmbeddedView(tab.contentTemplate);
      this.viewCache.set(tab.id, ref);
    }
  }
}
```

## Common mistakes

### Mistake 1 — Manipulating nativeElement directly in SSR apps

`nativeElement.style`, `nativeElement.innerHTML`, `nativeElement.classList`
only exist in the browser. During SSR these properties are either missing or
simulated — code that accesses them directly crashes or behaves unexpectedly:

```typescript
// ❌ Fails during SSR — style doesn't exist on server DOM emulation
@Directive({ selector: '[appHighlight]', standalone: true })
export class HighlightDirective {
  el = inject(ElementRef);
  ngOnInit() { this.el.nativeElement.style.background = 'yellow'; }
}

// ✅ Renderer2 — works in all Angular rendering contexts
@Directive({ selector: '[appHighlight]', standalone: true })
export class HighlightDirective {
  el = inject(ElementRef);
  r = inject(Renderer2);
  ngOnInit() { this.r.setStyle(this.el.nativeElement, 'background', 'yellow'); }
}
```

### Mistake 2 — Forgetting to destroy ComponentRef

`createComponent()` doesn't auto-clean up when the parent destroys unless
the `ComponentRef` is attached to a `ViewContainerRef` or `ApplicationRef`:

```typescript
// ❌ ComponentRef leaks — never destroyed
@Component({ /* ... */ })
export class ParentComponent {
  ngOnInit(): void {
    // createComponent() via ApplicationRef but never tracking the ref
    const ref = createComponent(ToastComponent, { environmentInjector: this.injector });
    this.appRef.attachView(ref.hostView);
    // ref is lost — will never be destroyed
  }
}

// ✅ Track refs and destroy on ngOnDestroy
export class ParentComponent implements OnDestroy {
  private toastRef?: ComponentRef<ToastComponent>;

  show(): void {
    this.toastRef = createComponent(ToastComponent, { ... });
  }

  ngOnDestroy(): void {
    this.toastRef?.destroy();
  }
}
```

### Mistake 3 — Reading ViewChild before ngAfterViewInit

`ViewContainerRef`, `TemplateRef`, and `ElementRef` queried with `@ViewChild`
are not available until `ngAfterViewInit`. Reading them in `ngOnInit` gives
`undefined`:

```typescript
// ❌ host is undefined in ngOnInit
@Component({ template: `<ng-container #host />` })
export class WrongComponent implements OnInit {
  @ViewChild('host', { read: ViewContainerRef }) host!: ViewContainerRef;

  ngOnInit(): void {
    this.host.createComponent(MyComp);   // TypeError: cannot call createComponent of undefined
  }
}

// ✅ Wait for ngAfterViewInit
export class CorrectComponent implements AfterViewInit {
  @ViewChild('host', { read: ViewContainerRef }) host!: ViewContainerRef;

  ngAfterViewInit(): void {
    this.host.createComponent(MyComp);   // safe — host is initialized
  }
}
```

## How this evolved

> - **Angular 2 (2016):** `ViewContainerRef`, `TemplateRef`, `EmbeddedViewRef`,
>   `ComponentRef`, `ElementRef`, and `Renderer2` all introduced. Dynamic
>   component creation required a `ComponentFactory` from
>   `ComponentFactoryResolver` — verbose, two-step process.
>
> - **Angular 9 (2020):** Ivy compiler rearchitected the view tree internally
>   but kept the public APIs compatible. Under Ivy, dynamic components became
>   faster because the compiler pre-compiles each component independently.
>
> - **Angular 13 (2021):** `ViewContainerRef.createComponent(ComponentType)`
>   overload added — pass the class directly, no factory needed.
>   `ComponentFactoryResolver` deprecated. `ApplicationRef.createComponent()`
>   added as a standalone entry point for portal-style rendering.
>
> - **Angular 14 (2022):** Standalone components work seamlessly with dynamic
>   creation — no `NgModule` needed in the `createComponent` options for
>   standalone components.
>
> - **Angular 17 (2023):** `createComponent` options extended with `directives`
>   and `bindings` — apply directives to dynamically created components
>   declaratively in the options object rather than imperatively afterwards.
>
> - **Angular 22 (now):** The rendering API is stable. `ComponentFactoryResolver`
>   is still present for migration but fully deprecated — all new code should
>   use `createComponent(Type)`. `Renderer2` remains the recommended safe DOM
>   manipulation API for all platforms.

## See also

- [Lifecycle](../components/lifecycle.md) — `ngAfterViewInit` timing for when
  `ViewChild` queries become safe to use
- [Dynamic Components](../components/dynamic-components.md) — higher-level
  patterns built on `ViewContainerRef.createComponent()`
- [SSR & Hydration](./ssr-hydration.md) — why `Renderer2` matters for SSR
  correctness
- [Dependency Injection](../dependency-injection/dependency-injection.md) —
  the `injector` option in `createComponent` for custom DI scoping
- [Official docs — ViewContainerRef](https://angular.dev/api/core/ViewContainerRef)
- [Official docs — Renderer2](https://angular.dev/api/core/Renderer2)
- [Official docs — Dynamic components](https://angular.dev/guide/components/dynamic-components)

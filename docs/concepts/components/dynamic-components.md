---
roadmap_node: "dynamic-components"
title: "Dynamic Components in Angular"
file: "components/dynamic-components.md"
source_days: [38]
original_authors: ["Khanh Tiet"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Dynamic Components in Angular

> **⚡ What changed since the original**
>
> This article was first written for Angular 9 (2020). The **concept** of
> dynamic components — loading the right child at runtime via `ViewContainerRef`
> — is unchanged in v22. What changed is **the entire API surface around it**:
>
> - **`ComponentFactoryResolver` is removed in Angular 22.** It was deprecated
>   in v13 when Ivy made factories redundant, and removed entirely in v22. The
>   `cfr.resolveComponentFactory(MyComponent)` step is gone.
> - **`ViewContainerRef.createComponent()` takes a component class directly.**
>   No more factory. `viewContainerRef.createComponent(MyComponent)` is the
>   whole call.
> - **`entryComponents` was removed.** It's not just deprecated — the `NgModule`
>   metadata field that pre-Ivy dynamic components required is gone since v15.
> - **`@Input()` → `input()` signal input.** And critically, **assigning
>   `componentRef.instance.data = '...'` doesn't properly trigger reactivity
>   for signal inputs.** Use **`componentRef.setInput('data', value)`** instead
>   (added in v14, mandatory for correctness with signal inputs).
> - **The new bindings options API (v20+)** — pass `inputBinding()`,
>   `outputBinding()`, `twoWayBinding()` to `createComponent` to declare
>   bindings at creation time, like a template would. Eliminates the
>   "set inputs after the first change detection" timing problem.
> - **`@ViewChild('ref', { read: ViewContainerRef })` → `viewChild('ref', { read: ViewContainerRef })`** signal query.
> - **`@NgModule` → standalone components.**
> - **`NgComponentOutlet`** from `@angular/common` is the **higher-level**
>   alternative — declarative dynamic components in templates, no
>   `ViewContainerRef` plumbing. Use it when the host slot is template-driven.
>
> The original Angular 9 walkthrough is preserved with `<!-- legacy -->`
> markers and followed by v22 equivalents. The mechanism reflection at the
> end explains **why** `ComponentFactory` and `ComponentFactoryResolver`
> existed in the first place (View Engine NgFactory files) and what Ivy
> changed to make them dead weight.
>
> **See also**: [Signal Inputs](../reactivity/signal-inputs.md) · [Signal Queries](../reactivity/signal-queries.md) · [Standalone Migration](../tooling/standalone-migration.md) · [Change Detection](../components/change-detection.md)

---

## Introduction

You already know parent/child components and how they interact. Consider parent **A** hosting child **B**:

![ParentComponent](assets/day-38-dynamic-component-01.png) <!-- TODO: asset -->

Sometimes at runtime you don't want a fixed child — sometimes **B**, sometimes **C**, depending on app logic. Or you want the user to do something in **A** before **B** loads. With a static template, **B** is always a child of **A**.

**Dynamic components** load the right component at runtime. That's what we'll explore today.

## Coding practice

### Step 1: Initialize the project

```sh
ng new dynamic-component-demo
```

### Step 2: Create components

```sh
ng g c example-container
```

```sh
ng g c dynamic-content-one
```

```sh
ng g c dynamic-content-two
```

In v22, `ng g c` produces standalone components by default — no `--standalone` flag.

Add the container to `app.component.html`. The selector tag stays the same; in v22 `AppComponent` imports `ExampleContainerComponent` directly:

```html
<app-example-container></app-example-container>
```

```ts
// app.component.ts (v22)
import { Component } from '@angular/core';
import { ExampleContainerComponent } from './example-container/example-container.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  imports: [ExampleContainerComponent],
})
export class AppComponent {}
```

### Step 3: Code the container component

Template with two buttons and a `ViewChild` host:

```html
<button (click)="addDynamicCompOne()" class="btn">
  Add Dynamic Component 1
</button>
<button (click)="addDynamicCompTwo()" class="btn">
  Add Dynamic Component 2
</button>

<div #dynamicComponent></div>
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: ComponentFactoryResolver + @ViewChild decorator
import {
  Component,
  OnInit,
  ViewChild,
  ViewContainerRef,
  ComponentFactoryResolver,
} from "@angular/core";
import { DynamicContentOneComponent } from "../dynamic-content-one/dynamic-content-one.component";
import { DynamicContentTwoComponent } from "../dynamic-content-two/dynamic-content-two.component";

@Component({
  selector: "app-example-container",
  templateUrl: "./example-container.component.html",
  styleUrls: ["./example-container.component.scss"],
})
export class ExampleContainerComponent implements OnInit {
  @ViewChild("dynamicComponent", { read: ViewContainerRef, static: true })
  containerRef: ViewContainerRef;

  constructor(private cfr: ComponentFactoryResolver) {}

  ngOnInit() {}

  addDynamicCompOne() {
    const componentFactory = this.cfr.resolveComponentFactory(
      DynamicContentOneComponent
    );
    const componentRef = this.containerRef.createComponent(componentFactory);
  }

  addDynamicCompTwo() {
    const componentFactory = this.cfr.resolveComponentFactory(
      DynamicContentTwoComponent
    );
    const componentRef = this.containerRef.createComponent(componentFactory);
  }
}
```

```typescript
// ── v22 equivalent: signal query + direct createComponent(Type) ───────────
import { Component, ViewContainerRef, viewChild } from "@angular/core";
import { DynamicContentOneComponent } from "../dynamic-content-one/dynamic-content-one.component";
import { DynamicContentTwoComponent } from "../dynamic-content-two/dynamic-content-two.component";

@Component({
  selector: "app-example-container",
  templateUrl: "./example-container.component.html",
  styleUrl: "./example-container.component.scss",
})
export class ExampleContainerComponent {
  // Signal query — returns Signal<ViewContainerRef | undefined>.
  // Read it as containerRef() at call time.
  readonly containerRef = viewChild("dynamicComponent", { read: ViewContainerRef });

  // No ComponentFactoryResolver, no constructor, no ngOnInit.

  addDynamicCompOne() {
    // Pass the component class directly — no factory resolution step.
    const ref = this.containerRef()?.createComponent(DynamicContentOneComponent);
  }

  addDynamicCompTwo() {
    const ref = this.containerRef()?.createComponent(DynamicContentTwoComponent);
  }
}
```

The flow collapses to two facts:

1. `viewChild('dynamicComponent', { read: ViewContainerRef })` gives you a signal that resolves to the `ViewContainerRef` for the `#dynamicComponent` element.
2. `containerRef().createComponent(MyComponent)` instantiates it. The component class **is** the factory in Ivy — there's nothing to resolve.

The original article's five-step explanation reduces to those two lines. Everything else (`ComponentFactoryResolver`, `resolveComponentFactory`, the factory parameter on `createComponent`) was scaffolding the View Engine compiler needed and Ivy doesn't.

### Step 4: ~~Add dynamic components to `entryComponents`~~ Not needed in v22

In Angular 9, the code above wouldn't run without registering both dynamic components in **`entryComponents`**. Otherwise you'd hit: "No component factory found ..."

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: required entryComponents declaration
@NgModule({
  declarations: [
    AppComponent,
    ExampleContainerComponent,
    DynamicContentOneComponent,
    DynamicContentTwoComponent,
  ],
  imports: [BrowserModule],
  providers: [],
  bootstrap: [AppComponent],
  entryComponents: [DynamicContentOneComponent, DynamicContentTwoComponent],
})
```

In v22, **`entryComponents` doesn't exist** — it was removed from `@NgModule` metadata in Angular 15. Standalone components don't need module-level registration at all; they're discovered via their `imports` array or via `import()` for lazy loading. This whole step is gone.

### Step 5: Clear dynamic components

This step is unchanged in v22 — `containerRef.clear()` still works:

```html
<button (click)="clearDynamicComp()" class="btn">Clear</button>
```

```typescript
// v22 — read the signal, then clear
clearDynamicComp() {
  this.containerRef()?.clear();
}
```

### Step 6: Interact with dynamic components — and why `setInput()` matters

Same as parent/child communication. On the child, declare the input.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: decorator input
@Input()
data: string;
```

```typescript
// ── v22 equivalent: signal input ──────────────────────────────────────────
import { Component, input } from '@angular/core';

@Component({ /* ... */ })
export class DynamicContentOneComponent {
  readonly data = input<string>('');
}
```

Template (unchanged shape; just note `data()` is a signal read):

```html
<h1>DYNAMIC CONTENT 1</h1>
<p>++++++{{ data() }}+++++++++</p>
```

On the parent, the Angular 9 article set properties on `componentRef.instance`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: assign directly to instance property
addDynamicCompOne() {
  const componentFactory = this.cfr.resolveComponentFactory(
    DynamicContentOneComponent
  );
  const componentRef = this.containerRef.createComponent(componentFactory);
  componentRef.instance.data = "INPUT DATA 1";
}
```

```typescript
// ── v22 equivalent: use setInput() — required for signal inputs ───────────
addDynamicCompOne() {
  const ref = this.containerRef()?.createComponent(DynamicContentOneComponent);
  ref?.setInput('data', 'INPUT DATA 1');
}
```

**Why `setInput()` instead of `ref.instance.data = '...'`?** With decorator
inputs the direct assignment worked because the field was just a class
property — the framework's binding pipeline was implicit. **Signal inputs are
read-only from outside the component** — `data` is an `InputSignal<string>`,
not a plain property, and the only sanctioned way to write to it externally
is through `ComponentRef.setInput(name, value)`. `setInput()` routes through
Angular's input binding machinery, triggers OnPush change detection
correctly, and updates the underlying signal so `computed()` and `effect()`
react.

Direct `ref.instance.data` assignment on a signal input either won't
compile (TypeScript catches it) or silently fails to propagate. Use
`setInput()` for **every** input on a dynamically-created component going
forward — it works for both decorator and signal inputs, so it's safe as a
default.

#### Even better in v20+ — bindings declared at creation time

Angular 20 added a bindings options API that lets you wire inputs and outputs
**during** creation, not after. This eliminates a subtle timing issue: when
you call `setInput()` *after* `createComponent()`, the first change detection
cycle has already run, so any `OnInit`/`effect()` setup in the dynamic
component sees the input as undefined until the next tick.

```typescript
// v20+: declarative bindings via createComponent options
import { inputBinding, outputBinding } from '@angular/core';

addDynamicCompOne() {
  this.containerRef()?.createComponent(DynamicContentOneComponent, {
    bindings: [
      // Bound at construction — visible on the first change detection cycle.
      inputBinding('data', () => 'INPUT DATA 1'),
      // Listen to outputs the same way you would in a template.
      // outputBinding('clicked', (event) => this.handleClick(event)),
      // Two-way binding ([(model)] equivalent):
      // twoWayBinding('value', this.someWritableSignal),
    ],
  });
}
```

The `inputBinding()` function takes the input name and a **factory function**
returning the current value. Angular subscribes to the function in a
reactive context — if you return a signal read like `() => this.someSignal()`,
the binding stays live and updates the dynamic component whenever the source
signal changes. This is the closest you'll get to "writing template bindings
in TypeScript."

### Step 7: Lazy loading dynamic components

`entryComponents` is gone, but lazy loading via dynamic `import()` is more
useful than ever — it splits the dynamic components into separate bundles
that only download when needed.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9 Ivy era: dynamic import + factory resolution
async addDynamicCompOne() {
  const { DynamicContentOneComponent } = await import('../dynamic-content-one/dynamic-content-one.component');
  const componentFactory = this.cfr.resolveComponentFactory(
    DynamicContentOneComponent
  );
  const componentRef = this.containerRef.createComponent(componentFactory);
  componentRef.instance.data = "INPUT DATA 1";
}

async addDynamicCompTwo() {
  const { DynamicContentTwoComponent } = await import('../dynamic-content-two/dynamic-content-two.component');
  const componentFactory = this.cfr.resolveComponentFactory(
    DynamicContentTwoComponent
  );
  const componentRef = this.containerRef.createComponent(componentFactory);
  componentRef.instance.data = "INPUT DATA 2";
}
```

```typescript
// ── v22 equivalent: dynamic import + direct class + setInput (or bindings)
async addDynamicCompOne() {
  const { DynamicContentOneComponent } = await import(
    '../dynamic-content-one/dynamic-content-one.component'
  );
  this.containerRef()?.createComponent(DynamicContentOneComponent, {
    bindings: [inputBinding('data', () => 'INPUT DATA 1')],
  });
}

async addDynamicCompTwo() {
  const { DynamicContentTwoComponent } = await import(
    '../dynamic-content-two/dynamic-content-two.component'
  );
  this.containerRef()?.createComponent(DynamicContentTwoComponent, {
    bindings: [inputBinding('data', () => 'INPUT DATA 2')],
  });
}
```

The Angular 9 `app.module.ts` cleanup step (removing the dynamic components
from `declarations`) is irrelevant in v22 — there's no `AppModule`, just
`bootstrapApplication(AppComponent, appConfig)`. Standalone components are
self-declaring.

### Bonus — `NgComponentOutlet` for template-driven dynamic components

For cases where the host slot is in your template (and you don't need fine-
grained programmatic control), `NgComponentOutlet` from `@angular/common` is
significantly cleaner than the `ViewContainerRef.createComponent` plumbing:

```typescript
import { Component, signal } from '@angular/core';
import { NgComponentOutlet } from '@angular/common';
import { DynamicContentOneComponent } from './dynamic-content-one.component';
import { DynamicContentTwoComponent } from './dynamic-content-two.component';

@Component({
  selector: 'app-example-container',
  imports: [NgComponentOutlet],
  template: `
    <button (click)="show('one')">Show 1</button>
    <button (click)="show('two')">Show 2</button>

    @if (current()) {
      <ng-container
        *ngComponentOutlet="current()!; inputs: { data: dataFor() }">
      </ng-container>
    }
  `,
})
export class ExampleContainerComponent {
  readonly current = signal<typeof DynamicContentOneComponent | typeof DynamicContentTwoComponent | null>(null);
  readonly dataFor = signal('');

  show(which: 'one' | 'two') {
    if (which === 'one') {
      this.current.set(DynamicContentOneComponent);
      this.dataFor.set('INPUT DATA 1');
    } else {
      this.current.set(DynamicContentTwoComponent);
      this.dataFor.set('INPUT DATA 2');
    }
  }
}
```

When you swap the value of `current()`, Angular destroys the previous component
and creates the new one. The `inputs` map on `NgComponentOutlet` is the
declarative equivalent of calling `setInput()` for each entry. For modal
hosts, tab switchers, plugin slots, or any "show the right component based on
state" pattern, this is usually what you want.

`ViewContainerRef.createComponent` is for cases where you need imperative
control — multiple dynamic components in the same host, programmatic
positioning via the `index` option, custom environment injectors, or
fine-grained control over creation timing.

## Concepts (v22)

### ViewContainerRef

A container that can create **host views** (from components) and **embedded
views** (from `TemplateRef`). Think of it as a DOM-like anchor where views
attach. Unchanged in v22, but the `createComponent` signature is now:

```typescript
createComponent<C>(
  componentType: Type<C>,
  options?: {
    index?: number;
    injector?: Injector;
    ngModuleRef?: NgModuleRef<unknown>;     // legacy escape hatch
    environmentInjector?: EnvironmentInjector | NgModuleRef<unknown>;
    projectableNodes?: Node[][];
    bindings?: Binding[];                    // v20+ — inputBinding/outputBinding/twoWayBinding
    directives?: (Type<unknown> | DirectiveWithBindings)[];  // v20+ — apply directives to dynamic component
  }
): ComponentRef<C>;
```

The `bindings` and `directives` options are the v20+ improvements that make
`createComponent` feel like a template binding rather than a constructor call.

### ComponentRef

The handle returned by `createComponent`. Key v22-relevant methods:

- `ref.setInput(name, value)` — write an input the framework-correct way
  (mandatory for signal inputs).
- `ref.instance` — the component instance. Read-only for signal inputs
  (you can read but not write `instance.signalInput`). Outputs on the
  instance can be subscribed to: `ref.instance.someOutput.subscribe(...)`.
- `ref.destroy()` — manually destroy. Usually you let the parent
  `ViewContainerRef` handle this.
- `ref.changeDetectorRef` — for manual change detection when needed
  (rare with signals).

### ~~ComponentFactory and ComponentFactoryResolver~~

**Removed in Angular 22.** These were the View Engine bridge that let the
runtime instantiate components compiled ahead of time. Ivy compiled the
factory logic directly into each component class (`ɵfac` and `ɵcmp` static
properties), so the resolver layer became pure overhead. See the mechanism
reflection below for the full story.

## Exercises

### 1. Replace component, not add

The demo stacks components in one `ViewChild`. Build **replace** behavior:
button A shows component A; button B **replaces** A with B.

(Hint: `containerRef().clear()` before each `createComponent` call, or use
`NgComponentOutlet` from the bonus section.)

### 2. Listen to outputs from a dynamic child

Use `outputBinding('clicked', (event) => this.handleClick(event))` in the
`bindings` option to listen to a child output. Compare to the old
"subscribe to `ref.instance.clicked` after creation" pattern.

---

## Mechanism reflection — why `ComponentFactory` existed and why it's gone

The factory-resolver pattern in the original article wasn't gratuitous
ceremony — it was load-bearing in Angular's old View Engine compiler. Once
you understand why it existed, the v22 removal makes more sense than just
"they simplified the API."

### Angular's View Engine compiler (Angular 2 – early v9)

Before Ivy, Angular's compiler emitted **NgFactory files** alongside your
components. For every `MyComponent` you wrote, the AOT compiler generated a
sibling file `my.component.ngfactory.js` (sometimes `.ngfactory.ts` in dev
builds) that contained a generated `MyComponentNgFactory` class. The factory
file held the imperative code to create a view of that component: how to set
up bindings, how to wire change detection, which DI tokens to look up,
which child components to instantiate.

At runtime, when Angular wanted to instantiate `MyComponent`, it didn't call
`new MyComponent()` directly. It went through a three-step dance:

1. Look up the component type → factory mapping. The mapping lived in the
   NgModule that *declared* the component, registered via a special
   `entryComponents` array.
2. `ComponentFactoryResolver.resolveComponentFactory(MyComponent)` returned
   the corresponding `MyComponentNgFactory` instance from that mapping.
3. `factory.create(injector)` actually instantiated the component view —
   creating the DOM, running the template, wiring change detection.

This is why pre-Ivy dynamic components needed `entryComponents`. The
factory-resolver only knew about types in its own module's `entryComponents`
list. Components reached via routes or template tags were automatically
listed (the compiler inferred them); components reached *only* via
`createComponent` calls weren't, so you had to list them by hand.

### Why the factory had to be a separate file

The View Engine compiler did **global program analysis** — it needed to see
your whole app to optimize template output. The factory files were the
output of that analysis: a flattened, runtime-ready representation of every
component's view. This is also why pre-Ivy AOT builds were slow and why
component libraries had to ship their `.ngfactory.d.ts` files: the factory
had to exist as a separate compiled artifact for the Angular runtime to
consume.

The cost: each NgFactory file was ~3–5x the size of the original component
source, the bundle had to include a giant lookup table from class → factory,
and the runtime had to maintain a resolver registry per module. You also got
the famous "No component factory found" error if you forgot
`entryComponents`.

### What Ivy changed (Angular 9, default in v9)

Ivy replaced the global-analysis compiler with a **per-component compiler**.
Each component file compiles in isolation, and the generated factory code
lives **inside the same class** as static properties:

```typescript
// Approximate shape of what Ivy emits — simplified
class MyComponent {
  // Your code: properties, methods, lifecycle hooks
  data = '';
  ngOnInit() { /* ... */ }

  // Emitted by the Ivy compiler — directly on the class:
  static ɵfac = function MyComponent_Factory(t) { return new (t || MyComponent)(); };
  static ɵcmp = ɵɵdefineComponent({
    type: MyComponent,
    selectors: [['app-my-component']],
    decls: 5,
    vars: 1,
    template: function MyComponent_Template(rf, ctx) { /* compiled template */ },
    // ...
  });
}
```

`ɵfac` is the factory function. `ɵcmp` is the component definition. **The
class is its own factory.** There's no separate NgFactory file, no module-
level lookup table, no resolver to register.

Once Ivy was the only compiler (Angular 13), `ComponentFactoryResolver`
became a wrapper around a one-line lookup: "given a component class,
return its `ɵfac`." It worked, but it was pointless ceremony — you already
had the class. Hence the deprecation note that landed in v13:
*"since v13, dynamic component creation via ViewContainerRef.createComponent
does not require resolving component factory: component class can be used
directly."*

`entryComponents` was deprecated alongside it — there's no factory registry
to register into when each class carries its own factory.

### The removal arc

- **Angular 9 (2020):** Ivy ships as opt-out; factory-based APIs remain
  the documented path.
- **Angular 13 (2021):** Ivy becomes the only compiler. View Engine removed.
  `ComponentFactoryResolver` deprecated. `ViewContainerRef.createComponent`
  starts accepting a component class directly.
- **Angular 14 (2022):** `ComponentRef.setInput()` added — the type-safe,
  reactive-system-aware way to set inputs on a dynamic component.
- **Angular 15 (2022):** `entryComponents` field removed from `@NgModule`
  metadata.
- **Angular 20 (2025):** Bindings options API stabilizes —
  `inputBinding`/`outputBinding`/`twoWayBinding` for declarative
  binding at creation time.
- **Angular 22 (now):** `ComponentFactoryResolver`, `ComponentFactory`, and
  the factory-accepting overload of `ViewContainerRef.createComponent`
  are removed from the public API.

### Why `setInput()` exists at all

If Ivy "just calls the constructor and runs the template" mentally, why does
`setInput()` need to exist? Why isn't `ref.instance.data = 'x'` enough?

Two reasons.

**One:** for **signal inputs**, `input()` returns an `InputSignal<T>` — an
object with internal write-tracking machinery. Assigning to it from outside
either fails TypeScript checks (the type is read-only) or, if you cast around
it, writes to a field that the framework doesn't read from. `setInput()`
routes through the framework's input-binding pipeline, which knows how to
write the underlying signal slot and trigger reactivity.

**Two:** for **decorator inputs**, assigning to `ref.instance.foo` works at
runtime but bypasses the change-detection notification path. With default
change detection it usually works by accident on the next tick; with
`OnPush`, the dynamic component may not re-render until something else
triggers detection. `setInput()` marks the view dirty correctly.

The v20 bindings API takes this one step further: by declaring bindings at
**creation** time, the framework runs the *first* change detection cycle
with the inputs already in place — no "set values, then mark dirty, then
detect changes" sequencing issue at all. This is closer to how template
bindings work: when you write `<my-component [data]="value" />`, the input
is bound before the component runs `ngOnInit` or any `effect()` setup.

### What stayed the same

Conceptually, dynamic components in v22 are the same shape as Angular 9:

- You still need a `ViewContainerRef` to anchor the dynamic view in the DOM
- You still get a `ComponentRef<T>` back from creation
- You still call `clear()` to remove all children, `destroy()` to dispose one
- You can still listen to outputs via `ref.instance.someOutput.subscribe(...)`
  (or now via `outputBinding()`)
- Content projection via `projectableNodes` still works the same way
- The component still goes through its full lifecycle:
  `ngOnInit`, `effect()` setup, change detection, eventually `ngOnDestroy`

The verbs and nouns are the same. Just no factory.

---

## Summary

You learned dynamic component loading in Angular v22: `ViewContainerRef.createComponent`
takes a component class directly (no factory), `ComponentRef.setInput()` is
the correct way to set inputs (especially signal inputs), the v20+
`inputBinding`/`outputBinding`/`twoWayBinding` options bind at creation time,
and `NgComponentOutlet` is the declarative template-driven alternative when
you don't need imperative control. The deeper takeaway: `ComponentFactoryResolver`
existed because the View Engine compiler split component code into separate
factory files; Ivy made the class its own factory, and v22 finalized the
cleanup by removing the resolver entirely.

## See also

- [Signal Inputs](../reactivity/signal-inputs.md) — `input()`, `input.required()`, `model()`
- [Signal Queries](../reactivity/signal-queries.md) — `viewChild()`, `viewChildren()`, `contentChild()`
- [Change Detection](../components/change-detection.md) — why `setInput()` handles `OnPush` correctly
- [Standalone Migration](../tooling/standalone-migration.md) — why `entryComponents` and `@NgModule` are gone
- [Defer Blocks](../rendering/defer-blocks.md) — `@defer` is often a better fit than imperative dynamic loading for "render this component when needed"

## Code sample

- https://github.com/januaryofmine/Dynamic-Component-Demo

## References

- [Dynamic component loader (angular.dev)](https://angular.dev/guide/components/dynamic-component-loader)
- [`ViewContainerRef.createComponent` API](https://angular.dev/api/core/ViewContainerRef#createComponent)
- [`ComponentRef.setInput` API](https://angular.dev/api/core/ComponentRef#setInput)
- [`NgComponentOutlet` API](https://angular.dev/api/common/NgComponentOutlet)
- [`inputBinding`, `outputBinding`, `twoWayBinding` (v20+)](https://angular.dev/api/core/inputBinding)
- [Dynamic component rendering in 5 minutes (Vietnamese)](https://www.tiepphan.com/angular-trong-5-phut-dynamic-component-rendering/)
- https://stackblitz.com/edit/angular-dynamic-components-example
- https://www.youtube.com/watch?v=dZD7pw6rmRA

## Author

Khanh Tiet — https://github.com/januaryofmine

*Translated from the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) series by Angular Vietnam. MIT licensed.*

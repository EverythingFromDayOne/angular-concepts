---
roadmap_node: "dynamic-components"
title: "Dynamic Components in Angular"
file: "components/dynamic-components.md"
source_days: [38]
original_authors: ["Khanh Tiet"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Dynamic Components in Angular

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

Add the container to `app.component.html`:

```html
<app-example-container></app-example-container>
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

Flow:

1. Create a `ViewChild` on `#dynamicComponent` — the DOM host for runtime components.
2. Bind it with `@ViewChild` → you get a `ViewContainerRef`.
3. Inject `ComponentFactoryResolver`.
4. Resolve a factory for the component to load.

```typescript
const componentFactory = this.cfr.resolveComponentFactory(
  DynamicContentOneComponent
);
```

5. Call `ViewContainerRef.createComponent(componentFactory)` to instantiate the dynamic component.

```typescript
const componentRef = this.containerRef.createComponent(componentFactory);
```

### Step 4: Add dynamic components to `entryComponents`

For the code above to work (pre-Ivy), add both dynamic components to **`entryComponents`**. Otherwise: "No component factory found ..."

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript

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

With Angular Ivy you can skip this step.

### Step 5: Clear dynamic components

```html
<button (click)="clearDynamicComp()" class="btn">Clear</button>
```

```typescript
clearDynamicComp() {
    this.containerRef.clear();
  }
```

### Step 6: Interact with dynamic components

Same as parent/child communication. On the child:

```typescript
@Input()
  data: string;
```

```html
<h1>DYNAMIC CONTENT 1</h1>
<p>++++++{{data}}+++++++++</p>
```

On the parent, set properties on `componentRef.instance`:

```typescript
addDynamicCompOne() {
    const componentFactory = this.cfr.resolveComponentFactory(
      DynamicContentOneComponent
    );
    const componentRef = this.containerRef.createComponent(componentFactory);
    componentRef.instance.data = "INPUT DATA 1";
  }
```

### Step 7: Update with Angular Ivy lazy load

`entryComponents` is legacy. With **Angular Ivy** you can dynamically `import()` components.

#### Step 7.1: Remove `entryComponents` from `app.module.ts`

#### Step 7.2: Update the container component

- Remove static imports of the dynamic components.
- Make `addDynamicComp*` methods async with dynamic `import()`:

```typescript
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

#### Step 7.3: Update `app.module.ts`

Remove dynamic component imports from declarations:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
  import { BrowserModule } from "@angular/platform-browser";
  import { NgModule } from "@angular/core";

  import { AppComponent } from "./app.component";
  import { ExampleContainerComponent } from "./example-container/example-container.component";

  @NgModule({
    declarations: [AppComponent, ExampleContainerComponent],
    imports: [BrowserModule],
    providers: [],
    bootstrap: [AppComponent],
  })
  export class AppModule {}
```

You can lazy-load dynamic components without declaring them upfront. **Note:** upgrade to an Ivy-enabled Angular version if you're on an older release.

## Concepts

### ViewContainerRef

A container that can create **host views** (from components) and **embedded views** (from `TemplateRef`). Think of it as a DOM-like anchor where views attach. Containers can nest (`ng-container`, etc.).

![Dynamic component rendering (Vietnamese)](https://www.tiepphan.com/angular-trong-5-phut-dynamic-component-rendering/) <!-- TODO: asset -->

### ComponentFactory

Class that creates dynamic component instances — returned by `ComponentFactoryResolver.resolveComponentFactory()`.

### ComponentFactoryResolver

Resolves a component type into a `ComponentFactory` that `ViewContainerRef` uses to create the instance.

## Exercises

### 1. Replace component, not add

The demo stacks components in one `ViewChild`. Build **replace** behavior: button A shows component A; button B **replaces** A with B.

### 2. Interact with more view children

Use multiple `ViewChild` hosts and load different dynamic components into each. Try emitting events from a dynamic child and handling them in the parent.

## Summary

You learned dynamic component loading with `ViewContainerRef` and `ComponentFactoryResolver`, clearing hosts, passing `@Input` data, and Ivy-era dynamic imports. Practice with the exercises and references below.

## Code sample

- https://github.com/januaryofmine/Dynamic-Component-Demo

## References

- https://angular.io/guide/dynamic-component-loader
- [Dynamic component rendering in 5 minutes (Vietnamese)](https://www.tiepphan.com/angular-trong-5-phut-dynamic-component-rendering/)
- https://stackblitz.com/edit/angular-dynamic-components-example
- https://www.youtube.com/watch?v=dZD7pw6rmRA

## Author

Khanh Tiet — https://github.com/januaryofmine

*Translated from the original Vietnamese as part of the angular-concepts project.*

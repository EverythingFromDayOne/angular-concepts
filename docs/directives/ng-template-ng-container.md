---
roadmap_node: "ng-template-ng-container"
title: "ng-template, ngTemplateOutlet, and ng-container"
file: "directives/ng-template-ng-container.md"
source_days: [14]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# ng-template, ngTemplateOutlet, and ng-container

## `ng-template`

In [structural directives](../directives/structural-directives.md), we used `ng-template` with `*ngIf` and an `else` branch — defining a template reference with `#templateReferenceName` to render alternate content.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngIf="user.age >= 13; else noPG13">You can watch PG-13 content</div>
<ng-template #noPG13>
  <div>You cannot watch PG-13 content</div>
</ng-template>
```

From this example:

- HTML wrapped in `ng-template` is **not rendered immediately**. It renders only in specific cases — for example, when `*ngIf` uses it as an `else` template, or when you render it through `ngTemplateOutlet`.
- A template is a reusable fragment. Combining multiple templates can build a complete UI.

In short, `ng-template` is an Angular element for storing HTML that is never displayed at its definition site — only when explicitly rendered.

### When should you use `ng-template`?

Common cases:

1. **With structural directives** such as `*ngIf`
2. **Repeated UI fragments** inside one component that are too small to extract into a separate component
3. **Passing templates into other components** to override default markup

#### Repeating UI without copy-paste

Suppose a component has a `counter` variable and repeats the same badge UI in several places:

```html
<div class="card">
  <div class="card-header">
    You have selected
    <span class="badge badge-primary">{{ counter }}</span> items.
  </div>
  <div class="card-body">
    There are <span class="badge badge-primary">{{ counter }}</span> items was
    selected.
  </div>
  <div class="card-footer">
    You have selected
    <span class="badge badge-primary">{{ counter }}</span> items.
  </div>
</div>
```

Refactor with `ng-template` and `ngTemplateOutlet`:

```html
<div class="card">
  <div class="card-header">
    You have selected
    <ng-container [ngTemplateOutlet]="counterTmpl"></ng-container>.
  </div>
  <div class="card-body">
    There are <ng-container [ngTemplateOutlet]="counterTmpl"></ng-container> was
    selected.
  </div>
  <div class="card-footer">
    You have selected
    <ng-container [ngTemplateOutlet]="counterTmpl"></ng-container>.
  </div>
</div>

<ng-template #counterTmpl>
  <span class="badge badge-primary">{{ counter }}</span> items
</ng-template>
```

Benefits:

- Change the counter UI in one place instead of three — fewer typos and missed find-and-replace targets.
- The template fits in a single line at each call site — lighter than extracting a whole component.

#### Overriding a component's default template

A `tab-container` component might ship with a default tab header:

```ts
@Component({
  selector: 'tab-container',
  template: `
    <ng-template #defaultTabButtonsTmpl>
      <div class="default-tab-buttons">...</div>
    </ng-template>
    <ng-container
      *ngTemplateOutlet="headerTemplate || defaultTabButtons"
    ></ng-container>
    ... rest of tab container component ...
  `,
})
export class TabContainerComponent {
  @Input() headerTemplate: TemplateRef<any>; // Custom template provided by parent
}
```

The parent can pass a custom header:

```ts
@Component({
  selector: 'app-root',
  template: `
    <ng-template #customTabButtons>
      <div class="custom-class">
        <button class="tab-button" (click)="login()">
          {{loginText}}
        </button>
        <button class="tab-button" (click)="signUp()">
          {{signUpText}}
        </button>
      </div>
    </ng-template>
    <tab-container [headerTemplate]="customTabButtons"></tab-container>
  `
})
```

## `ngTemplateOutlet`

`ngTemplateOutlet` renders a template created by `ng-template`:

- `*ngTemplateOutlet="templateRef"` (the `*` matters for structural directive form)
- `[ngTemplateOutlet]="templateRef"`

Like `@Input()` on components, templates accept context data via `ngTemplateOutletContext`.

Reuse button markup with different labels and optional icons:

```html
<button class="btn btn-primary">Click here</button>

<button class="btn btn-danger">
  <i class="fa fa-remove"></i>
  Delete
</button>
```

Refactored:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ng-template
  #buttonTmpl
  let-label="label"
  let-className="className"
  let-icon="icon"
>
  <button [ngClass]="['btn', className ? className : '']">
    <i *ngIf="icon" class="fa {{icon}}"></i>
    {{ label }}
  </button>
</ng-template>

<ng-container
  [ngTemplateOutlet]="buttonTmpl"
  [ngTemplateOutletContext]="{ label: 'Click here', className: 'btn-primary', icon: null }"
>
</ng-container>

<ng-container
  [ngTemplateOutlet]="buttonTmpl"
  [ngTemplateOutletContext]="{ label: 'Remove', className: 'btn-danger', icon: 'fa-remove' }"
>
</ng-container>
```

Notes:

- In `ng-template`, `let-name="name"` binds a template variable: the left `name` is used inside the template; the right `name` is the key in `ngTemplateOutletContext`. They can differ.
- `let-name` without `="name"` uses the `$implicit` context key:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ng-template #buttonTmpl let-label let-className="className" let-icon="icon">
  <button [ngClass]="['btn', className ? className : '']">
    <i *ngIf="icon" class="fa {{icon}}"></i>
    {{ label }}
  </button>
</ng-template>

<ng-container
  [ngTemplateOutlet]="buttonTmpl"
  [ngTemplateOutletContext]="{ $implicit: 'Remove', className: 'btn-danger', icon: 'fa-remove' }"
>
</ng-container>
```

- Template variables inside `ng-template` are not type-safe. If you pass a `user` object with `firstName`, `lastName`, and `age`, using `user.fullName` won't be caught by the compiler or Angular language service.

## `ng-container`

`ng-container` is a grouping element that doesn't add an extra DOM node — useful when a wrapper would break CSS selectors like `parent > child`.

You could write:

```html
<div
  [ngTemplateOutlet]="buttonTmpl"
  [ngTemplateOutletContext]="{ label: 'Click here', class: 'btn-primary', icon: null }"
></div>
```

But that renders an extra wrapper:

```html
<div>
  <button class="btn btn-primary">Click here</button>
</div>
```

`ng-container` avoids the extra element.

## Summary

We've introduced `ng-template` for storing reusable markup, `ngTemplateOutlet` for rendering it (with context), and `ng-container` for grouping without extra DOM nodes.

Further reading:

- https://alligator.io/angular/reusable-components-ngtemplateoutlet/
- https://angular.io/guide/structural-directives#the-ng-template
- [Angular render recursive view using *ngFor and ng-template](https://trungk18.com/experience/angular-recursive-view-render/)
- https://blog.angular-university.io/angular-ng-template-ng-container-ngtemplateoutlet/

## Youtube Video

[![ng-template and ngTemplateOutlet](https://img.youtube.com/vi/3JM8pDR-MaU/0.jpg)](https://youtu.be/3JM8pDR-MaU) <!-- TODO: asset -->

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

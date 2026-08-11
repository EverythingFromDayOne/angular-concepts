---
roadmap_node: "templates-architecture"
title: "Template Variables, ViewChild, and ContentChild"
file: "components/templates/templates-architecture.md"
source_days: [10, 17]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Template Variables, ViewChild, and ContentChild

What if you need a reference to an element, component, or directive in a template and want to interact with it directly? Template reference variables answer that question — and when you need access from the component class, `ViewChild`, `ViewChildren`, `ContentChild`, and `ContentChildren` take over.

## Parent interacts with child via a local template variable

Suppose `AppComponent` embeds a toggle:

```html
<app-toggle></app-toggle>
```

Instead of clicking the toggle itself, we want a parent button to call `toggle()`:

```html
<button (click)="doSomething">Toggle</button>

<br />

<app-toggle></app-toggle>
```

Use a template reference variable:

```html
<button (click)="toggleComp.toggle()">Toggle</button>

<br />

<app-toggle #toggleComp></app-toggle>
```

The `#varName` syntax creates a template variable. You can define multiple variables in one template.

We used the same pattern with `*ngIf` / `else` — referencing an `ng-template` instance:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngIf="user.age >= 13; else noPG13">You can watch PG-13 content</div>
<ng-template #noPG13>
  <div>You cannot watch PG-13 content</div>
</ng-template>
```

See [structural directives](../../directives/structural-directives.md) for more on `*ngIf`.

### What type does a template variable hold?

By default, `#varName` on an `HTMLElement` gives you that element. On a component, you get the component instance.

When multiple directives sit on one element, request a specific type with `#varName="exportAsOfDirectiveOrComponent"`. With `FormsModule` and `ngModel`:

```html
<form #nameForm="ngForm">
  <input
    type="text"
    class="form-control"
    required
    [(ngModel)]="model.name"
    name="name"
    #name="ngModel"
  />
  <button>Submit</button>
</form>
```

- `nameForm` — instance of the directive with `exportAs: 'ngForm'`
- `name` — instance of the directive with `exportAs: 'ngModel'`

Without the explicit `exportAs`, these variables would resolve to plain `HTMLElement` references.

## Querying from the component class with `ViewChild`

Template variables work in templates, but application logic usually belongs in the class (or a service). Query a template variable from the component:

```html
<button (click)="toggleInside()">Toggle inside class</button>
<br />
<br />

<app-toggle #toggleComp></app-toggle>
```

```ts
export class AppComponent {
  @ViewChild('toggleComp') toggleComp: ToggleComponent;
  toggleInside() {
    this.toggleComp.toggle();
  }
}
```

For an `HTMLElement`, `ViewChild` returns an `ElementRef`, not the raw element:

```html
<div #chartContainer></div>
```

```ts
export class AppComponent {
  @ViewChild('chartContainer') container: ElementRef<HTMLDivElement>;
}
```

### `ViewChild` options

Full API: https://angular.io/api/core/ViewChild

```ts
// View queries are set before the ngAfterViewInit callback is called.
ViewChild(selector: string | Function | Type<any>, opts?: {
  read?: any;
  static?: boolean;
})
```

Selectors can be:

- Any class with `@Component` or `@Directive`
- A template reference variable string (e.g. `@ViewChild('cmp')` for `<my-component #cmp>`)
- Any provider in the child component tree
- A string token provider
- A `TemplateRef` (e.g. `@ViewChild(TemplateRef)` on `<ng-template>`)

`opts.read` lets you request a specific token — directive, component, service, etc.:

```html
<form #nameForm="ngForm">
  <input
    type="text"
    class="form-control"
    required
    [(ngModel)]="model.name"
    name="name"
    #name="ngModel"
  />
  <button>Submit</button>
</form>
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
export class NameFormComponent implements OnInit {
  model = {
    name: 'Tiep Phan',
  };

  @ViewChild('nameForm', {
    read: ElementRef,
    static: true,
  })
  form: ElementRef<HTMLFormElement>;
  constructor() {}

  ngOnInit() {
    console.log(this.form);
  }
}
```

Without `read`, you get an `NgForm` instance. With `read: ElementRef`, you get the form element instead.

`opts.static`: when the queried element is not inside `*ngIf` or another structural directive, set `static: true`. Angular resolves the query before change detection, so you can access it in `ngOnInit`. With `static: false` (the default), resolution happens after change detection — use `ngAfterViewInit` instead.

## Querying multiple elements with `ViewChildren`

`ViewChildren` returns a `QueryList` before `ngAfterViewInit` runs. `QueryList` exposes properties and methods, including a `changes` observable:

```html
<app-toggle></app-toggle>
<br />
<app-toggle></app-toggle>
```

```ts
@ViewChildren(ToggleComponent) toggleList: QueryList<ToggleComponent>;

ngAfterViewInit() {
  console.log(this.toggleList);
}
```

## View vs content

Before `ContentChild` and `ContentChildren`, let's clarify the distinction:

- **View** — the template the component directly owns (everything in `template` / `templateUrl` except what's projected through `ng-content`). A component's view is a black box to outside components.
- **Content** — template projected between a component's opening and closing tags (also called light DOM). The component does not directly manage it.

`ViewChild` / `ViewChildren` query the **view**. `ContentChild` / `ContentChildren` query **projected content**.

## Querying projected content with `ContentChild`

With [content projection](content-projection.md), child components inside projected markup are created in the parent's context before being passed down. Consider a tab group with counters:

```html
<app-bs-tab-group>
  <app-tab-panel title="Tab 1">
    content tab 1
    <app-counter></app-counter>
  </app-tab-panel>
  <app-tab-panel title="Tab 2">
    content tab 2
    <app-counter></app-counter>
  </app-tab-panel>
  <app-tab-panel title="Tab 3">
    content tab 3
    <app-counter></app-counter>
  </app-tab-panel>
</app-bs-tab-group>
<app-counter></app-counter>
```

You might expect one counter instance, but four are created — only one is visible. For complex tab content, we want lazy initialization: `TabPanelComponent` should receive content but render it only when needed.

Wrap content in `ng-template` and query it with `ContentChild`. First, a directive to mark the template:

```ts
import { Directive } from '@angular/core';

@Directive({
  selector: 'ng-template[tabPanelContent]',
})
export class TabPanelContentDirective {
  constructor() {}
}
```

Query the directive from `TabPanelComponent`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
export class TabPanelComponent implements OnInit, OnDestroy {
  @Input() title: string;
  @ViewChild(TemplateRef, { static: true }) panelBody: TemplateRef<unknown>;

  @ContentChild(TabPanelContentDirective, { static: true })
  explicitBody: TemplateRef<unknown>;

  constructor(private tabGroup: TabGroupComponent) {}

  ngOnInit() {
    this.tabGroup.addTabPanel(this);
  }
  ngOnDestroy() {
    this.tabGroup.removeTabPanel(this);
  }
}
```

Usage:

```html
<app-tab-panel title="Tab 1">
  <ng-template tabPanelContent>
    content tab 1
    <app-counter></app-counter>
  </ng-template>
</app-tab-panel>
```

`ContentChild` returns a `TabPanelContentDirective` instance. To get the `TemplateRef`, use `read`:

```ts
@ContentChild(TabPanelContentDirective, { static: true, read: TemplateRef })
explicitBody: TemplateRef<unknown>;
```

Support both implicit and explicit body templates:

```ts
export class TabPanelComponent implements OnInit, OnDestroy {
  @Input() title: string;
  @ViewChild(TemplateRef, { static: true }) implicitBody: TemplateRef<unknown>;

  @ContentChild(TabPanelContentDirective, { static: true, read: TemplateRef })
  explicitBody: TemplateRef<unknown>;

  get panelBody(): TemplateRef<unknown> {
    return this.explicitBody || this.implicitBody;
  }
}
```

Now only two counter instances are created (one per visible tab panel plus the standalone counter).

> Note: with lazy initialization like this, each time you activate a tab, the `TemplateRef` is recreated.

## Querying multiple projected items with `ContentChildren`

Instead of dependency injection to register tab panels, `ContentChildren` queries all projected `TabPanelComponent` instances:

```ts
export class TabGroupComponent implements OnInit {
  @Input() tabActiveIndex = 0;
  @Output() tabActiveChange = new EventEmitter<number>();

  @ContentChildren(TabPanelComponent)
  tabPanelList: QueryList<TabPanelComponent>;

  constructor() {}

  ngOnInit() {}

  selectItem(idx: number) {
    this.tabActiveIndex = idx;
    this.tabActiveChange.emit(idx);
  }
}
```

> Note: `ContentChildren` does not retrieve elements or directives in other components' templates — a component's template is always a black box to its ancestors.

## Listening to `QueryList` changes

`ContentChildren` is initialized before `ngAfterContentInit`. Listen to `changes` to react when projected children are added or removed:

```ts
export class TabGroupComponent implements OnInit, AfterContentInit {
  @Input() tabActiveIndex = 0;
  @Output() tabActiveChange = new EventEmitter<number>();

  @ContentChildren(TabPanelComponent)
  tabPanelList: QueryList<TabPanelComponent>;

  constructor() {}

  ngOnInit() {}

  ngAfterContentInit() {
    this.tabPanelList.changes.subscribe(() => {
      if (this.tabPanelList.length <= this.tabActiveIndex) {
        this.selectItem(0);
      }
    });
  }

  selectItem(idx: number) {
    this.tabActiveIndex = idx;
    this.tabActiveChange.emit(idx);
  }
}
```

## Summary

We've covered template reference variables, `ViewChild` / `ViewChildren` for the component view, the view-vs-content distinction, and `ContentChild` / `ContentChildren` for projected content — including lazy tab panel rendering and listening to `QueryList.changes`. We also touched `ngAfterViewInit` and `ngAfterContentInit`.

Further reading:

- https://angular.io/api/core/ViewChild
- https://angular.io/api/core/ViewChildren
- https://angular.io/api/core/ContentChild
- https://angular.io/api/core/ContentChildren
- https://angular.io/api/forms/NgModel
- [Template variables in Angular](https://www.tiepphan.com/thu-nghiem-voi-angular-template-variable-trong-angular/) (Vietnamese)
- [Dynamic component rendering in 5 minutes](https://www.tiepphan.com/angular-trong-5-phut-dynamic-component-rendering/) (Vietnamese)
- [Content projection in Angular](https://www.tiepphan.com/thu-nghiem-voi-angular-content-projection-trong-angular/) (Vietnamese)
- [Content projection and lifecycle hands-on](https://www.tiepphan.com/thu-nghiem-voi-angular-thuc-hanh-content-projection-va-lifecycle-angular/) (Vietnamese)
- [QueryList changes event](https://www.tiepphan.com/thu-nghiem-voi-angular-querylist-changes-event-trong-angular/) (Vietnamese)
- https://netbasal.com/understanding-viewchildren-contentchildren-and-querylist-in-angular-896b0c689f6e

## Youtube Video

[![Template Variables and ViewChild](https://img.youtube.com/vi/Wd_644YBQUM/0.jpg)](https://youtu.be/Wd_644YBQUM) <!-- TODO: asset -->

[![ContentChild and ContentChildren](https://img.youtube.com/vi/m3ZgeVGLZag/0.jpg)](https://youtu.be/m3ZgeVGLZag) <!-- TODO: asset -->

## Code sample

- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-10?file=src/app/app.component.ts
- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-17?file=src%2Fapp%2Fapp.component.html
- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-17-contentchildren?file=src%2Fapp%2Ftab-group%2Ftab-group.component.ts

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

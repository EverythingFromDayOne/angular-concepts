---
roadmap_node: "component-interactions-input-output"
title: "Component Interactions: Input, Output, and Two-Way Binding"
file: "components/component-interactions.md"
source_days: [7, 8, 9, 44]
original_authors: ["Tiep Phan", "Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Component Interactions: Input, Output, and Two-Way Binding

In real apps, some components work without any inputs, but many are designed for reuse — their display and behavior depend on properties passed in from a parent. Imagine a progress bar for file uploads or video playback: one reusable component, configured differently at each call site.

This article covers passing data **into** child components (`@Input`), emitting events **out** to parents (`@Output`), building **custom two-way binding**, and a lesser-known pattern: using an `Observable` directly as an `@Output`.

## Passing data from parent to child with `@Input`

First, let's generate a `progress-bar` component:

```
ng g c progress-bar
```

Or explicitly:

```
ng generate component progress-bar
```

### The `@Input` decorator

To accept a `progress` value from a parent, declare a property and add the `@Input` decorator:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
export class ProgressBarComponent implements OnInit {
  @Input() progress = 0;
  constructor() {}
  ngOnInit() {}
}
```

Angular now knows this component accepts a `progress` property with a default of `0`. We can add more inputs for colors:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
export class ProgressBarComponent implements OnInit {
  @Input() backgroundColor: string;
  @Input() progressColor: string;
  @Input() progress = 0;
  constructor() {}
  ngOnInit() {}
}
```

`@Input` is a property decorator — it attaches metadata to the property immediately following it. Without `@Input`, Angular won't bind values from parent templates; the property stays a plain class field.

Use property binding in the parent template:

```html
<app-progress-bar
  [progress]="15"
  [backgroundColor]="'#9e9e9e'"
  [progressColor]="'#2e8b57'"
>
</app-progress-bar>
```

Full component example:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
import { Component, OnInit, Input } from '@angular/core';

@Component({
  selector: 'app-progress-bar',
  template: `
    <div
      class="progress-bar-container"
      [style.backgroundColor]="backgroundColor"
    >
      <div
        class="progress"
        [style]="{
          backgroundColor: progressColor,
          width: progress + '%'
        }"
      ></div>
    </div>
  `,
  styles: [
    `
      .progress-bar-container,
      .progress {
        height: 20px;
      }

      .progress-bar-container {
        width: 100%;
      }
    `,
  ],
})
export class ProgressBarComponent implements OnInit {
  @Input() backgroundColor: string;
  @Input() progressColor: string;
  @Input() progress = 0;
  constructor() {}
  ngOnInit() {}
}
```

### `ngOnInit` vs `constructor`

Angular components have a lifecycle. The `constructor` runs once when an instance is created. `ngOnInit` runs after the constructor and **after** inputs have been bound.

If a parent binds a property in its template, the child won't receive that value in its constructor — but it will in `ngOnInit`. Angular recommends keeping constructors minimal and doing setup in `ngOnInit`.

### Reacting to input changes

What if you need to validate inputs (for example, when a parent passes `any`)? `ngOnInit` handles the first value, but not subsequent changes. Use `ngOnChanges`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
export class ProgressBarComponent implements OnInit, OnChanges {
  @Input() backgroundColor: string;
  @Input() progressColor: string;
  @Input() progress = 0;

  constructor() {}

  ngOnChanges(changes: SimpleChanges) {
    if ('progress' in changes) {
      if (typeof changes['progress'].currentValue !== 'number') {
        const progress = Number(changes['progress'].currentValue);
        if (Number.isNaN(progress)) {
          this.progress = 0;
        } else {
          this.progress = progress;
        }
      }
    }
  }

  ngOnInit() {}
}
```

Alternatively, use a getter/setter:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
export class ProgressBarComponent implements OnInit {
  @Input() backgroundColor: string;
  @Input() progressColor: string;
  private $progress = 0;
  @Input()
  get progress(): number {
    return this.$progress;
  }
  set progress(value: number) {
    if (typeof value !== 'number') {
      const progress = Number(value);
      if (Number.isNaN(progress)) {
        this.$progress = 0;
      } else {
        this.$progress = progress;
      }
    } else {
      this.$progress = value;
    }
  }

  constructor() {}

  ngOnInit() {}
}
```

## Emitting events from child to parent with `@Output`

In HTML, you listen for events like `click` on a button. Custom components can emit their own events using `EventEmitter` and `@Output`.

Generate two components:

```
ng g c author-list
ng g c author-detail
```

`AuthorListComponent` holds a list of authors and passes each one to `AuthorDetailComponent`:

```typescript
export interface Author {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  gender: string;
  ipAddress: string;
}
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
import { Component, OnInit } from '@angular/core';
import { authors } from '../authors';
@Component({
  selector: 'app-author-list',
  template: `<app-author-detail
    *ngFor="let author of authors"
    [author]="author"
  ></app-author-detail>`,
  styles: [``],
})
export class AuthorListComponent implements OnInit {
  authors = authors;
  constructor() {}
  ngOnInit() {}
}
```

`AuthorDetailComponent` receives an author via `@Input`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
import { Component, OnInit, Input } from '@angular/core';
import { Author } from '../authors';
@Component({
  selector: 'app-author-detail',
  template: `
    <div *ngIf="author">
      <strong>{{ author.firstName }} {{ author.lastName }}</strong>
      <button (click)="handleDelete()">x</button>
    </div>
  `,
  styles: [``],
})
export class AuthorDetailComponent implements OnInit {
  @Input() author: Author;
  constructor() {}
  ngOnInit() {}
  handleDelete() {}
}
```

The child shouldn't delete data it doesn't own. Instead, emit an event so the parent can handle removal:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
export class AuthorDetailComponent implements OnInit {
  @Input() author: Author;
  @Output() deleteAuthor = new EventEmitter<Author>();
  constructor() {}
  ngOnInit() {}
  handleDelete() {
    this.deleteAuthor.emit(this.author);
  }
}
```

The parent listens and filters the list:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
@Component({
  selector: 'app-author-list',
  template: `<app-author-detail
    *ngFor="let author of authors"
    [author]="author"
    (deleteAuthor)="handleDelete($event)"
  >
  </app-author-detail>`,
  styles: [``],
})
export class AuthorListComponent implements OnInit {
  authors = authors;
  constructor() {}
  ngOnInit() {}
  handleDelete(author: Author) {
    this.authors = this.authors.filter((item) => item.id !== author.id);
  }
}
```

## Custom two-way binding

We covered two-way binding in [data binding](../templates/data-binding.md). Custom two-way binding pairs an `@Input` with an `@Output` whose name is the input name plus `Change` — the same pattern as `ngModel` and `ngModelChange`.

### `ngModel` recap

`ngModel` comes from `FormsModule`. Import it in the module that declares your component:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';

import { AppComponent } from './app.component';

@NgModule({
  imports: [BrowserModule, FormsModule],
  declarations: [AppComponent],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

Then use `[(ngModel)]` in the template:

**app.component.html**

```html
<p>Your name: {{ name }}</p>

<input type="text" [(ngModel)]="name" />
```

**app.component.ts**

```ts
@Component({
  selector: 'my-app',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  name = 'Tiep Phan';
}
```

`[(ngModel)]` is shorthand for:

```html
<input type="text" [ngModel]="name" (ngModelChange)="name = $event" />
```

For custom two-way binding, create `@Input() value` and `@Output() valueChange`.

### Toggle component with two-way binding

Generate a toggle component:

```sh
ng g c toggle
```

**toggle.component.ts**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-toggle',
  templateUrl: './toggle.component.html',
  styleUrls: ['./toggle.component.css'],
})
export class ToggleComponent implements OnInit {
  @Input() checked = false;
  @Output() checkedChange = new EventEmitter<boolean>();

  constructor() {}

  ngOnInit() {}

  toggle() {
    this.checked = !this.checked;
    this.checkedChange.emit(this.checked);
  }
}
```

**toggle.component.html**

```html
<div
  class="toggle-wrapper"
  [class.checked]="checked"
  tabindex="0"
  (click)="toggle()"
>
  <div class="toggle"></div>
</div>
```

Use it like `ngModel`:

```html
<app-toggle [(checked)]="checked"></app-toggle>
```

![Toggle](assets/100doc-day9.gif) <!-- TODO: asset -->

## Observable as `@Output`

Here's a pattern many Angular developers miss because it's not prominently documented: you can assign an `Observable` directly to an `@Output` instead of manually subscribing and re-emitting through `EventEmitter`.

### Before

```ts
@Output() someEvent = new EventEmitter();
this.someSource$.pipe(
   // additional logic/transformation
).subscribe(data => this.someEvent.emit(data));
```

### After

```ts
@Output() someEvent = this.someSource$.pipe(
  /* additional logic transformation */
);
```

The use case: emit values to a parent when `someSource$` produces data. Why does the "After" version work?

Two concepts explain it:

**Event binding syntax `()`**

Event binding uses parentheses and an event name: `<child (someEvent)="invokeSomeEvent()"></child>`. The Angular compiler parses templates into an AST and knows what type of binding is in play. In the [output interpreter source](https://github.com/angular/angular/blob/6a9e3284329baf1bb6b621a8840ace629eb4b16e/packages/compiler/src/output/output_interpreter.ts#L166), if the bound event is a `SubscribeObservable`, the compiler subscribes to that source automatically.

![Observable Output](assets/day44-angularoutput.jpeg) <!-- TODO: asset -->

So event binding `()` automatically subscribes when the output is an `Observable` or `Subject`.

**`EventEmitter` class**

`EventEmitter` is a subclass of `Subject`. Since `Subject` is both an `Observable` and an `Observer`, `@Output` works through the compiler's auto-subscribe behavior described above.

### Use cases

- Interval output
- State selectors (NgRx)
- Any stream you can think of

## Summary

We've covered `@Input` for parent-to-child data, `@Output` and `EventEmitter` for child-to-parent events, custom two-way binding with the `property` + `propertyChange` convention, and using an `Observable` directly as an output.

Further reading:

- https://angular.io/guide/component-interaction
- https://angular.io/guide/lifecycle-hooks
- https://angular.io/api/forms/NgModel
- [Passing data to components with Input](https://www.tiepphan.com/thu-nghiem-voi-angular-2-truyen-du-lieu-cho-component-voi-input/) (Vietnamese)
- [Component events with EventEmitter and Output](https://www.tiepphan.com/thu-nghiem-voi-angular-2-component-event-voi-eventemitter-output/) (Vietnamese)
- [Custom two-way data binding](https://www.tiepphan.com/thu-nghiem-voi-angular-2-two-way-binding-custom-two-way-data-binding/) (Vietnamese)

## Youtube Video

[![Input Binding](https://img.youtube.com/vi/uTd2W4NQkgs/0.jpg)](https://youtu.be/uTd2W4NQkgs) <!-- TODO: asset -->

[![Output Events](https://img.youtube.com/vi/XFN75RZzMJY/0.jpg)](https://youtu.be/XFN75RZzMJY) <!-- TODO: asset -->

[![Two-Way Binding](https://img.youtube.com/vi/U8UCOKInmu8/0.jpg)](https://youtu.be/U8UCOKInmu8) <!-- TODO: asset -->

## Code sample

- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-7
- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-8?file=src%2Fapp%2Fauthor-detail%2Fauthor-detail.component.ts
- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-9?file=src%2Fapp%2Ftoggle%2Ftoggle.component.ts

## Author

Tiep Phan — https://github.com/tieppt

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

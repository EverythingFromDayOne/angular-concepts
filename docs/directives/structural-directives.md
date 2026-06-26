---
roadmap_node: "structural-directives"
title: "Structural Directives"
file: "directives/structural-directives.md"
source_days: [4, 5]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Structural Directives

In programming, we often need to make decisions based on conditions. Suppose we're building a video streaming app where some PG-13 titles require viewers to be at least 13 years old. How do we tell users whether they're eligible to watch? Angular's `*ngIf` and `*ngFor` structural directives are built for exactly this kind of work.

In Angular, **structural directives** add, remove, or change the DOM structure in a component's view.

## Conditional rendering with `*ngIf`

To show part of a template only when a condition is true, attach a special property to an element using the asterisk (`*`) syntax: `*ngIf="expression"`.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
@Component({
  selector: 'app-hello',
  template: `
    <h2>Hello there!</h2>
    <h3>Your name: {{ user.name }}</h3>
    <p>Your age: {{ user.age }}</p>
    <div *ngIf="user.age >= 13">You can watch PG-13 content</div>
  `,
})
export class HelloComponent {
  user = {
    name: 'Tiep Phan',
    age: 30,
  };
}
```

If the expression is truthy, the view is shown; if it's falsy, it isn't. Built-in structural directives make component templates very flexible.

### `if` / `else`

You might think of negating the `if` condition for the `else` branch — and that works:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngIf="user.age >= 13">You can watch PG-13 content</div>
<div *ngIf="user.age < 13">You cannot watch PG-13 content</div>
```

A cleaner approach uses `ng-template`. The `ng-template` tag stores a template between its opening and closing tags. Whatever is defined inside is not rendered to the view immediately, but we can use that template to render content programmatically or through structural directives:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngIf="user.age >= 13; else noPG13">You can watch PG-13 content</div>
<ng-template #noPG13>
  <div>You cannot watch PG-13 content</div>
</ng-template>
```

Angular also supports `ngIf-then-else` for more complex branching — see the reference links below.

### How the `*` syntax works

The `*` prefix is syntactic sugar. Under the hood, Angular expands it to property binding on `ng-template`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ng-template [ngIf]="user.age >= 13" [ngIfElse]="noPG13">
  <div>You can watch PG-13 content</div>
</ng-template>
```

## Looping with `*ngFor`

What if you need to render a list of items in a template? When your data is an array, `NgForOf` (often called `NgFor`) lets you loop in the template — similar to `for (let item of items)` in TypeScript.

Suppose we have a list of book authors in a bookstore or library app:

```typescript
authors = [
  {
    id: 1,
    firstName: 'Flora',
    lastName: 'Twell',
    email: 'ftwell0@phoca.cz',
    gender: 'Female',
    ipAddress: '99.180.237.33',
  },
  {
    id: 2,
    firstName: 'Priscella',
    lastName: 'Signe',
    email: 'psigne1@berkeley.edu',
    gender: 'Female',
    ipAddress: '183.243.228.65',
  },
  // more data
];
```

Here's how to use `NgForOf`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngFor="let author of authors">
  {{ author.id }} - {{ author.firstName }} {{ author.lastName }}
</div>
```

The syntax mirrors `for (let author of authors)` in TypeScript.

### Local variables in an `*ngFor` template

Each iteration exposes local variables you can use in the template:

| Term | Description |
| --- | --- |
| `$implicit: T` | The value of the current list item |
| `index: number` | Index of the current iteration |
| `count: number` | Total number of items in the list |
| `first: boolean` | `true` if this is the first item |
| `last: boolean` | `true` if this is the last item |
| `even: boolean` | `true` if the index is even |
| `odd: boolean` | `true` if the index is odd |

`$implicit` is bound to the variable you declare in `let something of xxx` — so `something` equals `$implicit`. For the other variables, use this syntax:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngFor="let author of authors; index as idx; count as total">
  ({{ idx }})/({{ total }}): {{ author.id }} - {{ author.firstName }}
  {{ author.lastName }}
</div>
```

Here `idx` maps to `index` and `total` maps to `count`. The same pattern applies to the remaining variables.

### `*ngFor` and `ng-template`

The asterisk syntax expands to `ng-template` with property binding:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ng-template
  ngFor
  [ngForOf]="authors"
  let-author
  let-idx="index"
  let-total="count"
>
  <div>
    ({{ idx }})/({{ total }}): {{ author.id }} - {{ author.firstName }}
    {{ author.lastName }}
  </div>
</ng-template>
```

### Using multiple structural directives on one element

Sometimes you need to filter items inside a loop. Putting `*ngIf` and `*ngFor` on the same element does not work — you cannot place more than one structural directive on a single element.

Think of it like TypeScript:

```typescript
for (let item of list) {
  if (somethingGood) {
    // more code
  }
}
```

You can't put `for` and `if` on the same line. The fix is to nest them with a wrapper:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngFor="let item of list">
  <div *ngIf="somethingGood">More code</div>
</div>
```

If you don't want an extra `div`, convert `*ngIf` to `ng-template` form or use `ng-container`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngFor="let item of list">
  <ng-container *ngIf="somethingGood">More code</ng-container>
</div>
<div *ngFor="let item of list">
  <ng-template [ngIf]="somethingGood">More code</ng-template>
</div>
```

## Summary

We've covered `*ngIf` (including `else` with `ng-template`), `*ngFor` with local variables, and how to combine structural directives without putting two on the same element.

Further reading:

- https://angular.io/guide/structural-directives
- https://angular.io/api/common/NgIf
- https://angular.io/api/common/NgForOf
- [Experimenting with Angular built-in directives NgIf, NgFor, NgSwitchCase](https://www.tiepphan.com/thu-nghiem-voi-angular-2-built-in-directives-ngif-ngfor-ngswitchcase/) (Vietnamese)
- [Experimenting with Angular NgFor index, first, last, even, odd, trackBy](https://www.tiepphan.com/thu-nghiem-voi-angular-2-ngfor-index-first-last-even-odd-trackby/) (Vietnamese)
- https://www.youtube.com/watch?v=dXDC-4KGIGI

## Youtube Video

[![Structural Directives](https://img.youtube.com/vi/Yujs6hi-l4w/0.jpg)](https://youtu.be/Yujs6hi-l4w) <!-- TODO: asset -->

[![NgForOf](https://img.youtube.com/vi/q7CQPEPSkD0/0.jpg)](https://youtu.be/q7CQPEPSkD0) <!-- TODO: asset -->

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

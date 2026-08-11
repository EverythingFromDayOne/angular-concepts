---
roadmap_node: "pipes"
title: "Transform Data with Angular Pipes"
file: "pipes/pipes.md"
source_days: [18]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Transform Data with Angular Pipes

Most applications follow a simple flow:

1. Fetch data from a server — an API call, or a WebSocket for real-time updates.
2. Transform the data — for example, turn `2020-06-24T09:00:00.000Z` (ISO format) into something readable like `Jun 24, 2020`.
3. Display it in the UI.

Pipes handle step 2 — transforming data before it reaches the user.

## What is a pipe?

A pipe is a function that takes an **input** and returns a transformed **output**.

Servers often exchange dates as ISO strings like `"2020-06-24T09:00:00.000Z"` (June 24, 2020, 5:00 PM Singapore time). Users shouldn't see raw ISO strings. We transform them to formats like `Jun 24, 2020, 5:00:00 PM`.

In Angular you can:

1. Write a function that accepts a date and returns a formatted string.
2. Write a pipe that does the same.

Pipes are easier to reuse across many templates that display dates.

## Using pipes

Angular ships common pipes in `@angular/common`. You can also write custom pipes for project-specific needs.

A pipe accepts input and returns output. Suppose we have a `now` property:

```ts
export class PipeExampleComponent implements OnInit {
  now = '2020-06-24T09:00:00.000Z';
}
```

Display it with the built-in [DatePipe](https://angular.io/api/common/DatePipe):

```html
<div>{{ now | date }}</div>
// Jun 24, 2020
<div>{{ now | date:'medium'}}</div>
// Jun 24, 2020, 5:00:00 PM
```

Inside `{{ }}`, the pipe operator `|` separates the value from the pipe name:

```html
{{ interpolated_value | pipe_name }}
```

### Pipe parameters

Pass parameters after colons:

```html
{{ interpolated_value | pipe_name:parameter1:parameter2:...:parameterN }}
```

There's no limit on parameter count.

### Chaining pipes

Chain multiple pipes left to right — each pipe receives the previous pipe's output:

```html
{{ interpolated_value | pipe_name_1 | pipe_name_2 |... | pipe_name_n }}
```

Add `uppercase` after `date`:

```html
{{ now | date:'medium' | uppercase}} // JUN 24, 2020, 5:00:00 PM
```

> The author was in Singapore (UTC+8) when writing the original article, so times may show as 5 PM. Readers in UTC+7 may see 4 PM depending on locale settings.

## Built-in pipes

Import `CommonModule` from `@angular/common` to use these. Commonly used built-ins:

| Pipe | Description |
| --- | --- |
| [`DatePipe`](https://angular.io/api/common/DatePipe) | Formats a date |
| [`UpperCasePipe`](https://angular.io/api/common/UpperCasePipe) | Converts text to uppercase |
| [`LowerCasePipe`](https://angular.io/api/common/LowerCasePipe) | Converts text to lowercase |
| [`CurrencyPipe`](https://angular.io/api/common/CurrencyPipe) | Displays a currency value |
| [`DecimalPipe`](https://angular.io/api/common/DecimalPipe) | Displays a decimal number |
| [`PercentPipe`](https://angular.io/api/common/PercentPipe) | Displays a percentage |
| [`JsonPipe`](https://angular.io/api/common/JsonPipe) | Displays JSON |
| [`AsyncPipe`](https://angular.io/api/common/AsyncPipe) | Subscribes to an observable and unsubscribes when the view is destroyed |

See the [full list in CommonModule](https://angular.io/api/common/CommonModule#pipes).

## Writing a custom pipe

A typical CRUD app reuses the same form HTML for add and edit. When editing, the route includes an `itemId`; when adding, it doesn't. Without a pipe, every template repeats:

```html
{{ itemId ? "Edit" : "Add" }}
```

A typo (`Adđ` instead of `Add`, with Vietnamese input method enabled) motivated a small reusable pipe.

### Step 1: Implement `PipeTransform`

```ts
interface PipeTransform {
  transform(value: any, ...args: any[]): any;
}
```

Example implementation:

```ts
export class AppTitlePipe implements PipeTransform {
  transform(resourceId: string): string {
    return resourceId ? 'Edit' : 'Add';
  }
}
```

Truthy `resourceId` returns `Edit`; otherwise `Add`.

### Step 2: Add the `@Pipe` decorator

```ts
@Pipe({
  name: 'appTitle',
})
export class AppTitlePipe implements PipeTransform {
  transform(resourceId: string): string {
    return resourceId ? 'Edit' : 'Add';
  }
}
```

The `name` property is required — here, `appTitle`. Add `AppTitlePipe` to the module's `declarations` array where you use it.

```html
<h2 class="ibox-title">{{ userId | appTitle }} User</h2>
```

Naming conventions ([Angular Style Guide](https://angular.io/guide/styleguide#pipe-names)):

- Class: `UpperCamelCase` (e.g. `AppTitlePipe`)
- Pipe `name`: `camelCase` (e.g. `appTitle`) — no hyphens

### Custom pipe parameters

Some pages need `Set` / `Change` instead of `Add` / `Edit`:

```ts
transform(
  resourceId: string,
  addText: string = "Add",
  editText: string = "Edit"
): string {
  return resourceId ? editText : addText;
}
```

```html
{{ userId | appTitle:"Set":"Change"}}
```

- First `transform` argument: the piped value (`userId`)
- Additional template parameters map to arguments 2, 3, … in order

## Change detection and pipes

### Primitive types

With string `resourceId`, when the value changes, the pipe re-runs and the UI updates:

```ts
export class PipeExampleComponent implements OnInit {
  userIdChangeAfterFiveSeconds = '14324';
  time$: Observable<number> = timer(0, 1000).pipe(
    map((val) => 5 - (val + 1)),
    startWith(5),
    finalize(() => {
      this.userIdChangeAfterFiveSeconds = '';
    }),
    takeWhile((val) => val >= 0)
  );
}
```

```html
<p>
  Set userId to empty string after {{ timer | async }} seconds, notice the text
  "Edit" will be set to "Add"
</p>
<pre ngNonBindable>{{ userIdChangeAfterFiveSeconds | appTitle}}</pre>
<div>Form title: {{ userIdChangeAfterFiveSeconds | appTitle}} User</div>
```

![Pipe primitive example](assets/day-18-pipes-01.gif) <!-- TODO: asset -->

Primitives (string, boolean, number) trigger pipe updates straightforwardly.

### Reference types

Given a `users` array:

```ts
users: User[] = [
  { name: "Tiep Phan", age: 30 },
  { name: "Trung Vo", age: 28 },
  { name: "Chau Tran", age: 29 },
  { name: "Tuan Anh", age: 16 }
];
```

An `isAdult` pipe filters users over 18:

```ts
@Pipe({
  name: 'isAdult',
})
export class IsAdultPipe implements PipeTransform {
  transform(arr: User[]): User[] {
    return arr.filter((x) => x.age > 18);
  }
}
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div class="row">
  <div class="col-xs-6">
    <h4>Full user list</h4>
    <div *ngFor="let user of users">{{ user.name }}</div>
  </div>
  <div class="col-xs-6">
    <div class="ml-4">
      <h4>Adult user list</h4>
      <div *ngFor="let user of users | isAdult">{{ user.name }}</div>
    </div>
  </div>
</div>
```

![Pipe filter example](assets/day-18-pipes-02.png) <!-- TODO: asset -->

`Tuan Anh` (age 16) is correctly excluded from the adult list.

Add a user with a form — pushing into the array doesn't update the piped list:

![Pipe mutation issue](assets/day-18-pipes-03.gif) <!-- TODO: asset -->

```ts
addUser() {
  this.users.push(this.newUser);
  this.newUser = new User()
}
```

By default, pipes are **pure** — Angular runs them only on a pure change to the input: a new primitive value, or a new object reference for objects/arrays/functions.

Mutating an array in place doesn't change its reference, so the pipe doesn't re-execute.

Reference checks are much faster than deep equality checks, so prefer pure pipes when possible.

Two fixes:

### 1. Update the variable reference

```ts
addUserByUpdateReference() {
  this.users = [...this.users, this.newUser];
  this.newUser = new User();
}
```

![Pipe reference update](assets/day-18-pipes-04.gif) <!-- TODO: asset -->

### 2. Set `pure: false` (impure pipe)

```ts
@Pipe({
  name: 'isAdult',
  pure: false
})
```

> Use impure pipes carefully. Deep change detection on large collections hurts performance noticeably.

## Summary

We've covered what pipes are, built-in and custom pipes, parameters and chaining, and the difference between pure and impure pipes in change detection.

Further reading:

- https://angular.io/guide/pipes
- https://angular.io/api/common/CommonModule#pipes
- [Angular pipe singular/plural](https://trungk18.com/experience/angular-pipe-singular-plural/)

## Youtube Video

[![Angular Pipes](https://img.youtube.com/vi/4BJ2Vk67f6A/0.jpg)](https://youtu.be/4BJ2Vk67f6A) <!-- TODO: asset -->

## Code sample

https://stackblitz.com/edit/angular-100-days-of-code-day-18-pipes

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

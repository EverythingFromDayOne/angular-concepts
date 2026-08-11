---
roadmap_node: "typescript-prereqs"
title: "TypeScript Prerequisites for Angular"
file: "typescript-prereqs.md"
source_days: [11, 12]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# TypeScript Prerequisites for Angular

> **⚡ What changed since the original**
>
> This article was first written for the TypeScript 3.x era (2020), when Angular 9 required TS 3.8+. The **fundamentals** — static types, interfaces, classes, generics, union/intersection/conditional types, utility types — are unchanged. What's new since then:
>
> - **TypeScript baseline for Angular v22 is TS 5.5+** (much stricter type inference, better error messages, faster builds). Versions earlier than 5.5 are no longer supported by the Angular compiler.
> - **The `satisfies` operator (TS 4.9)** is now common in Angular configs and route declarations — a short introduction below.
> - **Signal-aware utility types** like `Awaited<T>` (TS 4.5+) and `NoInfer<T>` (TS 5.4+) are worth knowing for v22 patterns.
> - **The Angular-specific code example** updates `@Input() flexDirection: FlexDirection = 'row'` to the v22 signal input form with `input()` and the `host: {}` object instead of `@HostBinding`.
> - Reference links updated from `angular.io` to `angular.dev` (Angular's documentation moved domains in v17).
>
> No mechanism reflection — TypeScript primer content is largely timeless. The closing "Angular + TypeScript today" sidebar covers the relationship evolution briefly.
>
> **See also**: [Reactive Forms](forms/reactive-forms.md) (typed forms in v22) · [Signal Inputs](reactivity/signal-inputs.md) · [Dependency Injection](dependency-injection/dependency-injection.md)

---

Over the first ten days we explored Angular concepts and wrote code — all of it **TypeScript** (**TS**). Working with Angular means TS fundamentals matter. Today we'll cover the basics; advanced types come in the second half of this article.

> Solid **TS** foundations help when you tackle harder Angular topics like `Dependency Injection`.

## What is TypeScript?

**TS** is a **superset** of **JavaScript** (**JS**). Installing **TS** gives you the **TypeScript Compiler** (`tsc`) CLI. `tsc` compiles **TS** to **JS** for browsers or runtimes like **Node.js**.

![TypeScript Graphics](assets/typescript-graphics.png) <!-- TODO: asset -->

**TS** = **JS** plus extra features — mainly static types.

## TypeScript minus the extras

**TS** adds **static types**. **JS** is dynamically typed and very permissive:

```javascript
let john = 'John';
john = 123;
```

That's valid **JS** but error-prone at scale.

The same code in **TS**: `john` is inferred as `string` when assigned `"John"`. Assigning `123` is a **compilation-time error** because `number` isn't assignable to `string`.

> Below, _infer_ means TypeScript's automatic type inference.

![TS Compilation Error](assets/ts-compilation-error.png) <!-- TODO: asset -->

> That's a **compilation-time error**. Your editor surfaces it while you type thanks to the language service; `tsc` reports the same when you build.

### Default types

```typescript
let someString: string;
let someNumber: number;
let someBoolean: boolean;
let something: any; // assignable to any other type
let someStringArray: string[]; // likewise number[], boolean[], any[]
let someObject: object;
let someNull: null;
let someUndefined: undefined;
let someUnknown: unknown;
let someNever: never; // e.g. a function that always throws
let someTuple: [string, number];
let someVoidFunction: () => void;
let someFunction: () => string;
```

### Interface / Type

Define object shapes with `interface` or `type`:

```typescript
interface User {
  firstName: string;
  lastName: string;
  age: number;
  job?: string;
}

type User = {
  firstName: string;
  lastName: string;
  age: number;
  job?: string;
};

const john: User = {
  firstName: 'John',
  lastName: 'Doe',
  age: 20,
  job: 'Student',
};
const susan: User = {
  firstName: 'Sue',
  lastName: 'Smith',
  age: 40,
};
```

Think of an `interface` as a mold: `job?: string` is optional; other fields are required. Editors autocomplete `john.` with `firstName`, `lastName`, `age`, `job`.

> `interface` and `type` overlap in many cases — pick one style per project. See [interface vs type](https://medium.com/@martin_hotell/interface-vs-type-alias-in-typescript-2-7-2a8f1777af4c).

### Class

`class` syntax (ES2015+) is syntactic sugar over prototypal inheritance in **JS**. **TS** adds strong typing and access modifiers.

```typescript
class User {
  firstName: string;
  lastName: string;
  age: number;
  job?: string;

  constructor(firstName: string, lastName: string, age: number, job?: string) {
    this.firstName = firstName;
    this.lastName = lastName;
    this.age = age;
    this.job = job;
  }
}
```

Shorthand with access modifiers:

```typescript
class User {
  constructor(
    public firstName: string,
    public lastName: string,
    public age: number,
    public job?: string
  ) {}
}
```

> Class vs interface: [classes vs interfaces in TypeScript](https://ultimatecourses.com/blog/classes-vs-interfaces-in-typescript)

### Generics

```typescript
abstract class BaseService<T> {
  protected model: Model<T>;

  find(): T[] {
    return this.model.findAll();
  }

  findOne(id: number): T {
    return this.model.findById(id);
  }
}

class DogService extends BaseService<Dog> {
  constructor(dogModel: Model<Dog>) {
    super();
    this.model = dogModel;
  }
}

class CatService extends BaseService<Cat> {
  constructor(catModel: Model<Cat>) {
    super();
    this.model = catModel;
  }
}
```

`<T>` is a type parameter. `DogService` inherits `find()` / `findOne()` typed as `Dog` without rewriting them.

> **Why generics matter in v22 Angular:** the entire forms system uses them
> heavily — `FormGroup<TControls>`, `FormControl<T>`, `FormArray<TControl>`.
> Signal inputs use `InputSignal<T>`. The Router uses `Routes` arrays with
> typed `data` and `resolve` shapes. Comfort with generics pays off
> immediately. See [Reactive Forms](forms/reactive-forms.md) for the
> typed-forms deep dive.

## Why TypeScript?

### Pros

Explicit types, familiar OOP syntax (`abstract`, `class`, generics), and strong editor support help you build maintainable apps. **TS** consistently ranks among the most-loved languages in developer surveys, including the [Stack Overflow Developer Survey](https://survey.stackoverflow.co/).

### Cons

More boilerplate, stricter checks, third-party libraries need `.d.ts` typings, and the so-called [TypeScript tax](https://medium.com/javascript-scene/the-typescript-tax-132ff4cb175b).

### Trade-off

Angular chose **TS** for structure, maintainability, and scale — worth the trade-offs for most teams. As of v22, Angular **requires** TypeScript — there's no untyped path.

## Advanced types

> TypeScript's type system is deep; a few articles can't cover it all. Practice and read the handbook.

### Union type

**Either/or** types use `|`:

```typescript
function listen(port: unknown) {
  if (typeof port === 'string') {
    port = parseInt(port, 10);
  }
  server.listen(port);
}
```

#### `typeof`

```typescript
typeof 'string'; // string
typeof 123; // number
typeof true; // boolean
typeof {}; // object
typeof []; // object
typeof (() => {}); // function
typeof null; // object
typeof undefined; // undefined
```

`unknown` (TS 3.0+) is safer than `any` when the type isn't known yet. See [the unknown top type](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html#new-unknown-top-type).

Narrow with a union:

```typescript
function listen(port: string | number) {
  // do listen
}

listen('3000'); // ok
listen(3000); // ok
listen(true); // error: not string | number
listen(); // error: expected 1 argument
```

Return types can be unions too. Reuse with a type alias:

```typescript
type StringOrNumber = string | number;
```

### Intersection type

Combine types with `&` (**and**):

```typescript
function merge<T1, T2>(o1: T1, o2: T2): T1 & T2 {
  return { ...o1, ...o2 };
}
```

Common in UI libraries — shared `StyleProps` intersected with component-specific props (**type composition**).

### Conditional type

Since TS 2.8:

```typescript
T extends U ? X : Y;
```

If `T` is assignable to `U`, result is `X`; otherwise `Y`.

### The `satisfies` operator (TS 4.9, common in v22 Angular)

`satisfies` lets you check that a value conforms to a type **without widening or losing the literal types** of the value. It's the answer to a frequent source of friction with type annotations:

```typescript
// Without satisfies — the annotation widens the type
const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'about', component: AboutComponent },
];
// routes[0].path is string, not the literal '' — we've lost precision
```

```typescript
// With satisfies — type-checked, but literal types preserved
const routes = [
  { path: '', component: HomeComponent },
  { path: 'about', component: AboutComponent },
] satisfies Routes;
// routes[0].path is the literal '' — useful for downstream inference
```

You'll see `satisfies` in v22 Angular code most often around:

- **Route configs** — preserves literal path strings for typed link helpers
- **`ApplicationConfig`** — preserves the precise shape of `providers`
- **`@Component` metadata** in third-party libraries that derive types from it
- **Discriminated unions** where you want exhaustiveness checking without losing the variant tag

Rule of thumb: when you want a value to *match* a type but keep its full literal precision, reach for `satisfies` instead of `: T`.

### Type alias examples

Restrict `flexDirection` to valid CSS values. The Angular 9 version used the decorator-based `@Input()` and `@HostBinding()`; the v22 version uses signal inputs and the `host: {}` object.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: decorator input + @HostBinding
type FlexDirection = 'row' | 'column' | 'row-reverse' | 'column-reverse';

@Component({
  selector: 'flex-container',
  template: `<ng-content></ng-content>`
})
export class FlexComponent {
  @Input() flexDirection: FlexDirection = 'row';

  @HostBinding('style.display') display = 'flex';
  @HostBinding('style.flex-direction') get fd() { return this.flexDirection; }
}
```

```typescript
// ── v22 equivalent: signal input + host object ────────────────────────────
import { Component, input } from '@angular/core';

type FlexDirection = 'row' | 'column' | 'row-reverse' | 'column-reverse';

@Component({
  selector: 'flex-container',
  template: `<ng-content />`,
  host: {
    'style.display': 'flex',
    '[style.flex-direction]': 'flexDirection()',
  },
})
export class FlexComponent {
  readonly flexDirection = input<FlexDirection>('row');
}
```

The `FlexDirection` type alias is unchanged — that's pure TypeScript and timeless. What changed is how Angular consumes it: `input<FlexDirection>('row')` produces an `InputSignal<FlexDirection>`, read in templates and host bindings as `flexDirection()`. The `host: {}` object replaces both `@HostBinding` (for property/attribute/style/class binding) and `@HostListener` (for events).

Conditional dictionary helper:

```typescript
type ObjectDictionary<T> = { [key: string]: T };
type ArrayDictionary<T> = { [key: string]: T[] };
export type Dictionary<T> = T extends []
  ? ArrayDictionary<T[number]>
  : ObjectDictionary<T>;
```

### Built-in utility types (sample)

`Exclude`, `Extract`, `Readonly`, `Partial`, `Pick`, `Record`, `ReturnType`, `Omit`, and more — see the [TypeScript Utility Types reference](https://www.typescriptlang.org/docs/handbook/utility-types.html).

```typescript
type Person = {
  firstName: string;
  lastName: string;
  password: string;
};

type PersonWithNames = Pick<Person, 'firstName' | 'lastName'>;
type PersonWithoutPassword = Omit<Person, 'password'>;
```

Two newer utility types worth knowing for v22 Angular code:

- **`Awaited<T>` (TS 4.5+)** — unwraps nested promises. Useful for typing
  the result of `await someAsyncFunction()` chains, especially with
  resolvers and the async resource APIs (`resource()`, `httpResource()`).

  ```typescript
  type FetchUser = () => Promise<Promise<User>>;
  type UserResult = Awaited<ReturnType<FetchUser>>; // → User, not Promise<User>
  ```

- **`NoInfer<T>` (TS 5.4+)** — blocks TypeScript from inferring a type
  parameter from a particular position. Useful when you want the call
  site to *provide* a type rather than have it inferred from one argument
  but used to constrain another.

  ```typescript
  function withDefault<T>(value: T | undefined, defaultValue: NoInfer<T>): T {
    return value ?? defaultValue;
  }
  // T is inferred from `value`; `defaultValue` is checked against it
  // but cannot itself drive the inference.
  ```

## Angular + TypeScript today (a brief sidebar)

The Angular team has leaned harder into TypeScript over each major release. A few milestones worth knowing:

- **v9 (2020):** Ivy compiler. Better type inference into template expressions, stricter null checks via `strictNullChecks`, type-aware AOT errors.
- **v12 (2021):** `strict` mode in `ng new` projects by default. Strict template type checking (`strictTemplates`) recommended for new code.
- **v14 (2022):** **Typed forms.** `FormGroup<TControls>`, `FormControl<T>`, `FormArray<TControl>` — the forms library finally has real types after years of `any`. See [Reactive Forms](forms/reactive-forms.md).
- **v16 (2023):** Signal inputs — `input<T>()` returns `InputSignal<T>`, fully typed in both directions (component definition and binding sites).
- **v17 (2023):** Standalone components are the default. Built-in control flow (`@if`, `@for`, `@switch`) with stricter type checking than the old structural directives.
- **v22 (now):** TypeScript 5.5+ minimum. The Application Builder (esbuild) emits TypeScript-checked output as the default. **Signal Forms** (experimental) leans even further into typed reactive primitives.

The trajectory: every Angular release has narrowed the gap where `any` could hide. Comfort with TypeScript generics, mapped types, and conditional types pays off more in v22 than it did in v9 — the framework's APIs assume it.

## Summary

You now have foundational **what**, **how**, and **why** for **TypeScript** plus a taste of unions, intersections, conditional types, `satisfies`, and the v22-relevant utility types. Keep practicing — you'll feel more confident in Angular and the broader TS ecosystem. Explore **decorators**, **enums**, and **mixins** on your own; this series focuses on Angular.

## Youtube Video

[![Day 11](https://img.youtube.com/vi/ozHjDLuusVU/0.jpg)](https://youtu.be/ozHjDLuusVU) <!-- TODO: asset -->
[![Day 12](https://img.youtube.com/vi/4tcajihANZQ/0.jpg)](https://youtu.be/4tcajihANZQ) <!-- TODO: asset -->

## References

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [TypeScript Utility Types](https://www.typescriptlang.org/docs/handbook/utility-types.html)
- [`satisfies` operator (TS 4.9 release notes)](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html#satisfies-operator)
- [Angular v22 release notes (angular.dev)](https://angular.dev/reference/releases)
- [Angular Style Guide](https://angular.dev/style-guide)

## Author

Chau Tran — https://github.com/nartc

*Translated from the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) series by Angular Vietnam. MIT licensed.*
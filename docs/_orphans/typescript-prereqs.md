---
roadmap_node: "typescript-prereqs"
title: "TypeScript Prerequisites for Angular"
file: "_orphans/typescript-prereqs.md"
source_days: [11, 12]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# TypeScript Prerequisites for Angular

Over the first ten days we explored Angular concepts and wrote code — all of it **TypeScript** (**TS**). Working with Angular means TS fundamentals matter. Today we'll cover the basics; advanced types come in the second half of this article.

> Solid **TS** foundations help when you tackle harder Angular topics like `Dependency Injection`.

## What is TypeScript?

**TS** is a **superset** of **JavaScript** (**JS**). Installing **TS** gives you the **TypeScript Compiler** (`tsc`) CLI. `tsc` compiles **TS** to **JS** for browsers or runtimes like **NodeJS**.

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

## Why TypeScript?

### Pros

Explicit types, familiar OOP syntax (`abstract`, `class`, generics), and strong editor support help you build maintainable apps. **TS** ranks highly in surveys like the [Stack Overflow Developer Survey](https://insights.stackoverflow.com/survey/2020#technology-most-loved-dreaded-and-wanted-languages-loved).

### Cons

More boilerplate, stricter checks, third-party libraries need `.d.ts` typings, and the so-called [TypeScript tax](https://medium.com/javascript-scene/the-typescript-tax-132ff4cb175b).

### Trade-off

Angular chose **TS** for structure, maintainability, and scale — worth the trade-offs for most teams.

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

`unknown` (TS 3.0+) is safer than `any` when the type isn't known yet. See [new unknown top type](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html#new-unknown-top-type).

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

### Type alias examples

Restrict `flexDirection` to valid CSS values:

```typescript
type FlexDirection = 'row' | 'column' | 'row-reverse' | 'column-reverse';

@Component({
  selector: 'flex-container',
  template: `<ng-content></ng-content>`
})
export class FlexComponent {
  @Input() flexDirection: FlexDirection = 'row';
  // HostBinding getters for display and flex-direction...
}
```

Conditional dictionary helper:

```typescript
type ObjectDictionary<T> = { [key: string]: T };
type ArrayDictionary<T> = { [key: string]: T[] };
export type Dictionary<T> = T extends []
  ? ArrayDictionary<T[number]>
  : ObjectDictionary<T>;
```

### Built-in utility types (sample)

`Exclude`, `Extract`, `Readonly`, `Partial`, `Pick`, `Record`, `ReturnType`, `Omit`, and more — see [Advanced Types](https://www.typescriptlang.org/docs/handbook/advanced-types.html).

```typescript
type Person = {
  firstName: string;
  lastName: string;
  password: string;
};

type PersonWithNames = Pick<Person, 'firstName' | 'lastName'>;
type PersonWithoutPassword = Omit<Person, 'password'>;
```

## Summary

You now have foundational **what**, **how**, and **why** for **TypeScript** plus a taste of unions, intersections, and conditional types. Keep practicing — you'll feel more confident in Angular and other TS ecosystems. Explore **decorators**, **enums**, and **mixins** on your own; this series focuses on Angular.

## Youtube Video

[![Day 11](https://img.youtube.com/vi/ozHjDLuusVU/0.jpg)](https://youtu.be/ozHjDLuusVU) <!-- TODO: asset -->
[![Day 12](https://img.youtube.com/vi/4tcajihANZQ/0.jpg)](https://youtu.be/4tcajihANZQ) <!-- TODO: asset -->

## Author

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

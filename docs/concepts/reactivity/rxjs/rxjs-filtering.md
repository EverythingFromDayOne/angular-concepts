---
roadmap_node: "rxjs-filtering"
title: "RxJS Filtering Operators"
file: "reactivity/rxjs/rxjs-filtering.md"
source_days: [22]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Filtering Operators

Today we continue with **RxJS Operators** — specifically **Filtering Operators**. As the name suggests, these operators filter values emitted from a source `Observable`, much like filtering elements in an `Array`.

### filter()

`filter<T>(predicate: (value: T, index: number) => boolean, thisArg?: any): MonoTypeOperatorFunction<T>`

`filter()` takes a `predicate` that must return a truthy or falsy value. Truthy values are emitted; falsy values are dropped. It works like `Array.prototype.filter()`.

![RxJS filter](assets/rxjs-filter.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4, 5, 6])
  .pipe(
    filter((x) => x % 2 === 0) // even numbers
  )
  .subscribe(console.log); // output: 2, 4, 6
```

### first()

`first<T, D>(predicate?: (value: T, index: number, source: Observable<T>) => boolean, defaultValue?: D): OperatorFunction<T, T | D>`

`first()` emits the first value from the `Observable`, then `complete`s. It throws `EmptyError` if the `Observable` completes without emitting (for example `EMPTY`, or `of()` with no arguments).

![RxJS first](assets/rxjs-first.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4, 5, 6])
  .pipe(first())
  .subscribe(console.log, null, () => console.log('complete')); // output: 1 -> complete

of() // an empty Observable
  .pipe(first())
  .subscribe(null, console.log, null); // Error: EmptyError
```

`first()` also accepts optional `predicate` and `defaultValue`. With a `predicate`, it throws if the source completes with no matching value. Pass `defaultValue` to avoid the error.

> If you've used **.NET LINQ**, `first(predicate, defaultValue)` behaves like `FirstOrDefault`.

```typescript
from([1, 2, 3, 4, 5, 6])
  .pipe(first((x) => x > 3))
  .subscribe(console.log, null, () => console.log('complete')); // output: 4 -> complete

from([1, 2, 3, 4, 5, 6])
  .pipe(first((x) => x > 6)) // without default value
  .subscribe(null, console.log, null); // Error: Error

from([1, 2, 3, 4, 5, 6])
  .pipe(
    first((x) => x > 6),
    'defaultValue'
  ) // with default value
  .subscribe(console.log, null, () => console.log('complete')); // output: 'defaultValue' -> complete
```

### last()

`last<T, D>(predicate?: (value: T, index: number, source: Observable<T>) => boolean, defaultValue?: D): OperatorFunction<T, T | D>`

The opposite of `first()`: `last()` emits the final value before the source `complete`s. It shares the same behaviors as `first()`:

- Throws `EmptyError` if the source completes without emitting.
- Accepts optional `predicate` and `defaultValue`.
- Throws if only `predicate` is given and no value matches.
- Emits `defaultValue` when both `predicate` and `defaultValue` are provided and nothing matches.

![RxJS last](assets/rxjs-last.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4, 5, 6])
  .pipe(last())
  .subscribe(console.log, null, () => console.log('complete')); // output: 6 -> complete

of() // an empty Observable
  .pipe(last())
  .subscribe(null, console.log, null); // Error: EmptyError
```

### find()

`find<T>(predicate: (value: T, index: number, source: Observable<T>) => boolean, thisArg?: any): OperatorFunction<T, T | undefined>`

Like `Array.prototype.find()`: emits the first value matching `predicate`, then `complete`s. Unlike `first()`, `find()` **requires** a `predicate` and does not error when nothing matches.

![RxJS find](assets/rxjs-find.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4, 5, 6])
  .pipe(
    find((x) => x % 2 === 0) // even numbers
  )
  .subscribe(console.log, null, () => console.log('complete')); // output: 2 -> complete
```

### single()

`single<T>(predicate?: (value: T, index: number, source: Observable<T>) => boolean): MonoTypeOperatorFunction<T>`

Similar to `first()` but stricter: `single()` throws if **more than one** value matches. It does not accept `defaultValue` and emits `undefined` when a `predicate` is given but nothing matches. Use `single()` mainly when you expect exactly one matching value. If the source emits more than one value (with or without a predicate), `single()` throws.

![RxJS single](assets/rxjs-single.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3]).pipe(single()).subscribe(null, console.log, null); // error: Error -> more than one value from from() with no predicate

from([1, 2, 3])
  .pipe(single((x) => x === 2))
  .subscribe(console.log, null, () => console.log('complete')); // output: 2 -> complete

from([1, 2, 3])
  .pipe(single((x) => x > 1))
  .subscribe(null, console.log, null); // error: Error -> more than one value > 1
```

### take()

`take<T>(count: number): MonoTypeOperatorFunction<T>`

`take()` accepts a `count` — how many values to emit from the source before completing.

![RxJS take](assets/rxjs-take.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4])
  .pipe(take(2))
  .subscribe(console.log, null, () => console.log('complete')); // output: 1, 2 -> complete
```

#### Special case: `take(1)`

`take(1)` looks like another form of `first()`, but `take(1)` does **not** throw if the source completes without emitting.

Use `take(1)` when you need:

- A one-time report of where the user clicked on first page load
- A snapshot of data at a point in time
- A route guard that returns an `Observable`

### takeLast()

`takeLast<T>(count: number): MonoTypeOperatorFunction<T>`

Like `take()` but from the end: emit the last `n` values. `takeLast()` only emits after the source `complete`s. On a long-lived source like `interval()`, `takeLast()` never emits.

![RxJS takeLast](assets/rxjs-takeLast.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4])
  .pipe(takeLast(2))
  .subscribe(console.log, null, () => console.log('complete')); // output: 3, 4 -> complete
```

### takeUntil()

`takeUntil<T>(notifier: Observable<any>): MonoTypeOperatorFunction<T>`

`takeUntil()` takes a `notifier` `Observable` and emits from the source **until** the notifier emits.

![RxJS takeUntil](assets/rxjs-takeUntil.png) <!-- TODO: asset -->

```typescript
interval(1000)
  .pipe(takeUntil(fromEvent(document, 'click')))
  .subscribe(console.log, null, () => console.log('complete')); // output: 0, 1, 2, 3, 4 -- click --> 'complete'
```

#### Use case in Angular

`takeUntil()` is very common for **unsubscribing** in `ngOnDestroy()`. Imagine a `destroySubject: Subject<void>` as the notifier. When `ngOnDestroy()` runs, call `destroySubject.next()` and pipe `takeUntil(this.destroySubject)` — subscriptions in the component are torn down when the component unmounts.

### takeWhile()

`takeWhile<T>(predicate: (value: T, index: number) => boolean, inclusive: boolean = false): MonoTypeOperatorFunction<T>`

Similar to `takeUntil()` but driven by a `predicate` on each emitted value instead of an external notifier. `takeWhile()` and `takeUntil()` are often confused, but they behave differently. See these community posts on the topic: [post 1 (Vietnamese)](https://www.facebook.com/groups/AngularVietnam/permalink/816969675468552/) and [post 2 (Vietnamese)](https://www.facebook.com/groups/AngularVietnam/permalink/845798295919023/)

![RxJS takeWhile](assets/rxjs-takeWhile.png) <!-- TODO: asset -->

```typescript
interval(1000)
  .pipe(takeWhile((x) => x < 6))
  .subscribe(console.log, null, () => console.log('complete')); // output: 0, 1, 2, 3, 4, 5 --> complete
```

`takeWhile()` works best when the stop condition comes from the stream itself (internal). `takeUntil()` works best with an external notifier.

### skip()

`skip<T>(count: number): MonoTypeOperatorFunction<T>`

The inverse of `take()`: skip the first `n` values, then emit the rest.

![RxJS skip](assets/rxjs-skip.png) <!-- TODO: asset -->

```typescript
from([1, 2, 3, 4])
  .pipe(skip(1))
  .subscribe(console.log, null, () => console.log('complete')); // output: 2, 3, 4 --> complete
```

### skipUntil()

`skipUntil<T>(notifier: Observable<any>): MonoTypeOperatorFunction<T>`

Like `takeUntil()` but inverted — skip until the notifier emits.

![RxJS skipUntil](assets/rxjs-skipUntil.png) <!-- TODO: asset -->

```typescript
interval(1000)
  .pipe(skipUntil(fromEvent(document, 'click')))
  .subscribe(console.log); // output: click at 5 seconds -> 5, 6, 7, 8, 9....
```

### skipWhile()

`skipWhile<T>(predicate: (value: T, index: number) => boolean): MonoTypeOperatorFunction<T>`

Like `takeWhile()` but inverted.

![RxJS skipWhile](assets/rxjs-skipWhile.png) <!-- TODO: asset -->

```typescript
interval(1000)
  .pipe(skipWhile((x) => x < 5))
  .subscribe(console.log); // output: 6, 7, 8, 9....
```

### distinct()

`distinct<T, K>(keySelector?: (value: T) => K, flushes?: Observable<any>): MonoTypeOperatorFunction<T>`

`distinct()` compares emitted values and only emits values that have not been emitted before.

```typescript
from([1, 2, 3, 4, 5, 5, 4, 3, 6, 1])
  .pipe(distinct())
  .subscribe(console.log, null, () => console.log('complete')); // output: 1, 2, 3, 4, 5, 6 -> complete
```

You can pass a `keySelector` to choose which property to compare when the stream emits complex objects:

```typescript
of({ age: 4, name: 'Foo' }, { age: 7, name: 'Bar' }, { age: 5, name: 'Foo' })
  .pipe(distinct((p) => p.name))
  .subscribe(console.log, null, () => console.log('complete')); // output: { age: 4, name: 'Foo' }, { age: 7, name: 'Bar' } -> complete
```

### distinctUntilChanged()

`distinctUntilChanged<T, K>(compare?: (x: K, y: K) => boolean, keySelector?: (x: T) => K): MonoTypeOperatorFunction<T>`

Similar to `distinct()`, but only compares the **incoming** value with the **previous** one — not the full history.

```typescript
from([1, 1, 2, 2, 2, 1, 1, 2, 3, 3, 4])
  .pipe(distinctUntilChanged())
  .subscribe(console.log, null, () => console.log('complete')); // output: 1, 2, 1, 2, 3, 4 -> complete
```

Optional `compare` and `keySelector` work like on `distinct()`. Without `compare`, `===` is used. If `compare` returns truthy, the value is skipped.

```typescript
of(
  { age: 4, name: 'Foo' },
  { age: 6, name: 'Foo' },
  { age: 7, name: 'Bar' },
  { age: 5, name: 'Foo' }
)
  .pipe(distinctUntilChanged((a, b) => a.name === b.name))
  .subscribe(console.log, null, () => console.log('complete')); // output: { age: 4, name: 'Foo' }, { age: 7, name: 'Bar' }, { age: 5, name: 'Foo' } -> complete
```

### distinctUntilKeyChanged()

`distinctUntilKeyChanged<T, K extends keyof T>(key: K, compare?: (x: T[K], y: T[K]) => boolean): MonoTypeOperatorFunction<T>`

Shortcut for `distinctUntilChanged()` with a `keySelector`.

```typescript
of(
  { age: 4, name: 'Foo' },
  { age: 6, name: 'Foo' },
  { age: 7, name: 'Bar' },
  { age: 5, name: 'Foo' }
)
  .pipe(distinctUntilKeyChanged('name')
  .subscribe(console.log, null, () => console.log('complete')); // output: { age: 4, name: 'Foo' }, { age: 7, name: 'Bar' }, { age: 5, name: 'Foo' } -> complete
```

### Note

Eight more operators come in pairs: `throttle` / `throttleTime`, `debounce` / `debounceTime`, and so on. We'll focus on the `*Time` variants because they mirror the non-time versions and are used more often day to day.

### throttle() / throttleTime()

`throttle<T>(durationSelector: (value: T) => SubscribableOrPromise<any>, config: ThrottleConfig = defaultThrottleConfig): MonoTypeOperatorFunction<T>`
`throttleTime<T>(duration: number, scheduler: SchedulerLike = async, config: ThrottleConfig = defaultThrottleConfig): MonoTypeOperatorFunction<T>`

`throttleTime()` takes a `duration` in milliseconds. When the source emits, `throttleTime()` emits that value and starts a timer. While the timer runs, further source emissions are ignored. When the timer finishes, it waits for the next source value and repeats.

> `throttle` works like `throttleTime` but takes an `Observable` as `durationSelector` instead of a fixed duration.

![RxJS throttleTime](assets/rxjs-throttleTime.png) <!-- TODO: asset -->

```typescript
fromEvent(document, 'mousemove')
  .pipe(throttleTime(1000))
  .subscribe(console.log, null, () => console.log('complete')); // output: MouseEvent {} - wait 1s -> MouseEvent { } - wait 1s -> MouseEvent { }
```

`throttleTime()` accepts `ThrottleConfig: {leading: boolean, trailing: boolean}` to control whether the first or last value in the window is emitted. Default is `{leading: true, trailing: false}`.

`throttleTime()` is common for DOM events like `mousemove` to limit how often handlers run.

### debounce() / debounceTime()

`debounce<T>(durationSelector: (value: T) => SubscribableOrPromise<any>): MonoTypeOperatorFunction<T>`
`debounceTime<T>(dueTime: number, scheduler: SchedulerLike = async): MonoTypeOperatorFunction<T>`

`debounceTime()` takes `dueTime` in milliseconds. Each source emission resets a timer; only when the timer completes without another emission does `debounceTime()` emit the **latest** value.

> `debounce` works like `debounceTime` but uses an `Observable` as `durationSelector` instead of `dueTime`.

![RxJS debounceTime](assets/rxjs-debounceTime.png) <!-- TODO: asset -->

```typescript
this.filterControl.valueChanges.pipe(debounceTime(500)).subscribe(console.log); // output: type "abcd" then pause 500ms -> 'abcd'
```

Because of that behavior, `debounceTime()` is the go-to for filter inputs on lists.

### audit() / auditTime()

`audit<T>(durationSelector: (value: T) => SubscribableOrPromise<any>): MonoTypeOperatorFunction<T>`
`auditTime<T>(duration: number, scheduler: SchedulerLike = async): MonoTypeOperatorFunction<T>`

`auditTime()` takes `duration` in milliseconds. It behaves like `throttleTime()` with `{trailing: true}` — after the timer completes, it emits the most recent source value.

![RxJS auditTime](assets/rxjs-auditTime.png) <!-- TODO: asset -->

```typescript
fromEvent(document, 'click').pipe(auditTime(1000)).subscribe(console.log); // output: click - wait 1s -> MouseEvent {} -click  wait 1s (in 1s, click 10 times) -> MouseEvent {} -> click wait 1s -> MouseEvent {}
```

### sample() / sampleTime()

`sample<T>(notifier: Observable<any>): MonoTypeOperatorFunction<T>`
`sampleTime<T>(period: number, scheduler: SchedulerLike = async): MonoTypeOperatorFunction<T>`

`sampleTime()` takes `period` in milliseconds. Its timer starts on subscribe and fires every `period`, emitting the latest source value at each tick.

![RxJS sampleTime](assets/rxjs-sampleTime.png) <!-- TODO: asset -->

```typescript
fromEvent(document, 'click').pipe(sampleTime(1000)).subscribe(console.log); // click - wait 1s -> MouseEvent {}
```

These four operators behave similarly except `debounceTime`, which is a bit different. This diagram illustrates the differences:

![RxJS difference](assets/rxjs-debounce-audit-sample-throttle.png) <!-- TODO: asset -->

_credit: [debounce vs throttle vs audit vs sample](https://dev.to/kosich/debounce-vs-throttle-vs-audit-vs-sample-difference-you-should-know-1f21)_

## Summary

That's a lot of operators! Commonly used **filtering operators** include `first()`, `last()`, `filter()`, `take()`, `takeUntil()`, `skip()`, `skipUntil()`, `debounceTime()`, and `throttleTime()`. The rest are useful too, just less frequent — dig deeper into any of them when you need to.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)

## Author

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

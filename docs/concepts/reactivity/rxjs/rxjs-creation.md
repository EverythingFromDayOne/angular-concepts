---
roadmap_node: "rxjs-creation"
title: "RxJS Creation Operators"
file: "reactivity/rxjs/rxjs-creation.md"
source_days: [20]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Creation Operators

In [the RxJS introduction](rxjs.md), we looked at `Observable` and learned how to create one by hand:

```typescript
const observable = new Observable(function subscribe(observer) {
  const id = setTimeout(() => {
    observer.next('Hello Rxjs');
    observer.complete();
  }, 1000);
  return function unsubscribe() {
    clearTimeout(id);
  };
});
```

You might wonder: "Do I really have to memorize this syntax every time I need an `Observable`? What about `next`, `complete`, and `unsubscribe`?" Today's article answers that question — we'll explore the **RxJS** operators used to create `Observable` instances.

> Operators are pure functions that let you program functionally with Observables. (See the [RxJS intro](rxjs.md).)

## Shared observer

Throughout this article we'll use this shared `observer`. If an example needs its own, we'll define it separately.

```typescript
const observer = {
  next: (val) => console.log(val),
  error: (err) => console.log(err),
  complete: () => console.log('complete'),
};
```

## Common creation operators

### `of()`

`of()` creates an `Observable` from any value: primitives, arrays, objects, functions, and so on. It accepts values as arguments and `complete`s immediately after all of them have been emitted.

1. Primitive value

```typescript
// output: 'hello'
// complete: 'complete'
of('hello').subscribe(observer);
```

2. Object / array

```typescript
// output: [1, 2, 3]
// complete: 'complete'
of([1, 2, 3]).subscribe(observer);
```

3. Sequence of values

```typescript
// output: 1, 2, 3, 'hello', 'world', {foo: 'bar'}, [4, 5, 6]
// complete: 'complete'
of(1, 2, 3, 'hello', 'world', { foo: 'bar' }, [4, 5, 6]).subscribe(observer);
```

### `from()`

`from()` is similar to `of()` — it also creates an `Observable` from a value. The difference is that `from()` only accepts an `Iterable` or a `Promise`.

> An iterable is anything you can loop over — for example an array, `Map`, `Set`, or string. When you loop over a string, you get each character.

1. Array

```typescript
// output: 1, 2, 3
// complete: 'complete'
from([1, 2, 3]).subscribe(observer);
```

When `from()` receives an array, it emits each element in sequence. That is equivalent to `of(1, 2, 3)`.

2. String

```typescript
// output: 'h', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd'
// complete: 'complete'
from('hello world').subscribe(observer);
```

3. Map / Set

```typescript
const map = new Map();
map.set(1, 'hello');
map.set(2, 'bye');

// output: [1, 'hello'], [2, 'bye']
// complete: 'complete'
from(map).subscribe(observer);

const set = new Set();
set.add(1);
set.add(2);

// output: 1, 2
// complete: 'complete'
from(set).subscribe(observer);
```

4. Promise

```typescript
// output: 'hello world'
// complete: 'complete'
from(Promise.resolve('hello world')).subscribe(observer);
```

`from()` unwraps the resolved value of a `Promise`. This is how you convert a `Promise` into an `Observable`.

### `fromEvent()`

`fromEvent()` turns a DOM event into an `Observable` — for example a mouse click or keyboard input.

```typescript
const btn = document.querySelector('#btn');
const input = document.querySelector('#input');

// output (example): MouseEvent {...}
// complete: nothing logged
fromEvent(btn, 'click').subscribe(observer);

// output (example): KeyboardEvent {...}
// complete: nothing logged
fromEvent(input, 'keydown').subscribe(observer);
```

Note that `fromEvent()` creates an `Observable` that does not `complete` on its own. That makes sense: you want to listen for events like `click` and `keydown` until you decide to stop. `fromEvent()` cannot know when you're done. That also means you must manually `unsubscribe` from `fromEvent()` Observables to avoid **memory leaks**.

### `fromEventPattern()`

`fromEventPattern()` is an _advanced_ form of `fromEvent()`. Conceptually it also creates an `Observable` from events, but the API and the kinds of events you can handle differ. Compare:

```typescript
// fromEvent() from the example above
// output: MouseEvent {...}
fromEvent(btn, 'click').subscribe(observer);

// fromEventPattern
// output: MouseEvent {...}
fromEventPattern(
  (handler) => {
    btn.addEventListener('click', handler);
  },
  (handler) => {
    btn.removeEventListener('click', handler);
  }
).subscribe(observer);
```

Another example: getting the pointer position on the clicked element.

```typescript
// output: 10 10
fromEvent(btn, 'click')
  .pipe(map((ev: MouseEvent) => ev.offsetX + ' ' + ev.offsetY))
  .subscribe(observer);

// fromEventPattern
// In this example we'll pull addHandler and removeHandler into separate functions

function addHandler(handler) {
  btn.addEventListener('click', handler);
}

function removeHandler(handler) {
  btn.removeEventListener('click', handler);
}

// output: 10 10
fromEventPattern(
  addHandler,
  removeHandler,
  (ev: MouseEvent) => ev.offsetX + ' ' + ev.offsetY
).subscribe(observer);
```

`fromEventPattern()` accepts three arguments: `addHandler`, `removeHandler`, and an optional `projectFunction`. It is not fundamentally different from `fromEvent()`, but it gives you an API to bridge native event APIs into `Observable`s — as in the example above with `addEventListener` and `removeEventListener`. With that pattern you can convert more complex event APIs — for example a **SignalR Hub**:

```typescript
// _getHub() returns the Hub instance
const hub = this._getHub(url);
return fromEventPattern(
  (handler) => {
    // open websocket
    hub.connection.on(methodName, handler);

    if (hub.refCount === 0) {
      hub.connection.start();
    }

    hub.refCount++;
  },
  (handler) => {
    hub.refCount--;
    // close websocket on unsubscribe
    hub.connection.off(methodName, handler);
    if (hub.refCount === 0) {
      hub.connection.stop();
      delete this._hubs[url];
    }
  }
);
```

### `interval()`

`interval()` creates an `Observable` that emits incrementing integers starting at 0 on a fixed schedule — like `setInterval`.

```typescript
// output: 0, 1, 2, 3, 4, ...
interval(1000) // emit a value every second
  .subscribe(observer);
```

Like `fromEvent()`, `interval()` does not `complete` automatically, so you need to handle `unsubscribe` yourself.

### `timer()`

`timer()` has two usage patterns:

- Create an `Observable` that emits once after a delay, then `complete`s.
- Create an `Observable` that emits once after a delay, then emits on every interval thereafter — similar to `interval()` but with an initial delay. This pattern does not `complete` on its own.

```typescript
// output: after 1 second -> 0
// complete: 'complete'
timer(1000).subscribe(observer);

// output: after 1 second -> 0, 1, 2, 3, 4, 5 ...
timer(1000, 1000).subscribe(observer);
```

### `throwError()`

`throwError()` creates an `Observable` that immediately errors when subscribed — instead of emitting values.

```typescript
// error: 'an error'
throwError('an error').subscribe(observer);
```

`throwError()` is often used in error handling: after handling an error on one `Observable`, you may want to propagate it to the next `ErrorHandler`. Some operators require you to return an `Observable` (for example `switchMap`, `catchError`) — `throwError()` fits that role well.

### `defer()`

Finally, let's look at `defer()` — a particularly useful operator. `defer()` accepts an `ObservableFactory` and returns the `Observable` it produces. The special part: `defer()` invokes the factory to create a **new** `Observable` for every `Subscriber`. Compare:

```typescript
// of()
const now$ = of(Math.random());
// output: 0.4146530439875191
now$.subscribe(observer);
// output: 0.4146530439875191
now$.subscribe(observer);
// output: 0.4146530439875191
now$.subscribe(observer);
```

`of()` returns the same `Math.random()` value for all three subscriptions. Now try `defer()`:

```typescript
const now$ = defer(() => of(Math.random()));
// output: 0.27312186273281935
now$.subscribe(observer);
// output: 0.7180321390218474
now$.subscribe(observer);
// output: 0.9626312890837065
now$.subscribe(observer);
```

With `defer()`, each subscription gets a different value. When is that useful? For example, when you need to `retry` an `Observable` and compare against a fresh random value to decide whether to continue — `defer()` (combined with `retry`) is a very effective solution.

## Summary

Today we covered quite a few operators for creating `Observable`s — officially called **Creation Operators**. They are common, but you mainly need a solid grasp of `from()`, `of()`, `interval()`, `timer()`, and `defer()`. `fromEvent()` and `fromEventPattern()` are used less often in Angular apps. **RxJS** also provides other creation operators such as `ajax()`, `fromFetch()`, and `generate()` — but in Angular we rarely need them. For HTTP, we already have `HttpClientModule` instead of `ajax()` and `fromFetch()`.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)

## Author

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

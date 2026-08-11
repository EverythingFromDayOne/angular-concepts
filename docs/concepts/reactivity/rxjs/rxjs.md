---
roadmap_node: "rxjs"
title: "Introduction to RxJS and Observables"
file: "reactivity/rxjs/rxjs.md"
source_days: [19]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Introduction to RxJS and Observables

When you learn Angular, you'll notice it depends heavily on **RxJS**. Forms, `HttpClient`, `QueryList`, `EventEmitter`, and more all use observables.

That's both a strength and a learning curve. RxJS handles asynchronous work powerfully — but you need to think in **streams**.

> RxJS is a library for composing asynchronous and event-based programs by using observable sequences. [RxJS Overview](https://rxjs.dev/guide/overview)

> In RxJS and in reactive programming in general, the fundamental unit of work is the stream. Think in terms of streams (think reactively) and design code so data flows through transformations until it reaches your desired state. [RxJS in Action](https://freecontent.manning.com/reactive-fundamentals-thinking-in-streams/)

![Everything is a stream](assets/everything-is-a-stream.jpg) <!-- TODO: asset -->

## Observable

In synchronous programming, **arrays** hold multiple values. JavaScript lets you chain `map`, `filter`, `reduce`, `every`, `some`, and more.

Asynchronous programming adds events, promises, and callbacks — things that may happen at unknown future times. Callbacks handle async tasks; promises still deliver only a **single** value, so they can't model multi-value streams like DOM events.

**Observables** handle multiple asynchronous values and treat everything as streams. Data flows through operators and emerges transformed at the end.

Think of an Observable as an array of values over time:

![Values over time](assets/rxjs-streams.gif) <!-- TODO: asset -->

Observables aren't native to JavaScript yet, but RxJS provides `Observable`, `Observer`, `Subject`, and a rich set of **operators**.

## Use case: throttle

Fast-firing events often need throttling — for example, ignoring button clicks that arrive faster than 500 ms apart.

Vanilla JS vs RxJS:

```ts
const btnjsThrottle = document.querySelector('#jsThrottle');
const btnrxjsThrottle = document.querySelector('#rxjsThrottle');
// PURE JS version
let count = 0;
let rate = 500;
let lastClick = Date.now() - rate;
btnjsThrottle.addEventListener('click', () => {
  if (Date.now() - lastClick >= rate) {
    console.log(`Clicked ${++count} times`);
    lastClick = Date.now();
  }
});

// RxJS version
import { fromEvent } from 'rxjs';
import { throttleTime, scan } from 'rxjs/operators';

fromEvent(btnrxjsThrottle, 'click')
  .pipe(
    throttleTime(500),
    scan((count) => count + 1, 0)
  )
  .subscribe((count) => console.log(`RxJS: Clicked ${count} times`));
```

The RxJS version is concise, and you can add more operators in the pipe as needed.

## RxJS core concepts

### Observable

- Represents a collection of future values or events. When values or events occur, the Observable delivers them to Observers.
- An Observable is essentially a function that takes an Observer and returns a teardown (unsubscribe) function.
  > Observables are functions that tie an observer to a producer. [Ben Lesh: Hot vs Cold Observables](https://medium.com/@benlesh/hot-vs-cold-observables-f8094ed53339)

### Observer

- A set of callbacks (`next`, `error`, `complete`) for values emitted by an Observable.

### Subscription

- The result of subscribing to an Observable — used to cancel execution.

### Operators

- Pure functions for functional programming with Observables.

### Subject

- Multicasts values to multiple Observers.

### Schedulers

- Control when a subscription starts and when values are delivered.

## Working with Observables

### Creating Observables

Call the `Observable` constructor with a **subscribe function** that receives an Observer:

```ts
const observable = new Observable(function subscribe(observer) {
  const id = setTimeout(() => {
    observer.next('Hello Rxjs');
    observer.complete();
  }, 1000);
});
```

Return a teardown function for cleanup:

```ts
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

### Invoking an Observable

Observables are lazy — nothing runs until you subscribe. Subscribe returns a `Subscription`:

```ts
const subscription = observable.subscribe({
  next: (value) => {
    console.log(value);
  },
  error: (error) => {
    console.log(error);
  },
  complete: () => {
    console.log('Done');
  },
});
```

All three callbacks are optional — provide only what you need.

### Executing Observables

The function passed to `new Observable(...)` is the **Observable execution**. After subscribe, execution starts. When `next`, `error`, or `complete` fires, the matching Observer callback runs.

Notification types:

- **Next** — delivers a value (any type)
- **Error** — delivers a JavaScript Error or exception
- **Complete** — signals the stream finished (no value)

`error` and `complete` are mutually exclusive — only one can fire, and nothing is delivered afterward.

> In an Observable Execution, zero to infinite Next notifications may be delivered. If either an Error or Complete notification is delivered, then nothing else can be delivered afterwards.

### Disposing Observable executions

Executions can run indefinitely. When data is stale or no longer needed — closing a WebSocket, removing an event listener from a destroyed DOM node — unsubscribe:

```ts
const subscription = observable.subscribe({
  next: (value) => {
    console.log(value);
  },
  error: (error) => {
    console.log(error);
  },
  complete: () => {
    console.log('Done');
  },
});

setTimeout(() => {
  subscription.unsubscribe();
}, 500);
```

> If you create an Observable manually, you must implement teardown yourself.
>
> When you subscribe, you get back a Subscription. Call `unsubscribe()` to cancel the execution.

## Observers

An Observer consumes data from an Observable — an object with `next`, `error`, and `complete` callbacks:

```ts
const observer = {
  next: (x) => console.log('Observer got a next value: ' + x),
  error: (err) => console.error('Observer got an error: ' + err),
  complete: () => console.log('Observer got a complete notification'),
};
```

Pass it to subscribe:

```ts
observable.subscribe(observer);
```

> Observers are just objects with three callbacks, one for each type of notification that an Observable may deliver.

You can omit callbacks. `subscribe` also accepts bare functions (discouraged except for a single `next` handler):

```ts
observable.subscribe(
  (x) => console.log('Observer got a next value: ' + x),
  (err) => console.error('Observer got an error: ' + err),
  () => console.log('Observer got a complete notification')
);
```

If you skip the error handler, pass `null` or `undefined`:

```ts
observable.subscribe(
  (x) => console.log('Observer got a next value: ' + x),
  null,
  () => console.log('Observer got a complete notification')
);
```

## Subscription

A Subscription represents a disposable resource — typically an Observable execution. `unsubscribe()` (RxJS 5+) cancels it.

Countdown example — unsubscribe after 5 seconds:

```ts
const observable = interval(1000);
const subscription = observable.subscribe((x) => console.log(x));

setTimeout(() => {
  subscription.unsubscribe();
}, 5000);
```

> A Subscription essentially just has an unsubscribe() function to release resources or cancel Observable executions.

A parent Subscription can hold child Subscriptions. Unsubscribing the parent unsubscribes children too:

```ts
const foo = interval(500);
const bar = interval(700);

const subscription = foo.subscribe((x) => console.log('first: ' + x));
const childSub = bar.subscribe((x) => console.log('second: ' + x));

subscription.add(childSub);

setTimeout(() => {
  // Unsubscribes BOTH `subscription` and `childSub`
  subscription.unsubscribe();
}, 2000);
```

## Summary

We've introduced reactive programming, RxJS core concepts, creating and subscribing to Observables, Observers, and Subscriptions.

Further reading:

- [RxJS reactive programming](https://www.tiepphan.com/rxjs-reactive-programming/) (Vietnamese)
- https://rxjs.dev/guide/overview
- https://angular.io/guide/observables
- https://medium.com/@benlesh/learning-observable-by-building-observable-d5da57405d87
- https://medium.com/@benlesh/hot-vs-cold-observables-f8094ed53339

## Youtube Video

[![RxJS Introduction](https://img.youtube.com/vi/lRfyUh4ex38/0.jpg)](https://youtu.be/lRfyUh4ex38) <!-- TODO: asset -->

## Code sample

https://stackblitz.com/edit/rxjs-racgao?file=index.ts

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

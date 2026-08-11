---
roadmap_node: "rxjs-transformation"
title: "RxJS Transformation Operators"
file: "reactivity/rxjs/rxjs-transformation.md"
source_days: [21]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Transformation Operators

In [RxJS Creation Operators](rxjs-creation.md) we met **Creation Operators** — operators you call like ordinary functions. Today we'll look at **Pipeable Operators**, which are used inside an `Observable` instance's `pipe()` method instead of being called on their own.

## Pipeable operators

A pipeable operator is a function that takes an `Observable` and returns a different `Observable`. They are pure: the input `Observable` is never mutated.

Syntax:

```ts
observableInstance.pipe(operator1(), operator2());
```

No matter how many operators you chain, `observableInstance` itself stays the same. The chain returns a new `Observable`, so you either assign it or subscribe immediately:

```ts
const returnObservable = observableInstance.pipe(operator1(), operator2());
```

If you use RxJS older than 5.5 you may see prototype method chaining instead. From 5.5 onward, prefer pipeable operators — see [pipeable operators](https://rxjs.dev/guide/v6/pipeable-operators) for background.

Pipeable operators fall into several categories. Today we focus on **Transformation Operators**.

## Transformation operators

You're probably comfortable with JavaScript arrays: loop over elements, apply a function to each one, and collect results into a new array of the same length:

```ts
const users = [
  {
    id: 'ddfe3653-1569-4f2f-b57f-bf9bae542662',
    username: 'tiepphan',
    firstname: 'tiep',
    lastname: 'phan',
  },
  {
    id: '34784716-019b-4868-86cd-02287e49c2d3',
    username: 'nartc',
    firstname: 'chau',
    lastname: 'tran',
  },
];

const usersVm = users.map((user) => {
  return {
    ...user,
    fullname: `${user.firstname} ${user.lastname}`,
  };
});
```

The result looks like this:

```ts
usersVm = [
  {
    id: 'ddfe3653-1569-4f2f-b57f-bf9bae542662',
    username: 'tiepphan',
    firstname: 'tiep',
    lastname: 'phan',
    fullname: 'tiep phan',
  },
  {
    id: '34784716-019b-4868-86cd-02287e49c2d3',
    username: 'nartc',
    firstname: 'chau',
    lastname: 'tran',
    fullname: 'chau tran',
  },
];
```

One transformation pass gives us the shape we want.

What about `Observable`? Imagine a system that tracks who logs in. At various times one or more users sign in, and each time the system sends us an event. We want to do the same kind of mapping as above:

```ts
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

interface User {
  id: string;
  username: string;
  firstname: string;
  lastname: string;
}

const source = new Observable<User>((observer) => {
  const users = [
    {
      id: 'ddfe3653-1569-4f2f-b57f-bf9bae542662',
      username: 'tiepphan',
      firstname: 'tiep',
      lastname: 'phan',
    },
    {
      id: '34784716-019b-4868-86cd-02287e49c2d3',
      username: 'nartc',
      firstname: 'chau',
      lastname: 'tran',
    },
  ];

  setTimeout(() => {
    observer.next(users[0]);
  }, 1000);
  setTimeout(() => {
    observer.next(users[1]);
    observer.complete();
  }, 3000);
});

const observer = {
  next: (value) => console.log(value),
  error: (err) => console.error(err),
  complete: () => console.log('completed'),
};
source.subscribe(observer);
```

After one second the first user is emitted; two seconds later the second user is emitted along with the complete signal.

### map

`map<T, R>(project: (value: T, index: number) => R, thisArg?: any): OperatorFunction<T, R>`

If you need to show each user's `fullname` in `next`, you could compute it inside the handler — but it's cleaner to **transform** the stream before it reaches the subscriber. That's what RxJS `map` is for.

```ts
import { map } from 'rxjs/operators';

source
  .pipe(
    map((user) => {
      return {
        ...user,
        fullname: `${user.firstname} ${user.lastname}`,
      };
    })
  )
  .subscribe(observer);
```

Or if the requirement changes to only emit the user id:

```ts
source.pipe(map((user) => user.id)).subscribe(observer);
```

This usage is _quite similar_ to `Array.prototype.map`, isn't it?

![RxJS map](assets/rxjs-map.png) <!-- TODO: asset -->

### pluck

`pluck<T, R>(...properties: string[]): OperatorFunction<T, R>`

For plucking a single property from an object, you can use `pluck`:

```ts
import { pluck } from 'rxjs/operators';

source.pipe(pluck('id')).subscribe(observer);
```

![RxJS pluck](assets/rxjs-pluck.png) <!-- TODO: asset -->

### mapTo

`mapTo<T, R>(value: R): OperatorFunction<T, R>`

What if you want every emitted value mapped to a fixed constant? For example, tracking mouse hover with `mouseover` and `mouseleave` — always `true` on `mouseover` and `false` on `mouseleave`.

For now, know that `merge` combines two streams into one; we'll cover combination operators in a later article.

```ts
const element = document.querySelector('#hover');

const mouseover$ = fromEvent(element, 'mouseover');
const mouseleave$ = fromEvent(element, 'mouseleave');

const hover$ = merge(
  mouseover$.pipe(mapTo(true)),
  mouseleave$.pipe(mapTo(false))
);

hover$.subscribe(observer);
```

Now we have a `hover$` stream that tells us when the pointer is over an element.

![RxJS mapTo](assets/rxjs-mapTo.png) <!-- TODO: asset -->

### scan

`scan<T, R>(accumulator: (acc: R, value: T, index: number) => R, seed?: T | R): OperatorFunction<T, R>`

Each time the stream emits, apply a function that also receives the previous accumulated result — like `Array.prototype.reduce`. Example: count button clicks.

```ts
const button = document.querySelector('#add');

const click$ = fromEvent(button, 'click');

click$.pipe(scan((acc, curr) => acc + 1, 0)).subscribe(observer);
```

Count total posts as users log in over time:

```ts
const users$ = new Observable<User>((observer) => {
  const users = [
    {
      id: 'ddfe3653-1569-4f2f-b57f-bf9bae542662',
      username: 'tiepphan',
      firstname: 'tiep',
      lastname: 'phan',
      postCount: 5,
    },
    {
      id: '34784716-019b-4868-86cd-02287e49c2d3',
      username: 'nartc',
      firstname: 'chau',
      lastname: 'tran',
      postCount: 22,
    },
  ];

  setTimeout(() => {
    observer.next(users[0]);
  }, 1000);
  setTimeout(() => {
    observer.next(users[1]);
    observer.complete();
  }, 3000);
});

users$.pipe(scan((acc, curr) => acc + curr.postCount, 0)).subscribe(observer);
```

![RxJS scan](assets/rxjs-scan.png) <!-- TODO: asset -->

### reduce

`reduce<T, R>(accumulator: (acc: T | R, value: T, index?: number) => T | R, seed?: T | R): OperatorFunction<T, T | R>`

Similar to `scan`, but `reduce` waits until the source completes, then emits one final value and completes.

```ts
users$.pipe(reduce((acc, curr) => acc + curr.postCount, 0)).subscribe(observer);
```

![RxJS reduce](assets/rxjs-reduce.png) <!-- TODO: asset -->

### toArray

`toArray<T>(): OperatorFunction<T, T[]>`

Collect every emitted value into an array, emit that array once when the source completes, then complete. You could write this with `reduce`:

```ts
users$.pipe(reduce((acc, curr) => [...acc, curr], [])).subscribe(observer);
```

Or more concisely with `toArray`:

```ts
users$.pipe(toArray()).subscribe(observer);
```

### buffer

`buffer<T>(closingNotifier: Observable<any>): OperatorFunction<T, T[]>`

Buffer emitted values until `closingNotifier` emits, then emit the buffered values as one array.

```ts
const interval$ = interval(1000);

const click$ = fromEvent(document, 'click');

const buffer$ = interval$.pipe(buffer(click$));

const subscribe = buffer$.subscribe((val) =>
  console.log('Buffered Values: ', val)
);

// output examples:
'Buffered Values: '[(0, 1)];
'Buffered Values: '[(2, 3, 4, 5, 6)];
```

![RxJS buffer](assets/rxjs-buffer.png) <!-- TODO: asset -->

### bufferTime

`bufferTime<T>(bufferTimeSpan: number): OperatorFunction<T, T[]>`

Like `buffer`, but emits on a fixed time interval (`bufferTimeSpan` in ms).

```ts
const source = interval(500);

const bufferTime = source.pipe(
  bufferTime(2000)
);

const bufferTimeSub = bufferTime.subscribe(
  val => console.log('Buffered with Time:', val)
);
// output
"Buffered with Time:"
[0, 1]
"Buffered with Time:"
[2, 3]
"Buffered with Time:"
[4, 5]
...
```

![RxJS bufferTime](assets/rxjs-bufferTime.png) <!-- TODO: asset -->

## Summary

Today we covered the basics of commonly used **Transformation Operators** in RxJS. Practice with more examples on [rxjs.dev](https://rxjs.dev) to deepen your understanding.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

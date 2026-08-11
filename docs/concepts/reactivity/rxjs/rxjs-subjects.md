---
roadmap_node: "rxjs-subjects"
title: "RxJS Subjects, Multicasting, and Unsubscribe in Angular"
file: "reactivity/rxjs/rxjs-subjects.md"
source_days: [26, 45]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Subjects, Multicasting, and Unsubscribe in Angular

In the [RxJS introduction](rxjs.md) we met **Observable** and briefly mentioned **Subject**. What role does **Subject** play in RxJS — and when must you **unsubscribe** in Angular? This article covers both.

## Observable execution

For a plain **Observable**, each `subscribe` starts a new independent execution.

```ts
const observable = interval(500).pipe(take(5));

const observerA = {
  next: (val) => console.log(`Observer A: ${val}`),
  error: (err) => console.log(`Observer A Error: ${err}`),
  complete: () => console.log(`Observer A complete`),
};

observable.subscribe(observerA);

/**
Output:

Observer A: 0
Observer A: 1
Observer A: 2
Observer A: 3
Observer A: 4
Observer A complete
*/
```

Subscribe a second observer after two seconds:

```ts
const observable = interval(500).pipe(take(5));

const observerA = {
  next: (val) => console.log(`Observer A: ${val}`),
  error: (err) => console.log(`Observer A Error: ${err}`),
  complete: () => console.log(`Observer A complete`),
};

observable.subscribe(observerA);

const observerB = {
  next: (val) => console.log(`Observer B: ${val}`),
  error: (err) => console.log(`Observer B Error: ${err}`),
  complete: () => console.log(`Observer B complete`),
};

setTimeout(() => {
  observable.subscribe(observerB);
}, 2000);

/**
Output:

Observer A: 0
Observer A: 1
Observer A: 2
Observer A: 3
Observer A: 4
Observer A complete
Observer B: 0
Observer B: 1
Observer B: 2
Observer B: 3
Observer B: 4
Observer B complete
*/
```

Two subscribers, two separate executions. Can late subscribers share one execution instead?

RxJS applies the [Observer pattern](https://en.wikipedia.org/wiki/Observer_pattern):

![Observer Pattern](assets/observer-pattern.png) <!-- TODO: asset -->

A hybrid observer that fans out to many listeners:

```ts
const hybridObserver = {
  observers: [],
  registerObserver(observer) {
    this.observers.push(observer);
  },
  next(value) {
    this.observers.forEach(observer => observer.next(value));
  },
  error(err) {
    this.observers.forEach(observer => observer.error(err));
  },
  complete() {
    this.observers.forEach(observer => observer.complete());
  }
}

hybridObserver.registerObserver(observerA);

observable.subscribe(hybridObserver);

setTimeout(() => {
  hybridObserver.registerObserver(observerB);
}, 2000);

/**
Output:

Observer A: 0
Observer A: 1
Observer A: 2
Observer A: 3
Observer A: 4
Observer B: 4
Observer A complete
Observer B complete
*/
```

Rename `registerObserver` to `subscribe` and you have something that is both observable-like and observer-like — a [`Subject` in RxJS](https://rxjs.dev/api/index/class/Subject).

> A Subject is a special type of Observable that allows values to be multicasted to many Observers. Subjects are like EventEmitters.

> Every Subject is an Observable and an Observer. You can subscribe to a Subject, and you can call next to feed values as well as error and complete.

```ts
const subject = new Subject();

subject.subscribe(observerA);

observable.subscribe(subject);

setTimeout(() => {
  subject.subscribe(observerB);
}, 2000);
```

We've moved from unicast to multicast by piping the source through a `Subject`.

- **Unicast**: like watching a recorded YouTube video — each viewer starts from the beginning independently.
- **Multicast**: like a live stream — everyone sees the same moment in time.

## Subject

Because a `Subject` is both an `Observable` (you subscribe) and an `Observer` (you call `next`, `error`, `complete`), it is popular as an event bus. Typeahead example:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@Component({
  selector: 'my-app',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit {
  searchTerm$ = new Subject<string>();

  ngOnInit() {
    this.searchTerm$
      .asObservable()
      .pipe(
        throttleTime(250, undefined, {
          leading: true,
          trailing: true,
        }),
        distinctUntilChanged()
      )
      .subscribe({
        next: (value) => console.log(value),
      });
  }

  onInput(event: Event) {
    const target = event.target as HTMLInputElement;
    this.searchTerm$.next(target.value);
  }
}
```

You control when notifications fire and shape the stream with standard operators.

### BehaviorSubject

Late subscribers to a plain `Subject` miss past values — they only see emissions after they subscribe:

```ts
const subject = new Subject();

subject.subscribe({
  next: (v) => console.log('observerA: ' + v),
});

subject.next(1);
subject.next(2);

subject.subscribe({
  next: (v) => console.log('observerB: ' + v),
});

subject.next(3);

/**
Output

observerA: 1
observerA: 2
observerA: 3
observerB: 3
*/
```

**BehaviorSubject** keeps the latest value and replays it to new subscribers immediately.

> A variant of Subject that requires an initial value and emits its current value whenever it is subscribed to. [BehaviorSubject](https://rxjs.dev/api/index/class/BehaviorSubject)

> BehaviorSubjects are useful for representing "values over time". For instance, an event stream of birthdays is a Subject, but the stream of a person's age would be a BehaviorSubject.

> Use a BehaviorSubject to share the currently logged-in user across Angular components.

Note: `BehaviorSubject` requires an initial value.

```ts
const subject = new BehaviorSubject(0); // 0 is the initial value

subject.subscribe({
  next: (v) => console.log('observerA: ' + v),
});

subject.next(1);
subject.next(2);

subject.subscribe({
  next: (v) => console.log('observerB: ' + v),
});

subject.next(3);

/**
Output

observerA: 0
observerA: 1
observerA: 2
observerB: 2
observerA: 3
observerB: 3
*/
```

### ReplaySubject

Like `BehaviorSubject` for late subscribers, but can buffer multiple past values (or the whole history).

Parameters:

- `buffer`: max number of values to store
- `windowTime` (ms): max age of buffered values

> A variant of Subject that "replays" or emits old values to new subscribers. [ReplaySubject](https://rxjs.dev/api/index/class/ReplaySubject)

```ts
const subject = new ReplaySubject(3); // buffer 3 values for new subscribers

subject.subscribe({
  next: (v) => console.log('observerA: ' + v),
});

subject.next(1);
subject.next(2);
subject.next(3);
subject.next(4);

subject.subscribe({
  next: (v) => console.log('observerB: ' + v),
});

subject.next(5);

/**
Output:

observerA: 1
observerA: 2
observerA: 3
observerA: 4
observerB: 2
observerB: 3
observerB: 4
observerA: 5
observerB: 5
*/
```

With `windowTime`:

```ts
const subject = new ReplaySubject(100, 500 /* windowTime */);

subject.subscribe({
  next: (v) => console.log('observerA: ' + v),
});

let i = 1;
const id = setInterval(() => subject.next(i++), 200);

setTimeout(() => {
  subject.subscribe({
    next: (v) => console.log('observerB: ' + v),
  });
}, 1000);

setTimeout(() => {
  subject.complete();
  clearInterval(id);
}, 2000);
```

After 1s, only values 3, 4, and 5 fall within the last 500ms and fit the buffer, so `observerB` replays those.

### AsyncSubject

Emits only the **last** value when the execution **complete**s — similar to a `Promise`.

> A variant of Subject that only emits a value when it completes. [AsyncSubject](https://rxjs.dev/api/index/class/AsyncSubject)

> If the stream never completes, nothing is emitted.

```ts
const subject = new AsyncSubject();

subject.subscribe({
  next: (v) => console.log('observerA: ' + v),
});

subject.next(1);
subject.next(2);
subject.next(3);
subject.next(4);

subject.subscribe({
  next: (v) => console.log('observerB: ' + v),
});

subject.next(5);
subject.complete();

/**
Output:

observerA: 5
observerB: 5
*/
```

### Subject completion

- **BehaviorSubject**: after complete, late subscribers only get the complete signal.
- **ReplaySubject**: late subscribers receive buffered values, then complete.
- **AsyncSubject**: even after complete, new subscribers can still receive the final value.

## Multicasting operators

To share one execution across subscribers without manual wiring:

```ts
const observable = interval(500).pipe(take(5));

const subject = new Subject();

const observerA = {
  next: (val) => console.log(`Observer A: ${val}`),
  error: (err) => console.log(`Observer A Error: ${err}`),
  complete: () => console.log(`Observer A complete`),
};

const observerB = {
  next: (val) => console.log(`Observer B: ${val}`),
  error: (err) => console.log(`Observer B Error: ${err}`),
  complete: () => console.log(`Observer B complete`),
};

subject.subscribe(observerA);

observable.subscribe(subject);

setTimeout(() => {
  subject.subscribe(observerB);
}, 2000);
```

Or use multicasting operators.

### multicast

`multicast<T, R>(subjectOrSubjectFactory: Subject<T> | (() => Subject<T>), selector?: (source: Observable<T>) => Observable<R>): OperatorFunction<T, R>`

> Returns an Observable that emits the results of invoking a specified selector on items emitted by a ConnectableObservable that shares a single subscription to the underlying stream. [multicast](https://rxjs.dev/api/operators/multicast)

Returns a [`ConnectableObservable`](https://rxjs.dev/api/index/class/ConnectableObservable) that shares one subscription.

```ts
const subject = new Subject();

const connectableObservable = interval(500).pipe(
  take(5),
  multicast(subject)
) as ConnectableObservable<number>;

connectableObservable.subscribe(observerA);
connectableObservable.connect();

setTimeout(() => {
  connectableObservable.subscribe(observerB);
}, 2000);
```

`connect()` starts the shared source — equivalent to `observable.subscribe(subject)`. Without `disconnect`, you risk memory leaks; store the subscription from `connect()` and `unsubscribe()` when done.

#### refCount

`refCount()` auto-connects when subscriber count goes from 0 → 1 and disconnects at 1 → 0.

### SubjectFactory

A completed `Subject` cannot accept more values. If you need a fresh multicast after completion, pass a factory:

```ts
multicast(() => new Subject())
```

### publish

Shorthand for `multicast(new Subject())`. Variants: `publishBehavior`, `publishReplay`, `publishLast`.

### share

Alias for `multicast(() => new Subject()), refCount()` — very common.

![RxJS share](assets/rxjs-share.png) <!-- TODO: asset -->

### shareReplay

> Share source and replay specified number of emissions on subscription.

Use when you have side effects or expensive work you do not want duplicated per subscriber, or when late subscribers need prior values. Popular for [HTTP caching](https://blog.thoughtram.io/angular/2018/03/05/advanced-caching-with-rxjs.html).

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs/Observable';
import { Subject } from 'rxjs/Subject';
import { timer } from 'rxjs/observable/timer';
import { switchMap, shareReplay, map, takeUntil } from 'rxjs/operators';

export interface Joke {
  id: number;
  joke: string;
  categories: Array<string>;
}

export interface JokeResponse {
  type: string;
  value: Array<Joke>;
}

const API_ENDPOINT = 'https://api.icndb.com/jokes/random/5?limitTo=[nerdy]';
const REFRESH_INTERVAL = 10000;
const CACHE_SIZE = 1;

@Injectable()
export class JokeService {
  private cache$: Observable<Array<Joke>>;
  private reload$ = new Subject<void>();

  constructor(private http: HttpClient) {}

  get jokes() {
    if (!this.cache$) {
      const timer$ = timer(0, REFRESH_INTERVAL);

      this.cache$ = timer$.pipe(
        switchMap(() => this.requestJokes()),
        takeUntil(this.reload$),
        shareReplay(CACHE_SIZE)
      );
    }

    return this.cache$;
  }

  forceReload() {
    this.reload$.next();
    this.cache$ = null;
  }

  private requestJokes() {
    return this.http
      .get<JokeResponse>(API_ENDPOINT)
      .pipe(map((response) => response.value));
  }
}
```

## When to unsubscribe in Angular

Working with Angular, you may wonder: when do I need to `unsubscribe`? Why is it fine in some places but not others? Can we avoid boilerplate?

### Angular EventEmitter

`EventEmitter` currently extends `Subject`. You can subscribe to `@Output()` manually or use event binding in templates. **Template event binding unsubscribes for you.** Manual subscriptions need cleanup.

### Subject inside a component

Simple case — subscribe directly to a component-scoped `Subject` with no long-lived inner streams:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { Component, OnInit } from '@angular/core';
import { Subject } from 'rxjs';

@Component({
  selector: 'app-product',
  templateUrl: './product.component.html',
  styleUrls: ['./product.component.scss']
})
export class ProductComponent implements OnInit {
  grandTotal$ = new Subject<number>();
  constructor() { }

  ngOnInit(): void {
    this.grandTotal$.subscribe({
      next: grandTotal => {
        console.log(grandTotal);
      }
    });
  }

  calculate(): void {
    this.grandTotal$.next(Math.random() * 1000);
  }
}
```

No `unsubscribe` needed — when the component is destroyed, `grandTotal$` is collected with it.

![Product Component Memory 1](./assets/day-45-heap-snapshot-1.png) <!-- TODO: asset -->
![Product Component Memory 2](./assets/day-45-heap-snapshot-2.png) <!-- TODO: asset -->

With operators that spawn non-finishing inner streams:

```ts
import { Component, OnInit } from '@angular/core';
import { interval, Subject } from 'rxjs';
import { mergeMap, scan } from 'rxjs/operators';

@Component({
  selector: 'app-product',
  templateUrl: './product.component.html',
  styleUrls: ['./product.component.scss']
})
export class ProductComponent implements OnInit {
  grandTotal$ = new Subject<number>();
  constructor() { }

  ngOnInit(): void {
    this.grandTotal$.pipe(
      mergeMap(total => interval(1000).pipe(
        scan((acc, value) => acc + value, total),
      )),
    ).subscribe({
      next: grandTotal => {
        console.log(grandTotal);
      }
    });
  }
}
```

The inner `interval` keeps running after destroy — **memory leak**. **Unsubscribe streams that can outlive the component.**

```ts
export class ProductComponent implements OnInit, OnDestroy {
  grandTotal$ = new Subject<number>();
  subscription = Subscription.EMPTY;
  constructor() { }

  ngOnInit(): void {
    this.subscription = this.grandTotal$.pipe(
      mergeMap(total => interval(1000).pipe(
        scan((acc, value) => acc + value, total),
      )),
    ).subscribe({
      next: grandTotal => {
        console.log(grandTotal);
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}
```

![Product Component Memory 3](./assets/day-45-heap-snapshot-3.png) <!-- TODO: asset -->
![Product Component Memory 4](./assets/day-45-heap-snapshot-4.png) <!-- TODO: asset -->

### ActivatedRoute

`ActivatedRoute` is created per component and exposes `paramMap`, `queryParamMap`, etc. A plain subscribe without long-lived derived streams can rely on GC — same as the simple `Subject` case.

Usually you `switchMap` into HTTP or WebSocket work — then unsubscribe like the second `Subject` example:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
export class ProductComponent implements OnInit, OnDestroy {
  subscription = Subscription.EMPTY;

  constructor(private activatedRouter: ActivatedRoute) {
  }

  ngOnInit(): void {
    this.subscription = this.activatedRouter.queryParamMap.pipe(
      mergeMap(query => {
        console.log(query);
        return interval(1000);
      })
    ).subscribe({
      next: data => {
        console.log(data);
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }
}
```

### Subscribing to a singleton service

A root-scoped service outlives any component. Subscribing without unsubscribing leaves callbacks alive:

```ts
@Injectable({
  providedIn: 'root'
})
export class CartService {
  private _cart$ = new BehaviorSubject<CartItem[]>([]);
  cart$ = this._cart$.asObservable();
  // ...
}
```

```ts
export class ProductComponent implements OnInit, OnDestroy {
  constructor(private cartService: CartService) { }

  ngOnInit(): void {
    this.cartService.cart$.subscribe(new ProductCartSubscriber());
  }
}
```

After destroy, `next` still runs when `cart$` emits.

![Product Component Memory 5](./assets/day-45-heap-snapshot-5.png) <!-- TODO: asset -->
![Product Component Memory 6](./assets/day-45-heap-snapshot-6.png) <!-- TODO: asset -->

Unsubscribe in `ngOnDestroy` when the service lifecycle differs from the component.

### Does HttpClient need unsubscribe?

`HttpClient` typically emits once then `complete`s. A direct subscribe without operators that never finish usually needs no manual cleanup. When in doubt, unsubscribe.

### Avoiding manual unsubscribe

**AsyncPipe** in templates subscribes and unsubscribes for you. Use it only in templates; multiple `async` pipes on the same stream create multiple subscriptions.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div *ngIf="stream$ | async as stream">
  Do something with stream here, e.g. {{stream.body}}
</div>
```

**takeUntil** with a destroy notifier — always place `takeUntil` **last** in the pipe:

```ts
export class ProductComponent implements OnInit, OnDestroy {
  destroyed$ = new Subject<void>();
  constructor(private cartService: CartService) { }

  ngOnInit(): void {
    this.cartService.cart$.pipe(
      takeUntil(this.destroyed$),
    ).subscribe(new ProductCartSubscriber());
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
```

A component-scoped **DestroyService** avoids repeating the `Subject` boilerplate:

```ts
import { Injectable, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable()
export class DestroyService implements OnDestroy {
  public destroyed$ = new Subject<void>();
  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}

@Component({
  selector: 'app-product',
  templateUrl: './product.component.html',
  styleUrls: ['./product.component.scss'],
  providers: [DestroyService],
})
export class ProductComponent implements OnInit {
  constructor(
    private cartService: CartService,
    private destroy: DestroyService,
  ) { }

  ngOnInit(): void {
    this.cartService.cart$.pipe(
      takeUntil(this.destroy.destroyed$),
    ).subscribe(new ProductCartSubscriber());
  }
}
```

## Summary

We've covered **Subject** variants, multicasting (`share`, `shareReplay`, `multicast`, `publish`), and practical **unsubscribe** rules in Angular: component-scoped vs singleton services, `HttpClient`, `AsyncPipe`, and `takeUntil`. These ideas apply beyond Angular anywhere Reactive Extensions are used.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)
- [rxmarbles](https://rxmarbles.com/)
- [RxJS Subject — Tiep Phan (Vietnamese)](https://www.tiepphan.com/rxjs-reactive-programming/#rxjs-subject)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

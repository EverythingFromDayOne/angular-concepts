---
roadmap_node: "rxjs-higher-order"
title: "RxJS Higher-Order Observables and Utility Operators"
file: "reactivity/rxjs/rxjs-higher-order.md"
source_days: [25]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Higher-Order Observables and Utility Operators

We've covered most of the **operators** you're likely to use in **Angular** — just a few categories left. Today we'll look at two of the last three: **RxJS Higher-Order Observables** and **Utility Operators**.

> The remaining category is **Multicasting Operators**, covered in [RxJS Subjects and Multicasting](rxjs-subjects.md).

## RxJS higher-order observables (HOOs)

**HOOs** take a value from an **outer Observable** (the **source**) and return a different **inner Observable** (the **destination**). We already met `map()` as a **transformation operator**:

```ts
interval(1000)
  .pipe(map((val) => val * 2))
  .suscribe(console.log);
// output: 0 -- 2 -- 4 -- 6 -- 8
```

`map()` transforms `0, 1, 2, 3, 4...` into `0, 2, 4, 6, 8...`. **HOOs** are transformation operators too, but instead of mapping to a new **value**, they map to a new **Observable** you subscribe to for the actual emissions.

#### Where HOOs come from

Before the named HOOs, understand `mergeAll()`, `concatAll()`, and `switchAll()`. `map()` turns each source value into something new. What if that something is an `Observable`?

```ts
fromEvent(document, 'click')
  .pipe(map(() => interval(1000)))
  .subscribe(console.log);
// Click
// output: Observable {}
// Click
// output: Observable {}
```

Each click gives you an `Observable {}` on the console because `map()` returned `interval(1000)` — a **higher-order Observable** (`Observable<Observable>`). Every click starts a new `interval()`. Pipe one of `mergeAll`, `switchAll`, or `concatAll` to flatten back to a first-order stream:

```ts
const source = fromEvent(document, 'click').pipe(map(() => interval(1000)));

source.pipe(mergeAll()).subscribe(console.log);
source.pipe(switchAll()).subscribe(console.log);
source.pipe(concatAll()).subscribe(console.log);
```

In short: **higher-order Observables** are `merge/switch/concatAll + map()`. How they differ mirrors `merge`, `switch`, and `concat`.

#### Why HOOs matter

```ts
this.queryInput.valueChanges.pipe(debounceTime(500)).subscribe((query) => {
  this.apiService.filterData(query).subscribe((data) => {
    /*...*/
  });
});
```

Classic search box: listen to `valueChanges`, call the API with the new `query`. Something is wrong here — **nested subscription** (subscribe inside subscribe), one of the most common RxJS mistakes.

Why is it bad? `Observable`s do nothing until subscribed. Nested subscriptions run two independent streams. Walk through it:

1. User types `"abc"` and pauses.
2. After 500ms (`debounceTime`), `valueChanges` emits `abc`.
3. You call `apiService.filterData(query)` and subscribe again.
4. Eventually the API returns `data` and you update the template.

That works until:

5. User deletes `abc` and types `xyz` within 500ms, stopping on `xyz`.
6–7. Steps 2–3 repeat for `xyz` — call this **{1}**.
8. Much later, user changes the query to `abcxyz`.
9. After 500ms you call the API again — **{2}**.
10. **{1}** finishes first and shows data for `xyz` while the input already says `abcxyz` — a serious **race condition**.

Nested subscriptions can't coordinate sibling streams. The fix is to learn and use **HOOs**.

#### switchMap()

`switchMap<T, R, O extends ObservableInput<any>>(project: (value: T, index: number) => O, resultSelector?: (outerValue: T, innerValue: ObservedValueOf<O>, outerIndex: number, innerIndex: number) => R): OperatorFunction<T, ObservedValueOf<O> | R>`

`switchMap()` is among the most used HOOs in **RxJS** and **Angular**. It takes a `project` function: outer value in, inner `Observable` out. The outer stream's emissions are whatever the active inner emits. When a new inner arrives, `switchMap()` **unsubscribes** from the previous inner — only one inner subscription at a time.

![RxJS switchMap](assets/rxjs-switchMap.png) <!-- TODO: asset -->

```ts
fromEvent(document, 'click').pipe(
  switchMap(() => interval(1000).pipe(take(10)))
);
```

- `fromEvent(document, 'click')`: emits on each document click.
- `interval(1000).pipe(take(10))`: fake 10-second request; `interval` lets us watch ticks.
- Each click returns a new inner; `switchMap` subscribes to it and cancels the prior inner if still running.

Applied to the search box:

```ts
this.queryInput.valueChanges
  .pipe(
    debounceTime(500),
    switchMap((query) => this.apiService.filterData(query))
  )
  .subscribe((data) => {
    /*...*/
  });
```

Each new `query` cancels the in-flight `filterData` call — stale results are dropped.

##### Note

`switchMap` is `switchAll + map`, but that equivalence breaks with **non-cancellable** `Promise`s — `switchAll` cannot cancel an in-flight HTTP `Promise`. For Angular `HttpClient`, prefer `switchMap` for **read** operations; for create/update/delete consider `mergeMap` or `concatMap` to avoid dropped writes.

#### mergeMap()

`mergeMap<T, R, O extends ObservableInput<any>>(project: (value: T, index: number) => O, resultSelector?: number | ((outerValue: T, innerValue: ObservedValueOf<O>, outerIndex: number, innerIndex: number) => R), concurrent: number = Number.POSITIVE_INFINITY): OperatorFunction<T, ObservedValueOf<O> | R>`

Second most common HOO. Unlike `switchMap()`, `mergeMap()` keeps **all** inner subscriptions alive — good for **writes** where you must not cancel in-flight work.

![RxJS mergeMap](assets/rxjs-mergeMap.png) <!-- TODO: asset -->

```ts
fromEvent(document, 'click').pipe(
  mergeMap(() => interval(1000).pipe(take(10)))
);

// Click, subscribe {1}
// {1}: 0 -- 1 -- 2 -- 3 -- 4
// Click, subscribe {2}
// {1}: 5 -- 6 -- 7 -- 8
// {2}: 0 -- 1 -- 2 -- 3
// ...
```

Many concurrent inners can mean **memory leaks** if you're not careful. `concurrent` limits how many inners run at once; `concurrent = 1` behaves like `concatMap`.

#### concatMap()

`concatMap<T, R, O extends ObservableInput<any>>(project: (value: T, index: number) => O, resultSelector?: (outerValue: T, innerValue: ObservedValueOf<O>, outerIndex: number, innerIndex: number) => R): OperatorFunction<T, ObservedValueOf<O> | R>`

Waits for each inner to **complete** before subscribing to the next — preserves **order**. Great for traffic lights, queue tickets, or ordered uploads:

```ts
from([image1, image2, image3]).pipe(
  // image1, image2, and image3 are File objects
  concatMap((singleImage) => this.apiService.upload(singleImage))
);
```

```ts
fromEvent(document, 'click').pipe(
  concatMap(() => interval(1000).pipe(take(5)))
);
// Clicks while {1} runs are queued until {1} completes
```

![RxJS concatMap](assets/rxjs-concatMap.png) <!-- TODO: asset -->

##### Note

`concatMap = concatAll + map` fails with eager **Promises** — `axios(...)` inside `map()` fires immediately, so `concatAll` cannot serialize requests:

```ts
fromEvent(document, 'click').pipe(
  map(() => axios('...')),
  concatAll()
);
```

#### exhaustMap()

`exhaustMap<T, R, O extends ObservableInput<any>>(project: (value: T, index: number) => O, resultSelector?: (outerValue: T, innerValue: ObservedValueOf<O>, outerIndex: number, innerIndex: number) => R): OperatorFunction<T, ObservedValueOf<O> | R>`

While an inner is active, **ignore** new outer values until that inner completes — like `throttle` for streams. Useful for "ignore clicks while request is in flight."

![RxJS exhaustMap](assets/rxjs-exhaustMap.png) <!-- TODO: asset -->

```ts
function log(val) {
  console.log(val + ' emitted!!!');
  console.log('-----------------');
}

concat(
  timer(1000).pipe(mapTo('first timer'), tap(log)),
  timer(5000).pipe(mapTo('second timer'), tap(log)),
  timer(3000).pipe(mapTo('last timer'), tap(log))
)
  .pipe(
    exhaustMap((c) =>
      interval(1000).pipe(
        map((v) => `${c}: ${v}`),
        take(4)
      )
    )
  )
  .subscribe(console.log);
// "last timer" is ignored while "second timer" inner is still running
```

#### switch / concat / mergeMapTo()

When you don't need the outer value, pass the inner `Observable` directly:

```ts
fromEvent(document, 'click').pipe(switchMapTo(interval(1000).pipe(take(10))));

fromEvent(document, 'click').pipe(mergeMapTo(interval(1000).pipe(take(10))));

fromEvent(document, 'click').pipe(concatMapTo(interval(1000).pipe(take(10))));
```

#### partition()

`partition<T>(source: any, predicate: (value: T, index: number) => boolean, thisArg?: any): [Observable<T>, Observable<T>]`

Not quite an HOO — a higher-order **function** — but it splits one source into two `Observable`s by `predicate`: matching vs non-matching.

![RxJS partition](assets/rxjs-partition.png) <!-- TODO: asset -->

```ts
const [even$, odd$] = partition(interval(1000), (x) => x % 2 === 1);
merge(
  evens$.pipe(map((x) => `even - ${x}`)),
  odds$.pipe(map((x) => `odd - ${x}`))
).subscribe(console.log);
```

Handy for splitting a WebSocket notification feed into `readNotification$` and `unreadNotification$`.

Other HOOs include `expand()`, `groupBy()`, and `mergeScan()` — less common in everyday Angular work.

## Utility operators

Helpers that are sometimes exactly what you need.

#### tap()

`tap<T>(nextOrObserver?: NextObserver<T> | ErrorObserver<T> | CompletionObserver<T> | ((x: T) => void), error?: (e: any) => void, complete?: () => void): MonoTypeOperatorFunction<T>`

Besides `subscribe`, `tap()` is probably the most used operator. It mirrors `subscribe`'s observer shape but does not change the stream — ideal for logging, side effects, or toggling loaders without altering emissions.

```ts
interval(1000)
  .pipe(
    tap((val) => console.log('before map', val)),
    map((val) => val * 2),
    tap((val) => console.log('after map', val))
  )
  .subscribe();
```

#### delay() / delayWhen()

`delay<T>(delay: number | Date, scheduler: SchedulerLike = async): MonoTypeOperatorFunction<T>`

Delays each emission by a duration or until a `Date`.

![RxJS delay](assets/rxjs-delay.png) <!-- TODO: asset -->

```ts
fromEvent(document, 'click').pipe(delay(1000)).subscribe(console.log);
```

`delayWhen()` uses a per-value `Observable` instead of a fixed delay.

![RxJS delayWhen](assets/rxjs-delayWhen.png) <!-- TODO: asset -->

#### finalize()

`finalize<T>(callback: () => void): MonoTypeOperatorFunction<T>`

Runs `callback` on complete **or** error — perfect for stopping spinners either way.

```ts
this.loading = true;
this.apiService
  .get()
  .pipe(finalize(() => (this.loading = false)))
  .subscribe();
```

#### repeat()

`repeat<T>(count: number = -1): MonoTypeOperatorFunction<T>`

Re-subscribes to the source when it completes, up to `count` times.

![RxJS repeat](assets/rxjs-repeat.png) <!-- TODO: asset -->

```ts
of('repeated data').pipe(repeat(3)).subscribe(console.log);
```

#### timeInterval()

`timeInterval<T>(scheduler: SchedulerLike = async): OperatorFunction<T, TimeInterval<T>>`

Measures elapsed time between emissions — e.g. time between clicks.

![RxJS timeInterval](assets/rxjs-timeInterval.png) <!-- TODO: asset -->

#### timeout()

`timeout<T>(due: number | Date, scheduler: SchedulerLike = async): MonoTypeOperatorFunction<T>`

Throws if no emission occurs within `due` (number) or before `due` (Date).

![RxJS timeout](assets/rxjs-timeout.png) <!-- TODO: asset -->

```ts
interval(2000).pipe(timeout(1000)).subscribe(console.log, console.error);
// Error { name: "TimeoutError" }
```

#### timeoutWith()

`timeoutWith<T, R>(due: number | Date, withObservable: any, scheduler: SchedulerLike = async): OperatorFunction<T, T | R>`

Like `timeout()` but switches to a fallback `Observable` instead of erroring.

![RxJS timeoutWith](assets/rxjs-timeoutWith.png) <!-- TODO: asset -->

#### toPromise()

Saved for last on purpose. `toPromise()` is an `Observable` instance method that converts a stream to a `Promise`. It was **deprecated** in **RxJS v7** — use `firstValueFrom` / `lastValueFrom` in modern code (upgrade pass will cover that).

```ts
async function test() {
  const helloWorld = await of('hello')
    .pipe(map((val) => val + ' World'))
    .toPromise();
  console.log(helloWorld); // hello World
}
```

Among utilities, `tap()` wins for day-to-day debugging.

## Summary

Today's operators are among the most important in **RxJS** and **Angular** for orchestrating async flows. Get truly comfortable with `switchMap`, `concatMap`, `mergeMap`, and `exhaustMap` — your Angular journey gets much easier.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)

## Author

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

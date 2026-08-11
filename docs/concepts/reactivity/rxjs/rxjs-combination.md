---
roadmap_node: "rxjs-combination"
title: "RxJS Combination Operators"
file: "reactivity/rxjs/rxjs-combination.md"
source_days: [23]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Combination Operators

Let's continue exploring **RxJS** operators. This time we'll look at operators that let you combine multiple `Observable`s — **Combination Operators**. They matter a lot in **Angular** work.

```ts
const observer = {
  next: (val) => console.log(val),
  error: (err) => console.log(err),
  complete: () => console.log('complete'),
};
```

### forkJoin()

`forkJoin(...sources: any[]): Observable<any>`

If you're familiar with `Promise.all()`, `forkJoin()` will feel very similar.

`forkJoin()` accepts a list of child `Observable`s as an array or as a dictionary (object). When **all** children **complete**, `forkJoin()` emits their final values as an array or dictionary (matching the input shape), then **complete**s.

![RxJS forkJoin](assets/rxjs-forkJoin.png) <!-- TODO: asset -->

```ts
forkJoin([of(1), of('hello'), of({ foo: 'bar' })]).subscribe(observer);
// output: [1, 'hello', {foo: 'bar'}]
// output: 'complete'

forkJoin({ one: of(1), hello: of('hello'), foo: of({ foo: 'bar' }) }).subscribe(
  observer
);
/**
 * output:
 * {
 *   one: 1,
 *   hello: 'hello',
 *   foo: { foo: 'bar' }
 * }
 * output: 'complete'
 */
```

#### Note

- `forkJoin()` only emits when all children complete. If any child never completes, `forkJoin()` never emits.
- `forkJoin()` errors if any child errors; values from siblings that already completed may be lost unless you handle errors carefully.

#### Use case

`forkJoin()` is widely used in **Angular** apps — especially when you need several dropdown/select lists at once.

```ts
forkJoin([
  this.apiService.getAccountDropdown(),
  this.apiService.getDepartmentDropdown(),
  this.apiService.getStoreDropdown(),
]).subscribe(observer);
// output: [accountList, departmentList, storeList]
// output: 'complete'
```

When children are passed as an array, `forkJoin()` can take a second argument: a `projectFunction`. It receives each child's final value; its return value is what `forkJoin()` emits. The function runs only when `forkJoin()` is about to emit (all children completed).

```ts
forkJoin(
  [
    this.apiService.getAccountDropdown(),
    this.apiService.getDepartmentDropdown(),
    this.apiService.getStoreDropdown(),
  ],
  (accountList, departmentList, storeList) => {
    return {
      accounts: accountList,
      departments: departmentList,
      stores: storeList,
    };
  }
).subscribe(observer);
// output: { accounts: [...], departments: [...], stores: [...] }
// output: 'complete'
```

### combineLatest()

`combineLatest<O extends ObservableInput<any>, R>(...observables: (SchedulerLike | O | ((...values: ObservedValueOf<O>[]) => R))[]): Observable<R>`

Like `forkJoin()`, `combineLatest()` accepts an array of `Observable`s. Unlike `forkJoin()`, it does not accept a dictionary, and it emits when **every** child has emitted at least once — children do not need to complete. Each emission is an array of the latest value from each child, in order.

> You can write `combineLatest(obs1, obs2)` without `[]`, but **RxJS** recommends `combineLatest([obs1, obs2])` for consistency with `forkJoin()` and predictable array results. This article uses only the array form.

![RxJS combineLatest](assets/rxjs-combineLatest.png) <!-- TODO: asset -->

```ts
combineLatest([
  interval(2000).pipe(map((x) => `First: ${x}`)), // {1}
  interval(1000).pipe(map((x) => `Second: ${x}`)), // {2}
  interval(3000).pipe(map((x) => `Third: ${x}`)), // {3}
]).subscribe(observer);

// output:
// after 3s (interval(3000) is slowest):
// [First 0, Second 2, Third 0] -- at 3s, {2} has emitted 3 times (0, 1, 2)

// after 1 more second (second 4):
// [First 1, Second 2, Third 0] -- at 4s, {1} has emitted twice (0, 1)
// [First 1, Second 3, Third 0] -- at 4s, {2} emits a fourth time (3)

// after 1 more second (second 5):
// [First 1, Second 4, Third 0] -- {2} emits a fifth time

// after 1 more second (second 6):
// [First 2, Second 4, Third 0] -- {1} emits a third time
// [First 2, Second 5, Third 0] -- {2} emits a sixth time
// [First 2, Second 5, Third 1] -- {3} emits a second time
```

#### Note

- After the first combined emission, each new child emission produces a new array: the fresh value from the emitting child plus the latest values from the others.
- In the example, child **{2}** (`interval(1000)`) "loses" its first two values (`0` and `1`) because it ticks faster than the slowest child **{3}**. Watch for **race conditions** like this.
- `combineLatest()` completes when all children complete.
- If any child never completes, `combineLatest()` never completes.
- `combineLatest()` errors if any child errors; other emitted values may be lost (same as `forkJoin()`).

#### Use case

Very common for combining state in **Angular** services. Because streams are often long-lived, `combineLatest()` pairs well with `AsyncPipe` in templates.

```ts
this.vm$ = combineLatest([
  this.paginationService.currentPage$,
  this.paginationService.currentSize$,
  this.paginationService.totalCount$,
  this.paginationService.currentOffset$,
]).pipe(
  map((currentPage, currentSize, totalCount, currentOffset) => {
    return {
      currentPage,
      currentSize,
      totalCount,
      currentOffset,
    };
  })
);

onSizeChanged(newSize: number) {
  this.paginationService.updateSize(newSize);
}

onPageChanged(newPage: number) {
  this.paginationService.updatePage(newPage);
}
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ng-container *ngIf="vm$ | async as vm">
  <app-show-total
    [offset]="vm.currentOffset"
    [total]="vm.totalCount"
    [size]="vm.currentSize"
  ></app-show-total>
  <!-- Display: 1 - 20 of 100 -->
  <app-paginator
    [current]="vm.currentPage"
    [total]="vm.totalCount"
    [size]="vm.currentSize"
    (sizeChanged)="onSizeChanged($event)"
    (pageChanged)="onPageChanged($event)"
  ></app-paginator>
</ng-container>
```

This is a solid pagination example using `combineLatest()` and `AsyncPipe`. When `updateSize()` or `updatePage()` runs, the relevant streams emit, `vm$` emits a new value, and the template updates via `vm$ | async`.

Like `forkJoin()`, `combineLatest()` supports a `projectFunction` as the last argument when using the array form — another reason to prefer `combineLatest([obs1, obs2])`:

```ts
this.vm$ = combineLatest(
  [
    this.paginationService.currentPage$,
    this.paginationService.currentSize$,
    this.paginationService.totalCount$,
    this.paginationService.currentOffset$,
  ],
  (currentPage, currentSize, totalCount, currentOffset) => {
    return {
      currentPage,
      currentSize,
      totalCount,
      currentOffset,
    };
  }
);
```

### zip()

`zip<O extends ObservableInput<any>, R>(...observables: (O | ((...values: ObservedValueOf<O>[]) => R))[]): Observable<ObservedValueOf<O>[] | R>`

`zip()` accepts child `Observable`s (and an optional trailing function). It pairs values by index across streams.

Example: `obs1` emits `1, 2, 3`; `obs2` emits `4, 5, 6`; `obs3` emits `7, 8, 9`.

With `combineLatest()`:

```ts
combineLatest(of(1, 2, 3), of(4, 5, 6), of(7, 8, 9)).subscribe(observer);
// [1, 4, 7], // all three have emitted
// [2, 4, 7], // obs1 emits 2; combineLatest pairs 2 with stale 4 and 7
// ...
// [3, 6, 9]
```

With `zip`:

```ts
zip(of(1, 2, 3), of(4, 5, 6), of(7, 8, 9)).subscribe(observer);
// [1, 4, 7];
// [2, 5, 8];
// [3, 6, 9];
```

- `zip()` completes when **any** child completes — you only get paired values while all streams still have values.

```ts
zip(of(1, 2, 3, 99), of(4, 5, 6), of(7, 8, 9)).subscribe(observer);
// [1, 4, 7];
// [2, 5, 8];
// [3, 6, 9];
// 99 from the first observable is dropped because the second and third already completed.
```

- `zip()` errors if any child errors.
- If the last argument is a function, it is treated as a `projectFunction` (same pattern as `combineLatest()` and `forkJoin()`).

#### Use case

`zip()` shines when:

- Final values must come from several `Observable`s in lockstep:

```ts
const age$ = of<number>(29, 28, 30);
const name$ = of<string>('Chau', 'Trung', 'Tiep');
const isAdmin$ = of<boolean>(true, false, true);

zip(age$, name$, isAdmin$).pipe(
  map(([age, name, isAdmin]) => ({ age, name, isAdmin }))
);
// output:
// { age: 29, name: 'Chau', isAdmin: true }
// { age: 28, name: 'Trung', isAdmin: false }
// { age: 30, name: 'Tiep', isAdmin: true }

// with projectFunction
zip(age$, name$, isAdmin$, (age, name, isAdmin) => ({
  age,
  name,
  isAdmin,
})).subscribe(observer);
```

- Pairing values from two `Observable`s at different moments — e.g. mouse coordinates from `mousedown` to `mouseup`:

```ts
const log = (event, val) => `${event}: ${JSON.stringify(val)}`;
const getCoords = pipe(
  map((e: MouseEvent) => ({ x: e.clientX, y: e.clientY }))
);
const documentEvent = (eventName) =>
  fromEvent(document, eventName).pipe(getCoords);

zip(documentEvent('mousedown'), documentEvent('mouseup')).subscribe((e) =>
  console.log(`${log('start', e[0])} ${log('end', e[1])}`)
);
// output:
// start: {"x":291,"y":136} end: {"x":143,"y":168}
// start: {"x":33,"y":284} end: {"x":503,"y":74}
```

### concat()

`concat<O extends ObservableInput<any>, R>(...observables: (SchedulerLike | O)[]): Observable<ObservedValueOf<O> | R>`

`concat()` takes child `Observable`s as rest arguments (not a single array). It subscribes to children **in order** and emits when the active child `{1}` completes.

- If **{1}** emits and completes, `concat()` forwards those values, then subscribes to the next child.
- If **{1}** errors, `concat()` errors immediately and skips remaining children.
- If **{1}** completes without emitting, `concat()` moves to the next child.
- If **{1}** emits but never completes, `concat()` forwards emissions but never subscribes to the next child.

This repeats for each child until none remain, then `concat()` completes.

![RxJS concat](assets/rxjs-concat.png) <!-- TODO: asset -->

```ts
concat(of(4, 5, 6).pipe(delay(1000)), of(1, 2, 3)).subscribe(observer);
// output:
// after 1s:
// 4-5-6-1-2-3
// output: 'complete'
```

`concat()` waits for `of(4, 5, 6).pipe(delay(1000))` to finish before subscribing to `of(1, 2, 3)`.

You can pass the same `Observable` multiple times:

```ts
const fiveSecondTimer = interval(1000).pipe(take(5));

concat(fiveSecondTimer, fiveSecondTimer, fiveSecondTimer).subscribe(observer);
// output: 0,1,2,3,4 - 0,1,2,3,4 - 0,1,2,3,4
// output: 'complete'

// using repeat()
concat(fiveSecondTimer.pipe(repeat(3))).subscribe(observer);
// output: 0,1,2,3,4 - 0,1,2,3,4 - 0,1,2,3,4
// output: 'complete'
```

### merge()

`merge<T, R>(...observables: any[]): Observable<R>`

`merge()` takes rest arguments `...(Observable | number)`. Unlike `concat()`, order of completion does not gate subscription — children can emit in parallel. If the last argument is a `number`, it sets `concurrent`: how many children `merge()` subscribes to at once. Default: all children concurrently.

`merge()`:

- emits whenever any child emits
- errors if any child errors
- completes when all children complete

![RxJS merge](assets/rxjs-merge.png) <!-- TODO: asset -->

```ts
merge(of(4, 5, 6).pipe(delay(1000)), of(1, 2, 3)).subscribe(observer);
// output:
// 1,2,3
// after 1s: 4,5,6
// output: 'complete'
```

Unlike `concat()`, `merge()` emits `1,2,3` immediately, then `4,5,6` — order of arguments does not serialize emissions.

```ts
merge(
  interval(2000).pipe(mapTo('emit every 2 seconds'), take(3)),
  interval(1000).pipe(mapTo('emit every 1 second'), take(3))
).subscribe(observer);

// output:
// (after 1s):
// emit every 1 second
// (after 2s):
// emit every 2 seconds
// emit every 1 second
// (after 3s):
// emit every 1 second - completes (take(3))
// (after 4s):
// emit every 2 seconds
// (after 6s):
// emit every 2 seconds - completes (take(3))
// output: 'complete'
```

With `concurrent`:

```ts
merge(
  interval(1000).pipe(mapTo('first'), take(5)), // will take 5 seconds to complete
  interval(2000).pipe(mapTo('second'), take(3)), // will take 6 seconds to complete
  interval(3000).pipe(mapTo('third'), take(2)), // will take 6 seconds to complete
  2
).subscribe(observer);

// With concurrent = 2, only first and second subscribe until first completes; then third starts.
```

In practice, `concat()` is `merge()` with `concurrent` set to `1`.

#### Use case

In **Angular**, `merge()` is handy when a `FormGroup` has several `FormControl.valueChanges` streams and you want to react to any change without caring which control fired first:

```ts
const formControlValueChanges = Object.keys(this.formGroup.value).map((key) =>
  this.formGroup.get(key).valueChanges.pipe(map((value) => ({ key, value })))
); // e.g. from {firstName: 'Chau', lastName: 'Tran'} -> [Observable<{key, value}>, ...]
merge(...formControlValueChanges).subscribe(({key, value}) => {
  if (key === 'firstName') {...};
  if (key === 'lastName') {...};
});
```

### race()

`race<T>(...observables: any[]): Observable<T>`

`race()` shares the same argument shape as `merge()` and `concat()`.

- Emits values from whichever child emits first, repeating until one child completes.
- Errors immediately if the fastest child errors instead of emitting.

```ts
race(
  interval(1000).pipe(mapTo('fast')),
  interval(2000).pipe(mapTo('medium')),
  interval(3000).pipe(mapTo('slow'))
).subscribe(observer);
// output: fast - 1s -> fast - 1s -> fast - 1s -> fast...
```

#### Use case

Show a banner after form submit (e.g. [ng-zorro Alert](https://ng.ant.design/components/alert/en)) and dismiss it when **any** of these happens:

- 10 seconds elapse
- User clicks close
- User navigates away

`race()` fits perfectly — you only need the first condition to win.

```ts
race(
  timer(10000), // timer 10 second
  this.userClick$, // user click event
  this.componentDestroy$ // navigate -> ngOnDestroy
)
  .pipe(takeUntil(this.componentDestroy$)) // stop listening to race after destroy
  .subscribe(() => this.closeBanner());
```

The operators above are **static functions**. The rest are **pipeable operators** applied to an **outer Observable**.

### withLatestFrom()

`withLatestFrom<T, R>(...args: any[]): OperatorFunction<T, R>`

`withLatestFrom()` takes at least one inner `Observable`. When the outer emits, it pairs that value with the latest inner value(s) and emits an array.

![RxJS withLatestFrom](assets/rxjs-withLatestFrom.png) <!-- TODO: asset -->

```ts
fromEvent(document, 'click')
  .pipe(withLatestFrom(interval(1000)))
  .subscribe(observer);
// output:
// - click before 1s --- wait until 1s --> [MouseEvent, 0]
// - click after 1s -> [MouseEvent, 0];
// - click at 5.5s -> [MouseEvent, 4];
```

An optional `projectFunction` works like other combination operators.

#### Use case

Because it only emits when the **outer** emits, `withLatestFrom()` suits cases where you listen to one stream and need the latest value from another — without `combineLatest()` re-emitting every time the inner stream ticks.

```ts
this.apiService.getSomething().pipe(withLatestFrom(this.currentLoggedInUser$));
// call an API and combine the result with the logged-in user for downstream logic
```

### startWith()

`startWith<T, D>(...array: (SchedulerLike | T)[]): OperatorFunction<T, T | D>`

`startWith()` prepends values to the stream before the outer emits — immediately on subscribe.

![RxJS startWith](assets/rxjs-startWith.png) <!-- TODO: asset -->

```ts
of('world').pipe(starWith('Hello')).subscribe(observer);
// output:
// 'Hello'
// 'word'
// 'complete'
```

#### Use case

Provide an initial value for async template data:

```ts
this.books$ = this.apiService.getBooks().pipe(startWith([]));
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ng-container *ngIf="books$ | async as books">
  <!-- because books$ has startWith([]), books is truthy immediately and *ngIf renders -->
</ng-container>
```

### endWith()

`endWith<T>(...array: (SchedulerLike | T)[]): MonoTypeOperatorFunction<T>`

Like `startWith()` but appends values when the outer **complete**s.

![RxJS endWith](assets/rxjs-endWith.png) <!-- TODO: asset -->

```ts
of('hi', 'how are you?', 'sorry, I have to go now')
  .pipe(endWith('goodbye!'))
  .subscribe(observer);
// output:
// 'hi'
// 'how are you?'
// 'sorry, I have to go now'
// 'goodbye!'
```

### pairwise()

`pairwise<T>(): OperatorFunction<T, [T, T]>`

`pairwise()` emits `[previous, current]` for each emission after the first.

![RxJS pairwise](assets/rxjs-pairwise.png) <!-- TODO: asset -->

```ts
from([1, 2, 3, 4, 5])
  .pipe(
    pairwise(),
    map((prev, cur) => prev + cur)
  )
  .subscribe(observer);
// output:
// 3 (1 + 2)
// 5 (2 + 3)
// 7 (3 + 4)
// 9 (4 + 5)
```

## Summary

Another big day of RxJS. The operators and use cases here are ones I've applied or can think of in real projects. When you find your own patterns with these operators, share them with the community.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)

## Author

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

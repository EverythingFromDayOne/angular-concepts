---
roadmap_node: "rxjs-error-handling"
title: "RxJS Error Handling and Conditional Operators"
file: "reactivity/rxjs/rxjs-error-handling.md"
source_days: [24]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# RxJS Error Handling and Conditional Operators

In the first RxJS article we learned that every `Observable` can send `next`, `error`, and `complete` notifications — and when an error occurs, the stream stops. How do we catch and handle those errors?

![Values over time](assets/rxjs-streams.gif) <!-- TODO: asset -->

Today we'll look at operators for error handling and for conditional logic (**Error Handling and Conditional Operators**).

We'll reuse this default observer:

```ts
const observer = {
  next: (val) => console.log(val),
  error: (err) => console.error(err),
  complete: () => console.log('complete'),
};
```

## RxJS error handling operators

### catchError

When you want to catch an error and handle it — for example turn it into a normal value and keep the stream alive — use `catchError` (`.catch` in the old prototype chain).

> Catches errors on the observable to be handled by returning a new observable or throwing an error. [RxJS catchError](https://rxjs.dev/api/operators/catchError)

`catchError<T, O extends ObservableInput<any>>(selector: (err: any, caught: Observable<T>) => O): OperatorFunction<T, T | ObservedValueOf<O>>`

```ts
import { of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
const cached = [4, 5];
of(1, 2, 3, 4, 5)
  .pipe(
    map((n) => {
      if (cached.includes(n)) {
        throw new Error('Duplicated: ' + n);
      }
      return n;
    }),
    catchError((err, caught) => of(err))
  )
  .subscribe(observer);

/**
 * Output:
 * --1--2--3--(next: Error)--|
 */
```

Without `catchError`, `observer.error` receives the failure. Here we return `of(err)`, so the error becomes a `next` value.

A practical case: with `forkJoin` ([combination operators](rxjs-combination.md)), one failing child fails the whole result. Wrap the risky child so the join still completes and you handle errors downstream:

```ts
forkJoin([of(1), of(2), throwError(new Error('401'))]).subscribe(observer);
/**
 * Output:
 * --(x: Error 401)--
 */

// with catchError

forkJoin([
  of(1),
  of(2),
  throwError(new Error('401')).pipe(catchError((err) => of(err))),
]).subscribe(observer);

/**
 * Output:
 * --(next: [1, 2, Error 401])|--
 */
```

![RxJS catchError](assets/rxjs-catchError.png) <!-- TODO: asset -->

Returning the `caught` source enables retry — but be careful of infinite loops. Combine with `take` to cap retries:

```ts
of(1, 2, 3, 4, 5)
  .pipe(
    map((n) => {
      if (cached.includes(n)) {
        throw new Error('Duplicated: ' + n);
      }
      return n;
    }),
    catchError((err, caught) => caught),
    take(10)
  )
  .subscribe(observer);

/**
 * Output:
 * --1--2--3--1--2--3--1|
 */
```

You can also re-throw from `catchError` for downstream handlers.

### retry

> Returns an Observable that mirrors the source Observable with the exception of an error. If the source Observable calls error, this method will resubscribe to the source Observable for a maximum of count resubscriptions (given as a number parameter) rather than propagating the error call.

`retry<T>(count: number = -1): MonoTypeOperatorFunction<T>`

`retry` resubscribes on error. With no `count`, retries are unbounded; with a number, it stops after that many attempts.

Useful for retrying HTTP GET requests. Avoid for create/update/delete — you can cause race conditions.

```ts
const cached = [4, 5];
of(1, 2, 3, 4, 5)
  .pipe(
    map((n) => {
      if (cached.includes(n)) {
        throw new Error('Duplicated: ' + n);
      }
      return n;
    }),
    retry(3)
  )
  .subscribe(observer);

/**
 * Output:
 * --1--2--3--1--2--3--1--2--3--1--2--3--(x: Error)
 */
```

![RxJS retry](assets/rxjs-retry.png) <!-- TODO: asset -->

> Note: `retry` behaves differently from the manual `catchError` + resubscribe pattern above.

For finer control (when to retry), use `retryWhen`. A popular pattern is [`retryBackoff`](https://github.com/alex-okrushko/backoff-rxjs/blob/7d38283bccc55237806062048eb5e6b90e9f9fff/src/operators/retryBackoff.ts), which increases delay between attempts:

```ts
export function retryBackoff(
  config: number | RetryBackoffConfig
): <T>(source: Observable<T>) => Observable<T> {
  const {
    initialInterval,
    maxRetries = Infinity,
    maxInterval = Infinity,
    shouldRetry = () => true,
    resetOnSuccess = false,
    backoffDelay = exponentialBackoffDelay,
  } = typeof config === 'number' ? { initialInterval: config } : config;
  return <T>(source: Observable<T>) =>
    defer(() => {
      let index = 0;
      return source.pipe(
        retryWhen<T>((errors) =>
          errors.pipe(
            concatMap((error) => {
              const attempt = index++;
              return iif(
                () => attempt < maxRetries && shouldRetry(error),
                timer(
                  getDelay(backoffDelay(attempt, initialInterval), maxInterval)
                ),
                throwError(error)
              );
            })
          )
        ),
        tap(() => {
          if (resetOnSuccess) {
            index = 0;
          }
        })
      );
    });
}
```

## RxJS conditional operators

### defaultIfEmpty / throwIfEmpty

`defaultIfEmpty<T, R>(defaultValue: R = null): OperatorFunction<T, T | R>`

`throwIfEmpty<T>(errorFactory: () => any = defaultErrorFactory): MonoTypeOperatorFunction<T>`

These handle an empty source that completes without emitting — either a default value or an error.

Example: if the user does not click within one second, fail (e.g. cancel an unconfirmed transaction).

```ts
import { fromEvent, timer } from 'rxjs';
import { throwIfEmpty, takeUntil } from 'rxjs/operators';

const click$ = fromEvent(document, 'click');

click$
  .pipe(
    takeUntil(timer(1000)),
    throwIfEmpty(
      () => new Error('the document was not clicked within 1 second')
    )
  )
  .subscribe(observer);
```

![RxJS throwIfEmpty](assets/rxjs-throwIfEmpty.png) <!-- TODO: asset -->

### every

> Returns an Observable that emits whether or not every item of the source satisfies the condition specified.

`every<T>(predicate: (value: T, index: number, source: Observable<T>) => boolean, thisArg?: any): OperatorFunction<T, boolean>`

Emits `true` only if every emitted value satisfies `predicate`.

> If the source never completes, nothing is emitted.

```ts
of(1, 2, 3, 4, 5, 6)
  .pipe(every((x) => x < 5))
  .subscribe(observer);

/**
 * Output:
 * ------false|
 */
```

![RxJS every](assets/rxjs-every.png) <!-- TODO: asset -->

JavaScript arrays have `every` and `some`. For an RxJS "some", combine `first` with a predicate — as in [Angular Router's guard checks](https://github.com/angular/angular/blob/10.0.x/packages/router/src/operators/check_guards.ts#L74-L76):

```ts
of(1, 2, 3, 14, 5, 6)
  .pipe(
    first((x) => x > 10, false),
    map((v) => Boolean(v))
  )
  .subscribe(observer);

/**
 * Output:
 * ------true|
 */
```

### iif

> Decides at subscription time which Observable will actually be subscribed. [RxJS iif](https://rxjs.dev/api/index/function/iif)

`iif<T = never, F = never>(condition: () => boolean, trueResult: SubscribableOrPromise<T> = EMPTY, falseResult: SubscribableOrPromise<F> = EMPTY): Observable<T | F>`

Pick which `Observable` to subscribe to when subscription happens, based on `condition()`.

> `iif` accepts a condition function and two Observables. When an Observable returned by the operator is subscribed, condition function will be called. Based on what boolean it returns at that moment, consumer will subscribe either to the first Observable (if condition was true) or to the second (if condition was false). Condition function may also not return anything - in that case condition will be evaluated as false and second Observable will be subscribed.

> Note that Observables for both cases (true and false) are optional. If condition points to an Observable that was left undefined, resulting stream will simply complete immediately. That allows you to, rather than controlling which Observable will be subscribed, decide at runtime if consumer should have access to given Observable or not.

> If you have more complex logic that requires decision between more than two Observables, `defer` will probably be a better choice. Actually `iif` can be easily implemented with `defer` and exists only for convenience and readability reasons.

```ts
import { iif, of } from 'rxjs';

let subscribeToFirst;
const firstOrSecond = iif(() => subscribeToFirst, of('first'), of('second'));

subscribeToFirst = true;
firstOrSecond.subscribe((value) => console.log(value));

// Logs:
// "first"

subscribeToFirst = false;
firstOrSecond.subscribe((value) => console.log(value));

// Logs:
// "second"
```

## Summary

Today we strengthened our RxJS toolkit with error-handling and conditional operators. Practice them in small examples until they feel natural.

## References

- [RxJS Overview](https://rxjs.dev/guide/overview)
- [LearnRxJS](https://www.learnrxjs.io/)
- [rxmarbles](https://rxmarbles.com/)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

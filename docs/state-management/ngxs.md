---
roadmap_node: "ngxs"
title: "NGXS"
file: "state-management/ngxs.md"
source_days: []
original_authors: []
status:
  translated: false
  upgraded: true
  reviewed: false
angular_when_written: null
angular_baseline: "22"
---

> **Modern Angular only**
> No equivalent exists in the original 100 Days series.
> Written fresh for Angular v22.

# NGXS

> **Lead with this:** NGXS is Redux-style state management where actions are
> TypeScript classes and state changes live inside a `@State` class — less
> ceremony than NgRx, more structure than plain signals, familiar to developers
> coming from MobX or class-based OOP patterns.

## What it is

NGXS (`@ngxs/store`) is a state management library that follows the same
unidirectional data flow as NgRx — single store, actions describe events,
selectors project state — but uses a class-based model instead of factory
functions:

| Concept | NgRx approach | NGXS approach |
| --- | --- | --- |
| Action | `createAction('type', props<T>())` | `export class LoadUsers {}` — a class |
| State | `createReducer(initial, on(...))` | `@State<T>` class with `@Action` methods |
| Selector | `createSelector(feature, fn)` | `@Selector()` static method in the state class |
| Side effects | Separate `@Injectable` effects class | Async logic inside `@Action` handler methods |

This model appeals to teams who prefer OOP patterns — action classes are
easier to find with TypeScript's "find all usages", state classes are
a natural home for async logic, and there are fewer files per feature.

> **Roadmap status:** NGXS is marked **optional** on this roadmap. It's a
> legitimate choice — actively maintained, Angular 22 compatible — but NgRx
> Store and NgRx Signal Store have wider adoption and better Angular team
> alignment. Choose NGXS when your team explicitly prefers the class-based model.

## How it works under the hood

### The class-based model vs factory functions

NgRx uses factory functions — `createAction`, `createReducer`, `createSelector`
— that produce typed values composed together by convention. NGXS uses
TypeScript class features — decorators, class methods, static members — to
achieve the same result with less indirection.

**NgRx pattern (factory functions):**
```typescript
// Three separate files typical: actions.ts, reducer.ts, effects.ts
const LoadUsers = createAction('[Users] Load');
const LoadUsersSuccess = createAction('[Users] Load Success', props<{ users: User[] }>());

const reducer = createReducer(
  initial,
  on(LoadUsers, state => ({ ...state, isLoading: true })),
  on(LoadUsersSuccess, (state, { users }) => ({ ...state, users, isLoading: false }))
);

@Injectable()
class UsersEffects {
  load$ = createEffect(() => this.actions$.pipe(
    ofType(LoadUsers),
    switchMap(() => this.api.getAll().pipe(map(users => LoadUsersSuccess({ users }))))
  ));
}
```

**NGXS pattern (class-based):**
```typescript
// actions.ts
export class LoadUsers {}
export class LoadUsersSuccess { constructor(public users: User[]) {} }

// users.state.ts — state, reducers, and effects in one class
@State<UsersStateModel>({ name: 'users', defaults: { users: [], isLoading: false } })
@Injectable()
export class UsersState {
  constructor(private api: UsersApiService) {}

  @Action(LoadUsers)
  load(ctx: StateContext<UsersStateModel>): Observable<void> {
    ctx.patchState({ isLoading: true });
    return this.api.getAll().pipe(
      tap(users => ctx.patchState({ users, isLoading: false }))
    );
  }
}
```

The state class handles both state mutations (`ctx.patchState`) and async
work (the `Observable` return) in one method — no separate effects file.
The `StateContext<T>` gives access to `getState()`, `setState()`, `patchState()`,
and `dispatch()` for chaining actions.

## Basic usage

### Setup

```bash
npm install @ngxs/store
# Optional plugins
npm install @ngxs/logger-plugin @ngxs/devtools-plugin
```

```typescript
// app.config.ts — standalone API
import { provideStore, provideState } from '@ngxs/store';
import { withNgxsLoggerPlugin } from '@ngxs/logger-plugin';
import { withNgxsDevelopmentOptions } from '@ngxs/store';
import { isDevMode } from '@angular/core';
import { UsersState } from './users/users.state';

export const appConfig: ApplicationConfig = {
  providers: [
    provideStore(
      [UsersState],              // register all root states
      withNgxsDevelopmentOptions({ developmentMode: isDevMode() })
    ),
    // Plugins registered after provideStore
    withNgxsLoggerPlugin({ disabled: !isDevMode() }),
  ],
};
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (pre-standalone)
@NgModule({
  imports: [
    NgxsModule.forRoot([UsersState], { developmentMode: !environment.production }),
    NgxsLoggerPluginModule.forRoot({ disabled: environment.production }),
  ],
})
export class AppModule {}
```

### Actions

NGXS actions are plain TypeScript classes. Simple actions need no constructor;
actions with payloads use the constructor:

```typescript
// users.actions.ts
export class LoadUsers {}

export class LoadUsersSuccess {
  static readonly type = '[Users API] Load Success';    // optional but aids DevTools
  constructor(public readonly users: User[]) {}
}

export class LoadUsersFailure {
  static readonly type = '[Users API] Load Failure';
  constructor(public readonly error: string) {}
}

export class DeleteUser {
  static readonly type = '[Users Page] Delete';
  constructor(public readonly userId: string) {}
}
```

Adding a static `type` string makes action names readable in DevTools — highly
recommended even though NGXS doesn't require it.

### State class

```typescript
// users.state.ts
import { State, Action, Selector, StateContext } from '@ngxs/store';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { LoadUsers, LoadUsersSuccess, LoadUsersFailure, DeleteUser } from './users.actions';

export interface UsersStateModel {
  users: User[];
  isLoading: boolean;
  error: string | null;
}

@State<UsersStateModel>({
  name: 'users',
  defaults: { users: [], isLoading: false, error: null },
})
@Injectable()
export class UsersState {
  constructor(private api: UsersApiService) {}

  // Memoized selector — recalculates only when state.users changes
  @Selector()
  static users(state: UsersStateModel): User[] { return state.users; }

  @Selector()
  static isLoading(state: UsersStateModel): boolean { return state.isLoading; }

  @Selector()
  static error(state: UsersStateModel): string | null { return state.error; }

  // Derived selector — composed from other selectors
  @Selector([UsersState.users])
  static adminUsers(users: User[]): User[] {
    return users.filter(u => u.role === 'admin');
  }

  // Synchronous action handler
  @Action(DeleteUser)
  delete(ctx: StateContext<UsersStateModel>, { userId }: DeleteUser): void {
    ctx.patchState({ users: ctx.getState().users.filter(u => u.id !== userId) });
  }

  // Async action handler — return Observable; NGXS subscribes automatically
  @Action(LoadUsers)
  load(ctx: StateContext<UsersStateModel>): Observable<void> {
    ctx.patchState({ isLoading: true, error: null });
    return this.api.getAll().pipe(
      tap(users => ctx.dispatch(new LoadUsersSuccess(users))),
      catchError(err => {
        ctx.dispatch(new LoadUsersFailure(err.message));
        return of(void 0);  // don't propagate the error to the store
      })
    );
  }

  @Action(LoadUsersSuccess)
  loadSuccess(ctx: StateContext<UsersStateModel>, { users }: LoadUsersSuccess): void {
    ctx.patchState({ users, isLoading: false });
  }

  @Action(LoadUsersFailure)
  loadFailure(ctx: StateContext<UsersStateModel>, { error }: LoadUsersFailure): void {
    ctx.patchState({ error, isLoading: false });
  }
}
```

### Selecting and dispatching in components

```typescript
import { Component, inject } from '@angular/core';
import { Store } from '@ngxs/store';
import { UsersState } from './users.state';
import { LoadUsers, DeleteUser } from './users.actions';

@Component({
  selector: 'app-users',
  standalone: true,
  template: `
    @if (isLoading()) {
      <app-spinner />
    } @else {
      @for (user of users(); track user.id) {
        <app-user-card [user]="user" (delete)="deleteUser(user.id)" />
      }
    }
  `,
})
export class UsersComponent {
  private store = inject(Store);

  // selectSignal() returns Signal<T> — works natively with @if/@for
  users     = this.store.selectSignal(UsersState.users);
  isLoading = this.store.selectSignal(UsersState.isLoading);
  admins    = this.store.selectSignal(UsersState.adminUsers);

  ngOnInit(): void {
    this.store.dispatch(new LoadUsers());
  }

  deleteUser(userId: string): void {
    this.store.dispatch(new DeleteUser(userId));
  }
}
```

`store.selectSignal()` (added in NGXS v3.8+) returns a `Signal<T>` — the
Angular 22 recommended way to read from the store. The older Observable-based
`store.select()` still works for RxJS pipelines.

### Lazy-loaded feature states

Register feature states at the route level using `provideState`:

```typescript
// users.routes.ts
export const usersRoutes: Routes = [
  {
    path: 'users',
    providers: [
      provideState([UsersState]),    // feature state loaded with this route
    ],
    loadComponent: () => import('./users.component'),
  },
];
```

## Real-world patterns

### Pattern 1 — Dispatching actions from action handlers

Action handlers can dispatch further actions via `ctx.dispatch()`, enabling
workflow orchestration without a separate effects layer:

```typescript
@Action(SubmitOrder)
submit(ctx: StateContext<OrderStateModel>, { order }: SubmitOrder): Observable<void> {
  ctx.patchState({ isSubmitting: true });
  return this.api.create(order).pipe(
    tap(saved => {
      // Chain multiple actions from one handler
      ctx.dispatch([
        new OrderSubmitted(saved),
        new ClearCart(),
        new Navigate(['/order-confirmation', saved.id]),
      ]);
    }),
    catchError(err => {
      ctx.dispatch(new OrderFailed(err.message));
      return of(void 0);
    })
  );
}
```

### Pattern 2 — Snapshot reads for one-time values

`store.selectSnapshot()` reads the current value synchronously — useful in
guards, resolvers, or anywhere you need the value once without subscribing:

```typescript
// In a route guard — read auth state without Observable/Signal
export const authGuard = (): boolean => {
  const store = inject(Store);
  const isAuthenticated = store.selectSnapshot(AuthState.isAuthenticated);

  if (!isAuthenticated) {
    inject(Router).navigate(['/login']);
    return false;
  }
  return true;
};
```

## Common mistakes

### Mistake 1 — Returning without subscribing to async action handlers

If your `@Action` method returns an Observable but nothing subscribes to it,
the async work never runs. NGXS handles the subscription automatically when
you return the Observable from the handler:

```typescript
// ❌ Observable created but not returned — NGXS never subscribes
@Action(LoadUsers)
load(ctx: StateContext<UsersStateModel>): void {
  this.api.getAll().pipe(tap(users => ctx.patchState({ users })));
  // no return — dead pipe
}

// ✅ Return the Observable — NGXS subscribes to it
@Action(LoadUsers)
load(ctx: StateContext<UsersStateModel>): Observable<void> {
  return this.api.getAll().pipe(tap(users => ctx.patchState({ users })));
}
```

### Mistake 2 — Mutating state directly instead of patchState

Like NgRx, NGXS state must be updated immutably:

```typescript
// ❌ Direct mutation — NGXS may not detect the change
@Action(AddUser)
add(ctx: StateContext<UsersStateModel>, { user }: AddUser): void {
  ctx.getState().users.push(user);   // mutation
}

// ✅ patchState produces a new reference
@Action(AddUser)
add(ctx: StateContext<UsersStateModel>, { user }: AddUser): void {
  ctx.patchState({ users: [...ctx.getState().users, user] });
}
```

### Mistake 3 — Putting business logic in @Selector methods

`@Selector` methods must be pure — they receive state and return a projection.
Putting side effects or async calls inside them breaks memoization:

```typescript
// ❌ Selector with a side effect — breaks memoization, unexpected behavior
@Selector()
static users(state: UsersStateModel): User[] {
  console.log('Fetching users...');  // side effect in a selector
  return state.users;
}

// ✅ Pure projection only
@Selector()
static users(state: UsersStateModel): User[] {
  return state.users;
}
```

## How this evolved

> - **NGXS v1–2 (2018):** Initial release. Class-based actions, `@State`
>   decorator, `@Action`, `@Selector`, NgModule-only setup. Quickly gained
>   traction as a lower-boilerplate Redux alternative to NgRx.
>
> - **NGXS v3 (2020):** Stability and performance improvements. Plugin
>   ecosystem matured — logger, devtools, storage, router plugins. Adopted in
>   production by many Angular teams.
>
> - **NGXS v3.8 (2022):** `provideStore()` and `provideState()` introduced —
>   standalone API for apps without NgModules. `store.selectSignal()` added,
>   returning `Signal<T>` from selectors.
>
> - **NGXS v4+ (2024–2025):** Active maintenance continues. Angular 18–22
>   compatibility. NGXS team chose not to build their own signal store —
>   instead providing utilities (`createSelectMap`, `createDispatchMap`) to
>   bridge NGXS global state with NgRx Signal Store for component-level state.
>
> - **Angular 22 (now):** NGXS is a stable, maintained option. The Angular
>   ecosystem's broader momentum is behind NgRx Signal Store and plain signal
>   services for new projects. NGXS is the right choice for teams that
>   actively prefer its class-based model or have existing NGXS codebases.

## See also

- [NgRx Store](./ngrx.md) — the Redux alternative with factory functions,
  strict conventions, and official Angular team alignment
- [NgRx Signal Store](./ngrx-signal-store.md) — the signal-native, low-ceremony
  alternative; works alongside NGXS via bridge utilities
- [Signals](../reactivity/signals.md) — plain signal services for simpler
  state that doesn't need a dedicated state library
- [Official NGXS docs](https://www.ngxs.io)
- [NGXS GitHub](https://github.com/ngxs/store)

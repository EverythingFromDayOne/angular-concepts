---
roadmap_node: "ngrx"
title: "NgRx Store"
file: "state-management/ngrx.md"
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

# NgRx Store

> **Lead with this:** NgRx implements the Redux pattern for Angular —
> immutable state lives in a single store, components dispatch actions to
> describe what happened, reducers derive the next state, and selectors
> project slices of state into your templates. The overhead is real but the
> payoff is predictability and DevTools time-travel at scale.

## What it is

NgRx is a collection of libraries that implement Redux-inspired state
management for Angular. The core package is `@ngrx/store`:

| Concept | What it does |
| --- | --- |
| **Store** | Single immutable state tree for the whole app |
| **Action** | An event describing something that happened (`{ type: '[Users] Load' }`) |
| **Reducer** | A pure function `(state, action) => newState` |
| **Selector** | A memoized projection `state => slice` |
| **Effect** | A class that handles side effects (HTTP, routing) triggered by actions |

Everything flows in one direction: component dispatches action → reducer produces
new state → selector projects it → component re-renders. No direct mutation,
no hidden state.

**When to reach for NgRx vs signals:**

Use NgRx when you need: shared state across many feature areas, complex async
orchestration across many actions, DevTools time-travel debugging, or a
large team that benefits from explicit conventions. For component-level or
feature-level state that doesn't need to be shared globally, signals
(or NgRx Signal Store) are simpler and more direct.

## How it works under the hood

### Old approach — imperative services with BehaviorSubject

Before NgRx, shared state lived in services:

```typescript
// Common pre-NgRx pattern — imperative, hard to trace
@Injectable({ providedIn: 'root' })
export class UsersService {
  private _users = new BehaviorSubject<User[]>([]);
  users$ = this._users.asObservable();

  loadUsers(): void {
    this.http.get<User[]>('/api/users').subscribe(users => {
      this._users.next(users);
    });
  }

  addUser(user: User): void {
    this._users.next([...this._users.value, user]);
  }
}
```

Problems at scale:
- **Mutations are invisible.** Any service or component can call `next()`.
  When state is wrong, finding who changed it requires searching the whole app.
- **No audit trail.** You know the current state, not how you got there.
- **Side effects are tangled.** HTTP calls live alongside state mutations.
  Testing requires mocking the service differently per scenario.
- **DevTools are impossible.** No record of what happened or in what order.

### NgRx's Redux model — one direction, one store

NgRx inverts this entirely. State is never mutated directly. Instead:

```
Component dispatches:  store.dispatch(UsersActions.loadUsers())
                                │
                                ▼
                    Effect intercepts the action,
                    calls the HTTP API,
                    dispatches success/failure action
                                │
                                ▼
                    Reducer produces a NEW state object
                    (old state + action → next state)
                                │
                                ▼
                    Selectors project the new state
                                │
                                ▼
                    Component receives updated values
                    via store.selectSignal()
```

Every state change is an action with a `type` string. NgRx DevTools records
every action and the state after it. You can replay, rewind, and inspect
exactly what happened and when — something impossible with mutable services.

Reducers are **pure functions** — same input always produces same output, no
side effects. This is what makes the reducer's behavior predictable and
independently testable.

## Setup

```bash
ng add @ngrx/store
ng add @ngrx/effects
ng add @ngrx/store-devtools  # Chrome/Firefox DevTools extension
```

```typescript
// app.config.ts — standalone API (replaces NgModule imports)
import { provideStore } from '@ngrx/store';
import { provideEffects } from '@ngrx/effects';
import { provideStoreDevtools } from '@ngrx/store-devtools';
import { isDevMode } from '@angular/core';
import { usersFeature } from './users/users.feature';
import { UsersEffects } from './users/users.effects';

export const appConfig: ApplicationConfig = {
  providers: [
    provideStore(),                              // root store (empty state at root)
    provideState(usersFeature),                  // register feature state
    provideEffects([UsersEffects]),              // register effects
    provideStoreDevtools({
      maxAge: 25,                               // remember last 25 states
      logOnly: !isDevMode(),                    // read-only in production
      autoPause: true,                          // pause when DevTools closed
    }),
  ],
};
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13)
@NgModule({
  imports: [
    StoreModule.forRoot({}),
    EffectsModule.forRoot([]),
    StoreDevtoolsModule.instrument({ maxAge: 25, logOnly: !isDevMode() }),
  ],
})
export class AppModule {}
```

## Core building blocks

### Actions — createActionGroup

Group related actions with a shared source. NgRx auto-generates typed action
creators from your event names:

```typescript
// users.actions.ts
import { createActionGroup, emptyProps, props } from '@ngrx/store';
import { User } from './user.model';

export const UsersActions = createActionGroup({
  source: 'Users',        // appears as "[Users]" prefix in DevTools
  events: {
    // emptyProps() — action with no payload
    loadUsers: emptyProps(),

    // props<T>() — action with typed payload
    loadUsersSuccess: props<{ users: User[] }>(),
    loadUsersFailure: props<{ error: string }>(),

    selectUser: props<{ userId: string }>(),
    deleteUser: props<{ userId: string }>(),
    updateUser: props<{ user: User }>(),
  },
});

// Generated (typed, ready to dispatch):
// UsersActions.loadUsers()
// UsersActions.loadUsersSuccess({ users })
// UsersActions.loadUsersFailure({ error })
// UsersActions.selectUser({ userId })
```

### Reducer + createFeature — state + auto-generated selectors

`createFeature` wraps your reducer and automatically generates a selector for
each top-level property in your state:

```typescript
// users.feature.ts
import { createFeature, createReducer, on } from '@ngrx/store';
import { createEntityAdapter, EntityState } from '@ngrx/entity';
import { User } from './user.model';
import { UsersActions } from './users.actions';

export interface UsersState extends EntityState<User> {
  selectedUserId: string | null;
  isLoading: boolean;
  error: string | null;
}

const adapter = createEntityAdapter<User>();
const initialState: UsersState = adapter.getInitialState({
  selectedUserId: null,
  isLoading: false,
  error: null,
});

export const usersFeature = createFeature({
  name: 'users',        // → feature key in the store
  reducer: createReducer(
    initialState,

    on(UsersActions.loadUsers, state => ({
      ...state,
      isLoading: true,
      error: null,
    })),

    on(UsersActions.loadUsersSuccess, (state, { users }) =>
      adapter.setAll(users, { ...state, isLoading: false })
    ),

    on(UsersActions.loadUsersFailure, (state, { error }) => ({
      ...state,
      isLoading: false,
      error,
    })),

    on(UsersActions.selectUser, (state, { userId }) => ({
      ...state,
      selectedUserId: userId,
    })),

    on(UsersActions.deleteUser, (state, { userId }) =>
      adapter.removeOne(userId, state)
    ),
  ),

  // Additional selectors beyond the auto-generated ones
  extraSelectors: ({ selectUsersState }) => ({
    ...adapter.getSelectors(selectUsersState),  // selectAll, selectEntities, selectTotal
  }),
});

// Auto-generated selectors from createFeature:
// usersFeature.selectUsersState     — full feature state
// usersFeature.selectSelectedUserId — state.selectedUserId
// usersFeature.selectIsLoading      — state.isLoading
// usersFeature.selectError          — state.error
// From extraSelectors (NgRx Entity):
// usersFeature.selectAll            — all users as array
// usersFeature.selectEntities       — users as entity map
// usersFeature.selectTotal          — count
```

### Effects — handling side effects

Effects listen for actions, perform async work, and dispatch new actions:

```typescript
// users.effects.ts
import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, exhaustMap, map, of } from 'rxjs';
import { UsersService } from './users.service';
import { UsersActions } from './users.actions';

@Injectable()
export class UsersEffects {
  private actions$ = inject(Actions);
  private usersService = inject(UsersService);

  loadUsers$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsersActions.loadUsers),
      exhaustMap(() =>                    // exhaustMap: ignore new loadUsers while one is pending
        this.usersService.getAll().pipe(
          map(users => UsersActions.loadUsersSuccess({ users })),
          catchError(error => of(UsersActions.loadUsersFailure({ error: error.message })))
        )
      )
    )
  );

  deleteUser$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsersActions.deleteUser),
      switchMap(({ userId }) =>           // switchMap: cancel if another delete fires
        this.usersService.delete(userId).pipe(
          map(() => UsersActions.loadUsers()),  // reload after delete
          catchError(error => of(UsersActions.loadUsersFailure({ error: error.message })))
        )
      )
    )
  );
}
```

**Choosing the right flattening operator for effects:**

| Operator | Behavior | Use when |
| --- | --- | --- |
| `exhaustMap` | Ignores new actions while one is in flight | One-at-a-time operations (load, auth) |
| `switchMap` | Cancels the previous, starts new | Latest-wins (search, real-time) |
| `concatMap` | Queues in order, one at a time | Sequential operations that must not overlap |
| `mergeMap` | Runs all in parallel | Parallel, independent operations |

### Selecting state — selectSignal (v16+)

`store.selectSignal()` returns a `Signal<T>` instead of `Observable<T>` — the
v22-recommended way to read from the store in components:

```typescript
import { Component, inject, computed } from '@angular/core';
import { Store } from '@ngrx/store';
import { usersFeature } from './users.feature';
import { UsersActions } from './users.actions';

@Component({
  selector: 'app-users',
  standalone: true,
  template: `
    @if (isLoading()) {
      <app-spinner />
    } @else if (error()) {
      <app-error-banner [message]="error()!" />
    } @else {
      <p>{{ totalUsers() }} users</p>
      <ul>
        @for (user of users(); track user.id) {
          <li>{{ user.name }}</li>
        }
      </ul>
    }
  `,
})
export class UsersComponent {
  private store = inject(Store);

  // selectSignal() returns Signal<T> — works with @if/@for natively
  users = this.store.selectSignal(usersFeature.selectAll);
  isLoading = this.store.selectSignal(usersFeature.selectIsLoading);
  error = this.store.selectSignal(usersFeature.selectError);
  totalUsers = this.store.selectSignal(usersFeature.selectTotal);

  ngOnInit(): void {
    this.store.dispatch(UsersActions.loadUsers());
  }
}
```

For Observable-based templates (legacy, still valid):
```typescript
// Observable approach — still works, AsyncPipe handles subscription
users$ = this.store.select(usersFeature.selectAll);
```

## Real-world patterns

### Pattern 1 — Feature state with lazy loading

Register feature state at the route level — loaded only when the user
visits that route:

```typescript
// users.routes.ts
export const usersRoutes: Routes = [
  {
    path: 'users',
    providers: [
      provideState(usersFeature),           // feature state scoped to this route
      provideEffects([UsersEffects]),       // effects scoped to this route
    ],
    children: [
      { path: '', loadComponent: () => import('./users-list.component') },
      { path: ':id', loadComponent: () => import('./user-detail.component') },
    ],
  },
];
```

### Pattern 2 — Facade pattern for cleaner components

A facade service wraps store dispatch and select calls, giving components a
domain API instead of a store API:

```typescript
// users.facade.ts
@Injectable({ providedIn: 'root' })
export class UsersFacade {
  private store = inject(Store);

  // Public signals — component reads these
  users = this.store.selectSignal(usersFeature.selectAll);
  isLoading = this.store.selectSignal(usersFeature.selectIsLoading);
  error = this.store.selectSignal(usersFeature.selectError);

  // Public actions — component calls these
  loadAll(): void { this.store.dispatch(UsersActions.loadUsers()); }
  select(id: string): void { this.store.dispatch(UsersActions.selectUser({ userId: id })); }
  delete(id: string): void { this.store.dispatch(UsersActions.deleteUser({ userId: id })); }
}

// Component becomes thin — no store knowledge
@Component({ /* ... */ })
export class UsersComponent {
  facade = inject(UsersFacade);

  ngOnInit(): void { this.facade.loadAll(); }
}
```

### Pattern 3 — Testing reducers and effects

Reducers are pure functions — test them without Angular:

```typescript
// users.reducer.spec.ts
describe('usersFeature reducer', () => {
  it('sets isLoading on loadUsers', () => {
    const state = usersFeature.reducer(initialState, UsersActions.loadUsers());
    expect(state.isLoading).toBeTrue();
  });

  it('stores users on loadUsersSuccess', () => {
    const users = [{ id: '1', name: 'Alice' }];
    const state = usersFeature.reducer(
      initialState,
      UsersActions.loadUsersSuccess({ users })
    );
    expect(state.ids).toEqual(['1']);
    expect(state.isLoading).toBeFalse();
  });
});
```

Effects need `provideMockActions` and `provideMockStore`:

```typescript
// users.effects.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideMockActions } from '@ngrx/effects/testing';
import { provideMockStore } from '@ngrx/store/testing';
import { of, throwError } from 'rxjs';
import { UsersEffects } from './users.effects';
import { UsersActions } from './users.actions';

describe('UsersEffects', () => {
  let actions$ = new Subject<Action>();
  let effects: UsersEffects;
  let usersService: jasmine.SpyObj<UsersService>;

  beforeEach(() => {
    usersService = jasmine.createSpyObj('UsersService', ['getAll']);

    TestBed.configureTestingModule({
      providers: [
        UsersEffects,
        provideMockActions(() => actions$),
        provideMockStore(),
        { provide: UsersService, useValue: usersService },
      ],
    });
    effects = TestBed.inject(UsersEffects);
  });

  it('dispatches loadUsersSuccess on success', (done) => {
    const users = [{ id: '1', name: 'Alice' }];
    usersService.getAll.and.returnValue(of(users));

    effects.loadUsers$.subscribe(action => {
      expect(action).toEqual(UsersActions.loadUsersSuccess({ users }));
      done();
    });

    actions$.next(UsersActions.loadUsers());
  });
});
```

## Common mistakes

### Mistake 1 — Mutating state in a reducer

Reducers must never mutate — always return new objects:

```typescript
// ❌ Mutation — NgRx won't detect the change; views won't update
on(UsersActions.updateUser, (state, { user }) => {
  state.entities[user.id] = user;  // direct mutation!
  return state;
}),

// ✅ New object — immutable update
on(UsersActions.updateUser, (state, { user }) =>
  adapter.updateOne({ id: user.id, changes: user }, state)
),
```

Use NgRx Entity's adapter methods (`setOne`, `updateOne`, `removeOne`, `addMany`)
to avoid manual spreading for entity collections.

### Mistake 2 — Using switchMap for write operations

`switchMap` cancels the previous observable when a new action arrives. For
write operations (create, update, delete), this can cancel a save mid-flight:

```typescript
// ❌ switchMap for a write — second save cancels the first
createUser$ = createEffect(() =>
  this.actions$.pipe(
    ofType(UsersActions.createUser),
    switchMap(({ user }) => this.usersService.create(user).pipe(...))
  )
);

// ✅ concatMap — queues writes; exhaustMap — ignores if one is pending
createUser$ = createEffect(() =>
  this.actions$.pipe(
    ofType(UsersActions.createUser),
    concatMap(({ user }) => this.usersService.create(user).pipe(...))
  )
);
```

### Mistake 3 — Putting derived data in the store

The store should hold **source of truth data**, not computed values. Selectors
handle derivation — they're memoized and recompute automatically:

```typescript
// ❌ Storing derived data in state — now you have two sources of truth
interface UsersState {
  users: User[];
  adminUsers: User[];   // derived! Must stay in sync with users manually
  userCount: number;    // derived!
}

// ✅ Derive in selectors — always consistent, always fresh
const selectAdmins = createSelector(
  usersFeature.selectAll,
  users => users.filter(u => u.role === 'admin')
);
const selectUserCount = createSelector(
  usersFeature.selectTotal,
  total => total
);
```

### Mistake 4 — Dispatching actions in effects without handling errors

An uncaught error in an effect kills the effect permanently — it stops
listening for future actions:

```typescript
// ❌ No catchError — if getAll() throws, loadUsers$ is dead forever
loadUsers$ = createEffect(() =>
  this.actions$.pipe(
    ofType(UsersActions.loadUsers),
    switchMap(() => this.usersService.getAll().pipe(
      map(users => UsersActions.loadUsersSuccess({ users }))
      // missing catchError — one failure kills this effect
    ))
  )
);

// ✅ catchError inside the inner observable — effect stays alive
loadUsers$ = createEffect(() =>
  this.actions$.pipe(
    ofType(UsersActions.loadUsers),
    switchMap(() => this.usersService.getAll().pipe(
      map(users => UsersActions.loadUsersSuccess({ users })),
      catchError(err => of(UsersActions.loadUsersFailure({ error: err.message })))
    ))
  )
);
```

The `catchError` must be inside the `switchMap`/`exhaustMap` callback — not on
the outer observable. Otherwise, a single error kills the whole effect stream.

## How this evolved

> - **NgRx v1–7 (2016–2018):** Class-based actions, `@Effect()` decorator,
>   NgModule-only setup. Verbose: three files (actions, reducer, effects) with
>   lots of boilerplate per feature.
>
> - **NgRx v8 (2019):** `createAction`, `createReducer`, `on()`, and
>   `createSelector` introduced. Type safety improved significantly.
>   `@Effect` deprecated in favor of `createEffect(() => ...)`.
>
> - **NgRx v12 (2021):** `createFeature` introduced — combines name, reducer,
>   and auto-generated selectors in one declaration.
>
> - **NgRx v14 (2022):** `createActionGroup` introduced — groups related
>   actions under one source. Standalone APIs: `provideStore`,
>   `provideState`, `provideEffects`, `provideStoreDevtools`.
>
> - **NgRx v16 (2023):** `store.selectSignal()` — returns `Signal<T>` instead
>   of `Observable<T>`. Functional effects (alternative to class-based).
>   `extraSelectors` in `createFeature`. `@Effect` decorator removed.
>
> - **NgRx v18+ (2024–2025):** NgRx Signal Store introduced as a separate,
>   signal-native alternative. NgRx Store remains the standard for large-scale
>   Redux-pattern apps.
>
> - **Angular 22 / NgRx ~v20 (now):** `store.selectSignal()` is the
>   recommended way to consume store state in components. `provideStore` +
>   `provideState` + `provideEffects` is the standard setup. NgModule-based
>   APIs still work but are considered legacy.

## See also

- [NgRx Signal Store](./ngrx-signal-store.md) — the signal-native alternative
  for feature-level state without the Redux ceremony
- [Signals](../reactivity/signals.md) — signal services as a lighter
  alternative to NgRx for local or feature state
- [HTTP](../http/http.md) — `HttpClient` patterns that effects orchestrate
- [Change Detection](../components/change-detection.md) — why `selectSignal()`
  works with `OnPush` without `markForCheck`
- [Official docs — NgRx Store](https://ngrx.io/guide/store)
- [Official docs — NgRx Effects](https://ngrx.io/guide/effects)
- [Official NgRx DevTools](https://ngrx.io/guide/store-devtools)

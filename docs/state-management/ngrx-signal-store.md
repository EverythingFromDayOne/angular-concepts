---
roadmap_node: "ngrx-signal-store"
title: "NgRx Signal Store"
file: "state-management/ngrx-signal-store.md"
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

# NgRx Signal Store

> **Lead with this:** NgRx Signal Store replaces Actions + Reducers + Effects with
> signals and methods — the same NgRx library family, but without the Redux
> ceremony. State is a group of signals. You update it with `patchState()`.
> Async work lives in `rxMethod()`. No action strings, no switch statements.

## What it is

NgRx Signal Store (`@ngrx/signals`) is a separate package from `@ngrx/store`.
It is not Redux. It does not use actions, reducers, or effects. Instead, it
gives you a composable, signal-native way to build stores using a set of
"feature" functions:

| Feature | What it adds |
| --- | --- |
| `withState()` | Reactive state — each property becomes a `Signal<T>` |
| `withComputed()` | Derived signals built from state |
| `withMethods()` | Public methods that update state or trigger async work |
| `withProps()` | Private dependencies — inject services into the store |
| `withHooks()` | Lifecycle callbacks — `onInit` and `onDestroy` |
| `withEntities()` | Collection management (from `@ngrx/signals/entities`) |

You compose a store by calling `signalStore(feature1, feature2, feature3, ...)`.
The result is an injectable Angular service.

**NgRx Signal Store vs NgRx Store — when to use which:**

| | NgRx Signal Store | NgRx Store |
| --- | --- | --- |
| Boilerplate | Low | High |
| DevTools | Community (`@angular-architects/ngrx-toolkit`) | Official, excellent |
| Conventions | Flexible | Strict |
| Redux pattern | No | Yes |
| Best for | Feature stores, mid-size apps | Large teams, strict audit trail needed |

## How it works under the hood

### NgRx Store — explicit Redux ceremony

NgRx Store follows the Redux pattern: every state change goes through an
action, a reducer, and produces a new state object. The audit trail is
complete but the boilerplate is high — a simple "load users" feature needs
actions (3+), a reducer, a feature, selectors, and an effects class.

```
dispatch(LoadUsers)
  → Effect intercepts → HTTP → dispatch(LoadUsersSuccess)
    → Reducer produces newState
      → Selector projects
        → Component re-renders
```

Every hop is explicit and logged. Powerful for debugging at scale. Verbose
for straightforward data fetching.

### NgRx Signal Store — signals + composition

Signal Store collapses the Redux hops into direct method calls and signal
reads:

```
component calls store.loadUsers()
  → method sets { isLoading: true } via patchState()
    → rxMethod fires HTTP
      → tapResponse sets { users, isLoading: false } via patchState()
        → signals notify template
          → component re-renders
```

No action strings. No switch statements. No separate effects class. State
updates happen in one place — the `withMethods()` block — using `patchState()`,
which patches the state immutably (like `store.dispatch()` but synchronous
and direct).

Every property in `withState()` becomes a signal automatically. When you call
`patchState(store, { count: 5 })`, Angular's signal graph marks all consumers
of `store.count` as dirty and schedules a re-render — exactly as if you had
called `count.set(5)` on a writable signal.

## Basic usage

### Creating a store

```typescript
import { computed, inject } from '@angular/core';
import {
  patchState, signalStore, withComputed,
  withHooks, withMethods, withProps, withState,
} from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { tapResponse } from '@ngrx/operators';
import { pipe, switchMap, tap } from 'rxjs';
import { UserService } from './user.service';

type UsersState = {
  users: User[];
  isLoading: boolean;
  error: string | null;
  query: string;
};

const initialState: UsersState = {
  users: [],
  isLoading: false,
  error: null,
  query: '',
};

export const UsersStore = signalStore(
  { providedIn: 'root' },        // injectable anywhere; omit for component-scoped

  withState(initialState),       // state.users, state.isLoading become signals

  withProps(() => ({             // inject private dependencies here
    _userService: inject(UserService),
  })),

  withComputed(({ users, query }) => ({
    // computed() reads signals — auto-updates when users or query changes
    filteredUsers: computed(() => {
      const q = query().toLowerCase();
      return users().filter(u => u.name.toLowerCase().includes(q));
    }),
    userCount: computed(() => users().length),
  })),

  withMethods((store) => ({
    // Synchronous state update
    setQuery(query: string): void {
      patchState(store, { query });
    },

    // Async method using rxMethod — accepts value, Signal, or Observable
    loadUsers: rxMethod<void>(
      pipe(
        tap(() => patchState(store, { isLoading: true, error: null })),
        switchMap(() =>
          store._userService.getAll().pipe(
            tapResponse({
              next: users => patchState(store, { users, isLoading: false }),
              error: (e: Error) => patchState(store, { error: e.message, isLoading: false }),
            })
          )
        )
      )
    ),

    deleteUser: rxMethod<string>(
      pipe(
        switchMap(id =>
          store._userService.delete(id).pipe(
            tapResponse({
              next: () => patchState(store, state => ({
                users: state.users.filter(u => u.id !== id),
              })),
              error: (e: Error) => patchState(store, { error: e.message }),
            })
          )
        )
      )
    ),
  })),

  withHooks({
    onInit(store): void {
      // Runs in injection context — safe to call rxMethod or inject() here
      store.loadUsers();
    },
    onDestroy(store): void {
      console.log('Store destroyed. Final user count:', store.userCount());
    },
  })
);
```

### Using the store in a component

```typescript
import { Component, inject } from '@angular/core';
import { UsersStore } from './users.store';

@Component({
  selector: 'app-users',
  standalone: true,
  template: `
    <input
      [value]="store.query()"
      (input)="store.setQuery($any($event.target).value)"
      placeholder="Search users…"
    />

    <p>{{ store.filteredUsers().length }} of {{ store.userCount() }} users</p>

    @if (store.isLoading()) {
      <app-spinner />
    } @else if (store.error()) {
      <app-error [message]="store.error()!" />
    } @else {
      @for (user of store.filteredUsers(); track user.id) {
        <app-user-card
          [user]="user"
          (delete)="store.deleteUser(user.id)"
        />
      }
    }
  `,
})
export class UsersComponent {
  store = inject(UsersStore);
  // store.users(), store.isLoading(), store.error(), store.query()
  // store.filteredUsers(), store.userCount()
  // store.loadUsers(), store.setQuery(), store.deleteUser()
  // — all available directly
}
```

### Entity management — withEntities

For collections, `withEntities` from `@ngrx/signals/entities` provides
dictionary storage and auto-generated `entities()` computed signal:

```typescript
import { withEntities, setAllEntities, addEntity, removeEntity, updateEntity } from '@ngrx/signals/entities';
import { signalStore, withMethods, withProps, patchState } from '@ngrx/signals';

export const ProductsStore = signalStore(
  { providedIn: 'root' },
  withEntities<Product>(),         // adds: ids, entityMap, entities (computed)

  withProps(() => ({
    _api: inject(ProductsApiService),
  })),

  withMethods((store) => ({
    load: rxMethod<void>(
      pipe(
        switchMap(() => store._api.getAll().pipe(
          tapResponse({
            next: products => patchState(store, setAllEntities(products)),
            error: console.error,
          })
        ))
      )
    ),

    add: rxMethod<CreateProductDto>(
      pipe(
        switchMap(dto => store._api.create(dto).pipe(
          tapResponse({
            next: product => patchState(store, addEntity(product)),
            error: console.error,
          })
        ))
      )
    ),

    remove(id: string): void {
      patchState(store, removeEntity(id));          // optimistic — no async
    },
  }))
);
```

```html
<!-- Template — entities() is a computed Signal<Product[]> -->
@for (product of store.entities(); track product.id) {
  <app-product [product]="product" (remove)="store.remove(product.id)" />
}
```

### Component-scoped stores

Omit `{ providedIn: 'root' }` and provide the store in the component —
the store is created per component instance and destroyed with it:

```typescript
@Component({
  selector: 'app-search',
  standalone: true,
  providers: [SearchStore],  // instance-scoped — created and destroyed with this component
  template: `...`,
})
export class SearchComponent {
  store = inject(SearchStore);
}
```

Use component-scoped stores for wizard steps, multi-step forms, or any UI
where state doesn't need to outlive the component.

### Custom reusable features

`signalStoreFeature()` lets you extract a pattern into a reusable feature
that can be composed into any store:

```typescript
// with-request-status.ts — reusable loading/error feature
import { signalStoreFeature, withState, withComputed, patchState } from '@ngrx/signals';
import { computed } from '@angular/core';

export type RequestStatus = 'idle' | 'pending' | 'fulfilled' | { error: string };

export function withRequestStatus() {
  return signalStoreFeature(
    withState({ requestStatus: 'idle' as RequestStatus }),
    withComputed(({ requestStatus }) => ({
      isPending:   computed(() => requestStatus() === 'pending'),
      isFulfilled: computed(() => requestStatus() === 'fulfilled'),
      error:       computed(() => {
        const s = requestStatus();
        return typeof s === 'object' ? s.error : null;
      }),
    }))
  );
}

// Helper updaters — use these in patchState() calls
export const setPending    = (): Partial<{ requestStatus: RequestStatus }> => ({ requestStatus: 'pending' });
export const setFulfilled  = (): Partial<{ requestStatus: RequestStatus }> => ({ requestStatus: 'fulfilled' });
export const setError      = (error: string): Partial<{ requestStatus: RequestStatus }> => ({ requestStatus: { error } });
```

```typescript
// Compose into any store
export const UsersStore = signalStore(
  { providedIn: 'root' },
  withState({ users: [] as User[] }),
  withRequestStatus(),          // adds isPending, isFulfilled, error signals
  withMethods(store => ({
    load: rxMethod<void>(pipe(
      tap(() => patchState(store, setPending())),
      switchMap(() => usersService.getAll().pipe(
        tapResponse({
          next: users => patchState(store, { users }, setFulfilled()),
          error: (e: Error) => patchState(store, setError(e.message)),
        })
      ))
    )),
  }))
);
```

## Real-world patterns

### Pattern 1 — Reactive search with rxMethod connected to a signal

`rxMethod` accepts a signal directly — when the signal changes, the method
re-runs automatically. This is the cleanest way to drive data loading from
a reactive input:

```typescript
withMethods((store) => ({
  // rxMethod can accept: a value, a Signal<T>, or an Observable<T>
  searchByQuery: rxMethod<string>(
    pipe(
      debounceTime(300),
      distinctUntilChanged(),
      tap(() => patchState(store, setPending())),
      switchMap(query =>
        store._api.search(query).pipe(
          tapResponse({
            next: results => patchState(store, { results }, setFulfilled()),
            error: (e: Error) => patchState(store, setError(e.message)),
          })
        )
      )
    )
  ),
})),

withHooks({
  onInit(store): void {
    // Connect the query SIGNAL to the rxMethod — auto-searches on every change
    store.searchByQuery(store.query);  // passing signal directly — not store.query()
  },
})
```

### Pattern 2 — tapResponse vs catchError

Never use `catchError` inside an `rxMethod` pipeline — it completes the outer
stream, which means the method stops working after the first error:

```typescript
// ❌ catchError completes the outer stream — method dies after first failure
loadUsers: rxMethod<void>(
  pipe(
    switchMap(() => usersService.getAll().pipe(
      map(users => patchState(store, { users })),
      catchError(err => { patchState(store, { error: err.message }); return EMPTY; })
      // ^ after this error, the rxMethod stops listening for future calls
    ))
  )
),

// ✅ tapResponse handles error without completing the outer stream
loadUsers: rxMethod<void>(
  pipe(
    switchMap(() => usersService.getAll().pipe(
      tapResponse({
        next: users => patchState(store, { users }),
        error: (e: Error) => patchState(store, { error: e.message }),
        // outer rxMethod keeps running after this error — future calls work
      })
    ))
  )
),
```

## Common mistakes

### Mistake 1 — Mutating state directly instead of patchState

Signal Store's state is deep-frozen in dev mode. Mutating it directly throws:

```typescript
// ❌ Throws in dev mode — state is immutable
withMethods(store => ({
  addUser(user: User): void {
    store.users().push(user);    // mutation — error in dev mode
  }
})),

// ✅ patchState produces a new object
withMethods(store => ({
  addUser(user: User): void {
    patchState(store, state => ({ users: [...state.users, user] }));
  }
})),
```

### Mistake 2 — Injecting services in withMethods instead of withProps

`withMethods` receives the store object — `inject()` must be called outside of it,
in `withProps()`, which runs in the injection context:

```typescript
// ❌ inject() in withMethods — may fail depending on execution context
withMethods(store => ({
  load: rxMethod<void>(pipe(
    switchMap(() => inject(UserService).getAll().pipe(...))  // unreliable
  ))
})),

// ✅ inject() in withProps — guaranteed injection context
withProps(() => ({ _userService: inject(UserService) })),
withMethods(store => ({
  load: rxMethod<void>(pipe(
    switchMap(() => store._userService.getAll().pipe(...))   // correct
  ))
})),
```

### Mistake 3 — Passing store.signal() instead of store.signal to rxMethod

`rxMethod` accepts a `Signal<T>` reference — not the signal's current value.
Passing `store.query()` gives rxMethod a single string, not reactive tracking:

```typescript
withHooks({
  onInit(store): void {
    store.search(store.query());  // ❌ passes the current string value — static
    store.search(store.query);    // ✅ passes the Signal<string> — reactive
  }
})
```

### Mistake 4 — Using signalStore when signals alone are enough

Signal Store adds structure and DI integration. For simple shared state with
no async, a plain service with signals is simpler:

```typescript
// ❌ Signal Store overkill for three signals and two methods
export const ThemeStore = signalStore(
  { providedIn: 'root' },
  withState({ theme: 'light' as 'light' | 'dark' }),
  withMethods(store => ({
    toggle(): void { patchState(store, s => ({ theme: s.theme === 'light' ? 'dark' : 'light' })); }
  }))
);

// ✅ Plain injectable signal service is cleaner for simple cases
@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly theme = signal<'light' | 'dark'>('light');
  toggle(): void { this.theme.update(t => t === 'light' ? 'dark' : 'light'); }
}
```

Reach for Signal Store when you need: `rxMethod` for async, `withHooks` for
lifecycle, `withEntities` for collections, or custom reusable features. For
1–3 signals with simple sync methods, a plain service is fine.

## How this evolved

> - **NgRx v16 (2023):** `@ngrx/signals` introduced in **developer preview**
>   alongside `store.selectSignal()`. First release of `signalStore`,
>   `withState`, `withComputed`, `withMethods`, `patchState`.
>
> - **NgRx v17 (2023):** `withEntities` from `@ngrx/signals/entities`
>   introduced. `rxMethod` stabilized. `tapResponse` operator added to
>   `@ngrx/operators`.
>
> - **NgRx v18 (2024):** `withProps` added — clean injection context for
>   private dependencies. `signalStoreFeature` improved type inference.
>
> - **NgRx v19 (2024):** Signal Store graduated to **stable**. Community
>   DevTools integration via `@angular-architects/ngrx-toolkit` (`withDevtools`)
>   matured. `signalState` introduced as a lightweight alternative to
>   `signalStore` for stores that don't need DI or lifecycle hooks.
>
> - **Angular 22 / NgRx ~v20 (now):** NgRx Signal Store is the recommended
>   choice for feature-level and mid-size application state in new Angular
>   projects. NgRx Store remains for applications that need strict Redux
>   conventions, full official DevTools, and complex action-based orchestration.
>   The two can coexist in the same app.

## See also

- [NgRx Store](./ngrx.md) — the Redux-pattern alternative for apps that need
  strict conventions, full DevTools, and action audit trails
- [Signals](../reactivity/signals.md) — the Angular primitive Signal Store
  builds on; plain signal services for simpler cases
- [NGXS](./ngxs.md) — class-based state management, an alternative pattern
- [toSignal & toObservable](../reactivity/to-signal.md) — bridging rxMethod
  outputs with Observable-based code
- [Official docs — NgRx Signal Store](https://ngrx.io/guide/signals/signal-store)
- [Official docs — withEntities](https://ngrx.io/guide/signals/signal-store/entity-management)
- [Official docs — rxMethod](https://ngrx.io/guide/signals/rxjs-integration)

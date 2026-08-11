---
recipe_id: "ngrx-to-signal-store-migration"
title: "NgRx → Signal Store: Migrating Without a Big-Bang Rewrite"
file: "recipes/state-management/ngrx-to-signal-store-migration.md"
primary_concept: "state-management/ngrx"
related_concepts: ["reactivity/signals", "dependency-injection/dependency-injection", "http/http"]
demo_repo: null
angular_baseline: "22"
difficulty: "advanced"
status:
  upgraded: true
  reviewed: false
---

# NgRx → Signal Store: Migrating Without a Big-Bang Rewrite

> **What you'll build:** an incremental migration path from a
> classical NgRx codebase (actions, reducers, selectors, effects)
> to `@ngrx/signals` Signal Store. Both stores run side-by-side
> during the transition; features migrate one at a time; the
> bridge pattern handles cross-store dependencies until the last
> slice is converted. Concrete before/after for four common patterns
> plus honest guidance on which slices to migrate first and which
> to leave alone.
>
> **Concepts you'll touch:** [NgRx / State Management](../../concepts/state-management/ngrx.md), [Signals](../../concepts/reactivity/signals.md), [Dependency Injection](../../concepts/dependency-injection/dependency-injection.md), [HTTP](../../concepts/http/http.md)
>
> **Time:** ~35 minutes to read; the actual migration is
> feature-by-feature over weeks or months depending on codebase size.

---

## The scenario

You inherited an Angular 12 codebase upgraded to v22. It has 40 NgRx feature slices — cart, user, orders, products, notifications, and dozens more. The team knows NgRx but complains about the boilerplate:

- Adding a new field to a feature = touch actions, reducer, selectors, effect, component. 5 files for 1 field.
- Type-safe access is possible but requires discipline (correct `createFeatureSelector`, correct `createSelector` chains).
- New team members spend a week learning Redux vocabulary before they can ship.
- Simple state (a toggle, a modal-open flag) still requires the full action/reducer dance.

You've read about `@ngrx/signals` (Signal Store). It's ~60% less code for the same functionality. But you can't rewrite 40 slices in a sprint. Every slice you rewrite is a slice that has to keep working — production users depend on it.

**The strategy is incremental migration.** Both stores run at the same time. New features are written in Signal Store; old NgRx slices are migrated one at a time, leaf-first (features with no other-slice dependencies). During the transition, a bridge layer lets Signal Store slices read from NgRx slices that haven't been migrated yet. When the last NgRx slice ships to Signal Store, delete NgRx.

This recipe walks through that path.

---

## The two mental models — side by side

Before code, the mental shift:

| Concern | NgRx | Signal Store |
| --- | --- | --- |
| **State** | Immutable objects in a Store | State signals inside `signalStore()` |
| **Reads** | Selectors returning Observables | Computed signals, read synchronously |
| **Writes** | `store.dispatch(Action)` → reducer | Method call → `patchState(store, patch)` |
| **Async side effects** | `@Effect` classes with Actions stream | `rxMethod<T>()` on the store |
| **Cross-slice reads** | `createSelector` combining feature selectors | `inject(OtherStore)` in `withComputed` |
| **Feature registration** | `provideStore` / `provideState` | `signalStore({ providedIn: 'root' })` |
| **DevTools** | Full time-travel via Redux DevTools | `withDevtools()` gives read-only history |

**The load-bearing conceptual change**: NgRx is *event-driven* — you dispatch an event, the state responds. Signal Store is *procedure-driven* — you call a method, the state mutates. The former is powerful for logging, replay, and time-travel; the latter is much simpler for the common case.

The action-reducer indirection in NgRx makes sense when many things dispatch the same action or when you need audit history. For 90% of typical UI state (this modal is open, this list is loaded, this user is authenticated), the indirection is boilerplate without payoff.

---

## What migrates cleanly, what needs thought

Not every NgRx pattern maps 1:1 to Signal Store. A quick triage:

**Migrates cleanly:**

- Simple state slices (loading flags, form drafts, UI state)
- Entity collections (with `@ngrx/signals/entities`)
- Selectors → computed signals
- Simple effects (fetch data, save data)
- Cross-slice reads via composition

**Needs adaptation:**

- Effects that dispatch multiple actions in sequence → become methods that call other methods
- Effects with complex `withLatestFrom` chains → `rxMethod` with `pipe`
- Meta-reducers (logging, undo/redo) → `withHooks` or custom features
- Action-based analytics/logging → move to method interceptors or manual calls

**May stay in NgRx:**

- Codebases with heavy Redux DevTools time-travel usage in production debugging
- Slices with established third-party middleware (some analytics providers integrate via NgRx effects)
- Team investment / knowledge (if the team is more productive with NgRx, that's data)

The recipe below assumes you've decided to migrate. If Signal Store isn't the right choice for you, that's fine — the [Component Communication recipe](../components/component-communication.md) covers the "when NgRx is right" discussion.

---

## The migration playbook — five steps per slice

For each NgRx feature slice you migrate:

1. **Add the Signal Store version** alongside the existing NgRx slice. Both exist during the transition.
2. **Migrate components** to read from the new Signal Store. Keep the old NgRx slice populated (via a bridge or by dual-writing).
3. **Migrate mutations** — component code that dispatches NgRx actions now calls Signal Store methods.
4. **Migrate effects** — replace `@Effect` classes with `rxMethod` on the store.
5. **Delete the NgRx slice** — remove actions, reducer, effects, selectors, provider registration.

The five steps are per slice; the whole migration is one slice at a time. New features written from day one use Signal Store.

---

## Pattern 1 — simple feature slice

The base case. A slice with plain state, some methods to mutate it, and derived selectors.

### Before — NgRx

```typescript
// File: cart/cart.state.ts
export interface CartState {
  items: CartItem[];
  loading: boolean;
  error: string | null;
}

export const initialCartState: CartState = {
  items: [],
  loading: false,
  error: null,
};

// File: cart/cart.actions.ts
export const CartActions = createActionGroup({
  source: 'Cart',
  events: {
    'Load Cart': emptyProps(),
    'Load Cart Success': props<{ items: CartItem[] }>(),
    'Load Cart Failure': props<{ error: string }>(),
    'Add Item': props<{ item: CartItem }>(),
    'Remove Item': props<{ productId: string }>(),
    'Update Quantity': props<{ productId: string; quantity: number }>(),
    'Clear Cart': emptyProps(),
  },
});

// File: cart/cart.feature.ts
export const cartFeature = createFeature({
  name: 'cart',
  reducer: createReducer(
    initialCartState,
    on(CartActions.loadCart, state => ({ ...state, loading: true, error: null })),
    on(CartActions.loadCartSuccess, (state, { items }) =>
      ({ ...state, items, loading: false })),
    on(CartActions.loadCartFailure, (state, { error }) =>
      ({ ...state, loading: false, error })),
    on(CartActions.addItem, (state, { item }) => ({
      ...state,
      items: state.items.find(i => i.productId === item.productId)
        ? state.items.map(i =>
            i.productId === item.productId
              ? { ...i, quantity: i.quantity + item.quantity }
              : i,
          )
        : [...state.items, item],
    })),
    on(CartActions.removeItem, (state, { productId }) => ({
      ...state,
      items: state.items.filter(i => i.productId !== productId),
    })),
    on(CartActions.updateQuantity, (state, { productId, quantity }) => ({
      ...state,
      items: state.items.map(i =>
        i.productId === productId ? { ...i, quantity } : i,
      ),
    })),
    on(CartActions.clearCart, state => ({ ...state, items: [] })),
  ),
  extraSelectors: ({ selectItems }) => ({
    selectItemCount: createSelector(selectItems, items =>
      items.reduce((sum, item) => sum + item.quantity, 0),
    ),
    selectSubtotal: createSelector(selectItems, items =>
      items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    ),
    selectIsEmpty: createSelector(selectItems, items => items.length === 0),
  }),
});

// File: cart/cart.effects.ts
@Injectable()
export class CartEffects {
  private readonly actions$ = inject(Actions);
  private readonly http = inject(HttpClient);

  loadCart$ = createEffect(() =>
    this.actions$.pipe(
      ofType(CartActions.loadCart),
      switchMap(() =>
        this.http.get<CartItem[]>('/api/cart').pipe(
          map(items => CartActions.loadCartSuccess({ items })),
          catchError(error =>
            of(CartActions.loadCartFailure({ error: error.message })),
          ),
        ),
      ),
    ),
  );
}
```

Component usage:

```typescript
@Component({ /* … */ })
export class CartPageComponent {
  private readonly store = inject(Store);

  readonly items = this.store.selectSignal(cartFeature.selectItems);
  readonly itemCount = this.store.selectSignal(cartFeature.selectItemCount);
  readonly subtotal = this.store.selectSignal(cartFeature.selectSubtotal);
  readonly loading = this.store.selectSignal(cartFeature.selectLoading);

  constructor() {
    this.store.dispatch(CartActions.loadCart());
  }

  addItem(item: CartItem) {
    this.store.dispatch(CartActions.addItem({ item }));
  }

  removeItem(productId: string) {
    this.store.dispatch(CartActions.removeItem({ productId }));
  }
}
```

That's ~150 lines across four files, plus the provider registration.

### After — Signal Store

```typescript
// File: cart/cart.store.ts
import { computed, inject } from '@angular/core';
import { signalStore, withState, withComputed, withMethods, patchState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { pipe, switchMap, tap, catchError, of } from 'rxjs';

export interface CartItem {
  productId: string;
  name: string;
  price: number;
  quantity: number;
}

interface CartState {
  items: CartItem[];
  loading: boolean;
  error: string | null;
}

const initialState: CartState = {
  items: [],
  loading: false,
  error: null,
};

export const CartStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed(({ items }) => ({
    itemCount: computed(() =>
      items().reduce((sum, item) => sum + item.quantity, 0),
    ),
    subtotal: computed(() =>
      items().reduce((sum, item) => sum + item.price * item.quantity, 0),
    ),
    isEmpty: computed(() => items().length === 0),
  })),
  withMethods((store, http = inject(HttpClient)) => ({
    addItem(item: CartItem): void {
      const existing = store.items().find(i => i.productId === item.productId);
      const items = existing
        ? store.items().map(i =>
            i.productId === item.productId
              ? { ...i, quantity: i.quantity + item.quantity }
              : i,
          )
        : [...store.items(), item];
      patchState(store, { items });
    },

    removeItem(productId: string): void {
      patchState(store, {
        items: store.items().filter(i => i.productId !== productId),
      });
    },

    updateQuantity(productId: string, quantity: number): void {
      if (quantity <= 0) {
        this.removeItem(productId);
        return;
      }
      patchState(store, {
        items: store.items().map(i =>
          i.productId === productId ? { ...i, quantity } : i,
        ),
      });
    },

    clear(): void {
      patchState(store, { items: [] });
    },

    loadCart: rxMethod<void>(
      pipe(
        tap(() => patchState(store, { loading: true, error: null })),
        switchMap(() =>
          http.get<CartItem[]>('/api/cart').pipe(
            tap(items => patchState(store, { items, loading: false })),
            catchError(error => {
              patchState(store, { loading: false, error: error.message });
              return of(null);
            }),
          ),
        ),
      ),
    ),
  })),
);
```

Component usage:

```typescript
@Component({ /* … */ })
export class CartPageComponent {
  protected readonly cart = inject(CartStore);

  constructor() {
    this.cart.loadCart();
  }
}
```

Template:

```html
@if (cart.loading()) {
  <p>Loading…</p>
} @else if (cart.isEmpty()) {
  <p>Your cart is empty.</p>
} @else {
  @for (item of cart.items(); track item.productId) {
    <div>
      {{ item.name }} — {{ item.quantity }} × {{ item.price }}
      <button (click)="cart.removeItem(item.productId)">Remove</button>
    </div>
  }
  <p>Total: {{ cart.subtotal() }}</p>
}
```

That's ~70 lines in one file. **~60% code reduction** for the same functionality, with the same or better type safety.

**Five things worth absorbing:**

- **`withState(initialState)`** replaces the entire state interface + reducer boilerplate. State signals are auto-generated from the shape.
- **`withComputed`** replaces the entire selectors file. Computed signals are memoized automatically (like `createSelector` was).
- **`withMethods`** replaces both the action/reducer file AND the effect file. Methods are just method calls — no dispatch, no ofType filtering.
- **`patchState(store, partial)`** replaces `on(Action, (state, props) => ({ ...state, ... }))`. Partial patches are merged into the state signal.
- **`rxMethod`** for async work — receives a pipe that runs on every method call. `switchMap`/`tap`/`catchError` compose exactly like they did in effects, but the trigger is a direct method call, not an action.

---

## Pattern 2 — entity feature (with `withEntities`)

NgRx's `EntityAdapter` is popular for entity collections (things with IDs). Signal Store has `withEntities` from `@ngrx/signals/entities` that provides the same normalized-collection primitives.

### Before — NgRx

```typescript
// File: products/products.state.ts
import { EntityState, EntityAdapter, createEntityAdapter } from '@ngrx/entity';

export interface Product {
  id: string;
  name: string;
  price: number;
  category: string;
}

export interface ProductsState extends EntityState<Product> {
  loading: boolean;
  selectedId: string | null;
}

export const adapter: EntityAdapter<Product> = createEntityAdapter<Product>({
  selectId: (product) => product.id,
  sortComparer: (a, b) => a.name.localeCompare(b.name),
});

export const initialState: ProductsState = adapter.getInitialState({
  loading: false,
  selectedId: null,
});

// File: products/products.reducer.ts
const productsReducer = createReducer(
  initialState,
  on(ProductsActions.loadProducts, state => ({ ...state, loading: true })),
  on(ProductsActions.loadProductsSuccess, (state, { products }) =>
    adapter.setAll(products, { ...state, loading: false }),
  ),
  on(ProductsActions.addProduct, (state, { product }) =>
    adapter.addOne(product, state),
  ),
  on(ProductsActions.updateProduct, (state, { update }) =>
    adapter.updateOne(update, state),
  ),
  on(ProductsActions.removeProduct, (state, { id }) =>
    adapter.removeOne(id, state),
  ),
  on(ProductsActions.selectProduct, (state, { id }) =>
    ({ ...state, selectedId: id }),
  ),
);

// File: products/products.selectors.ts
const { selectAll, selectEntities, selectIds, selectTotal } = adapter.getSelectors();

export const productsFeature = createFeature({
  name: 'products',
  reducer: productsReducer,
  extraSelectors: ({ selectProductsState }) => ({
    selectAll: createSelector(selectProductsState, selectAll),
    selectEntities: createSelector(selectProductsState, selectEntities),
    selectTotal: createSelector(selectProductsState, selectTotal),
    selectSelectedId: createSelector(selectProductsState, s => s.selectedId),
    selectSelectedProduct: createSelector(
      selectProductsState,
      s => s.selectedId ? s.entities[s.selectedId] : null,
    ),
  }),
});
```

### After — Signal Store with `withEntities`

```typescript
// File: products/products.store.ts
import { computed, inject } from '@angular/core';
import { signalStore, withState, withComputed, withMethods, patchState } from '@ngrx/signals';
import {
  withEntities,
  setAllEntities,
  addEntity,
  updateEntity,
  removeEntity,
} from '@ngrx/signals/entities';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { pipe, switchMap, tap } from 'rxjs';

export interface Product {
  id: string;
  name: string;
  price: number;
  category: string;
}

export const ProductsStore = signalStore(
  { providedIn: 'root' },
  withState({ loading: false, selectedId: null as string | null }),
  withEntities<Product>(),
  withComputed(({ entities, selectedId }) => ({
    total: computed(() => entities().length),
    selectedProduct: computed(() => {
      const id = selectedId();
      if (!id) return null;
      return entities().find(p => p.id === id) ?? null;
    }),
    productsByCategory: computed(() => {
      const grouped: Record<string, Product[]> = {};
      for (const product of entities()) {
        (grouped[product.category] ??= []).push(product);
      }
      return grouped;
    }),
  })),
  withMethods((store, http = inject(HttpClient)) => ({
    selectProduct(id: string | null): void {
      patchState(store, { selectedId: id });
    },

    addProduct(product: Product): void {
      patchState(store, addEntity(product));
    },

    updateProduct(id: string, changes: Partial<Product>): void {
      patchState(store, updateEntity({ id, changes }));
    },

    removeProduct(id: string): void {
      patchState(store, removeEntity(id));
    },

    loadProducts: rxMethod<void>(
      pipe(
        tap(() => patchState(store, { loading: true })),
        switchMap(() =>
          http.get<Product[]>('/api/products').pipe(
            tap(products =>
              patchState(store, setAllEntities(products), { loading: false }),
            ),
          ),
        ),
      ),
    ),
  })),
);
```

Component usage:

```typescript
@Component({ /* … */ })
export class ProductsListComponent {
  protected readonly products = inject(ProductsStore);

  constructor() {
    this.products.loadProducts();
  }
}
```

Template:

```html
@for (product of products.entities(); track product.id) {
  <div (click)="products.selectProduct(product.id)">
    {{ product.name }}
  </div>
}
@if (products.selectedProduct(); as selected) {
  <div>Selected: {{ selected.name }}</div>
}
```

**Three things worth absorbing:**

- **`withEntities<Product>()`** auto-generates `entities` (array signal) and `entityMap` (dictionary signal) from the entity type. `Product` needs an `id: string` field by default; a custom `idKey` is available if your entities key by something else.
- **`setAllEntities`, `addEntity`, `updateEntity`, `removeEntity`** are the equivalents of `adapter.setAll`, `adapter.addOne`, etc. They return partials that `patchState` applies. Multiple can be composed: `patchState(store, addEntity(product), { loading: false })`.
- **The sort comparator moves to a computed** if needed — no built-in sort in `withEntities`. If you need auto-sorted entities, add a `sortedEntities = computed(() => [...entities()].sort(...))`.

---

## Pattern 3 — effect → `rxMethod`

The most conceptually different mapping. NgRx effects listen for actions; Signal Store `rxMethod` runs when the method is called directly.

### Before — NgRx effect

```typescript
@Injectable()
export class SearchEffects {
  private readonly actions$ = inject(Actions);
  private readonly http = inject(HttpClient);

  search$ = createEffect(() =>
    this.actions$.pipe(
      ofType(SearchActions.query),
      debounceTime(300),
      distinctUntilChanged((a, b) => a.term === b.term),
      switchMap(({ term }) =>
        this.http.get<SearchResult[]>(`/api/search?q=${term}`).pipe(
          map(results => SearchActions.querySuccess({ results })),
          catchError(error => of(SearchActions.queryFailure({ error }))),
        ),
      ),
    ),
  );
}
```

Component dispatches an action to trigger:

```typescript
this.store.dispatch(SearchActions.query({ term }));
```

### After — Signal Store `rxMethod`

```typescript
export const SearchStore = signalStore(
  { providedIn: 'root' },
  withState({
    term: '',
    results: [] as SearchResult[],
    loading: false,
    error: null as string | null,
  }),
  withMethods((store, http = inject(HttpClient)) => ({
    search: rxMethod<string>(
      pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(term => patchState(store, { term, loading: true, error: null })),
        switchMap(term =>
          http.get<SearchResult[]>(`/api/search?q=${term}`).pipe(
            tap(results => patchState(store, { results, loading: false })),
            catchError(error => {
              patchState(store, { loading: false, error: error.message });
              return of([]);
            }),
          ),
        ),
      ),
    ),
  })),
);
```

Component calls the method directly:

```typescript
@Component({ /* … */ })
export class SearchComponent {
  protected readonly search = inject(SearchStore);

  onInput(term: string) {
    this.search.search(term);   // triggers the rxMethod pipeline
  }
}
```

**Three things worth absorbing:**

- **The pipe operators are identical** to the NgRx effect — `debounceTime`, `distinctUntilChanged`, `switchMap`, etc. Composition patterns from RxJS carry over exactly. The [race-conditions recipe](../reactivity/race-conditions.md) applies verbatim.
- **The trigger is the method call**, not an action dispatch. `search.search('typescript')` fires the pipe with `'typescript'` as the source value. The type parameter (`rxMethod<string>`) constrains input.
- **The pipe subscribes on first method call** and stays subscribed for the store's lifetime. Later calls emit into the same pipe. `takeUntilDestroyed` is handled internally by `rxMethod` — no leak.

### rxMethod with a signal source

`rxMethod` can also accept a signal as input, running the pipe automatically when the signal changes:

```typescript
// In the store's methods:
loadUserProfile: rxMethod<string>(
  pipe(
    switchMap(userId => http.get<Profile>(`/api/users/${userId}`)),
    tap(profile => patchState(store, { profile })),
  ),
),

// In a component:
const authStore = inject(AuthStore);
const profileStore = inject(ProfileStore);

// Automatically re-fetches whenever the currentUserId signal changes
profileStore.loadUserProfile(authStore.currentUserId);
```

Passing the signal itself (`authStore.currentUserId`) instead of its current value (`authStore.currentUserId()`) makes `rxMethod` subscribe reactively. This is the Signal Store equivalent of "effect with `withLatestFrom(store.select(...))`" — much cleaner.

---

## Pattern 4 — cross-slice composition

NgRx often has selectors that combine multiple feature slices (`createSelector(featureA.select, featureB.select, (a, b) => ...)`). Signal Store handles this by injecting one store into another.

### Before — NgRx cross-slice selector

```typescript
// File: checkout/checkout.selectors.ts
export const selectCanCheckout = createSelector(
  cartFeature.selectItemCount,
  userFeature.selectIsAuthenticated,
  userFeature.selectHasPaymentMethod,
  (itemCount, isAuth, hasPayment) => itemCount > 0 && isAuth && hasPayment,
);
```

### After — Signal Store composition

```typescript
export const CheckoutStore = signalStore(
  { providedIn: 'root' },
  withState({ /* … */ }),
  withComputed((store, cart = inject(CartStore), user = inject(UserStore)) => ({
    canCheckout: computed(() =>
      cart.itemCount() > 0 && user.isAuthenticated() && user.hasPaymentMethod(),
    ),
  })),
  withMethods((store, cart = inject(CartStore), user = inject(UserStore), http = inject(HttpClient)) => ({
    placeOrder: rxMethod<void>(
      pipe(
        switchMap(() =>
          http.post<Order>('/api/orders', {
            items: cart.items(),
            userId: user.currentUserId(),
          }),
        ),
        tap(() => cart.clear()),
      ),
    ),
  })),
);
```

**Two things worth absorbing:**

- **`inject()` inside `withComputed`/`withMethods`** — you can inject other stores (or any DI-provided value) using default parameter values. The signature `withComputed((store, cart = inject(CartStore))` gives you both the current store's state and the injected `CartStore`.
- **Direct signal reads across stores** — `cart.itemCount()` reads the sibling store's signal. Reactivity flows automatically; when the cart's `itemCount` changes, the `canCheckout` computed re-runs.

The composition is simpler than NgRx's `createSelector` chains because there's no plumbing — inject the other store, read its signals, done.

---

## The bridge pattern — cross-store during migration

The migration is incremental. What happens when your new Signal Store needs data from an NgRx slice that hasn't been migrated yet?

**Two options:**

### Option 1 — bridge via `toSignal`

Convert an NgRx selector to a signal, then use it in the Signal Store:

```typescript
export const NewFeatureStore = signalStore(
  { providedIn: 'root' },
  withState({ /* … */ }),
  withComputed((store, ngrxStore = inject(Store)) => {
    // Bridge: NgRx selector → Signal via toSignal
    const currentUserFromNgRx = toSignal(
      ngrxStore.select(userFeature.selectCurrentUser),
      { initialValue: null },
    );

    return {
      combined: computed(() => {
        const user = currentUserFromNgRx();
        // …use user + new feature state…
      }),
    };
  }),
);
```

Note: `toSignal` needs an injection context, which `withComputed`'s function provides. This works because Signal Store's factory functions run during store instantiation, which is an injection context.

### Option 2 — read-through service

If the bridge is used in many places, wrap it in a service:

```typescript
@Injectable({ providedIn: 'root' })
export class UserBridgeService {
  private readonly ngrxStore = inject(Store);

  readonly currentUser = toSignal(
    this.ngrxStore.select(userFeature.selectCurrentUser),
    { initialValue: null },
  );

  readonly isAuthenticated = toSignal(
    this.ngrxStore.select(userFeature.selectIsAuthenticated),
    { initialValue: false },
  );

  dispatchLogout(): void {
    this.ngrxStore.dispatch(UserActions.logout());
  }
}
```

New Signal Stores inject `UserBridgeService`; they never touch NgRx directly. When the user slice is migrated to Signal Store, only the bridge service needs to change — the consuming Signal Stores keep working with a wrapper that now delegates to the new `UserStore`.

**This is the recommended pattern for large migrations.** The bridge is a single point of change; you don't have to update N Signal Stores each time you migrate a source slice.

---

## Migration order — which slices first

The order matters. Migrating a heavily-depended-upon slice (auth, user) first means the bridge from Signal Store to NgRx is temporary and short-lived; migrating leaf slices first means the bridge lives longer but is simpler.

**Recommended order:**

1. **Standalone leaf slices first.** Features with no other-slice dependencies — a "notifications preferences" slice, a "UI settings" slice, a "recently viewed" slice. Practice the migration mechanics without cross-slice complexity.
2. **Non-critical mid-tier slices.** Features that depend on 1-2 other slices but aren't in the critical path. Give the team confidence and pattern familiarity.
3. **New features from day one.** As you migrate, all new features get built in Signal Store. This makes the NgRx surface strictly shrinking.
4. **Cross-cutting concerns last.** Auth, user, permissions. These are read by everything. Migrating them requires either (a) bridging back to Signal Store from remaining NgRx slices (reverse direction), or (b) doing this migration when only a few NgRx slices remain.

**Anti-pattern**: migrating a heavily-used slice first. Every Signal Store that reads from the (still-NgRx) auth slice would go through the bridge; when auth migrates, all bridges break. Migrate auth once you have the fewest possible slices depending on it.

### Timeline

For a 40-slice codebase, expect:

- Week 1-2: Set up Signal Store package, migrate first leaf slice, establish team patterns
- Weeks 3-8: Migrate leaf and mid-tier slices, 2-4 per week depending on team size
- Weeks 9-16: Migrate cross-cutting slices (auth, user) with careful bridge management
- Week 17+: Final cleanup, remove NgRx packages from `package.json`

Aggressive teams can compress this. Cautious teams take longer. The point is that it's continuous, not big-bang.

---

## When Signal Store isn't the right migration target

The recipe assumes you've decided to migrate. Cases where you shouldn't:

- **Heavy Redux DevTools time-travel usage in production debugging.** Signal Store has `withDevtools()` for readonly history, but full time-travel is NgRx-specific.
- **Established action-based analytics/logging middleware.** If every action fires an analytics event via effect middleware, migrating means rewriting that layer.
- **Third-party effect libraries.** Some libraries provide effects (e.g., some Sentry integrations). If you depend on them, migrating means finding alternatives.
- **Team resistance without data.** If the team is productive with NgRx and doesn't feel constrained by it, forcing migration is architectural churn without payoff.

**For hybrid teams**: keep NgRx for the slices where the action-reducer model earns its keep (audit-critical, complex effects, time-travel debugging) and use Signal Store for everything else. Both coexist indefinitely. The bridge pattern makes this viable long-term.

---

## Trade-offs and common pitfalls

**Use Signal Store when:**

- The codebase has significant NgRx boilerplate for simple state
- The team is comfortable with signals (or willing to learn)
- Time-travel debugging isn't heavily used in production workflows
- New features are being built and can adopt Signal Store from the start

**Keep NgRx when:**

- Production debugging depends on Redux DevTools time-travel
- Established action-based middleware ecosystem is in use
- Team investment / knowledge tips the productivity scale toward NgRx

### Common pitfalls

- **Big-bang migration.** Rewriting 40 slices in a sprint. Guarantees production bugs. Migrate slice-by-slice with tests.
- **Two sources of truth during migration.** Same state in both NgRx and Signal Store, both being written to by different code paths. They drift. Pick one source per slice; the other reads via a bridge.
- **Effects still firing after slice removal.** You migrated the reducer but forgot the effect; it dispatches actions no one listens to. Delete effects in the same PR as the reducer.
- **Components reading both stores for related data.** UI shows an inconsistent view because half the reads are from NgRx (which has been updated) and half from Signal Store (which hasn't). Bridge one to the other; don't dual-read.
- **`inject()` outside injection context.** `withComputed` and `withMethods` factories ARE injection contexts, but functions inside them (called later, at runtime) aren't. `inject()` calls belong in the factory signature (as default parameters), not inside method bodies.
- **Forgetting `patchState` for updates.** Reading `store.items()` and mutating the array directly (`store.items().push(item)`) doesn't update the signal — signals require immutable updates. Always go through `patchState`.
- **`rxMethod` with side effects that assume synchronous flow.** `rxMethod`'s pipeline is asynchronous; the method call returns immediately. Don't chain synchronous calls after it expecting the pipeline to have completed.
- **Not clearing Signal Store state on logout.** Root-provided stores persist across navigation. When a user logs out, their cart / notifications / etc. should reset. Add a `reset()` method to each store and call from `logout()`.
- **Team members writing new code in the old style.** Without a clear policy ("new features MUST use Signal Store"), the NgRx surface stops shrinking. Update contribution guidelines; PR review catches drift.
- **DevTools showing incorrect state during migration.** Redux DevTools show only NgRx state; Signal Store's `withDevtools` shows only Signal Store state. Debugging a bug that spans both requires flipping between tools. Document this for the team.
- **`withEntities` with a non-standard ID field.** Default assumes `id`. If your entities key on `_id` (MongoDB) or `uuid`, configure explicitly: `withEntities<Product>({ selectId: (p) => p.uuid })`.
- **Serializing signal store state for SSR / debugging.** Signals aren't JSON-serializable directly; you need to call each one to get its value. Build a helper if you export state snapshots frequently.

---

## See also

- [NgRx / State Management](../../concepts/state-management/ngrx.md) — the concept article; deeper coverage of both NgRx and Signal Store patterns
- [Component Communication](../components/component-communication.md) — the "when NgRx is right" discussion; also covers the signal-service pattern that's an alternative to Signal Store for simpler cases
- [Signals](../../concepts/reactivity/signals.md) — the underlying reactivity model
- [Race Conditions](../reactivity/race-conditions.md) — RxJS operators used in `rxMethod` pipes work identically
- [Optimistic Updates](../form-and-search/optimistic-updates.md) — the snapshot/restore pattern; Signal Store makes this even cleaner because the whole state can be snapshotted as one call
- [Request Deduplication](../http/request-deduplication.md) — cache invalidation via mutation is straightforward with Signal Store methods

## References

- [`@ngrx/signals` (ngrx.io)](https://ngrx.io/guide/signals) — Signal Store official documentation
- [`@ngrx/signals/entities` (ngrx.io)](https://ngrx.io/guide/signals/signal-store/entity-management) — entity management
- [`rxMethod` (ngrx.io)](https://ngrx.io/guide/signals/rxjs-integration) — RxJS interop for methods
- [`withDevtools` (ngrx.io)](https://ngrx.io/guide/signals/signal-store/devtools) — Redux DevTools integration for Signal Store
- [Migrating from NgRx Store to Signal Store (Angular Architects)](https://www.angulararchitects.io/en/blog/) — community guides on migration
- [Signal Store recipes (ngrx.io)](https://ngrx.io/guide/signals/signal-store/recipes) — patterns for common use cases

## Demo source

Synthesized from real-world NgRx-to-Signal-Store migration patterns rather than a single demo file. The 5-step-per-slice playbook, the bridge pattern for cross-store dependencies, and the "leaf-first" migration order reflect the strategies that most teams converge on after their first few slices. The recipe is honest about when NgRx should stay — not every migration is the right migration. All code is original.
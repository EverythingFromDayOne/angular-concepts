---
recipe_id: "component-communication"
title: "Component Communication: When NgRx Is Overkill (And When It Isn't)"
file: "recipes/components/component-communication.md"
primary_concept: "components/component-interactions"
related_concepts: ["reactivity/signals", "dependency-injection/dependency-injection", "routing/routing", "state-management/ngrx"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Component Communication: When NgRx Is Overkill (And When It Isn't)

> **What you'll build:** a working answer to the most common Angular
> architectural question — "where should this shared state live?" Five
> concrete patterns (shared service with signals, event-based service,
> router state, subtree-scoped service, parent-child `input`/`output`
> chains), a decision tree that maps situations to patterns, and an
> honest framing of when NgRx is actually the right answer rather than
> a reflex.
>
> **Concepts you'll touch:** [Component interactions](../../components/component-interactions.md), [Signals](../../reactivity/signals.md), [Dependency Injection](../../dependency-injection/dependency-injection.md), [Routing](../../routing/routing.md), [NgRx](../../state-management/ngrx.md)
>
> **Time:** ~30 minutes to read; ~3 hours to audit your codebase for
> patterns that aren't matching this decision tree.

---

## The scenario

An e-commerce app. Five different components need to know about the shopping cart:

- `<app-header>` shows the cart icon with a badge count
- `<app-product-card>` (nested 4 levels deep inside the product grid) has an "Add to cart" button
- `<app-cart-drawer>` is a modal that shows full cart contents
- `<app-checkout-page>` is a route component that reads cart for the total
- `<app-mini-cart-recommendations>` reads cart contents to show "frequently bought together" suggestions

The first instinct is `@Input` / `@Output` — pass `cart` down from the root, emit events up. After implementing it, the app has:

- Eight components that all carry `@Input() cart` even though they never directly use it (they just pass it down to the next level)
- Six `@Output() addToCart` event chains that propagate identical events through different paths
- The `AppComponent` template knows about every detail of every page's cart needs because everything flows through it
- Adding a sixth component that needs cart access means modifying every component between root and target

This is the **prop-drilling** anti-pattern. The Angular fix is to lift the state into a service. The substance of this recipe is which kind of service — and when other patterns are actually better.

---

## Pattern 1 — shared service with signals (the v22 default)

For state that multiple components need to read AND mutate, a singleton service with signals is almost always the right answer:

```typescript
// File: services/cart.service.ts
import { Injectable, computed, signal } from '@angular/core';

export interface CartItem {
  productId: string;
  name: string;
  price: number;
  quantity: number;
}

@Injectable({ providedIn: 'root' })
export class CartService {
  // Private writable signal — only the service can mutate it.
  private readonly items = signal<CartItem[]>([]);

  // Public readonly signal — components can read but not modify directly.
  readonly cartItems = this.items.asReadonly();

  // Derived state via computed() — automatically updates when items() changes.
  readonly itemCount = computed(() =>
    this.items().reduce((sum, item) => sum + item.quantity, 0),
  );

  readonly subtotal = computed(() =>
    this.items().reduce((sum, item) => sum + item.price * item.quantity, 0),
  );

  readonly isEmpty = computed(() => this.items().length === 0);

  addItem(product: { id: string; name: string; price: number }, quantity: number = 1): void {
    this.items.update(current => {
      const existing = current.find(i => i.productId === product.id);
      if (existing) {
        return current.map(i =>
          i.productId === product.id ? { ...i, quantity: i.quantity + quantity } : i,
        );
      }
      return [...current, { productId: product.id, name: product.name, price: product.price, quantity }];
    });
  }

  removeItem(productId: string): void {
    this.items.update(current => current.filter(i => i.productId !== productId));
  }

  updateQuantity(productId: string, quantity: number): void {
    if (quantity <= 0) {
      this.removeItem(productId);
      return;
    }
    this.items.update(current =>
      current.map(i => (i.productId === productId ? { ...i, quantity } : i)),
    );
  }

  clear(): void {
    this.items.set([]);
  }
}
```

Any component injects and reads/writes:

```typescript
// File: header.component.ts
@Component({
  selector: 'app-header',
  template: `
    <header>
      <span>My Store</span>
      <app-cart-icon />
    </header>
  `,
})
export class HeaderComponent {}

// File: cart-icon.component.ts
@Component({
  selector: 'app-cart-icon',
  template: `
    <button (click)="openCart()">
      🛒
      @if (cart.itemCount() > 0) {
        <span class="badge">{{ cart.itemCount() }}</span>
      }
    </button>
  `,
})
export class CartIconComponent {
  protected readonly cart = inject(CartService);
  openCart() { /* … */ }
}

// File: product-card.component.ts (nested 4 levels deep — doesn't matter)
@Component({
  selector: 'app-product-card',
  template: `
    <div class="card">
      <h3>{{ product().name }}</h3>
      <p>{{ product().price | currency }}</p>
      <button (click)="addToCart()">Add to cart</button>
    </div>
  `,
})
export class ProductCardComponent {
  protected readonly product = input.required<Product>();
  private readonly cart = inject(CartService);

  addToCart() {
    this.cart.addItem(this.product());
  }
}
```

**Five things doing the work:**

- **`private readonly items = signal(...)` + `readonly cartItems = this.items.asReadonly()`** — the encapsulation pattern. The private writable signal stays inside the service; consumers get a `Signal<CartItem[]>` (readonly type) that they can subscribe to but can't `.set()` or `.update()`. Mutations go through service methods, which means business rules (clamp quantity at 0, merge duplicate items, etc.) are enforced in one place.

- **`computed()` for derived state.** `itemCount`, `subtotal`, `isEmpty` are not stored — they're recomputed reactively when `items()` changes. Components that read `subtotal()` re-render only when the subtotal actually changes (not when any cart field changes).

- **`inject()` over constructor injection.** Field initializer style is the v22 idiom.

- **Components read signals directly in templates** — `cart.itemCount()`. No `async` pipe, no `BehaviorSubject`, no subscribe/unsubscribe dance. Change detection runs when the signal updates.

- **No event chains.** `ProductCardComponent` calls `cart.addItem()` directly. The header's `CartIconComponent` reactively sees the new count. No event bubbles through six parent components.

### When this isn't enough — service-on-service composition

For state that's derived from multiple services, just have one service inject another:

```typescript
@Injectable({ providedIn: 'root' })
export class CheckoutService {
  private readonly cart = inject(CartService);
  private readonly user = inject(UserService);

  readonly canCheckout = computed(() =>
    this.cart.itemCount() > 0 && this.user.isAuthenticated()
  );

  readonly checkoutSummary = computed(() => ({
    items: this.cart.cartItems(),
    subtotal: this.cart.subtotal(),
    customerEmail: this.user.email(),
  }));
}
```

Clean composition. The dependency graph stays explicit and readable.

---

## Pattern 2 — event-based service with `Subject`

For **events** (fire-and-forget signals) rather than state, use a `Subject`. The classic example is a notification/toast system:

```typescript
// File: services/notification.service.ts
import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly events = new Subject<Toast>();
  readonly events$: Observable<Toast> = this.events.asObservable();

  show(message: string, type: Toast['type'] = 'info', duration: number = 3000): void {
    this.events.next({
      id: crypto.randomUUID(),
      message,
      type,
      duration,
    });
  }

  success(message: string) { this.show(message, 'success'); }
  error(message: string) { this.show(message, 'error', 6000); }
  warning(message: string) { this.show(message, 'warning'); }
}
```

A toast container component (mounted once at the app root) subscribes:

```typescript
@Component({
  selector: 'app-toast-container',
  template: `
    <div class="toast-stack">
      @for (toast of toasts(); track toast.id) {
        <div class="toast" [class]="toast.type">
          {{ toast.message }}
        </div>
      }
    </div>
  `,
})
export class ToastContainerComponent {
  private readonly notifications = inject(NotificationService);
  protected readonly toasts = signal<Toast[]>([]);

  constructor() {
    this.notifications.events$.pipe(
      takeUntilDestroyed(),
    ).subscribe(toast => {
      this.toasts.update(current => [...current, toast]);
      if (toast.duration) {
        setTimeout(() => {
          this.toasts.update(current => current.filter(t => t.id !== toast.id));
        }, toast.duration);
      }
    });
  }
}
```

Any component fires a toast:

```typescript
saveProfile() {
  this.api.save(this.profile()).subscribe({
    next: () => this.notifications.success('Profile saved'),
    error: () => this.notifications.error('Could not save — please retry'),
  });
}
```

**Three patterns doing the work:**

- **`Subject` instead of `signal`.** Subjects emit values and forget them — perfect for events with no "current state" semantics. Signals have a current value at all times; Subjects represent "something happened at time T."

- **`takeUntilDestroyed()` on the subscription.** The toast container is a long-lived component, but the rule is uniform: every Observable subscription in a component gets `takeUntilDestroyed`.

- **The event payload contains everything needed to react.** No "look up state from the service" — the event is self-contained. Each toast carries its message, type, and duration.

### When to use Subject vs Signal for state

The dividing line:

- **Signal**: "What is the current value of X?" — cart contents, current user, theme preference, route data
- **Subject**: "What just happened?" — toast fired, modal opened, action completed, scroll event

Confusing them is a common bug. Storing cart state in a `Subject<CartItem[]>` means a component that subscribes *after* the cart was last updated doesn't know what's in the cart — Subjects don't replay. Storing toast events in a `signal<Toast | null>` works for one toast at a time but breaks if two toasts fire close together (the second overwrites the first before the UI sees it).

`BehaviorSubject` sits between the two (has a current value AND emits to new subscribers), but for new code, prefer signals for state. The choice between `Subject` and `BehaviorSubject` matters mostly when bridging to/from existing RxJS code.

---

## Pattern 3 — router state (for URL-persistent state)

Some state should survive page reloads and be shareable via URL. Filter selections, search queries, pagination offsets, selected tabs. The router is the right "service" for that — and it's already there.

```typescript
// File: services/product-filters.service.ts
import { Injectable, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs/operators';

export interface ProductFilters {
  category: string;
  priceMin: number;
  priceMax: number;
  sortBy: 'newest' | 'price-asc' | 'price-desc' | 'popular';
  page: number;
}

const DEFAULTS: ProductFilters = {
  category: 'all',
  priceMin: 0,
  priceMax: Number.MAX_SAFE_INTEGER,
  sortBy: 'newest',
  page: 1,
};

@Injectable({ providedIn: 'root' })
export class ProductFiltersService {
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  // The filters signal is derived from the URL's query params.
  readonly filters = toSignal(
    this.route.queryParamMap.pipe(
      map(params => ({
        category: params.get('cat') ?? DEFAULTS.category,
        priceMin: Number(params.get('pmin')) || DEFAULTS.priceMin,
        priceMax: Number(params.get('pmax')) || DEFAULTS.priceMax,
        sortBy: (params.get('sort') as ProductFilters['sortBy']) ?? DEFAULTS.sortBy,
        page: Number(params.get('p')) || DEFAULTS.page,
      })),
    ),
    { initialValue: DEFAULTS },
  );

  update(partial: Partial<ProductFilters>): void {
    const next = { ...this.filters(), ...partial };
    this.router.navigate([], {
      queryParams: this.toQueryParams(next),
      queryParamsHandling: '',  // replace entirely (not 'merge')
    });
  }

  private toQueryParams(f: ProductFilters): Record<string, string | null> {
    return {
      cat: f.category === DEFAULTS.category ? null : f.category,
      pmin: f.priceMin === DEFAULTS.priceMin ? null : String(f.priceMin),
      pmax: f.priceMax === DEFAULTS.priceMax ? null : String(f.priceMax),
      sort: f.sortBy === DEFAULTS.sortBy ? null : f.sortBy,
      p: f.page === DEFAULTS.page ? null : String(f.page),
    };
  }
}
```

Components read and write through the service:

```typescript
@Component({ /* … */ })
export class ProductGridComponent {
  protected readonly filters = inject(ProductFiltersService);

  // Reactively re-fetch when filters change
  readonly products = computed(() => {
    const f = this.filters.filters();
    return this.fetchProducts(f);  // returns Observable; bridge appropriately
  });

  changeSortOrder(sortBy: ProductFilters['sortBy']) {
    this.filters.update({ sortBy, page: 1 });  // reset to page 1 on sort
  }
}
```

**Three patterns worth absorbing:**

- **`toSignal(route.queryParamMap.pipe(map(...)))`** — the bridge from RxJS (the router's stream) to signals (the component's read). The signal updates whenever the URL changes.

- **Defaults are excluded from the URL** (`f.category === DEFAULTS.category ? null : f.category`). The URL stays clean — `/products` not `/products?cat=all&pmin=0&pmax=999999&sort=newest&p=1`. Sharing the URL keeps just the meaningful state.

- **Filter updates trigger navigation, not direct signal writes.** The signal is *derived* from the URL — the source of truth is the URL. Updates go through `router.navigate`; the queryParamMap subscription fires; the signal updates. One direction; no inconsistency.

### When to use router state

| Concern | Router state? |
| --- | --- |
| URL should reflect the state (shareable, bookmarkable) | Yes |
| State should survive page reload | Yes |
| Browser back button should toggle the state | Yes |
| State is sensitive (password, payment) | No — never in URL |
| State changes very frequently (mouse position) | No — query param updates are too coarse |
| State is large (full document content) | No — URL has length limits |

Filters, search queries, current tab, modal-open flag (debatable), page number — all good fits. Cart contents — usually wrong (you don't want a URL that contains the cart).

---

## Pattern 4 — subtree-scoped service

Sometimes state should be shared by a section of the app but not globally. A wizard flow has its own state; a modal has its own state; a feature module's components might share state that's irrelevant to the rest of the app.

```typescript
// File: services/wizard-state.service.ts
@Injectable()  // NOT providedIn: 'root' — provided per component
export class WizardStateService {
  readonly currentStep = signal(0);
  readonly answers = signal<Record<string, unknown>>({});

  next() { this.currentStep.update(s => s + 1); }
  previous() { this.currentStep.update(s => Math.max(0, s - 1)); }
  setAnswer(key: string, value: unknown) {
    this.answers.update(current => ({ ...current, [key]: value }));
  }
}
```

Provide it on a component:

```typescript
@Component({
  selector: 'app-onboarding-wizard',
  template: `
    <div class="wizard">
      <app-step-progress />
      <app-current-step />
      <app-wizard-nav />
    </div>
  `,
  providers: [WizardStateService],  // ← fresh instance for each wizard
})
export class OnboardingWizardComponent {
  // Don't need to inject — its children will
}
```

All child components (`StepProgressComponent`, `CurrentStepComponent`, `WizardNavComponent`) inject `WizardStateService` and share the same instance. **A different wizard mounted elsewhere gets its own instance.** No global singleton; no leak between wizards; the wizard's lifecycle owns the state.

```typescript
@Component({ /* … */ })
export class WizardNavComponent {
  protected readonly state = inject(WizardStateService);
}
```

### When to use subtree-scoped vs root-scoped

- **Root-scoped** (`providedIn: 'root'`): state that's truly app-wide (cart, current user, theme)
- **Subtree-scoped** (`providers: [Service]` on a component): state owned by a feature subtree (wizard, modal, feature page)
- **Lazy-loaded module scoped** (`providedIn: 'someModule'` or providers in `loadChildren`): state shared by a feature, recreated when the feature is re-entered

The subtree-scoped pattern is underused. Many apps reach for root-scoped services for state that's really only relevant to one feature, accumulating global state that leaks across navigation. Subtree-scoping bounds the lifetime cleanly.

---

## Pattern 5 — parent-child `input`/`output` (when it's actually right)

Despite this recipe being about avoiding prop drilling, `input`/`output` is still the right answer for short component trees where the state is genuinely local:

```typescript
// File: card-list.component.ts
@Component({
  selector: 'app-card-list',
  template: `
    <h2>{{ title() }}</h2>
    @for (card of cards(); track card.id) {
      <app-card
        [card]="card"
        (selected)="onCardSelected($event)"
      />
    }
  `,
})
export class CardListComponent {
  readonly title = input.required<string>();
  readonly cards = input.required<Card[]>();
  readonly cardSelected = output<Card>();

  onCardSelected(card: Card) {
    this.cardSelected.emit(card);
  }
}

// File: card.component.ts
@Component({
  selector: 'app-card',
  template: `
    <div class="card" (click)="selected.emit(card())">
      {{ card().title }}
    </div>
  `,
})
export class CardComponent {
  readonly card = input.required<Card>();
  readonly selected = output<Card>();
}
```

**Use input/output when:**

- The relationship is direct parent-child (1 level)
- The component being communicated with is intentionally reusable in different parents (a generic `<app-card>` shouldn't know about the global cart)
- The state is genuinely local to this UI flow (not shared elsewhere)
- The "depth" is small (≤ 2 levels)

The 2-level rule is approximate. The signal is when you find yourself adding the same `@Input` or `@Output` to two or more components purely to "pass it through" — that's prop drilling, lift to a service.

### v22 signal-based `input` / `output` / `model`

The recipe uses the modern signal-based forms throughout. For migration context:

<!-- legacy: decorator-based @Input/@Output — modernized in the upgrade pass -->
```typescript
// Legacy: decorator-based @Input/@Output
@Component({ /* … */ })
export class CardComponent implements OnChanges {
  @Input() card!: Card;
  @Input() selectable = false;
  @Output() selected = new EventEmitter<Card>();

  ngOnChanges(changes: SimpleChanges) {
    if (changes['card']) { /* react to card change */ }
  }
}

// Modern (v17+): signal-based input/output
@Component({ /* … */ })
export class CardComponent {
  readonly card = input.required<Card>();
  readonly selectable = input(false);
  readonly selected = output<Card>();

  constructor() {
    effect(() => {
      const c = this.card();
      // react to card change — runs on every change automatically
    });
  }
}
```

Plus `model()` for two-way binding:

```typescript
// Two-way bindable signal — equivalent of [(value)]
@Component({ /* … */ })
export class CounterComponent {
  readonly value = model(0);

  increment() { this.value.update(v => v + 1); }
}

// Parent uses banana-in-a-box binding
<app-counter [(value)]="myCount" />
```

The signal-based forms eliminate `ngOnChanges`, `EventEmitter`, and `@ContentChild`/`@ViewChild` boilerplate. They also make derived state easy via `computed()` — a derived value automatically updates when the input changes.

---

## The decision tree

When you need state or events shared between components, ask:

```text
                       "What kind of communication?"
                                  │
        ┌─────────────────────────┼──────────────────────────┐
        │                         │                          │
"Parent-child, ≤2 levels,"   "Cross-tree state"      "Cross-tree events"
"truly local to flow"        (multiple components     (fire-and-forget,
                              read AND mutate)         no current state)
        │                         │                          │
        ▼                         ▼                          ▼
    input/output             [further branch]              Subject
    (Pattern 5)                                            (Pattern 2)
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
        "App-wide state"   "Feature/subtree"    "URL-persistent /
        (cart, user,        (wizard, modal,      shareable"
         theme)              feature page)       (filters, search)
              │                   │                    │
              ▼                   ▼                    ▼
        Root-scoped         Subtree-scoped       Router state
        signal service      signal service       + signal bridge
        (Pattern 1)         (Pattern 4)          (Pattern 3)
```

Or as a table:

| Scenario | Pattern |
| --- | --- |
| Form passes data to a child input control | `input()` / `model()` |
| Modal emits "confirm" / "cancel" | `output()` |
| Card list with selectable cards | `input()` / `output()` |
| Cart contents (header badge, drawer, checkout) | Root-scoped signal service |
| Current user identity | Root-scoped signal service |
| Toast notifications fired from anywhere | Subject-based event service |
| Modal open/close events | Subject-based event service (or signal service) |
| Product filters (shareable URL) | Router state + signal bridge |
| Search query (back button should work) | Router state + signal bridge |
| Wizard state (per-instance) | Subtree-scoped signal service |
| Feature dashboard layout state | Subtree-scoped signal service |

---

## When NgRx is the right answer

NgRx (and its lighter cousin Signal Store) solves problems that signals + services don't cover well:

**Use NgRx when:**

- You have **complex entity relationships** that need normalization — products that belong to multiple categories, orders with line items that reference products and customers, etc. Manual cross-service joins get tangled.
- You need **time-travel debugging** — replaying state changes step-by-step. The Redux DevTools workflow.
- You have **command/event sourcing requirements** — every state change is an audit event; the state is replayable from events.
- The team **already knows Redux** — there's existing investment, ecosystem familiarity, conventions.
- You have **many components mutating the same state from different angles** — the explicit action-reducer pattern keeps mutations auditable.

**NgRx is overkill when:**

- Single component (or a small number) owns the state — local signals are fine
- State is simple (lists, counters, flags) — services + signals are simpler
- The team is small and doesn't have Redux background — the learning curve outweighs benefits
- You're prototyping or building an MVP — defer the complexity until the problem demands it
- You'd be using NgRx for HTTP data caching — the [request-deduplication](../http/request-deduplication.md) pattern handles that simpler

**The middle ground**: NgRx Signal Store is significantly lighter than the full Redux pattern. It's a structured way to organize signal-based services with conventions for entity collections, computed selectors, and async effects. For mid-sized apps that need *some* discipline but not full Redux, Signal Store fills the gap.

**A reality check**: in our experience, **most Angular apps don't need NgRx**. The teams that reach for it on day one often spend more time on action-reducer boilerplate than the time signals + disciplined services would have cost. Reach for NgRx when you've hit a problem that signals can't solve cleanly — not as default architecture.

---

## Trade-offs and common pitfalls

**Use these patterns when:**

- The state truly needs to be shared (you've verified prop drilling is the alternative)
- The pattern matches the lifetime of the state (root for global, subtree for feature-scoped, etc.)
- The encapsulation discipline (private mutable signal, public readonly) is maintained

**Be cautious about:**

- Reaching for services for state that's actually local to one component — local `signal()` inside the component is simpler
- Making everything `providedIn: 'root'` — subtree-scoping is often the right answer for feature state
- Combining multiple patterns redundantly (URL state + service state + NgRx for the same data) — pick one source of truth per piece of state

### Common pitfalls

- **Forgetting `asReadonly()`** — exposing the mutable signal lets any consumer call `.set()`/`.update()` directly, bypassing the service's business rules. The `private writable / public readonly` pattern is the encapsulation contract.
- **Circular service dependencies** — `ServiceA` injects `ServiceB`, which injects `ServiceA`. Detect at startup, but only if it's at the constructor level. With `inject()` and lazy lookups (the [DI lazy injection](../../dependency-injection/dependency-injection.md#lazy-injection--injector-as-an-escape-hatch) pattern), accidental cycles can slip past.
- **Using `Subject` for state.** Subjects don't replay; a late subscriber doesn't know the current value. For state, use signals or `BehaviorSubject`.
- **Using `signal` for events.** Signals always have a current value; firing the "same" event twice in a row doesn't trigger consumers (signals dedupe equal values by default). For events with no current-value semantics, use `Subject`.
- **`providedIn: 'root'` for state that's actually feature-scoped** — the state leaks across feature navigation. Use a `providers: []` on a feature component to scope it.
- **Reading mutable service state in `computed()` and forgetting that mutations from inside an `effect()` can cause loops.** If effect A reads X and writes Y, and effect B reads Y and writes X, you have a loop. Use `untracked()` to read without subscribing, or restructure to a one-way data flow.
- **Storing the same data in multiple services without designating one as the source of truth.** When User and Cart both know the user's email, updates can diverge. Pick one owner; the other derives or reads.
- **Bridging RxJS → signals with `toSignal()` but forgetting the `initialValue` option.** Without it, the signal type includes `undefined`; reads need null-checks. Provide `initialValue` whenever you have a sensible default.
- **Storing UI state (modal open, drawer open, hover state) in a global service** — that's almost always feature-local. Local component signal is simpler.
- **Inline `EventEmitter` in legacy code mixed with new `output()` in adjacent components.** Pick one form per codebase; consistency matters more than which one you pick.
- **Two-way binding `model()` with no validation** — the parent can set arbitrary values. If the child has invariants (e.g., counter must be ≥ 0), enforce them in the child's update methods rather than trusting the binding.

---

## See also

- [Component interactions](../../components/component-interactions.md) — the concept article with input/output API details
- [Signals](../../reactivity/signals.md) — `signal`, `computed`, `effect`, `model`
- [Dependency Injection](../../dependency-injection/dependency-injection.md) — `inject()`, `providedIn`, subtree providers
- [Routing](../../routing/routing.md) — `ActivatedRoute`, `queryParamMap`, programmatic navigation
- [NgRx](../../state-management/ngrx.md) — when and how to use the full store pattern
- [Request Deduplication](../http/request-deduplication.md) — HTTP-layer caching that often substitutes for "state management" in simple data apps
- [Optimistic Updates](../forms-and-search/optimistic-updates.md) — using signals for fast UI updates across components

## References

- [`input` / `output` API (angular.dev)](https://angular.dev/api/core/input)
- [`model` API (angular.dev)](https://angular.dev/api/core/model)
- [`signal` and `computed` (angular.dev)](https://angular.dev/api/core/signal)
- [Hierarchical injectors guide (angular.dev)](https://angular.dev/guide/di/hierarchical-dependency-injection)
- [NgRx Signal Store (ngrx.io)](https://ngrx.io/guide/signals) — the lighter alternative to full Redux NgRx

## Demo source

Synthesized from common Angular architecture patterns rather than a single demo file. The five-pattern taxonomy reflects what most apps converge on once they grow beyond a handful of components. The decision tree is the recipe's lasting contribution — most teams reach for one or two patterns by reflex and apply them everywhere; the tree makes the right choice mechanical instead of intuitive. All code is original.
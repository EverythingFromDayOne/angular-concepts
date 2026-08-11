---
recipe_id: "testing-signal-components"
title: "Testing Signal-Based Components: Patterns for the v22 Era"
file: "recipes/testing/testing-signal-components.md"
primary_concept: "testing/component-testing"
related_concepts: ["reactivity/signals", "components/components", "dependency-injection/dependency-injection"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Testing Signal-Based Components: Patterns for the v22 Era

> **What you'll build:** working tests for signal-based v22 components
> — reading signals from tests, updating them and asserting the DOM
> follows, testing computed derivations without re-implementing the
> logic, testing effects (which don't run without help), testing
> `input()` and `output()` signal-based component I/O, mocking
> signal-based services cleanly, and the fakeAsync-vs-whenStable
> decision that trips up teams migrating from Zone.js-era tests. Plus
> the specific TestBed patterns that stopped working when signals
> arrived and the ones that replaced them.
>
> **Concepts you'll touch:** Testing / Component Testing, [Signals](../../concepts/reactivity/signals.md), Components, [Dependency Injection](../../concepts/dependency-injection/dependency-injection.md)
>
> **Time:** ~30 minutes to read; ~1 day to modernize a real test
> suite from Zone-era patterns to signal-native ones.

---

## The scenario

You've been building v22 components using the patterns from earlier recipes — signals for state, `computed()` for derived values, `input()` and `output()` for component I/O, `inject()` for services. Everything works in the browser.

You go to write the test:

```typescript
it('shows the current count', () => {
  const fixture = TestBed.createComponent(CounterComponent);
  fixture.detectChanges();

  expect(fixture.nativeElement.textContent).toContain('0');

  fixture.componentInstance.count = 5;         // ❌ can't assign to signal
  fixture.detectChanges();

  expect(fixture.nativeElement.textContent).toContain('5');
});
```

Compilation error: `Cannot assign to 'count' because it is a read-only property.` (Signals are read via `.set()` / `.update()`, not assignment.)

You fix that. Next test:

```typescript
it('runs the effect', () => {
  const fixture = TestBed.createComponent(EffectDemo);
  fixture.componentInstance.name.set('Alice');
  // Expect the effect to have logged something...
  expect(logSpy).toHaveBeenCalledWith('Hello, Alice');   // ❌ FAIL — effect didn't run
});
```

The effect isn't running. Or it is, but not on the timeline you expect.

You write a third test with `input()`:

```typescript
it('reflects the input value', () => {
  const fixture = TestBed.createComponent(GreetingComponent);
  fixture.componentInstance.name = 'Bob';       // ❌ can't set input signal directly
  fixture.detectChanges();
});
```

Compilation error again.

Signal-based Angular changed how components are tested. Old patterns (assign to property, call `detectChanges`, assert DOM) don't map cleanly. The new patterns are just as clean, but they're different. This recipe walks through them.

---

## Setting up TestBed for a signal-based component

For a standalone component (the v22 default), the setup is minimal:

```typescript
// File: counter.component.spec.ts
import { TestBed } from '@angular/core/testing';
import { CounterComponent } from './counter.component';

describe('CounterComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CounterComponent],        // ← standalone imports go here
      providers: [
        // Test doubles for services the component uses
        // { provide: SomeService, useValue: mockService },
      ],
    });
  });

  it('creates', () => {
    const fixture = TestBed.createComponent(CounterComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });
});
```

**Three things worth absorbing:**

- **Standalone components go in `imports`, not `declarations`.** The old `declarations` array is for NgModule-based components; standalone components are self-contained and import via `imports`.
- **`beforeEach` sets up TestBed once per test.** Each test gets a fresh instance; no state leaks between tests.
- **`fixture.componentInstance`** is the component instance; `fixture.nativeElement` is the DOM root; `fixture.debugElement` is Angular's debug wrapper (used for `query` and `queryAll` with `By.css` / `By.directive`).

---

## Pattern 1 — reading and setting signals from tests

Signals are read by calling them as functions (`signal()`). Set via `.set()` or `.update()`. In tests, both work the same as in production code:

```typescript
@Component({
  selector: 'app-counter',
  template: `
    <span data-testid="count">{{ count() }}</span>
    <button (click)="increment()">+</button>
  `,
})
export class CounterComponent {
  readonly count = signal(0);

  increment() {
    this.count.update(c => c + 1);
  }
}
```

Test:

```typescript
it('increments the counter on button click', () => {
  const fixture = TestBed.createComponent(CounterComponent);
  fixture.detectChanges();

  const countElement = fixture.debugElement.query(By.css('[data-testid="count"]')).nativeElement;
  const button = fixture.debugElement.query(By.css('button')).nativeElement;

  expect(countElement.textContent).toBe('0');

  button.click();
  fixture.detectChanges();

  expect(countElement.textContent).toBe('1');

  // Direct signal manipulation for setup:
  fixture.componentInstance.count.set(100);
  fixture.detectChanges();
  expect(countElement.textContent).toBe('100');
});
```

**Four things worth absorbing:**

- **`fixture.componentInstance.count()`** — reading the signal in a test is the same as reading it anywhere else. Call it as a function.
- **`fixture.componentInstance.count.set(100)`** — setting from outside works if the signal isn't `.asReadonly()`. For encapsulated state (private writable, public readonly), you can't set from outside — you drive changes through the component's API (methods, events).
- **`fixture.detectChanges()` after signal mutations** — signals mark subscribers dirty, but the DOM only updates on change detection. In production, Zone.js or the microtask queue triggers CD automatically; in tests, you call it explicitly. Same rule as pre-signal Angular.
- **`data-testid`** attributes over CSS classes — decouples tests from styling. Changing a class name doesn't break tests; changing a data-testid does, which is what you want.

### `whenStable()` for async settling

For components that trigger async work (HTTP, signals updated in effects, promises), `whenStable()` waits for pending microtasks and macrotasks:

```typescript
it('loads data on init', async () => {
  const fixture = TestBed.createComponent(UserListComponent);
  fixture.detectChanges();  // triggers init

  await fixture.whenStable();  // waits for the HTTP mock to resolve

  const users = fixture.debugElement.queryAll(By.css('[data-testid="user-row"]'));
  expect(users.length).toBe(3);
});
```

`whenStable()` is preferred over `tick()` for HTTP tests — you don't need to know exactly how many microtasks the operation takes. It waits for the app to settle, then continues.

---

## Pattern 2 — testing computed derivations

`computed()` signals derive from other signals. Test them by driving the source signals and asserting the derived value:

```typescript
@Component({
  selector: 'app-cart',
  template: `
    <div data-testid="count">{{ itemCount() }}</div>
    <div data-testid="total">{{ subtotal() | currency }}</div>
  `,
})
export class CartComponent {
  readonly items = signal<CartItem[]>([]);

  readonly itemCount = computed(() =>
    this.items().reduce((sum, i) => sum + i.quantity, 0),
  );

  readonly subtotal = computed(() =>
    this.items().reduce((sum, i) => sum + i.price * i.quantity, 0),
  );
}
```

Test:

```typescript
it('computes item count and subtotal from items', () => {
  const fixture = TestBed.createComponent(CartComponent);
  fixture.detectChanges();

  expect(fixture.componentInstance.itemCount()).toBe(0);
  expect(fixture.componentInstance.subtotal()).toBe(0);

  fixture.componentInstance.items.set([
    { productId: 'p1', name: 'Widget', price: 10, quantity: 2 },
    { productId: 'p2', name: 'Gadget', price: 15, quantity: 1 },
  ]);

  // No detectChanges needed for reading signals — they update synchronously.
  // detectChanges is only needed if you're asserting DOM.
  expect(fixture.componentInstance.itemCount()).toBe(3);
  expect(fixture.componentInstance.subtotal()).toBe(35);

  fixture.detectChanges();  // now assert the DOM

  const countEl = fixture.debugElement.query(By.css('[data-testid="count"]')).nativeElement;
  expect(countEl.textContent).toContain('3');
});
```

**Three things worth absorbing:**

- **Signal reads are synchronous** — no need for `detectChanges` between setting a source and reading a computed. The computed re-runs lazily on read.
- **`detectChanges` is only for DOM assertions.** If you're asserting on a signal value (`itemCount()` returns 3), no detectChanges needed. If you're asserting on the rendered text, you need it.
- **Test the computed's inputs and outputs, not its internals.** The test above doesn't verify HOW `computed` implements the sum — it verifies that given items, the count is right. If you later change the implementation (e.g., cache reduce), the test still passes.

---

## Pattern 3 — testing effects (the "why doesn't this run" trap)

`effect()` blocks run reactively when the signals they depend on change. But **in tests**, effects don't run until:

1. Something triggers change detection (`detectChanges`), OR
2. The effect's scheduler is explicitly flushed

This is the source of many "the effect works in the browser but not in tests" bugs.

```typescript
@Component({
  selector: 'app-tracker',
  template: `<div>{{ value() }}</div>`,
})
export class TrackerComponent {
  readonly value = signal(0);
  private readonly logger = inject(LoggerService);

  constructor() {
    effect(() => {
      this.logger.log(`Value changed to ${this.value()}`);
    });
  }
}
```

Test:

```typescript
it('logs when value changes', () => {
  const loggerSpy = jasmine.createSpyObj('LoggerService', ['log']);

  TestBed.configureTestingModule({
    imports: [TrackerComponent],
    providers: [
      { provide: LoggerService, useValue: loggerSpy },
    ],
  });

  const fixture = TestBed.createComponent(TrackerComponent);
  fixture.detectChanges();  // ← triggers initial effect run

  expect(loggerSpy.log).toHaveBeenCalledWith('Value changed to 0');

  fixture.componentInstance.value.set(5);
  fixture.detectChanges();  // ← triggers effect on the change

  expect(loggerSpy.log).toHaveBeenCalledWith('Value changed to 5');
});
```

**Three things worth absorbing:**

- **`detectChanges()` triggers effect runs**, both the initial one and subsequent ones. Without it, the effect stays dirty; the test sees no side effects.
- **The initial effect runs on the first `detectChanges`**, not on component instantiation. You need `fixture.detectChanges()` after `createComponent` for the effect to fire the first time.
- **Effects run outside the Angular zone by default** if the test uses zoneless testing. For zoneful tests (the current default), effects run as part of change detection.

### The `flushEffects` alternative (v18+)

For more explicit control, `TestBed.tick()` or `TestBed.flushEffects()` (v18+ APIs) flush pending effects without triggering full change detection:

```typescript
it('effect runs on signal update', () => {
  const fixture = TestBed.createComponent(TrackerComponent);
  fixture.detectChanges();  // initial

  fixture.componentInstance.value.set(10);
  TestBed.tick();  // flush effects without full detectChanges

  expect(loggerSpy.log).toHaveBeenCalledWith('Value changed to 10');
});
```

For most tests, `fixture.detectChanges()` is fine and matches production behavior more closely. Use the explicit flush when you specifically want to test effect scheduling.

---

## Pattern 4 — testing input signals

`input()` and `input.required()` create signal-based component inputs. **You can't assign to them directly** — they're read-only from the outside. Use `componentRef.setInput()`:

```typescript
@Component({
  selector: 'app-greeting',
  template: `<h1>Hello, {{ name() }}!</h1>`,
})
export class GreetingComponent {
  readonly name = input.required<string>();
}
```

Test:

```typescript
it('renders the name input', () => {
  const fixture = TestBed.createComponent(GreetingComponent);

  // Use componentRef.setInput, NOT componentInstance.name = ...
  fixture.componentRef.setInput('name', 'Alice');
  fixture.detectChanges();

  expect(fixture.nativeElement.textContent).toContain('Hello, Alice!');

  fixture.componentRef.setInput('name', 'Bob');
  fixture.detectChanges();

  expect(fixture.nativeElement.textContent).toContain('Hello, Bob!');
});
```

**Four things worth absorbing:**

- **`fixture.componentRef.setInput(name, value)`** is the only correct way to set signal inputs from tests. Direct assignment fails at compile time.
- **The property name is a string** (`'name'`) — TypeScript can't type-check it in current versions. Typos here don't fail at compile time; they fail at runtime.
- **For `input.required()`, `createComponent` succeeds without the input being set**, but `detectChanges` throws if the template reads it. Setting the input before `detectChanges` avoids the error.
- **Default `input(value)` provides a fallback** so tests can skip setting it. Only `input.required<T>()` mandates a set-before-detect.

### Testing optional inputs

```typescript
@Component({ /* … */ })
export class WidgetComponent {
  readonly size = input<'small' | 'medium' | 'large'>('medium');
  readonly disabled = input(false, { transform: booleanAttribute });
}
```

```typescript
it('uses default values when inputs not provided', () => {
  const fixture = TestBed.createComponent(WidgetComponent);
  fixture.detectChanges();  // no setInput needed

  expect(fixture.componentInstance.size()).toBe('medium');
  expect(fixture.componentInstance.disabled()).toBe(false);
});

it('applies input transforms', () => {
  const fixture = TestBed.createComponent(WidgetComponent);
  fixture.componentRef.setInput('disabled', '');  // empty string → true via booleanAttribute
  fixture.detectChanges();

  expect(fixture.componentInstance.disabled()).toBe(true);
});
```

The `transform` function runs when `setInput` is called; the test verifies transform behavior end-to-end.

---

## Pattern 5 — testing output signals

`output()` creates a subscribable channel. Test by subscribing and asserting emissions:

```typescript
@Component({
  selector: 'app-card',
  template: `<button (click)="onSelect()">Select</button>`,
})
export class CardComponent {
  readonly card = input.required<Card>();
  readonly selected = output<Card>();

  onSelect() {
    this.selected.emit(this.card());
  }
}
```

Test:

```typescript
it('emits selected event when button clicked', () => {
  const testCard: Card = { id: '1', title: 'Test Card' };
  const emittedValues: Card[] = [];

  const fixture = TestBed.createComponent(CardComponent);
  fixture.componentRef.setInput('card', testCard);

  // Subscribe to the output BEFORE triggering
  fixture.componentInstance.selected.subscribe(value => emittedValues.push(value));
  fixture.detectChanges();

  const button = fixture.nativeElement.querySelector('button');
  button.click();
  fixture.detectChanges();

  expect(emittedValues.length).toBe(1);
  expect(emittedValues[0]).toEqual(testCard);
});
```

**Two things worth absorbing:**

- **`output()` is subscribable in tests just like an Observable.** The `.subscribe(callback)` returns a subscription; each emission fires the callback.
- **Subscribe before triggering.** Late subscribers miss emissions (outputs don't replay).

### Spy-based alternative

For terser tests:

```typescript
it('emits on click', () => {
  const emitSpy = jasmine.createSpy('emit');
  const fixture = TestBed.createComponent(CardComponent);
  fixture.componentRef.setInput('card', { id: '1', title: 'X' });
  fixture.componentInstance.selected.subscribe(emitSpy);
  fixture.detectChanges();

  fixture.nativeElement.querySelector('button').click();

  expect(emitSpy).toHaveBeenCalledOnceWith({ id: '1', title: 'X' });
});
```

Same mechanics; the spy just wraps the assertion.

---

## Pattern 6 — testing components with signal-based services

Signal-based services (from the [component-communication recipe](../components/component-communication.md)) need to be mocked in tests. The pattern is: provide a test double whose signals you control.

```typescript
// The service
@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly _items = signal<CartItem[]>([]);
  readonly items = this._items.asReadonly();
  readonly itemCount = computed(() => this._items().length);

  addItem(item: CartItem): void { /* … */ }
}

// The component
@Component({
  selector: 'app-cart-badge',
  template: `<span>{{ cart.itemCount() }}</span>`,
})
export class CartBadgeComponent {
  protected readonly cart = inject(CartService);
}
```

Test:

```typescript
describe('CartBadgeComponent', () => {
  // Fake service where we control the signals
  let fakeItems: WritableSignal<CartItem[]>;
  let fakeCart: { items: Signal<CartItem[]>; itemCount: Signal<number>; addItem: jasmine.Spy };

  beforeEach(() => {
    fakeItems = signal<CartItem[]>([]);
    fakeCart = {
      items: fakeItems.asReadonly(),
      itemCount: computed(() => fakeItems().length),
      addItem: jasmine.createSpy('addItem'),
    };

    TestBed.configureTestingModule({
      imports: [CartBadgeComponent],
      providers: [
        { provide: CartService, useValue: fakeCart },
      ],
    });
  });

  it('shows the current item count', () => {
    const fixture = TestBed.createComponent(CartBadgeComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('0');

    // Drive the fake service's signal — the component reacts
    fakeItems.set([
      { productId: 'p1', name: 'Widget', price: 10, quantity: 1 },
      { productId: 'p2', name: 'Gadget', price: 15, quantity: 1 },
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('2');
  });
});
```

**Four things worth absorbing:**

- **The fake service is a plain object** with signal-shaped fields. TypeScript doesn't require it to be an actual class instance — the DI system just returns what you gave it.
- **The `WritableSignal` inside the test (`fakeItems`) is the control point.** The component sees only the `.asReadonly()` view; the test drives changes via the writable original.
- **`computed()` on the fake works exactly like the real one** — it recomputes when `fakeItems` changes.
- **Method spies (`jasmine.createSpy`) verify calls** — if you test a component that calls `cart.addItem()`, the spy lets you assert the call happened with the right args.

### Type-safe fakes with the `Partial<T>` pattern

For services with many methods, only implement what the test uses:

```typescript
const fakeCart: Partial<CartService> = {
  items: signal([]).asReadonly(),
  itemCount: signal(0),
  addItem: jasmine.createSpy('addItem'),
};

TestBed.configureTestingModule({
  providers: [
    { provide: CartService, useValue: fakeCart },
  ],
});
```

The `Partial<CartService>` gives you type-checking for the fields you implement without requiring the full interface. Missing methods that the component tries to call will fail at runtime — which is fine, because that's a test bug (missing implementation for what the code needs).

---

## Pattern 7 — `TestBed.runInInjectionContext` for injectable setup

Some test setup needs an injection context — creating a validator, testing an interceptor, running code that uses `inject()`. `TestBed.runInInjectionContext` provides one:

```typescript
it('username availability validator returns null for empty input', async () => {
  TestBed.configureTestingModule({
    providers: [
      { provide: HttpClient, useValue: httpMock },
    ],
  });

  const validator = TestBed.runInInjectionContext(() => usernameAvailable());
  // Now `validator` is a function that would have failed to inject HttpClient
  // if we'd called it outside the injection context.

  const control = new FormControl('');
  const errors = await firstValueFrom(validator(control) as Observable<ValidationErrors | null>);

  expect(errors).toBeNull();
});
```

Without `runInInjectionContext`, calling `usernameAvailable()` (from the [async-validation recipe](../form-and-search/async-validation.md)) would throw — the factory uses `inject(HttpClient)`, which requires an active injection context.

This is v16+. Use it whenever you're calling a factory function that itself uses `inject()`.

---

## fakeAsync vs whenStable — the decision

Two ways to handle async in tests. Both work; they have different trade-offs.

### `fakeAsync` + `tick()`

Wraps the test in a fake time zone. Async operations don't actually wait; you control time with `tick(ms)`. Fast and deterministic:

```typescript
it('debounces the search', fakeAsync(() => {
  const fixture = TestBed.createComponent(SearchComponent);
  fixture.detectChanges();

  fixture.componentInstance.searchTerm.set('a');
  fixture.componentInstance.searchTerm.set('ab');
  fixture.componentInstance.searchTerm.set('abc');

  tick(200);  // fast-forward 200ms — debounce hasn't fired yet (300ms threshold)
  expect(httpMock.get).not.toHaveBeenCalled();

  tick(100);  // now 300ms elapsed — debounce fires
  expect(httpMock.get).toHaveBeenCalledOnceWith('/api/search?q=abc');
}));
```

**Advantages**: fast, deterministic, precise control of time. **Limitations**: some APIs (real HTTP, WebSockets, service workers) don't work under fakeAsync; you're not testing real timing.

### `whenStable()` + async

Uses real time; waits for microtasks and macrotasks to settle:

```typescript
it('loads data on init', async () => {
  const fixture = TestBed.createComponent(UserListComponent);
  fixture.detectChanges();
  await fixture.whenStable();

  expect(fixture.nativeElement.textContent).toContain('Alice');
});
```

**Advantages**: works with real async APIs; matches production timing. **Limitations**: slower; less deterministic for precise timing (debounce, retry backoff).

**Rule of thumb:**

- **`fakeAsync` for tests that check timing behavior** (debounce, retry delays, animations)
- **`whenStable` for tests that just need to wait for async work** (HTTP calls, promise chains)

### The signal-effect timing subtlety

Effects have their own microtask scheduler. Under `fakeAsync`, calling `tick(0)` flushes microtasks — including pending effect runs:

```typescript
it('effect runs after signal update', fakeAsync(() => {
  const fixture = TestBed.createComponent(TrackerComponent);
  fixture.detectChanges();  // initial effect

  fixture.componentInstance.value.set(10);
  tick();  // flushes the effect's microtask

  expect(loggerSpy.log).toHaveBeenCalledWith('Value changed to 10');
}));
```

Without the `tick()`, the effect's scheduler hasn't fired. Under real async (`whenStable`), `await fixture.whenStable()` handles this.

---

## Testing HTTP with signal-based components

The `HttpTestingController` pattern is unchanged from pre-signal Angular — mock HTTP responses, verify requests. What's new is how the component consumes them (signal-based state instead of Observable subscriptions):

```typescript
@Component({
  template: `
    @if (loading()) { <div>Loading…</div> }
    @if (users(); as list) {
      @for (user of list; track user.id) {
        <div data-testid="user-row">{{ user.name }}</div>
      }
    }
  `,
})
export class UserListComponent {
  private readonly http = inject(HttpClient);
  readonly users = signal<User[] | null>(null);
  readonly loading = signal(false);

  constructor() {
    this.loading.set(true);
    this.http.get<User[]>('/api/users').pipe(
      takeUntilDestroyed(),
    ).subscribe({
      next: users => { this.users.set(users); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
```

Test:

```typescript
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

describe('UserListComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [UserListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();  // ensures no unexpected requests
  });

  it('loads and displays users', async () => {
    const fixture = TestBed.createComponent(UserListComponent);
    fixture.detectChanges();

    // Verify the HTTP call was made
    const req = httpMock.expectOne('/api/users');
    expect(req.request.method).toBe('GET');

    // Respond with mock data
    req.flush([
      { id: '1', name: 'Alice' },
      { id: '2', name: 'Bob' },
    ]);

    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.users()).toEqual([
      { id: '1', name: 'Alice' },
      { id: '2', name: 'Bob' },
    ]);

    const rows = fixture.nativeElement.querySelectorAll('[data-testid="user-row"]');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('Alice');
  });
});
```

**Three things worth absorbing:**

- **`provideHttpClient() + provideHttpClientTesting()`** for standalone tests. `provideHttpClientTesting` provides the mock backend that `HttpTestingController` uses.
- **`httpMock.expectOne(url)` returns a request handle**; `flush(data)` responds with the mock data.
- **`await fixture.whenStable()` after `flush`** — the HTTP mock resolves synchronously in a sense, but the subscribe callback runs in a microtask; wait for it before asserting.

---

## Trade-offs and common pitfalls

**Use these test patterns when:**

- The component uses signals for state (v22 idiom)
- You're writing new tests or migrating from Zone-era tests
- The test needs to verify reactive behavior end-to-end

**Skip / adapt when:**

- The component still uses `BehaviorSubject`/`Observable`-based state → the older `subscribe` patterns still work
- Testing pure business logic that doesn't touch the DOM → skip TestBed entirely; test the function directly

### Common pitfalls

- **`fixture.componentInstance.count = 5`** — signals aren't writable properties. Use `count.set(5)` or `componentRef.setInput('count', 5)` for input signals.
- **Missing `detectChanges` after signal updates.** Signal reads reflect immediately (`count()` returns 5), but the DOM only updates after change detection. `expect(nativeElement.textContent).toBe('5')` fails without `detectChanges`.
- **Missing initial `detectChanges`.** Effects don't run before the first `detectChanges`. Neither does template rendering. Every test needs at least one `detectChanges` after `createComponent`.
- **Assigning to input signals directly.** `fixture.componentInstance.name = 'Alice'` fails at compile time. `componentRef.setInput('name', 'Alice')` is the correct API.
- **Subscribing to outputs after the emission.** `output()` subscriptions are cold — late subscribers miss emissions. Subscribe before triggering.
- **Not calling `httpMock.verify()`.** Without it, un-flushed requests silently pile up; tests pass locally, mysterious hangs in CI.
- **Using `tick()` for HTTP tests.** HTTP mocks resolve via `flush`, not time. Use `await fixture.whenStable()` after `flush`.
- **`inject()` calls in test setup outside injection context.** `TestBed.runInInjectionContext(() => usernameAvailable())` provides the context for factories that use inject internally.
- **Full mocks for services when only signals matter.** `{ items: signal([]).asReadonly(), addItem: jasmine.createSpy('addItem') } as Partial<CartService>` is enough. Full class implementations are usually over-mocking.
- **Sharing signals across tests.** If a fake service holds signals declared at describe-level (not in beforeEach), state leaks between tests. Always instantiate fakes in `beforeEach`.
- **Testing effect implementation, not outcomes.** Testing "the effect calls console.log at 3 different times" ties tests to the implementation. Test the observable outcome — was the message logged with the right value — not the mechanism.
- **`fakeAsync` around code that uses `setTimeout(fn, 0)` with real dependencies.** Real network calls or timers that fakeAsync can't intercept will cause "1 periodic timer(s) still in the queue" errors. Isolate the async surface being tested.
- **Deep-equality checks on signal values.** `expect(component.data()).toEqual(expected)` works, but if the signal holds a large object, matcher output on failure is huge. For big data, assert on specific fields.
- **Testing components that use `provideExperimentalZonelessChangeDetection()` with zoneful test setup.** Provide the zoneless config in tests too, or expected behaviors diverge.

---

## See also

- Testing / Component Testing (concept article) — the broader testing primer this recipe extends
- [Signals](../../concepts/reactivity/signals.md) — the state primitive being tested
- [Component Communication](../components/component-communication.md) — the signal-based service pattern this recipe mocks
- [Async Validation](../form-and-search/async-validation.md) — the async validator pattern tested with `runInInjectionContext`
- [Optimistic Updates](../form-and-search/optimistic-updates.md) — testing UI updates with rollback semantics
- [Search Engine](../form-and-search/search-engine.md) — testing debounce with `fakeAsync + tick`

## References

- [`TestBed` API (angular.dev)](https://angular.dev/api/core/testing/TestBed)
- [`ComponentRef.setInput` (angular.dev)](https://angular.dev/api/core/ComponentRef#setInput) — the signal-input setter
- [`fakeAsync` and `tick` (angular.dev)](https://angular.dev/api/core/testing/fakeAsync)
- [`HttpTestingController` (angular.dev)](https://angular.dev/api/common/http/testing/HttpTestingController)
- [`provideHttpClientTesting` (angular.dev)](https://angular.dev/api/common/http/testing/provideHttpClientTesting)
- [`runInInjectionContext` (angular.dev)](https://angular.dev/api/core/runInInjectionContext)

## Demo source

Synthesized from real-world signal-component testing patterns rather than a single demo file. The `componentRef.setInput` pattern, the `runInInjectionContext` for factories, and the `Partial<T>` mocking approach reflect the conventions v22 codebases converge on. The "why doesn't my effect run" gotcha and the `detectChanges` requirements are the top questions in v22 testing discussions. All code is original.
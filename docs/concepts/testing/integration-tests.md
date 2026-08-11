---
roadmap_node: "integration-tests"
title: "Integration Tests"
file: "testing/integration-tests.md"
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

# Integration Tests

> **Lead with this:** Integration tests verify that multiple pieces work
> together — a parent component with its real children, a routed component with
> the real router, or a form with real validation. The test boundary is wider
> than a unit test, and fewer things are mocked.

## What it is

The line between unit and integration tests is a boundary decision: how much
of the real system do you let run?

| Test type | What runs | What's faked |
| --- | --- | --- |
| **Unit test** | One component/service | All dependencies mocked |
| **Integration test** | Component tree or route | Only external services mocked |
| **E2E test** | Full browser + real backend | Nothing (or a test backend) |

In practice, Angular integration tests still use `TestBed` — the setup looks
similar to a unit test, but you import the real component tree (children
included) rather than replacing children with stubs, and you let the real
Angular Router run rather than mocking `ActivatedRoute`.

The payoff: integration tests catch bugs at the seams — input/output
mismatches between parent and child, route guards that silently redirect, forms
whose validation doesn't wire up correctly. These are the bugs unit tests miss.

## How it works under the hood

### Old approach — stub everything, mock the router

The traditional integration test strategy was: stub every child component,
mock `ActivatedRoute` by hand, use `RouterTestingModule`. This led to a
"mocking tax" — test code that was longer than the feature code, and tests that
passed even when the real integration was broken.

```typescript
// Old approach — heavy mocking of things Angular should own
@Component({ selector: 'app-header', template: '' })
class StubHeaderComponent {}                         // stub child

@Component({ selector: 'app-sidebar', template: '' })
class StubSidebarComponent {}                        // stub child

TestBed.configureTestingModule({
  declarations: [ShellComponent, StubHeaderComponent, StubSidebarComponent],
  imports: [RouterTestingModule.withRoutes([])],     // deprecated
  providers: [
    {
      provide: ActivatedRoute,                       // mocking Angular internals
      useValue: { paramMap: of(new Map([['id', '5']])) }
    }
  ],
});
```

Problems with this:
- Your mock of `ActivatedRoute` may not behave like the real one (async
  sequencing, change detection coupling, etc.)
- Child stub components don't test that inputs/outputs are correctly wired
- `RouterTestingModule` is deprecated

### New approach — real standalone tree + RouterTestingHarness

Standalone components changed the economics of integration testing. When you
import a standalone component in `TestBed.configureTestingModule({ imports: [ShellComponent] })`,
Angular automatically brings in all of `ShellComponent`'s declared imports —
its real child components, real directives, real pipes — for free. You get
the real component tree without manually listing every piece.

For the router, `provideRouter()` + `provideLocationMocks()` +
`RouterTestingHarness` replace `RouterTestingModule` with a real routing
context. You navigate to a URL and the harness renders whatever component the
route matches — no `ActivatedRoute` mocking needed.

```
Old: Stub children + mock ActivatedRoute + RouterTestingModule
  → Tests pass but real integration may be broken

New: Real children via standalone imports + provideRouter() + RouterTestingHarness
  → Tests fail when real integration is broken — that's the point
```

The tradeoff: real trees require real (or stubbed) services for every dependency
in the tree. You mock services, not components.

## Basic usage

### Testing a component tree together

Import the real parent — all its children come along automatically:

```typescript
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ProductCardComponent } from './product-card.component';

// ProductCardComponent imports: PricePipe, StockBadgeComponent, FavoriteButtonComponent
// All are standalone — they come in automatically when we import ProductCardComponent

describe('ProductCardComponent (integration)', () => {
  let fixture: ComponentFixture<ProductCardComponent>;

  const mockProduct: Product = {
    id: '1',
    name: 'Wireless Headphones',
    price: 89.99,
    stock: 12,
    isFeatured: true,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductCardComponent],  // real tree — children auto-included
    }).compileComponents();

    fixture = TestBed.createComponent(ProductCardComponent);
    fixture.componentRef.setInput('product', mockProduct);
    await fixture.whenStable();
  });

  it('renders the product name', () => {
    expect(fixture.nativeElement.textContent).toContain('Wireless Headphones');
  });

  it('formats price via the real PricePipe', () => {
    // PricePipe runs for real — tests the integration, not a stub
    expect(fixture.nativeElement.textContent).toContain('$89.99');
  });

  it('shows in-stock badge when stock > 0', () => {
    const badge = fixture.debugElement.query(By.css('[data-testid="stock-badge"]'));
    expect(badge.nativeElement.textContent).toContain('In Stock');
  });

  it('shows out-of-stock badge when stock is 0', async () => {
    fixture.componentRef.setInput('product', { ...mockProduct, stock: 0 });
    await fixture.whenStable();

    const badge = fixture.debugElement.query(By.css('[data-testid="stock-badge"]'));
    expect(badge.nativeElement.textContent).toContain('Out of Stock');
  });
});
```

### Testing parent → child interaction

Verify inputs are correctly wired from parent to child:

```typescript
describe('ProductListComponent + ProductCardComponent', () => {
  let fixture: ComponentFixture<ProductListComponent>;

  const mockProductService = {
    getAll: signal<Product[]>([
      { id: '1', name: 'Widget A', price: 10, stock: 5 },
      { id: '2', name: 'Widget B', price: 20, stock: 0 },
    ]),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductListComponent],      // brings ProductCardComponent along
      providers: [
        { provide: ProductService, useValue: mockProductService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ProductListComponent);
    await fixture.whenStable();
  });

  it('renders one card per product', () => {
    const cards = fixture.debugElement.queryAll(By.css('app-product-card'));
    expect(cards.length).toBe(2);
  });

  it('passes product name to each card', () => {
    const cards = fixture.debugElement.queryAll(By.css('app-product-card'));
    expect(cards[0].nativeElement.textContent).toContain('Widget A');
    expect(cards[1].nativeElement.textContent).toContain('Widget B');
  });
});
```

### Testing child → parent output

Verify events bubble correctly from child to parent handler:

```typescript
describe('CartComponent + RemoveButton interaction', () => {
  let fixture: ComponentFixture<CartComponent>;
  let cartService: CartService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CartComponent],
      providers: [CartService],
    }).compileComponents();

    fixture = TestBed.createComponent(CartComponent);
    cartService = TestBed.inject(CartService);
    cartService.add({ id: '1', name: 'Widget', price: 9.99 });
    await fixture.whenStable();
  });

  it('removes item when remove button is clicked', async () => {
    const removeBtn = fixture.nativeElement
      .querySelector('[data-testid="remove-1"]');
    removeBtn.click();
    await fixture.whenStable();

    expect(cartService.items().length).toBe(0);
    expect(fixture.nativeElement.textContent).toContain('Your cart is empty');
  });
});
```

### Testing routed components with RouterTestingHarness

`RouterTestingHarness` creates a real routing context — no mocking of
`ActivatedRoute`, no fragile param setup. Navigate to a URL and let the
router resolve it:

```typescript
import { RouterTestingHarness } from '@angular/router/testing';
import { provideRouter } from '@angular/router';
import { provideLocationMocks } from '@angular/common/testing';
import { UserProfileComponent } from './user-profile.component';

describe('UserProfileComponent routing integration', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'users/:id', component: UserProfileComponent },
        ]),
        provideLocationMocks(),   // replaces RouterTestingModule
        { provide: UserService, useValue: mockUserService },
      ],
    });
  });

  it('loads the user for the given route param', async () => {
    mockUserService.getUser.and.returnValue(
      of({ id: '42', name: 'Alice' })
    );

    const harness = await RouterTestingHarness.create();
    // Navigate to the route — harness resolves the component
    const component = await harness.navigateByUrl('/users/42', UserProfileComponent);

    expect(component.userId()).toBe('42');
    expect(harness.routeNativeElement?.textContent).toContain('Alice');
  });

  it('redirects unauthenticated users to login', async () => {
    mockAuthService.isAuthenticated.and.returnValue(false);

    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/users/42');

    expect(TestBed.inject(Router).url).toBe('/login');
  });
});
```

`provideLocationMocks()` is the standalone replacement for
`RouterTestingModule`. Always pair it with `provideRouter()` in routing
integration tests.

### Testing route guards in isolation

Guards are functions — test them directly using `RouterTestingHarness`:

```typescript
import { vi } from 'vitest';       // Vitest — use jasmine.createSpy for Karma

describe('authGuard', () => {
  @Component({ standalone: true, template: '<h1>Protected</h1>' })
  class ProtectedPage {}

  @Component({ standalone: true, template: '<h1>Login</h1>' })
  class LoginPage {}

  async function setup(isAuthenticated: boolean) {
    const authStore = { isAuthenticated: () => isAuthenticated };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthStore, useValue: authStore },
        provideRouter([
          { path: 'protected', component: ProtectedPage, canActivate: [authGuard] },
          { path: 'login', component: LoginPage },
        ]),
        provideLocationMocks(),
      ],
    });
    return await RouterTestingHarness.create();
  }

  it('allows authenticated users', async () => {
    const harness = await setup(true);
    await harness.navigateByUrl('/protected');
    expect(harness.routeNativeElement?.textContent).toContain('Protected');
  });

  it('redirects unauthenticated users to /login', async () => {
    const harness = await setup(false);
    await harness.navigateByUrl('/protected');
    expect(TestBed.inject(Router).url).toBe('/login');
  });
});
```

## Real-world patterns

### Pattern 1 — Selective child replacement

Import the real parent (and most children) but swap one specific child
that has heavy dependencies:

```typescript
// Real tree — but replace the map component that needs a browser API
@Component({
  selector: 'app-location-map',
  standalone: true,
  template: '<p data-testid="map-stub">Map placeholder</p>',
})
class MockLocationMap {
  @Input() coordinates!: Coordinates;
}

TestBed.configureTestingModule({
  imports: [OrderDetailComponent],     // real tree
}).overrideComponent(OrderDetailComponent, {
  set: {
    // Swap just the map — everything else is real
    imports: [
      ...OrderDetailComponent.imports.filter(i => i !== LocationMapComponent),
      MockLocationMap,
    ],
  },
});
```

### Pattern 2 — Testing form submission end-to-end

A form integration test verifies: validation rules fire, submit is disabled
while invalid, and the service is called with the right data on success:

```typescript
describe('LoginForm integration', () => {
  let fixture: ComponentFixture<LoginFormComponent>;
  let authService: jasmine.SpyObj<AuthService>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj('AuthService', ['login']);
    authService.login.and.returnValue(Promise.resolve({ token: 'abc' }));

    await TestBed.configureTestingModule({
      imports: [LoginFormComponent],
      providers: [{ provide: AuthService, useValue: authService }],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginFormComponent);
    await fixture.whenStable();
  });

  it('disables submit while form is invalid', () => {
    const submit = fixture.nativeElement.querySelector('[data-testid="submit"]');
    expect(submit.disabled).toBeTrue();
  });

  it('enables submit when form is valid', async () => {
    typeInto('[data-testid="email"]', 'alice@example.com');
    typeInto('[data-testid="password"]', 'secret123');
    await fixture.whenStable();

    const submit = fixture.nativeElement.querySelector('[data-testid="submit"]');
    expect(submit.disabled).toBeFalse();
  });

  it('calls AuthService.login with form values on submit', async () => {
    typeInto('[data-testid="email"]', 'alice@example.com');
    typeInto('[data-testid="password"]', 'secret123');
    fixture.nativeElement.querySelector('[data-testid="submit"]').click();
    await fixture.whenStable();

    expect(authService.login).toHaveBeenCalledWith('alice@example.com', 'secret123');
  });

  function typeInto(selector: string, value: string): void {
    const el = fixture.nativeElement.querySelector(selector);
    el.value = value;
    el.dispatchEvent(new Event('input'));
    el.dispatchEvent(new Event('blur'));
  }
});
```

## Common mistakes

### Mistake 1 — Mocking ActivatedRoute manually

Manual `ActivatedRoute` mocks are fragile — they don't replicate the real
router's async sequencing or CD coupling:

```typescript
// ❌ Fragile mock — doesn't behave like the real router
providers: [
  {
    provide: ActivatedRoute,
    useValue: { paramMap: of(convertToParamMap({ id: '5' })) }
  }
]

// ✅ Real router via RouterTestingHarness — no mock needed
providers: [
  provideRouter([{ path: 'detail/:id', component: DetailComponent }]),
  provideLocationMocks(),
]
// Then: await harness.navigateByUrl('/detail/5', DetailComponent)
```

### Mistake 2 — Using deprecated RouterTestingModule

```typescript
// ❌ Deprecated — RouterTestingModule was removed in favor of standalone APIs
imports: [RouterTestingModule.withRoutes(routes)]

// ✅ Modern replacement
providers: [provideRouter(routes), provideLocationMocks()]
```

### Mistake 3 — Asserting on child component internals

Integration tests should assert on observable behavior, not internal state
of child components:

```typescript
// ❌ Reaches into the child component's internals — brittle
const childDebug = fixture.debugElement.query(By.directive(StockBadgeComponent));
const childInstance = childDebug.componentInstance;
expect(childInstance.badgeClass).toBe('in-stock');

// ✅ Assert on what the user sees — resilient to child refactoring
const badge = fixture.nativeElement.querySelector('[data-testid="stock-badge"]');
expect(badge.textContent).toContain('In Stock');
expect(badge.classList).toContain('badge--success');
```

### Mistake 4 — Forgetting provideLocationMocks() with provideRouter()

`provideRouter()` alone doesn't mock the browser's `Location` API. Without
`provideLocationMocks()`, real navigation APIs may fire in tests and interfere:

```typescript
// ❌ Missing provideLocationMocks — navigation may behave unexpectedly
providers: [provideRouter(routes)]

// ✅ Always pair them for test isolation
providers: [provideRouter(routes), provideLocationMocks()]
```

## How this evolved

> - **Angular 2–13 (2016–2021):** Integration tests relied on `RouterTestingModule`
>   and manual `ActivatedRoute` mocks. NgModule-based components required
>   listing every child in `declarations[]` — easy to miss dependencies and
>   get false positives. Stub-heavy test setup was the norm.
>
> - **Angular 14 (2022):** Standalone components arrived. Importing a standalone
>   component in `imports[]` automatically brought its entire dependency tree.
>   The mocking tax dropped significantly. `provideRouter()` introduced as the
>   standalone replacement for `RouterModule.forRoot()`.
>
> - **Angular 15 (2022):** `provideLocationMocks()` introduced — standalone
>   replacement for `RouterTestingModule`. `RouterTestingHarness` introduced
>   in Angular 15.2 — the first official tool for testing routed components
>   without mocking `ActivatedRoute`.
>
> - **Angular 20 (2025):** `RouterTestingModule` deprecated. All routing tests
>   should use `provideRouter()` + `provideLocationMocks()` +
>   `RouterTestingHarness`.
>
> - **Angular 22 (now):** The standard integration testing pattern is: import
>   the standalone component (real tree), provide real services where practical,
>   mock only external boundaries (HTTP, analytics, auth), use
>   `RouterTestingHarness` for any route-aware tests, and assert on DOM
>   output rather than component internals.

## See also

- [Unit Tests](./unit-tests.md) — `TestBed`, `fixture.whenStable()`, and the
  Karma → Vitest runner evolution
- [Component Harnesses](./component-harnesses.md) — the CDK's stable API for
  interacting with Angular Material components in integration tests
- [E2E Testing](./e2e-testing.md) — when integration tests aren't enough and
  a real browser is needed
- [Routing](../routing/routing.md) — understanding the router internals that
  `RouterTestingHarness` exercises
- [Official docs — Testing routing and navigation](https://angular.dev/guide/routing/testing)
- [Official docs — Component test scenarios](https://angular.dev/guide/testing/components-scenarios)
- [Official docs — RouterTestingHarness](https://angular.dev/api/router/testing/RouterTestingHarness)

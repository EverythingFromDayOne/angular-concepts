---
roadmap_node: "unit-tests"
title: "Unit Tests"
file: "testing/unit-tests.md"
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

# Unit Tests

> **Lead with this:** Angular unit tests use `TestBed` to create a minimal
> Angular environment for each spec — no browser, no server — so you can
> test one component or service in isolation, with real DI and real templates,
> but with fake dependencies you control.

## What it is

A **unit test** verifies one piece of code in isolation. In Angular that
usually means one component, one service, one pipe, or one directive.
Dependencies are replaced with fakes so a failure in a dependency doesn't
cause a false failure in the unit under test.

Angular's testing toolkit ships in `@angular/core/testing`:

| Tool | What it does |
| --- | --- |
| `TestBed` | Configures a minimal Angular environment for the test |
| `ComponentFixture<T>` | Wrapper around a component instance + its DOM |
| `TestBed.inject()` | Retrieves a service from the test injector |
| `TestBed.tick()` | Runs all pending effects and CD (v20+, replaces `flushEffects`) |

In v22, the default test runner for new projects is **Vitest** (via
`@angular/build:unit-test`). Existing projects that haven't migrated still
use Jasmine + Karma. Both work with the same `TestBed` API — the runner is
a separate concern from the Angular testing utilities.

## How it works under the hood

### Old testing model — Zone.js + manual change detection

Before Angular 21, tests ran inside Zone.js by default. The test environment
patched async APIs, and every component test followed this pattern:

```typescript
// Old zone-based pattern — Angular 2–20
beforeEach(async () => {
  await TestBed.configureTestingModule({
    declarations: [MyComponent],   // NgModule-style declarations
    imports: [CommonModule],
  }).compileComponents();          // async compilation required
});

it('shows the title', () => {
  const fixture = TestBed.createComponent(MyComponent);
  fixture.detectChanges();         // manually trigger first CD
  expect(fixture.nativeElement.querySelector('h1').textContent).toBe('Hello');
});
```

`fixture.detectChanges()` was required because `TestBed.createComponent()`
does not run change detection automatically — you had to explicitly trigger
it after setting up state and after every mutation.

### New testing model — zoneless + await fixture.whenStable()

Angular 21 made applications **zoneless by default**. The CLI now generates
tests that match this reality:

```typescript
// Modern zoneless pattern — Angular 21+ (v22 default)
beforeEach(async () => {
  await TestBed.configureTestingModule({
    imports: [MyComponent],        // standalone — import directly
  }).compileComponents();
});

it('shows the title', async () => {
  const fixture = TestBed.createComponent(MyComponent);
  await fixture.whenStable();      // wait for Angular to settle
  expect(fixture.nativeElement.querySelector('h1').textContent).toBe('Hello');
});
```

`await fixture.whenStable()` waits for the scheduler to settle — all pending
microtasks, effects, and CD cycles complete before your assertion runs. This
mirrors production behavior more closely than `fixture.detectChanges()`, which
forces a synchronous CD cycle that may not match the timing of zoneless
production code.

The Angular docs are explicit: **avoid `fixture.detectChanges()` in new zoneless
tests**. For existing test suites, `fixture.detectChanges()` still works — it's
not worth mass-migrating stable tests.

### How TestBed works under the hood

`TestBed.configureTestingModule()` spins up a **minimal Angular environment**
in memory — no browser DOM (JSDOM is used instead), no router, no HTTP client
unless you explicitly provide them. It:

1. Creates an `EnvironmentInjector` rooted at the test module
2. Registers all providers and imports declared in `configureTestingModule`
3. Compiles any component templates via `compileComponents()`

`TestBed.createComponent(MyComponent)` then:

1. Creates a component instance within the test injector tree
2. Attaches it to a real (JSDOM) DOM node
3. Returns a `ComponentFixture<MyComponent>` wrapping both

The fixture gives you access to the component instance (`.componentInstance`),
the DOM (`.nativeElement`), and change detection control (`.detectChanges()`,
`.whenStable()`).

### NgModule vs standalone in tests

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13) — declare components in declarations[]
TestBed.configureTestingModule({
  declarations: [MyComponent, MockChildComponent],
  imports: [CommonModule, ReactiveFormsModule],
  providers: [{ provide: MyService, useClass: MockMyService }],
});
```

```typescript
// Standalone approach (Angular 14+ — recommended)
// Standalone components go in imports[], not declarations[]
TestBed.configureTestingModule({
  imports: [MyComponent],    // MyComponent brings its own deps
  providers: [
    { provide: MyService, useValue: mockMyService },
  ],
});
```

For standalone components, you often override specific imports after the fact:

```typescript
TestBed.overrideComponent(MyComponent, {
  set: {
    imports: [MockChildComponent],  // replace real child with fake
  }
});
```

## Basic usage

### Service unit tests — no DOM needed

Services don't need `createComponent` or a fixture. Just configure the providers
and inject:

```typescript
import { TestBed } from '@angular/core/testing';
import { CartService } from './cart.service';

describe('CartService', () => {
  let service: CartService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CartService],
    });
    service = TestBed.inject(CartService);
  });

  it('should start with an empty cart', () => {
    expect(service.items().length).toBe(0);
  });

  it('should add items', () => {
    service.add({ id: '1', name: 'Widget', price: 9.99 });
    expect(service.items().length).toBe(1);
    expect(service.total()).toBe(9.99);
  });

  it('should remove items', () => {
    service.add({ id: '1', name: 'Widget', price: 9.99 });
    service.remove('1');
    expect(service.items().length).toBe(0);
  });
});
```

### Component unit tests — standalone

```typescript
import { TestBed } from '@angular/core/testing';
import { ComponentFixture } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { CounterComponent } from './counter.component';

describe('CounterComponent', () => {
  let fixture: ComponentFixture<CounterComponent>;
  let component: CounterComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CounterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CounterComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();    // initial render settled
  });

  it('should display count 0 on init', () => {
    const p = fixture.nativeElement.querySelector('p');
    expect(p.textContent).toContain('0');
  });

  it('should increment on button click', async () => {
    const btn = fixture.debugElement.query(By.css('button'));
    btn.triggerEventHandler('click', null);

    await fixture.whenStable();    // wait for CD to process the click
    expect(component.count()).toBe(1);
    expect(fixture.nativeElement.querySelector('p').textContent).toContain('1');
  });

  it('should accept an initial count via input', async () => {
    fixture.componentRef.setInput('initialCount', 5);
    await fixture.whenStable();
    expect(component.count()).toBe(5);
  });
});
```

`fixture.componentRef.setInput()` sets a signal input (or `@Input`) and
schedules change detection — use `await fixture.whenStable()` after it.

### Mocking dependencies

```typescript
import { signal } from '@angular/core';

describe('UserCardComponent', () => {
  // Minimal fake service — only implement what this test needs
  const mockUserService = {
    currentUser: signal<User | null>({ id: '1', name: 'Alice', role: 'admin' }),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserCardComponent],
      providers: [
        { provide: UserService, useValue: mockUserService },
      ],
    }).compileComponents();
  });

  it('should show admin badge for admin users', async () => {
    const fixture = TestBed.createComponent(UserCardComponent);
    await fixture.whenStable();

    const badge = fixture.nativeElement.querySelector('[data-testid="admin-badge"]');
    expect(badge).toBeTruthy();
  });

  it('should hide admin badge for regular users', async () => {
    mockUserService.currentUser.set({ id: '2', name: 'Bob', role: 'viewer' });

    const fixture = TestBed.createComponent(UserCardComponent);
    await fixture.whenStable();

    const badge = fixture.nativeElement.querySelector('[data-testid="admin-badge"]');
    expect(badge).toBeNull();
  });
});
```

> **Note:** Use `data-testid` attributes on elements you want to query in tests.
> Angular removed `ng-reflect-*` attributes in v20 — selectors like
> `[ng-reflect-value="foo"]` no longer work.

### Testing signals and effects

Test signals by reading them directly — no special helper needed:

```typescript
describe('CounterStore signal', () => {
  let store: CounterStore;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CounterStore],
    });
    store = TestBed.inject(CounterStore);
  });

  it('should track count signal', () => {
    expect(store.count()).toBe(0);
    store.increment();
    expect(store.count()).toBe(1);
  });

  it('should track computed double', () => {
    store.increment();
    store.increment();
    expect(store.double()).toBe(4);
  });
});
```

For effects, use `TestBed.tick()` (v20+) to flush pending effects synchronously:

```typescript
it('should sync theme to localStorage', () => {
  const store = TestBed.inject(ThemeStore);
  const spy = spyOn(localStorage, 'setItem');

  store.setTheme('dark');
  TestBed.tick();      // flush pending effects

  expect(spy).toHaveBeenCalledWith('theme', 'dark');
});
```

### Testing HTTP services

Use `provideHttpClientTesting()` and `HttpTestingController`:

```typescript
import { HttpClient, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

describe('ProductService', () => {
  let service: ProductService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ProductService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(ProductService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => controller.verify());  // assert no unexpected requests

  it('should fetch products', () => {
    const mockProducts = [{ id: '1', name: 'Widget' }];
    let result: Product[] | undefined;

    service.getAll().subscribe(p => (result = p));

    const req = controller.expectOne('/api/products');
    expect(req.request.method).toBe('GET');
    req.flush(mockProducts);

    expect(result).toEqual(mockProducts);
  });

  it('should handle 404 errors', () => {
    let error: Error | undefined;

    service.getById('999').subscribe({ error: e => (error = e) });

    controller.expectOne('/api/products/999').flush(
      'Not found',
      { status: 404, statusText: 'Not Found' }
    );

    expect(error?.message).toContain('not found');
  });
});
```

## Test runner evolution — Karma → Jest → Vitest

This is the other half of the mechanism reflection. Angular's test runner story
has changed completely since the early days — and the API you write tests in
today looks like Jest, not Jasmine, even though Jasmine is still technically
the assertion library.

### Old model — Karma + Jasmine (Angular 2–20 default)

For the first eight years of Angular, the default test setup was:

| Layer | Tool | What it does |
| --- | --- | --- |
| Test framework | **Jasmine** | `describe`, `it`, `expect`, `spy` |
| Test runner | **Karma** | Launches a real browser, serves test files, reports results |
| Build | `@angular-devkit/build-angular:karma` | Webpack-based compilation of test files |

**Why Karma felt slow:**
Karma launches a real browser (Chrome, Firefox) every time you run `ng test`.
The browser starts, Angular compiles all test files with Webpack, the files
are served to the browser, tests run, results come back. For a large app
this could take 20–60 seconds just to start, and rebuilds on file save were
also slow due to Webpack's transformation overhead.

**Why the community moved to Jest:**
Jest runs in Node.js with a virtual DOM (JSDOM) — no real browser launch, no
Webpack, just fast native transforms. The community built `jest-preset-angular`
to bridge the gap. Many large Angular teams switched to Jest for the speed
improvement alone. But it was never the official Angular recommendation.

**Karma's deprecation:** Google's Chrome team deprecated the Karma project in
2023. It remains functional but receives no new features. This accelerated
Angular's official switch.

### New model — Vitest (Angular 21+ default)

Angular 21 introduced **Vitest** as the official test runner via the
`@angular/build:unit-test` builder. New projects generated with `ng new`
now use Vitest by default.

| Layer | Tool | What it does |
| --- | --- | --- |
| Test framework | **Vitest** | `describe`, `it`, `expect`, `vi` — Jest-compatible API |
| DOM environment | **JSDOM** | Virtual DOM, no real browser needed |
| Build | `@angular/build:unit-test` | Vite + esbuild — much faster compilation |

**Vitest's relationship to Jest:** Vitest was designed as a Jest-compatible
drop-in. It shares the same `describe` / `it` / `expect` / `beforeEach` /
`afterEach` vocabulary. The main difference is that Jest uses `jest.fn()` and
`jest.spyOn()` while Vitest uses `vi.fn()` and `vi.spyOn()`. If you know Jest,
you know Vitest — and vice versa.

**Why Vitest and not Jest?** Vitest is built on Vite, which Angular 22 uses
as its build tool. This gives you a unified build pipeline — the same Vite
config and esbuild transforms that build your app also run your tests. No
separate webpack-for-production / jest-transformer-for-tests split. Rebuild
times on watch mode drop from seconds to milliseconds.

### Side-by-side: how the same test looks across all three runners

```typescript
// All three runners — identical test body
describe('CartService', () => {
  it('should add items', () => {
    const service = new CartService();
    service.add({ id: '1', name: 'Widget', price: 9.99 });
    expect(service.items().length).toBe(1);
  });
});
```

The difference shows up only when you need mocking or spying:

```typescript
// Jasmine / Karma
const spy = spyOn(service, 'save').and.returnValue(Promise.resolve());
expect(spy).toHaveBeenCalled();

// Jest
const spy = jest.spyOn(service, 'save').mockResolvedValue(undefined);
expect(spy).toHaveBeenCalled();

// Vitest (Angular 22 default)
import { vi } from 'vitest';
const spy = vi.spyOn(service, 'save').mockResolvedValue(undefined);
expect(spy).toHaveBeenCalled();
```

The `expect`, `describe`, `it`, `beforeEach`, `afterEach` API is **identical**
across all three. Only the mock/spy API differs.

### Setup for new vs existing projects

**New project (Angular 22 — Vitest):**

```json
// angular.json — generated automatically
"test": {
  "builder": "@angular/build:unit-test",
  "options": {
    "buildTarget": "my-app:build"
  }
}
```

```bash
ng test    # starts Vitest in watch mode
```

**Existing project (legacy — Karma/Jasmine):**

```json
"test": {
  "builder": "@angular-devkit/build-angular:karma",
  "options": {
    "polyfills": ["zone.js", "zone.js/testing"]
  }
}
```

For zoneless projects on Karma, remove `zone.js` and `zone.js/testing` from
polyfills. To migrate a Karma project to Vitest, run:

```bash
ng generate @angular/build:vitest-migration
```

The migration schematic updates `angular.json`, removes Karma config files,
and adjusts `jest.fn()` → `vi.fn()` calls if you previously used Jest.

## Real-world patterns

### Pattern 1 — Page Object for readable tests

A page object wraps DOM queries so tests read like user stories, not CSS selectors:

```typescript
// counter.po.ts
class CounterPage {
  constructor(private fixture: ComponentFixture<CounterComponent>) {}

  get countText(): string {
    return this.fixture.nativeElement.querySelector('[data-testid="count"]').textContent;
  }

  async clickIncrement(): Promise<void> {
    this.fixture.nativeElement.querySelector('[data-testid="increment"]').click();
    await this.fixture.whenStable();
  }

  async clickDecrement(): Promise<void> {
    this.fixture.nativeElement.querySelector('[data-testid="decrement"]').click();
    await this.fixture.whenStable();
  }
}

// counter.spec.ts — tests read clearly
describe('CounterComponent', () => {
  it('increments', async () => {
    const { page } = await setup();
    await page.clickIncrement();
    expect(page.countText).toContain('1');
  });
});

async function setup() {
  await TestBed.configureTestingModule({
    imports: [CounterComponent],
  }).compileComponents();
  const fixture = TestBed.createComponent(CounterComponent);
  await fixture.whenStable();
  return { fixture, page: new CounterPage(fixture) };
}
```

### Pattern 2 — Testing a component with a spy on a real service

Sometimes a thin spy on a real service is cleaner than a full mock:

```typescript
describe('LoginComponent', () => {
  let authService: AuthService;
  let navigateSpy: jasmine.Spy;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [AuthService],
    }).compileComponents();

    authService = TestBed.inject(AuthService);
    const router = TestBed.inject(Router);
    navigateSpy = spyOn(router, 'navigate');
  });

  it('should navigate to dashboard on successful login', async () => {
    spyOn(authService, 'login').and.returnValue(Promise.resolve(true));

    const fixture = TestBed.createComponent(LoginComponent);
    await fixture.whenStable();

    fixture.componentInstance.form.setValue({
      email: 'alice@example.com',
      password: 'secret',
    });

    fixture.nativeElement.querySelector('[data-testid="submit"]').click();
    await fixture.whenStable();

    expect(navigateSpy).toHaveBeenCalledWith(['/dashboard']);
  });
});
```

## Common mistakes

### Mistake 1 — Querying the DOM before `whenStable()`

`TestBed.createComponent()` does not run change detection. Querying immediately
after creation gives you the pre-render state:

```typescript
// ❌ DOM hasn't rendered yet
const fixture = TestBed.createComponent(MyComponent);
expect(fixture.nativeElement.querySelector('p').textContent).toBe('Hello'); // fails

// ✅ Wait for Angular to settle first
const fixture = TestBed.createComponent(MyComponent);
await fixture.whenStable();
expect(fixture.nativeElement.querySelector('p').textContent).toBe('Hello');
```

### Mistake 2 — Using `TestBed.get()` (removed in v20)

`TestBed.get()` was deprecated in v9 and finally removed in v20. Use
`TestBed.inject()`:

```typescript
// ❌ Removed — will throw ReferenceError in Angular 20+
const service = TestBed.get(MyService);

// ✅ Correct
const service = TestBed.inject(MyService);
```

### Mistake 3 — Selecting elements with `ng-reflect-*` attributes

Angular removed `ng-reflect-*` debug attributes in v20. Tests using those
selectors silently fail to find elements:

```typescript
// ❌ ng-reflect-* attributes no longer exist in the DOM
fixture.nativeElement.querySelector('[ng-reflect-router-link="/home"]');

// ✅ Use data-testid attributes on your elements
// In template: <a routerLink="/home" data-testid="home-link">
fixture.nativeElement.querySelector('[data-testid="home-link"]');
```

### Mistake 4 — Calling `flushEffects()` (deprecated since v20)

```typescript
// ❌ Deprecated — flushEffects() removed in v20+
TestBed.flushEffects();

// ✅ Use TestBed.tick() to run pending effects and CD
TestBed.tick();
```

### Mistake 5 — Missing `await` before `fixture.whenStable()`

`whenStable()` returns a Promise. Without `await`, the assertion runs
immediately before Angular has settled:

```typescript
// ❌ Missing await — assertion runs before Angular settles
it('should update', () => {
  component.name.set('Bob');
  fixture.whenStable();   // returns Promise, not awaited
  expect(fixture.nativeElement.textContent).toContain('Bob');  // may fail
});

// ✅ Always await whenStable()
it('should update', async () => {
  component.name.set('Bob');
  await fixture.whenStable();
  expect(fixture.nativeElement.textContent).toContain('Bob');
});
```

## How this evolved

> - **Angular 2 (2016):** `TestBed` introduced. Zone.js-based, NgModule
>   declarations required, `fixture.detectChanges()` mandatory. `TestBed.get()`
>   for service retrieval.
>
> - **Angular 9 (2019):** `TestBed.inject()` introduced; `TestBed.get()`
>   deprecated. Ivy (the new compiler) enabled AOT-compiled tests.
>
> - **Angular 14 (2022):** Standalone components. Tests could import standalone
>   components directly in `imports[]` without NgModule wrappers.
>
> - **Angular 17 (2023):** `TestBed.flushEffects()` introduced for flushing
>   signal effects in tests. `ComponentFixture.autoDetectChanges()` boolean
>   parameter deprecated.
>
> - **Angular 19 (2024):** `@angular/build:unit-test` builder with Vitest
>   introduced as experimental. AoT compilation for tests enabled.
>
> - **Angular 20 (2025):** `TestBed.get()` removed. `ng-reflect-*` attributes
>   removed from the DOM. `TestBed.flushEffects()` deprecated in favor of
>   `TestBed.tick()`. `provideZonelessChangeDetection()` stable.
>
> - **Angular 21 (2025):** **Zoneless is the default.** CLI generates
>   `await fixture.whenStable()` in new component tests. Vitest becomes the
>   default test runner. `jest` and `web-test-runner` experimental builders
>   removed.
>
> - **Angular 22 (now):** `TestBed.tick()` stable. Vitest is the standard.
>   Tests for new projects: standalone imports, `await fixture.whenStable()`,
>   `TestBed.inject()`, `data-testid` selectors. `fixture.detectChanges()` still
>   supported for existing test suites — not worth mass-migrating.

## See also

- [Integration Tests](./integration-tests.md) — testing component trees together
  with real child components
- [Component Harnesses](./component-harnesses.md) — the CDK's stable API for
  interacting with Angular Material components in tests
- [Change Detection](../components/change-detection.md) — why `whenStable()`
  waits for what it waits for
- [Signals](../reactivity/signals.md) — `TestBed.tick()` for testing effects
- [HTTP](../http/http.md) — `provideHttpClientTesting()` setup covered in the
  HTTP overview
- [Official docs — Testing overview](https://angular.dev/guide/testing)
- [Official docs — Component test scenarios](https://angular.dev/guide/testing/components-scenarios)
- [Official docs — Zoneless testing](https://angular.dev/guide/zoneless#testing)

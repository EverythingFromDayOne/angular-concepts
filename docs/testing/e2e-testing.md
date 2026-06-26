---
roadmap_node: "e2e-testing"
title: "E2E Testing"
file: "testing/e2e-testing.md"
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

# E2E Testing

> **Lead with this:** E2E tests launch a real browser, load your running app,
> and automate what a user would do — click, type, navigate, assert. They catch
> the bugs that unit and integration tests can't: broken routing in production
> builds, third-party script failures, cross-component flows.

## What it is

End-to-end tests sit at the top of the testing pyramid — broadest scope, slowest
feedback, fewest in number. They verify **complete user journeys** through your
real application running in a real browser.

```
         /\
        /E2E\        ← few, slow, highest confidence
       /------\
      / Integr. \    ← some, moderate speed
     /------------\
    /   Unit tests  \ ← many, fast, lowest scope
   /------------------\
```

Use E2E tests for critical paths — login, checkout, form submission, navigation
flows. Don't use them for logic that unit tests can cover more quickly and reliably.

Angular v22 ships **no built-in E2E tool**. The Angular team deprecated and
removed Protractor (the old default) and now provides CLI schematics to plug in
your chosen tool. The two most common choices:

| Tool | Architecture | Best for |
| --- | --- | --- |
| **Playwright** | CDP/WebKit protocol, Node.js | Cross-browser, multi-tab, CI-first |
| **Cypress** | In-browser runner | Interactive dev experience, single-origin |

## How it works under the hood

### Old mechanism — Protractor and the WebDriver protocol

Protractor (Angular's original E2E tool, created 2013, EOL August 2023) was
built on **Selenium WebDriver**. The test runner communicated with the browser
through a chain of network calls:

```
Test code (Node.js)
    │
    │  JSON Wire Protocol (HTTP)
    ▼
ChromeDriver / GeckoDriver (local process)
    │
    │  native browser automation API
    ▼
Browser
```

Every test action — `element(by.css()).click()` — was an HTTP request across this
chain. This introduced latency, race conditions, and flakiness. WebDriver's
protocol design meant Angular had to add `browser.waitForAngular()` — a hook
that told Protractor to wait until Angular's digest cycle finished before acting.
This helped but added overhead and still missed edge cases.

Protractor also had an `ElementFinder` API (`element(by.css('.foo'))`) that
returned lazy references, not real elements — confusing to debug.

### New mechanism — CDP and in-browser runners

Modern tools abandon WebDriver entirely:

**Playwright** uses the **Chrome DevTools Protocol (CDP)** for Chromium,
and equivalent low-level protocols for Firefox and WebKit (Safari). CDP is
a direct, high-bandwidth channel into the browser's internals — the same
protocol Chrome DevTools itself uses. This gives Playwright:

- Direct access to network, storage, console, performance APIs
- Genuine multi-tab, multi-frame, multi-origin support
- Automatic waiting built into every action — Playwright retries locating
  and interacting with elements until they're actionable, no `waitFor*` calls
  needed for the common case

```
Test code (Node.js)
    │
    │  CDP / WebSocket (same machine)
    ▼
Browser (Chromium / Firefox / WebKit)
```

**Cypress** takes a different approach: it runs your test code **inside the
browser itself**, injecting a runner that shares the same JavaScript runtime
as your app. This eliminates the network round-trip entirely but constrains
Cypress to a single origin per test and prevents multi-tab scenarios.

Both tools remove the flakiness that plagued WebDriver-based testing. Neither
needs Angular-specific waiting hooks — they wait for elements to become
actionable rather than waiting for Angular's internal cycle.

## Tool comparison

### Playwright

**Install via Angular CLI:**
```bash
ng add playwright-ng-schematics
# or: npm init playwright@latest (without CLI integration)
```

**Architecture:** Node.js process, CDP/WebKit protocol, true headless
**Browsers:** Chromium, Firefox, WebKit (Safari) — cross-browser in one tool
**Strengths:** multi-tab, multi-origin, CI performance, TypeScript-first,
  network interception, rich trace/video recording
**Limitations:** less interactive dev experience than Cypress; browser
  inspection is through a separate trace viewer

### Cypress

**Install via Angular CLI:**
```bash
ng add @cypress/schematic
```

**Architecture:** test code runs inside the browser
**Browsers:** Chrome, Firefox, Edge (no Safari/WebKit)
**Strengths:** best-in-class interactive runner (time-travel debugging, DOM
  snapshots), visual test recording, component testing built-in
**Limitations:** single origin per test, no multi-tab, no Safari support

**Which to choose:** Playwright for CI-first, cross-browser, or multi-origin
requirements. Cypress for teams that prioritize developer experience in the
interactive runner. Both are excellent — the choice often comes down to
which DX your team prefers.

## Basic usage

### Playwright

A full Playwright test for a login flow:

```typescript
// e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('shows validation errors for empty form', async ({ page }) => {
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByText('Email is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();
  });

  test('redirects to dashboard on successful login', async ({ page }) => {
    await page.getByLabel('Email').fill('alice@example.com');
    await page.getByLabel('Password').fill('correct-password');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Welcome, Alice' }))
      .toBeVisible();
  });

  test('shows error message for wrong credentials', async ({ page }) => {
    await page.getByLabel('Email').fill('alice@example.com');
    await page.getByLabel('Password').fill('wrong-password');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByRole('alert')).toContainText('Invalid credentials');
    await expect(page).toHaveURL('/login');  // stays on login page
  });
});
```

**Playwright locator strategy — semantic over CSS:**

```typescript
// Preferred: semantic locators — resilient to UI redesign
page.getByRole('button', { name: 'Submit' })
page.getByLabel('Email address')
page.getByPlaceholder('Search products…')
page.getByText('Welcome back')
page.getByTestId('product-card')          // uses data-testid attribute

// Less preferred: CSS — breaks when class names change
page.locator('.btn-primary')              // fragile
page.locator('#submit-btn')              // fragile
```

`getByTestId` is a good middle ground — semantic intent but not tied to visible
text. Add `data-testid` attributes to elements you intend to test:

```html
<button data-testid="submit-order">Place Order</button>
```

**Playwright config:**

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env['CI'] ? 2 : 0,   // retry flaky tests on CI
  workers: process.env['CI'] ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4200',    // ng serve address
    trace: 'on-first-retry',            // record trace on failure
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
  ],
  webServer: {
    command: 'ng serve',
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env['CI'],
  },
});
```

The `webServer` block starts `ng serve` automatically before tests run and
shuts it down after — no manual server management in CI.

### Cypress

```typescript
// cypress/e2e/checkout.cy.ts
describe('Checkout flow', () => {
  beforeEach(() => {
    cy.visit('/cart');
  });

  it('shows empty cart message', () => {
    cy.get('[data-testid="empty-cart"]').should('contain.text', 'Your cart is empty');
  });

  it('proceeds to checkout with items in cart', () => {
    // Seed via intercept — no need for real backend
    cy.intercept('GET', '/api/cart', { fixture: 'cart-with-items.json' });
    cy.visit('/cart');

    cy.get('[data-testid="checkout-btn"]').click();
    cy.url().should('include', '/checkout');
  });

  it('submits order successfully', () => {
    cy.intercept('POST', '/api/orders', { statusCode: 201, body: { id: 'ORD-123' } })
      .as('createOrder');

    cy.get('[data-testid="place-order"]').click();
    cy.wait('@createOrder');
    cy.url().should('include', '/order-confirmation/ORD-123');
  });
});
```

## Real-world patterns

### Pattern 1 — Intercepting API calls in Playwright

Network interception makes E2E tests fast and deterministic — no real backend
needed for happy-path tests:

```typescript
test('shows products from the API', async ({ page }) => {
  // Intercept BEFORE navigation — route is set up before the app makes requests
  await page.route('/api/products*', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: '1', name: 'Widget', price: 9.99 },
        { id: '2', name: 'Gadget', price: 24.99 },
      ]),
    });
  });

  await page.goto('/products');

  await expect(page.getByTestId('product-card')).toHaveCount(2);
  await expect(page.getByText('Widget')).toBeVisible();
});
```

### Pattern 2 — Page Object Model for maintainability

When selectors are scattered across many test files, a change to the DOM
breaks all of them. A Page Object centralizes selectors:

```typescript
// e2e/pages/login.page.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async fillEmail(email: string) {
    await this.page.getByLabel('Email').fill(email);
  }

  async fillPassword(password: string) {
    await this.page.getByLabel('Password').fill(password);
  }

  async submit() {
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }

  async getErrorMessage() {
    return this.page.getByRole('alert').textContent();
  }
}

// e2e/login.spec.ts — test reads like a user story
test('login with wrong password shows error', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.fillEmail('alice@example.com');
  await loginPage.fillPassword('wrong');
  await loginPage.submit();

  expect(await loginPage.getErrorMessage()).toContain('Invalid credentials');
});
```

### Pattern 3 — Authentication setup with storageState

Repeating login in every test is slow. Playwright's `storageState` saves
browser cookies and localStorage after one login and reuses it:

```typescript
// e2e/auth.setup.ts
import { test as setup } from '@playwright/test';

const authFile = '.playwright/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('test-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('/dashboard');

  // Save auth state — all subsequent tests reuse this
  await page.context().storageState({ path: authFile });
});
```

```typescript
// playwright.config.ts — apply saved auth state to all tests in a project
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'authenticated',
    dependencies: ['setup'],
    use: { storageState: '.playwright/user.json' },
  },
]
```

## Common mistakes

### Mistake 1 — Testing logic that belongs in unit tests

E2E tests are expensive. Routing all test coverage through E2E wastes CI
minutes and produces slow, flaky suites:

```typescript
// ❌ Testing a pure calculation via E2E — unit test territory
test('calculates 10% discount correctly', async ({ page }) => {
  await page.goto('/products/1');
  await page.getByRole('button', { name: 'Apply 10% discount' }).click();
  await expect(page.getByTestId('price')).toHaveText('$8.99');
});

// ✅ Unit test for the calculation; E2E for the user journey
// Unit: expect(applyDiscount(9.99, 0.1)).toBe(8.99)
// E2E: test the checkout flow, not individual math
```

Reserve E2E for complete user flows. Everything else belongs in unit or
integration tests.

### Mistake 2 — Hard-coded waits

Never use `page.waitForTimeout()` or `cy.wait(2000)` for timing:

```typescript
// ❌ Fragile — breaks if the server is slow, passes incorrectly if fast
await page.waitForTimeout(2000);
expect(await page.getByTestId('result').textContent()).toBe('Done');

// ✅ Wait for the condition, not a duration
await expect(page.getByTestId('result')).toHaveText('Done');
// Playwright retries until the element has that text or the timeout expires
```

Playwright and Cypress have automatic waiting built in for every action and
assertion. Hard-coded waits are always wrong.

### Mistake 3 — CSS class selectors that break on design changes

Tests that select by class name break every time the design system changes:

```typescript
// ❌ Breaks when Tailwind classes change or SCSS is refactored
page.locator('.text-green-500.font-bold')

// ✅ Select by role, label, or data-testid — stable through redesigns
page.getByRole('status', { name: 'Success' })
page.getByTestId('order-status-success')
```

### Mistake 4 — Running E2E against the dev server in CI

`ng serve` is the development server — unoptimized, uses source maps, doesn't
tree-shake. E2E tests in CI should run against a production build:

```bash
# ❌ Dev server in CI — tests may pass locally, fail in production
ng serve &
npx playwright test

# ✅ Production build in CI
ng build
npx serve dist/my-app &
npx playwright test
```

If your E2E tests pass against the dev server but fail in production, it's
almost always a lazy-loading, code-splitting, or environment variable issue
that only manifests in the built artifact.

## How this evolved

> - **Angular 2–11 (2016–2020):** **Protractor** was the default E2E tool —
>   bundled with `ng new`, WebDriver-based, Selenium-powered. Tests were written
>   with `element(by.css())` and `browser.get()`. Fragile, slow, and required
>   `browser.waitForAngular()` to sync with Angular's CD cycle.
>
> - **Angular 12 (2021):** Protractor deprecated. Angular announced it would
>   not be investing in Protractor further. Community adoption of Cypress
>   had already reached ~64% even while Protractor was official.
>
> - **Angular 15 (2022):** Protractor development officially ended. New Angular
>   projects no longer include an E2E setup by default — `ng e2e` prompts you
>   to choose from the available schematics.
>
> - **August 2023:** Protractor reaches end of life. No security patches,
>   no maintenance.
>
> - **Angular 22 (now):** Five CLI-supported schematics: `@cypress/schematic`,
>   `playwright-ng-schematics`, `@nightwatch/schematics`, `@wdio/schematics`,
>   `@puppeteer/ng-schematics`. The Angular team does not endorse one over
>   another — both Cypress and Playwright are excellent choices.
>   Playwright is the recommended choice in new Angular documentation examples
>   due to its cross-browser support and first-class TypeScript API.

## See also

- [Unit Tests](./unit-tests.md) — the fast, isolated layer below E2E
- [Integration Tests](./integration-tests.md) — the middle layer; use these
  before reaching for E2E
- [Component Harnesses](./component-harnesses.md) — CDK harnesses usable in
  both integration and E2E tests
- [Official docs — End-to-end testing](https://angular.dev/tools/cli/end-to-end)
- [Playwright docs](https://playwright.dev)
- [Cypress docs](https://docs.cypress.io)
- [Playwright Angular schematic](https://github.com/playwright-community/playwright-ng-schematics)

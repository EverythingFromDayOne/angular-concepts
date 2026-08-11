---
roadmap_node: "component-harnesses"
title: "Component Harnesses"
file: "testing/component-harnesses.md"
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

# Component Harnesses

> **Lead with this:** A component harness gives you a stable testing API for a
> component — interact with its inputs, read its state, trigger its behaviors —
> without depending on its internal DOM structure. When the component is
> refactored, your tests don't break.

## What it is

When you test a component by querying its internal DOM directly — `querySelector('.mdc-button__label')`, `.triggerEventHandler('click', null)` — your test is coupled to implementation details. Rename a CSS class, restructure a template, and every test that touched that DOM breaks. This is especially painful with third-party component libraries like Angular Material, which sometimes restructure their internal HTML between versions.

**Component harnesses** solve this by providing a stable, documented API that sits in front of the DOM. Instead of reaching into the component's HTML, you call `harness.click()`, `harness.getValue()`, `harness.isDisabled()` — methods that the harness author intentionally exposed and commits to keeping stable across versions.

Angular CDK ships harnesses for all Angular Material components. You can also write your own harnesses for custom components — the same API, the same stability contract.

The harness system lives in `@angular/cdk/testing`. It has no runtime cost — it's purely a testing utility.

## How it works under the hood

### Old approach — direct DOM querying

A test for a Material button dialog flow without harnesses looks like this:

```typescript
// ❌ Direct DOM — coupled to Material's internal HTML structure
it('opens dialog on click', () => {
  const btn = fixture.nativeElement.querySelector('.mat-mdc-button');
  btn.click();
  fixture.detectChanges();

  // Dialog is in the document body — not inside the fixture
  const dialog = document.querySelector('.mat-mdc-dialog-container');
  expect(dialog).toBeTruthy();

  const title = document.querySelector('.mat-mdc-dialog-title');
  expect(title?.textContent).toContain('Confirm');
});
```

Problems:
- `.mat-mdc-button` and `.mat-mdc-dialog-container` are Material's internal class names, not its public API. They changed significantly from Material v14 to v15 (MDC migration). Every test that used them broke.
- The dialog renders outside the fixture root — you have to reach into `document.body` manually.
- No semantic meaning — `.mat-mdc-button` doesn't tell you what button you're clicking.

### New approach — harness API

The same test with harnesses:

```typescript
// ✅ Harness API — decoupled from internal DOM structure
it('opens dialog on click', async () => {
  const button = await loader.getHarness(MatButtonHarness.with({ text: 'Open Dialog' }));
  await button.click();

  // documentRootLoader finds things rendered outside the fixture (overlays, dialogs)
  const dialog = await rootLoader.getHarness(MatDialogHarness);
  expect(await dialog.getTitleText()).toBe('Confirm');
});
```

How this works internally: `TestbedHarnessEnvironment` wraps the fixture and provides `HarnessLoader` instances. When you call `loader.getHarness(MatButtonHarness)`, the loader queries the DOM using the `hostSelector` defined in `MatButtonHarness` (which is Angular Material's internal selector) and wraps the found element in a `UnitTestElement`. The `UnitTestElement` is an environment-agnostic wrapper that knows how to trigger events, read values, and interact with Angular's change detection in a way that works correctly in the test environment.

This abstraction layer is why harnesses work regardless of Angular Material's internal DOM changes — the harness class is updated alongside the component, so the method names stay stable even when the underlying HTML structure changes.

### documentRootLoader — handling overlays and portals

Many Angular Material components render outside their host element — dialogs, tooltips, select dropdowns, date pickers all use the CDK Overlay and append to `document.body`. A `HarnessLoader` rooted at the fixture can't find these. That's what `documentRootLoader` is for:

```typescript
// loader — searches inside the fixture's root element
const loader = TestbedHarnessEnvironment.loader(fixture);

// rootLoader — searches the entire document (for overlays, dialogs, tooltips)
const rootLoader = TestbedHarnessEnvironment.documentRootLoader(fixture);
```

## Basic usage

### Setup

```typescript
import { HarnessLoader } from '@angular/cdk/testing';
import { TestbedHarnessEnvironment } from '@angular/cdk/testing/testbed';

// Note: two different import paths — intentional
// @angular/cdk/testing: environment-agnostic (HarnessLoader, ComponentHarness)
// @angular/cdk/testing/testbed: TestBed-specific (TestbedHarnessEnvironment)
```

```typescript
describe('MyButtonDialogComponent', () => {
  let fixture: ComponentFixture<MyButtonDialogComponent>;
  let loader: HarnessLoader;       // inside the fixture
  let rootLoader: HarnessLoader;   // entire document — for overlays

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MyButtonDialogComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MyButtonDialogComponent);
    loader = TestbedHarnessEnvironment.loader(fixture);
    rootLoader = TestbedHarnessEnvironment.documentRootLoader(fixture);
    await fixture.whenStable();
  });
});
```

> **Use `NoopAnimationsModule` (or `provideNoopAnimations()`)** in harness tests.
> Material animations are async — without disabling them, tests that interact
> with animated components (dialogs, menus, tabs) may time out or behave
> unexpectedly.

### Using Angular Material harnesses

```typescript
import {
  MatButtonHarness,
  MatInputHarness,
  MatSelectHarness,
  MatDialogHarness,
  MatCheckboxHarness,
} from '@angular/material/...'; // each component has its own /testing entrypoint

it('fills and submits a form', async () => {
  // Get individual inputs
  const nameInput = await loader.getHarness(MatInputHarness.with({ selector: '#name' }));
  const roleSelect = await loader.getHarness(MatSelectHarness);
  const agreeCheckbox = await loader.getHarness(MatCheckboxHarness.with({ label: 'I agree' }));
  const submitBtn = await loader.getHarness(MatButtonHarness.with({ text: 'Submit' }));

  // Interact through the harness API — no DOM selectors
  await nameInput.setValue('Alice');
  await roleSelect.open();
  await roleSelect.clickOptions({ text: 'Admin' });
  await agreeCheckbox.check();
  await submitBtn.click();

  await fixture.whenStable();
  expect(submitSpy).toHaveBeenCalledWith({ name: 'Alice', role: 'admin', agreed: true });
});

it('shows success dialog after submission', async () => {
  // ... fill form ...
  await submitBtn.click();

  // Dialog renders outside fixture — use rootLoader
  const dialog = await rootLoader.getHarness(MatDialogHarness);
  expect(await dialog.getTitleText()).toBe('Success!');

  const closeBtn = await dialog.getHarness(MatButtonHarness.with({ text: 'Close' }));
  await closeBtn.click();

  // Dialog gone
  expect(await rootLoader.hasHarness(MatDialogHarness)).toBeFalse();
});
```

### HarnessLoader query methods

```typescript
// Get the first matching harness — throws if none found
const button = await loader.getHarness(MatButtonHarness);

// Get all matching harnesses
const buttons = await loader.getAllHarnesses(MatButtonHarness);
expect(buttons.length).toBe(3);

// Check existence without throwing
const hasError = await loader.hasHarness(MatErrorHarness);
expect(hasError).toBeTrue();

// Count matches
const count = await loader.countHarnesses(MatChipHarness);
expect(count).toBe(5);

// Get by index
const secondOption = await loader.getHarnessAtIndex(MatOptionHarness, 1);
```

### HarnessPredicate — filtering harnesses

When you have multiple instances of a component, filter with `.with()`:

```typescript
// By text content
const saveBtn = await loader.getHarness(MatButtonHarness.with({ text: 'Save' }));
const cancelBtn = await loader.getHarness(MatButtonHarness.with({ text: 'Cancel' }));

// By CSS selector
const disabledInput = await loader.getHarness(
  MatInputHarness.with({ selector: '[disabled]' })
);

// By ancestor — find a button inside a specific section
const submitInFooter = await loader.getHarness(
  MatButtonHarness.with({ ancestor: 'footer' })
);
```

### parallel() — running queries concurrently

```typescript
import { parallel } from '@angular/cdk/testing';

// ❌ Sequential — three round-trips
const mode = await progressBar.getMode();
const value = await progressBar.getValue();
const isIndeterminate = await progressBar.isIndeterminate();

// ✅ Concurrent — one batch operation
const [mode, value, isIndeterminate] = await parallel(() => [
  progressBar.getMode(),
  progressBar.getValue(),
  progressBar.isIndeterminate(),
]);
```

`parallel()` runs all the harness queries in a single batch, which is faster
and avoids multiple change detection cycles between reads.

### Writing a custom harness

Extend `ComponentHarness` and implement `static hostSelector`:

```typescript
// rating.harness.ts
import { ComponentHarness, HarnessPredicate } from '@angular/cdk/testing';

export interface RatingHarnessFilters {
  maxRating?: number;
}

export class RatingHarness extends ComponentHarness {
  // Must match the component's selector — the loader uses this to find instances
  static hostSelector = 'app-rating';

  // Locators for internal elements — lazy, won't throw if missing
  private readonly stars = this.locatorForAll('[data-testid="star"]');
  private readonly activeStars = this.locatorForAll('[data-testid="star"].active');

  /** Gets the number of stars selected. */
  async getRating(): Promise<number> {
    return (await this.activeStars()).length;
  }

  /** Gets the total number of stars. */
  async getMaxRating(): Promise<number> {
    return (await this.stars()).length;
  }

  /** Selects a specific star (1-based). */
  async setRating(stars: number): Promise<void> {
    const allStars = await this.stars();
    await allStars[stars - 1].click();
  }

  /** Checks whether the component is disabled. */
  async isDisabled(): Promise<boolean> {
    return (await this.host()).hasClass('disabled');
  }

  /** Filtering factory — create a HarnessPredicate */
  static with(options: RatingHarnessFilters): HarnessPredicate<RatingHarness> {
    return new HarnessPredicate(RatingHarness, options)
      .addOption('maxRating', options.maxRating, async (harness, maxRating) =>
        (await harness.getMaxRating()) === maxRating
      );
  }
}
```

Consuming the custom harness:

```typescript
it('starts at zero stars', async () => {
  const rating = await loader.getHarness(RatingHarness);
  expect(await rating.getRating()).toBe(0);
  expect(await rating.getMaxRating()).toBe(5);
});

it('can select a rating', async () => {
  const rating = await loader.getHarness(RatingHarness);
  await rating.setRating(3);
  expect(await rating.getRating()).toBe(3);
});

it('can find a 10-star rating by filter', async () => {
  const bigRating = await loader.getHarness(RatingHarness.with({ maxRating: 10 }));
  expect(await bigRating.getMaxRating()).toBe(10);
});
```

## Real-world patterns

### Pattern 1 — Harnesses with a dialog workflow

A complete test of a confirm-delete dialog using both `loader` (for the trigger)
and `rootLoader` (for the dialog, which renders in the overlay):

```typescript
describe('DeleteUserComponent', () => {
  let loader: HarnessLoader;
  let rootLoader: HarnessLoader;
  let userService: jasmine.SpyObj<UserService>;

  beforeEach(async () => {
    userService = jasmine.createSpyObj('UserService', ['delete']);
    userService.delete.and.returnValue(Promise.resolve());

    await TestBed.configureTestingModule({
      imports: [DeleteUserComponent, NoopAnimationsModule],
      providers: [{ provide: UserService, useValue: userService }],
    }).compileComponents();

    const fixture = TestBed.createComponent(DeleteUserComponent);
    loader = TestbedHarnessEnvironment.loader(fixture);
    rootLoader = TestbedHarnessEnvironment.documentRootLoader(fixture);
    await fixture.whenStable();
  });

  it('deletes user on confirm', async () => {
    const deleteBtn = await loader.getHarness(
      MatButtonHarness.with({ text: 'Delete User' })
    );
    await deleteBtn.click();

    // Dialog opens in overlay — use rootLoader
    const dialog = await rootLoader.getHarness(MatDialogHarness);
    expect(await dialog.getTitleText()).toContain('Delete');

    const confirmBtn = await dialog.getHarness(
      MatButtonHarness.with({ text: 'Confirm' })
    );
    await confirmBtn.click();

    expect(userService.delete).toHaveBeenCalled();
  });

  it('cancels without deleting', async () => {
    await (await loader.getHarness(MatButtonHarness.with({ text: 'Delete User' }))).click();

    const dialog = await rootLoader.getHarness(MatDialogHarness);
    await (await dialog.getHarness(MatButtonHarness.with({ text: 'Cancel' }))).click();

    expect(userService.delete).not.toHaveBeenCalled();
    expect(await rootLoader.hasHarness(MatDialogHarness)).toBeFalse();
  });
});
```

### Pattern 2 — Testing a list of items with harnesses

```typescript
it('renders the correct number of chips and allows removal', async () => {
  const chips = await loader.getAllHarnesses(MatChipHarness);
  expect(chips.length).toBe(3);

  // Read text via harness
  const labels = await parallel(() => chips.map(c => c.getText()));
  expect(labels).toEqual(['Angular', 'TypeScript', 'RxJS']);

  // Remove the first chip
  await chips[0].remove();
  expect(await loader.countHarnesses(MatChipHarness)).toBe(2);
});
```

## Common mistakes

### Mistake 1 — Using the wrong loader for overlays

The most common harness bug: dialogs, menus, tooltips, date pickers all render
in `document.body` via CDK Overlay. Using `loader` (fixture-rooted) instead of
`rootLoader` (document-rooted) returns null or throws:

```typescript
// ❌ Dialog renders outside the fixture — getHarness throws "not found"
const dialog = await loader.getHarness(MatDialogHarness);

// ✅ documentRootLoader searches the whole document
const rootLoader = TestbedHarnessEnvironment.documentRootLoader(fixture);
const dialog = await rootLoader.getHarness(MatDialogHarness);
```

The rule: if the component uses `CdkOverlay` (dialogs, selects, autocomplete,
menus, tooltips), use `rootLoader`.

### Mistake 2 — Forgetting NoopAnimationsModule / provideNoopAnimations()

Material components with animations (dialogs, drawers, expansion panels) have
async open/close sequences. Without disabling animations, harness operations
may resolve before the animation completes:

```typescript
// ❌ Real animations — dialog may not be "open" when harness checks
TestBed.configureTestingModule({
  imports: [MyComponent, BrowserAnimationsModule],
});

// ✅ Noop animations — synchronous state transitions in tests
TestBed.configureTestingModule({
  imports: [MyComponent, NoopAnimationsModule],
  // or: providers: [provideNoopAnimations()]
});
```

### Mistake 3 — Not awaiting harness methods

Every harness method is async. Missing an `await` silently passes on the
unresolved Promise:

```typescript
// ❌ No await — assigns a Promise, not the value; assertion always passes
const text = loader.getHarness(MatInputHarness);
expect(text).toBeTruthy();   // Promise is always truthy

// ✅ Await every harness call
const input = await loader.getHarness(MatInputHarness);
const value = await input.getValue();
expect(value).toBe('Alice');
```

### Mistake 4 — Mixing harness and direct DOM assertions on the same element

Harness methods trigger Angular's change detection internally. Mixing them with
direct DOM reads can produce inconsistent state:

```typescript
// ❌ Harness click triggers CD internally; direct DOM read may see stale state
await button.click();
expect(fixture.nativeElement.querySelector('.active')).toBeTruthy();

// ✅ Use harness for everything, or flush manually before raw DOM read
await button.click();
await fixture.whenStable();
expect(fixture.nativeElement.querySelector('.active')).toBeTruthy();
```

## How this evolved

> - **Angular 9 / Material 9 (2020):** Component harnesses introduced in
>   `@angular/cdk/testing`. All Angular Material components got corresponding
>   harnesses. Two environments shipped: `TestbedHarnessEnvironment` (unit/
>   integration tests) and `ProtractorHarnessEnvironment` (E2E with Protractor).
>
> - **Angular 12 (2021):** Material underwent the MDC migration — internal DOM
>   restructured to use Material Design Components primitives. Every direct DOM
>   test using Material's internal CSS classes (`.mat-button`, `.mat-dialog-container`)
>   broke. Tests using harnesses were unaffected — the harnesses were updated
>   alongside the components.
>   This is the clearest real-world demonstration of why harnesses exist.
>
> - **Angular 15 (2022):** `ProtractorHarnessEnvironment` deprecated alongside
>   Protractor. The CDK docs now recommend implementing a custom `HarnessEnvironment`
>   for Playwright or Cypress if E2E harness support is needed.
>
> - **Angular 22 (now):** Harnesses are the recommended testing strategy for
>   any Angular Material component. The harness API is stable and unchanged.
>   The two environments remain `TestbedHarnessEnvironment` (unit/integration)
>   and `SeleniumWebDriverHarnessEnvironment` (Selenium WebDriver). Writing
>   custom harnesses for your own component library is considered best practice
>   for any shared component library team.

## See also

- [Unit Tests](./unit-tests.md) — `TestBed` setup that harnesses plug into
- [Integration Tests](./integration-tests.md) — component trees where harnesses
  replace direct DOM queries
- [Angular Material](../components/styling/angular-material.md) — the component
  library whose harnesses you'll use most
- [Official docs — Using component harnesses](https://angular.dev/guide/testing/using-component-harnesses)
- [Official docs — Creating component harnesses](https://angular.dev/guide/testing/creating-component-harnesses)
- [Material harness catalog](https://material.angular.io) — every Material component
  lists its harness and available query options

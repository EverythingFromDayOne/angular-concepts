---
recipe_id: "dynamic-forms"
title: "Dynamic Forms: Shape That Changes With User Input"
file: "recipes/forms-and-search/dynamic-forms.md"
primary_concept: "forms/reactive-forms"
related_concepts: ["forms/validation", "reactivity/signals", "reactivity/to-signal"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Dynamic Forms: Shape That Changes With User Input

> **What you'll build:** real-world solutions for the five patterns that
> make forms "dynamic" — conditional sub-forms that preserve user input
> across toggles, repeating line items via `FormArray`, type-discriminated
> forms (different fields per option), cascading dependent dropdowns, and
> dynamic validators. Plus the one method call (`updateValueAndValidity`)
> that nobody talks about and everybody forgets.
>
> **Concepts you'll touch:** [Reactive Forms](../../forms/reactive-forms.md), [Validation](../../forms/validation.md), [Signals](../../reactivity/signals.md), [toSignal / toObservable](../../reactivity/to-signal.md)
>
> **Time:** ~30 minutes to read; an afternoon to refactor a real form once
> you can see the patterns.

---

## The scenario

A user fills out an account registration form. There's a checkbox: "I have an emergency contact." When they check it, three fields appear — name, phone, relationship. They fill them in. They uncheck the checkbox to change their mind. Then they re-check it.

**Their data is gone.** They have to type it all again.

This is the most common "dynamic forms" bug. The fix involves adding and removing controls at runtime, and remembering values that were set on now-removed controls. The same patterns show up everywhere:

- **Checkout flows** — "Same as billing" toggle hides shipping fields; un-toggling should restore them
- **Order forms** — line items added/removed in a list
- **Payment forms** — radio selector flips between Card, Bank, PayPal; each has different fields
- **Address forms** — country → state → city, where states load after country picks
- **Profile forms** — "Notifications: email / SMS / push" — different validators per chosen mode

This recipe walks through the five patterns. Each one is a complete working component you can drop in and adapt.

---

## Pattern 1 — conditional sub-form with preserve-input

The checkbox-toggles-a-section pattern. The non-obvious part is preserving values across the toggle.

### The naive approach (and why it loses data)

```typescript
// BUGGY — values lost on every toggle
@Component({ /* … */ })
export class RegistrationComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    firstName: this.fb.control('', Validators.required),
    hasContact: this.fb.control(false),
    emergencyContact: this.fb.group({
      name: this.fb.control(''),
      phone: this.fb.control(''),
      relationship: this.fb.control(''),
    }),
  });

  constructor() {
    this.form.controls.hasContact.valueChanges.subscribe(hasContact => {
      const sub = this.form.controls.emergencyContact;
      if (hasContact) {
        sub.enable();
      } else {
        sub.disable();
        sub.reset();  // ← BUG: this wipes the values permanently
      }
    });
  }
}
```

Toggle off → `.reset()` clears the values. Toggle on → user sees empty fields. The fix has two pieces:

1. **Don't `.reset()` on toggle-off** — just hide
2. **Buffer the values** in case the user wants them back

### The fix — buffered sub-form

```typescript
// File: registration.component.ts
import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

interface ContactValue {
  name: string;
  phone: string;
  relationship: string;
}

@Component({ /* … */ })
export class RegistrationComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  // The buffer survives across toggles. Plain field works too; using a
  // signal lets us inspect it from the template during dev.
  private readonly contactBuffer = signal<ContactValue | null>(null);

  readonly form = this.fb.group({
    firstName: this.fb.control('', Validators.required),
    hasContact: this.fb.control(false),
    emergencyContact: this.fb.group({
      name: this.fb.control('', Validators.required),
      phone: this.fb.control('', [Validators.required, Validators.pattern(/^\+?\d[\d\s-]+$/)]),
      relationship: this.fb.control('', Validators.required),
    }),
  });

  constructor() {
    // Start with the sub-form disabled so its validators don't block submit.
    this.form.controls.emergencyContact.disable();

    this.form.controls.hasContact.valueChanges.pipe(
      takeUntilDestroyed(),
    ).subscribe(hasContact => {
      const sub = this.form.controls.emergencyContact;

      if (hasContact) {
        sub.enable();
        // Restore from buffer if we have one
        const buffered = this.contactBuffer();
        if (buffered) {
          sub.patchValue(buffered);
        }
      } else {
        // Save current values to buffer before disabling
        this.contactBuffer.set(sub.getRawValue());
        sub.disable();
      }
    });
  }

  onSubmit() {
    if (this.form.invalid) return;
    // form.value excludes disabled controls; use getRawValue() for all values
    const fullForm = this.form.getRawValue();
    console.log('Submitting:', fullForm);
  }
}
```

```html
<form [formGroup]="form" (submit)="onSubmit()">
  <input formControlName="firstName" placeholder="First name" />

  <label>
    <input type="checkbox" formControlName="hasContact" />
    I have an emergency contact
  </label>

  @if (form.controls.hasContact.value) {
    <fieldset formGroupName="emergencyContact">
      <input formControlName="name" placeholder="Name" />
      <input formControlName="phone" placeholder="Phone" />
      <input formControlName="relationship" placeholder="Relationship" />
    </fieldset>
  }

  <button type="submit" [disabled]="form.invalid">Register</button>
</form>
```

**Five things doing the work:**

- **`.disable()` instead of `.removeControl()`** — disabled controls don't run their validators (so the parent form stays valid when the section is hidden), but their structure is preserved. Cheaper than add/remove.
- **`getRawValue()` to read disabled values** — `form.value` strips disabled controls; `getRawValue()` includes them. This is the buffer source.
- **`form.value` for submit, `getRawValue()` for buffer** — different APIs for different needs.
- **`patchValue` instead of `setValue`** — `setValue` requires all keys to be present; `patchValue` accepts partial. The buffer might have stale data from before a schema change; `patchValue` is safer.
- **`@if (form.controls.hasContact.value)` in the template** — drives the visual show/hide directly from the form state. No separate `boolean` signal to keep in sync.

### Variant — `addControl` / `removeControl` for true structural changes

When you need the field to literally not exist in `form.value` (because it doesn't apply at all, not just "disabled"), use `addControl` and `removeControl`:

```typescript
constructor() {
  this.form.controls.hasContact.valueChanges.pipe(
    takeUntilDestroyed(),
  ).subscribe(hasContact => {
    if (hasContact) {
      const contactGroup = this.fb.group({
        name: this.fb.control('', Validators.required),
        phone: this.fb.control('', Validators.required),
        relationship: this.fb.control('', Validators.required),
      });
      const buffered = this.contactBuffer();
      if (buffered) contactGroup.patchValue(buffered);
      this.form.addControl('emergencyContact', contactGroup);
    } else {
      const existing = this.form.get('emergencyContact');
      if (existing) {
        this.contactBuffer.set(existing.getRawValue() as ContactValue);
        this.form.removeControl('emergencyContact');
      }
    }
  });
}
```

Trade-off: cleaner data shape (the key isn't in `form.value` when section is hidden), but TypeScript can't verify the dynamic shape. The form's static type still has `emergencyContact` even when it doesn't exist at runtime. Reads via `form.get('emergencyContact')?` to handle the possibly-absent case.

---

## Pattern 2 — repeating items via `FormArray`

Line items in an order. Items in a cart. Tasks in a checklist. The user adds and removes as they go.

```typescript
// File: order.component.ts
import { Component, inject } from '@angular/core';
import { FormArray, FormGroup, NonNullableFormBuilder, Validators } from '@angular/forms';

interface LineItem {
  product: FormControl<string>;
  quantity: FormControl<number>;
  unitPrice: FormControl<number>;
}

@Component({ /* … */ })
export class OrderComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    orderNumber: this.fb.control('', Validators.required),
    items: this.fb.array<FormGroup<LineItem>>([]),
  });

  get items(): FormArray<FormGroup<LineItem>> {
    return this.form.controls.items;
  }

  constructor() {
    // Start with one item so the user can begin entering immediately.
    this.addItem();
  }

  addItem(): void {
    this.items.push(this.buildItem());
  }

  removeItem(index: number): void {
    this.items.removeAt(index);
  }

  moveItem(fromIndex: number, toIndex: number): void {
    const control = this.items.at(fromIndex);
    this.items.removeAt(fromIndex);
    this.items.insert(toIndex, control);
  }

  clearItems(): void {
    this.items.clear();
  }

  private buildItem(): FormGroup<LineItem> {
    return this.fb.group({
      product: this.fb.control('', Validators.required),
      quantity: this.fb.control(1, [Validators.required, Validators.min(1)]),
      unitPrice: this.fb.control(0, [Validators.required, Validators.min(0)]),
    });
  }
}
```

```html
<form [formGroup]="form">
  <input formControlName="orderNumber" placeholder="Order #" />

  <div formArrayName="items">
    @for (item of items.controls; track item; let i = $index) {
      <fieldset [formGroupName]="i">
        <input formControlName="product" placeholder="Product" />
        <input formControlName="quantity" type="number" />
        <input formControlName="unitPrice" type="number" />
        <button type="button" (click)="removeItem(i)" [disabled]="items.length === 1">
          Remove
        </button>
      </fieldset>
    }
  </div>

  <button type="button" (click)="addItem()">+ Add item</button>
  <button type="submit" [disabled]="form.invalid">Place order</button>
</form>
```

**Five things doing the work:**

- **`FormArray<FormGroup<LineItem>>`** — fully typed, line-item shape known to TypeScript and the template.
- **`@for (item of items.controls; track item)`** — `track` by the control reference, not by index. This matters when items are reordered — using `track $index` would cause every item to re-render on reorder; tracking by reference re-renders only the moved ones.
- **`[formGroupName]="i"`** — binds each iteration to the FormGroup at that index. Required for nested form controls inside an array.
- **`items.controls` not `items.value`** — the template iterates over controls (which have `formGroupName`); the value is for reading data.
- **`items.removeAt(i)` not `splice`** — the form API methods notify Angular of the change; direct array manipulation doesn't.

### The "drag to reorder" pattern

For drag-and-drop reordering, the `moveItem(from, to)` helper above is the pattern: remove from one index, insert at another. Combined with the [Angular CDK drag-drop](https://material.angular.io/cdk/drag-drop/overview) directive, this handles the visual side. The recipe stays form-focused; the visual drag-drop is a separate UI library concern.

### `track` semantics matter for performance

For long lists (50+ items), `@for` tracking is the difference between snappy reorders and visible thrash. Two approaches:

```typescript
// Stable identity: track by the control reference itself
@for (item of items.controls; track item) { … }

// Or by a stable ID inside the FormGroup
@for (item of items.controls; track item.controls.id.value) { … }
```

The control-reference form is fine for short lists. For longer lists where items have natural IDs (existing order line items loaded from the server), tracking by ID is more robust because it survives form rebuilds (e.g., when the parent component patches the entire form).

---

## Pattern 3 — type-discriminated form (radio selector)

A payment form: the user picks Card, Bank, or PayPal. Each option requires different fields. The naive approach has all three sub-forms always present and conditionally hidden — but then their validators run even when hidden.

### The fix — swap the active sub-form

```typescript
type PaymentMethod = 'card' | 'bank' | 'paypal';

interface CardForm {
  cardNumber: FormControl<string>;
  expiry: FormControl<string>;
  cvv: FormControl<string>;
}

interface BankForm {
  accountNumber: FormControl<string>;
  routingNumber: FormControl<string>;
}

interface PaypalForm {
  email: FormControl<string>;
}

@Component({ /* … */ })
export class PaymentComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  // Buffers per method so switching back restores values.
  private readonly buffers = {
    card: signal<Partial<CardForm extends Record<string, FormControl<infer T>> ? T : never> | null>(null),
    bank: signal<Partial<{ accountNumber: string; routingNumber: string }> | null>(null),
    paypal: signal<{ email: string } | null>(null),
  };

  readonly form = this.fb.group({
    method: this.fb.control<PaymentMethod>('card'),
    amount: this.fb.control(0, [Validators.required, Validators.min(0.01)]),
    // 'details' starts as a Card form — replaced when method changes
    details: this.buildCardForm(),
  });

  constructor() {
    this.form.controls.method.valueChanges.pipe(
      takeUntilDestroyed(),
    ).subscribe(method => this.swapDetailsFor(method));
  }

  private swapDetailsFor(method: PaymentMethod): void {
    // Buffer current details before replacing
    const current = this.form.controls.details;
    if (current instanceof FormGroup) {
      const currentMethod = this.previousMethod;
      if (currentMethod) {
        (this.buffers as any)[currentMethod].set(current.getRawValue());
      }
    }

    // Build new sub-form for the chosen method
    const next =
      method === 'card' ? this.buildCardForm() :
      method === 'bank' ? this.buildBankForm() :
      this.buildPaypalForm();

    // Restore from buffer if present
    const buffered = (this.buffers as any)[method].value;
    if (buffered) next.patchValue(buffered);

    // Swap: removeControl + addControl as one logical operation
    this.form.removeControl('details');
    this.form.addControl('details', next);
    this.previousMethod = method;
  }

  private previousMethod: PaymentMethod | null = null;

  private buildCardForm() {
    return this.fb.group({
      cardNumber: this.fb.control('', [Validators.required, Validators.pattern(/^\d{16}$/)]),
      expiry: this.fb.control('', [Validators.required, Validators.pattern(/^\d{2}\/\d{2}$/)]),
      cvv: this.fb.control('', [Validators.required, Validators.pattern(/^\d{3,4}$/)]),
    });
  }

  private buildBankForm() {
    return this.fb.group({
      accountNumber: this.fb.control('', [Validators.required, Validators.minLength(8)]),
      routingNumber: this.fb.control('', [Validators.required, Validators.pattern(/^\d{9}$/)]),
    });
  }

  private buildPaypalForm() {
    return this.fb.group({
      email: this.fb.control('', [Validators.required, Validators.email]),
    });
  }
}
```

```html
<form [formGroup]="form">
  <label><input type="radio" formControlName="method" value="card" /> Card</label>
  <label><input type="radio" formControlName="method" value="bank" /> Bank</label>
  <label><input type="radio" formControlName="method" value="paypal" /> PayPal</label>

  <input formControlName="amount" type="number" placeholder="Amount" />

  <fieldset formGroupName="details">
    @switch (form.controls.method.value) {
      @case ('card') {
        <input [formControl]="getDetailsControl('cardNumber')" placeholder="Card number" />
        <input [formControl]="getDetailsControl('expiry')" placeholder="MM/YY" />
        <input [formControl]="getDetailsControl('cvv')" placeholder="CVV" />
      }
      @case ('bank') {
        <input [formControl]="getDetailsControl('accountNumber')" placeholder="Account #" />
        <input [formControl]="getDetailsControl('routingNumber')" placeholder="Routing #" />
      }
      @case ('paypal') {
        <input [formControl]="getDetailsControl('email')" placeholder="PayPal email" />
      }
    }
  </fieldset>
</form>
```

**The honest typing trade-off**: TypeScript can't verify that the `details` sub-form has the right shape for the current method. The `getDetailsControl(name: string)` helper is internally an unchecked cast. This is the cost of dynamic structural typing in forms.

Two ways to make this less painful:

1. **Discriminated union of typed sub-forms** — one type per method, narrowed by the `method` value
2. **Untyped helper that delegates to typed builders** — accept the unchecked cast at one boundary; the rest of the code stays typed

For most apps, option 2 is the practical choice. Type the builders (`buildCardForm()` returns `FormGroup<CardForm>`); accept that the runtime swap is untyped at the seam.

---

## Pattern 4 — cascading dependent controls

Country → State → City. Picking a country populates the state dropdown options. Picking a state populates the city dropdown.

```typescript
// File: address.component.ts
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NonNullableFormBuilder, Validators } from '@angular/forms';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Observable, of, switchMap } from 'rxjs';

@Component({ /* … */ })
export class AddressComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly http = inject(HttpClient);

  readonly form = this.fb.group({
    country: this.fb.control('', Validators.required),
    state: this.fb.control({ value: '', disabled: true }, Validators.required),
    city: this.fb.control({ value: '', disabled: true }, Validators.required),
  });

  // Options for each level — computed reactively from the upstream control
  readonly states = toSignal(
    this.form.controls.country.valueChanges.pipe(
      switchMap(country => this.loadStates(country)),
      takeUntilDestroyed(),
    ),
    { initialValue: [] as string[] },
  );

  readonly cities = toSignal(
    this.form.controls.state.valueChanges.pipe(
      switchMap(state => this.loadCities(this.form.controls.country.value, state)),
      takeUntilDestroyed(),
    ),
    { initialValue: [] as string[] },
  );

  constructor() {
    // When country changes: reset state and city, enable state once states load
    this.form.controls.country.valueChanges.pipe(
      takeUntilDestroyed(),
    ).subscribe(() => {
      this.form.controls.state.reset('');
      this.form.controls.city.reset('');
      this.form.controls.state.enable();
      this.form.controls.city.disable();
    });

    // When state changes: reset city, enable it
    this.form.controls.state.valueChanges.pipe(
      takeUntilDestroyed(),
    ).subscribe(state => {
      this.form.controls.city.reset('');
      if (state) {
        this.form.controls.city.enable();
      } else {
        this.form.controls.city.disable();
      }
    });
  }

  private loadStates(country: string): Observable<string[]> {
    if (!country) return of([]);
    return this.http.get<string[]>(`/api/states?country=${country}`);
  }

  private loadCities(country: string, state: string): Observable<string[]> {
    if (!country || !state) return of([]);
    return this.http.get<string[]>(`/api/cities?country=${country}&state=${state}`);
  }
}
```

```html
<form [formGroup]="form">
  <select formControlName="country">
    <option value="">Select country…</option>
    <option value="US">United States</option>
    <option value="VN">Vietnam</option>
    <option value="JP">Japan</option>
  </select>

  <select formControlName="state">
    <option value="">Select state…</option>
    @for (state of states(); track state) {
      <option [value]="state">{{ state }}</option>
    }
  </select>

  <select formControlName="city">
    <option value="">Select city…</option>
    @for (city of cities(); track city) {
      <option [value]="city">{{ city }}</option>
    }
  </select>
</form>
```

**Three patterns doing the work:**

- **`switchMap` on the upstream change** — when country changes, the previous state-loading HTTP call is cancelled. Same for state → city. Prevents the [stale-response race condition](../reactivity/race-conditions.md#race-2--out-of-order-responses-the-b-before-a-problem) where a slow request for the previous country's states arrives after the new country was already selected.
- **Reset + disable downstream on change** — when country changes, both state and city should reset (their values no longer apply) and city should disable (state hasn't loaded yet). Layered disables produce a clear "fill in order" UX.
- **`toSignal` for the options array** — `states()` and `cities()` are signals consumed in templates via `@for`. The HTTP cancellation lives inside the `valueChanges` pipeline; `toSignal` just bridges the result.

### The composability win

The reactive `switchMap` chain composes beautifully with the [request-deduplication](../http/request-deduplication.md) pattern. If two address components on the same page both load states for the same country, the dedup interceptor returns one shared response. With [retry-with-backoff](../http/retry-with-backoff.md) in place, transient failures don't break the cascade — the state dropdown shows a brief delay, then populates.

---

## Pattern 5 — dynamic validators (`updateValueAndValidity` gotcha)

A "Same as billing" checkbox in a checkout flow. When checked, the shipping address fields should be ignored (no validation, no required). When unchecked, they require the full set.

```typescript
@Component({ /* … */ })
export class CheckoutComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    billing: this.fb.group({
      street: this.fb.control('', Validators.required),
      city: this.fb.control('', Validators.required),
      zip: this.fb.control('', Validators.required),
    }),
    shippingIsSameAsBilling: this.fb.control(true),
    shipping: this.fb.group({
      street: this.fb.control(''),
      city: this.fb.control(''),
      zip: this.fb.control(''),
    }),
  });

  constructor() {
    this.form.controls.shippingIsSameAsBilling.valueChanges.pipe(
      takeUntilDestroyed(),
    ).subscribe(sameAsBilling => {
      const shipping = this.form.controls.shipping;
      const required = sameAsBilling ? [] : [Validators.required];

      shipping.controls.street.setValidators(required);
      shipping.controls.city.setValidators(required);
      shipping.controls.zip.setValidators(required);

      // THE LINE EVERYONE FORGETS:
      shipping.controls.street.updateValueAndValidity();
      shipping.controls.city.updateValueAndValidity();
      shipping.controls.zip.updateValueAndValidity();
    });
  }
}
```

**The `updateValueAndValidity()` gotcha** — `setValidators()` registers the new validators but doesn't run them. The control's `valid` / `invalid` state reflects the *old* validators until something triggers re-evaluation. `updateValueAndValidity()` is that trigger.

Without it, the form thinks the shipping fields are still required (or still optional) even after the toggle. The submit button stays disabled when it should enable, or vice versa.

### Two ways to remember to call it

**Approach A — wrap in a helper**:

```typescript
function setRequiredOn(control: AbstractControl, required: boolean): void {
  control.setValidators(required ? [Validators.required] : []);
  control.updateValueAndValidity();
}

// Usage:
setRequiredOn(this.form.controls.shipping.controls.street, !sameAsBilling);
```

Single point of failure. If the helper has the call, every use of the helper is correct.

**Approach B — drive shape from a signal + effect**:

```typescript
private readonly sameAsBilling = toSignal(
  this.form.controls.shippingIsSameAsBilling.valueChanges,
  { initialValue: true },
);

constructor() {
  effect(() => {
    const same = this.sameAsBilling();
    const required = same ? [] : [Validators.required];
    const shipping = this.form.controls.shipping;
    for (const control of [shipping.controls.street, shipping.controls.city, shipping.controls.zip]) {
      control.setValidators(required);
      control.updateValueAndValidity({ emitEvent: false });  // avoid feedback loop
    }
  });
}
```

The `{ emitEvent: false }` prevents `valueChanges` from firing when we update validity — which would otherwise re-trigger the effect, potentially loop.

Both approaches eliminate the "forgot the call" bug. Pick whichever fits the codebase's general style.

### When validators depend on other form values

A common case: confirm-password field must match password field. Both are siblings in the same group. The validator on `confirmPassword` needs to read `password`.

```typescript
function matchesField(otherFieldName: string): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    if (!control.parent) return null;
    const other = control.parent.get(otherFieldName);
    if (!other) return null;
    return control.value === other.value ? null : { mismatch: true };
  };
}

readonly form = this.fb.group({
  password: this.fb.control('', Validators.required),
  confirmPassword: this.fb.control('', [Validators.required, matchesField('password')]),
});

constructor() {
  // When password changes, re-run confirmPassword's validators
  this.form.controls.password.valueChanges.pipe(
    takeUntilDestroyed(),
  ).subscribe(() => {
    this.form.controls.confirmPassword.updateValueAndValidity();
  });
}
```

The same `updateValueAndValidity()` story: when the password changes, the confirm-password's validator's *result* changes, but the control's `errors` doesn't reflect that until you tell it to recheck.

---

## Trade-offs and common pitfalls

**Use these patterns when:**

- Form shape genuinely depends on user input (different fields per option, conditional sections, etc.)
- The form has structural variations that don't fit a single static shape
- You're hitting the "data lost on toggle" bug or the "validators run on hidden fields" bug

**Skip the dynamic patterns when:**

- The form is small and a single static shape with `[hidden]` and conditional validators is clearer
- Form shape is driven by config from the server (use a form-builder library like [Formly](https://formly.dev/) instead — it has dynamic forms baked in)
- You'd be better off with a wizard/multi-step flow (each step is its own static form; transitions handle the cross-step state)

### Common pitfalls

- **Forgetting `updateValueAndValidity()` after `setValidators`.** The most common dynamic-forms bug. Discussed at length above; wrap the call in a helper.
- **Using `[hidden]` instead of `@if`** — hidden controls still validate. The form remains "invalid" because hidden fields are required. Use `@if` to conditionally render OR disable the control so validators don't run.
- **`form.value` for submission when controls are disabled.** `form.value` strips disabled controls. If you intentionally disabled a field (e.g., a read-only computed total), `form.getRawValue()` is what you submit.
- **Calling `.reset()` when you mean `.patchValue({})`.** `reset` returns the form to its initial state (which includes initial values); if you set up the form with non-empty defaults, `.reset()` brings those back, not "empty."
- **Not tracking buffer state per option in Pattern 3.** If you only have one buffer for all payment methods, switching back to a method you visited earlier shows another method's data.
- **`@for` over `items.controls` without a stable `track`.** Index tracking is the default; reordering then re-renders every item visually. Use `track item` (control reference) or `track item.controls.id.value` (stable ID).
- **Cascading dropdown without `switchMap`.** Country changes; states are loading; user changes country again before states finished. Without `switchMap`, the first country's states arrive and populate after the new country was already selected. Always cancel the previous load.
- **Validators that depend on sibling fields without re-triggering the dependent.** When `password` changes, `confirmPassword`'s validator result changes — but the control doesn't know unless you call `updateValueAndValidity()` on it.
- **Mutating `FormArray` via JavaScript array methods.** `array.splice()` or `array.push()` (on `array.controls` directly) bypasses Angular's change detection. Use `formArray.push(control)`, `formArray.removeAt(i)`, `formArray.insert(i, control)`, `formArray.clear()`.
- **Typed forms breaking on dynamic shape.** TypeScript can't verify that a runtime-added control matches the static type. Either type the form to always include the dynamic field (and toggle `disabled`/validators), or accept the cast at the structural-change seam.

---

## See also

- [Reactive Forms](../../forms/reactive-forms.md) — typed forms, `FormBuilder`, control APIs
- [Validation](../../forms/validation.md) — synchronous/async validators, custom validator patterns
- [Race Conditions](../reactivity/race-conditions.md) — the `switchMap` story used in the cascading pattern
- [Search Engine](./search-engine.md) — `valueChanges` + RxJS composition patterns
- [Signals](../../reactivity/signals.md) — the storage primitive for buffer state and form-shape signals

## References

- [`FormArray` API (angular.dev)](https://angular.dev/api/forms/FormArray)
- [`AbstractControl.setValidators` (angular.dev)](https://angular.dev/api/forms/AbstractControl#setValidators)
- [`updateValueAndValidity` (angular.dev)](https://angular.dev/api/forms/AbstractControl#updateValueAndValidity) — the API everyone needs to remember
- [Reactive Forms guide (angular.dev)](https://angular.dev/guide/forms/reactive-forms) — the canonical reactive-forms primer
- [Formly](https://formly.dev/) — config-driven form builder for cases where forms come from server schemas
- [Angular CDK Drag and Drop](https://material.angular.io/cdk/drag-drop/overview) — for the visual side of reorderable FormArrays
- [Signal Forms RFC](https://github.com/angular/angular/discussions/53485) — the experimental signal-native forms API; a future-looking complement to reactive forms

## Demo source

Synthesized from common production form patterns rather than a single demo file. The five patterns (conditional sub-form with preserve-input, FormArray repeating items, type-discriminated form, cascading dropdowns, dynamic validators) cover ~90% of the cases that drive teams from static forms to dynamic ones. All code is original.
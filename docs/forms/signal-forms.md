---
roadmap_node: "signal-forms"
title: "Signal Forms"
file: "forms/signal-forms.md"
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

# Signal Forms

> **Lead with this:** Signal Forms replaces `FormGroup`/`FormControl` with a
> plain signal holding your form data and a `form()` field tree that gives
> every field reactive state signals — value, errors, touched, dirty — without
> subscribing to anything.

## What it is

Angular has historically had two forms approaches:

- **Template-driven forms** — `[(ngModel)]` bindings in the template,
  validation via attributes, state accessed through template reference variables
- **Reactive forms** — `FormGroup`/`FormControl` built in TypeScript,
  Observable-based `.valueChanges`, validators as functions

Both work, both have sharp edges, and both have one thing in common: they
predate signals entirely.

**Signal Forms** (`@angular/forms/signals`, stable since v22) is a new forms
system built on Angular's reactive primitive. A form model is a plain writable
`signal()` holding your data. The `form()` function wraps it in a **field
tree** — an object that mirrors your model's shape, where each leaf is a
callable that returns reactive state signals for that field. No Observables.
No subscriptions. Every piece of form state is a signal you read synchronously.

> **Reactive forms are not deprecated.** Signal Forms is a new system for new
> code. If you have an existing reactive forms codebase, there is a
> compatibility bridge (`@angular/forms/signals/compat`) to interoperate.
> Choose reactive forms for complex dynamic forms where you need to add/remove
> controls at runtime; choose Signal Forms for most new forms.

## How it works under the hood

### Old model — Reactive Forms (Observable-based)

Reactive forms represent form state as a tree of `AbstractControl` instances.
Each `FormControl` is an Observable — it emits on every value change via
`.valueChanges`. The whole system is push-based and async.

```typescript
// Reactive Forms — Observable-driven
readonly loginForm = new FormGroup({
  email: new FormControl('', [Validators.required, Validators.email]),
  password: new FormControl('', [Validators.required]),
});

// State reads require subscribing or snapshot calls
this.loginForm.get('email')?.value       // snapshot — not reactive in template
this.loginForm.get('email')?.valueChanges  // Observable — needs async pipe or subscribe

// Validation errors
this.loginForm.get('email')?.errors?.['required']

// Submitting
onSubmit() {
  if (this.loginForm.valid) {
    this.authService.login(this.loginForm.value);
  }
}
```

Problems: accessing field state in templates is verbose (`.get('email')?.errors?.['required']`). Validators are attached to controls, not described in a schema. Value reads inside templates need the `async` pipe or manual change detection. FormControl wraps state in an Observable even when synchronous reads would be simpler.

### New model — Signal Forms (synchronous, signal-based)

Signal Forms separates the model (a plain signal) from the field tree (a
structural wrapper that adds reactive state signals):

```
Plain signal (your data)
    ↓
form(modelSignal, schemaFn)
    ↓
Field tree — same shape as your model, where each leaf:
  • Is addressable by dot notation: loginForm.email
  • Is callable as a function: loginForm.email() → FieldState signals
  • FieldState.value()   — Signal<string> of the current value
  • FieldState.touched() — Signal<boolean>
  • FieldState.invalid() — Signal<boolean>
  • FieldState.errors()  — Signal<ValidationError[]>
```

When a user types in an input bound with `[formField]`, the `FormField`
directive writes the new value into the model signal. The signal change
propagates through the reactive graph: `computed()` signals that read the
model update, validation re-runs, field state signals emit their new values,
and the template re-renders — all synchronously within the same change
detection cycle.

## Basic usage

### Setup

Signal Forms live in their own import path:

```typescript
import { form, FormField, required, email, submit } from '@angular/forms/signals';
```

`FormField` is a directive that must be imported in each component that uses
signal forms bindings:

```typescript
@Component({
  standalone: true,
  imports: [FormField],
  template: `...`,
})
```

### A complete login form

```typescript
import { Component, signal } from '@angular/core';
import { form, FormField, required, email, submit } from '@angular/forms/signals';

interface LoginData {
  email: string;
  password: string;
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormField],
  template: `
    <form (submit)="onSubmit($event)">

      <label>
        Email
        <input type="email" [formField]="loginForm.email" />
      </label>

      @if (loginForm.email().touched() && loginForm.email().invalid()) {
        <ul class="errors">
          @for (error of loginForm.email().errors(); track error) {
            <li>{{ error.message }}</li>
          }
        </ul>
      }

      <label>
        Password
        <input type="password" [formField]="loginForm.password" />
      </label>

      @if (loginForm.password().touched() && loginForm.password().invalid()) {
        <ul class="errors">
          @for (error of loginForm.password().errors(); track error) {
            <li>{{ error.message }}</li>
          }
        </ul>
      }

      <button type="submit" [disabled]="loginForm().invalid()">
        Log In
      </button>

    </form>
  `,
})
export class LoginComponent {
  // Step 1: define your form data as a plain signal
  loginModel = signal<LoginData>({ email: '', password: '' });

  // Step 2: create the field tree with an optional validation schema
  loginForm = form(this.loginModel, (path) => {
    required(path.email,    { message: 'Email is required' });
    email(path.email,       { message: 'Enter a valid email' });
    required(path.password, { message: 'Password is required' });
  });

  // Step 3: submit using the submit() function
  onSubmit(event: Event): void {
    event.preventDefault();
    submit(this.loginForm, {
      action: async () => {
        const credentials = this.loginModel();   // read the plain data object
        await this.authService.login(credentials);
      },
    });
  }
}
```

Three steps. That's the full pattern.

### The model signal

The model is a plain writable `signal()`. You read it at submission with
`this.loginModel()` to get the current form data. You can also set it to
reset or programmatically populate the form:

```typescript
// Reset the form
this.loginModel.set({ email: '', password: '' });

// Pre-fill from a loaded user profile
this.loginModel.set({ email: user.email, password: '' });

// Update one field without touching others
this.loginModel.update(m => ({ ...m, email: 'new@example.com' }));
```

**Important:** the model must be a plain object. Class instances, `Map`, and
`Set` are not supported in the structural layer — Signal Forms walks the model
with `Object.keys()`. Translate class instances to plain objects at the form
boundary.

### The field tree

`form(modelSignal)` returns a field tree that mirrors your model's shape. Each
property is a `FieldTree<T>`:

```typescript
// loginForm.email is FieldTree<string>
// loginForm.password is FieldTree<string>

// For nested models:
const userModel = signal({
  name: '',
  address: { city: '', country: '' },
});
const userForm = form(userModel);

// userForm.address.city is FieldTree<string>
// TypeScript error: userForm.phone — property does not exist
```

### Field state signals

Calling a `FieldTree` as a function returns its `FieldState` — an object of
reactive signals:

```typescript
// All synchronous signal reads — no subscribe, no async pipe needed
loginForm.email().value()     // current value (Signal<string>)
loginForm.email().touched()   // user has interacted (Signal<boolean>)
loginForm.email().dirty()     // value differs from initial (Signal<boolean>)
loginForm.email().invalid()   // has active validation errors (Signal<boolean>)
loginForm.email().errors()    // array of ValidationError objects (Signal<ValidationError[]>)
```

### Form-level state

Calling the field tree itself (without a property) returns the overall form state:

```typescript
loginForm().invalid()   // true if ANY field is invalid (Signal<boolean>)
loginForm().touched()   // true if ANY field has been touched
loginForm().errors()    // all form-level errors
```

### Validation schema

The second argument to `form()` is a schema function that receives a path
object matching your model's shape. Call built-in validators on each path:

```typescript
loginForm = form(this.loginModel, (path) => {
  // path.email and path.password are the typed schema paths
  required(path.email,    { message: 'Email is required' });
  email(path.email,       { message: 'Must be a valid email' });
  required(path.password, { message: 'Password is required' });
});
```

**Built-in validators from `@angular/forms/signals`:**
- `required(path, options?)` — field must not be empty
- `email(path, options?)` — field must match email format
- `minLength(path, min, options?)` — string length ≥ min
- `maxLength(path, max, options?)` — string length ≤ max
- `pattern(path, regex, options?)` — string must match pattern
- `min(path, min, options?)` — number must be ≥ min
- `max(path, max, options?)` — number must be ≤ max

Signal Forms also supports **Standard Schema** — a community interface
implemented by Zod, Valibot, and other validation libraries — so you can
validate using your existing schema library.

### Both NgModule and standalone

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Reactive Forms (Angular 2–21) — still the right choice for existing apps
import { Component } from '@angular/core';
import { ReactiveFormsModule, FormGroup, FormControl, Validators } from '@angular/forms';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <input formControlName="email" />
      <span *ngIf="form.get('email')?.hasError('required')">Required</span>
      <button type="submit" [disabled]="form.invalid">Submit</button>
    </form>
  `,
})
export class ReactiveLoginComponent {
  form = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email]),
    password: new FormControl('', [Validators.required]),
  });
  onSubmit() { if (this.form.valid) { /* submit */ } }
}
```

```typescript
// Signal Forms (Angular 22+ — recommended for new forms)
import { Component, signal } from '@angular/core';
import { form, FormField, required, email, submit } from '@angular/forms/signals';

@Component({
  standalone: true,
  imports: [FormField],
  template: `
    <form (submit)="onSubmit($event)">
      <input type="email" [formField]="loginForm.email" />
      @if (loginForm.email().touched() && loginForm.email().invalid()) {
        <span>{{ loginForm.email().errors()[0].message }}</span>
      }
      <button type="submit" [disabled]="loginForm().invalid()">Submit</button>
    </form>
  `,
})
export class SignalLoginComponent {
  model = signal({ email: '', password: '' });
  loginForm = form(this.model, (path) => {
    required(path.email); email(path.email);
    required(path.password);
  });
  onSubmit(event: Event): void {
    event.preventDefault();
    submit(this.loginForm, { action: async () => { /* submit this.model() */ } });
  }
}
```

## Real-world patterns

### Pattern 1 — Nested form model

Signal Forms naturally handles nested models — no `FormGroup` inside `FormGroup`:

```typescript
interface AddressData {
  street: string;
  city: string;
  country: string;
}

interface CheckoutData {
  email: string;
  shippingAddress: AddressData;
  billingAddress: AddressData;
}

@Component({
  standalone: true,
  imports: [FormField],
  template: `
    <h2>Shipping</h2>
    <input [formField]="checkoutForm.shippingAddress.street" placeholder="Street" />
    <input [formField]="checkoutForm.shippingAddress.city" placeholder="City" />

    <h2>Billing</h2>
    <input [formField]="checkoutForm.billingAddress.street" placeholder="Street" />
    <input [formField]="checkoutForm.billingAddress.city" placeholder="City" />
  `,
})
export class CheckoutComponent {
  checkoutModel = signal<CheckoutData>({
    email: '',
    shippingAddress: { street: '', city: '', country: '' },
    billingAddress: { street: '', city: '', country: '' },
  });

  checkoutForm = form(this.checkoutModel, (path) => {
    required(path.email);
    required(path.shippingAddress.street);
    required(path.shippingAddress.city);
    // validators on nested paths work naturally
  });
}
```

### Pattern 2 — Reading form state in computed signals

Because field state is signals, you can derive from them with `computed()`:

```typescript
@Component({ /* ... */ })
export class RegistrationComponent {
  model = signal({ password: '', confirmPassword: '' });
  registerForm = form(this.model);

  // Derive from field state signals — no subscription needed
  passwordStrength = computed(() => {
    const pw = this.registerForm.password().value();
    if (pw.length < 8) return 'weak';
    if (/[A-Z]/.test(pw) && /[0-9]/.test(pw)) return 'strong';
    return 'medium';
  });

  passwordsMatch = computed(() =>
    this.registerForm.password().value() ===
    this.registerForm.confirmPassword().value()
  );
}
```

## Common mistakes

### Mistake 1 — Using a class instance as the form model

Signal Forms walks the model with `Object.keys()`. Class instances lose their
prototype methods on the first write (Signal Forms shallow-copies objects on
update):

```typescript
class LoginData {
  email = '';
  password = '';
  getFullData() { return { email: this.email, password: this.password }; }
}

// ❌ class instance — methods lost after first write
loginModel = signal(new LoginData());

// ✅ plain object — always supported
loginModel = signal({ email: '', password: '' });
```

### Mistake 2 — Reading field state before the field exists in the model

If a field is initialized to `undefined`, Signal Forms excludes it from the
field tree. Accessing it at runtime returns `undefined` rather than a
`FieldState`:

```typescript
// ❌ phoneNumber is undefined — excluded from the field tree
model = signal({ email: '', phoneNumber: undefined });
// loginForm.phoneNumber → undefined (no FieldState)

// ✅ null marks the field as optional but present in the tree
model = signal({ email: '', phoneNumber: null as string | null });
// loginForm.phoneNumber → FieldTree<string | null>
```

### Mistake 3 — Calling the field state once and storing it

`FieldState` signals must be read inside a reactive context to track updates.
Storing the result of a single `loginForm.email()` call breaks reactivity:

```typescript
// ❌ Reads FieldState once on construction — won't update
export class MyComponent {
  emailState = this.loginForm.email();   // stale snapshot — not reactive
}

// ✅ Read inside the template or computed() — tracked by Angular's reactive graph
// Template: {{ loginForm.email().value() }}  → reactive, updates on change
// Or: emailValue = computed(() => this.loginForm.email().value());
```

### Mistake 4 — Forgetting to import FormField

`FormField` is a standalone directive that must be in `imports`. Without it,
`[formField]` is silently ignored — inputs don't bind and no errors are thrown:

```typescript
// ❌ Missing FormField — [formField] binding silently does nothing
@Component({
  standalone: true,
  imports: [],   // FormField missing
  template: `<input [formField]="loginForm.email" />`,
})

// ✅ FormField imported — binding works
@Component({
  standalone: true,
  imports: [FormField],
  template: `<input [formField]="loginForm.email" />`,
})
```

## How this evolved

> - **Angular 2–20 (2016–2025):** Template-driven forms and Reactive Forms
>   were the only two approaches. Both relied on Zone.js for CD triggering
>   and Observables for state streams. The community tried many signal-adjacent
>   patterns (ngxs-forms, formly) but no official signal-based system existed.
>
> - **Angular 21 (November 2025):** Signal Forms introduced in **experimental
>   preview** as `@angular/forms/signals`. Initial API included `form()`,
>   `FormField`, `required`, `email`, and basic field state signals. Not
>   production-ready — API still being refined.
>
> - **Angular 22 (June 2026):** Signal Forms graduated to **stable**. Full
>   validator set, Standard Schema integration (Zod, Valibot), `submit()`
>   function, `SignalFormControl` compatibility bridge, and the compat layer
>   (`@angular/forms/signals/compat`) for interoperating with existing reactive
>   forms codebases. Officially recommended for new Angular forms.

## See also

- [Reactive Forms](./reactive-forms.md) — still the right choice for complex
  dynamic forms and existing codebases
- [Validation](./validation.md) — the reactive forms validation model, useful
  context for how Signal Forms improves on it
- [Signals](../reactivity/signals.md) — the foundational primitive Signal Forms
  builds on
- [Signal Inputs](../reactivity/signal-inputs.md) — `model()` for component
  two-way binding, distinct from Signal Forms models
- [Official docs — Signal Forms overview](https://angular.dev/guide/forms/signals/overview)
- [Official docs — Form models](https://angular.dev/guide/forms/signals/models)
- [Official docs — Validation](https://angular.dev/guide/forms/signals/validation)
- [Official docs — Comparison with other form systems](https://angular.dev/guide/forms/signals/comparison)

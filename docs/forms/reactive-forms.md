---
roadmap_node: "reactive-forms"
title: "Angular Reactive Forms"
file: "forms/reactive-forms.md"
source_days: [35, 36]
original_authors: ["Tiep Phan", "Trung Vo"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Reactive Forms

> **⚡ What changed since the original**
>
> This article was first written for Angular 9 (2020). The **runtime model** of Reactive Forms — `FormGroup` / `FormControl` / `FormArray`, sync and async validators, `valueChanges` and `statusChanges` observables, immutable state on each change — is unchanged in v22. What changed is **how you declare forms and how TypeScript reads them**:
>
> - **Strictly typed forms (v14+).** `FormGroup<TControls>`, `FormControl<T>`, and `FormArray<TControl>` are now generic. `form.value` and `form.controls.username` are precisely typed instead of `any`. The old untyped types are still available as `UntypedFormGroup` / `UntypedFormControl` / `UntypedFormArray` for migration.
> - **`nonNullable: true`** on `FormControl` (and `NonNullableFormBuilder`) drops `| null` from the value type and makes `reset()` go back to the initial value instead of `null`.
> - **`new FormControl(value, options)`** with an options object is the v22-idiomatic constructor. The three-tuple `[value, validators, asyncValidators]` shorthand still works inside `FormBuilder.group()`.
> - **`Validators.compose([...])` is no longer needed.** The `validators` field accepts a plain array directly.
> - **`ReactiveFormsModule` is imported into the standalone component**, not into an `AppModule`.
> - **`constructor(private fb: FormBuilder)` → `private fb = inject(NonNullableFormBuilder)`** at the class field.
> - **`*ngIf` / `*ngFor` → `@if` / `@for`** in templates; `toSignal(form.valueChanges, { initialValue: form.value })` is the v22 idiom for reading form state into signal-based templates.
> - **Signal Forms** is a new experimental API in Angular 22 covered separately in [Signal Forms](../forms/signal-forms.md). Reactive Forms remain fully supported and are still the recommended choice for complex form logic at the time of writing.
>
> Each Angular 9 code block below is preserved with its `<!-- legacy -->` marker and followed by a v22 equivalent. The mechanism reflection at the end focuses on **typed forms** — how the type system actually maps controls to values, why `nonNullable` exists, and what changed between `FormGroup` and `FormGroup<TControls>` mechanically.
>
> **See also**: [Template-Driven Forms](../forms/template-driven-forms.md) · [Form Validation](../forms/validation.md) · [Control Value Accessor](../forms/control-value-accessor.md) · [Signal Forms](../forms/signal-forms.md) · [Signal Inputs](../reactivity/signal-inputs.md) · [toSignal](../reactivity/to-signal.md)

---

In [template-driven forms](template-driven-forms.md) we built forms with directives in the template. Angular also offers **Reactive Forms** (Model-driven Forms) — a powerful alternative.

How do they differ? Can they handle complex forms? Let's find out.

## Reactive Forms

Reactive (Model-driven) forms build the form model in the component class instead of leaning on `ngModel`, `required`, and similar template directives.

**Note:** template-driven forms update asynchronously; reactive forms are synchronous.

You create the full control tree in code (constructor, field initializer, or `ngOnInit`), so you can read form state immediately.

Form state is **immutable** — each change produces a new state object.

Reactive forms expose `Observable` streams such as `valueChanges` and `statusChanges` that you can combine like any other RxJS stream.

Validators are plain functions you can swap at runtime.

From [Angular reactive forms overview](https://angular.dev/guide/forms/reactive-forms):

> Reactive forms use an explicit and immutable approach to managing the state of a form at a given point in time. Each change to the form state returns a new state, which maintains the integrity of the model between changes. Reactive forms are built around observable streams, where form inputs and values are provided as streams of input values, which can be accessed synchronously.
>
> Reactive forms also provide a straightforward path to testing because you are assured that your data is consistent and predictable when requested. Any consumers of the streams have access to manipulate that data safely.
>
> Reactive forms differ from template-driven forms in distinct ways. Reactive forms provide more predictability with synchronous access to the data model, immutability with observable operators, and change tracking through observable streams.

## Sign in reactive form component

We'll recreate the familiar **Sign in** form reactively.

![Forms](assets/sign-form-template.jpg) <!-- TODO: asset -->
[From victorthemes](https://victorthemes.com/freebies/sign-form-template/)

Generate the component:

```sh
ng g c sign-in-rf
```

In v22, `ng g c` produces standalone components by default — no `--standalone` flag needed.

```ts
// app.routes.ts (v22 — see Routing article)
const routes: Routes = [
  {
    path: 'sign-in',
    component: SignInComponent,
  },
  {
    path: 'sign-in-rf',
    component: SignInRfComponent,
  },
];
```

Template (same structure as before):

```html
<div class="container">
  <form class="sign-in-form">
    <h2>Sign in</h2>
    <div class="row-control">
      <mat-form-field appearance="outline">
        <mat-label>Username</mat-label>
        <input matInput placeholder="Username" />
      </mat-form-field>
    </div>
    <div class="row-control">
      <mat-form-field appearance="outline">
        <mat-label>Password</mat-label>
        <input type="password" matInput placeholder="Password" />
      </mat-form-field>
    </div>
    <div class="row-control">
      <mat-checkbox>Remember me</mat-checkbox>
    </div>
    <div class="row-control row-actions">
      <button mat-raised-button color="primary" type="submit">Sign in</button>
    </div>
  </form>
</div>
```

Visit http://localhost:4200/sign-in-rf after `ng serve`.

![day35-sign-in-form](assets/day35-sign-in-form.png) <!-- TODO: asset -->

## Integrate Angular Forms

In Angular 9 you imported `ReactiveFormsModule` into the `NgModule` that declared the component:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// Angular 9: AppModule
import { ReactiveFormsModule } from '@angular/forms';

@NgModule({
  declarations: [
    // components, pipes, directives
  ],
  imports: [
    // other imports
    ReactiveFormsModule,
  ],
  // ...
})
export class AppModule {}
```

In v22, the standalone component imports `ReactiveFormsModule` directly. Material modules are imported the same way:

```ts
// ── v22 equivalent: imports on the component itself ───────────────────────
import { Component } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-sign-in-rf',
  templateUrl: './sign-in-rf.component.html',
  styleUrl: './sign-in-rf.component.scss',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
  ],
})
export class SignInRfComponent {}
```

Each component declares exactly what it needs. No app-wide `ReactiveFormsModule` import that quietly pulls forms machinery into every bundle whether the component uses it or not.

## `FormGroup`, `FormControl`, `FormArray`

- `AbstractControl` — base class for the three types below
- `FormControl<T>` — tracks value and validation for a single input
- `FormGroup<TControls>` — object-shaped group of controls
- `FormArray<TControl>` — array-shaped group for dynamic lists

A form usually starts with a **FormGroup** that registers child **AbstractControl** instances.

For Sign in:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// Angular 9: untyped FormGroup, value is any
export class SignInRfComponent implements OnInit {
  signInForm = new FormGroup({
    username: new FormControl(''), // default value
    password: new FormControl(''),
    rememberMe: new FormControl(false),
  });
  constructor() {}

  ngOnInit(): void {}
}
```

```ts
// ── v22 equivalent: typed FormGroup with nonNullable controls ─────────────
import { Component } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-sign-in-rf',
  templateUrl: './sign-in-rf.component.html',
  styleUrl: './sign-in-rf.component.scss',
  imports: [ReactiveFormsModule /* + Material modules */],
})
export class SignInRfComponent {
  // Types flow automatically: signInForm.controls.username is FormControl<string>,
  // signInForm.value is { username?: string; password?: string; rememberMe?: boolean }.
  readonly signInForm = new FormGroup({
    username: new FormControl('', { nonNullable: true }),
    password: new FormControl('', { nonNullable: true }),
    rememberMe: new FormControl(false, { nonNullable: true }),
  });
}
```

A few things changed:

- **`new FormControl('', { nonNullable: true })`** — the second argument is now an options object. `nonNullable: true` does two things: it makes the value type `string` (not `string | null`), and it makes `reset()` restore the initial value (not `null`).
- **No `implements OnInit`, no `constructor`, no `ngOnInit`.** Class field initializers run during construction; if the form has no async dependencies, it can be declared inline.
- **`readonly` on the form field.** The form *instance* never reassigns — only its internal state changes. Marking it `readonly` prevents accidental reassignment and signals intent.

## Binding the form

Bind the group and controls (this template is unchanged in v22):

```html
<form class="sign-in-form" [formGroup]="signInForm">
  <h2>Sign in</h2>
  <div class="row-control">
    <mat-form-field appearance="outline">
      <mat-label>Username</mat-label>
      <input matInput placeholder="Username" formControlName="username" />
    </mat-form-field>
  </div>
  <div class="row-control">
    <mat-form-field appearance="outline">
      <mat-label>Password</mat-label>
      <input
        type="password"
        matInput
        placeholder="Password"
        formControlName="password"
      />
    </mat-form-field>
  </div>
  <div class="row-control">
    <mat-checkbox formControlName="rememberMe">Remember me</mat-checkbox>
  </div>
  <div class="row-control row-actions">
    <button mat-raised-button color="primary" type="submit">Sign in</button>
  </div>
  <pre>{{ signInForm.value | json }}</pre>
</form>
```

![day35-sign-in-form Reactive Forms](assets/day35-sign-in-form-01.gif) <!-- TODO: asset -->

## `FormBuilder` service

Large forms get verbose with `new FormControl(...)`. Use `FormBuilder` — or in v22, **`NonNullableFormBuilder`** for typed nullable-free controls without writing `{ nonNullable: true }` on every line.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// Angular 9: FormBuilder, untyped
export class SignInRfComponent implements OnInit {
  signInForm: FormGroup;
  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.signInForm = this.fb.group({
      username: '',
      password: '',
      rememberMe: false,
    });
  }
}
```

```ts
// ── v22 equivalent: NonNullableFormBuilder + inject() ─────────────────────
import { Component, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-sign-in-rf',
  templateUrl: './sign-in-rf.component.html',
  imports: [ReactiveFormsModule /* + Material */],
})
export class SignInRfComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  // Types are inferred: signInForm is FormGroup<{
  //   username: FormControl<string>,
  //   password: FormControl<string>,
  //   rememberMe: FormControl<boolean>,
  // }>
  readonly signInForm = this.fb.group({
    username: '',
    password: '',
    rememberMe: false,
  });
}
```

`NonNullableFormBuilder` is `FormBuilder` with every control defaulting to `{ nonNullable: true }`. If you want some nullable controls and some non-nullable, inject the regular `FormBuilder` and pass options per-control:

```ts
private readonly fb = inject(FormBuilder);

readonly profileForm = this.fb.group({
  // Non-nullable: required field, value is always string
  username: this.fb.nonNullable.control(''),
  // Nullable: optional field, value is string | null
  bio: this.fb.control<string | null>(null),
});
```

## Updating values with `patchValue` and `setValue`

`AbstractControl` provides `setValue` and `patchValue`:

- On `FormControl`, `patchValue` delegates to `setValue`.
- On `FormGroup` / `FormArray`, `patchValue` updates only the keys you pass; `setValue` requires an exact shape match.

Use `patchValue` for partial updates; use `setValue` when you want strict structure enforcement.

`reset()` restores initial state — and with `nonNullable: true` controls, that means the original default value, not `null`.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
ngOnInit(): void {
  this.signInForm = this.fb.group({
    username: '',
    password: '',
    rememberMe: false,
  });
  setTimeout(() => {
    // fake api call then update form value
    this.signInForm.patchValue({
      username: 'TiepPhan'
    });
  }, 1000);
}
```

```ts
// ── v22 equivalent: same API, but patchValue is now type-checked ──────────
constructor() {
  setTimeout(() => {
    // TypeScript verifies these key/value pairs match the form shape:
    this.signInForm.patchValue({
      username: 'TiepPhan',
      // password: 123, // ← compile error: number not assignable to string
      // emailAddress: 'x', // ← compile error: key not in form shape
    });
  }, 1000);
}
```

With typed forms, `patchValue` and `setValue` catch shape mismatches at compile time. This was one of the most common runtime bugs in the untyped era — `patchValue({ usrname: 'x' })` (typo) used to silently do nothing.

## `submit` vs `ngSubmit`

Reactive forms support `(ngSubmit)` the same way template-driven forms do:

```html
<form
  class="sign-in-form"
  [formGroup]="signInForm"
  autocomplete="off"
  (ngSubmit)="onSubmit()"
></form>
```

```ts
// v22 — same shape, but signInForm.value is now precisely typed
onSubmit(): void {
  console.log(this.signInForm.value);
  // Type: Partial<{ username: string; password: string; rememberMe: boolean }>
  //
  // If you've validated and know all fields are filled, use getRawValue() for
  // the non-partial shape:
  const credentials = this.signInForm.getRawValue();
  // Type: { username: string; password: string; rememberMe: boolean }
}
```

Why `Partial<...>` on `.value`? Because a `FormGroup` can have disabled controls, and disabled controls don't appear in `.value`. `.getRawValue()` includes disabled controls and returns the full shape. This is one of the small but important distinctions typed forms make explicit.

## Validation requirements

Same rules as [template-driven validation](template-driven-forms.md):

- **Username:** required, 6–32 characters, letters only
- **Password:** required, 6–32 characters, letters, digits, and at least one of `!@#$%^&*`

With reactive forms, validators live in the component setup — not as template attributes.

### Validator functions

**1. Sync validators** — receive a control, return errors or `null` immediately.

```ts
let control = new FormControl('', Validators.required);
// Or
this.fb.control('', Validators.required);
```

**2. Async validators** — return `Promise` or `Observable` (e.g. username uniqueness check). Passed as the **third** constructor argument, or via the options object's `asyncValidators` field in v22:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// Angular 9: third positional argument
isUserNameDuplicated(control: AbstractControl): Observable<ValidationErrors> {
    return of(null);
}

let control = new FormControl("", Validators.required, this.isUserNameDuplicated);
this.fb.control("", Validators.required, this.isUserNameDuplicated);
```

```ts
// ── v22 equivalent: options object form, explicit asyncValidators ─────────
const control = new FormControl('', {
  nonNullable: true,
  validators: [Validators.required],
  asyncValidators: [isUserNameDuplicated],
  updateOn: 'blur', // bonus: only re-validate on blur, not every keystroke
});
```

The options-object form makes intent explicit. The positional-argument form still works in v22, but you have to remember the order (value, sync, async), and `updateOn` isn't expressible without the options form.

> For performance reasons, Angular only runs async validators if all sync validators pass. Each must complete before errors are set. (Unchanged in v22.)

### Built-in `Validators`

```ts
class Validators {
  static min(min: number): ValidatorFn;
  static max(max: number): ValidatorFn;
  static required(control: AbstractControl): ValidationErrors | null;
  static requiredTrue(control: AbstractControl): ValidationErrors | null;
  static email(control: AbstractControl): ValidationErrors | null;
  static minLength(minLength: number): ValidatorFn;
  static maxLength(maxLength: number): ValidatorFn;
  static pattern(pattern: string | RegExp): ValidatorFn;
  static nullValidator(control: AbstractControl): ValidationErrors | null;
  static compose(validators: ValidatorFn[]): ValidatorFn | null;
  static composeAsync(validators: AsyncValidatorFn[]): AsyncValidatorFn | null;
}
```

`compose` and `composeAsync` still exist for backward compatibility, but you don't need them in v22 — the `validators` field accepts a plain array directly.

Form setup with validators:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
// Angular 9: Validators.compose([...])
this.signInForm = this.fb.group({
  username: [
    '',
    Validators.compose([
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^[a-z]{6,32}$/i),
    ]),
  ],
  password: [
    '',
    Validators.compose([
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^(?=.*[!@#$%^&*]+)[a-z0-9!@#$%^&*]{6,32}$/),
    ]),
  ],
  rememberMe: false,
});
```

```ts
// ── v22 equivalent: plain array, no compose() wrapper ─────────────────────
readonly signInForm = this.fb.group({
  username: [
    '',
    [
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^[a-z]{6,32}$/i),
    ],
  ],
  password: [
    '',
    [
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^(?=.*[!@#$%^&*]+)[a-z0-9!@#$%^&*]{6,32}$/),
    ],
  ],
  rememberMe: [false],
});
```

With `FormBuilder`, each control is still a tuple: `[defaultValue, syncValidators, asyncValidators]`. With the new options object on `FormControl` directly:

```ts
// Equivalent v22 form with the options-object style:
readonly signInForm = new FormGroup({
  username: new FormControl('', {
    nonNullable: true,
    validators: [
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^[a-z]{6,32}$/i),
    ],
  }),
  password: new FormControl('', {
    nonNullable: true,
    validators: [
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^(?=.*[!@#$%^&*]+)[a-z0-9!@#$%^&*]{6,32}$/),
    ],
  }),
  rememberMe: new FormControl(false, { nonNullable: true }),
});
```

Both styles produce the same form. `FormBuilder.group` is more concise; the explicit `new FormControl` form is more discoverable for someone reading the type signature.

![Reactive Forms 2](assets/day36-01.gif) <!-- TODO: asset -->

Disable submit until the form is valid:

```html
<!-- v22: works in both styles, but with built-in control flow you can do more -->
<button mat-raised-button color="primary" type="submit" [disabled]="signInForm.invalid">
  Sign in
</button>

@if (signInForm.controls.username.invalid && signInForm.controls.username.touched) {
  <mat-error>
    @if (signInForm.controls.username.errors?.['required']) {
      Username is required.
    } @else if (signInForm.controls.username.errors?.['minlength']) {
      Username must be at least 6 characters.
    } @else if (signInForm.controls.username.errors?.['pattern']) {
      Username must contain only letters.
    }
  </mat-error>
}
```

`signInForm.controls.username` is now `FormControl<string>` — fully typed, no `as FormControl` cast, no non-null assertion. Compare to the Angular 9 era where you'd have to write `signInForm.get('username') as FormControl` or live with `AbstractControl | null`.

### Your first custom validator

`Validators.required` passes for whitespace-only input. Six spaces satisfy `required` and `minLength(6)` but aren't meaningful usernames.

Remove `Validators.pattern` temporarily to see the issue:

![Reactive Forms 2](assets/day36-02.gif) <!-- TODO: asset -->

`NoWhitespaceValidator`:

```ts
import { AbstractControl, ValidatorFn, ValidationErrors } from '@angular/forms';

export function noWhitespaceValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    let controlVal = control.value;
    if (typeof controlVal === 'number') {
      controlVal = `${controlVal}`;
    }
    const isWhitespace = (controlVal || '').trim().length === 0;
    return isWhitespace ? { whitespace: 'value is only whitespace' } : null;
  };
}
```

Tiny v22 polish: the function name is `noWhitespaceValidator` (lowerCamelCase) per the Angular style guide convention for validator factory functions. The original `NoWhitespaceValidator` (PascalCase) was treating the factory as a class-like construct; lowerCamelCase signals it's a function that *returns* a validator.

Replace `Validators.required` with `noWhitespaceValidator()`:

```ts
readonly signInForm = this.fb.group({
  username: [
    '',
    [
      noWhitespaceValidator(),
      Validators.minLength(6),
    ],
  ],
});
```

![Reactive Forms 2](assets/day36-03.gif) <!-- TODO: asset -->

Used in the [Angular Jira Clone](https://github.com/trungk18/jira-clone-angular/blob/master/frontend/src/app/core/validators/no-whitespace.validator.ts) project.

### Reading form state into a signal (v22 idiom)

In v22, when your template reads form state, the cleanest pattern is to bridge `valueChanges` to a signal via `toSignal`. This lets the rest of your component treat form value as just another signal:

```ts
import { toSignal } from '@angular/core/rxjs-interop';

export class SignInRfComponent {
  private readonly fb = inject(NonNullableFormBuilder);

  readonly signInForm = this.fb.group({
    username: '',
    password: '',
    rememberMe: false,
  });

  // Bridge the form value to a signal. The form still uses Observables
  // internally — this is just a convenience for signal-based reads.
  readonly formValue = toSignal(this.signInForm.valueChanges, {
    initialValue: this.signInForm.getRawValue(),
  });

  // Derived state: a computed signal that reads from formValue.
  readonly hasCredentials = computed(() => {
    const v = this.formValue();
    return !!v.username && !!v.password;
  });
}
```

For long-lived subscriptions in event handlers (e.g., reacting to value changes with side effects), use `takeUntilDestroyed()`:

```ts
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

constructor() {
  this.signInForm.valueChanges.pipe(
    takeUntilDestroyed(),
  ).subscribe(value => {
    // side effect — e.g., log analytics, autosave draft
  });
}
```

`takeUntilDestroyed()` works because the constructor runs inside an injection context, so it can resolve `DestroyRef` automatically. No `ngOnDestroy`, no manual `Subject` teardown.

---

## Mechanism reflection — how typed forms actually work

The headline v22 change for reactive forms is **typed forms** — the v14 release that made `FormGroup`, `FormControl`, and `FormArray` generic. The runtime is otherwise unchanged: `AbstractControl` is the same base class, validators are the same plain functions, `valueChanges` is the same `Observable`. The change is entirely at the TypeScript layer, but it shapes how you write every form in modern Angular.

### The Angular 9 model — `any` all the way down

In Angular 9, `FormControl`, `FormGroup`, and `FormArray` were not generic. The type signatures looked roughly like this:

```ts
class FormControl extends AbstractControl {
  value: any;
  // ...
}

class FormGroup extends AbstractControl {
  controls: { [key: string]: AbstractControl };
  value: any;
  // ...
}
```

Notice `value: any` everywhere. The `controls` dictionary mapped strings to `AbstractControl` — the base class. So:

- `form.value` was `any`
- `form.controls.username` was `AbstractControl` (and the `.username` access was unchecked, because the dictionary was string-indexed)
- `form.get('username')` returned `AbstractControl | null`, requiring `?.` or `!` on every read
- `patchValue({ usrname: 'x' })` (typo) silently did nothing — no compile error

This was a constant source of runtime bugs. The Angular team's analysis showed that even disciplined teams with strict TypeScript settings accumulated `as FormControl` casts and `!` non-null assertions across their forms code.

### What changed in v14 — `FormGroup<TControls>` and mapped types

In v14, the form types became generic. The simplified signatures are now:

```ts
class FormControl<TValue = any> extends AbstractControl<TValue> {
  value: TValue;
  // ...
}

type FormGroupControls = { [K: string]: AbstractControl<any> };

class FormGroup<TControls extends FormGroupControls> extends AbstractControl {
  controls: TControls;
  value: Partial<{ [K in keyof TControls]: TControls[K]['value'] }>;
  // ...
}
```

The mapped type `Partial<{ [K in keyof TControls]: TControls[K]['value'] }>` is doing the heavy lifting. It says:

> "For each key in `TControls`, look at the control type at that key, extract its `value` type, and that's the type of the corresponding field on the form's value. Wrap it all in `Partial` because controls can be disabled."

Concretely, if you write:

```ts
const form = new FormGroup({
  username: new FormControl('', { nonNullable: true }),
  age: new FormControl<number | null>(null),
});
```

TypeScript infers:

```ts
form.controls.username  // FormControl<string>
form.controls.age       // FormControl<number | null>
form.value              // { username?: string; age?: number | null }
form.getRawValue()      // { username: string; age: number | null }
```

`patchValue({ usrname: 'x' })` is now a compile error. `form.controls.username.setValue('x')` works without a cast. `form.value.username` is `string | undefined`, not `any`.

### Why `nonNullable: true` exists

The default `FormControl('')` has value type `string | null` — not just `string`. Why? Because calling `control.reset()` on a `FormControl<string>` sets the value to `null` by default, not back to the initial value. That's been the runtime behavior since Angular 2, and the type system has to reflect it honestly.

`nonNullable: true` changes both:

- The value type becomes `string` (drops `| null`)
- `reset()` restores the **initial value** (the first argument passed to the constructor), not `null`

So `new FormControl('', { nonNullable: true })` is "this is a `string` form control whose default and reset value are both `''`". For most form fields — where you genuinely want a string, not a string-or-null — this is what you want. Hence `NonNullableFormBuilder`, which makes `nonNullable: true` the default on everything it builds.

The implication is subtle but important: **the option doesn't just change types, it changes runtime behavior**. A `reset()` on a non-nullable control behaves differently from `reset()` on a nullable one. The two used to be indistinguishable; now they're not.

### The migration story — `UntypedFormGroup` and friends

If you ran the v14 `ng update` migration on an Angular 13 codebase, it wrapped every `FormGroup`, `FormControl`, and `FormArray` in their `Untyped*` equivalents:

```ts
// Before migration (Angular 13)
new FormGroup({ username: new FormControl('') });

// After v14 migration — preserves the old untyped behavior
new UntypedFormGroup({ username: new UntypedFormControl('') });
```

`UntypedFormGroup` etc. are aliases for the generic types with `any` as the type parameter — i.e., they behave exactly like the pre-v14 untyped versions. This let codebases adopt v14 without rewriting every form.

The intended path forward is to migrate forms file by file from `Untyped*` to the typed versions, adding `nonNullable: true` and explicit value types where appropriate. There's no automated migration for that part — it's editorial work.

### What's the same — the runtime is unchanged

It's worth restating: the form **runtime** is identical to Angular 9. Same `AbstractControl` base, same validator function signature `(c: AbstractControl) => ValidationErrors | null`, same `valueChanges` and `statusChanges` observables, same change detection integration (still works with `OnPush` the same way), same lifecycle. If you have a custom validator, custom `ControlValueAccessor`, or custom directive that worked in Angular 9, it still works in v22 with no changes — typed forms is a pure TypeScript-layer addition.

This is why you can take a v22 typed form and pass `form.value` to a v9-era service that expects `any` — at runtime, it's the same object.

### Looking forward — Signal Forms in v22

Angular 22 introduces an experimental **Signal Forms** API as an alternative to Reactive Forms. The headline difference is that Signal Forms are built around signals natively rather than observables — `value()` is a signal, not an `Observable`, and the entire form tree integrates with the rest of the signal system. Reactive Forms remain fully supported and are the recommended choice for production code at the time of writing. See [Signal Forms](../forms/signal-forms.md) for the experimental API.

---

## Summary

You now know reactive form fundamentals in v22:

- `FormGroup<TControls>` / `FormControl<T>` / `FormArray<TControl>` are generic and strictly typed
- `nonNullable: true` drops `| null` from the value type and changes reset behavior
- `NonNullableFormBuilder` is the v22-recommended builder for typed default-non-null forms
- `inject(NonNullableFormBuilder)` replaces `constructor(private fb: FormBuilder)`
- `ReactiveFormsModule` is imported into the standalone component, not into an `AppModule`
- `Validators.compose([...])` is unnecessary — pass arrays directly
- `toSignal(form.valueChanges, { initialValue: form.getRawValue() })` bridges form state to signals
- `takeUntilDestroyed()` replaces manual `Subject` teardown for `valueChanges` subscriptions

For async validators and cross-field checks, see [form validation](validation.md).

## See also

- [Template-Driven Forms](../forms/template-driven-forms.md) — the directive-driven alternative
- [Form Validation](../forms/validation.md) — async validators, cross-field, dynamic
- [Control Value Accessor](../forms/control-value-accessor.md) — custom form controls
- [Signal Forms](../forms/signal-forms.md) — the experimental v22 successor
- [toSignal](../reactivity/to-signal.md) — bridging Observables to signals
- [Signal Inputs](../reactivity/signal-inputs.md) — `input()`, `output()`, `model()`

## Code sample

- https://github.com/tieppt/100-doc-angular/tree/day35
- https://stackblitz.com/edit/100-days-of-angular-day-35
- https://stackblitz.com/edit/100-days-of-angular-day-36

## Youtube Video

[![Day 35](https://img.youtube.com/vi/oTwukyGa_qY/0.jpg)](https://youtu.be/oTwukyGa_qY) <!-- TODO: asset -->
[![Day 36](https://img.youtube.com/vi/ozHU4MmRS1w/0.jpg)](https://youtu.be/ozHU4MmRS1w) <!-- TODO: asset -->

## References

- [Forms overview (angular.dev)](https://angular.dev/guide/forms)
- [Reactive Forms (angular.dev)](https://angular.dev/guide/forms/reactive-forms)
- [Typed Forms (angular.dev)](https://angular.dev/guide/forms/typed-forms)
- [Validators API (angular.dev)](https://angular.dev/api/forms/Validators)
- [Experimenting with Angular reactive forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-reactive-forms-trong-angular/)
- [Experimenting with Angular template-driven forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-template-driven-forms-trong-angular/)

## Author

Tiep Phan — https://github.com/tieppt · Trung Vo — https://github.com/trungk18

*Translated from the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) series by Angular Vietnam. MIT licensed.*

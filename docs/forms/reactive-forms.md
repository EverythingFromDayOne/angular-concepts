---
roadmap_node: "reactive-forms"
title: "Angular Reactive Forms"
file: "forms/reactive-forms.md"
source_days: [35, 36]
original_authors: ["Tiep Phan", "Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Reactive Forms

In [template-driven forms](template-driven-forms.md) we built forms with directives in the template. Angular also offers **Reactive Forms** (Model-driven Forms) — a powerful alternative.

How do they differ? Can they handle complex forms? Let's find out.

## Reactive Forms

Reactive (Model-driven) forms build the form model in the component class instead of leaning on `ngModel`, `required`, and similar template directives.

**Note:** template-driven forms update asynchronously; reactive forms are synchronous.

You create the full control tree in code (constructor, field initializer, or `ngOnInit`), so you can read form state immediately.

Form state is **immutable** — each change produces a new state object.

Reactive forms expose `Observable` streams such as `valueChanges` and `statusChanges` that you can combine like any other RxJS stream.

Validators are plain functions you can swap at runtime.

From [Angular reactive forms overview](https://angular.io/guide/reactive-forms#overview-of-reactive-forms):

> Reactive forms use an explicit and immutable approach to managing the state of a form at a given point in time. Each change to the form state returns a new state, which maintains the integrity of the model between changes. Reactive forms are built around observable streams, where form inputs and values are provided as streams of input values, which can be accessed synchronously.
>
> Reactive forms also provide a straightforward path to testing because you are assured that your data is consistent and predictable when requested. Any consumers of the streams have access to manipulate that data safely.
>
> Reactive forms differ from template-driven forms in distinct ways. Reactive forms provide more predictability with synchronous access to the data model, immutability with observable operators, and change tracking through observable streams.
>
> Template-driven forms allow direct access to modify data in your template, but are less explicit than reactive forms because they rely on directives embedded in the template, along with mutable data to track changes asynchronously. See the [Forms Overview](https://angular.io/guide/forms-overview) for detailed comparisons between the two paradigms.

## Sign in reactive form component

We'll recreate the familiar **Sign in** form reactively.

![Forms](assets/sign-form-template.jpg) <!-- TODO: asset -->
[From victorthemes](https://victorthemes.com/freebies/sign-form-template/)

Generate the component:

```sh
ng g c sign-in-rf
```

```ts
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

Import `ReactiveFormsModule` in `AppModule` (or the module that declares the component):

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
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

## `FormGroup`, `FormControl`, `FormArray`

- `AbstractControl` — base class for the three types below
- `FormControl` — tracks value and validation for a single input
- `FormGroup` — object-shaped group of controls
- `FormArray` — array-shaped group for dynamic lists

A form usually starts with a **FormGroup** that registers child **AbstractControl** instances.

For Sign in:

```ts
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

## Binding the form

Bind the group and controls:

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

Large forms get verbose with `new FormControl(...)`. Use `FormBuilder`:

```ts
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

## Updating values with `patchValue` and `setValue`

`AbstractControl` provides `setValue` and `patchValue`:

- On `FormControl`, `patchValue` delegates to `setValue`.
- On `FormGroup` / `FormArray`, `patchValue` updates only the keys you pass; `setValue` requires an exact shape match.

Use `patchValue` for partial updates; use `setValue` when you want strict structure enforcement.

`reset()` restores initial state.

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
onSubmit(): void {
  console.log(this.signInForm);
}
```

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

**2. Async validators** — return `Promise` or `Observable` (e.g. username uniqueness check). Passed as the **third** constructor argument.

```ts
isUserNameDuplicated(control: AbstractControl): Observable<ValidationErrors> {
    return of(null);
}

let control = new FormControl("", Validators.required, this.isUserNameDuplicated);
this.fb.control("", Validators.required, this.isUserNameDuplicated);
```

> For performance reasons, Angular only runs async validators if all sync validators pass. Each must complete before errors are set.

https://angular.io/guide/form-validation#validator-functions

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

Form setup with validators:

```ts
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

With `FormBuilder`, each control is a three-element array: `[defaultValue, syncValidators, asyncValidators]`.

![Reactive Forms 2](assets/day36-01.gif) <!-- TODO: asset -->

Disable submit until the form is valid: `[disabled]="signInForm.invalid"` on the button.

### Your first custom validator

`Validators.required` passes for whitespace-only input. Six spaces satisfy `required` and `minLength(6)` but aren't meaningful usernames.

Remove `Validators.pattern` temporarily to see the issue:

![Reactive Forms 2](assets/day36-02.gif) <!-- TODO: asset -->

`NoWhitespaceValidator`:

```ts
import { AbstractControl, ValidatorFn } from '@angular/forms';

export function NoWhitespaceValidator(): ValidatorFn {
  return (control: AbstractControl): { [key: string]: any } => {
    let controlVal = control.value;
    if (typeof controlVal === 'number') {
      controlVal = `${controlVal}`;
    }
    let isWhitespace = (controlVal || '').trim().length === 0;
    let isValid = !isWhitespace;
    return isValid ? null : { whitespace: 'value is only whitespace' };
  };
}
```

Replace `Validators.required` with `NoWhitespaceValidator()`:

```ts
this.signInForm = this.fb.group({
  username: [
    '',
    Validators.compose([
      NoWhitespaceValidator(),
      Validators.minLength(6),
    ]),
  ],
});
```

![Reactive Forms 2](assets/day36-03.gif) <!-- TODO: asset -->

Used in the [Angular Jira Clone](https://github.com/trungk18/jira-clone-angular/blob/master/frontend/src/app/core/validators/no-whitespace.validator.ts) project.

## Summary

You now know reactive form fundamentals — `FormGroup`, `FormControl`, `FormBuilder`, binding, value updates, sync validators, and a custom validator. For async validators and cross-field checks, see [form validation](validation.md).

## Code sample

- https://github.com/tieppt/100-doc-angular/tree/day35
- https://stackblitz.com/edit/100-days-of-angular-day-35
- https://stackblitz.com/edit/100-days-of-angular-day-36

## Youtube Video

[![Day 35](https://img.youtube.com/vi/oTwukyGa_qY/0.jpg)](https://youtu.be/oTwukyGa_qY) <!-- TODO: asset -->
[![Day 36](https://img.youtube.com/vi/ozHU4MmRS1w/0.jpg)](https://youtu.be/ozHU4MmRS1w) <!-- TODO: asset -->

## References

- https://angular.io/guide/forms-overview
- https://angular.io/guide/forms
- https://angular.io/guide/reactive-forms
- https://angular.io/api/forms/Validators
- [Experimenting with Angular reactive forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-reactive-forms-trong-angular/)
- [Experimenting with Angular template-driven forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-template-driven-forms-trong-angular/)

## Author

Tiep Phan — https://github.com/tieppt · Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

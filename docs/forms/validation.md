---
roadmap_node: "validation"
title: "Angular Form Async Validators"
file: "forms/validation.md"
source_days: [37]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Form Async Validators

In [reactive forms](reactive-forms.md) we covered sync validation and a simple custom validator. This article focuses on **async validators**.

## Prerequisites

We'll build a `registerForm` with:

1. **Username**
   - Required, 6–32 letters only
   - Mock existing users: `trungvo`, `tieppt`, `chautran` — registration blocked if the username matches

2. **Password**
   - Required, 6–32 characters, letters, digits, at least one special from `!@#$%^&*`

3. **Confirm password**
   - Same rules as password
   - Must match the password field

### Setup

```sh
ng g c register
```

```diff
const routes: Routes = [
  {
    path: "sign-in",
    component: SignInComponent
  },
  {
    path: "sign-in-rf",
    component: SignInRfComponent
  },
+  {
+    path: "register",
+    component: RegisterComponent
+  },
  {
    path: "",
    redirectTo: "register",
    pathMatch: "full"
  }
];
```

```ts
const PASSWORD_PATTERN = /^(?=.*[!@#$%^&*]+)[a-z0-9!@#$%^&*]{6,32}$/;

this.registerForm = this._fb.group({
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
      Validators.pattern(PASSWORD_PATTERN),
    ]),
  ],
  confirmPassword: [
    '',
    Validators.compose([
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(PASSWORD_PATTERN),
    ]),
  ],
});
```

Template:

```html
<div class="container">
  <form
    class="register-form"
    [formGroup]="registerForm"
    autocomplete="off"
    (ngSubmit)="submitForm()"
  >
    <h2>Register</h2>
    <div class="row-control">
      <mat-form-field appearance="outline">
        <mat-label>Username</mat-label>
        <input matInput placeholder="Username" formControlName="username" />
      </mat-form-field>
      <pre>{{ registerForm.get("username")?.errors | json }}</pre>
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
      <pre>{{ registerForm.get("password")?.errors | json }}</pre>
    </div>
    <div class="row-control">
      <mat-form-field appearance="outline">
        <mat-label>Confirm Password</mat-label>
        <input
          type="password"
          matInput
          placeholder="Confirm Password"
          formControlName="confirmPassword"
        />
      </mat-form-field>
      <pre>{{ registerForm.get("confirmPassword")?.errors | json }}</pre>
    </div>
    <div class="row-control row-actions">
      <button
        mat-raised-button
        color="primary"
        type="submit"
        [disabled]="registerForm.invalid"
      >
        Register
      </button>
    </div>
    <pre>{{ registerForm.value | json }}</pre>
  </form>
</div>
```

## Custom validators needed

1. Async validator — API check for duplicate username
2. Sync group validator — confirm password matches password

## 1. Async validator for username

Async validators return `Promise<ValidationErrors | null>` or `Observable<ValidationErrors | null>`. Username uniqueness usually requires a server round-trip.

Mock API (logs `Trigger API call` on each invocation):

```ts
validateUsername(username: string): Observable<boolean> {
  console.log("Trigger API call");
  let existedUsers = ["trungvo", "tieppt", "chautran"];
  let isValid = existedUsers.every(x => x !== username);
  return of(isValid).pipe(delay(1000));
}
```

Two ways to write an async validator:

- A function `(control: AbstractControl) => Promise<...> | Observable<...>`
- Implement the [AsyncValidator](https://angular.io/api/forms/AsyncValidator) interface

We'll use the function style (the interface approach needs injecting services into the validator factory).

### `validateUserNameFromAPI`

```ts
const validateUserNameFromApi = (api: ApiService) => {
  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    return api.validateUsername(control.value).pipe(
      map((isValid: boolean) => {
        return isValid ? null : { usernameDuplicated: true };
      })
    );
  };
};
```

Wire it as the third array element on the control:

```ts
this.registerForm = this._fb.group({
  username: [
    '',
    Validators.compose([
      Validators.required,
      Validators.minLength(6),
      Validators.pattern(/^[a-z]{6,32}$/i),
    ]),
    validateUserNameFromApi(this._api),
  ],
});
```

After six valid letters, the async validator runs on every keystroke:

![Async Validator](assets/day37-01.gif) <!-- TODO: asset -->

### `validateUserNameFromAPIDebounce`

Search boxes often wait ~300ms between keystrokes before calling the API. Same idea with `timer`:

```ts
const validateUserNameFromApiDebounce = (api: ApiService) => {
  return (control: AbstractControl): Observable<ValidationErrors | null> => {
    return timer(300).pipe(
      switchMap(() =>
        api.validateUsername(control.value).pipe(
          map((isValid) => {
            if (isValid) {
              return null;
            }
            return {
              usernameDuplicated: true,
            };
          })
        )
      )
    );
  };
};
```

![Async Validator debounced](assets/day37-02.gif) <!-- TODO: asset -->

## Note

> Angular doesn't wait for async validators to complete before firing ngSubmit. So the form may be invalid if the validators have not resolved.

While the username check is pending (1s delay), the Register button can become enabled. A fast click submits before validation finishes.

```ts
submitForm() {
  console.log("Submit form leh");
}
```

![Async Validator submit race](assets/day37-03.gif) <!-- TODO: asset -->

Fix pattern from [Stack Overflow](https://stackoverflow.com/questions/49516084/reactive-angular-form-to-wait-for-async-validator-complete-on-submit): wait until status is not `PENDING`, then submit only if `VALID`.

```ts
this.formSubmit$
  .pipe(
    tap(() => this.registerForm.markAsDirty()),
    switchMap(() =>
      this.registerForm.statusChanges.pipe(
        startWith(this.registerForm.status),
        filter((status) => status !== 'PENDING'),
        take(1)
      )
    ),
    filter((status) => status === 'VALID'),
    tap(() => {
      this.submitForm();
    })
  )
  .subscribe();
```

```html
<form
  class="register-form"
  [formGroup]="registerForm"
  autocomplete="off"
  (ngSubmit)="formSubmit$.next()"
></form>
```

![Async Validator fixed submit](assets/day37-04.gif) <!-- TODO: asset -->

## 2. Bonus: validate confirm password

Cross-field check on the `FormGroup`:

```ts
const validateMatchedControlsValue = (
  firstControlName: string,
  secondControlName: string
) => {
  return function (formGroup: FormGroup): ValidationErrors | null {
    const { value: firstControlValue } = formGroup.get(
      firstControlName
    ) as AbstractControl;
    const { value: secondControlValue } = formGroup.get(
      secondControlName
    ) as AbstractControl;
    return firstControlValue === secondControlValue
      ? null
      : {
          valueNotMatch: {
            firstControlValue,
            secondControlValue,
          },
        };
  };
};
```

Apply at group level:

```ts
this.registerForm = this._fb.group(
    {
      password: [
        "",
        Validators.compose([
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(PASSWORD_PATTERN)
        ])
      ],
      confirmPassword: [
        "",
        Validators.compose([
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(PASSWORD_PATTERN)
        ])
      ]
    },
    {
      validators: validateMatchedControlsValue("password", "confirmPassword")
    }
  );
```

![Confirm password validation](assets/day37-05.gif) <!-- TODO: asset -->

## Summary

- Async validators: `validate(control): Promise<ValidationErrors | null> | Observable<ValidationErrors | null>`
- Angular does **not** wait for async validators before `ngSubmit` — guard submit yourself when validators can be pending

## Code sample

- https://stackblitz.com/edit/100-days-of-angular-day-37-async-validator

## References

- https://trungk18.com/experience/angular-async-validator/
- [Experimenting with Angular reactive forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-reactive-forms-trong-angular/)
- [Experimenting with Angular template-driven forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-template-driven-forms-trong-angular/)

## Youtube Video

[![Day 37](https://img.youtube.com/vi/-ib5p8KbapQ/0.jpg)](https://youtu.be/-ib5p8KbapQ) <!-- TODO: asset -->

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

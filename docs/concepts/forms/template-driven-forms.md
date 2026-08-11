---
roadmap_node: "template-driven-forms"
title: "Angular Template-driven Forms"
file: "forms/template-driven-forms.md"
source_days: [33, 34]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Angular Template-driven Forms

Forms are everywhere — bank account applications, university registration, onboarding paperwork at a new job. Apps need forms to collect user input. A familiar example is a **Sign in** form:

![Forms](assets/sign-form-template.jpg) <!-- TODO: asset -->
[From victorthemes](https://victorthemes.com/freebies/sign-form-template/)

## Introduction

Angular is a full-fledged framework with two built-in form approaches: **Template-driven Forms** and **Reactive Forms** (also called **Model-driven Forms**).

> Angular provides two different approaches to handling user input through forms: reactive and template-driven. Both capture user input events from the view, validate the user input, create a form model and data model to update, and provide a way to track changes. [Angular Forms overview](https://angular.io/guide/forms-overview)

- **Template-driven Forms** rely mainly on template **directives** such as `NgForm`, `NgModel`, `required`, and so on. They use two-way binding to keep the template and component model in sync.

- **Reactive Forms** build the form from model objects in the component class, with only a few directives on the template.

> Template-driven forms use two-way data binding to update the data model in the component as changes are made in the template and vice versa. [Angular.io](https://angular.io/guide/forms)

> Reactive forms provide a model-driven approach to handling form inputs whose values change over time. [Angular.io](https://angular.io/guide/reactive-forms)

## Getting started

We'll use Angular and Angular Material for a nicer demo.

Create a new project:

```sh
ng new acme
```

Choose routing and styles when prompted, for example:

```
? Would you like to add Angular routing? Yes
? Which stylesheet format would you like to use? SCSS
```

Add Angular CDK and Material:

```sh
ng add @angular/cdk
```

```sh
ng add @angular/material
```

Answer the setup questions or accept defaults, for example:

```
? Choose a prebuilt theme name, or "custom" for a custom theme: Indigo/Pink [ Preview: https://material.angular.io?theme=indigo-pink ]
? Set up global Angular Material typography styles? Yes
? Set up browser animations for Angular Material? Yes
```

Start the dev server:

```sh
ng serve
```

## Sign in form

Generate a `sign-in` component and add a route:

```sh
ng g c sign-in
```

```ts
const routes: Routes = [
  {
    path: 'sign-in',
    component: SignInComponent,
  },
];
```

Open http://localhost:4200/sign-in and build the form: username, password, remember-me checkbox, and submit button.

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

Import the Material modules used by `SignInComponent` in `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';

@NgModule({
  declarations: [AppComponent, SignInComponent],
  imports: [
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatButtonModule,
  ],
})
export class AppModule {}
```

![day33-sign-in-form](assets/day33-sign-in-form.png) <!-- TODO: asset -->

## Integrate Angular Forms

Import `FormsModule` from `@angular/forms` into `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
import { FormsModule } from '@angular/forms';

@NgModule({
  declarations: [AppComponent, SignInComponent],
  imports: [
    // other NgModules
    FormsModule,
  ],
})
export class AppModule {}
```

### `ngForm` and `ngModel` directives

Expose the `NgForm` instance with a template reference and `ngForm` export:

```html
<form novalidate #signInForm="ngForm" ...></form>
```

Use `signInForm` in the template or pass it to the component class. Example — handle submit:

```ts
export class SignInComponent implements OnInit {
  constructor() {}

  ngOnInit(): void {}

  onSubmit(form: NgForm): void {
    console.log(form);
  }
}
```

```html
<form
  novalidate
  #signInForm="ngForm"
  (submit)="onSubmit(signInForm)"
  ...
></form>
```

Without `ngModel`, controls aren't registered and `signInForm.value` is empty:

```html
<pre>
{{ signInForm.value | json }}
</pre>
```

Register controls with `ngModel`:

```html
<input matInput placeholder="Username" ngModel />
```

Saving triggers a runtime error:

```
Error: If ngModel is used within a form tag, either the name attribute must be set or the form control must be defined as 'standalone' in ngModelOptions.

  Example 1: <input [(ngModel)]="person.firstName" name="first">
  Example 2: <input [(ngModel)]="person.firstName" [ngModelOptions]="{standalone: true}">
```

Add a `name` attribute to register the control with the parent form:

```html
<input matInput placeholder="Username" ngModel name="username" />
```

The control is registered; typing updates the form value.

![day33-sign-in-form](assets/day33-sign-in-form-2.png) <!-- TODO: asset -->

Do the same for the other fields:

```html
<form
  class="sign-in-form"
  novalidate
  #signInForm="ngForm"
  (submit)="onSubmit(signInForm)"
>
  <h2>Sign in</h2>
  <div class="row-control">
    <mat-form-field appearance="outline">
      <mat-label>Username</mat-label>
      <input matInput placeholder="Username" ngModel name="username" />
    </mat-form-field>
  </div>
  <div class="row-control">
    <mat-form-field appearance="outline">
      <mat-label>Password</mat-label>
      <input
        type="password"
        matInput
        placeholder="Password"
        ngModel
        name="password"
      />
    </mat-form-field>
  </div>
  <div class="row-control">
    <mat-checkbox ngModel name="rememberMe">Remember me</mat-checkbox>
  </div>
  <div class="row-control row-actions">
    <button mat-raised-button color="primary" type="submit">Sign in</button>
  </div>

  <pre>{{ signInForm.value | json }}</pre>
</form>
```

![day33-sign-in-form](assets/day33-sign-in-form-3.png) <!-- TODO: asset -->

### `submit` vs `ngSubmit`

We listened to native `submit` above. Angular also fires `ngSubmit` on form submit.

Both run when the user submits (e.g. clicks the submit button). `ngSubmit` prevents the browser's default full-page reload behavior.

If your handler throws, native `submit` may reload the page; `ngSubmit` won't (in current Angular versions).

```ts
onSubmit(form: NgForm) {
  // Do something awesome
  console.log(form);
  throw new Error('something went wrong');
}
```

Prefer `ngSubmit` for form submit handlers.

> Note: `ngSubmit` works with Reactive Forms too.

## `ngModel`, `[ngModel]`, and `[(ngModel)]`

`ngModel` registers a control with the form. The other forms bind data:

- `[ngModel]` — one-way property binding from the component to the template
- `[(ngModel)]` — two-way binding between template and model

Pre-fill the form from a component object:

```ts
export class SignInComponent implements OnInit {
  userInfo = {
    userName: 'tiepphan',
    password: '',
    rememberMe: true,
  };
  constructor() {}

  ngOnInit(): void {}

  onSubmit(form: NgForm): void {
    console.log(form);
  }
}
```

```html
<form
  class="sign-in-form"
  novalidate
  #signInForm="ngForm"
  (submit)="onSubmit(signInForm)"
>
  <h2>Sign in</h2>
  <div class="row-control">
    <mat-form-field appearance="outline">
      <mat-label>Username</mat-label>
      <input
        matInput
        placeholder="Username"
        [ngModel]="userInfo.userName"
        name="username"
      />
    </mat-form-field>
  </div>
  <div class="row-control">
    <mat-form-field appearance="outline">
      <mat-label>Password</mat-label>
      <input
        type="password"
        matInput
        placeholder="Password"
        [ngModel]="userInfo.password"
        name="password"
      />
    </mat-form-field>
  </div>
  <div class="row-control">
    <mat-checkbox [ngModel]="userInfo.rememberMe" name="rememberMe"
      >Remember me</mat-checkbox
    >
  </div>
  <div class="row-control row-actions">
    <button mat-raised-button color="primary" type="submit">Sign in</button>
  </div>

  <pre>{{ signInForm.value | json }}</pre>
  <pre>{{ userInfo | json }}</pre>
</form>
```

The model values appear in the controls, but user edits don't flow back to `userInfo` — one-way binding only:

![day33-sign-in-form](assets/day33-sign-in-form-4.png) <!-- TODO: asset -->

Switch to two-way binding:

```html
<input matInput placeholder="Username" [(ngModel)]="userInfo.userName" name="username" />
<!-- same for password and rememberMe -->
```

![day33-sign-in-form](assets/day33-sign-in-form.gif) <!-- TODO: asset -->

![day33-sign-in-form](assets/day33-sign-in-form-5.png) <!-- TODO: asset -->

## Angular Forms validation

Frontend validation is easy to bypass — **always validate on the server** too, whether or not the client validated.

### Control state flags

| Flag | Meaning |
| --- | --- |
| `touched` | User focused then blurred the control, or `markAsTouched()` was called |
| `untouched` | Opposite of `touched` |
| `dirty` | User changed the value (even typing then deleting counts) |
| `pristine` | Value unchanged since initialization |

Angular adds CSS classes you can style against:

- `.ng-valid`
- `.ng-invalid`
- `.ng-pending`
- `.ng-pristine`
- `.ng-dirty`
- `.ng-untouched`
- `.ng-touched`

### Built-in validation directives

Template-driven forms ship with:

- `required` — value must be present
- `minlength` — minimum length
- `maxlength` — maximum length
- `pattern` — must match a RegExp
- `email` — email-like pattern

Source: [validators.ts](https://github.com/angular/angular/blob/10.0.x/packages/forms/src/directives/validators.ts)

### Validating the Sign in form

Requirements:

- **Username:** required, 6–32 characters, letters only
- **Password:** required, 6–32 characters, letters and digits, at least one special character from `!@#$%^&*`

Username field:

```html
<input
  matInput
  placeholder="Username"
  required
  minlength="6"
  maxlength="32"
  [pattern]="usernamePattern"
  [(ngModel)]="userInfo.userName"
  name="username">
```

```ts
export class SignInComponent {
  usernamePattern = /^[a-z]{6,32}$/i;
}
```

Watch the DOM classes change as you type:

![Sign In form state](assets/day34-sign-in-form-1.gif) <!-- TODO: asset -->

Expose `ngModel` to read `errors`:

```html
<input
  ...
  #username="ngModel"
  [(ngModel)]="userInfo.userName"
  name="username">

<pre>{{ username.errors | json }}</pre>
```

![Sign In form errors](assets/day34-sign-in-form-2.gif) <!-- TODO: asset -->

Show messages with `*ngIf`:

```html
<mat-error *ngIf="username.errors.required">Username is required!</mat-error>
```

That throws at first because `errors` is `null` when valid or untouched. Use safe navigation:

```html
<mat-error *ngIf="username.errors?.required">Username is required!</mat-error>
```

Angular Material shows errors after `touched`. Without Material, also check `touched` or `dirty`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<mat-error *ngIf="username.touched && !username.valid">
  <span *ngIf="username.errors.required">Username is required</span>
  <span *ngIf="username.errors.minlength || username.errors.maxlength">Length from 6 to 32 characters</span>
  <span *ngIf="!(username.errors.minlength || username.errors.maxlength) && username.errors.pattern">Only alphabet</span>
</mat-error>
```

![Sign In form errors](assets/day34-sign-in-form-3.gif) <!-- TODO: asset -->

Password field — same pattern:

```html
<mat-form-field appearance="outline">
  <mat-label>Password</mat-label>
  <input
    type="password"
    matInput
    placeholder="Password"
    required
    minlength="6"
    maxlength="32"
    [pattern]="passwordPattern"
    #password="ngModel"
    [(ngModel)]="userInfo.password"
    name="password">
  <mat-error *ngIf="password.touched && !password.valid">
    <span *ngIf="password.errors.required">Password is required</span>
    <span *ngIf="password.errors.minlength || password.errors.maxlength">Length from 6 to 32 characters</span>
    <span *ngIf="!(password.errors.minlength || password.errors.maxlength) && password.errors.pattern">
      Only alphabet, digit and at least one of !@#$%^&*
    </span>
  </mat-error>
</mat-form-field>
```

```ts
passwordPattern = /^(?=.*[!@#$%^&*]+)[a-z0-9!@#$%^&*]{6,32}$/;
```

## Summary

You now know template-driven form basics — `FormsModule`, `ngForm`, `ngModel`, two-way binding, `ngSubmit`, and template validation. Practice on more forms from UI template sites.

## Code sample

- https://github.com/tieppt/100-doc-angular/tree/day33
- https://github.com/tieppt/100-doc-angular/tree/day34
- https://stackblitz.com/edit/100-days-of-angular-day-33?file=src%2Fapp%2Fsign-in%2Fsign-in.component.html
- https://stackblitz.com/edit/100-days-of-angular-day-34?file=src%2Fapp%2Fsign-in%2Fsign-in.component.html

## Youtube Video

[![Day 33](https://img.youtube.com/vi/0kbEVtO79Xw/0.jpg)](https://youtu.be/0kbEVtO79Xw) <!-- TODO: asset -->
[![Day 34](https://img.youtube.com/vi/45VnmzfV_MI/0.jpg)](https://youtu.be/45VnmzfV_MI) <!-- TODO: asset -->

## References

- https://angular.io/guide/forms-overview
- https://angular.io/guide/forms
- https://angular.io/guide/form-validation
- https://angular.io/guide/reactive-forms
- [Experimenting with Angular template-driven forms (Vietnamese)](https://www.tiepphan.com/thu-nghiem-voi-angular-template-driven-forms-trong-angular/)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

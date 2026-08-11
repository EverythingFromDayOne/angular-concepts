---
roadmap_node: "control-value-accessor"
title: "DisabledControlDirective for Reactive Forms"
file: "forms/control-value-accessor.md"
source_days: [43]
original_authors: ["Chau Tran"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# DisabledControlDirective for Reactive Forms

## Did You Know — Reactive Forms warning

With Reactive Forms you may have seen:

```
It looks like you're using the disabled attribute with a reactive form directive. If you set disabled to true
when you set up this control in your component class, the disabled attribute will actually be set in the DOM for
you. We recommend using this approach to avoid 'changed after checked' errors.

Example:
form = new FormGroup({
first: new FormControl({value: 'Nancy', disabled: true}, Validators.required),
last: new FormControl('Drew', Validators.required)
});
```

Triggering code:

```ts
export class ReactiveFormWarningComponent implements OnInit {
  disabledName = false;
  form: FormGroup;

  constructor(private fb: FormBuilder) {}

  ngOnInit() {
    this.form = this.fb.group({
      name: [''],
    });
  }
}
```

```html
<button (click)="disabledName = !disabledName">Toggle name state</button>
<form [formGroup]="form">
  <input
    class="form-control"
    type="text"
    formControlName="name"
    [disabled]="disabledName"
  />
</form>
```

![DisabledControlDirective to disable Reactive Form control](./assets/day43-01.gif) <!-- TODO: asset -->

Reactive Forms ignore the native `disabled` attribute — the input won't actually disable.

## Approach

### 1. Declare disabled state in the `FormGroup`

```ts
this.form = this.fb.group({
  name: [{ value: '', disabled: false }],
});
```

### 2. Use `FormControl.enable()` / `disable()`

```ts
this.form.get('name').enable();
this.form.get('name').disable();
```

Both work, but neither lets you drive disable state from the template with `[disabled]="disabledName"` like the warning example.

## Directive approach

Use a **directive** — **DisabledControlDirective**. It applies alongside `formControlName` or `formControl`. Use `[disabledControl]` instead of `[disabled]`:

```ts
import { Directive, Input } from '@angular/core';
import { NgControl } from '@angular/forms';

@Directive({
  selector: '([formControlName], [formControl])[disabledControl]',
})
export class DisabledControlDirective {
  @Input() set disabledControl(state: boolean) {
    const action = state ? 'disable' : 'enable';
    this.ngControl.control[action]();
  }

  constructor(private readonly ngControl: NgControl) {}
}
```

Template:

```html
<form [formGroup]="form">
  <input type="text" formControlName="name" [disabledControl]="disabledName" />
</form>
```

![DisabledControlDirective to disable Reactive Form control](./assets/day43-02.gif) <!-- TODO: asset -->

## Note

Disabled controls are **omitted** from `FormGroup.value`. Use `FormGroup.getRawValue()` to include disabled control values.

## Source code

https://stackblitz.com/edit/angular-disable-reactive-form-control-directive?file=src/app/disabled-control.directive.ts

## Author

Chau Tran — https://github.com/nartc

*Translated from the original Vietnamese as part of the angular-concepts project.*

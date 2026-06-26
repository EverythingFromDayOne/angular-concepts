---
roadmap_node: "directive-composition"
title: "Composing Form Data Sources with Directives"
file: "directives/directive-composition.md"
source_days: [47]
original_authors: ["Tuan Le"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Composing Form Data Sources with Directives

## Introduction

Forms are everywhere. Often a select control shares the same UI logic but only differs by **data source**. Reusing that control across the app means repeating fetch/mapping code.

![SelectExample](assets/day-047-select-example.jpg) <!-- TODO: asset -->

This pattern combines **directives** and an **injection token** so each select picks its data source declaratively:

```html
<form [formGroup]="form">
  <h1>Select</h1>
  <!-- using mode data source -->
  <app-select-control
    appModeDataSource 
    formControlName="mode"
    placeholder="Select mode"
  ></app-select-control>

  <!-- using condition data source -->
  <app-select-control
    appConditionDataSource
    formControlName="condition"
    placeholder="Select condition"
  ></app-select-control>
</form>
```

Swap the directive → different options, same control component.

## Concepts

![ConceptDiagram](assets/day-047-concept-diagram.jpg) <!-- TODO: asset -->

All data-source directives implement a shared interface so the select control sees a uniform `options$` stream. The select injects a token to discover which directive is paired on the same element.

## Coding practice

### Step 1: Project setup

```sh
ng new composition-datasource-with-directive
```

Install ng-zorro (other UI libraries work similarly):

```sh
ng add ng-zorro-antd
```

```sh
ng g c select-control
```

### Step 2: Control value accessor base

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
@Directive() // Prevent error with Angular 9 and upper
// tslint:disable-next-line:directive-class-suffix
export class BaseControlValueAccessor implements ControlValueAccessor {

  @ViewChild(FormControlDirective, { static: true })
  formControlDirective?: FormControlDirective;
  @Input() formControl?: FormControl;
  @Input() formControlName?: string;

  get control(): FormControl {
    return (
      this.formControl ||
      this.controlContainer.control?.get(this.formControlName as string) as FormControl
    );
  }

  protected constructor(
    protected controlContainer: ControlContainer
  ) {}

  registerOnChange(fn: any): void { ... }

  registerOnTouched(fn: any): void { ... }

  setDisabledState(isDisabled: boolean): void { ... }

  writeValue(obj: any): void { ... }
}
```

### Step 3: Select control

```typescript
@Component({
  selector: 'app-select-control',
  templateUrl: './select-control.component.html',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: SelectControlComponent,
      multi: true,
    }
  ],
})
export class SelectControlComponent extends BaseControlValueAccessor {
  @Input() placeholder = '';

  constructor(
    @Optional() controlContainer: ControlContainer,
  ) {
    super(controlContainer);
  }
}
```

### Step 4: Interface and injection token

```
├───select-control
│   └───directives
│           constants.ts
│           types.ts
```

`types.ts`

```typescript
import { Observable } from 'rxjs';

export interface Option {
  value: string,
  label: string
}

export interface SelectDirective {
  options$: Observable<Option[]>;
}
```

`constants.ts`

```typescript
import { InjectionToken } from '@angular/core';

export const SELECT_DIRECTIVE = new InjectionToken<SelectDirective>('SELECT_DIRECTIVE');
```

### Step 5: Wire the select to the token

```typescript
@Component({
  selector: 'app-select-control',
  templateUrl: './select-control.component.html',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: SelectControlComponent,
      multi: true,
    }
  ],
})
export class SelectControlComponent extends BaseControlValueAccessor {
  @Input() placeholder = '';

  options$: Observable<Option[]> = of([]);

  constructor(
    @Optional() controlContainer: ControlContainer,
    @Optional() @Inject(SELECT_DIRECTIVE) private directive: SelectDirective,
  ) {
    super(controlContainer);
    this.options$ = directive ? directive.options$ : of([]);
  }
}
```

### Step 6: Data-source directives

```sh
ng g d mode-data-source.directive
ng g d condition-data-source.directive
```

`mode-data-source.directive.ts`:

```typescript
@Directive({
  selector: 'app-select-control[appModeDataSource]',
  providers: [
    {
      provide: SELECT_DIRECTIVE,
      useExisting: ModeDataSourceDirective,
    },
  ],
})
export class ModeDataSourceDirective implements SelectDirective {
  options$: Observable<Option[]> = of([
    { label: 'Auto', value: 'auto' },
    { label: 'Manual', value: 'manual' },
  ]);
}
```

The selector `app-select-control[appModeDataSource]` limits the directive to the paired control.

Usage:

```html
<app-select-control
  appModeDataSource
  formControlName="mode"
  placeholder="Select mode"
></app-select-control>
```

When the component constructs, it resolves `SELECT_DIRECTIVE` via `useExisting` on the directive's `providers`. The standardized `options$` feeds the template.

Service-backed source with RxJS mapping:

```typescript
@Directive({
  selector: 'app-select-control[appConditionDataSource]',
  providers: [
    {
      provide: SELECT_DIRECTIVE,
      useExisting: ConditionDataSourceDirective,
    },
  ],
})
export class ConditionDataSourceDirective implements SelectDirective {
  constructor(private ref: RefService) {}

  options$: Observable<Option[]> = this.ref.getConditions();
}
```

Add `@Input()` on directives for extra customization.

## Summary

This pattern reduces duplication when many selects share UI but differ only by data source. It fits independent, reusable sources best. Tightly coupled options from one API call may need a different approach; dependent sources can use directive `@Input()` hooks.

## Code sample

- https://github.com/ngoctuanle/composition-datasource-with-directive

## Author

Tuan Le — https://github.com/ngoctuanle

*Translated from the original Vietnamese as part of the angular-concepts project.*

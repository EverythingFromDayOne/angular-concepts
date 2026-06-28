---
roadmap_node: "cdk-coercion"
title: "Input Coercion: built-in transforms and CDK utilities"
file: "tooling/cdk-coercion.md"
source_days: [42]
original_authors: ["Chau Tran", "Trung Vo"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Input Coercion: built-in transforms and CDK utilities

> **⚡ What changed since the original**
>
> This article was first written for Angular 9 (2020). The original opened
> by introducing CDK coercion (`coerceBooleanProperty`, `coerceNumberProperty`,
> etc.) as the way to normalize component inputs. **Angular 16.1 (2023) built
> the most common cases — boolean and number coercion — directly into the
> framework**, so the headline technique has changed:
>
> - **`booleanAttribute` and `numberAttribute`** are now exported from
>   `@angular/core`. Use them via the input transform API:
>   `@Input({ transform: booleanAttribute }) flag = false` (decorator) or
>   `input(false, { transform: booleanAttribute })` (signal).
> - **The `coerceBooleanProperty` setter+getter dance from the original
>   article is no longer needed for boolean inputs.** It still works — and is
>   preserved below with a `<!-- legacy -->` marker — but new code should use
>   `booleanAttribute`.
> - **CDK coercion is still useful** for cases v22 didn't build in:
>   `coerceArray`, `coerceCssPixelValue`, `coerceElement`, `coerceStringArray`,
>   plus runtime coercion outside template inputs.
> - **The article was moved** from `_orphans/cdk-coercion.md` to
>   `tooling/cdk-coercion.md` and the "Did You Know" / "After two Jira clone
>   tutorials" framing was dropped since that case-study series was retired
>   from this project.
>
> The article's structure flips: built-in transforms lead, CDK coercion
> functions are framed as the niche/library-author toolbox they actually are
> in v22.
>
> **See also**: [Signal Inputs](../reactivity/signal-inputs.md) · [Attribute Directives](../directives/attribute-directives.md)

---

When you build library components, custom directives, or any reusable piece
that exposes `@Input` (or `input()`) values to consumers, you'll eventually
hit a friction point: **the value the consumer wrote in the template isn't
quite the type your component wants to work with**. HTML attributes are
strings. Presence flags want to be booleans. Numeric attributes arrive as
strings too. **Coercion** is the process of normalizing those incoming values
to the type your component expects.

> Coercion is the process of implicitly converting data to a required format.

In **JS** you see **implicit** and **explicit** coercion everywhere.

### Implicit coercion

`1 + '1'` coerces `1` to `'1'` → `'11'`. `if ('trung') {}` coerces a non-empty
string to `true`.

### Explicit coercion

`if (Boolean('string')) {}` tells **JS** to convert explicitly — type casting.

**Implicit** vs **explicit** — that's the underlying idea. Angular input
coercion is mostly **explicit**: you tell the framework (or the framework
tells itself) how to convert the incoming value.

---

## The v22 way: built-in input transforms

Angular 16.1 introduced **`booleanAttribute`** and **`numberAttribute`** —
plain functions exported from `@angular/core` that you pass to an input's
`transform` option. The framework calls them automatically on every value
flowing into the input.

### `booleanAttribute` — for presence-style HTML flags

```typescript
import { Component, input, booleanAttribute } from '@angular/core';

@Component({
  selector: 'app-child',
  template: `flag is: {{ someFlag() }}`,
})
export class ChildComponent {
  readonly someFlag = input(false, { transform: booleanAttribute });
}
```

All of these now work — and produce the expected boolean:

```html
<!-- Presence — true -->
<app-child someFlag></app-child>

<!-- Explicit string "true" — true -->
<app-child someFlag="true"></app-child>
<app-child [someFlag]="'true'"></app-child>

<!-- Explicit string "false" — false -->
<app-child someFlag="false"></app-child>
<app-child [someFlag]="'false'"></app-child>

<!-- Bound boolean expression — passes through -->
<app-child [someFlag]="true"></app-child>
<app-child [someFlag]="isAdmin()"></app-child>
```

The behavior of `booleanAttribute`: returns `false` only for the literal
string `'false'` (case-insensitive) or for falsy values like `false`, `null`,
`undefined`, `0`, `''`. Everything else — including presence-only — is
`true`. This matches the way native HTML boolean attributes work (presence
of `disabled` means disabled, regardless of the attribute value).

### `numberAttribute` — for numeric HTML attributes

```typescript
import { Component, input, numberAttribute } from '@angular/core';

@Component({
  selector: 'app-pager',
  template: `Page {{ page() }} of {{ total() }}`,
})
export class PagerComponent {
  readonly page = input(1, { transform: numberAttribute });
  readonly total = input(0, { transform: numberAttribute });
}
```

```html
<!-- String "5" coerced to number 5 -->
<app-pager page="5" total="100"></app-pager>

<!-- Bound number passes through -->
<app-pager [page]="currentPage()" [total]="100"></app-pager>
```

`numberAttribute` returns `NaN` for unparseable values by default. You can
provide a fallback via the second-argument form:

```typescript
readonly page = input(1, {
  transform: (value: unknown) => numberAttribute(value, 1), // fallback 1 instead of NaN
});
```

### Same pattern works for decorator inputs (if you have legacy code)

If you're working in a codebase that still uses `@Input()` decorators, the
same `transform` option works there too — it was added to `@Input` in v16.1
alongside the standalone helpers:

```typescript
import { Component, Input, booleanAttribute, numberAttribute } from '@angular/core';

@Component({ /* ... */ })
export class ChildComponent {
  @Input({ transform: booleanAttribute }) someFlag = false;
  @Input({ transform: numberAttribute }) someCount = 0;
}
```

### Custom transforms

The `transform` option accepts **any function** with signature
`(value: T_input) => T_stored`. `booleanAttribute` and `numberAttribute` are
just two examples. Write your own when you need domain-specific normalization:

```typescript
import { Component, input } from '@angular/core';

// Coerce a comma-separated string into a string array
function csvToArray(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') return value.split(',').map(s => s.trim());
  return [];
}

@Component({ /* ... */ })
export class TagListComponent {
  readonly tags = input([], { transform: csvToArray });
}
```

```html
<!-- Both work -->
<app-tag-list tags="angular,signals,v22"></app-tag-list>
<app-tag-list [tags]="['angular', 'signals', 'v22']"></app-tag-list>
```

Custom transforms are the natural place to drop in CDK coercion helpers when
those still apply — covered in the next section.

---

## CDK coercion APIs (still useful in v22)

Angular CDK exposes a small toolbox of coercion utilities. The bool/number
ones are now superseded by built-ins, but several are still the right tool
for v22 code.

### Still useful

| Function | What it coerces | Typical v22 use |
| --- | --- | --- |
| `coerceArray<T>(value)` | A `T \| T[]` into `T[]` | Inside a custom `transform` for inputs that accept either a single value or an array |
| `coerceCssPixelValue(value)` | A `number \| string` into a CSS pixel string (`123` → `"123px"`, `"12em"` → `"12em"`) | Building style bindings from numeric inputs |
| `coerceElement(elementOrRef)` | An `ElementRef \| HTMLElement` into the underlying `HTMLElement` | Library code that accepts either form for ergonomic APIs |
| `coerceStringArray(value, separator?)` | A `string \| string[]` into a `string[]`, splitting strings on a separator | The "comma-separated input" pattern shown above |

```typescript
import { coerceArray, coerceCssPixelValue } from '@angular/cdk/coercion';
import { Component, input } from '@angular/core';

@Component({
  selector: 'app-grid',
  template: `<div [style.height]="height()"></div>`,
})
export class GridComponent {
  // height accepts 200, '200px', or '12em' — all coerced to a CSS pixel value
  readonly height = input('auto', {
    transform: (v: number | string) => coerceCssPixelValue(v),
  });

  // items accepts a single Item or an array — always stored as Item[]
  readonly items = input([], {
    transform: (v: Item | Item[]) => coerceArray(v),
  });
}
```

These complement the built-in `booleanAttribute`/`numberAttribute` rather
than competing with them — they handle cases the framework didn't build in.

### Legacy in v22 (still exported, but new code should use built-ins)

| Function | v22 replacement |
| --- | --- |
| `coerceBooleanProperty(value)` | `booleanAttribute(value)` from `@angular/core` |
| `coerceNumberProperty(value, fallback?)` | `numberAttribute(value, fallback?)` from `@angular/core` |

The CDK versions remain in the package for backward compatibility — they
won't be removed in v22 — but they shouldn't appear in new code.

---

## The pre-v16.1 way: `coerceBooleanProperty` setter pattern

Before v16.1, the input transform API didn't exist. The standard pattern was
a setter+getter on the input property, with the getter exposing the coerced
value under a different name (the setter can't share the name of a `boolean`
backing field).

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9-16.0: setter + private backing field + getter
import { Component, Input } from '@angular/core';
import { coerceBooleanProperty } from '@angular/cdk/coercion';

@Component({
  selector: 'app-child',
  template: `flag is: {{ castedSomeFlag }}`,
})
export class ChildComponent {
  @Input() set someFlag(val: any) {
    this._someFlag = coerceBooleanProperty(val);
  }

  get castedSomeFlag(): boolean {
    return this._someFlag;
  }

  private _someFlag = false;
}
```

The v22 equivalent collapses all of that into a single line:

```typescript
// ── v22 equivalent: input() + booleanAttribute transform ──────────────────
import { Component, input, booleanAttribute } from '@angular/core';

@Component({
  selector: 'app-child',
  template: `flag is: {{ someFlag() }}`,
})
export class ChildComponent {
  readonly someFlag = input(false, { transform: booleanAttribute });
}
```

No backing field, no separate getter name, no `any` cast on the setter
parameter. The transform happens automatically every time the binding fires.

You'll still see the setter pattern in libraries that support older Angular
versions (or in codebases that haven't migrated yet). When you encounter it,
recognize what it's doing and reach for the input-transform replacement.

---

## Why this matters — the mechanism in one paragraph

Input transforms run **inside Angular's input binding pipeline**, before the
value is written to the input's underlying storage. For a signal input, the
transform's return value is what gets written to the signal slot — readers
see the coerced value, never the raw one. For a decorator input, the
transform runs before the property setter is called. Either way, the
transform is a pure function the framework calls; it has no access to `this`
or DI. That's why custom transforms must be self-contained functions (no
class methods bound with `this`) — they run outside the component instance's
context.

The setter pattern from the legacy era worked, but it ran *after* the
property had already been written, then overwrote it with the coerced value.
That meant any `ngOnChanges` or effect observing the input could briefly see
the un-coerced value between the write and the coercion. Input transforms
eliminate that window — the coerced value is the only value the rest of the
framework ever sees.

---

## Summary

In v22, reach for **built-in input transforms** first:

- `booleanAttribute` for HTML-presence-style boolean flags
- `numberAttribute` for numeric attributes (with optional fallback)
- Custom transform functions for anything else (CSV strings, pixel values,
  domain-specific normalization)

**CDK coercion** still has a place — `coerceArray`, `coerceCssPixelValue`,
`coerceElement`, `coerceStringArray` are typically used **inside** custom
transforms or in non-template code where you're normalizing values at
runtime. The boolean/number CDK helpers (`coerceBooleanProperty`,
`coerceNumberProperty`) are legacy in v22; their built-in replacements have
the same behavior with less ceremony.

## See also

- [Signal Inputs](../reactivity/signal-inputs.md) — `input()`, `input.required()`, and the transform option in depth
- [Attribute Directives](../directives/attribute-directives.md) — coercion in custom directive inputs
- [Reactive Forms](../forms/reactive-forms.md) — typed forms use a related pattern (typed value flows)

## Source code

https://stackblitz.com/edit/angular-ivy-cdk-coercion?file=src/app/child/child.component.ts

## References

- [`booleanAttribute` API (angular.dev)](https://angular.dev/api/core/booleanAttribute)
- [`numberAttribute` API (angular.dev)](https://angular.dev/api/core/numberAttribute)
- [Input transforms guide (angular.dev)](https://angular.dev/guide/components/inputs#transforms)
- [`@angular/cdk/coercion` source](https://github.com/angular/components/tree/main/src/cdk/coercion)
- [JS type coercion explained (freeCodeCamp)](https://www.freecodecamp.org/news/js-type-coercion-explained-27ba3d9a2839/)

## Author

Chau Tran — https://github.com/nartc · Trung Vo — https://github.com/trungk18

*Adapted from the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) series (Day 46) by Angular Vietnam. MIT licensed.*
---
roadmap_node: "cdk-coercion"
title: "Angular CDK Coercion"
file: "_orphans/cdk-coercion.md"
source_days: [42]
original_authors: ["Chau Tran", "Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Did You Know — Angular CDK Coercion

After two Jira clone tutorials, let's look at **Angular CDK Coercion** — handy APIs with sparse official docs.

## What is Angular CDK Coercion?

Angular CDK ships **coercion** utilities. When you build libraries and need `@Input` values normalized to the right type, these helpers shine.

> Coercion is the process of implicitly converting data to a required format.

Coercion converts inputs to the expected type. In **JS** you see **implicit** and **explicit** coercion everywhere.

### Implicit coercion

`1 + '1'` coerces `1` to `'1'` → `'11'`. `if ('trung') {}` coerces a non-empty string to `true`.

### Explicit coercion

`if (Boolean('string')) {}` tells **JS** to convert explicitly — type casting.

**Implicit** vs **explicit** — that's the idea.

### CDK coercion APIs

- `coerceArray`
- `coerceBooleanProperty`
- `coerceCssPixelValue`
- `coerceElement`
- `coerceNumberProperty`
- `coerceStringArray`

Source: [src/cdk/coercion](https://github.com/angular/components/tree/master/src/cdk/coercion)

## `coerceBooleanProperty`

We'll demo boolean inputs — it changes how you pass `true`/`false` to components.

### Typical boolean `@Input`

```ts
export class ChildComponent {
  @Input() someFlag: boolean;
}
```

Binding syntax required:

```html
<child [someFlag]="true"></child>  <!-- works -->
<child [someFlag]="false"></child> <!-- works -->
```

These fail (Ivy may also fail the build on type mismatch):

```html
<child someFlag="false"></child>      <!-- doesn't work -->
<child someFlag="true"></child>       <!-- doesn't work -->
<child [someFlag]="'false'"></child>  <!-- doesn't work -->
<child [someFlag]="'true'"></child>   <!-- doesn't work -->
```

![Angular CDK Coercion](./assets/day42-01.png) <!-- TODO: asset -->

Only boolean expressions work.

### Boolean input with `coerceBooleanProperty`

HTML-style presence attributes are ergonomic when a flag is usually `true`:

```html
<child someFlag></child>
```

Steps:

1. `npm i @angular/cdk`
2. Coerce in a setter:

```ts
export class ChildComponent {
  @Input() set someFlag(val: any) {
    this._someFlag = coerceBooleanProperty(val);
  }

  get castedSomeFlag(): boolean {
    return this._someFlag;
  }

  private _someFlag: boolean;
}
```

Template usage — `[someFlag]="true"` and bare `someFlag` both work:

```html
<child [someFlag]="false"></child>
<child [someFlag]="true"></child>
<child someFlag></child>
```

> The getter must use a different name than the setter property (`castedSomeFlag`, not `someFlag`) so types align.

![Angular CDK Coercion](./assets/day42-02.png) <!-- TODO: asset -->

## Summary

Consider CDK coercion when you want cleaner template APIs for library inputs.

## Source code

https://stackblitz.com/edit/angular-ivy-cdk-coercion?file=src/app/child/child.component.ts

## Reference

- https://www.freecodecamp.org/news/js-type-coercion-explained-27ba3d9a2839/
- https://indepth.dev/posts/1315/angular-cdk-coercion

## Author

Chau Tran — https://github.com/nartc · Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

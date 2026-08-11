---
roadmap_node: "attribute-directives"
title: "Attribute Directives"
file: "directives/attribute-directives.md"
source_days: [6]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Attribute Directives

What are attribute directives, and how do they differ from structural directives like `NgIf` and `NgForOf`?

Structural directives add, remove, or change the DOM tree. Attribute directives change the appearance (style) or behavior of a DOM element, component, or other directive. That's the key difference.

## Class binding

In real apps, we often need to add or remove CSS classes based on conditions. For example, when a tab is selected, it gets a `tab-active` class while the others don't:

```html
<div [class.tab-active]="isTabActive">some content</div>
```

This is property binding: when `isTabActive` is `true`, the element's `classList` includes `tab-active`; when `false`, it doesn't.

You can also bind the entire `class` attribute:

```html
[class]="classExpr"
```

`classExpr` can be a string, an array of strings, or an object — object keys with truthy values are added, falsy keys are removed.

| Type | Value |
| --- | --- |
| String | `"my-class-1 my-class-2 my-class-3"` |
| Array of strings | `['foo', 'bar']` |
| Object | `{ foo: true, bar: false }` |

`ngClass` works similarly to `[class]="classExpr"`, but class binding is generally preferred over `ngClass`.

## Style binding

Sometimes you need to bind inline styles. Style binding syntax:

`[style.property]="expression"`

The expression evaluates to `string | undefined | null`. Example:

```html
<div [style.width]="someValue"></div>
```

With a unit suffix: `[style.property.unit]="expression"`

The expression evaluates to `number | undefined | null`. Example:

`[style.height.%]="containerHeight"`

You can also bind the entire style object:

`[style]="styleExpr"`

| Type | Value |
| --- | --- |
| String | `"width: 100%; height: 100%"` |
| Array of strings | `['width', '100px']` |
| Object | `{ width: '100px', height: '100px' }` |

`ngStyle` is similar, but style binding is recommended in most cases.

Note: style property names accept both dash-case and camelCase — for example, `font-size` and `fontSize` both work.

## Summary

We've looked at built-in attribute directives for class and style binding, so you can style elements based on component data.

Further reading:

- https://angular.io/guide/template-syntax#attribute-class-and-style-bindings
- https://angular.io/api/common/NgClass
- https://angular.io/api/common/NgStyle
- [Experimenting with Angular NgStyle and NgClass](https://www.tiepphan.com/thu-nghiem-voi-angular-2-built-in-directives-ngstyle-ngclass/) (Vietnamese)

## Youtube Video

[![Attribute Directives](https://img.youtube.com/vi/Zh36WRD3MMQ/0.jpg)](https://youtu.be/Zh36WRD3MMQ) <!-- TODO: asset -->

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

---
roadmap_node: "content-projection"
title: "Content Projection"
file: "components/templates/content-projection.md"
source_days: [13]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Content Projection

Sometimes you'll build components that share the same layout but differ in labels or inner content. You could pass everything through `@Input` properties — but what happens to markup placed between a component's opening and closing tags? Can we drop template content inside a component tag and have it appear where we want?

**Content projection** (similar to web component `slot`) solves this.

## `ng-content` and common questions

### How do I use `ng-content`?

Suppose we reuse the toggle component from [component interactions](../component-interactions.md) for a customer survey. Questions are Yes/No, but each question has a different label. How do we make the toggle flexible without adding more inputs? Project the content passed between the component tags.

Place `ng-content` anywhere in the component template:

**toggle.component.html**

```html
<div
  class="toggle-wrapper"
  [class.checked]="checked"
  tabindex="0"
  (click)="toggle()"
>
  <div class="toggle"></div>
</div>
<div class="toogle-label">
  <ng-content></ng-content>
</div>
```

**app.component.html**

```html
<app-toggle [(checked)]="questions.question1">
  <span>Question 1</span>
</app-toggle>

<app-toggle [(checked)]="questions.question2">
  <span>Question 2</span>
</app-toggle>
```

### Can I use multiple `ng-content` tags?

What if you put `ng-content` twice in the template — does content appear in both places?

**toggle.component.html**

```html
<div class="toogle-label">
  <div>content 1</div>
  <ng-content></ng-content>
</div>

<div class="toogle-label">
  <div>content 2</div>
  <ng-content></ng-content>
</div>
```

Only `content 2` shows with the projected label. With multiple unqualified `ng-content` tags, only the last one receives the content — like having a single slot. Use one `ng-content` without a selector, or use selectors (below).

![multiple ng-content](assets/ng100doc-d013-multiple-ng-content.png) <!-- TODO: asset -->

### `ng-content` and selectors

HTML `<table>` reorders `<thead>`, `<tbody>`, and `<tfoot>` regardless of source order. You can do something similar with `ng-content` **selectors** — and this also lets you use multiple projection slots.

Selector forms:

- Tag selector: `<ng-content select="some-component-selector-or-html-tag"></ng-content>`
- CSS class selector: `<ng-content select=".some-class"></ng-content>`
- Attribute selector: `<ng-content select="[some-attr]"></ng-content>`
- Combined: `<ng-content select="some-tag[some-attr]"></ng-content>`

Toggle component example:

**toggle.component.html**

```html
<header>
  <ng-content select=".toogle-header"></ng-content>
</header>
<div
  class="toggle-wrapper"
  [class.checked]="checked"
  tabindex="0"
  (click)="toggle()"
>
  <div class="toggle"></div>
</div>
<div class="toogle-label">
  <ng-content select="label"></ng-content>
</div>

<div class="toggle-content">
  <ng-content></ng-content>
</div>
```

**app.component.html**

```html
<app-toggle [(checked)]="questions.question1">
  <h3 class="toogle-header">Header 1</h3>
  <label>Question 1</label>
  <span>Some paragraph</span>
</app-toggle>
```

Even if you reorder projected elements, the toggle component displays them in the layout defined by its `ng-content` slots:

```html
<app-toggle [(checked)]="questions.question2">
  <h3 class="toogle-header">Header 2</h3>
  <span>Some paragraph 2</span>
  <label>Question 2</label>
</app-toggle>
```

> Note: when multiple elements match a `select` selector, `ng-content` projects all of them.

### `ng-content` and `ngProjectAs`

Suppose the toggle expects content with selector `app-label`, but consumers want a plain HTML `<label>`, a different label component, or a label wrapped in a `div`. The `select` attribute won't match.

Use `ngProjectAs` to tell Angular how to treat projected content:

**app.component.html**

```html
<app-toggle [(checked)]="questions.question1">
  <h3 class="toogle-header">Header 1</h3>
  <label ngProjectAs="app-label">Question 1</label>
  <span>Some paragraph</span>
</app-toggle>
```

Many libraries use this technique for customization — for example, [ngx-dropzone](https://github.com/peterfreeman/ngx-dropzone).

## Summary

`ng-content` (and the `slot` concept in other frameworks) helps you build highly reusable components. This article introduced the basics; we'll revisit projection when we cover `ContentChild` in [templates architecture](templates-architecture.md).

Further reading:

- [Content projection in Angular](https://www.tiepphan.com/thu-nghiem-voi-angular-content-projection-trong-angular/) (Vietnamese)
- https://medium.com/claritydesignsystem/ng-content-the-hidden-docs-96a29d70d11b

## Youtube Video

[![Content Projection](https://img.youtube.com/vi/-vN52YVbcgk/0.jpg)](https://youtu.be/-vN52YVbcgk) <!-- TODO: asset -->

## Code sample

https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-13?file=src%2Fapp%2Ftoggle%2Ftoggle.component.html

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

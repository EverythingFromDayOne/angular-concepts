---
roadmap_node: "js-widget-embedding"
title: "JavaScript Widgets and Embedded Scripts"
file: "_orphans/js-widget-embedding.md"
source_days: [46]
original_authors: ["Tuan Le"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# JavaScript Widgets and Embedded Scripts

How to build and deploy a JavaScript widget via an embedded script.

## Purpose and use cases

Modern web apps are mostly JavaScript. Live sites often need **lightweight, independent** features — feedback forms, support widgets, chat — without redeploying the whole host app. **JavaScript widgets** solve that.

## Concept

A **JavaScript widget** adds capabilities to an existing page through a small **embedded script** plus configuration.

The script bootstraps everything the host needs for a self-contained feature.

Example: [Intercom](https://www.intercom.com/) chat — paste a snippet, get full chat support.

![Demo Intercom 1](./assets/day-46-demo-intercom-1.png) <!-- TODO: asset -->
![Demo Intercom 2](./assets/day-46-demo-intercom-2.gif) <!-- TODO: asset -->

Source: Intercom

## Implementation notes

Widgets inject DOM nodes into the host page. Watch for:

- Style and script conflicts with the host
- Bundle size
- Browser features the host environment may lack

Webpack plugins and polyfills help address these for modern stacks.

## Building embedded scripts with React and Angular

### React

Build like a normal React app with custom webpack output.

Instead of mounting only from `app.tsx` on `index.html`, export a mount API from `embeddable-widget.tsx`:

```ts
export default class WidgetBooking {
  static htmlelment: any;

  static mount(
    id: string,
    locale: "en" | "vi" = "en",
    fullscreened: boolean = false,
    divId: string = ""
  ) {
    const component = (
      <Widget id={id} locale={locale} fullscreened={fullscreened} divId={divId} />
    );

    function doRender() {
      if (WidgetBooking.htmlelment) {
        throw new Error("EmbeddableWidget is already mounted, unmount first");
      }
      let htmlelment = null;
      if (divId) {
        htmlelment = document.querySelector(`#${divId}`);
      } else {
        htmlelment = document.createElement("div");
        htmlelment.style.position = "fixed";
        htmlelment.style.bottom = "20px";
        htmlelment.style.right = "20px";
        document.body.appendChild(htmlelment);
      }

      ReactDOM.render(component, htmlelment);
      WidgetBooking.htmlelment = htmlelment;
    }
    if (document.readyState === "complete") {
      doRender();
    } else {
      window.addEventListener("load", () => {
        doRender();
      });
    }
  }

  static unmount() {
    if (!WidgetBooking.el) {
      throw new Error("EmbeddableWidget is not mounted, mount first");
    }
    ReactDOM.unmountComponentAtNode(WidgetBooking.htmlelment);
    WidgetBooking.htmlelment.parentNode.removeChild(WidgetBooking.htmlelment);
    WidgetBooking.htmlelment = null;
  }
}
```

Webpack exposes the library on `window`:

```js
// webpack.config.base.js (excerpt)
  output: {
    path: path.resolve(__dirname, "dist"),
    publicPath: "/",
    filename: "[name].js",
    library: "WidgetBooking",
    libraryExport: "default",
    libraryTarget: "window"
  },
```

Host usage:

```html
<script src="./widget.js"></script>
<script>
    WidgetBooking.mount(
        'idXXX',
    "en",
    true // fullscreen
    );
</script>
```

### Angular

Use [Angular Elements](https://angular.io/guide/elements) — register a custom element in `AppModule`:

```ts
import { createCustomElement } from '@angular/elements';

export class AppModule {
  constructor(injector: Injector) {
    const el = createCustomElement(AppComponent, { injector });
    customElements.define('online-booking', el);
  }

  ngDoBootstrap() {}
}
```

Build without hashing, then concatenate chunks:

```bash
ng build booking-widget --output-hashing none
```

```js
const fs = require('fs-extra');
const concat = require('concat');

(async function build() {
  const files = [
    './dist/apps/booking-widget/runtime-es2015.js',
    './dist/apps/booking-widget/polyfills-es2015.js',
    './dist/apps/booking-widget/main-es2015.js'
  ];

  const es5Files = [
    './dist/apps/booking-widget/runtime-es5.js',
    './dist/apps/booking-widget/polyfills-es5.js',
    './dist/apps/booking-widget/main-es5.js'
  ];

  await concat(files, './dist/booking-widget.js');
  await concat(es5Files, './dist/booking-widget-es5.js');

  await fs.ensureDir('./dist/assets/booking-widget');

  await fs.copyFile('./dist/apps/booking-widget/styles.css', './dist/assets/booking-widget/styles.css');
})();
```

Embed on the host:

```html
<script src="./booking-widget.js"></script>
<script src="./booking-widget-es5.js" nomodule defer"></script>
<script>
const widgetElement = document.createElement('div');
widgetElement.innerHTML = `
          <online-booking id="${id}" lang="${lang}" fullscreen="${true}" ></online-booking>`;
document.body.appendChild(widgetElement);
</script>
```

Both React and Angular widgets remain testable like normal apps.

### Web Component (vanilla)

Define a custom element; initialization runs in `connectedCallback`:

![Web Component Life Cycle](./assets/day-46-webcomponent-life-cycle.png) <!-- TODO: asset -->

Source: https://www.thinktecture.com

React inside shadow DOM:

```jsx
class Widget extends HTMLElement {
  connectedCallback() {
    const mountPoint = document.createElement(div);
    this.attachShadow({ mode: 'open' }).appendChild(mountPoint);

    const id = this.getAttribute('id');
    ReactDOM.render(<WidgetApp id={id} />, mountPoint);
  }
}
customElements.define('embedded-widget', Widget);

// when using
<embedded-widget id="Idxxx"></embedded-widget>
```

Custom element names should include a hyphen to avoid clashing with native tags.

## Summary

Embedded scripts are a practical complement to [micro frontends](../monorepo/module-federation.md). Widgets still need a strategy for cross-widget communication — a topic for another article.

## Author

Tuan Le — https://github.com/ngoctuanle

*Translated from the original Vietnamese as part of the angular-concepts project.*

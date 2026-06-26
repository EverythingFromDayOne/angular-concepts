---
roadmap_node: "module-federation"
title: "Micro Frontends with Module Federation"
file: "monorepo/module-federation.md"
source_days: [39]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "11"
angular_baseline: "22"
---

# Micro Frontends with Module Federation

> Good frontend development is hard. Scaling frontend development so that many teams can work simultaneously on a large and complex product is even harder.

> source: [https://martinfowler.com/articles/micro-frontends.html](https://martinfowler.com/articles/micro-frontends.html)

## What are micro frontends?

Single Page Apps (SPAs) are everywhere — feature-rich, complex, and often paired with microservices on the backend. Over time they grow into **frontend monoliths** that are hard to maintain.

Recently, microservices ideas have been applied to the frontend. **Micro frontends** split one SPA into independently developed feature slices, each owned by its own team.

> "An architectural style where independently deliverable frontend applications are composed into a greater whole"

> source: [https://martinfowler.com/articles/micro-frontends.html](https://martinfowler.com/articles/micro-frontends.html)

### Monolithic frontends

![Monolithic Frontends](https://micro-frontends.org/ressources/diagrams/organisational/monolith-frontback-microservices.png) <!-- TODO: asset -->

> source: [https://micro-frontends.org](https://micro-frontends.org)

### Micro frontends

![Micro Frontends](https://micro-frontends.org/ressources/diagrams/organisational/verticals-headline.png) <!-- TODO: asset -->

> source: [https://micro-frontends.org](https://micro-frontends.org)

## Approaches

- **Iframe** — easy but limited (navigation, running host scripts, etc.)
- **Proxy (e.g. nginx)** — separate apps at paths like `<host>/mailbox`, `<host>/calendar`; navigating between apps feels like a full reload
- **Web Components** — framework-agnostic custom elements ([Angular Elements](https://angular.io/guide/elements), [Stencil](https://stenciljs.com))
- **Orchestrator frameworks** — Webpack 5 Module Federation, [piral](https://piral.io), [luigi](https://luigi-project.io/), [single-spa](https://single-spa.js.org/)

## Build an email client with micro frontends

Demo repo: [https://github.com/tieppt/micro-frontends-demo](https://github.com/tieppt/micro-frontends-demo)

![Email Client Micro Frontends](./assets/micro-fe-app.jpg) <!-- TODO: asset -->

Two teams can own **mailbox** and **calendar**. The calendar team might ship a widget embeddable in mailbox pages via custom elements.

### Shell or host app

Micro apps need a **shell (host)** for routing, shared state, and composition. The shell technology constrains micro apps — e.g. Angular/React shells need wrappers so each micro app's router obeys the host framework.

### Prerequisites

We'll use **Webpack 5 Module Federation** and **Angular 14** (article written during Angular 11 RC era).

Create the workspace:

```sh
npx @angular/cli@14 new ngft-email-client --create-application=false
```

Generate three applications — shell plus two remotes:

```
npx ng generate application shell
# ? Would you like to add Angular routing? Yes
# ? Which stylesheet format would you like to use? SCSS

npx ng generate application mailbox
# routing: Yes, SCSS

npx ng generate application calendar
# routing: Yes, SCSS
```

Install custom webpack support:

```sh
npm i -D @angular-builders/custom-webpack@14
```

Example `package.json` scripts:

```json
{
  "name": "acme-email-client",
  "scripts": {
    "start:shell": "ng serve --project=shell",
    "start:mailbox": "ng serve --project=mailbox",
    "start:calendar": "ng serve --project=calendar"
  },
  "dependencies": {
    "@angular/animations": "^14.2.0",
    "@angular/common": "^14.2.0",
    "@angular/compiler": "^14.2.0",
    "@angular/core": "^14.2.0",
    "@angular/forms": "^14.2.0",
    "@angular/platform-browser": "^14.2.0",
    "@angular/platform-browser-dynamic": "^14.2.0",
    "@angular/router": "^14.2.0",
    "rxjs": "~7.5.0",
    "tslib": "^2.3.0",
    "zone.js": "~0.11.4"
  },
  "devDependencies": {
    "@angular-builders/custom-webpack": "^14.0.1",
    "@angular-devkit/build-angular": "^14.2.3",
    "@angular/cli": "~14.2.3",
    "@angular/compiler-cli": "^14.2.0",
    "typescript": "~4.7.2"
  }
}
```

Assign ports in `angular.json` (shell `5200`, mailbox `5300`, calendar `5400`):

```json
{
  "projects": {
    "shell": {
      "architect": {
        "serve": {
          "options": {
            "port": 5200
          }
        }
      }
    }
  }
}
```

### Enable Module Federation

Create `webpack.config.js` and `webpack.prod.config.js` per app. In `angular.json`:

- Replace `@angular-devkit/build-angular` with `@angular-builders/custom-webpack`
- Point `customWebpackConfig` at your webpack files
- Add `publicHost` under `serve.options` for federation

```json
{
  "projects": {
    "shell": {
      "architect": {
        "build": {
          "builder": "@angular-builders/custom-webpack:browser",
          "options": {
            "customWebpackConfig": {
              "path": "projects/shell/webpack.config.js"
            }
          },
          "configurations": {
            "production": {
              "customWebpackConfig": {
                "path": "projects/shell/webpack.prod.config.js"
              }
            }
          }
        },
        "serve": {
          "builder": "@angular-builders/custom-webpack:dev-server",
          "options": {
            "port": 5200,
            "publicHost": "http://localhost:5200/"
          }
        }
      }
    }
  }
}
```

Repeat for `mailbox` and `calendar`.

#### Shell config

```js
const { ModuleFederationPlugin } = require('webpack').container;

/** @type {require('webpack').Configuration} */
module.exports = {
  output: {
    publicPath: 'auto',
    uniqueName: 'shell',
  },
  optimization: {
    runtimeChunk: false,
  },
  experiments: {
    outputModule: true,
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'shell',
      library: {
        type: 'module',
      },
      remotes: {
        mailbox: 'http://localhost:5300/remoteEntry.js',
        calendar: 'http://localhost:5400/remoteEntry.js',
      },
      shared: ['@angular/core', '@angular/common', '@angular/router'],
    }),
  ],
};
```

Shell routing loads remote modules:

```ts
const routes: Routes = [
  {
    path: 'mailbox',
    loadChildren: () => import('mailbox/MailboxModule').then(m => m.MailboxModule)
  },
  {
    path: 'calendar',
    loadChildren: () => import('calendar/CalendarModule').then(m => m.CalendarModule)
  }
];
```

TypeScript doesn't know those virtual paths — add `src/types.d.ts`:

```ts
declare module 'mailbox/MailboxModule';
declare module 'calendar/CalendarModule';
```

Run `yarn start:shell`. You may hit `Uncaught Error: Shared module is not available for eager consumption` when sharing packages. Webpack recommends a dynamic import bootstrap split:

**bootstrap.ts**

```ts
import { enableProdMode } from '@angular/core';
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';

import { AppModule } from './app/app.module';
import { environment } from './environments/environment';

if (environment.production) {
  enableProdMode();
}

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
```

**main.ts**

```ts
import('./bootstrap').catch(err => console.error(err));
```

#### Remote app config (mailbox example)

```js
const { ModuleFederationPlugin } = require('webpack').container;

module.exports = {
  output: {
    publicPath: 'auto',
    uniqueName: 'mailbox',
  },
  optimization: {
    runtimeChunk: false,
  },
  experiments: {
    outputModule: true,
  },
  plugins: [
    new ModuleFederationPlugin({
      name: 'mailbox',
      filename: 'remoteEntry.js',
      library: {
        type: 'module',
      },
      exposes: {
        './MailboxModule': 'projects/mailbox/src/app/mailbox/mailbox.module.ts',
      },
      shared: ['@angular/core', '@angular/common', '@angular/router'],
    }),
  ],
};
```

Key remote fields: `name`, `library`, `filename` (must match shell's `remoteEntry.js` URL), and `exposes` (public API per [ESM syntax in Node 14](https://medium.com/dev-genius/module-federation-advanced-api-inwebpack-5-0-0-beta-17-71cd4d42e534)).

**Standalone mode:** remotes can run alone — use the same dynamic `import('./bootstrap')` pattern and their own routing:

```ts
export const MAILBOX_ROUTES: Routes = [
  {
    path: '',
    component: MailboxHomeComponent,
  }
];

@NgModule({
  declarations: [
    MailboxHomeComponent
  ],
  imports: [
    CommonModule,
    RouterModule.forChild(MAILBOX_ROUTES),
  ]
})
export class MailboxModule { }
```

Calendar remote mirrors mailbox with `./CalendarModule`.

### Run the apps

```sh
npm run start:shell
npm run start:mailbox
npm run start:calendar
```

Open:

- http://localhost:5200/
- http://localhost:5300/
- http://localhost:5400/

![Micro Frontends Angular](./assets/micro-frontends.gif) <!-- TODO: asset -->

Each micro app runs standalone or through the shell.

## Summary

With Webpack 5 Module Federation you can compose an Angular micro-frontend email client. A follow-up topic is custom elements for embeddable widgets across micro apps.

## Code sample

- https://github.com/tieppt/micro-frontends-demo

## References

- https://medium.com/dev-genius/module-federation-advanced-api-inwebpack-5-0-0-beta-17-71cd4d42e534
- https://www.angulararchitects.io/aktuelles/the-microfrontend-revolution-part-2-module-federation-with-angular/
- https://martinfowler.com/articles/micro-frontends.html

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

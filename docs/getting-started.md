---
roadmap_node: "getting-started"
title: "Getting Started with Angular"
file: "getting-started.md"
source_days: [1, 2]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Getting Started with Angular

> **⚡ What changed since the original**
>
> This article was first written for Angular 9 (2020). The **journey** is the same — install Node.js, install the Angular CLI, scaffold a project, run it, understand its structure, create your first component. What changed is **what the scaffold produces**:
>
> - **Node.js requirement bumped.** Angular v22 needs Node 20.11+ or 22.11+. Node 12 (mentioned in the original) hasn't been supported for years.
> - **`AppModule` is gone.** Standalone components are the v22 default. The scaffold produces `app.config.ts` (providers), `app.routes.ts` (routes), and a standalone `AppComponent` instead of an `@NgModule`.
> - **`platformBrowserDynamic().bootstrapModule(AppModule)` → `bootstrapApplication(AppComponent, appConfig)`** in `main.ts`.
> - **No `environments/` folder by default.** The old `environment.ts` / `environment.prod.ts` split was removed in v17. Use environment files only if you add them via the CLI schematic.
> - **The "add HelloComponent to declarations" lesson at the end becomes "add HelloComponent to imports".** Standalone components are imported by other components, not declared in modules.
> - **CLI prompts changed.** `ng new` no longer asks about routing (enabled by default) — it asks about SSR/SSG instead.
> - Reference links updated from `angular.io` to `angular.dev` (Angular's documentation moved domains in v17).
>
> The Angular 9 walkthrough is preserved with `<!-- legacy -->` markers and followed by v22 equivalents. The closing "Why no AppModule?" section briefly explains the standalone shift in beginner-friendly terms — it's not a deep mechanism reflection, just enough context to understand what you're seeing.
>
> **See also**: [TypeScript Prerequisites](typescript-prereqs.md) · [Dependency Injection](dependency-injection/dependency-injection.md) · [Routing](routing/routing.md)

---

## Introduction

In recent years, Angular has remarkably improved and re-innovated its features and performance. These positive changes have helped this powerful framework attract more organizations, including big names such as Apple, PayPal, Telegram, Forbes, Nike, and others. We, **Angular Vietnam**, recognized that it is an opportune time to embark on this project, **100 Days of Angular**.

This series of tutorials aims to provide you a continuously intensive learning experience which not only inspires but also challenges you in your learning journey with Angular. In order to follow along, you're expected to be equipped with basic JavaScript and TypeScript knowledge. If you already know JS, [this tutorial](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html) from the TS official documentation would help you quickly get started with TS — or read our own [TypeScript Prerequisites](typescript-prereqs.md) walkthrough.

## Prerequisites

The essential tools and utilities for your learning journey with Angular include (but are not limited to):

- **IDE/Text Editor**: Choose what you're comfortable with. At **Angular Vietnam**, our team recommends either Visual Studio Code (VS Code) or JetBrains WebStorm as they are equipped with features that leverage your developer experience, such as smart code auto-completion, advanced debugging tools, and more.
- For readers choosing VS Code: These extensions suggested below will be tremendously helpful:
  - [Angular Language Service](https://marketplace.visualstudio.com/items?itemName=Angular.ng-template)
  - [EditorConfig for VS Code](https://marketplace.visualstudio.com/items?itemName=EditorConfig.EditorConfig)
  - [ESLint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint) — TSLint was deprecated; ESLint is the v22 standard
  - [Nx Console (optional)](https://marketplace.visualstudio.com/items?itemName=nrwl.angular-console)
  - [Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) — for consistent formatting

## Setting Up the Workspace

### Node.js

First, install **Node.js** from [`https://nodejs.org/en/download/`](https://nodejs.org/en/download/). Angular v22 requires:

- **Node.js 20.11.1+ or 22.11.0+** (Node 20 LTS and 22 LTS are both supported; older versions are not)
- **npm 10+** (ships with the supported Node versions)

If you're familiar with the terminal, use [**NVM**](https://github.com/nvm-sh/nvm) (macOS/Linux) or [**nvm-windows**](https://github.com/coreybutler/nvm-windows) to manage multiple Node versions when you work across projects.

To check if Node.js is installed:

```bash
node -v   # should print v20.x.x or v22.x.x
npm -v    # should print 10.x.x or newer
```

### Angular CLI

The **Angular CLI** is the standard tool for managing Angular projects from the terminal. Install it globally with npm:

```bash
npm install -g @angular/cli@latest
```

To verify the install:

```bash
ng version
```

At the time of this writing, the Angular CLI is at version **22**.

A few side notes:

- If you're using Windows, you may have to install either `Python` or `windows-build-tools` for native module compilation to succeed.
- If `'ng' is not recognized as an internal or external command` shows up after `ng version`, add `npm`'s global directory to your OS `PATH`. Run `npm config get prefix` to find it.
- On PowerShell, if you see "running scripts is disabled on this system," open PowerShell as Administrator and run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
  ```

## Application Initialization

After you've finished the steps above, run this command to scaffold your first Angular application:

```bash
ng new <your-app-name>
```

For example: `ng new angular100-d-o-c`

The CLI will ask a couple of questions. **The v22 prompts are different from the Angular 9 originals:**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```text
Angular 9 CLI prompts:
? Would you like to add Angular routing? (Y/n)
? Which stylesheet format would you like to use? (Use arrow keys)
```

```text
# v22 CLI prompts (typical, may vary slightly by minor version):
? Which stylesheet format would you like to use? (Use arrow keys)
? Do you want to enable Server-Side Rendering (SSR) and Static Site Generation (SSG/Prerendering)? (y/N)
```

Notice what's missing: **the routing question.** Routing is enabled by default in v22; opt out with `--routing=false` if you don't need it. Standalone components are also the default — there's no longer a `--standalone` flag.

For this tutorial, accept the defaults — SCSS for styling, **N** for SSR (we'll cover SSR separately).

After this step, open the generated folder in your preferred editor.

To run the app, execute this command in your project's directory:

```bash
ng serve
```

By default, the app runs at port 4200. Change the port with:

```bash
ng serve --port=9000
```

The working application is served at `http://localhost:4200/` and viewable in your browser.

## Exploring the Angular Project Structure

The v22 scaffold looks meaningfully different from the Angular 9 scaffold. Here's a comparison.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```text
Angular 9 scaffold:
src/
├── app/
│   ├── app-routing.module.ts    # AppRoutingModule (forRoot)
│   ├── app.component.ts         # AppComponent (declared in AppModule)
│   ├── app.component.html
│   ├── app.component.scss
│   ├── app.component.spec.ts
│   └── app.module.ts            # AppModule — registers AppComponent
├── environments/
│   ├── environment.ts           # dev environment
│   └── environment.prod.ts      # production environment
├── assets/
├── index.html
├── main.ts                      # platformBrowserDynamic().bootstrapModule(AppModule)
├── polyfills.ts                 # Zone.js + browser polyfills
└── styles.scss
```

```text
# v22 scaffold:
src/
├── app/
│   ├── app.config.ts            # ApplicationConfig — providers (provideRouter etc.)
│   ├── app.routes.ts            # Routes array — plain TS file, no NgModule
│   ├── app.ts                   # AppComponent — standalone (was app.component.ts in older v22 setups)
│   ├── app.html
│   ├── app.scss
│   └── app.spec.ts
├── index.html
├── main.ts                      # bootstrapApplication(AppComponent, appConfig)
└── styles.scss

# Notes on the v22 scaffold:
# - No app.module.ts, no app-routing.module.ts
# - No environments/ folder by default (add via `ng generate environments`)
# - No polyfills.ts by default (Zone.js is optional in v22; opt out for zoneless)
# - Filenames may be the trimmed form (app.ts) per the v20 style guide,
#   or the traditional form (app.component.ts) — both are valid in v22
```

Let's walk through the v22 scaffold piece by piece.

### `index.html`

Inside the `src` folder, you'll see an XML-like tag that doesn't seem like a legit HTML tag — `app-root`. To make an assumption, this tag seems to be a customized tag that wraps around something more intricate that magically renders the whole application. Hold onto that intuition — we'll explain `app-root` shortly.

```html
<!--src/index.html-->

<!--other stuff-->
<body>
  <app-root></app-root>
</body>
<!--other stuff-->
```

### `main.ts` — the entry point

`main.ts` is where your app starts running. The Angular 9 version used `platformBrowserDynamic().bootstrapModule(AppModule)`. The v22 version uses `bootstrapApplication(AppComponent, appConfig)` — no module needed.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: bootstrap via NgModule
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

```typescript
// ── v22 equivalent: bootstrap directly to the AppComponent ────────────────
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

bootstrapApplication(AppComponent, appConfig)
  .catch(err => console.error(err));
```

What changed:

- **`bootstrapApplication`** comes from `@angular/platform-browser` directly — no separate `platform-browser-dynamic` package needed.
- **`AppComponent`** is passed as the root component, **not** an `AppModule`. Standalone components can be roots.
- **`appConfig`** holds the app-wide providers (the providers list used to live inside `AppModule`).
- **`enableProdMode()` is gone.** Production mode is automatically enabled in production builds; you don't call it explicitly.

### `app/app.config.ts` — providers (replaces `AppModule`'s `providers` and `imports`)

In Angular 9, app-wide providers and shared modules were registered inside `AppModule`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: src/app/app.module.ts
import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, AppRoutingModule],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

In v22, the same job is done by `ApplicationConfig`:

```typescript
// ── v22: src/app/app.config.ts ────────────────────────────────────────────
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    // Other app-wide providers go here:
    // provideHttpClient(), provideAnimations(), etc.
  ],
};
```

And the routes themselves live in a plain TypeScript file:

```typescript
// src/app/app.routes.ts
import { Routes } from '@angular/router';

export const routes: Routes = [
  // Route entries — see the Routing article for the full guide
];
```

Notice what isn't there: no `declarations` array (standalone components self-declare), no `imports` array of `NgModule`s (each component imports what it uses), no `bootstrap` array (passed directly to `bootstrapApplication`).

### `app/app.component.ts` — standalone component

The component class itself looks similar to the Angular 9 version — the changes are subtle:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9: src/app/app.component.ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'first-application';
}
```

```typescript
// ── v22 equivalent: standalone + RouterOutlet import ──────────────────────
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss', // singular styleUrl in v22, plural styleUrls deprecated
  imports: [RouterOutlet],          // the component declares what it uses
  // standalone: true is the default in v22 — no need to write it
})
export class AppComponent {
  title = 'first-application';
}
```

Two real changes:

- **`styleUrls` (plural) → `styleUrl` (singular).** Singular form preferred for single-file styles. Plural still works but is deprecated.
- **`imports: [...]`** — this is the big one. When `AppComponent`'s template uses `<router-outlet>`, the component must list `RouterOutlet` in its `imports` array. This is the same pattern you'll use for every directive, pipe, or child component the template references.

That last bullet leads us to the lesson from the original article — what happens when you forget to import?

## Creating a New Angular Component

We'll create a `hello.component.ts` file and place it in the same folder as `app.component.ts`. In v22, run:

```bash
ng generate component hello
```

This produces a standalone component by default — no `--standalone` flag needed (it's been the default since v17, and the only mode in newer projects).

The generated file looks like this:

```typescript
// src/app/hello/hello.component.ts (v22)
import { Component } from "@angular/core";

@Component({
  selector: "app-hello",
  template: ` <h2>Hello there!</h2> `,
  // standalone: true is the default — no need to write it
})
export class HelloComponent {}
```

(The original article walked through creating this file manually first, then showed the `ng generate component` shortcut. The end result is the same.)

### The classic "not a known element" error

Let's try to use the new component. Append this line to `app.component.html`:

```html
<app-hello></app-hello>
```

Save it and run `ng serve`. If your intuition told you that maybe something will go wrong, it's right: the app fails to compile with this error:

```text
NG8001: 'app-hello' is not a known element:
1. If 'app-hello' is an Angular component, then verify that it is included in the
   'imports' of this component.
2. If 'app-hello' is a Web Component then add 'CUSTOM_ELEMENTS_SCHEMA' to the
   '@Component.schemas' of this component to suppress this message.
```

Notice the error wording in v22: it says **"included in the `imports` of this component"** — not "part of this module" like the Angular 9 error did. That single word change is the whole story of the standalone shift.

In Angular 9, the fix was to add `HelloComponent` to `AppModule.declarations`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Angular 9 fix: declare HelloComponent in AppModule
import { HelloComponent } from './hello.component';

@NgModule({
  declarations: [
    AppComponent,
    HelloComponent     // ← add it here
  ],
  imports: [BrowserModule, AppRoutingModule],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

In v22, the fix is to add `HelloComponent` to `AppComponent.imports`:

```typescript
// ── v22 fix: import HelloComponent into AppComponent ──────────────────────
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HelloComponent } from './hello/hello.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  imports: [
    RouterOutlet,
    HelloComponent,    // ← add it here
  ],
})
export class AppComponent {
  title = 'first-application';
}
```

The mental model shifts from **"components live inside modules"** (Angular 9) to **"components import other components directly"** (v22). The error fixed itself the same way each time — by telling the host where to find the child — but the host is now another component, not a module.

> **CLI naming convention reminder:** if you order a component `${name}` via
> `ng generate component`, the exported class is `${PascalCase(name)}Component`
> and its CSS selector is `app-${name}`. So `ng generate component hello`
> produces a class named `HelloComponent` with selector `app-hello`. Same
> convention as Angular 9 — the only thing that changed is where you register
> the result.

That's enough for today! Next, we'll cover **data binding**.

---

## Why no `AppModule`?

You might be wondering why `AppModule` exists in older Angular code if v22 doesn't need it. Here's the short version, suitable for a Day 1 article — the deeper story lives in [Standalone Migration](tooling/standalone-migration.md).

When Angular shipped in 2016, components needed a containing "module" to declare them. The NgModule served three jobs:

1. **Declare components, directives, and pipes** so the framework knew which templates could use which selectors
2. **Import other modules** to bring in shared functionality (the router, HTTP client, forms, etc.)
3. **Provide services** to the dependency injection tree

This worked, but it meant every component required two files to exist meaningfully — the component itself, and the module that declared it. As apps grew, "what module does this thing belong to" became a frequent source of friction. Lazy loading was tied to modules. Shared modules sprawled. The mental model added work without adding clarity for most apps.

Standalone components, introduced in Angular 14 and made the default in v17, fold all three jobs into the component itself:

- **Declarations** — the component declares its own selector; no external registry needed
- **Imports** — the component lists which other components, directives, and pipes its template uses
- **Providers** — app-wide providers live in `bootstrapApplication`'s `providers` array, route-level providers live in route definitions, component-level providers live on the component itself

The v22 scaffold reflects this: `app.config.ts` for app-wide providers, `app.routes.ts` for routes, and each component declaring its own dependencies. `AppModule` was eliminated by absorbing its three jobs into other parts of the framework — not by removing the jobs themselves.

**You'll still see NgModule in older codebases and some third-party libraries.** Angular maintains backward compatibility, so the two patterns coexist. New code should be standalone; legacy code can migrate file by file using `ng generate @angular/core:standalone`.

> **Historical footnote:** the original article noted *"there are heated
> discussions on whether NgModule should be deprecated in future Angular
> releases."* That discussion is now settled — Angular 17 made standalone the
> default for new code, and v22 continues that direction. NgModule is not
> deprecated and still works, but it's no longer the recommended pattern.

---

## Summary

You've installed Node.js (20+ or 22+) and the Angular CLI v22, scaffolded an app with `ng new`, walked through the v22 project structure (`main.ts`, `app.config.ts`, `app.routes.ts`, `app.component.ts`), and learned the v22 "component imports component" pattern by creating `HelloComponent` and wiring it up. The next article covers **data binding** — how component class state flows into the template.

## References

- [Angular setup guide (angular.dev)](https://angular.dev/installation)
- [Angular tutorial (angular.dev)](https://angular.dev/tutorials/learn-angular)
- [Angular architecture overview (angular.dev)](https://angular.dev/essentials)
- [Standalone components (angular.dev)](https://angular.dev/guide/components)
- [Angular version compatibility table](https://angular.dev/reference/versions)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the Vietnamese ["100 Days of Angular"](https://github.com/angular-vietnam/100-days-of-angular) series by Angular Vietnam. MIT licensed.*
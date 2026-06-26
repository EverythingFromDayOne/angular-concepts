---
roadmap_node: "getting-started"
title: "Getting Started with Angular"
file: "_orphans/getting-started.md"
source_days: [1, 2]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Getting Started with Angular

## Introduction

In recent years, Angular has remarkably improved and re-innovated its features and performance. These positive changes have helped this powerful framework attract more organizations, including big names such as Apple, PayPal, Telegram, Forbes, Nike, and others. We, **Angular Vietnam**, recognized that it is an opportune time to embark on this project, **100 Days of Angular**.

This series of tutorials aims to provide you a continuously intensive learning experience which not only inspires but also challenges you in your learning journey with Angular. In order to follow along, you're expected to be equipped with basic JavaScript and TypeScript knowledge. If you already know JS, [this tutorial](https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html) from the TS official documentation would help you quickly get started with TS.

## Prerequisites

The essential tools and utilities for your learning journey with Angular include (but are not limited to):

- **IDE/Text Editor**: Choose what you're comfortable with. At **Angular Vietnam**, our team recommends either Visual Studio Code (VS Code) or JetBrains WebStorm as they are equipped with features that leverage your developer experience, such as smart code auto-completion, advanced debugging tools, and more.
- For readers choosing VS Code: These extensions suggested below will be tremendously helpful:
  - [Angular Language Service](https://marketplace.visualstudio.com/items?itemName=Angular.ng-template)
  - [EditorConfig for VS Code](https://marketplace.visualstudio.com/items?itemName=EditorConfig.EditorConfig)
  - [ESLint/TSLint](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-typescript-tslint-plugin)
  - [Nx Console (optional)](https://marketplace.visualstudio.com/items?itemName=nrwl.angular-console)

## Setting Up the Workspace

### Node.js

First things first, you need to download **Node.js** from [`https://nodejs.org/en/download/`](https://nodejs.org/en/download/) and install it on your machine. It doesn't matter whether you choose the long-term support (LTS) version or the Current one. At the time of this writing, the latest LTS version is Node 12, with which Angular 9 is compatible.

If you're familiar with the terminal environment, you should use [**NVM**](https://github.com/nvm-sh/nvm) to install and manage multiple versions of Node.js in cases where you need to work with multiple projects requiring different versions of Node.js.

To check if Node.js is successfully installed on your machine, execute these command lines in your OS terminal application (by default, `Terminal` if you're using macOS/Linux, or `Command Prompt`/`Powershell` if you're using Windows):

```bash
node -v
npm -v
```

If you can see version numbers displayed, it means that `Node.js` and `NPM CLI` are ready to be used.

### Angular CLI

For development of an Angular project, **Angular CLI** is an essential utility to manage the project from the terminal environment. One way to install Angular CLI is to use NPM CLI by running this command line in your OS terminal application:

```bash
npm install -g @angular/cli@latest
```

To check if Angular CLI is properly installed, use this command:

```bash
ng version
```

At the time of this writing, Angular CLI is at version 9.

A few side notes:

- If you're using Windows, there's a chance that you have to install either `Python` or `windows-build-tools` to get SCSS running properly for the upcoming projects.
- If you encountered the error `'ng' is not recognized as an internal or external command.` after executing `ng version`, you need to add `npm global` into your OS `PATH` global variable.
- If you executed these commands on `Powershell`, you may encounter this error:

`File C:\Users\<username>\AppData\Roaming\npm\ng.ps1 cannot be loaded because running scripts is disabled on this system. For more information, see about_Execution_Policies at https:/go.microsoft.com/fwlink/?LinkID=135170.`

In this case, you have to enable policy to run commands. To enable it, open `Powershell` as Administrator and execute this command `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine` or follow the link in the error message for more details.

## Application Initialization

After you've finished the steps above, run this command to initialize an Angular application:

```bash
ng new <your-app-name>
```

For example, `ng new angular100-d-o-c`

You have to provide your answers for questions regarding concerns about your application's routing and style config as listed below:

- `Would you like to add Angular routing?`
- `Which stylesheet format would you like to use?`

At this point, you may want to accept the default options (`Y` for the question about routing and `SCSS` for the question about styling).

After this step, you can use your preferred text editor/IDE to open and edit the generated Angular application's source code.

To run the app, execute this command in your project's directory:

```bash
ng serve
```

By default, the app runs at port 4200. You can change which port to run the app by using the command:

```bash
ng serve --port=other-port-number
```

For instance: `ng serve --port=9000`

The working application is served at the address `http://localhost:4200/`, which can be viewed in your browser.

## Exploring the Angular Project Structure

Angular application project structure might be intimidating to you as a first timer, but actually it's pretty well organized. Let's walk through it together!

![overview project structure](https://raw.githubusercontent.com/angular-vietnam/100-days-of-angular/master/assets/day2-brief-overview-project-structure.png) <!-- TODO: asset -->

Firstly, let's investigate the `index.html` file inside the `src` folder: you would see an XML-like tag that doesn't seem like a legit HTML tag — `app-root` in most cases. To make an assumption, this tag seems to be a customized tag or selector that wraps around something more intricate that magically renders the whole application. As we gradually go through this section, you will get closer to understanding `app-root`'s true nature.

```html
<!--src/index.html-->

<!--other stuff-->
<body>
  <app-root></app-root>
</body>
<!--other stuff-->
```

Next, we'll investigate `main.ts`, which is the entry point of this Angular application. It's a typical TypeScript module file, initiated by ES6 import statements that expose needed utilities to the entire file. There is nothing special about this file; these are just some functions being called to bootstrap our application.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
/* src/main.ts */

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

Another file worth investigating is `app/app.module.ts`: At first glance, you would have the impression that this module file declares and exports an Angular-specific class component. You may get that idea when seeing `@Component`. This is the syntax of a decorator in TypeScript. In this scenario, the `Component` decorator acts as a factory adding more configuration into the class being defined below it — but here, the decorator is actually `NgModule`, which makes this class an `NgModule`.

> You can learn about *decorators* from [this TS official tutorial link](https://www.typescriptlang.org/docs/handbook/decorators.html).

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
/* src/app/app.module.ts */

import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

At this point, you might be confused between the concepts of a TypeScript module and `NgModule`. A TS module, in the simplest sense, is a set of functions, variables, and so on being logically grouped together. A TS module can import other TS modules, and it can also "export" selected functions, variables, and so on for other modules to consume. On the other hand, `NgModule` is specifically a building block of an Angular application, each of them performing a distinct functionality. As you can see, the configuration object of `NgModule` inside `app.module.ts` has an `imports` property to describe which other `NgModule` instances the root `AppModule` needs to rely upon.

> At the time of writing, there are heated discussions (for instance, [this one](https://github.com/angular/angular/issues/37904)) on whether `NgModule` should be deprecated in future Angular releases.

Back to the `AppModule` class: its `declarations` property is an array currently having only one element named `AppComponent` imported from `app.component.ts`. Conventionally, every element placed inside this array has to be a *declarable*, which can be either a *component*, a *directive*, or a *pipe*. *Directives* and *pipes* will be topics for other posts. For the scope of this tutorial, we will only study *components* hands-on as we attempt to create a new component in the next section. Normally, most of the time we develop an Angular application is spent writing components.

> Actually, a *component* is also a type of *directive*. But for the sake of simplicity, we shouldn't dive deep into their interrelationship yet, and instead, we should think of a component as its own kind.

```typescript
/* src/app/app.component.ts */

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

For each component defined in Angular, there will be a corresponding *view*, which is defined by [Angular official documentation](https://angular.io/guide/architecture) as "sets of screen elements that Angular can choose among and modify according to your program logic and data". If developing an Angular application is like building a house, then `NgModule`s can be comparable to systems that can be constructed independently from each other — floor framing system, electrical system, and so on. Each of these systems needs to be made up of multiple components. Analogously, the view of an Angular application is a composition of well-integrated components — header, navigation bar, content area, sidebar, footer, and so on. Each of these components can also be made up of other micro-components.

`AppComponent` is special because it's the root component of our application. As you can see inside `app.component.ts`, the decorator `Component` specifies what HTML and styling template to use to render this component's view through `templateUrl` and `styleUrls` config values respectively, and its view tag name through the `selector` config value.

Do you remember the assumption we made early in this tutorial about the `app-root` XML-like tag? Before moving on to the next section, please be sure that you can figure out for yourself what this tag really is. When you're ready, let's try creating a new Angular component!

## Creating a New Angular Component

Placing the to-be-created class inside `AppComponent` is possible, but doing so will result in an overlong code file which is horrible to read and maintain. Hence, we'll create a `hello.component.ts` file and place it in the same folder as `app.component.ts`.

```typescript
/* src/app/hello.component.ts */

export class HelloComponent {}
```

In order to be recognized as a valid Angular component, this class needs to be "empowered" by the `Component` decorator as follows.

```typescript
/* src/app/hello.component.ts */

import { Component } from "@angular/core";
@Component({
  selector: "app-hello",
  template: ` <h2>Hello there!</h2> `,
})
export class HelloComponent {}
```

Could this component be used interchangeably with `AppComponent`? Let's experiment by appending this line into the `app.component.html` file, and then save it and run the application using the `ng serve` command as demonstrated in the setup section above:

```html
<app-hello></app-hello>
```

If your intuition told you that maybe there is something seriously wrong, then it's right: the app crashed and you're presented with this error message:

```zsh
error NG8001: 'app-hello' is not a known element:

1. If `app-hello` is an Angular component, then verify that it is part of this module.
2. If `app-hello` is a Web Component then add 'CUSTOM_ELEMENTS_SCHEMA' to the '@NgModule.schemas' of this component to suppress this message.
```

We made this mistake by assuming that `HelloComponent` is "smart" enough to automatically know which `NgModule` it belongs to. It's like placing a new employee inside your office and letting them figure out for themselves who their manager is and where their office is. To fix this, we have to "attach" this component into `AppModule`, which is the only `NgModule` at the moment.

But where to "attach" it? I hinted at the answer in the first section, in the part where I introduced *declarables*. You don't have to memorize everything; instead, let your IDE refresh your memory by hovering your cursor over the `declarations` keyword inside `app.module.ts`:

> **The set of components, directives, and pipes (declarables) that belong to this module.**

> `@usageNotes` — The set of selectors that are available to a template include those declared here, and those that are exported from imported NgModules. Declarables must belong to exactly one module. The compiler emits an error if you try to declare the same class in more than one module. Be careful not to declare a class that is imported from another module.

I'll leave the properly edited `app.module.ts` below. Before taking a peek, please stop reading for a minute and try to come up with the answer on your own.

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
/* keep the original import statements and add below import statement */
import { HelloComponent } from './hello.component';

@NgModule({
  declarations: [
    AppComponent,
    HelloComponent
  ],
  /* keep the other stuff intact */
})
export class AppModule { }
```

The app should be running as expected now. You see, creating a component manually isn't so hard. By "manually", I mean that you can also achieve the same goal of creating `HelloComponent` by using this Angular CLI command:

```shell
ng generate component hello
```

When I was introduced to this, I found myself asking: "What kind of dark magic is that?" The trick is that Angular has a naming convention for generating a new component using that CLI command: if you order a component `${name}` to be initiated, the exported class will be named `${name.charAt(0).toUpperCase() + name.slice(1)}Component` and its CSS selector will be named `app-${name}`.

That's enough magic for today! In the next article, we'll introduce you to **data binding**!

## References

- [https://angular.io/guide/setup-local](https://angular.io/guide/setup-local)
- [https://angular.io/tutorial/toh-pt0](https://angular.io/tutorial/toh-pt0)
- [https://angular.io/guide/architecture](https://angular.io/guide/architecture)
- [https://angular.io/guide/architecture-modules](https://angular.io/guide/architecture-modules)
- [https://angular.io/guide/architecture-components](https://angular.io/guide/architecture-components)

## Author

Tiep Phan — https://github.com/tieppt

*Translated from the original Vietnamese as part of the angular-concepts project.*

---
roadmap_node: "jira-clone"
title: "Jira Clone Tutorial — Project Setup and Layout"
file: "_orphans/jira-clone.md"
source_days: [40, 41]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Jira Clone Tutorial — Project Setup and Layout

This is the first installment in a series on the [Jira clone](https://jira.trungk18.com/) app the Angular Vietnam community supported. We'll focus on interesting, complex pieces (drag-and-drop, rich text) rather than line-by-line coverage — the original build took more than two weeks.

## What is the Jira clone?

An Angular side project that recreates a simplified Atlassian Jira for learning and the 100 Days of Angular series.

- Live demo: [jira.trungk18.com](https://jira.trungk18.com/)
- Source: [trungk18/jira-clone-angular](https://github.com/trungk18/jira-clone-angular)

![Jira clone built with Angular 9 and Akita](https://github.com/trungk18/jira-clone-angular/raw/master/frontend/src/assets/img/jira-clone-angular-demo-trungk18.gif) <!-- TODO: asset -->

### Tech stack

![Tech logos](https://github.com/trungk18/jira-clone-angular/raw/master/frontend/src/assets/img/jira-clone-tech-stack.png) <!-- TODO: asset -->

- [Angular CLI](https://cli.angular.io/)
- [Akita](https://datorama.github.io/akita/) state management
- [NestJS](https://nestjs.com/)
- UI: [TailwindCSS](https://tailwindcss.com/), Angular CDK [drag and drop](https://material.angular.io/cdk/drag-drop/overview), [ng-zorro](https://ng.ant.design/docs/introduce/en), [ngx-quill](https://github.com/KillerCodeMonkey/ngx-quill)
- [Netlify](https://www.netlify.com/), [Heroku](https://www.heroku.com/)

## Prerequisites

- Angular basics: interpolation, components, directives, [reactive forms](https://angular.io/guide/reactive-forms), [router](https://angular.io/guide/router), lazy loading, [@Input / @Output](https://angular.io/guide/component-interaction)
- TypeScript: [interface](https://www.typescriptlang.org/docs/handbook/interfaces.html), [class](https://www.typescriptlang.org/docs/handbook/classes.html)
- `npm` or `yarn`, RxJS (`map`, `combineLatest`, …), Git, command line

### Why command line skills?

Modern frontend tooling is CLI-driven (`npm i jquery` vs downloading ZIPs). If you're new to the terminal, read a [command-line tutorial](https://www.learnenough.com/command-line-tutorial/basics) first.

## Before coding

Break work into a task list ([Notion board](https://www.notion.so/trungk18/Angular-Jira-clone-Phase-1-79d3205e26024357a75ebfc00aba558e)) — groundwork, backend, frontend (layout, breadcrumb, kanban, filters, issue detail, inline edit, modals, search).

## Part 1: GitHub repo and Angular app

### Why source control?

Use GitHub, Gitlab, or Bitbucket — **version control is mandatory**. Without commits you can't rewind when experiments break.

### Create a GitHub repository

![Angular Jira Clone Tutorial Part 01](./assets/jira01/01.png) <!-- TODO: asset -->

- Name: e.g. `jira-angular-clone`
- Description optional
- Private until ready to publish
- Initialize README, Node `.gitignore`, MIT license

### Clone locally

```bash
git clone your_repo_url
```

![Angular Jira Clone Tutorial Part 01](./assets/jira01/02.png) <!-- TODO: asset -->

### Install Angular CLI

```bash
npm install -g @angular/cli
ng --version
```

![Angular Jira Clone Tutorial Part 01](./assets/jira01/03.png) <!-- TODO: asset -->
![Angular Jira Clone Tutorial Part 01](./assets/jira01/04.png) <!-- TODO: asset -->

### `npm init` for root `package.json`

Monorepo-style root with future `frontend` and `api` folders:

```bash
npm init
```

![Angular Jira Clone Tutorial Part 01](./assets/jira01/05.png) <!-- TODO: asset -->

### Create the Angular app

```bash
ng new frontend --skipTests=true
```

Enable routing and SCSS. Commit when done.

![Angular Jira Clone Tutorial Part 01](./assets/jira01/06.png) <!-- TODO: asset -->
![Angular Jira Clone Tutorial Part 01](./assets/jira01/07.png) <!-- TODO: asset -->

## Configure TailwindCSS

Detailed guide: [Configure Tailwind CSS with Angular (Vietnamese)](https://trungk18.com/experience/configure-tailwind-css-with-angular/)

Create branch `tailwind-configuration` before merging incomplete config:

```bash
git checkout -b tailwind-configuration
```

![Angular Jira Clone Tutorial Part 01](./assets/jira01/08.png) <!-- TODO: asset -->

Install packages:

```bash
npm i tailwindcss postcss-scss postcss-import postcss-loader @angular-builders/custom-webpack -D
```

Import in `style.scss`:

```scss
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';
```

`webpack.config.js` — use `postcss-loader@^3` or `^4` syntax per [postcss-loader docs](https://webpack.js.org/loaders/postcss-loader/).

Point `angular.json` at `@angular-builders/custom-webpack` for `build` and `serve`.

Test `@apply` and commit.

![Angular Jira Clone Tutorial Part 01](./assets/jira01/09.png) <!-- TODO: asset -->
![Angular Jira Clone Tutorial Part 01](./assets/jira01/10.png) <!-- TODO: asset -->
![Angular Jira Clone Tutorial Part 01](./assets/jira01/11.png) <!-- TODO: asset -->

## Prettier

Install [Prettier for VS Code](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) and add `.prettierrc`.

![Angular Jira Clone Tutorial Part 01](./assets/jira01/12.png) <!-- TODO: asset -->

## Root build scripts

Optional root `package.json` scripts for deploy workflows.

![Angular Jira Clone Tutorial Part 01](./assets/jira01/13.png) <!-- TODO: asset -->

---

## Part 2: Layout with Flexbox and TailwindCSS

Checkout [tailwind-configuration](https://github.com/trungk18/jira-clone-angular/tree/tailwind-configuration) before following below.

### Navigation section

Main areas:

- **Left nav** — logo, icons, avatar, help
- **Collapsible sidebar** — settings, board links
- **Resizer** — toggle sidebar
- **Content** — board or forms

![Angular Jira Clone Tutorial Part 02](./assets/jira02/01.png) <!-- TODO: asset -->

Horizontal flex layout:

```html
<div class="navigation">
  <div class="flex flex-row overflow-hidden h-full">
    <app-navbar-left></app-navbar-left>
    <app-sidebar [expanded]="expanded"></app-sidebar>
  </div>
  <app-resizer (click)="toggle()" [expanded]="expanded"></app-resizer>
</div>
```

```css
.navigation {
  display: flex;
}
```

### 1. Custom Tailwind spacing

Navbar width `64px`, sidebar `240px` — extend [tailwind.config.js](https://github.com/trungk18/jira-clone-angular/blob/master/frontend/tailwind.config.js) for `w-navbarLeft` and `w-sidebar`.

![Angular Jira Clone Tutorial Part 02](./assets/jira02/02.png) <!-- TODO: asset -->

See [Tailwind spacing scale](https://tailwindcss.com/docs/customizing-spacing).

### 2. Left navigation

```css
.navbarLeft-content {
  @apply h-screen w-navbarLeft pt-6 pb-5 flex flex-col bg-primary flex-shrink-0;
}

.logoLink {
  @apply relative pb-2 flex items-center justify-center;
}
```

![Angular Jira Clone Tutorial Part 02](./assets/jira02/03.png) <!-- TODO: asset -->

### 3. Sidebar

Same flex approach; challenge: **scrollable content** when space is tight.

![Angular Jira Clone Tutorial Part 02](./assets/jira02/04.gif) <!-- TODO: asset -->

### 4. Scrollable container with dynamic height

Read [Scrollable Containers with Dynamic Height using Flexbox](https://codepen.io/stephenbunch/pen/KWBNVo) — set height on the outermost flex column chain so an inner child can scroll.

Applied from `app-component` down to the scroll region:

![Angular Jira Clone Tutorial Part 02](./assets/jira02/05.png) <!-- TODO: asset -->

### 5. Resizer

```ts
export class ResizerComponent implements OnInit {
  @Input() expanded: boolean;

  get icon() {
    return this.expanded ? 'chevron-left' : 'chevron-right';
  }
  constructor() {}

  ngOnInit(): void {}
}
```

Auto-collapse sidebar below 1024px with [window.matchMedia](https://developer.mozilla.org/en-US/docs/Web/API/Window/matchMedia):

```ts
handleResize() {
  const match = window.matchMedia('(min-width: 1024px)');
  match.addEventListener('change', (e) => {
    console.log(e)
    this.expanded = e.matches;
  });
}
```

Add `removeListener` in `ngOnDestroy` in production code.

![Angular Jira Clone Tutorial Part 02](./assets/jira02/06.gif) <!-- TODO: asset -->

### Wire the shell

```html
<div class="w-full h-full flex">
  <app-navigation
    [expanded]="expanded"
    (manualToggle)="manualToggle()"
  ></app-navigation>
  <div id="content">
    <router-outlet></router-outlet>
  </div>
</div>
<svg-definitions></svg-definitions>
```

`ProjectModule` routes:

```ts
const routes: Routes = [
  {
    path: '',
    component: ProjectComponent,
    children: [
      {
        path: 'board',
        component: BoardComponent,
      },
      {
        path: 'settings',
        component: SettingsComponent,
      },
      {
        path: `issue/:${ProjectConst.IssueId}`,
        component: FullIssueDetailComponent,
      },
      {
        path: '',
        redirectTo: 'board',
        pathMatch: 'full',
      },
    ],
  },
];
```

## Summary

Part 1 covered repo setup, Angular CLI, Tailwind, and Prettier. Part 2 built the flex-based shell with collapsible sidebar and scrollable regions — often the slowest part of a real app.

> This series was originally written years ago; some steps may be outdated — open a PR if you spot issues.

## Source code

- https://github.com/trungk18/jira-clone-angular/tree/tailwind-configuration
- https://github.com/trungk18/jira-clone-angular/tree/leftnav-sidebar

## Author

Trung Vo — https://github.com/trungk18

*Translated from the original Vietnamese as part of the angular-concepts project.*

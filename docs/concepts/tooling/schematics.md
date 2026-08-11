---
roadmap_node: "schematics"
title: "Schematics"
file: "tooling/schematics.md"
source_days: []
original_authors: []
status:
  translated: false
  upgraded: true
  reviewed: false
angular_when_written: null
angular_baseline: "22"
---

> **Modern Angular only**
> No equivalent exists in the original 100 Days series.
> Written fresh for Angular v22.

# Schematics

> **Lead with this:** A schematic is a code generator — a TypeScript function
> that reads and writes files through a virtual file system, so Angular can
> run it safely, preview what would change, and roll it back if it fails.
> When you run `ng generate component`, a schematic does the work.

## What it is

Every `ng generate` command, every `ng add`, every `ng update` migration runs
a **schematic** under the hood. A schematic is:

1. A TypeScript function (the **rule factory**) that takes an options object
   and returns a **Rule**
2. A **Rule** is a function `(tree: Tree, context: SchematicContext) => Tree`
3. A **Tree** is an in-memory virtual representation of the project's file system

Changes happen to the Tree first — not the real disk. Only when the schematic
finishes successfully does Angular commit the Tree's changes to disk. This is
what enables `ng generate --dry-run`: the Tree runs fully, Angular shows you
what would change, then discards it.

**When to write your own schematics:**

| Scenario | What a schematic gives you |
| --- | --- |
| Consistent feature scaffolding | One command generates module + component + service + route |
| Library `ng add` support | Users run `ng add my-lib`; schematic configures the project automatically |
| Enforced team conventions | All generated code follows your team's patterns, not Angular's defaults |
| Automated migrations | `ng update` applies breaking-change transformations to existing code |
| Reduced review overhead | Generated code is correct by construction, not by review |

## How it works under the hood

### Old approach — manual boilerplate and copy-paste

Without schematics, adding a new feature meant:

```
1. mkdir src/app/feature-name
2. create feature.component.ts         (from memory or a previous component)
3. create feature.component.html
4. create feature.component.scss
5. create feature.service.ts
6. Manually update app.routes.ts       (forgot? broken navigation)
7. Manually update app.config.ts       (forgot to register the service? runtime error)
8. 15 minutes, 3 files to copy-paste, 2 files to manually edit, 1 typo
```

The mistakes happen in steps 6–8 — the manual edits of existing files.
Forgetting to add a route, or adding it to the wrong place in the routes
array, produces a runtime error that isn't caught until the app runs.
Copy-pasted boilerplate also drifts: if the team's base service pattern
evolves, old copy-paste survives in the codebase.

### How schematics solve it

A schematic operates on a **virtual file system** — the `Tree`. The Tree is
an in-memory overlay on the real file system: reads come from disk, writes
accumulate in memory. The schematic does its work on the Tree, and only if
everything succeeds does Angular apply the changes atomically to disk.

```
ng generate feature my-feature
            │
            ▼
Angular loads the schematic's factory function with options = { name: 'my-feature' }
            │
            ▼
Factory returns a Rule — a function (tree, context) => tree
            │
            ▼
Rule runs against the virtual Tree:
  • apply(url('./files'), [template(options), move(path)]) → new files in Tree
  • tree.read('src/app/app.routes.ts') → reads existing file
  • tree.overwrite(routesPath, updatedContent) → writes to Tree (not disk yet)
            │
            ▼
All rules succeed → Angular commits Tree changes to real disk atomically
(If any rule throws → no disk changes, Tree discarded)
```

### Four core types

```typescript
// A Rule transforms a Tree into a new Tree
type Rule = (tree: Tree, context: SchematicContext) => Tree | Observable<Tree> | Rule | void;

// Tree — virtual file system
interface Tree {
  exists(path: string): boolean;
  read(path: string): Buffer | null;
  create(path: string, content: string | Buffer): void;
  overwrite(path: string, content: string | Buffer): void;
  delete(path: string): void;
  rename(from: string, to: string): void;
}

// SchematicContext — logger, task scheduling, engine access
interface SchematicContext {
  logger: logging.LoggerApi;   // .info(), .warn(), .error()
  addTask(task: TaskConfigurationGenerator): TaskId;
}
```

## Basic usage

### 1 — Project setup

```bash
npm install -g @angular-devkit/schematics-cli
schematics blank --name=my-schematics
cd my-schematics
npm install
```

Structure created:

```
my-schematics/
├── src/
│   └── my-schematics/
│       └── index.ts           ← rule factory
├── collection.json             ← schematic registry
├── package.json
└── tsconfig.json
```

### 2 — collection.json

Declares which schematics this package contains:

```json
{
  "$schema": "../node_modules/@angular-devkit/schematics/collection-schema.json",
  "schematics": {
    "my-schematics": {
      "description": "A custom schematic.",
      "factory": "./my-schematics/index#mySchematics",
      "schema": "./my-schematics/schema.json"
    }
  }
}
```

### 3 — schema.json

Declares the options your schematic accepts. The Angular CLI uses this to
prompt for missing options and validate provided ones:

```json
{
  "$schema": "http://json-schema.org/schema",
  "type": "object",
  "title": "Feature Schematic",
  "properties": {
    "name": {
      "type": "string",
      "description": "The feature name (used to name generated files)",
      "$default": { "$source": "argv", "index": 0 }
    },
    "path": {
      "type": "string",
      "description": "The path to create the feature in",
      "default": "src/app",
      "format": "path"
    },
    "withService": {
      "type": "boolean",
      "description": "Whether to generate a service alongside the component",
      "default": true
    }
  },
  "required": ["name"]
}
```

### 4 — The rule factory (index.ts)

The heart of every schematic. A factory function takes typed options and
returns a Rule:

```typescript
// src/my-schematics/index.ts
import {
  Rule, SchematicContext, Tree,
  apply, chain, mergeWith, move, template, url,
} from '@angular-devkit/schematics';
import { strings } from '@angular-devkit/core';
import { Schema } from './schema';

export function mySchematics(options: Schema): Rule {
  return (tree: Tree, context: SchematicContext) => {
    context.logger.info(`Generating feature: ${options.name}`);

    // Build file source from template files in ./files directory
    const templateSource = apply(url('./files'), [
      template({
        ...options,               // spread options for use in templates
        ...strings,               // dasherize, classify, camelize, capitalize
      }),
      move(options.path),         // write to target path
    ]);

    // Chain multiple rules together
    return chain([
      mergeWith(templateSource),
    ])(tree, context);
  };
}
```

### 5 — Template files

Template files live in a `files/` directory alongside `index.ts`. File names
and content use EJS-style expressions:

```
src/my-schematics/files/
└── __name@dasherize__/
    ├── __name@dasherize__.component.ts.template
    ├── __name@dasherize__.component.html.template
    └── __name@dasherize__.service.ts.template
```

The `__name@dasherize__` in file/folder names applies the `dasherize`
transform to the `name` option. For `name = 'UserProfile'`:

```
__name@dasherize__ → user-profile
__name@classify__  → UserProfile
__name@camelize__  → userProfile
```

Template content (EJS syntax):

```typescript
// __name@dasherize__.component.ts.template
import { Component, inject } from '@angular/core';
import { <%= classify(name) %>Service } from './<%= dasherize(name) %>.service';

@Component({
  selector: 'app-<%= dasherize(name) %>',
  standalone: true,
  templateUrl: './<%= dasherize(name) %>.component.html',
})
export class <%= classify(name) %>Component {
  private service = inject(<%= classify(name) %>Service);
}
```

With `name = 'ProductList'`, this generates:

```typescript
import { Component, inject } from '@angular/core';
import { ProductListService } from './product-list.service';

@Component({
  selector: 'app-product-list',
  standalone: true,
  templateUrl: './product-list.component.html',
})
export class ProductListComponent {
  private service = inject(ProductListService);
}
```

### 6 — Build and test

```bash
npm run build

# Test locally without installing to a project
schematics .:my-schematics --name=product-list --dry-run

# Apply for real
schematics .:my-schematics --name=product-list

# Test inside an Angular project (link the package first)
npm link
cd ../my-angular-project
npm link my-schematics
ng generate my-schematics:my-schematics product-list
```

## Real-world patterns

### Pattern 1 — Feature scaffolder with route registration

A schematic that generates a full feature (component + service + route entry)
and modifies `app.routes.ts` to register the new route:

```typescript
import {
  Rule, SchematicContext, Tree,
  apply, chain, mergeWith, move, template, url, noop,
} from '@angular-devkit/schematics';
import { strings } from '@angular-devkit/core';

export function feature(options: FeatureSchema): Rule {
  return chain([
    // Rule 1 — generate files from templates
    mergeWith(
      apply(url('./files'), [
        template({ ...options, ...strings }),
        move(options.path),
      ])
    ),

    // Rule 2 — add route to app.routes.ts
    addRouteToRoutes(options),
  ]);
}

function addRouteToRoutes(options: FeatureSchema): Rule {
  return (tree: Tree, context: SchematicContext) => {
    const routesPath = 'src/app/app.routes.ts';
    const buffer = tree.read(routesPath);

    if (!buffer) {
      context.logger.warn(`Could not find ${routesPath}. Skipping route registration.`);
      return tree;
    }

    const content = buffer.toString('utf-8');
    const dasherized = strings.dasherize(options.name);
    const classified = strings.classify(options.name);

    // Build the new route entry
    const newRoute = `  {
    path: '${dasherized}',
    loadComponent: () => import('./${dasherized}/${dasherized}.component')
      .then(m => m.${classified}Component),
  },`;

    // Insert before the closing bracket of the routes array
    const updated = content.replace(
      '];',
      `${newRoute}\n];`
    );

    tree.overwrite(routesPath, updated);
    context.logger.info(`✔ Added route /${dasherized} to app.routes.ts`);
    return tree;
  };
}
```

### Pattern 2 — ng add schematic for a library

When users run `ng add my-library`, Angular CLI looks for a schematic named
`ng-add` in the library's `package.json`'s `schematics` field. This schematic
sets up everything the library needs:

```json
// my-library/package.json
{
  "schematics": "./schematics/collection.json"
}
```

```json
// schematics/collection.json
{
  "schematics": {
    "ng-add": {
      "description": "Add my-library to an Angular project",
      "factory": "./ng-add/index#ngAdd"
    }
  }
}
```

```typescript
// schematics/ng-add/index.ts
import {
  Rule, SchematicContext, Tree, chain,
} from '@angular-devkit/schematics';
import { NodePackageInstallTask } from '@angular-devkit/schematics/tasks';
import { addRootProvider } from '@schematics/angular/utility';

export function ngAdd(): Rule {
  return chain([
    // Rule 1 — add the provider to app.config.ts
    addRootProvider('my-library', ({ code, external }) =>
      code`${external('provideMyLibrary', 'my-library')}()`
    ),

    // Rule 2 — install npm packages (runs after all file changes)
    (_tree: Tree, context: SchematicContext) => {
      context.addTask(new NodePackageInstallTask());
      context.logger.info('Installing dependencies...');
    },
  ]);
}
```

## Common mistakes

### Mistake 1 — Writing to disk directly instead of using Tree

Schematics must use the `Tree` API — writing to disk directly (`fs.writeFileSync`)
bypasses the virtual file system, breaks dry-run, and prevents rollback:

```typescript
// ❌ Direct filesystem write — breaks dry-run and rollback
import * as fs from 'fs';
export function mySchematic(): Rule {
  return (tree: Tree) => {
    fs.writeFileSync('src/app/new.ts', content);  // always writes, even on dry-run
    return tree;
  };
}

// ✅ Write through the Tree — respects dry-run and is atomic
export function mySchematic(): Rule {
  return (tree: Tree) => {
    tree.create('src/app/new.ts', content);
    return tree;
  };
}
```

### Mistake 2 — Using console.log instead of context.logger

`console.log` output doesn't respect the Angular CLI's logging level and
doesn't appear correctly in the formatted CLI output:

```typescript
// ❌ console.log — bypasses CLI formatting
export function mySchematic(): Rule {
  return (tree: Tree, context: SchematicContext) => {
    console.log('Done!');   // raw output, no formatting
    return tree;
  };
}

// ✅ context.logger — properly formatted CLI output
export function mySchematic(): Rule {
  return (tree: Tree, context: SchematicContext) => {
    context.logger.info('✔ Done!');    // info (green checkmark)
    context.logger.warn('⚠ Check config');  // warning (yellow)
    context.logger.error('✗ Failed');  // error (red)
    return tree;
  };
}
```

### Mistake 3 — Forgetting to build before running locally

Schematics are TypeScript files that must be compiled to JavaScript before
they run. Forgetting `npm run build` after editing `index.ts` means you're
running stale code:

```bash
# ❌ Edit index.ts, then immediately run — stale JS
schematics .:my-schematic --dry-run

# ✅ Always build first (or use watch mode during development)
npm run build
schematics .:my-schematic --dry-run

# Better: use watch mode while developing
npm run watch &
schematics .:my-schematic --dry-run
```

### Mistake 4 — Overwriting without reading first

`tree.overwrite()` replaces the file's entire content. If you want to add
to an existing file, read it first and then write the modified version:

```typescript
// ❌ Overwrites the entire file with just the new import line
tree.overwrite('src/app/app.config.ts', `import { myProvider } from 'my-lib';`);

// ✅ Read existing content, modify, overwrite with modified version
const existing = tree.read('src/app/app.config.ts')?.toString('utf-8') ?? '';
const modified = existing.replace(
  'providers: [',
  'providers: [\n    myProvider(),'
);
tree.overwrite('src/app/app.config.ts', modified);
```

## How this evolved

> - **Angular CLI 1.0 (2017):** Schematics introduced as the engine behind
>   `ng generate` and `ng new`. Closed source initially, using an internal
>   fork of the `@angular-devkit/schematics` package.
>
> - **Angular CLI 6 (2018):** Schematics opened to the public. `ng add` and
>   `ng update` commands added — both powered by schematics. Library authors
>   could now ship `ng-add` schematics to automate setup.
>
> - **Angular CLI 8 (2019):** Migration schematics for `ng update` stabilized.
>   `@schematics/angular` package opened — the source of Angular's own
>   `ng generate component/service/module` schematics, now available for
>   community schematics to extend via `externalSchematic()`.
>
> - **Angular CLI 14–15 (2022):** Standalone component support added to built-in
>   schematics — `ng generate component --standalone`. `addRootProvider` utility
>   introduced for `ng-add` schematics to cleanly add providers to
>   `app.config.ts` without string munging.
>
> - **Angular 22 (now):** Schematics API is stable and unchanged. The main
>   evolution is that standalone-first templates are the default output of
>   `@schematics/angular`. Custom schematics should generate standalone
>   components by default and avoid generating NgModules.

## See also

- [Builders](./builders.md) — the companion system: schematics generate code,
  builders execute tasks (compile, test, serve)
- [Nx](./nx.md) — Nx generators are built on the same schematics API; Nx's
  tooling adds dependency-awareness and caching on top
- [Official docs — Schematics overview](https://angular.dev/tools/cli/schematics)
- [Official docs — Authoring schematics](https://angular.dev/tools/cli/schematics-authoring)
- [@angular-devkit/schematics API](https://www.npmjs.com/package/@angular-devkit/schematics)

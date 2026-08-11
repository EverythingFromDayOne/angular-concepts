---
roadmap_node: "builders"
title: "Builders"
file: "tooling/builders.md"
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

# Builders

> **Lead with this:** Builders are what the Angular CLI runs when you type
> `ng build`, `ng test`, or `ng serve` — typed, configurable, schema-validated
> task executors that pipe progress back to the CLI. Understanding builders
> lets you configure the built-in ones precisely, and write your own when no
> built-in does the job.

## What it is

Every Angular CLI command that does real work delegates to a **builder**:

```
ng build  →  finds the "build" target in angular.json
           →  loads the builder named in that target's "builder" field
           →  passes validated options to the builder function
           →  streams BuilderOutput events back to the CLI
```

A builder is a TypeScript function that takes a validated options object and a
`BuilderContext`, performs a task, and returns either a `Promise<BuilderOutput>`
(one-shot) or an `Observable<BuilderOutput>` (watch mode — emits repeatedly).

**Builders vs Schematics:** both are Angular CLI extension points, but they
do different things. Schematics modify the project structure (generate files,
update config). Builders execute tasks at runtime (compile, bundle, test, serve,
deploy). Schematics run once and finish; builders can be long-running.

## How it works under the hood

### Old approach — npm scripts and manual orchestration

Before builders (Angular CLI < 6), build tooling was configured with npm
scripts and raw tool invocations:

```json
// package.json — pre-Architect era
{
  "scripts": {
    "build": "tsc && cp -r src/assets dist/assets",
    "build:prod": "tsc -p tsconfig.prod.json && uglifyjs ...",
    "test": "karma start karma.conf.js",
    "lint": "tslint src/**/*.ts"
  }
}
```

Problems at scale: no typed options, no schema validation, no progress
reporting to the CLI, no configuration inheritance (dev vs prod must be
entirely separate scripts), no way to invoke one task from another in a
structured way. Changing build parameters meant editing shell scripts,
string-concatenating flags, and hoping nobody broke the argument order.

### How Architect solves it

The **Architect framework** sits between the CLI command and the actual tool
(webpack, esbuild, Vitest, etc.). The flow:

```
ng build my-app --configuration=production
         │
         ▼
Architect reads angular.json:
  project "my-app"
  → target "build"
  → builder "@angular/build:application"
  → options: { outputPath, index, browser, ... }
  → configurations.production: { optimization: true, sourceMap: false, ... }
         │
         ▼
Architect merges: base options + production config overrides
Validates merged options against the builder's schema.json
         │
         ▼
Architect loads the builder module, calls:
  builderFn(mergedOptions, context)
         │
         ▼
Builder runs (esbuild bundles, emits progress via context.reportProgress)
Builder returns Promise<BuilderOutput> → { success: true }
         │
         ▼
CLI reports success / failure
```

The key benefits: typed options, validation before execution, configuration
inheritance (`production` only specifies what changes from the base), progress
streaming, and the ability for one builder to invoke another via
`context.scheduleTarget()`.

### The v22 builder landscape — from Webpack to esbuild

This is the other major mechanism shift worth understanding. Angular's built-in
builders have changed significantly since Angular 17:

**Old builders** (still works, legacy):

| Command | Old builder |
| --- | --- |
| `ng build` | `@angular-devkit/build-angular:browser` (Webpack) |
| `ng serve` | `@angular-devkit/build-angular:dev-server` (webpack-dev-server) |
| `ng test` | `@angular-devkit/build-angular:karma` (Karma + Webpack) |

**New builders** (Angular 17+, default in v22):

| Command | New builder |
| --- | --- |
| `ng build` | `@angular/build:application` (esbuild) |
| `ng serve` | `@angular/build:dev-server` (Vite) |
| `ng test` | `@angular/build:unit-test` (Vitest) |
| `ng extract-i18n` | `@angular/build:extract-i18n` |

The switch from Webpack to esbuild cut build times by 2–5x for most
applications. Vite's dev server uses native ES modules — no full bundle on
startup, instant HMR. These are not configuration changes; they are entirely
different builder packages doing the same job faster.

If your `angular.json` still references `@angular-devkit/build-angular:browser`,
run `ng update` — it migrates to `@angular/build:application` automatically.

## Reading and configuring angular.json targets

Understanding the `angular.json` structure unlocks fine-grained control over
every CLI command:

```json
// angular.json
{
  "projects": {
    "my-app": {
      "architect": {
        "build": {
          "builder": "@angular/build:application",
          "options": {
            // Merged into every configuration — defaults
            "outputPath": "dist/my-app",
            "index": "src/index.html",
            "browser": "src/main.ts",
            "polyfills": ["zone.js"],
            "tsConfig": "tsconfig.app.json",
            "assets": [
              { "glob": "**/*", "input": "public" }
            ],
            "styles": ["src/styles.scss"],
            "scripts": []
          },
          "configurations": {
            "production": {
              // Only these keys override the base options above
              "budgets": [
                { "type": "initial", "maximumWarning": "500kB", "maximumError": "1MB" }
              ],
              "outputHashing": "all",
              "optimization": true,
              "sourceMap": false,
              "namedChunks": false
            },
            "development": {
              "optimization": false,
              "extractLicenses": false,
              "sourceMap": true,
              "namedChunks": true
            },
            "staging": {
              // Extend production, then override specific keys
              "optimization": true,
              "sourceMap": true    // source maps in staging but not production
            }
          },
          "defaultConfiguration": "production"
        },
        "serve": {
          "builder": "@angular/build:dev-server",
          "options": {
            "buildTarget": "my-app:build"
          },
          "configurations": {
            "production": { "buildTarget": "my-app:build:production" },
            "development": { "buildTarget": "my-app:build:development" }
          },
          "defaultConfiguration": "development"
        },
        "test": {
          "builder": "@angular/build:unit-test",
          "options": {
            "buildTarget": "my-app:build:development",
            "tsConfig": "tsconfig.spec.json"
          }
        },
        "extract-i18n": {
          "builder": "@angular/build:extract-i18n",
          "options": {
            "buildTarget": "my-app:build"
          }
        }
      }
    }
  }
}
```

Run any target directly:

```bash
ng run my-app:build                   # uses defaultConfiguration
ng run my-app:build:production        # explicit configuration
ng run my-app:build:staging           # custom configuration
ng build --configuration=staging     # shorthand for ng run my-app:build:staging
```

## Writing a custom builder

### When to write one

Custom builders make sense for:
- Deploying to a specific hosting provider (`ng run my-app:deploy`)
- Post-build steps (copying files, sending Slack notifications, invalidating CDN cache)
- Running non-Angular tools that have Angular-aware options (custom linters, doc generators)
- Orchestrating multiple targets in a defined order with dependency awareness

### Project structure

```
my-builders/
├── src/
│   └── deploy/
│       ├── index.ts          ← builder implementation
│       └── schema.json       ← options schema
├── builders.json             ← builder registry
├── package.json              ← includes "builders": "./builders.json"
└── tsconfig.json
```

### 1 — builders.json

```json
{
  "$schema": "@angular-devkit/architect/src/builders-schema.json",
  "builders": {
    "deploy": {
      "implementation": "./src/deploy",
      "schema": "./src/deploy/schema.json",
      "description": "Deploy the built app to S3"
    }
  }
}
```

```json
// package.json
{
  "name": "my-builders",
  "builders": "./builders.json"
}
```

### 2 — schema.json

```json
{
  "$schema": "http://json-schema.org/schema",
  "type": "object",
  "title": "Deploy Builder",
  "properties": {
    "bucket": {
      "type": "string",
      "description": "The S3 bucket name to deploy to"
    },
    "region": {
      "type": "string",
      "description": "AWS region",
      "default": "us-east-1"
    },
    "distFolder": {
      "type": "string",
      "description": "Path to the built app (relative to workspace root)",
      "default": "dist/my-app/browser"
    }
  },
  "required": ["bucket"]
}
```

### 3 — Builder implementation

```typescript
// src/deploy/index.ts
import {
  BuilderContext,
  BuilderOutput,
  createBuilder,
  targetFromTargetString,
} from '@angular-devkit/architect';
import { JsonObject } from '@angular-devkit/core';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { readdir, readFile } from 'fs/promises';
import { join } from 'path';

interface DeployOptions extends JsonObject {
  bucket: string;
  region: string;
  distFolder: string;
}

async function deployBuilder(
  options: DeployOptions,
  context: BuilderContext,
): Promise<BuilderOutput> {
  // 1 — log start
  context.reportStatus(`Deploying to s3://${options.bucket}…`);
  context.logger.info(`Region: ${options.region}`);

  // 2 — optionally invoke another builder first (e.g. build the app)
  const buildTarget = { project: context.target!.project, target: 'build', configuration: 'production' };
  const buildResult = await context.scheduleTarget(buildTarget);
  const buildOutput = await buildResult.output.toPromise();
  if (!buildOutput.success) {
    return { success: false, error: 'Build failed before deploy' };
  }

  // 3 — do the actual work
  const distPath = join(context.workspaceRoot, options.distFolder);
  const files = await readdir(distPath, { recursive: true });
  const client = new S3Client({ region: options.region });

  let uploaded = 0;
  for (const file of files) {
    const content = await readFile(join(distPath, file));
    await client.send(new PutObjectCommand({
      Bucket: options.bucket,
      Key: file,
      Body: content,
    }));
    uploaded++;
    context.reportProgress(uploaded, files.length, `Uploaded ${file}`);
  }

  context.reportStatus('Done.');
  return { success: true };
}

export default createBuilder(deployBuilder);
```

### 4 — Register in angular.json and use

```json
// angular.json
{
  "projects": {
    "my-app": {
      "architect": {
        "deploy": {
          "builder": "my-builders:deploy",
          "options": {
            "bucket": "my-production-bucket",
            "region": "eu-west-1",
            "distFolder": "dist/my-app/browser"
          },
          "configurations": {
            "staging": {
              "bucket": "my-staging-bucket"
            }
          }
        }
      }
    }
  }
}
```

```bash
ng run my-app:deploy               # production bucket
ng run my-app:deploy:staging       # staging bucket

# Before publishing — test locally by linking
npm link
cd ../my-angular-project
npm link my-builders
```

### Watch mode — Observable builders

For long-running tasks (file watchers, dev servers), return an Observable:

```typescript
import { Observable } from 'rxjs';

function watchBuilder(
  options: WatchOptions,
  context: BuilderContext,
): Observable<BuilderOutput> {
  return new Observable(subscriber => {
    context.logger.info('Watching for changes…');

    const watcher = startFileWatcher(options.glob, () => {
      runTask(options, context)
        .then(() => subscriber.next({ success: true }))
        .catch(err => subscriber.next({ success: false, error: err.message }));
    });

    // Teardown when the CLI user hits Ctrl+C
    return () => {
      watcher.close();
      context.logger.info('Watcher stopped.');
    };
  });
}

export default createBuilder(watchBuilder);
```

## Common mistakes

### Mistake 1 — Not migrating to the new @angular/build builders

If your project was created before Angular 17, it still uses the old Webpack
builders. `ng update` migrates automatically, but teams that skip updates
carry a significant build speed penalty:

```json
// ❌ Old — Webpack, slow cold builds
"build": { "builder": "@angular-devkit/build-angular:browser" }
"serve": { "builder": "@angular-devkit/build-angular:dev-server" }
"test":  { "builder": "@angular-devkit/build-angular:karma" }

// ✅ New — esbuild/Vite/Vitest, 2–5x faster
"build": { "builder": "@angular/build:application" }
"serve": { "builder": "@angular/build:dev-server" }
"test":  { "builder": "@angular/build:unit-test" }
```

Run `ng update @angular/core @angular/cli` to migrate.

### Mistake 2 — Putting all options in the base instead of configurations

Options in the `options` block are shared across all configurations. Putting
production-only settings there means they apply to development too:

```json
// ❌ optimization in base — applies to ng serve as well
"options": {
  "optimization": true,   // dev builds are now minified and slow to debug
  "outputPath": "dist"
}

// ✅ optimization in production configuration only
"options": {
  "outputPath": "dist"
},
"configurations": {
  "production": { "optimization": true }
}
```

### Mistake 3 — Using console.log instead of context.logger

Same as schematics — `console.log` output doesn't integrate with the CLI's
output formatting and verbosity controls:

```typescript
// ❌ Raw output — no formatting, ignores --verbose flag
console.log('Building...');

// ✅ Structured logger output
context.logger.info('Building...');
context.logger.warn('This option is deprecated');
context.logger.error('Build failed');
```

### Mistake 4 — Returning success: true when async work failed

If your builder spawns a child process or calls async code, ensure failure
surfaces as `{ success: false }` — not swallowed:

```typescript
// ❌ Error swallowed — CLI reports success even when the deploy failed
try {
  await deploy(options);
} catch (err) {
  context.logger.error(err.message);
}
return { success: true };   // always returns success

// ✅ Return failure on error
try {
  await deploy(options);
  return { success: true };
} catch (err) {
  context.logger.error(err.message);
  return { success: false, error: err.message };
}
```

## How this evolved

> - **Angular CLI 1–5 (2017–2018):** No Architect framework. Build tooling was
>   scripts in package.json, Webpack configuration files, and npm-run-all for
>   orchestration. Customizing builds required ejecting Webpack config — a
>   one-way door that gave control at the cost of automatic upgrade support.
>
> - **Angular CLI 6 (2018):** Architect framework introduced. `createBuilder()`
>   API, `angular.json` targets, configuration inheritance, progress reporting.
>   All built-in commands migrated to builders. Custom builders now possible
>   without ejecting.
>
> - **Angular CLI 14 (2022):** `@angular-devkit/build-angular:browser-esbuild`
>   added as experimental — esbuild for production builds, still webpack dev server.
>
> - **Angular CLI 17 (2023):** `@angular/build:application` added as the new
>   primary builder — esbuild for builds, Vite for the dev server. First time
>   the dev server moved away from webpack-dev-server. New projects use it by
>   default.
>
> - **Angular CLI 21 (2025):** `@angular/build:unit-test` (Vitest) added as
>   the default test builder. `@angular-devkit/build-angular:karma` still
>   supported for migration.
>
> - **Angular CLI 22 (now):** The `@angular/build` package is the standard.
>   `@angular-devkit/build-angular` legacy builders remain for migration.
>   `ng update` migrates projects automatically. All three key commands
>   (build, serve, test) are faster and use modern tooling by default.

## See also

- [Schematics](./schematics.md) — the companion system: schematics generate
  code, builders execute tasks
- [Nx](./nx.md) — Nx executors extend builders with computation caching and
  dependency-awareness
- [Unit Tests](../testing/unit-tests.md) — `@angular/build:unit-test` and
  Vitest configuration details
- [Official docs — CLI builders](https://angular.dev/tools/cli/cli-builder)
- [Official docs — Angular CLI workspace config](https://angular.dev/reference/configs/workspace-config)
- [@angular-devkit/architect API](https://www.npmjs.com/package/@angular-devkit/architect)

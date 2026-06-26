---
roadmap_node: "nx"
title: "Nx"
file: "tooling/nx.md"
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

# Nx

> **Lead with this:** Nx turns your repo into a monorepo where multiple Angular
> apps and shared libraries live together, share code without npm publishing,
> and only rebuild and retest the parts that changed. The payoff scales with
> repo size: 45-minute CI runs become 6 minutes, and "I changed one line —
> why is everything rebuilding?" stops being a daily question.

## What it is

**Nx** is a build system and developer toolkit for monorepos. It sits on top
of the Angular CLI (it doesn't replace it) and adds:

| Feature | What it does |
| --- | --- |
| **Project graph** | A dependency map of every app and library in the repo |
| **Task graph** | The order tasks must run in, based on the project graph |
| **Affected commands** | Run a task only on projects affected by your changes |
| **Computation caching** | Skip tasks whose inputs haven't changed (local + remote) |
| **Code generators** | Scaffold apps, libraries, components with Nx conventions |
| **Module boundaries** | ESLint rules that enforce architectural layering |
| **Distributed task execution** | Run cache-able tasks across multiple CI agents |

You typically reach for Nx when your codebase outgrows a single Angular app —
when you start needing shared component libraries, multiple deployable apps,
or want a backend in the same repo. For a single small app, the Angular CLI
alone is enough.

## The problem Nx solves — what life is like without it

This is the most important question, because Nx's value depends entirely on
the problems you're hitting. If you don't have these problems, Nx is overhead.
If you have them, Nx is transformative.

### Pain 1 — Sharing code between Angular apps

Say you have two Angular apps: `admin-portal` and `customer-portal`. Both
need the same `Button` component, the same `AuthService`, and the same `User`
TypeScript interface.

**Without Nx, you have two bad options:**

**Option A — Copy-paste the code.** Now you have two `Button` components in
two repos. A bug fix means fixing it twice. Designs drift. Behavior diverges.
After six months, the two buttons are subtly different and nobody knows why.

**Option B — Publish a private npm package.** Now `Button` lives in
`@mycompany/ui-components`. You need:
- A separate Git repo for the library
- A CI pipeline to build and publish it
- A private npm registry (or GitHub Packages)
- Version management (`1.4.2` → `1.4.3` → which app uses which?)
- A release process for every change (cut version, publish, then in each
  consuming app: bump dependency, install, test, deploy)

Making one change to `Button` means: PR to ui-components → review → merge →
CI publishes → bump in admin-portal → CI → bump in customer-portal → CI.
A 5-line CSS fix becomes a 40-minute round trip across three repos.

**With Nx:** `Button` lives at `libs/ui-components/src/lib/button.component.ts`.
Both apps import it as `@myorg/ui-components`. The TypeScript path mapping
(set up automatically) resolves to the local source. One PR changes both the
library and any consuming code together. No publishing, no versioning, no
inter-repo coordination.

### Pain 2 — "Why is CI taking 45 minutes?"

A repo with 8 Angular apps. Every PR runs `ng build && ng test && ng lint`
for all 8 apps. Most PRs touch one app. The other 7 builds are pure waste —
their code didn't change, but CI rebuilds them anyway because there's no
mechanism to know that.

**Without Nx:** Either accept 45-minute CI runs, or write custom logic in
your CI config to detect which folder changed and run only those builds.
This breaks the moment apps share code — if `app-1/src/lib/util.ts` changed
and `app-3` imports it, your custom logic doesn't know to build `app-3`.
You're either over-cautious (build everything, slow) or under-cautious
(skip too much, broken builds make it to prod).

**With Nx:** `nx affected -t build,test,lint` walks the project graph, sees
which projects depend on the files that changed in this PR, and runs the
tasks only for those projects. Same logic for `affected` works whether the
change is a one-app fix or a shared library that 6 apps depend on. Real
production data: BlackRock's Angular monorepo team saves on average over 15 hours per week of CI computation time with Nx's affected and caching features.

### Pain 3 — "I didn't change this — why is it rebuilding?"

You're working on `customer-portal`. You make a typo, save, hit Cmd+S in
your editor. The dev server rebuilds. You fix the typo, save again. The dev
server rebuilds again. Each rebuild takes 12 seconds because the project is
large. You've burned five minutes of your morning waiting for rebuilds of
code that has identical input every time.

**Without Nx:** Angular CLI rebuilds when its inputs change. There's no
mechanism to recognize "I've built this exact input combination before — here's
the cached output."

**With Nx:** Every cacheable task computes a hash of its inputs (source
files, dependencies, environment). Before running, Nx checks if it has the
output for that hash in cache. If yes, it replays the cached output — restoring
files, log output, and exit codes — without running the task. Nx checks locally first, then remotely if a remote cache is configured.

With Nx Cloud's remote cache, this scales further: when your teammate runs
the build on their machine, the output is cached remotely. When you pull
their branch and run the same build, Nx downloads their cached output instead
of rebuilding. Real production case: Hetzner Cloud cut CI time from 45 minutes to 6 minutes with an 85% cache hit rate.

### Pain 4 — Architecture rot in a large team

A repo with 30 developers and 15 libraries. Without enforced boundaries,
someone in `feature-checkout` imports directly from `feature-billing`'s
internal files. Six months later, you can't refactor `feature-billing`
because three other features quietly reach into its internals.

**Without Nx:** You write a CONTRIBUTING.md document, hope reviewers catch
violations, and watch architectural decay happen anyway.

**With Nx:** ESLint rules (`@nx/enforce-module-boundaries`) read the
project graph and tags. You declare `feature-checkout` can import from
`type:ui` and `type:util` but NOT from other `type:feature` libraries.
CI fails on violations. Boundaries become a contract enforced by tooling,
not goodwill.

## How it works under the hood

### The project graph — the foundation

When you run any Nx command, Nx first builds the **project graph**: a
directed graph of every app and library in your workspace and the
dependencies between them.

```
Project graph for a typical Angular monorepo:

apps/
  ├─ admin-portal      ─→ libs/ui-components, libs/auth, libs/data-access
  └─ customer-portal   ─→ libs/ui-components, libs/payment, libs/data-access

libs/
  ├─ ui-components     ─→ libs/util
  ├─ auth             ─→ libs/data-access, libs/util
  ├─ payment          ─→ libs/data-access, libs/util
  ├─ data-access      ─→ libs/util
  └─ util             (no dependencies)
```

Nx analyzes files' source code, your installed dependencies, and TypeScript files to figure out these dependencies automatically. You don't maintain the graph by hand — Nx reads your imports.

You can visualize the graph with `nx graph` — it opens an interactive HTML
viewer showing every project, its dependencies, and (if you give it a PR
base) the affected subset.

### The task graph — and computation hashing

Once Nx has the project graph, running a task is two-step:

**Step 1 — Build the task graph.** If you run `nx build customer-portal`,
Nx walks the project graph from `customer-portal`. If any dependency has a
`build` target, that build must run first (or come from cache). The result
is a directed graph of tasks ordered by dependency.

**Step 2 — Compute hashes and check cache.** For each task, Nx computes a
**computation hash**. For a task like `nx test remixapp`, the hash includes all the source files of the project and its dependencies, the dependent npm package versions, the executor configuration, and global config files affecting all tasks.

The hash function is deterministic — same inputs always produce the same
hash. Before running a task, Nx looks up the hash in cache. Hit → replay
output, skip execution. Miss → run the task, store result in cache for next
time.

This is why you can run `nx build customer-portal` ten times in a row and
only the first one takes time — the other nine replay the cached output in
milliseconds.

### Affected — the same idea, applied to PRs

The `affected` command combines Git history with the project graph:

```
1. Git tells Nx which files changed in this PR (base: main, head: HEAD)
2. Nx maps changed files to projects (libs/auth/src/foo.ts → "auth" project)
3. Nx walks the project graph backwards from changed projects
   to find every project that DEPENDS on them
4. Nx runs the specified tasks only on that affected set
```

If you change one line in `libs/util`, every project that depends on
`util` is affected (which is usually most of them). If you change one line
in `apps/admin-portal`, only `admin-portal` is affected — no library and no
other app cares.

Nx Affected is best paired with remote caching and distributed task execution because the set of affected projects is always calculated with respect to your last successful run on the main branch.

## Setup

### Creating a new Nx workspace

```bash
npx create-nx-workspace@latest myorg --preset=angular-monorepo
```

The CLI walks you through choosing an app name, styling solution, and
e2e/test runners. Result:

```
myorg/
├── apps/
│   └── my-first-app/        ← your Angular app
├── libs/                    ← shared libraries go here
├── nx.json                  ← Nx workspace config
├── tsconfig.base.json       ← root TS config with path mappings
└── package.json
```

### Adding Nx to an existing Angular CLI workspace

```bash
npx nx@latest init
```

This adds Nx alongside the Angular CLI without breaking your existing setup.
`ng build` keeps working; `nx build` now works too and gains caching.

### Creating apps and libraries

```bash
# Generate a new Angular app
nx g @nx/angular:app booking-portal

# Generate a shared library
nx g @nx/angular:library ui-components

# Generate a component inside the library
nx g @nx/angular:component button --project=ui-components
```

Use the library in any app:

```typescript
// apps/booking-portal/src/app/page.component.ts
import { ButtonComponent } from '@myorg/ui-components';
//                              ↑ TypeScript path mapping resolves
//                              this to libs/ui-components/src/index.ts
```

The path mapping is set up automatically in `tsconfig.base.json` —
no npm publish required.

### Library types and module boundaries

A common Nx convention is to tag libraries by `type` and `scope`:

```json
// libs/ui-components/project.json
{
  "tags": ["type:ui", "scope:shared"]
}

// libs/feature-checkout/project.json
{
  "tags": ["type:feature", "scope:checkout"]
}

// libs/data-access/project.json
{
  "tags": ["type:data-access", "scope:shared"]
}
```

Then in `.eslintrc.json`, enforce rules using these tags:

```json
{
  "rules": {
    "@nx/enforce-module-boundaries": ["error", {
      "depConstraints": [
        { "sourceTag": "type:feature", "onlyDependOnLibsWithTags": ["type:ui", "type:data-access", "type:util"] },
        { "sourceTag": "type:ui",      "onlyDependOnLibsWithTags": ["type:util"] },
        { "sourceTag": "type:util",    "onlyDependOnLibsWithTags": ["type:util"] },
        { "sourceTag": "scope:checkout", "onlyDependOnLibsWithTags": ["scope:checkout", "scope:shared"] }
      ]
    }]
  }
}
```

Now `lint` fails if `ui-components` ever tries to import from a `type:feature`
library, or `feature-checkout` tries to import `scope:billing`. Architecture
enforcement becomes automatic.

## Real-world patterns

### Pattern 1 — Daily commands

The most common Nx commands during regular development:

```bash
# Run one task on one project
nx serve admin-portal              # ng serve admin-portal
nx build admin-portal --prod
nx test ui-components --watch

# Run a task on every project that has it
nx run-many -t build               # build all projects with a build target
nx run-many -t test --parallel=4   # test all, up to 4 in parallel

# Run a task only on affected projects (the gold-standard CI command)
nx affected -t build               # only projects affected by current changes
nx affected -t test,lint           # multiple targets
nx affected -t build --base=main   # compare against main branch

# Inspect the project graph
nx graph                           # opens an interactive graph viewer
nx graph --affected                # only the affected subset
```

### Pattern 2 — CI with affected + caching

A typical Nx-aware CI pipeline:

```yaml
# .github/workflows/ci.yml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0          # full history needed for affected base comparison

- run: npm ci

# Optional but transformative: connect to Nx Cloud for remote cache
- run: npx nx-cloud start-ci-run

# Run lint/test/build only on projects affected by this PR
- run: npx nx affected -t lint,test,build --base=origin/main
```

Without `nx affected`, every PR runs every task for every app — minutes wasted.
With `nx affected` + remote cache: build and test execution time drops dramatically; one BlackRock team reported saving over 15 hours per week of CI time.

### Pattern 3 — Polyglot monorepo

Nx is not Angular-specific. Nx now handles polyglot workspaces natively with support for Gradle, Maven, and .NET. One command can spin up any backend necessary for your frontend, and changes can be made across both frontend and backend all at once.

```bash
# Frontend (Angular)
nx g @nx/angular:app web

# Backend (Node)
nx g @nx/nest:app api

# Run both at once
nx run-many -t serve --projects=web,api --parallel=2
```

The task graph orchestrates both. The web app's `serve` can depend on the
API's `serve`, so starting the web app boots the API automatically.

## Common mistakes

### Mistake 1 — Reaching for Nx too early

Nx pays for itself when you have multiple apps, shared libraries, or slow
CI. For a single Angular app with a small team, the Angular CLI alone is
simpler and has less to learn. **Symptom that you should switch:** you're
about to copy-paste a component to a second app, or you're about to publish
your first private npm library for code sharing.

### Mistake 2 — Putting global files in implicitDependencies

Files listed in Nx's implicit dependencies invalidate every project's cache
when changed. If you add `angular.json`, `tsconfig.base.json`, or other global files to implicitDependencies, even a small change can cause every app to be considered affected and rebuilt. The default Nx config is conservative enough that you should rarely need to add more — investigate carefully before doing so.

### Mistake 3 — Treating libs as buckets instead of bounded contexts

A library should have a clear purpose: a UI component set, a feature flow,
a data-access wrapper, a set of utility functions. Avoid `libs/shared`
becoming a catch-all where everything lives. Use the `type:` and `scope:`
tag convention from the start, and split libraries by purpose.

### Mistake 4 — Skipping `nx migrate` for updates

Nx ships its own update mechanism that knows how to migrate your workspace
across breaking changes:

```bash
# ❌ Manual: edit package.json, npm install, debug breakage
npm install nx@latest @nx/angular@latest

# ✅ Automated: Nx generates a migration plan and applies code transforms
nx migrate latest
npm install
nx migrate --run-migrations
```

The `migrate` command handles renamed APIs, deprecated patterns, and
configuration shape changes automatically. The Nx team uses the migrate process to keep workspaces up-to-date with new major versions of frameworks like Angular, React, and Next.js.

## How this evolved

> - **Nx 1.0 (2017):** Started as Nrwl Extensions for Angular — a set of
>   schematics that added monorepo capabilities to the Angular CLI. Focused
>   on shared libraries and module boundaries.
>
> - **Nx 7+ (2019):** Added the affected commands and computation cache.
>   This is when Nx became fundamentally about build performance, not just
>   monorepo structure.
>
> - **Nx 13+ (2021):** Added Nx Cloud — remote caching across CI machines
>   and developer workstations. Cache hit rates of 80%+ became achievable
>   in production.
>
> - **Nx 16+ (2023):** Distributed Task Execution (DTE) shipped — automatically
>   distributes cache-able tasks across CI agents. Combined with affected,
>   this is the "45min CI becomes 6min" story.
>
> - **Nx 17–20 (2024–2025):** Polyglot support broadened — Gradle, Maven, .NET.
>   TypeScript Project References became the default configuration for new workspaces, significantly speeding up development. The Nx team also introduced Angular Rspack — a fast bundler for Angular teams.
>
> - **Nx 21+ (2025–2026):** Nx MCP server shipped — gives AI assistants deep access to workspace structure, project dependencies, task configurations, and real-time terminal output. The Terminal UI was introduced for viewing multiple running tasks simultaneously.
>
> - **With Angular 22 (now):** Nx supports Angular 22's signal-first
>   architecture, zoneless default, and the new Vitest test runner.
>   `nx migrate latest` handles the Angular CLI 22 → Nx Angular 22 upgrade
>   automatically.

## See also

- [Schematics](./schematics.md) — Nx generators are built on Angular schematics;
  understanding schematics helps you write custom Nx generators
- [Builders](./builders.md) — Nx executors are an evolution of Angular builders
  with caching and dependency awareness
- [Unit Tests](../testing/unit-tests.md) — Nx's default test runner is Vitest;
  `nx test` and `nx affected -t test` work with it
- [E2E Testing](../testing/e2e-testing.md) — Nx generates Playwright or Cypress
  setups by default for new apps
- [Official Nx docs](https://nx.dev)
- [Nx + Angular guide](https://nx.dev/recipes/angular)
- [Nx mental model](https://nx.dev/concepts/mental-model)

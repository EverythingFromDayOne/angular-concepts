# Session — structural refactor to suite-standard layout

**Repo:** `EverythingFromDayOne/angular-concepts`
**Base branch:** `master` (current default)
**Work branch:** create `main` from `master` — do not commit to `master`
**Scope:** structure only. Do not rewrite, expand, shorten, or "improve" any article prose.

---

## 0. Ground rules

1. **Content is preserved verbatim** except where this document explicitly says to delete or rewrite something. If you are tempted to reword a sentence, don't.
2. **Every step is mechanical.** Where a rule is ambiguous, stop and list the ambiguity in `REFACTOR-REPORT.md` rather than guessing.
3. **Nothing is deleted without being counted.** Every removal goes in the report with a count.
4. Work in one branch, one PR. Commit in the phases below so the diff is reviewable.

```bash
git fetch origin
git checkout -b main origin/master
```

Do **not** attempt to change the repository's default branch — that is a GitHub setting, not a git operation. It will be done manually after this PR merges.

---

## 1. Target layout

This is the layout of the sibling repo `nextjs-concepts` (verified against its `main` branch). Reproduce it exactly.

```
.editorconfig
.github/workflows/verify.yml
.gitignore
AGENTS.md
LICENSE
README.md
package.json
pnpm-workspace.yaml
progress.md
roadmap.md
docs/
  concepts/<folder>/<slug>.md
  recipes/<folder>/<slug>.md
  recipes/index.md
  templates/ARTICLE_TEMPLATE.md
  templates/RECIPE_TEMPLATE.md
  evolution-ledger.md
scripts/
  build-article.py
  verify-code-blocks.mjs
  verify-legacy-markers.mjs
  verify-links.mjs
  lib/extract.mjs
prompts/
```

Two differences from the current repo that drive most of the work:

- **All concept articles move down one level** into `docs/concepts/`. Today they sit at `docs/<folder>/`. Recipes already sit at `docs/recipes/<folder>/` and stay where they are.
- **`glossary.md` moves** from the repo root to `docs/glossary.md`.

---

## 2. Phase 1 — move files

Use `git mv` for every move so history is preserved.

Move every folder currently under `docs/` **except** `recipes/` into `docs/concepts/`:

```
docs/components/          → docs/concepts/components/
docs/dependency-injection/ → docs/concepts/dependency-injection/
docs/directives/          → docs/concepts/directives/
docs/forms/               → docs/concepts/forms/
docs/http/                → docs/concepts/http/
docs/monorepo/            → docs/concepts/monorepo/
docs/pipes/               → docs/concepts/pipes/
docs/reactivity/          → docs/concepts/reactivity/
docs/rendering/           → docs/concepts/rendering/
docs/routing/             → docs/concepts/routing/
docs/state-management/    → docs/concepts/state-management/
docs/testing/             → docs/concepts/testing/
docs/tooling/             → docs/concepts/tooling/
```

Also move the two loose files at `docs/` root:

```
docs/getting-started.md      → docs/concepts/foundations/getting-started.md
docs/typescript-prereqs.md   → docs/concepts/foundations/typescript-prereqs.md
glossary.md                  → docs/glossary.md
```

**Filename bug to fix in this phase.** One recipe filename contains a space before the extension:

```
docs/recipes/state-management/ngrx-to-signal-store-migration .md
```

`git mv` it to `ngrx-to-signal-store-migration.md`. Report whether the space was present in the git index or only on disk.

Commit: `refactor: move concept articles under docs/concepts/`

---

## 3. Phase 2 — repair every relative link

The Phase 1 move invalidates every relative link in the repo. There is also pre-existing link rot. Fix both together.

Write a throwaway script (do not commit it) that, for every `.md` file in the repo, parses markdown links of the form `](path.md)` and `](path.md#anchor)`, resolves each against the containing file's new directory, and reports whether the target exists.

Then repair in this order:

**3a. Known pre-existing breakage — fix these explicitly.**

- `README.md` links every recipe as `recipes/<folder>/<slug>.md`. README is at the repo root, so all of these need the `docs/` prefix: `docs/recipes/<folder>/<slug>.md`.
- Both `README.md` and `progress.md` refer to `forms-and-search`. The directory on disk is `form-and-search` — singular. Correct the references, do not rename the directory.
- `docs/concepts/components/component-interactions.md` links `../templates/data-binding.md`. After the move the correct path is `templates/data-binding.md` (sibling folder under `components/`). Verify and fix.
- `docs/concepts/components/templates/data-binding.md` links `../../_orphans/getting-started.md`. No `_orphans` directory exists. Retarget to `../../foundations/getting-started.md`.
- `docs/concepts/dependency-injection/dependency-injection.md` contains 17 links to flat-root paths spanning 9 distinct basenames. **Six of the nine do not exist anywhere in the repo** — `di-modern.md`, `di-tokens.md`, `environment-injector.md`, `signal-queries.md`, `standalone-migration.md`, `router-modern.md`. Convert those to plain text and list them in the report under "unwritten articles referenced". The remaining three **do** exist and must be retargeted per the general §3b rule: `signal-inputs.md` → `../reactivity/signal-inputs.md`, `control-flow.md` → `../components/templates/control-flow.md`, `unit-tests.md` → `../testing/unit-tests.md`.

  (Corrected 2026-08-11: the original text of this bullet claimed none of the nine existed, which was false and caused three valid cross-references to be stripped.)

**3b. Everything else.** For each remaining broken link, if a file with that exact basename exists somewhere in the repo, retarget to it. If no such file exists, strip the link syntax and keep the label, and add it to the "unwritten articles referenced" list.

**Never create a placeholder file to satisfy a link.** An empty article is worse than a plain-text reference.

Report the before/after broken-link count. It must be zero when you finish.

Commit: `fix: repair relative links after restructure`

---

## 4. Phase 3 — frontmatter migration

Every article under `docs/concepts/` currently carries frontmatter shaped like this:

```yaml
---
roadmap_node: "lazy-loading"
title: "Angular Router — Lazy Loading"
file: "routing/lazy-loading.md"
source_days: [29]
original_authors: ["Trung Vo"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---
```

Rewrite it to the suite shape:

```yaml
---
article_id: lazy-loading
concept_folder: routing
related:
  - routing/routing
  - routing/router-configuration
angular_baseline: "22.1.1"
verified_against: "@angular/core@22.1.1"
verified_on: 2026-08-11
status: draft
translation:
  source_days: [29]
  angular_when_written: "9"
  translated: true
  upgraded: true
  reviewed: false
---
```

Field-by-field rules:

| Old | New | Rule |
| --- | --- | --- |
| `roadmap_node` | `article_id` | **Use the filename slug, not the old value.** Several disagree — `router-configuration.md` has `roadmap_node: "configuration"`. The filename wins. |
| `title` | *(delete)* | The `# H1` is the title. Do not delete the H1. |
| `file` | *(delete)* | Derivable from the path. |
| — | `concept_folder` | The immediate parent folder under `docs/concepts/`. For nested paths like `reactivity/rxjs/`, use `reactivity/rxjs`. |
| `original_authors` | *(delete)* | See §5. |
| `source_days` | `translation.source_days` | Preserved — provenance, not authorship. |
| `angular_when_written` | `translation.angular_when_written` | Preserved. |
| `status.{translated,upgraded,reviewed}` | `translation.*` | **Preserved verbatim.** These three booleans define the Phase 2 modernization queue. Collapsing them loses the queue. |
| — | `status` (scalar) | Derived, see below. |
| `angular_baseline: "22"` | `angular_baseline: "22.1.1"` | Pin the patch version. |
| — | `verified_against` | `"@angular/core@22.1.1"` |
| — | `verified_on` | The date you run this refactor, ISO format. |
| `related` | `related` | Keep where present. Where absent, **leave it absent** — do not invent relationships. |

Scalar `status` derivation, applied mechanically:

| `translated` | `upgraded` | `reviewed` | → `status` |
| --- | --- | --- | --- |
| any | any | `true` | `reviewed` |
| `true` | `true` | `false` | `draft` |
| `false` | `true` | `false` | `draft` |
| `true` | `false` | `false` | `needs-upgrade` |

Recipes under `docs/recipes/` get the recipe shape instead:

```yaml
---
recipe_id: <filename slug>
primary_concept: <folder>/<slug of the concept it teaches>
difficulty: foundational | intermediate | advanced
angular_baseline: "22.1.1"
---
```

If a recipe has no existing field telling you its `primary_concept` or `difficulty`, **leave the field out and list the file in the report**. Do not guess difficulty.

Commit: `refactor: migrate frontmatter to suite schema`

---

## 5. Phase 4 — remove per-article attribution

Delete from **every** article and recipe:

- The entire `## Author` section, including the name, GitHub URL, and the italic line beneath it (`*Translated from the original Vietnamese as part of the angular-concepts project.*` and its variants).
- Any `See CREDITS.md for full attribution` line inside an article body.
- The `original_authors` frontmatter key (already covered in Phase 3).

Delete nothing else. Some articles reference an author inside prose as part of an explanation — for example a sentence like "in the router configuration article, Tiep showed how to…". Rewrite only the minimum needed to remove the personal reference: "in [the router configuration article](…), we configured a feature module…". Report every such prose edit individually with before/after text.

**Delete `CREDITS.md`.** `git rm CREDITS.md`. Remove every link to it from `README.md`, `progress.md`, `CONTRIBUTING.md`, and any article body.

**Also remove the attribution paragraph from `README.md`** — the one naming the original authors and the source series (currently near the end, beginning "This project is an English translation and modernization of…"). Delete the paragraph and its heading if the heading has no other content beneath it.

**Replace `LICENSE`** with the suite-standard dual license. The sibling `nextjs-concepts` uses CC BY 4.0 for prose and MIT for code; adopt the same shape. Note the scope line differs — this repo has no `demos/` directory, so code scope is `scripts/` only. Write exactly this:

```
Copyright (c) 2026 Nguyen Hoang Cong Huy
Copyright (c) 2020 Angular Vietnam

PROSE — the concept articles and recipes (all .md files) are licensed under
Creative Commons Attribution 4.0 International (CC BY 4.0).
Full text: https://creativecommons.org/licenses/by/4.0/legalcode

CODE — everything under scripts/, and all code samples embedded in the
articles, is licensed under the MIT License:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

This drops the "derivative work of…" explanatory paragraph and the descriptive parenthetical after the second copyright — the sibling has neither, and neither is required. Keep the two copyright lines exactly as written above and change nothing else in this file.

Report: number of `## Author` sections removed, number of prose edits made.

Commit: `refactor: remove attribution sections, delete CREDITS.md, adopt suite license`

---

## 6. Phase 5 — scaffold the missing infrastructure

The repo currently has **no CI, no package.json, and no verification scripts**. `scripts/` contains only `sync-progress.py`. Create the following. Where a file's content depends on tooling that does not exist in this repo, create the file with correct structure and a `TODO` marker rather than a broken implementation.

**`package.json`** — mirror the sibling's shape:

```json
{
  "name": "angular-concepts",
  "version": "0.0.0",
  "private": true,
  "description": "Concept articles and symptom-first recipes for Angular — English translation and v22 modernization of the 100 Days of Angular series.",
  "packageManager": "pnpm@10.33.0",
  "engines": { "node": ">=22" },
  "scripts": {
    "verify:links": "node scripts/verify-links.mjs",
    "verify:frontmatter": "node scripts/verify-frontmatter.mjs",
    "verify": "pnpm verify:links && pnpm verify:frontmatter"
  },
  "license": "SEE LICENSE IN LICENSE"
}
```

Note what is **absent** and why: the sibling's `verify:code-blocks`, `verify:legacy`, and `verify:templates` gates all depend on a demo application to extract code from. **This repo has no demo app and no TypeScript files at all.** Do not scaffold those three scripts against a demo that doesn't exist. Create `docs/templates/ARTICLE_TEMPLATE.md` and `RECIPE_TEMPLATE.md` as structural placeholders only.

**`scripts/verify-links.mjs`** — port the link checker: resolve every relative `.md` link and `#anchor` against GitHub's heading-slug algorithm, exit non-zero on any failure.

**`scripts/verify-frontmatter.mjs`** — assert that every file under `docs/concepts/` has `article_id` matching its filename slug, `concept_folder` matching its path, and a `status` from the allowed set; every file under `docs/recipes/` has `recipe_id` matching its filename.

**`.github/workflows/verify.yml`** — Node 22, pnpm 10.33.0, runs `pnpm verify`. Trigger on push to `main` and on pull request.

**`AGENTS.md`** — the sibling's version encodes repo-specific invariants. Write angular-concepts' equivalent covering: baseline is `@angular/core@22.1.1`; verify claims against the registry or angular.dev, never training recall; `<!-- legacy: … -->` markers precede preserved pre-v22 code blocks; `article_id` is always the filename slug; the mandatory article section order.

**`docs/evolution-ledger.md`** — create the file with the sibling's table shape (`Old surface | New surface | Kind of change | Owning article | Status`) and seed it **only** with rows you can support from content already in the repo — for example `NgModule → standalone + route providers`, `RouterModule.forRoot → provideRouter`, `class guards → functional guards`, `CanLoad → CanMatch`, `Zone.js → signals/zoneless`. Do not invent rows.

**`.editorconfig`, `.gitignore`, `pnpm-workspace.yaml`** — standard, matching the sibling.

Commit: `chore: scaffold CI, verification scripts, and templates`

---

## 7. Phase 6 — update the tracking files

`progress.md` and `README.md` both describe the old layout and contain stale claims. Update **paths and counts only** — do not rewrite their prose or restructure their tables.

Specific corrections required:

- Every `docs/<folder>/` path becomes `docs/concepts/<folder>/`.
- `progress.md`'s open-TODO block states that `CREDITS.md` and `LICENSE` are not yet created. `LICENSE` exists; `CREDITS.md` was deleted in Phase 4. Remove both TODO items.
- `progress.md` names `reactivity/signals.md` as the highest-priority queued Phase 2 item. Its frontmatter is `translated: false, upgraded: true` and the file opens with a banner stating it was written fresh for v22. It is not a Phase 2 item. Correct the entry.
- `progress.md` references roughly 19 `.md` paths that do not exist on disk — among them `components/components.md`, `routing/route-guards.md` (disk: `guards-resolvers.md`), `components/lifecycle-hooks.md` (disk: `lifecycle.md`), `ssr/ssr-hydration.md` (disk: `rendering/ssr-hydration.md`). For each: if a file with that basename exists, fix the path; if not, mark the row `⚪ unwritten` and leave it.
- The Phase 2 queue table tracks 8 articles. **23 articles have `translated: true, upgraded: false`** — the untracked 15 include the entire 8-article RxJS block under `reactivity/rxjs/`. Add every missing article to the table with status `⚪`.

Commit: `docs: update progress and README for new structure`

---

## 8. Deliverable

Push the `main` branch and open a **draft** PR from `main` into `master` titled **"Restructure to suite-standard layout — REVIEW ONLY, DO NOT MERGE"**. The PR exists to give a reviewable diff; `main` is going to become the repository's default branch, so merging it into `master` would defeat the purpose. Leave it in draft.

Commit `REFACTOR-REPORT.md` at the repo root containing:

1. **Move manifest** — every `git mv`, old path → new path.
2. **Link repair** — broken count before, broken count after (must be 0), and the full list of "unwritten articles referenced" that were converted to plain text.
3. **Frontmatter** — count of articles migrated, and the derived `status` distribution.
4. **Attribution** — count of `## Author` sections removed; every prose edit with before/after text; confirmation that `CREDITS.md` was deleted and that `LICENSE` matches the block specified in Phase 4 exactly.
5. **Scaffolded files** — what was created, and what was deliberately *not* created because this repo has no demo app.
6. **Ambiguities** — everything you had to decide that this document did not specify. This section is the most important one; if it is empty, you did not look hard enough.

Do not squash. Do not force-push. Do not touch `master`.

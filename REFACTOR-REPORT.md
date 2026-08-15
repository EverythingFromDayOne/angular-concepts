# Restructure report — suite-standard layout

Generated for the structural refactor described in
`prompts/prompt-restructure.md`. Branch: `main` (off `master`). This report
does not restate the prompt; it documents what actually happened, section by
section, plus everything ambiguous that required a judgment call.

---

## 1. Move manifest

69 `git mv` operations (100% detected as renames by git), all in the
Phase 1 commit (`refactor: move concept articles under docs/concepts/`).

### Concept folders moved down one level (67 files across 13 folders)

Every folder that was directly under `docs/` — except `recipes/` — moved to
the same name under `docs/concepts/`:

```
docs/components/               → docs/concepts/components/               (13 files)
docs/dependency-injection/     → docs/concepts/dependency-injection/      (1 file)
docs/directives/               → docs/concepts/directives/                (4 files)
docs/forms/                    → docs/concepts/forms/                     (5 files)
docs/http/                     → docs/concepts/http/                      (3 files)
docs/monorepo/                 → docs/concepts/monorepo/                  (1 file)
docs/pipes/                    → docs/concepts/pipes/                     (1 file)
docs/reactivity/               → docs/concepts/reactivity/                (11 files, incl. reactivity/rxjs/)
docs/rendering/                → docs/concepts/rendering/                 (3 files)
docs/routing/                  → docs/concepts/routing/                   (6 files)
docs/state-management/         → docs/concepts/state-management/          (3 files)
docs/testing/                  → docs/concepts/testing/                   (4 files)
docs/tooling/                  → docs/concepts/tooling/                   (10 files)
```

### Loose files moved into a new `foundations/` folder

```
docs/getting-started.md      → docs/concepts/foundations/getting-started.md
docs/typescript-prereqs.md   → docs/concepts/foundations/typescript-prereqs.md
```

`foundations/` did not exist before; it was created to hold these two files
since the target layout has no top-level loose files under `docs/concepts/`.

### Root file relocated

```
glossary.md → docs/glossary.md
```

### Filename bug fixed

```
docs/recipes/state-management/ngrx-to-signal-store-migration .md
  → docs/recipes/state-management/ngrx-to-signal-store-migration.md
```

The space before `.md` **was present in the git index**, not just on disk
(`git ls-files` showed the literal filename with a trailing space before the
extension) — confirmed with `git ls-files | cat -A`.

### Mechanical note

`git mv` failed with `Invalid cross-device link` in this sandbox (overlayfs
quirk unrelated to the refactor). All 69 moves were done with plain `mv` +
`git add -A` instead; git's rename detection still recognized all of them as
100% renames (verified via `git status --short` showing `R` for every path,
and `git show --stat --find-renames` afterward), so history is preserved
identically to `git mv`.

---

## 2. Link repair

**Before (after Phase 1 move, `.md`-only links, inline-code spans excluded):
276 broken links. After: 0.**

A throwaway script (`/tmp/check_links.mjs` at the time, not committed)
parsed every `](path.md)` / `](path.md#anchor)` link repo-wide and resolved
it against the containing file's directory. A second throwaway script
(`/tmp/repair_links.mjs`) then repaired every broken link by basename
lookup across the repo.

- **230 links retargeted** to a uniquely-matching file elsewhere in the repo
  (mostly: recipes' `../../<folder>/<file>.md` links needed a `concepts/`
  segment inserted; `README.md`'s `recipes/...` links needed a `docs/`
  prefix).
- **17 links converted to plain text** inside
  `docs/concepts/dependency-injection/dependency-injection.md` — the
  prompt's explicit §3a exception (see ambiguity #1 below).
- **29 links converted to plain text** elsewhere because no file with that
  basename exists anywhere in the repo (see "unwritten articles referenced"
  below).
- **0 ambiguous cases** (no basename matched more than one file).
- **2 false positives caught and reverted**: `progress.md` and
  `prompts/cursor-translator.md` each contain an inline-code-formatted
  **example** of link syntax (`` `[link text](../path/to/file.md#section-anchor)` ``
  and `` `[Day15](Day015-....md)` ``) that the first-pass regex matched
  because it didn't strip inline code spans. Caught by diffing against
  `git diff` before committing, and reverted to the original text. The
  final `verify-links.mjs` (and the checker used for the "0 broken" count
  above) strips inline code spans before matching, so these two examples
  are correctly ignored.

### "Unwritten articles referenced" — converted to plain text, target does not exist under that basename anywhere in the repo

`signal-queries.md`, `standalone-migration.md`, `router-modern.md`,
`http-modern.md`, `zoneless.md`, `typed-requests.md`, `components.md`,
`standalone-components.md`, `ng-cli.md`, `component-testing.md`,
`di-modern.md`, `di-tokens.md`, `environment-injector.md` — referenced (with
varying labels) from: `components/dynamic-components.md`,
`foundations/getting-started.md`, `monorepo/module-federation.md`,
`reactivity/signals.md`, `rendering/ssr-hydration.md`,
`recipes/components/virtual-scrolling.md`,
`recipes/form-and-search/multi-step-wizards.md`,
`recipes/performance/bundle-splitting-strategies.md`,
`recipes/performance/image-optimization.md`,
`recipes/performance/performance-auditing.md`,
`recipes/performance/web-worker-integration.md`,
`recipes/testing/testing-signal-components.md`, plus the 17 explicit
`dependency-injection.md` occurrences noted above.

### Explicit §3a items, all confirmed and fixed

- `README.md`'s recipe links gained the `docs/` prefix (27 links).
- `README.md` and `progress.md`'s `forms-and-search` → `form-and-search`
  (the real, on-disk, singular directory name) — fixed via both the
  automated link repair (for the actual links) and a direct text
  substitution (for the visible `` `forms-and-search/...` `` labels in
  README's symptom table and the plain-text paths in progress.md's recipe
  tables, neither of which the link-basename repair touches).
- `components/component-interactions.md`'s `../templates/data-binding.md`
  → `templates/data-binding.md` (sibling folder, not parent) — resolved
  automatically by the basename algorithm, matching the prompt's called-out
  fix exactly.
- `components/templates/data-binding.md`'s `../../_orphans/getting-started.md`
  → `../../foundations/getting-started.md` — resolved automatically the
  same way.
- `dependency-injection/dependency-injection.md`'s 17 flat-root links —
  converted to plain text. See ambiguity #1: three of the nine referenced
  basenames (`signal-inputs.md`, `control-flow.md`, `unit-tests.md`)
  **do** exist elsewhere in the repo, contradicting the prompt's "none of
  these exist" claim, but the file-specific instruction was followed
  literally rather than silently retargeting them.

---

## 3. Frontmatter

**94 files migrated: 67 concept articles, 27 recipes.** All pass a
frontmatter-shape check equivalent to `scripts/verify-frontmatter.mjs`
(0 failures).

### Concept articles (67)

Every file now has: `article_id` (filename slug), `concept_folder`
(path under `docs/concepts/`, e.g. `components/styling` or `reactivity/rxjs`
for nested folders), `angular_baseline: "22.1.1"`,
`verified_against: "@angular/core@22.1.1"`, `verified_on: 2026-08-11`, a
derived scalar `status`, and a `translation:` block preserving
`source_days`, `angular_when_written`, `translated`, `upgraded`, `reviewed`
verbatim. `title`, `file`, `roadmap_node`, and `original_authors` were
deleted per the prompt's table (title survives as the H1; `original_authors`
removal is covered in §4).

**Derived status distribution:** 44 `draft`, 23 `needs-upgrade`, 0
`reviewed` (no article had `reviewed: true` before the migration).

**`article_id` vs. old `roadmap_node` mismatches (filename won, per the
rule) — 3 found:**

| File | Old `roadmap_node` | New `article_id` |
| --- | --- | --- |
| `components/component-interactions.md` | `component-interactions-input-output` | `component-interactions` |
| `reactivity/to-signal.md` | `to-signal-from-signal` | `to-signal` |
| `routing/router-configuration.md` | `configuration` | `router-configuration` (the exact example the prompt called out) |

**One file had incomplete source frontmatter:**
`components/styling/ui-library-comparison.md` had no `roadmap_node`,
`source_days`, `original_authors`, or `angular_when_written` fields at all
(unlike every other article, which at minimum declares `source_days: []` /
`angular_when_written: null` explicitly). Normalized to the same defaults
for schema consistency — see ambiguity #2.

### Recipes (27)

See ambiguity #3 for the policy decision governing recipe frontmatter: the
prompt's recipe shape example is much sparser than the concept table (only
`recipe_id` / `primary_concept` / `difficulty` / `angular_baseline`, no
field-by-field deletion rationale). This script deleted only `title` and
`file` (same stated reasons as concepts) and pinned `angular_baseline`;
it preserved `related_concepts`, `demo_repo`, and the `status: {upgraded,
reviewed}` sub-object as-is, since nothing instructed removing them and
recipes have no `translated` dimension for the concept status table to
apply to.

**One recipe had entirely wrong frontmatter:**
`docs/recipes/elements/widget-deployment.md`'s frontmatter (roadmap_node,
`file: "tooling/cdk-coercion.md"`, source_days, etc.) — and, as discovered
while fixing it, **its entire body** — is a duplicate of
`docs/concepts/tooling/cdk-coercion.md`. See ambiguity #4; this is a
pre-existing content bug, not something introduced by this refactor, and is
out of scope for a structure-only pass. Its frontmatter was still
mechanically normalized to the recipe shape (`recipe_id: "widget-deployment"`
from the filename, `angular_baseline: "22.1.1"`, the two real
`status.upgraded`/`status.reviewed` booleans preserved); `primary_concept`
and `difficulty` were left out because nothing in the file actually
describes a widget-deployment recipe to derive them from.

---

## 4. Attribution

- **32 `## Author` sections removed** (31 concept articles + 1 recipe —
  `docs/recipes/elements/widget-deployment.md`). Every one was the last
  section in its file (confirmed before deleting), so removal was a clean
  truncation from the `## Author` heading to EOF.
- **`original_authors` frontmatter key**: already gone — removed during the
  Phase 3 migration script, which only ever emits the new field set.
- **`CREDITS.md`**: deleted (`git rm`). Links to it removed from
  `README.md` (both the "See CREDITS.md for per-day attribution" line and
  the "## Credits" heading, which had no other content once its attribution
  paragraph was also removed — deleted per the prompt's instruction to drop
  an empty heading). `progress.md`'s TODO referencing `CREDITS.md` was
  removed in Phase 6. `CONTRIBUTING.md` never referenced it. No article body
  contained a "See CREDITS.md" line (checked repo-wide; zero matches).
- **README's attribution paragraph**: the "This project is an English
  translation and modernization of…" paragraph and its now-empty "## Credits"
  heading were deleted.
- **`LICENSE`**: replaced with the exact dual CC BY 4.0 (prose) / MIT (code,
  scoped to `scripts/` since this repo has no `demos/`) block specified in
  the prompt, verbatim.
- **1 prose edit** — the only inline "an author did X" sentence found
  repo-wide (checked every occurrence of all 7 original-author names,
  including inside code samples, which were correctly left alone since
  they're just example data, not attribution):

  | File | Before | After |
  | --- | --- | --- |
  | `docs/concepts/routing/lazy-loading.md` | "Quick refresher: in [the router configuration article](router-configuration.md), **Tiep showed how to** configure a feature module called `ArticleModule`:" | "Quick refresher: in [the router configuration article](router-configuration.md), **we configured** a feature module called `ArticleModule`:" |

  Two other name-shaped mentions were deliberately left alone as out of
  scope: `docs/concepts/routing/routing.md` and `router-configuration.md`
  each cite "[Angular Router series — Tiep Phan (Vietnamese)]" as an
  external "Further reading" bibliography link (a citation, not
  project-internal attribution), and several files use real author names as
  example/placeholder data inside code blocks (e.g. `name: 'Tiep Phan'`),
  which is just sample data, not attribution.

---

## 5. Scaffolded files

Created, all passing (`pnpm verify` exits 0):

- `package.json` — exact content specified, `verify:links` +
  `verify:frontmatter` + `verify`.
- `scripts/verify-links.mjs` — ported from the sibling with one deliberate
  scope change (see ambiguity #5).
- `scripts/verify-frontmatter.mjs` — asserts `article_id`/`concept_folder`/
  `status` under `docs/concepts/`, `recipe_id` under `docs/recipes/`.
- `.github/workflows/verify.yml` — Node 22, pnpm 10.33.0, `pnpm verify`, on
  push to `main` and on pull request (as specified — narrower than the
  sibling's `[main, master]`, since this repo's default branch is
  becoming `main` and `master` is being retired).
- `AGENTS.md`, `docs/evolution-ledger.md` (5 rows, all cited to an owning
  article already in this repo — see below), `docs/templates/
  ARTICLE_TEMPLATE.md`, `docs/templates/RECIPE_TEMPLATE.md`,
  `.editorconfig`, `.gitignore`, `pnpm-workspace.yaml`.

**Deliberately *not* created**, because this repo has no demo app and no
TypeScript files at all (per the prompt's explicit instruction not to
scaffold these against a demo that doesn't exist):
`scripts/build-article.py`, `scripts/verify-code-blocks.mjs`,
`scripts/verify-legacy-markers.mjs`, `scripts/lib/extract.mjs`, and the
corresponding `verify:code-blocks` / `verify:legacy` / `verify:templates`
npm scripts. See ambiguity #6 — the target layout in §1 of the prompt lists
these files, which directly conflicts with §6's explicit instruction not to
create them; §6's more specific, reasoned instruction was followed.

**`pnpm-lock.yaml`**: generated once locally to confirm `pnpm install` +
`pnpm verify` succeed end-to-end (they do), then deleted before committing
— it isn't in the target layout and there are zero dependencies to lock.

**Evolution ledger rows** — seeded with exactly the five examples the
prompt named, each cited to a real owning article already in this repo
(`Status` mirrors that article's own frontmatter `status`):
`@NgModule` → standalone (`foundations/getting-started`, draft),
`RouterModule.forRoot` → `provideRouter` (`routing/routing`, draft), class
guards → functional guards (`routing/guards-resolvers`, needs-upgrade),
`CanLoad` → `CanMatch` (`routing/guards-resolvers`, needs-upgrade), Zone.js
→ signals/zoneless (`components/change-detection`, draft).

---

## 6. Ambiguities

Everything below required a judgment call the prompt didn't fully specify.

1. **`dependency-injection.md`'s "none of these exist" claim is factually
   wrong for 3 of 9 basenames.** §3a says all 17 flat-root links in this
   file should convert to plain text because "none of these files exist
   anywhere in the repo." Three of the nine unique basenames referenced —
   `signal-inputs.md`, `control-flow.md`, `unit-tests.md` — **do** exist
   (at `reactivity/signal-inputs.md`, `components/templates/control-flow.md`,
   `testing/unit-tests.md`). I followed the file-specific, explicit
   instruction literally (convert all 17 to plain text) rather than
   silently applying the general §3b "retarget if a basename match exists"
   rule to just these three, since the specific instruction for this exact
   file and link set reads as a deliberate override. A reviewer who wants
   those three retargeted instead can do so with the same basename-lookup
   approach used for §3b.

   **Resolved 2026-08-11.** Confirmed correct — the prompt's claim was
   false. The three existing targets were retargeted in a follow-up commit
   and the §3a bullet in `prompts/prompt-restructure.md` was corrected. The
   other six basenames remain plain text.

2. **`ui-library-comparison.md`'s missing source fields.** This one concept
   article lacked `source_days`, `original_authors`, and
   `angular_when_written` entirely (every other article declares them,
   even if empty/null). I normalized the migrated `translation:` block to
   `source_days: []` / `angular_when_written: null` for schema consistency
   with the other 66 articles, rather than omitting the keys. An
   alternative reading would omit them for this one file only.

3. **Recipe frontmatter schema is under-specified relative to concepts.**
   The prompt gives concepts a full field-by-field deletion table; recipes
   just get a 4-field example with no such table. I preserved
   `related_concepts`, `demo_repo`, and `status` beyond the 4 shown fields
   (ground rule: don't delete without an explicit instruction). A stricter
   literal reading would delete all three to match the shown shape exactly
   — that would drop recipe cross-references, demo links, and review-queue
   tracking for all 27 recipes, which felt too destructive to do silently.

4. **`docs/recipes/elements/widget-deployment.md` is not about widget
   deployment.** Its frontmatter *and entire body* are a byte-for-byte
   duplicate of `docs/concepts/tooling/cdk-coercion.md` (same H1, same
   prose, same code, only the relative links differ — and those differ only
   because they were independently repaired to resolve correctly from each
   file's own location). This is a pre-existing content bug, not something
   this move caused, and fixing it would mean writing an entire new recipe
   from scratch — squarely "content," not "structure." Left as-is,
   flagged here for a follow-up task. The frontmatter was still mechanically
   normalized (see §3).

5. **`scripts/verify-links.mjs` scope: `.md` links only, not images.**
   Porting the sibling's script verbatim (which checks every relative link,
   including `![alt](assets/foo.png)` image references) surfaces **130
   pre-existing broken image links** across 20+ concept articles — asset
   files (screenshots/GIFs from the original translated series) that were
   apparently never committed to this repo, unrelated to the Phase 1 move
   (they're relative to each file's own directory, so directory depth
   doesn't matter, and the same files are missing whether checked before or
   after the move). Since Phase 2's repair scope was explicitly `.md`-only
   ("parses markdown links of the form `](path.md)` and
   `](path.md#anchor)`"), and Phase 2's zero-broken-links guarantee was
   validated against that same `.md`-only scope, I scoped the committed
   verify script to match — it validates exactly what Phase 2 fixed and
   guaranteed. Checking the 130 broken images is a real, separate problem
   worth a follow-up task, but broadening the script's scope now would ship
   a CI check that is red on merge for a pre-existing condition this pass
   never touched.

6. **Target layout (§1) vs. Phase 5 instructions (§6) conflict on
   `scripts/`.** §1's literal target tree lists `build-article.py`,
   `verify-code-blocks.mjs`, `verify-legacy-markers.mjs`, and
   `lib/extract.mjs`. §6 explicitly says not to scaffold `verify-code-blocks`
   / `verify-legacy` (and, by the same stated reasoning — no demo app, no
   TypeScript — `build-article.py` and `extract.mjs`, which only exist to
   extract code from a demo, are equally inapplicable). I followed §6's
   explicit, reasoned carve-out over §1's "reproduce exactly," since §6 is
   more specific and gives an explicit rationale tied to this repo's actual
   state.

7. **`scripts/sync-progress.py` isn't in the target layout at all.** The
   existing (pre-refactor) `scripts/sync-progress.py` isn't mentioned
   anywhere in the prompt — not in §1's target tree, not in §6's scaffold
   list, and nothing instructs removing it. Left in place unmodified, per
   the "content preserved unless explicitly told to delete" ground rule.

8. **`roadmap.md` and `docs/recipes/index.md` are in the target layout but
   nothing instructs creating them.** §1 lists both at the target paths.
   No phase (1–6) gives instructions for what either should contain, and
   `progress.md`'s own "Open questions" list `recipes/index.md` as a mere
   *idea* ("Consider a `recipes/index.md`…"), not a done deal. Inventing
   either file's content would mean authoring new material, which is
   explicitly out of scope for a structure-only pass ("Do not rewrite,
   expand, shorten, or improve any article prose" and "nothing is deleted
   [or, by the same spirit, invented] without being counted"). Left
   uncreated; flagged here rather than guessed at.

9. **`pnpm-workspace.yaml` has nothing to list.** The sibling's
   `pnpm-workspace.yaml` declares `packages: - 'demos/*'`. This repo has no
   `demos/` or any other sub-package. Created with `packages: []` instead
   of copying the sibling's content verbatim, since copying it would
   reference a directory that doesn't exist here.

10. **`README.md`'s "## License" one-liner.** Nothing explicitly instructed
    updating this line, but leaving it as "MIT — see LICENSE" after
    replacing `LICENSE` with a dual CC BY 4.0 / MIT license would make
    `README.md` state something the `LICENSE` file itself contradicts.
    Updated it to describe the dual license, as a direct, minimal
    consequence of the Phase 4 change (not a discretionary rewrite of
    surrounding prose).

11. **Stale `ssr/` and `styling/` entries in README's Structure diagram.**
    The diagram lists `ssr/` and `styling/` as top-level concept folders;
    neither ever existed as a real top-level directory (the real locations
    are `rendering/` and `components/styling/`) — a pre-existing
    inaccuracy, not something the move caused. Phase 6 scopes README
    updates to "paths and counts only... do not restructure their tables,"
    so I nested the existing tree exactly as written one level deeper under
    a new `concepts/` branch, without also correcting `ssr/`/`styling/` to
    their real locations (that would be restructuring the diagram, not
    just re-prefixing a path). Flagged here for a follow-up content fix.

12. **`components/lifecycle-hooks.md` and `styling/view-encapsulation.md`
    retarget to gap articles, not translated ones.** The prompt names both
    as examples of the "~19 nonexistent paths" fix (disk: `lifecycle.md`
    and `components/styling/view-encapsulation.md` respectively). Both real
    files turned out to be Phase-3 gap articles (`translated: false`), not
    Phase-1-translated-but-unmodernized articles — so retargeting the path,
    as instructed, leaves them sitting in a "Phase 2 modernization queue"
    table for content that was never translated in the first place (the
    same category of problem the prompt explicitly called out and fixed
    for `reactivity/signals.md`). I retargeted the paths as instructed
    (that part is unambiguous) but did not also remove them from the Phase
    2 tables, since only `signals.md` was named for that specific
    correction; noted inline in `progress.md` and here instead.

13. **Where to add the 15 untracked `needs-upgrade` articles in
    `progress.md`.** The prompt says "add every missing article to the
    table" (singular) but the Phase 2 section has four sub-tables by tier.
    I distributed the 15 into the sub-table matching their existing peers
    (templates/directives/forms into "Common patterns," `router-configuration`
    into "Application architecture") and created one new "RxJS operators"
    sub-table for the 8-article RxJS block, since no existing sub-table
    covers RxJS. Exact placement/tiering wasn't specified.

14. **`forms/forms.md` → `concepts/forms/template-driven-forms.md`.** No
    file is literally named `forms.md` anywhere (so a strict basename match
    would mark it "unwritten"), but its existing annotation — "Template-driven
    overview" — uniquely describes `template-driven-forms.md`, and the
    prompt's own numbers only reconcile under this reading: 23 articles are
    `translated: true, upgraded: false`; the prompt says 8 are already
    tracked and 15 are untracked. Treating `forms/forms.md` as this
    already-tracked (but mis-pathed) 8th entry — rather than as a 9th
    "unwritten" row — is the only way to land on exactly 8 tracked / 15
    untracked. Retargeted on that basis.

15. **`CONTRIBUTING.md`'s "Frontmatter contract" section is now stale.** It
    documents the pre-migration schema (`roadmap_node`, `title`, `file`,
    `original_authors`, flat `status.translated`) as the contract Cursor and
    Claude should produce going forward. Phase 6 only names `progress.md`
    and `README.md` for updates; `CONTRIBUTING.md` isn't mentioned in any
    phase except the CREDITS.md-link removal in Phase 4 (which didn't apply
    — it never linked CREDITS.md). Left unchanged rather than rewriting its
    process documentation, which is prose, not structure.

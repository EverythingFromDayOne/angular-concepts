# Agent rules — `angular-concepts`

This repo targets **`@angular/core@22.1.1`** (pinned in every article's
`angular_baseline` / `verified_against` frontmatter). Your training data may
predate this baseline — verify before you write.

## Before you write any Angular claim

1. Verify against the npm registry (`@angular/core` version metadata) or
   [angular.dev](https://angular.dev) — never rely on training recall alone.
2. Check `docs/evolution-ledger.md` for the old→new surface map before
   describing a mechanism as "current".
3. Hedge explicitly when a claim cannot be verified in-session.

## Legacy code preservation

Pre-v22 code blocks are preserved side by side with their modern equivalent,
each preceded by the marker comment:

```
<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```

Never present a `<!-- legacy -->`-marked block as current guidance on its
own — it must be paired with the modern equivalent in the same section.

## Frontmatter invariants

- `article_id` (concept articles) and `recipe_id` (recipes) are **always the
  filename slug** — never a separate roadmap/task-tracker ID, even if one
  disagrees with the filename. The filename wins.
- `concept_folder` is the article's immediate parent folder under
  `docs/concepts/` (e.g. `reactivity/rxjs` for a nested folder).
- Enforced by `scripts/verify-frontmatter.mjs`; relative links enforced by
  `scripts/verify-links.mjs`. Both run in CI via `pnpm verify`.

## Mandatory article section order

Concept articles (`docs/concepts/`):

1. Frontmatter
2. Lead-with-this callout
3. What it is
4. How it works under the hood
5. Basic usage (legacy + modern)
6. Real-world patterns
7. Common mistakes
8. How this evolved
9. See also

Recipes (`docs/recipes/`):

1. Frontmatter
2. "What you'll build" callout
3. The scenario
4. Walkthrough
5. Variations
6. Trade-offs and common pitfalls
7. See also
8. References
9. Demo source

## Attribution policy

No per-article attribution. This repo carries a single top-level `LICENSE`
(CC BY 4.0 for prose, MIT for code) — do not reintroduce per-article
`## Author` sections, `original_authors` frontmatter, or a `CREDITS.md`.

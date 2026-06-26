# Contributing & Workflow

## Tool split (read this first)

| Tool | Job | Phases |
| --- | --- | --- |
| **Cursor** | Translate Vietnamese → English | Phase 1 only |
| **Claude** | Modernize translated articles + write gap nodes | Phases 2 & 3 |

Cursor never modernizes. Claude never translates from scratch (it adapts what Cursor produced).

---

## Frontmatter contract

Every article starts with this YAML block. The field set differs slightly between
translated and gap articles.

### Translated article (Cursor produces this)

```yaml
---
roadmap_node: "guards-resolvers"
title: "Guards & Resolvers"
file: "routing/guards-resolvers.md"
source_days: [30, 31, 32]
original_authors: ["Tiep Phan"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---
```

### Gap article (Claude produces this)

```yaml
---
roadmap_node: "signals"
title: "Signals"
file: "reactivity/signals.md"
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
> This article has no equivalent in the original 100 Days series.
> It covers Angular v16+ signals — written fresh for the current baseline.
```

### Upgraded article (Claude adds this block after upgrading)

After the frontmatter, add the callout:

```markdown
> **What changed since the original**
>
> - **Angular 9 (2020):** …what the original article covered…
> - **Angular 14:** …standalone components landed…
> - **Angular 17:** …@if/@for replaced *ngIf/*ngFor…
> - **Angular 22 (now):** …current recommended approach…
```

---

## File naming

- Filename = roadmap node ID exactly: `guards-resolvers.md`, `signals.md`, `data-binding.md`
- Place in the folder matching the roadmap section (see `progress.md`)
- Merge articles: one output file covering all source days listed in `source_days`

---

## Style

All voice, terminology, and English-variant decisions are in [`glossary.md`](./glossary.md).
Short version: American English, friendly tutorial voice, code identifiers stay as-is,
Angular API terms stay in English, drop social hashtags.

---

## Working discipline

- One unit at a time — stop for review before the next
- Update `progress.md` the moment a status changes
- "Keep rolling" = continue the queue without stopping
- Prefer explicit confirmation checkpoints over autonomous progression

---

## Legacy code marking

Cursor must add this comment above any code block using APIs deprecated in Angular 17+:

```
<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```

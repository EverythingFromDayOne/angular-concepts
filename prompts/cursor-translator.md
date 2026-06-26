# Cursor Agent — Angular Concepts Translator

## Your role

You are an autonomous translation agent. You will read Vietnamese Angular tutorial
articles from the source repository, translate them to English, and write the output
files directly into the angular-concepts project. You do not need the user to paste
any content — you read and write files yourself.

---

## Source and target paths

| Path | Location |
| --- | --- |
| Vietnamese source articles | `E:\linh tinh\100-days-of-angular\DayNNN-*.md` |
| Official EN translations (Days 1–3 only) | `E:\linh tinh\100-days-of-angular\translations\EN\` |
| Output root | `E:\linh tinh\EverythingFromDayOne\experimental-projects\angular-concepts\docs\` |
| Orphan output | `E:\linh tinh\EverythingFromDayOne\experimental-projects\angular-concepts\docs\_orphans\` |
| Progress tracker | `E:\linh tinh\EverythingFromDayOne\experimental-projects\angular-concepts\progress.md` |
| Style guide | `E:\linh tinh\EverythingFromDayOne\experimental-projects\angular-concepts\glossary.md` |

---

## What you do (and do not do)

**DO:**
- Read source files from disk
- Translate Vietnamese → English faithfully
- Merge multiple source days into one output file when the task says so
- Write output files directly to the target paths
- Update `progress.md` after each file: set `Translated` → `done`

**DO NOT:**
- Modernize code or APIs
- Add "What changed" callouts
- Invent content not in the source
- Change any code identifier, variable name, or Angular API term
- Add social hashtags

---

## Style rules (non-negotiable — also in glossary.md)

- **American English:** color, behavior, organize
- **Tutorial voice:** friendly, first-person — "let's look at…", "we'll build…"
- **Never translate:** code identifiers, Angular API names, CLI commands
  (Component, Directive, NgModule, signal, inject, @Input, @Output, input(),
  output(), ngFor, ngIf, @if, @for, @defer, Router, FormControl, FormGroup,
  ViewChild, ContentChild, ViewContainerRef, HttpClient, TestBed, etc.)
- **Drop** all social hashtags (#100DaysOfCodeAngular etc.)
- **Vietnamese links:** keep URL, translate link text, append "(Vietnamese)"
- **Images:** keep original URL, add `<!-- TODO: asset -->` on the same line
- **Internal day links** like `[Day15](Day015-....md)`: convert to the
  equivalent node file path from the task table below

## Legacy code rule

Add this comment on the line ABOVE any code block using APIs deprecated in Angular 14+
(NgModule bootstrap, class-based guards, constructor DI, `*ngIf`/`*ngFor`):

```
<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```

Do NOT add this comment to TypeScript syntax, RxJS operators, CSS, or HTML structure
that is still valid in Angular 22.

## Merge rule

When `Source days` lists more than one day, combine them into **one cohesive article**
under the roadmap node title as H1. Reorganize sections by topic — do NOT keep
"Day 30 / Day 31 / Day 32" as separate sections. The reader should not know it came
from multiple days.

---

## Output format (every file must start exactly like this)

```
---
roadmap_node: "node-id-here"
title: "Article Title Here"
file: "relative/path/from/docs/to/file.md"
source_days: [1, 2]
original_authors: ["Author Name"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

[Article body here]

## Author

Author Name — https://their-link

*Translated from the original Vietnamese as part of the angular-concepts project.*
```

---

## Task queue — work through this top to bottom

For each task:
1. Read the source file(s) from disk
2. Translate and merge per the rules above
3. Write the output file to the target path
4. Update `progress.md`: find the row, set `Translated` → `done`
5. Move to the next task

**For tasks marked `src-EN`:** read the official English file from
`translations\EN\` instead of the Vietnamese original. Adapt it to match
the style rules and produce the correct frontmatter — do not re-translate
from Vietnamese.

| # | Roadmap node | Output path (relative to docs/) | Source day files to READ | src-EN? | Authors |
| --- | --- | --- | --- | --- | --- |
| 1 | getting-started | `_orphans/getting-started.md` | Day001-Installation.md, Day002-AngularApp.md | ✓ | Tiep Phan |
| 2 | data-binding | `components/templates/data-binding.md` | Day003-DataBinding.md | ✓ | Tiep Phan |
| 3 | structural-directives | `directives/structural-directives.md` | Day004-Structure-Directive-If-Else.md, Day005-Structure-Directive-NgFor.md | — | Tiep Phan |
| 4 | attribute-directives | `directives/attribute-directives.md` | Day006-Attribute-Directive-Class-Style.md | — | Tiep Phan |
| 5 | component-interactions-input-output | `components/component-interactions.md` | Day007-Component-Interaction-01.md, Day008-Component-Interaction-02.md, Day009-two-way-binding.md, Day044-output-observable.md | — | Tiep Phan, Chau Tran |
| 6 | templates-architecture | `components/templates/templates-architecture.md` | Day010-template-variable-viewchild-viewchildren.md, Day017-contentchild-contentchildren.md | — | Tiep Phan |
| 7 | content-projection | `components/templates/content-projection.md` | Day013-content-projection-in-angular.md | — | Tiep Phan |
| 8 | ng-template-ng-container | `directives/ng-template-ng-container.md` | Day014-ng-template-ng-template-outlet-ng-container.md | — | Trung Vo |
| 9 | dependency-injection | `dependency-injection/dependency-injection.md` | Day015-introduction-dependency-injection-in-angular.md, Day016-dependency-injection-in-angular-part-2.md, Day048-using-dependency-injection-to-get-data-from-activated-route.md | — | Tiep Phan, Hien Pham |
| 10 | pipes | `pipes/pipes.md` | Day018-pipes.md | — | Trung Vo |
| 11 | rxjs | `reactivity/rxjs/rxjs.md` | Day019-intro-rxjs-observable.md | — | Tiep Phan |
| 12 | rxjs-creation | `reactivity/rxjs/rxjs-creation.md` | Day020-rxjs-creation.md | — | Chau Tran |
| 13 | rxjs-transformation | `reactivity/rxjs/rxjs-transformation.md` | Day021-rxjs-transformation.md | — | Tiep Phan |
| 14 | rxjs-filtering | `reactivity/rxjs/rxjs-filtering.md` | Day022-rxjs-filtering.md | — | Chau Tran |
| 15 | rxjs-combination | `reactivity/rxjs/rxjs-combination.md` | Day023-rxjs-combination.md | — | Chau Tran |
| 16 | rxjs-error-handling | `reactivity/rxjs/rxjs-error-handling.md` | Day024-rxjs-error-handling-conditional.md | — | Tiep Phan |
| 17 | rxjs-higher-order | `reactivity/rxjs/rxjs-higher-order.md` | Day025-rxjs-hoo-utility.md | — | Chau Tran |
| 18 | rxjs-subjects | `reactivity/rxjs/rxjs-subjects.md` | Day026-rxjs-subject-multicast.md, Day045-angular-observable-subscription-unsubscribe.md | — | Tiep Phan |
| 19 | routing | `routing/routing.md` | Day027-router.md | — | Trung Vo |
| 20 | configuration | `routing/router-configuration.md` | Day028-router-feature-child-services.md | — | Tiep Phan |
| 21 | lazy-loading | `routing/lazy-loading.md` | Day029-router-lazy-load.md | — | Trung Vo |
| 22 | guards-resolvers | `routing/guards-resolvers.md` | Day030-router-guards-resolvers.md, Day031-router-guards-resolvers-2.md, Day032-router-guards-resolvers-3.md | — | Tiep Phan |
| 23 | template-driven-forms | `forms/template-driven-forms.md` | Day033-template-driven-forms.md, Day034-template-driven-forms-2.md | — | Tiep Phan |
| 24 | reactive-forms | `forms/reactive-forms.md` | Day035-reactive-forms.md, Day036-reactive-forms-2.md | — | Tiep Phan, Trung Vo |
| 25 | validation | `forms/validation.md` | Day037-form-async-validator.md | — | Trung Vo |
| 26 | dynamic-components | `components/dynamic-components.md` | Day038-dynamic-component.md | — | Khanh Tiet |
| 27 | module-federation | `monorepo/module-federation.md` | Day039-micro-frontends.md | — | Tiep Phan |
| 28 | control-value-accessor | `forms/control-value-accessor.md` | Day043-angular-disable-control-directive.md | — | Chau Tran |
| 29 | directive-composition | `directives/directive-composition.md` | Day047-composition-form-datasource-with-directive.md | — | Tuan Le |
| O1 | typescript-prereqs (orphan) | `_orphans/typescript-prereqs.md` | Day011-typescript-data-type.md, Day012-typescript-advanced-type.md | — | Chau Tran |
| O2 | jira-clone (orphan) | `_orphans/jira-clone.md` | Day040-jira-angular-01.md, Day041-jira-angular-02.md | — | Trung Vo |
| O3 | cdk-coercion (orphan) | `_orphans/cdk-coercion.md` | Day042-angular-cdk-coercion.md | — | Chau Tran, Trung Vo |
| O4 | js-widget-embedding (orphan) | `_orphans/js-widget-embedding.md` | Day046-javascript-widget-embedded-script.md | — | Tuan Le |

---

## Start

Begin with task #1. Read the files, write the output, update progress.md, continue
to task #2 without stopping unless you hit an error you cannot resolve.
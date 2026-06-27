"""Sync progress.md Upgraded/Reviewed/Translated columns from docs frontmatter."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PROGRESS = ROOT / "progress.md"

# Manual metadata not in frontmatter (preserve from existing tracker)
ROADMAP_META = {
    "components/templates/data-binding.md": {"source_days": "3", "merge": "1:1", "model": "S"},
    "directives/structural-directives.md": {"source_days": "4, 5", "merge": "merge", "model": "S"},
    "directives/attribute-directives.md": {"source_days": "6", "merge": "1:1", "model": "S"},
    "components/component-interactions.md": {
        "source_days": "7, 8, 9, 44",
        "merge": "merge",
        "model": "S",
        "node": "component-interactions-input-output",
    },
    "components/templates/templates-architecture.md": {
        "source_days": "10, 17",
        "merge": "merge",
        "model": "S",
    },
    "components/templates/content-projection.md": {"source_days": "13", "merge": "1:1", "model": "S"},
    "directives/ng-template-ng-container.md": {"source_days": "14", "merge": "1:1", "model": "S"},
    "dependency-injection/dependency-injection.md": {
        "source_days": "15, 16, 48",
        "merge": "merge",
        "model": "O",
    },
    "pipes/pipes.md": {"source_days": "18", "merge": "1:1 → 2 sections", "model": "S"},
    "reactivity/rxjs/rxjs.md": {"source_days": "19", "merge": "seed", "model": "S", "node": "rxjs (intro)"},
    "reactivity/rxjs/rxjs-creation.md": {"source_days": "20", "merge": "sub", "model": "S", "node": "(rxjs-creation)"},
    "reactivity/rxjs/rxjs-transformation.md": {
        "source_days": "21",
        "merge": "sub",
        "model": "S",
        "node": "(rxjs-transformation)",
    },
    "reactivity/rxjs/rxjs-filtering.md": {"source_days": "22", "merge": "sub", "model": "S", "node": "(rxjs-filtering)"},
    "reactivity/rxjs/rxjs-combination.md": {"source_days": "23", "merge": "sub", "model": "S", "node": "(rxjs-combination)"},
    "reactivity/rxjs/rxjs-error-handling.md": {
        "source_days": "24",
        "merge": "sub",
        "model": "S",
        "node": "(rxjs-error-handling)",
    },
    "reactivity/rxjs/rxjs-higher-order.md": {
        "source_days": "25",
        "merge": "sub",
        "model": "S",
        "node": "(rxjs-higher-order)",
    },
    "reactivity/rxjs/rxjs-subjects.md": {"source_days": "26, 45", "merge": "merge", "model": "S", "node": "(rxjs-subjects)"},
    "routing/routing.md": {"source_days": "27", "merge": "1:1", "model": "S"},
    "routing/router-configuration.md": {"source_days": "28", "merge": "1:1", "model": "S", "node": "configuration"},
    "routing/lazy-loading.md": {"source_days": "29", "merge": "1:1", "model": "S"},
    "routing/guards-resolvers.md": {"source_days": "30, 31, 32", "merge": "merge", "model": "S"},
    "forms/template-driven-forms.md": {"source_days": "33, 34", "merge": "merge", "model": "S"},
    "forms/reactive-forms.md": {"source_days": "35, 36", "merge": "merge", "model": "S"},
    "forms/validation.md": {"source_days": "37", "merge": "1:1", "model": "S"},
    "components/dynamic-components.md": {"source_days": "38", "merge": "1:1", "model": "S"},
    "monorepo/module-federation.md": {"source_days": "39", "merge": "1:1", "model": "S"},
    "forms/control-value-accessor.md": {"source_days": "43", "merge": "1:1", "model": "S"},
    "directives/directive-composition.md": {"source_days": "47", "merge": "1:1", "model": "S"},
    "_orphans/getting-started.md": {
        "source_days": "1, 2",
        "merge": "merge",
        "model": "S",
        "node": "*(getting-started)*",
        "orphan": True,
    },
    "_orphans/typescript-prereqs.md": {"source_days": "11, 12", "orphan": True},
    "_orphans/jira-clone.md": {"source_days": "40, 41", "orphan": True},
    "_orphans/cdk-coercion.md": {"source_days": "42", "orphan": True},
    "_orphans/js-widget-embedding.md": {"source_days": "46", "orphan": True},
}

GAP_META = {
    "components/lifecycle.md": {"depends": "components", "model": "S"},
    "components/styling/view-encapsulation.md": {"depends": "components", "model": "S"},
    "tooling/sass.md": {"depends": "—", "model": "S"},
    "components/styling/angular-material.md": {"depends": "—", "model": "S"},
    "components/styling/ui-library-comparison.md": {"depends": "—", "model": "S", "node": "ui-library-comparison"},
    "components/animations.md": {"depends": "lifecycle", "model": "S"},
    "components/templates/control-flow.md": {"depends": "templates", "model": "S"},
    "components/change-detection.md": {"depends": "lifecycle, signals", "model": "O"},
    "components/angular-devtools.md": {"depends": "—", "model": "S"},
    "reactivity/signals.md": {"depends": "—", "model": "O"},
    "reactivity/signal-inputs.md": {"depends": "signals", "model": "S"},
    "reactivity/to-signal.md": {"depends": "signals, rxjs", "model": "S", "node": "to-signal-from-signal"},
    "routing/router-link.md": {"depends": "routing", "model": "S"},
    "routing/router-outlets.md": {"depends": "routing", "model": "S"},
    "http/http.md": {"depends": "—", "model": "S", "node": "http"},
    "http/interceptors.md": {"depends": "http", "model": "S"},
    "http/error-handling.md": {"depends": "http, rxjs", "model": "S", "node": "error-handling (http)"},
    "testing/unit-tests.md": {"depends": "DI", "model": "S"},
    "testing/integration-tests.md": {"depends": "unit-tests", "model": "S"},
    "testing/component-harnesses.md": {"depends": "integration-tests", "model": "S"},
    "testing/e2e-testing.md": {"depends": "—", "model": "S"},
    "state-management/ngrx.md": {"depends": "rxjs, signals", "model": "S"},
    "state-management/ngrx-signal-store.md": {"depends": "signals, ngrx", "model": "S"},
    "state-management/ngxs.md": {"depends": "—", "model": "S"},
    "rendering/defer-blocks.md": {"depends": "—", "model": "S"},
    "rendering/ssr-hydration.md": {"depends": "change-detection", "model": "O"},
    "rendering/view-ref.md": {"depends": "DI", "model": "S"},
    "forms/signal-forms.md": {"depends": "signals, reactive-forms", "model": "S"},
    "tooling/nx.md": {"depends": "—", "model": "S"},
    "tooling/angular-elements.md": {"depends": "DI", "model": "S"},
    "tooling/pwa.md": {"depends": "—", "model": "S"},
    "tooling/ionic.md": {"depends": "—", "model": "S"},
    "tooling/schematics.md": {"depends": "—", "model": "S"},
    "tooling/builders.md": {"depends": "—", "model": "S"},
    "tooling/built-in-i18n.md": {"depends": "—", "model": "S"},
    "tooling/ngx-translate.md": {"depends": "—", "model": "S"},
}


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    status: dict = {}
    in_status = False
    for line in m.group(1).split("\n"):
        if line.startswith("status:"):
            in_status = True
            continue
        if in_status:
            sm = re.match(r"  (\w+): (.+)", line)
            if sm:
                raw = sm.group(2).strip().strip('"')
                if raw == "true":
                    status[sm.group(1)] = True
                elif raw == "false":
                    status[sm.group(1)] = False
                else:
                    status[sm.group(1)] = raw
                continue
            if line and not line.startswith("  "):
                in_status = False
        km = re.match(r"^(\w+): (.+)", line)
        if km and not in_status:
            fm[km.group(1)] = km.group(2).strip().strip('"')
    fm["status"] = status
    return fm


def col(flag: bool) -> str:
    return "done" if flag else "–"


def load_articles():
    articles = []
    for p in sorted(DOCS.rglob("*.md")):
        rel = p.relative_to(DOCS).as_posix()
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        st = fm.get("status", {})
        articles.append(
            {
                "file": rel,
                "node": fm.get("roadmap_node", "—"),
                "translated": bool(st.get("translated")),
                "upgraded": bool(st.get("upgraded")),
                "reviewed": bool(st.get("reviewed")),
            }
        )
    return articles


def main():
    articles = {a["file"]: a for a in load_articles()}

    roadmap_rows = []
    orphan_rows = []
    gap_rows = []

    for file, meta in ROADMAP_META.items():
        a = articles[file]
        node = meta.get("node", f"`{a['node']}`" if a["node"] != "—" else "—")
        if not meta.get("orphan"):
            if not str(node).startswith("*") and not str(node).startswith("("):
                node = f"`{a['node']}`"
            roadmap_rows.append(
                (
                    node,
                    f"`{file}`",
                    meta["source_days"],
                    meta["merge"],
                    col(a["translated"]),
                    col(a["upgraded"]),
                    col(a["reviewed"]),
                    meta["model"],
                )
            )
        else:
            if file == "_orphans/getting-started.md":
                continue  # listed in roadmap table
            orphan_rows.append(
                (
                    f"`{file}`",
                    meta["source_days"],
                    col(a["translated"]),
                    col(a["upgraded"]),
                    col(a["reviewed"]),
                )
            )

    for file, meta in GAP_META.items():
        a = articles[file]
        node = meta.get("node", a["node"])
        if node != "—":
            node = f"`{node}`"
        gap_rows.append(
            (
                node,
                f"`{file}`",
                meta["depends"],
                col(a["upgraded"]),
                col(a["reviewed"]),
                meta["model"] if meta["model"] != "O" else "**O**",
            )
        )

    # getting-started in roadmap
    gs = articles["_orphans/getting-started.md"]
    roadmap_rows.insert(
        0,
        (
            "*(getting-started)*",
            "`_orphans/getting-started.md`",
            "1, 2",
            "merge",
            col(gs["translated"]),
            col(gs["upgraded"]),
            col(gs["reviewed"]),
            "S",
        ),
    )

    trans_done = sum(1 for a in articles.values() if a["translated"])
    upg_done = sum(1 for a in articles.values() if a["upgraded"])
    rev_done = sum(1 for a in articles.values() if a["reviewed"])
    gap_done = sum(1 for f in GAP_META if articles[f]["upgraded"])

    content = f"""# Progress Tracker

Single source of truth. Update this file the moment any status changes.

## Legend

**Origin**
- `translated` — article exists with teaching content from the original series
- `gap` — written fresh for Angular v22 (no prior article)

**Translated**
- `–` not started · `done` complete

**Upgraded**
- `–` not started · `done` modernized to Angular v22 with "What changed" callout

**Reviewed**
- `–` not started · `done` approved by Huy

**Model** (for upgrade/gap work)
- `S` = Sonnet 4.6 Max + Thinking ON
- `O` = Opus 4.7 Max + Thinking ON

---

## Roadmap articles

| Roadmap node ID | File | Source days | Merge type | Translated | Upgraded | Reviewed | Model |
| --- | --- | --- | --- | --- | --- | --- | --- |
"""
    for row in roadmap_rows:
        content += "| " + " | ".join(row) + " |\n"

    content += """
**Orphans** (no roadmap node yet)

| File | Source days | Translated | Upgraded | Reviewed |
| --- | --- | --- | --- | --- |
"""
    for row in orphan_rows:
        content += "| " + " | ".join(row) + " |\n"

    content += """
---

## Gap articles (written fresh for v22)

| Roadmap node ID | File | Depends on | Upgraded | Reviewed | Model |
| --- | --- | --- | --- | --- | --- |
"""
    for row in gap_rows:
        content += "| " + " | ".join(row) + " |\n"

    content += f"""
---

## Summary counts

| Category | Count | Translated | Upgraded | Reviewed |
| --- | --- | --- | --- | --- |
| Roadmap articles | {len(roadmap_rows)} | {sum(1 for r in roadmap_rows if r[4] == 'done')} | {sum(1 for r in roadmap_rows if r[5] == 'done')} | {sum(1 for r in roadmap_rows if r[6] == 'done')} |
| Orphan articles | {len(orphan_rows)} | {sum(1 for r in orphan_rows if r[2] == 'done')} | {sum(1 for r in orphan_rows if r[3] == 'done')} | {sum(1 for r in orphan_rows if r[4] == 'done')} |
| Gap articles | {len(gap_rows)} | — | {gap_done} | {sum(1 for r in gap_rows if r[4] == 'done')} |
| **Total** | **{len(articles)}** | **{trans_done}** | **{upg_done}** | **{rev_done}** |
"""

    PROGRESS.write_text(content, encoding="utf-8")
    print(f"Wrote {PROGRESS}")
    print(f"Articles: {len(articles)}, upgraded done: {upg_done}, reviewed done: {rev_done}")


if __name__ == "__main__":
    main()

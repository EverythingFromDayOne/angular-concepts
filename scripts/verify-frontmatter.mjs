#!/usr/bin/env node
/**
 * Verify frontmatter invariants for docs/concepts/ and docs/recipes/.
 *
 * - Every file under docs/concepts/ must have `article_id` matching its
 *   filename slug, `concept_folder` matching its path relative to
 *   docs/concepts/, and a `status` from the allowed set.
 * - Every file under docs/recipes/ must have `recipe_id` matching its
 *   filename slug.
 *
 * Usage: node scripts/verify-frontmatter.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  ".."
);
const CONCEPTS_ROOT = path.join(REPO_ROOT, "docs/concepts");
const RECIPES_ROOT = path.join(REPO_ROOT, "docs/recipes");
const ALLOWED_STATUSES = new Set(["draft", "needs-upgrade", "reviewed", "stub"]);

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(full, out);
    else if (ent.isFile() && ent.name.endsWith(".md")) out.push(full);
  }
  return out;
}

function parseFrontmatter(file) {
  const text = fs.readFileSync(file, "utf8");
  const m = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (!m) return null;
  const fm = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([a-zA-Z_]+):\s*(.*)$/);
    if (!kv) continue;
    let val = kv[2].trim();
    if (/^".*"$/.test(val)) val = val.slice(1, -1);
    fm[kv[1]] = val;
  }
  return fm;
}

const failures = [];
let checked = 0;

for (const file of walk(CONCEPTS_ROOT)) {
  checked++;
  const rel = path.relative(REPO_ROOT, file);
  const fm = parseFrontmatter(file);
  if (!fm) { failures.push(`${rel}: no frontmatter`); continue; }

  const expectedId = path.basename(file, ".md");
  if (fm.article_id !== expectedId) {
    failures.push(`${rel}: article_id "${fm.article_id}" !== filename slug "${expectedId}"`);
  }

  const expectedFolder = path.relative(CONCEPTS_ROOT, path.dirname(file)).split(path.sep).join("/");
  if (fm.concept_folder !== expectedFolder) {
    failures.push(`${rel}: concept_folder "${fm.concept_folder}" !== path "${expectedFolder}"`);
  }

  if (!ALLOWED_STATUSES.has(fm.status)) {
    failures.push(`${rel}: status "${fm.status}" not in allowed set {${[...ALLOWED_STATUSES].join(", ")}}`);
  }
}

for (const file of walk(RECIPES_ROOT)) {
  checked++;
  const rel = path.relative(REPO_ROOT, file);
  const fm = parseFrontmatter(file);
  if (!fm) { failures.push(`${rel}: no frontmatter`); continue; }

  const expectedId = path.basename(file, ".md");
  if (fm.recipe_id !== expectedId) {
    failures.push(`${rel}: recipe_id "${fm.recipe_id}" !== filename slug "${expectedId}"`);
  }
}

for (const f of failures) console.error(f);
console.log(`\nchecked ${checked} file(s); ${failures.length} frontmatter failure(s)`);
process.exit(failures.length ? 1 : 0);

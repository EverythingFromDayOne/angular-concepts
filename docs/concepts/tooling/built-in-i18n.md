---
roadmap_node: "built-in-i18n"
title: "Built-in i18n"
file: "tooling/built-in-i18n.md"
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

# Built-in i18n

> **Lead with this:** Angular's built-in i18n compiles translations directly
> into separate bundles at build time — one bundle per locale, each with
> the translated strings inlined, no runtime translation overhead. The tradeoff
> is that switching languages requires serving a different URL.

## What it is

Internationalization (i18n) is the process of preparing your app to be
displayed in multiple languages and regions. Angular ships a complete,
first-party i18n system as part of `@angular/localize`. It works in two steps:

1. **Mark** — annotate template elements and code strings with translation markers
2. **Extract → Translate → Build** — extract a source-language file, hand it to
   translators, then build one locale-specific bundle per language

The defining characteristic of Angular's built-in i18n is **compile-time
inlining**: when you build for French, the Angular compiler reads your
`messages.fr.xlf` translation file and replaces every marked string with its
French translation. The resulting bundle literally contains "Bonjour" where
your source has "Hello" — no translation service, no runtime lookup table,
no i18n overhead when the user loads the page.

**When to use built-in i18n vs ngx-translate:**

| Scenario | Use |
| --- | --- |
| App stays in one language per session, user switches by changing the URL | **Built-in i18n** |
| Zero runtime translation overhead — maximum performance | **Built-in i18n** |
| Runtime language switching without page reload | **ngx-translate** |
| Translations loaded dynamically from an API | **ngx-translate** |
| Mixed-language content on the same page | **ngx-translate** |

## How it works under the hood

### Old approach — manual translation services

Before Angular's i18n system, teams wrote their own:

```typescript
// Typical pre-i18n pattern — translation map + pipe or service
const translations = {
  'en': { 'welcome': 'Welcome', 'logout': 'Log out' },
  'fr': { 'welcome': 'Bienvenue', 'logout': 'Se déconnecter' },
};

@Injectable({ providedIn: 'root' })
export class TranslateService {
  private locale = 'en';
  translate(key: string): string {
    return translations[this.locale][key] ?? key;
  }
}
```

Problems: keys are stringly-typed strings (typos cause silent failures),
no tooling support (no IDE completion, no unused-key detection), plural and
gender forms require custom logic, and the translation workflow is entirely
manual — you'd update the map by hand and pray it stayed in sync with the UI.

### New approach — compiler-driven extraction and inlining

Angular's i18n system is built into the compiler pipeline:

**Extraction (once per dev cycle, or in CI):**

```
Templates with i18n attributes + TypeScript with $localize
        ↓
ng extract-i18n
        ↓
messages.xlf (XLIFF XML file listing every translatable string with its ID)
        ↓
Translator fills in <target> elements
        ↓
messages.fr.xlf, messages.de.xlf, messages.ar.xlf
```

**Build (per deployment):**

```
ng build --localize
        ↓
Compiler reads messages.fr.xlf
For every i18n-marked string or $localize call:
  Replace source string → French translation (inlined in JS)
        ↓
dist/my-app/fr/   ← complete app in French, no translation service
dist/my-app/de/   ← complete app in German, no translation service
dist/my-app/en-US/ ← complete app in English (source locale)
```

The French bundle's JavaScript literally contains `"Bonjour"` where the
English source says `"Hello"`. At runtime there's no translation lookup at
all — the strings are already there.

This is what makes the built-in system fast and why it doesn't support
runtime switching: the language is baked into the bundle. To show French,
you serve the French bundle at `/fr/`. To show German, you serve the German
bundle at `/de/`.

## Setup

```bash
ng add @angular/localize
```

This installs the package and adds `/// <reference types="@angular/localize" />`
to `main.ts` (required for `$localize` to work in TypeScript).

## Marking content for translation

### The i18n attribute — template elements

Add `i18n` to any element whose text content should be translated:

```html
<!-- Basic — Angular generates an automatic ID from the content hash -->
<h1 i18n>Hello, world!</h1>
<p i18n>Welcome to our application.</p>

<!-- With meaning|description — helps translators understand context -->
<h1 i18n="site header|The main page heading">Hello, world!</h1>
<p i18n="home page|Welcome message for new users">
  Welcome to our application.
</p>

<!-- With custom ID — stable across content changes, required if content changes often -->
<h1 i18n="@@site-header">Hello, world!</h1>
<h1 i18n="site header|Greeting@@site-header">Hello, world!</h1>
```

The metadata format inside the `i18n` attribute value:
```
i18n="meaning|description@@custom-id"
```
All three parts are optional. Providing a custom `@@id` is important for
strings that may be rephrased — without it, Angular generates the ID from
the content hash, so any wording change creates a new ID and loses existing
translations.

### Marking HTML attributes

To translate an attribute (like `alt`, `title`, `placeholder`), use `i18n-{attrname}`:

```html
<!-- Translate the alt attribute -->
<img src="logo.png" i18n-alt alt="Angular logo" />

<!-- Translate placeholder on an input -->
<input i18n-placeholder placeholder="Search…" />

<!-- Translate aria-label for accessibility -->
<button i18n-aria-label aria-label="Close dialog">×</button>
```

### Marking code strings — $localize

For strings outside templates (TypeScript, Angular services, etc.), use the
`$localize` tagged template literal:

```typescript
import '@angular/localize/init';

// Basic
const message = $localize`Hello, world!`;

// With metadata (meaning|description@@id)
const header = $localize`:site header|Main page heading@@site-header:Hello, world!`;

// With dynamic values — name the placeholder with :name: syntax
const greeting = $localize`Hello, ${userName}:userName:!`;
const summary = $localize`There are ${items.length}:itemCount: items in your cart.`;

// In a service
@Injectable({ providedIn: 'root' })
export class NotificationService {
  getWelcomeMessage(name: string): string {
    return $localize`Welcome back, ${name}:name:!`;
  }
}
```

The `:placeholderName:` syntax after each interpolation is recommended — it
appears in the translation file and helps translators understand what the
expression represents. Without it, Angular auto-generates placeholder names
like `INTERPOLATION` or `INTERPOLATION_1`, which are unhelpful to translators.

### ICU expressions — plurals and selects

For grammatically correct translations, Angular supports ICU (International
Components for Unicode) expressions inside `i18n`-marked elements:

**Plural:**

```html
<!-- Adapts to the user's locale plural rules automatically -->
<p i18n>
  You have {itemCount, plural,
    =0 {no notifications}
    =1 {one notification}
    other {{{ itemCount }} notifications}
  }.
</p>
```

Different languages have different plural categories. English has two (one,
other). Arabic has six. Russian has three. Angular's `@angular/common`
includes ICU plural rules for hundreds of locales — your template stays the
same; the locale's rule determines which category to use.

**Select (gender, status, etc.):**

```html
<p i18n>The author is
  {gender, select,
    male {a male author}
    female {a female author}
    other {an author}
  }.
</p>
```

**Nested ICU:**

```html
<p i18n>
  {gender, select,
    male {He sent {count, plural, =1 {a message} other {{{count}} messages}}}
    female {She sent {count, plural, =1 {a message} other {{{count}} messages}}}
    other {They sent {count, plural, =1 {a message} other {{{count}} messages}}}
  }
</p>
```

## Extracting and translating

### Step 1 — Extract to XLIFF

```bash
ng extract-i18n
# Output: messages.xlf in the project root

# With options
ng extract-i18n --output-path src/locale --out-file messages.xlf --format xlf2
```

**Supported formats:**

| Format | Option | Notes |
| --- | --- | --- |
| XLIFF 1.2 | `xlf` (default) | Most tool support |
| XLIFF 2.0 | `xlf2` | Newer, more features |
| XMB | `xmb` | Google format (pairs with XTB for translations) |
| JSON | `json` | Simple but less metadata |
| ARB | `arb` | Flutter/Dart compatible |

### Step 2 — Copy and translate

Create one translation file per target locale:

```bash
cp src/locale/messages.xlf src/locale/messages.fr.xlf
cp src/locale/messages.xlf src/locale/messages.de.xlf
```

In each copy, translators add a `<target>` element alongside each `<source>`:

```xml
<!-- messages.fr.xlf -->
<trans-unit id="site-header" datatype="html">
  <source>Hello, world!</source>
  <target>Bonjour le monde !</target>
  <note priority="1" from="description">Main page heading</note>
</trans-unit>

<trans-unit id="3935776912">
  <source>Welcome to our application.</source>
  <target>Bienvenue dans notre application.</target>
</trans-unit>
```

### Step 3 — Configure angular.json

```json
{
  "projects": {
    "my-app": {
      "i18n": {
        "sourceLocale": "en-US",
        "locales": {
          "fr": {
            "translation": "src/locale/messages.fr.xlf",
            "baseHref": "/fr/"
          },
          "de": {
            "translation": "src/locale/messages.de.xlf",
            "baseHref": "/de/"
          },
          "ar": {
            "translation": "src/locale/messages.ar.xlf",
            "baseHref": "/ar/"
          }
        }
      },
      "architect": {
        "build": {
          "options": {
            "localize": true
          }
        }
      }
    }
  }
}
```

### Step 4 — Build all locales

```bash
# Build all configured locales at once
ng build --localize

# Output:
# dist/my-app/en-US/   ← source locale
# dist/my-app/fr/      ← French
# dist/my-app/de/      ← German
# dist/my-app/ar/      ← Arabic

# Build a single locale (faster during development)
ng build --localize fr

# Serve a single locale in dev mode (only one locale at a time)
ng serve --localize fr
```

## Real-world patterns

### Pattern 1 — Language switcher via navigation

Since each locale is a separate bundle at a different path, the language
switcher is a simple anchor tag, not a reactive state change:

```typescript
@Component({
  selector: 'app-lang-switcher',
  standalone: true,
  template: `
    <nav>
      @for (locale of locales; track locale.code) {
        <a
          [href]="'/' + locale.code + currentPath()"
          [class.active]="locale.code === currentLocale"
          [lang]="locale.code"
        >
          {{ locale.label }}
        </a>
      }
    </nav>
  `,
})
export class LangSwitcherComponent {
  private router = inject(Router);

  locales = [
    { code: 'en-US', label: 'English' },
    { code: 'fr', label: 'Français' },
    { code: 'de', label: 'Deutsch' },
  ];

  currentLocale = $localize.locale ?? 'en-US';

  currentPath = toSignal(
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map((e: NavigationEnd) => e.url),
    ),
    { initialValue: this.router.url }
  );
}
```

### Pattern 2 — Locale-aware date, number, and currency pipes

Angular's built-in pipes automatically adapt to the active locale — no
additional configuration needed once `@angular/localize` is set up:

```html
<!-- Renders differently per locale -->
<p>{{ orderDate | date:'longDate' }}</p>
<!-- en-US: "June 26, 2026" -->
<!-- fr:    "26 juin 2026" -->
<!-- de:    "26. Juni 2026" -->

<p>{{ price | currency }}</p>
<!-- en-US: "$1,299.99" -->
<!-- fr:    "1 299,99 €"  (if currency is EUR) -->
<!-- de:    "1.299,99 €" -->

<p>{{ ratio | percent:'1.1-2' }}</p>
<!-- en-US: "73.5%" -->
<!-- de:    "73,5 %" (note space before %) -->
```

### Pattern 3 — Detecting missing translations in CI

Add a build step to catch untranslated strings before shipping:

```json
// angular.json — fail the build on missing translations
"build": {
  "options": {
    "i18nMissingTranslation": "error"    // "error" | "warning" | "ignore"
  }
}
```

With `"error"`, the build fails if any translation unit in the XLF file
is missing a `<target>` element. Add this to CI to prevent shipping
untranslated strings.

## Common mistakes

### Mistake 1 — Omitting custom IDs on frequently-changing strings

Without a custom `@@id`, Angular generates an ID from the content hash.
Changing "Hello" to "Hi" generates a new ID — all existing translations
for that string become orphaned and must be re-translated:

```html
<!-- ❌ No custom ID — content change orphans translations -->
<h1 i18n>Hello, {{ name }}!</h1>

<!-- ✅ Custom ID — stable across content changes -->
<h1 i18n="@@greeting-header">Hello, {{ name }}!</h1>
```

Use custom IDs for any string that might be rephrased without changing
its meaning — headings, buttons, labels.

### Mistake 2 — Using ng serve with multiple locales

`ng serve` (the dev server) supports only one locale at a time. Running
`ng serve` without `--localize` serves the source locale. Setting
`"localize": true` in options and running `ng serve` is an error:

```bash
# ❌ Error — dev server can't serve multiple locales simultaneously
ng serve   # with "localize": true in angular.json options

# ✅ Specify one locale for development
ng serve --localize fr

# ✅ Or test multi-locale with a production build
ng build --localize && npx http-server dist/my-app
```

### Mistake 3 — Forgetting to name interpolation placeholders

Unnamed placeholders appear in XLIFF as `INTERPOLATION`, `INTERPOLATION_1`,
etc. Translators can't tell what a number in position 2 represents:

```typescript
// ❌ Unnamed — translator sees "INTERPOLATION" and "INTERPOLATION_1"
$localize`Hello ${firstName}, you have ${count} messages.`;

// ✅ Named — translator sees "firstName" and "messageCount"
$localize`Hello ${firstName}:firstName:, you have ${count}:messageCount: messages.`;
```

### Mistake 4 — Building without the localize flag

`ng build` without `--localize` builds only the source locale, regardless
of what's configured in `angular.json`. To get all locale bundles:

```bash
# ❌ Only builds source locale — French/German bundles not generated
ng build

# ✅ Builds all configured locales
ng build --localize

# ✅ Or set localize: true in the build configuration
# angular.json: "configurations": { "production": { "localize": true } }
ng build --configuration=production
```

## How this evolved

> - **Angular 2–8 (2016–2019):** Built-in i18n existed but the tooling was
>   basic. Only XLIFF 1.2 supported. Merging translations required a separate
>   `--i18n-file` build flag. The workflow was functional but clunky.
>
> - **Angular 9 (2020):** `@angular/localize` introduced as the foundation
>   for all i18n tooling. `$localize` tagged template literal stable. The
>   compile-time inlining model formalized. Multiple locale builds now
>   produced in one `ng build --localize` command.
>
> - **Angular 11 (2020):** XLIFF 2.0, JSON, and ARB format support added.
>   `i18nMissingTranslation` build option introduced.
>
> - **Angular 14+ (2022):** Standalone component i18n works identically to
>   NgModule components — no changes required to use i18n with standalone
>   components.
>
> - **Angular 22 (now):** The i18n API is stable and unchanged. The built-in
>   i18n system is the right choice for apps where each locale session maps
>   to a fixed URL. For runtime language switching, see [ngx-translate](./ngx-translate.md).

## See also

- [ngx-translate](./ngx-translate.md) — runtime language switching;
  the right choice when users switch languages without reloading
- [Builders](./builders.md) — the `@angular/build:extract-i18n` builder
  that powers `ng extract-i18n`
- [Official docs — i18n overview](https://angular.dev/guide/i18n)
- [Official docs — Prepare component for translation](https://angular.dev/guide/i18n/prepare)
- [Official docs — Work with translation files](https://angular.dev/guide/i18n/translation-files)
- [Official docs — Deploy multiple locales](https://angular.dev/guide/i18n/deploy)

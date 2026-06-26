---
roadmap_node: "ngx-translate"
title: "ngx-translate"
file: "tooling/ngx-translate.md"
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
> Written fresh for Angular v22, ngx-translate v18.

# ngx-translate

> **Lead with this:** ngx-translate loads translations at runtime from JSON
> files, so users can switch languages instantly without a page reload —
> the tradeoff compared to Angular's built-in i18n, which inlines translations
> at build time for zero runtime overhead.

## What it is

`@ngx-translate/core` is the most widely adopted third-party i18n library
for Angular. Instead of requiring a separate bundle per language (Angular's
built-in approach), ngx-translate ships one bundle and fetches the appropriate
translation JSON file at runtime.

**When to pick ngx-translate over built-in i18n:**

| Scenario | Built-in i18n | ngx-translate |
| --- | --- | --- |
| Language switching without page reload | ❌ | ✅ |
| One bundle, multiple languages | ❌ | ✅ |
| Zero runtime translation overhead | ✅ | ❌ (JSON parse + lookup) |
| Translations loaded from an API | ❌ | ✅ |
| ICU plural/gender expressions | ✅ built-in | ❌ manual |
| Teams with translation TMS integration | Both work | Both work |

For new projects where compile-time performance and simplicity matter, start
with built-in i18n. Reach for ngx-translate when you need runtime switching
or dynamic translation loading.

## How it works under the hood

### The key difference — runtime vs compile-time

Angular's built-in i18n inlines translations into the bundle at build time.
Each locale is a complete, separate JS bundle. The user never downloads
translations they don't use, but switching languages means loading a new
bundle (a full navigation or page reload).

ngx-translate works differently:

```
App bootstraps
     ↓
TranslateService.use('en') called
     ↓
TranslateHttpLoader fetches /i18n/en.json from the server
     ↓
Translations stored in-memory as a JavaScript object
     ↓
{{ 'HELLO' | translate }} → looks up 'HELLO' in the object → renders 'Hello'

User switches to French:
     ↓
TranslateService.use('fr') called
     ↓
Loader fetches /i18n/fr.json (or returns from cache)
     ↓
In-memory translations replaced with French object
     ↓
All TranslatePipe / translate() instances re-render automatically
No page reload. Same bundle. New language.
```

**How pipes and signals react:** Since ngx-translate v18, `TranslatePipe`
is powered by Angular signals internally. When `use('fr')` fires, a
translations signal updates, which invalidates all computed values and
template views that read it — the re-render is pure signal propagation,
not manual `ChangeDetectorRef.markForCheck()`.

The tradeoff: every `{{ key | translate }}` performs a key lookup at render
time. In large templates this is fast in practice but isn't free like
compile-time inlining.

## Setup

```bash
npm install @ngx-translate/core @ngx-translate/http-loader
```

```typescript
// app.config.ts
import { ApplicationConfig, inject, provideAppInitializer } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import {
  provideTranslateService, TranslateService
} from '@ngx-translate/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(),              // TranslateHttpLoader uses HttpClient
    provideTranslateService({
      lang: 'en',                     // default language on startup
      fallbackLang: 'en',            // fallback when a key is missing
      loader: provideTranslateHttpLoader({
        prefix: '/i18n/',            // serves /i18n/en.json, /i18n/fr.json
        suffix: '.json',
      }),
    }),
    // Optional: load translations before the app renders
    provideAppInitializer(() =>
      inject(TranslateService).use('en')
    ),
  ],
};
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13, ngx-translate v12–v14)
@NgModule({
  imports: [
    HttpClientModule,
    TranslateModule.forRoot({
      defaultLanguage: 'en',
      loader: {
        provide: TranslateLoader,
        useFactory: (http: HttpClient) =>
          new TranslateHttpLoader(http, '/i18n/', '.json'),
        deps: [HttpClient],
      },
    }),
  ],
})
export class AppModule {}
```

## Translation files

Translation files are plain JSON. Use nested keys for organization:

```json
// src/i18n/en.json
{
  "COMMON": {
    "SAVE": "Save",
    "CANCEL": "Cancel",
    "LOADING": "Loading…"
  },
  "AUTH": {
    "LOGIN": "Log in",
    "LOGOUT": "Log out",
    "WELCOME": "Welcome, {{ name }}!",
    "ERRORS": {
      "INVALID_CREDENTIALS": "Invalid email or password"
    }
  },
  "NOTIFICATIONS": {
    "COUNT_ONE": "You have 1 notification",
    "COUNT_OTHER": "You have {{ count }} notifications"
  }
}
```

```json
// src/i18n/fr.json
{
  "COMMON": {
    "SAVE": "Enregistrer",
    "CANCEL": "Annuler",
    "LOADING": "Chargement…"
  },
  "AUTH": {
    "LOGIN": "Se connecter",
    "LOGOUT": "Se déconnecter",
    "WELCOME": "Bienvenue, {{ name }} !",
    "ERRORS": {
      "INVALID_CREDENTIALS": "Email ou mot de passe invalide"
    }
  },
  "NOTIFICATIONS": {
    "COUNT_ONE": "Vous avez 1 notification",
    "COUNT_OTHER": "Vous avez {{ count }} notifications"
  }
}
```

## Using translations in components

### TranslatePipe — in templates

Import `TranslatePipe` in each standalone component that needs it:

```typescript
import { Component } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <nav>
      <a>{{ 'AUTH.LOGIN' | translate }}</a>
      <a>{{ 'AUTH.LOGOUT' | translate }}</a>

      <!-- With interpolation parameters -->
      <p>{{ 'AUTH.WELCOME' | translate:{ name: currentUser().name } }}</p>
    </nav>
  `,
})
export class HeaderComponent { /* ... */ }
```

### The translate() signal function — v18 (recommended for component code)

The new standalone `translate()` function returns a `Signal<string>` that
automatically updates when the language changes:

```typescript
import { Component, inject } from '@angular/core';
import { translate, TranslateService, TranslatePipe } from '@ngx-translate/core';

@Component({
  selector: 'app-page-title',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <title>{{ pageTitle() }}</title>
    <h1>{{ 'HOME.HEADING' | translate }}</h1>
  `,
})
export class PageTitleComponent {
  // Signal that auto-updates on language change — use in computed(), effect(), or template
  pageTitle = translate('HOME.TITLE');

  // With parameters — reactive parameters via a signal
  userGreeting = translate('AUTH.WELCOME', { name: 'Alice' });
}
```

### TranslateService — for programmatic translations

For toasts, alerts, document titles, or any translation needed in TypeScript
code:

```typescript
import { Component, inject, computed } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

@Component({ /* ... */ })
export class NotificationComponent {
  private translate = inject(TranslateService);

  // currentLang is a Signal<Language | null> in v18+ — call it as a function
  currentLang = this.translate.currentLang;    // Signal<'en' | 'fr' | null>

  // Synchronous translation (only safe after translations are loaded)
  getInstant(key: string): string {
    return this.translate.instant(key);
  }

  // Observable — emits once when loaded
  getAsync(key: string): void {
    this.translate.get('AUTH.ERRORS.INVALID_CREDENTIALS').subscribe(msg => {
      this.showToast(msg);
    });
  }

  // Stream — emits immediately AND re-emits on language change
  watchedMessage = this.translate.stream('NOTIFICATIONS.COUNT_OTHER', { count: 5 });

  // Switch language
  switchToFrench(): void {
    this.translate.use('fr');   // fetches fr.json if not cached, then updates all pipes/signals
  }
}
```

### *translateBlock — translating several keys in one block

The `TranslateBlockDirective` is a structural directive that exposes a typed
`t()` function to translate multiple keys cleanly in a template block:

```typescript
import { TranslatePipe, TranslateBlockDirective } from '@ngx-translate/core';

@Component({
  standalone: true,
  imports: [TranslatePipe, TranslateBlockDirective],
  template: `
    <ng-container *translateBlock="let t">
      <button>{{ t('COMMON.SAVE') }}</button>
      <button>{{ t('COMMON.CANCEL') }}</button>
      <p>{{ t('AUTH.WELCOME', { name: user().name }) }}</p>
    </ng-container>
  `,
})
export class FormFooterComponent { /* ... */ }
```

`*translateBlock` is the recommended replacement for the deprecated
content-as-key pattern (`<div translate>KEY</div>`, removed in v19).

## Real-world patterns

### Pattern 1 — Language switcher

```typescript
@Component({
  selector: 'app-lang-switcher',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <div class="lang-switcher">
      @for (lang of availableLangs; track lang.code) {
        <button
          [class.active]="currentLang() === lang.code"
          (click)="switchLang(lang.code)"
        >
          {{ lang.label }}
        </button>
      }
    </div>
  `,
})
export class LangSwitcherComponent {
  private translate = inject(TranslateService);

  currentLang = this.translate.currentLang;  // Signal — reads reactively in template

  availableLangs = [
    { code: 'en', label: 'English' },
    { code: 'fr', label: 'Français' },
    { code: 'de', label: 'Deutsch' },
  ];

  switchLang(lang: string): void {
    this.translate.use(lang);
    localStorage.setItem('preferred-lang', lang);
  }
}
```

```typescript
// app.config.ts — restore saved language on startup
provideAppInitializer(() => {
  const translate = inject(TranslateService);
  const saved = localStorage.getItem('preferred-lang') ?? 'en';
  return translate.use(saved);
})
```

### Pattern 2 — Lazy-loaded feature translations

For large apps, load only the global translations at startup and merge
feature-specific translations when a route loads:

```typescript
// feature/feature.routes.ts
export const featureRoutes: Routes = [
  {
    path: 'dashboard',
    providers: [
      {
        provide: APP_INITIALIZER,
        useFactory: (http: HttpClient, translate: TranslateService) => () =>
          http.get(`/i18n/dashboard/en.json`).pipe(
            tap(translations => translate.setTranslation('en', translations, true)),
          ).toPromise(),
        deps: [HttpClient, TranslateService],
        multi: true,
      },
    ],
    component: DashboardComponent,
  },
];
```

The `true` third argument to `setTranslation()` merges into existing
translations rather than replacing them.

### Pattern 3 — Custom MissingTranslationHandler

Log missing keys in development; return the key as a fallback in production:

```typescript
import { MissingTranslationHandler, MissingTranslationHandlerParams } from '@ngx-translate/core';

export class LoggingMissingTranslationHandler implements MissingTranslationHandler {
  handle(params: MissingTranslationHandlerParams): string {
    if (!environment.production) {
      console.warn(`[i18n] Missing translation for key: "${params.key}"`);
    }
    return params.key;   // Show key as fallback rather than empty string
  }
}

// Register in provideTranslateService
provideTranslateService({
  lang: 'en',
  missingTranslationHandler: {
    provide: MissingTranslationHandler,
    useClass: LoggingMissingTranslationHandler,
  },
})
```

## Testing

Use a static translation loader in tests to avoid HTTP dependencies:

```typescript
import { TestBed } from '@angular/core/testing';
import {
  provideTranslateService,
  provideTranslateLoader,
  TranslateLoader,
  Translation,
} from '@ngx-translate/core';
import { of } from 'rxjs';

const testTranslations: { [key: string]: Translation } = {
  en: {
    'AUTH.LOGIN': 'Log in',
    'AUTH.WELCOME': 'Welcome, {{ name }}!',
  },
};

class StaticTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of(testTranslations[lang] ?? {});
  }
}

describe('HeaderComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HeaderComponent],
      providers: [
        provideTranslateService({
          lang: 'en',
          loader: provideTranslateLoader(StaticTranslateLoader),
        }),
      ],
    });
  });
});
```

## Common mistakes

### Mistake 1 — Reading currentLang as a string (v18 breaking change)

In ngx-translate v17 and earlier, `currentLang` was a plain string property.
In v18 it became a `Signal<Language | null>`. Code that reads it directly
without calling it now gets a signal object, not the language code:

```typescript
// ❌ Returns a Signal object in v18 — not the language string
if (this.translate.currentLang === 'en') { ... }

// ✅ Call the signal
if (this.translate.currentLang() === 'en') { ... }

// ✅ Or use the non-reactive snapshot helper
if (this.translate.getCurrentLang() === 'en') { ... }
```

### Mistake 2 — Using instant() before translations are loaded

`instant()` reads translations synchronously from the current in-memory state.
If called before the language file has loaded, it returns the key (or the
missing-translation handler's result):

```typescript
// ❌ Called too early — translations not loaded yet, returns the key
export class AppComponent {
  title = this.translate.instant('APP.TITLE');   // probably returns 'APP.TITLE'
  constructor(private translate: TranslateService) {}
}

// ✅ Use translate() signal — resolves when translations are available
export class AppComponent {
  title = translate('APP.TITLE');   // Signal — empty until loaded, then fills in
}

// ✅ Or wait for translations to load via get()
export class AppComponent {
  title = '';
  constructor(private translate: TranslateService) {
    translate.get('APP.TITLE').subscribe(t => this.title = t);
  }
}
```

### Mistake 3 — Using deprecated content-as-key syntax

The `<div translate>KEY</div>` pattern was deprecated in v18 and will be
removed in v19. It's also hard to read — the key isn't in the attribute where
you'd expect it:

```html
<!-- ❌ Deprecated — content as translation key -->
<span translate>AUTH.LOGIN</span>

<!-- ✅ Pipe — clear and explicit -->
<span>{{ 'AUTH.LOGIN' | translate }}</span>

<!-- ✅ translate() signal — for use in component logic -->
<span>{{ loginLabel() }}</span>
```

### Mistake 4 — Forgetting to import TranslatePipe per component

`TranslatePipe` is a standalone pipe that must be imported in each component's
`imports` array. Forgetting it causes the pipe to be treated as unknown and
either errors or renders nothing:

```typescript
// ❌ TranslatePipe not imported — {{ 'KEY' | translate }} renders nothing
@Component({
  standalone: true,
  imports: [],
  template: `<p>{{ 'AUTH.LOGIN' | translate }}</p>`,
})

// ✅ TranslatePipe imported
@Component({
  standalone: true,
  imports: [TranslatePipe],
  template: `<p>{{ 'AUTH.LOGIN' | translate }}</p>`,
})
```

## How this evolved

> - **ngx-translate v1–8 (2015–2019):** The go-to Angular i18n library before
>   Angular's own `@angular/localize` existed. NgModule-only setup,
>   `TranslateModule.forRoot()`. Imperative API with `getDefaultLang()` and
>   `setDefaultLang()`.
>
> - **ngx-translate v9–14 (2019–2022):** Maintained alongside Angular's
>   growing built-in i18n. API largely stable. The use case narrowed: Angular's
>   built-in i18n gained ICU support, XLIFF2, and multi-locale builds.
>   ngx-translate remained the choice for runtime switching.
>
> - **ngx-translate v15–17 (2023–2024):** Standalone component support. The
>   library's API modernized significantly. `setDefaultLang()` and
>   `defaultLang` deprecated in favor of `fallbackLang`.
>
> - **ngx-translate v18 (2025):** **Signal-first rewrite.** `currentLang` and
>   `fallbackLang` became `Signal<Language | null>`. `isLoading` signal added.
>   `TranslatePipe` internals replaced with signal-based reactivity. New
>   standalone `translate()` signal function. `*translateBlock` directive.
>   Content-as-key pattern deprecated. Angular 18–22 compatible. This is the
>   stable v18 API documented in this article.

## See also

- [Built-in i18n](./built-in-i18n.md) — Angular's compile-time alternative
  with zero runtime overhead; covers when to use each approach
- [Signals](../reactivity/signals.md) — the Angular signal primitives that
  power ngx-translate v18's reactivity
- [Official ngx-translate docs](https://ngx-translate.org)
- [ngx-translate GitHub](https://github.com/ngx-translate/core)
- [@ngx-translate/http-loader](https://github.com/ngx-translate/http-loader)

---
roadmap_node: "control-flow"
title: "Built-in Control Flow"
file: "components/templates/control-flow.md"
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
> Written fresh for Angular v17+, baseline v22.

# Built-in Control Flow

> **Lead with this:** Angular 17 replaced `*ngIf`, `*ngFor`, and `*ngSwitch`
> with first-class `@if`, `@for`, and `@switch` syntax — no imports, better
> performance, and proper TypeScript type narrowing built in.

## What it is

Every template needs to conditionally show content, repeat over lists, and
branch on values. Before Angular 17, you did this with **structural directives**
— `*ngIf`, `*ngFor`, `*ngSwitch` — imported from `CommonModule`. They worked,
but they had friction: you had to remember to import `CommonModule` (or the
individual directive), type narrowing didn't flow through them cleanly, and
`trackBy` was optional (so most developers skipped it and paid the performance
price).

Angular 17 introduced **built-in control flow** — `@if`, `@for`, `@switch` —
as first-class template syntax handled directly by the compiler. No imports.
`track` is required in `@for` (so the performance optimization is never
accidental). And `@if` narrows TypeScript types inside its block exactly the
way an `if` statement does in regular TypeScript.

There is also `@defer` for lazy rendering — it shares the `@` syntax but it
is a separate, larger feature with its own article. See
[@defer Blocks](../../rendering/defer-blocks.md).

## How it works under the hood

Structural directives like `*ngIf` work by injecting `TemplateRef` and
`ViewContainerRef` and programmatically inserting or removing DOM fragments at
runtime. They are regular Angular directives, which means they need to be
declared or imported before the compiler recognizes them.

The new `@if`, `@for`, and `@switch` blocks are not directives. They are part
of the **Angular template compiler's grammar** — recognized and transformed at
compile time before any JavaScript runs. The compiler emits optimized
instruction calls directly rather than going through the directive instantiation
path.

Two concrete consequences:

**No import required.** Because the compiler handles `@if` and `@for` natively,
there is no directive to import. `CommonModule`, `NgIf`, `NgFor`, and `NgSwitch`
are completely unnecessary when you use the new syntax.

**`track` is required, not optional.** The old `*ngFor` had an optional
`trackBy` function that most developers skipped. Without it, Angular
re-creates every DOM node on every change — even if only one item changed.
The new `@for` makes `track` mandatory. The compiler enforces the optimization
so you can't accidentally skip it.

## Basic usage

### @if — conditional rendering

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<!-- NgModule / legacy approach with *ngIf -->
<div *ngIf="isLoggedIn; else loggedOut">
  <p>Welcome back, {{ user.name }}</p>
</div>
<ng-template #loggedOut>
  <p>Please sign in.</p>
</ng-template>
```

```html
<!-- Modern @if — no import, reads like TypeScript -->
@if (isLoggedIn) {
  <p>Welcome back, {{ user.name }}</p>
} @else {
  <p>Please sign in.</p>
}
```

`@else if` chains are first-class — no nested `*ngIf` or extra template
references needed:

```html
@if (status === 'loading') {
  <app-spinner />
} @else if (status === 'error') {
  <app-error-message [message]="errorMessage" />
} @else {
  <app-content [data]="data" />
}
```

#### Type narrowing inside @if

This is the improvement that makes the biggest practical difference. With
`*ngIf`, TypeScript couldn't narrow types inside the template. With `@if`, it
can — in exactly the same way as a regular TypeScript `if` block.

```typescript
// Component
interface User {
  name: string;
  avatar: string;
}

@Component({ ... })
export class ProfileComponent {
  user = signal<User | null>(null);
}
```

```html
<!-- *ngIf — TypeScript sees user as User | null inside, you need the !. operator -->
<div *ngIf="user()">
  <img [src]="user()!.avatar" />  <!-- non-null assertion required -->
</div>

<!-- @if — TypeScript narrows to User inside the block, no ! needed -->
@if (user(); as u) {
  <img [src]="u.avatar" />        <!-- u is User, not User | null -->
}
```

The `as` alias (`;  as u`) captures the checked value so you don't call the
signal or expression multiple times. Use it whenever the condition is a
function call or a complex expression.

### @for — list rendering

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<!-- NgModule / legacy approach with *ngFor -->
<ul>
  <li *ngFor="let item of items; trackBy: trackById">
    {{ item.name }}
  </li>
</ul>
```

```html
<!-- Modern @for — track is required -->
<ul>
  @for (item of items; track item.id) {
    <li>{{ item.name }}</li>
  }
</ul>
```

#### The track expression

`track` tells Angular how to identify each item across re-renders. When the
list changes, Angular reconciles old DOM nodes with new data using this key
rather than position. Use a **stable unique identifier** — typically `item.id`.

```html
<!-- ✅ Track by stable ID — Angular reuses DOM nodes efficiently -->
@for (product of products; track product.id) {
  <app-product-card [product]="product" />
}

<!-- ⚠️ Track by index — works but defeats the purpose for dynamic lists -->
@for (item of items; track $index) {
  <li>{{ item }}</li>
}
```

Use `track $index` only for **static lists** that never reorder or change
length. For any list that can be mutated, sorted, filtered, or paginated,
always track by a stable ID.

#### Built-in loop variables

`@for` provides implicit variables you can use without declaring them:

```html
@for (item of items; track item.id; let i = $index, let isFirst = $first, let isLast = $last, let isEven = $even) {
  <li [class.highlight]="isEven" [class.first]="isFirst">
    {{ i + 1 }}. {{ item.name }}
    @if (isLast) { <span>(last)</span> }
  </li>
}
```

| Variable | Type | Value |
| --- | --- | --- |
| `$index` | `number` | Zero-based position in the list |
| `$count` | `number` | Total number of items |
| `$first` | `boolean` | `true` for the first item |
| `$last` | `boolean` | `true` for the last item |
| `$even` | `boolean` | `true` for even-indexed items |
| `$odd` | `boolean` | `true` for odd-indexed items |

#### @empty — the missing feature from *ngFor

`*ngFor` had no built-in way to show a fallback when the list was empty — you
needed a separate `*ngIf` on a sibling element. `@for` solves this with `@empty`:

```html
@for (message of messages; track message.id) {
  <app-message [message]="message" />
} @empty {
  <p class="empty-state">No messages yet. Start a conversation!</p>
}
```

### @switch — value branching

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<!-- NgModule / legacy approach with ngSwitch -->
<div [ngSwitch]="status">
  <span *ngSwitchCase="'active'">Active</span>
  <span *ngSwitchCase="'pending'">Pending</span>
  <span *ngSwitchDefault>Unknown</span>
</div>
```

```html
<!-- Modern @switch — reads like a TypeScript switch statement -->
@switch (status) {
  @case ('active') {
    <app-status-badge color="green">Active</app-status-badge>
  }
  @case ('pending') {
    <app-status-badge color="orange">Pending</app-status-badge>
  }
  @case ('suspended') {
    <app-status-badge color="red">Suspended</app-status-badge>
  }
  @default {
    <span>Unknown status</span>
  }
}
```

`@switch` does not fall through between cases — no `break` needed. `@default`
is optional but recommended.

## Real-world patterns

### Pattern 1 — Async data with loading and error states

The most common real-world pattern: fetch data, show a spinner while loading,
show an error if it fails, show the content when ready.

```typescript
@Component({
  selector: 'app-user-list',
  standalone: true,
  template: `
    @if (state().loading) {
      <app-skeleton-list [rows]="5" />
    } @else if (state().error) {
      <app-error-banner [message]="state().error!" />
    } @else {
      <ul>
        @for (user of state().data; track user.id) {
          <li>
            <img [src]="user.avatar" [alt]="user.name" />
            <span>{{ user.name }}</span>
          </li>
        } @empty {
          <li>No users found.</li>
        }
      </ul>
    }
  `,
})
export class UserListComponent {
  private userService = inject(UserService);

  state = toSignal(
    this.userService.getUsers().pipe(
      map(data => ({ loading: false, data, error: null })),
      startWith({ loading: true, data: [], error: null }),
      catchError(err => of({ loading: false, data: [], error: err.message }))
    ),
    { initialValue: { loading: true, data: [], error: null } }
  );
}
```

### Pattern 2 — Role-based UI branching

Showing different UI based on user role — a real-world `@switch` use case:

```typescript
@Component({
  selector: 'app-dashboard-header',
  standalone: true,
  template: `
    @switch (currentUser().role) {
      @case ('admin') {
        <app-admin-toolbar [user]="currentUser()" />
      }
      @case ('editor') {
        <app-editor-toolbar [user]="currentUser()" />
      }
      @case ('viewer') {
        <app-viewer-banner [user]="currentUser()" />
      }
      @default {
        <button (click)="signIn()">Sign in</button>
      }
    }
  `,
})
export class DashboardHeaderComponent {
  currentUser = inject(AuthService).currentUser;
  signIn() { inject(Router).navigate(['/login']); }
}
```

### Pattern 3 — Nested @for with @empty

Nested lists — a common UI pattern in admin dashboards, tree views, and
category/product layouts:

```html
@for (category of categories; track category.id) {
  <section>
    <h2>{{ category.name }}</h2>

    @for (product of category.products; track product.id) {
      <app-product-card [product]="product" />
    } @empty {
      <p class="empty">No products in {{ category.name }} yet.</p>
    }
  </section>
} @empty {
  <p class="empty">No categories available.</p>
}
```

## Common mistakes

### Mistake 1 — Forgetting track (TypeScript won't catch it)

The compiler enforces `track` — you'll get a template error if you omit it.
But the *value* you track by matters just as much:

```html
<!-- ❌ Tracking by index on a sortable list — sorts cause full re-render -->
@for (row of tableRows; track $index) {
  <tr><td>{{ row.name }}</td></tr>
}

<!-- ✅ Track by stable ID — sort/filter/paginate without re-creating DOM -->
@for (row of tableRows; track row.id) {
  <tr><td>{{ row.name }}</td></tr>
}
```

### Mistake 2 — Calling a function multiple times in @if without the as alias

```html
<!-- ❌ getExpensiveData() called twice — once for the check, once for the value -->
@if (getExpensiveData()) {
  <app-display [data]="getExpensiveData()" />
}

<!-- ✅ Captured once with 'as' — one call, type-narrowed inside the block -->
@if (getExpensiveData(); as data) {
  <app-display [data]="data" />
}
```

This also applies to signals — `@if (user(); as u)` calls the signal once and
gives you the narrowed value.

### Mistake 3 — Using @switch for range comparisons

`@switch` uses strict equality (`===`). It cannot compare ranges:

```html
<!-- ❌ Won't work — @case uses ===, not >= or <= -->
@switch (score) {
  @case (score >= 90) { <span>A</span> }
  @case (score >= 80) { <span>B</span> }
}

<!-- ✅ Use @if/@else if for range comparisons -->
@if (score >= 90) {
  <span>A</span>
} @else if (score >= 80) {
  <span>B</span>
} @else {
  <span>C</span>
}
```

### Mistake 4 — Mixing old and new syntax unnecessarily

You can use `*ngIf` and `@if` in the same project — Angular supports both
during migration. But avoid mixing them in the **same component template**.
It creates inconsistency and confuses readers:

```html
<!-- ❌ Mixed — jarring to read, signals unfinished migration -->
<div *ngIf="showHeader">
  <h1>{{ title }}</h1>
</div>
@for (item of items; track item.id) {
  <app-item [item]="item" />
}

<!-- ✅ Consistent — pick one style per template -->
@if (showHeader) {
  <h1>{{ title }}</h1>
}
@for (item of items; track item.id) {
  <app-item [item]="item" />
}
```

Run the Angular migration schematic to convert an entire project at once:
```bash
ng generate @angular/core:control-flow
```

## How this evolved

> - **Angular 2–16 (2016–2023):** Conditional and list rendering done via
>   structural directives — `*ngIf`, `*ngFor`, `*ngSwitch` — imported from
>   `CommonModule`. Optional `trackBy` meant most lists were unoptimized.
>   No `@else if` without nesting. No built-in empty-list handling.
>
> - **Angular 17 (2023):** Built-in control flow introduced as **developer
>   preview** — `@if`, `@for` (with required `track`), `@switch`. Also
>   introduced `@defer` for lazy rendering. Structural directives still work
>   but are now considered legacy syntax.
>
> - **Angular 18 (2024):** Built-in control flow promoted to **stable**. The
>   migration schematic (`ng generate @angular/core:control-flow`) became the
>   recommended way to convert existing projects. Structural directives remain
>   supported but deprecated in new code.
>
> - **Angular 22 (now):** `@if`, `@for`, `@switch` are the standard. New
>   projects generated by the CLI use them by default. `*ngIf` and `*ngFor`
>   still compile but linters flag them as legacy. The Angular team's guidance
>   is clear: migrate when you can, use the new syntax for all new code.

## See also

- [Data Binding](./data-binding.md) — property binding and interpolation that
  feed values into control flow expressions
- [Structural Directives](../../directives/structural-directives.md) — how
  `*ngIf` and `*ngFor` worked under the hood (useful context for the migration)
- [@defer Blocks](../../rendering/defer-blocks.md) — the fourth `@` block,
  for lazy rendering triggered by viewport, interaction, or timer
- [Official docs — Built-in control flow](https://angular.dev/guide/templates/control-flow)
- [Migration schematic](https://angular.dev/reference/migrations/control-flow)

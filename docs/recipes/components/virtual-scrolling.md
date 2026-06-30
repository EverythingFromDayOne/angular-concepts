---
recipe_id: "virtual-scrolling"
title: "Virtual Scrolling: Rendering 10,000 Items Without Killing the Browser"
file: "recipes/components/virtual-scrolling.md"
primary_concept: "components/components"
related_concepts: ["reactivity/signals", "http/http", "components/standalone-components"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Virtual Scrolling: Rendering 10,000 Items Without Killing the Browser

> **What you'll build:** a virtualized list that handles 10,000+ items
> smoothly using CDK's `cdk-virtual-scroll-viewport` — fixed-size and
> auto-sized variants, the load-bearing `trackBy` function that prevents
> re-render thrash, infinite scroll with prefetch-on-near-end so users
> don't see a loading spinner, and the bounded-window pattern for truly
> massive datasets where keeping everything in memory isn't an option.
>
> **Concepts you'll touch:** [Components](../../components/components.md), [Signals](../../reactivity/signals.md), [HTTP](../../http/http.md), [Standalone components](../../components/standalone-components.md)
>
> **Time:** ~25 minutes to read; ~1 hour to retrofit a slow list page.

---

## The scenario

A user opens the admin dashboard. It shows all 10,847 users in the system. The browser pinwheels for 8 seconds. Memory usage in DevTools shows 500MB. Scrolling stutters every time data updates. On mobile, the tab eventually crashes.

What happened: the template renders a `@for` over the full array. Each user row has an avatar, name, email, role badge, action buttons — call it 8 DOM nodes per row. 10,847 × 8 = **86,776 DOM nodes**. The browser has to parse, lay out, style, and paint every single one before showing anything. Memory holds all the user data PLUS all the DOM nodes PLUS Angular's bookkeeping for each binding.

Even if the initial render somehow finishes, every subsequent change-detection cycle iterates all 86,776 bindings. Scroll, click, hover — all stutter.

The fix is **virtual scrolling**: render only the items currently visible (plus a small buffer above and below), recycle DOM nodes as the user scrolls. The browser sees maybe 20 rows at a time instead of 10,000. Memory stays constant regardless of dataset size. Initial render is fast. Scrolling is smooth.

The Angular CDK provides this out of the box. The substance of this recipe is the patterns that make it work correctly — the `trackBy` that prevents re-render thrash, the prefetch-on-near-end that avoids visible loading spinners, the bounded window for truly massive datasets, and the small CSS gotcha that 80% of "virtual scroll doesn't render anything" Stack Overflow questions are about.

---

## Setting up CDK Virtual Scroll

CDK Virtual Scroll lives in `@angular/cdk/scrolling`. Install if you haven't already:

```bash
npm install @angular/cdk
```

In standalone components (the v22 default), import the directives you need:

```typescript
import { Component, signal, inject } from '@angular/core';
import { CdkVirtualScrollViewport, CdkVirtualForOf, CdkFixedSizeVirtualScroll } from '@angular/cdk/scrolling';
// Or for everything:
// import { ScrollingModule } from '@angular/cdk/scrolling';

@Component({
  selector: 'app-user-list',
  imports: [CdkVirtualScrollViewport, CdkVirtualForOf, CdkFixedSizeVirtualScroll],
  // ...
})
export class UserListComponent { /* … */ }
```

The granular imports are slightly cleaner than the whole module; either form works.

---

## The minimum viable virtual list

A 10,000-row list rendered with virtual scroll:

```typescript
// File: user-list.component.ts
import { Component, signal, inject } from '@angular/core';
import {
  CdkVirtualScrollViewport,
  CdkVirtualForOf,
  CdkFixedSizeVirtualScroll,
} from '@angular/cdk/scrolling';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

interface User {
  id: string;
  name: string;
  email: string;
  avatar: string;
}

@Component({
  selector: 'app-user-list',
  imports: [CdkVirtualScrollViewport, CdkVirtualForOf, CdkFixedSizeVirtualScroll],
  template: `
    <cdk-virtual-scroll-viewport itemSize="60" class="viewport">
      <div
        *cdkVirtualFor="let user of users(); trackBy: trackById"
        class="row"
      >
        <img [src]="user.avatar" alt="" class="avatar" />
        <div class="meta">
          <div class="name">{{ user.name }}</div>
          <div class="email">{{ user.email }}</div>
        </div>
      </div>
    </cdk-virtual-scroll-viewport>
  `,
  styles: `
    .viewport {
      height: 600px;              /* REQUIRED — viewport needs explicit height */
      width: 100%;
      border: 1px solid #e5e7eb;
    }
    .row {
      height: 60px;               /* MUST match itemSize="60" above */
      display: flex;
      align-items: center;
      padding: 0 16px;
      border-bottom: 1px solid #f3f4f6;
    }
    .avatar { width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; }
    .meta { display: flex; flex-direction: column; }
    .name { font-weight: 500; }
    .email { color: #6b7280; font-size: 14px; }
  `,
})
export class UserListComponent {
  private readonly http = inject(HttpClient);
  readonly users = signal<User[]>([]);

  // The track function — keep it as a field so the reference is stable.
  // A new function reference on every change detection would defeat the optimization.
  trackById = (_index: number, user: User) => user.id;

  constructor() {
    this.http.get<User[]>('/api/users').pipe(
      takeUntilDestroyed(),
    ).subscribe(users => this.users.set(users));
  }
}
```

**Five things doing the work:**

- **`itemSize="60"` matches the actual rendered row height.** CDK uses this to calculate which items are visible. If `itemSize` says 60 but rows actually render at 50, the calculations drift — scrolling lands on the wrong items, the viewport empties out, all sorts of visible wrongness.

- **The viewport has an explicit `height`**. This is the #1 cause of "virtual scroll renders nothing." Without a height, the viewport is 0 tall, no items count as visible, the DOM is empty. The error message is unhelpful — usually no error at all, just an empty container.

- **`*cdkVirtualFor`** is the structural directive that integrates with the viewport — different from `@for`/`*ngFor`. The `@for` block can't power virtual scroll because it always renders the full iteration; `cdkVirtualFor` only renders what the viewport reports as visible.

- **`trackBy: trackById`** is the load-bearing performance optimization. Without it, every change to `users()` re-renders every visible row from scratch. With it, only the rows that actually changed update.

- **`trackById` is a class field, not an inline arrow function.** `trackBy: (i, u) => u.id` would create a new function reference on every render — defeating the change-detection short-circuit. Always assign to a stable field.

### The explicit-height gotcha (one more time, because it bites everyone)

`cdk-virtual-scroll-viewport` is itself a flex container or block element. If it's inside another flex container without `flex: 1` or an explicit height, it collapses to 0. Symptoms: empty container, no error, no log message, no clue.

```css
/* WRONG: parent doesn't constrain height */
.list-wrapper {
  display: flex;
  flex-direction: column;
}
.viewport { /* height: ??? */ }

/* RIGHT: parent has bounded height; viewport fills it */
.list-wrapper {
  display: flex;
  flex-direction: column;
  height: 100vh;       /* or some fixed value */
}
.viewport {
  flex: 1;             /* fill remaining space */
  min-height: 0;       /* override flex's default min-height: auto */
}
```

The `min-height: 0` is itself a flex gotcha — without it, flex children can grow past their container in some browsers. Two CSS lines that "shouldn't matter" turn out to matter a lot.

---

## Variable-height items — the `autosize` strategy

Some lists have items that aren't all the same height. A chat with messages of varying length, a comment thread, a feed with mixed content types. Fixed-size won't work — items would either be truncated (size too small) or have visible gaps (size too big).

CDK's `autosize` strategy measures each item as it renders:

```typescript
import { CdkAutoSizeVirtualScroll } from '@angular/cdk/scrolling';

@Component({
  imports: [CdkVirtualScrollViewport, CdkVirtualForOf, CdkAutoSizeVirtualScroll],
  template: `
    <cdk-virtual-scroll-viewport
      autosize
      minBufferPx="200"
      maxBufferPx="400"
      class="viewport"
    >
      <div
        *cdkVirtualFor="let message of messages(); trackBy: trackById"
        class="message"
      >
        {{ message.body }}
      </div>
    </cdk-virtual-scroll-viewport>
  `,
  styles: `
    .viewport { height: 600px; }
    .message {
      padding: 12px 16px;
      border-bottom: 1px solid #f3f4f6;
      /* No fixed height — content determines it */
    }
  `,
})
export class ChatListComponent { /* … */ }
```

**Three new things:**

- **`autosize` directive** instead of `itemSize`. CDK doesn't know item heights upfront; it measures.
- **`minBufferPx` and `maxBufferPx`** — the buffer above/below the visible area, in pixels rather than item count. Larger buffers mean more pre-rendered items (smoother scrolling, more memory); smaller buffers mean less waste. Defaults are reasonable; 200/400 are typical custom values.
- **No fixed item height in CSS.** Items size to their content.

**Trade-off**: `autosize` is significantly more expensive than fixed-size. Each item triggers a measurement, which forces layout. For tens of thousands of items, the cumulative cost is noticeable. Use fixed-size whenever item heights are predictable; use `autosize` only when they genuinely vary.

If items mostly have one of a few discrete heights (e.g., "text message", "image message", "system notification" — each fixed size in its own type), consider rendering them in separate fixed-size lists or computing the height upfront and passing it to CDK via a custom strategy.

---

## Infinite scroll with prefetch-on-near-end

Loading 10,000 items in one HTTP call is usually wrong even with virtual scroll. The browser still has to hold all of them in memory. The server has to serialize all of them. The network has to transfer them. The right pattern: **paginated fetches, triggered as the user approaches the end of what's loaded.**

```typescript
@Component({
  selector: 'app-infinite-list',
  imports: [
    CdkVirtualScrollViewport, CdkVirtualForOf, CdkFixedSizeVirtualScroll,
  ],
  template: `
    <cdk-virtual-scroll-viewport
      itemSize="60"
      class="viewport"
      (scrolledIndexChange)="onScrolledIndexChange($event)"
    >
      <div
        *cdkVirtualFor="let item of items(); trackBy: trackById"
        class="row"
      >
        {{ item.title }}
      </div>
      @if (loading()) {
        <div class="loading-row">Loading more…</div>
      }
    </cdk-virtual-scroll-viewport>
  `,
  styles: `
    .viewport { height: 600px; }
    .row { height: 60px; padding: 16px; border-bottom: 1px solid #f3f4f6; }
    .loading-row { padding: 16px; color: #6b7280; text-align: center; }
  `,
})
export class InfiniteListComponent {
  private readonly http = inject(HttpClient);
  readonly items = signal<Item[]>([]);
  readonly loading = signal(false);

  private nextPage = 1;
  private hasMore = true;
  private readonly PAGE_SIZE = 50;
  private readonly PREFETCH_BUFFER = 20;  // start loading when within 20 of the end

  trackById = (_: number, item: Item) => item.id;

  constructor() {
    this.loadNextPage();  // initial fetch
  }

  onScrolledIndexChange(topVisibleIndex: number): void {
    const total = this.items().length;
    const distanceFromEnd = total - topVisibleIndex;

    if (
      distanceFromEnd <= this.PREFETCH_BUFFER &&
      this.hasMore &&
      !this.loading()
    ) {
      this.loadNextPage();
    }
  }

  private loadNextPage(): void {
    this.loading.set(true);

    this.http.get<PaginatedResponse<Item>>(
      `/api/items?page=${this.nextPage}&size=${this.PAGE_SIZE}`,
    ).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: response => {
        this.items.update(current => [...current, ...response.items]);
        this.hasMore = response.hasMore;
        this.nextPage++;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        // Toast/banner: "Couldn't load more — please retry"
      },
    });
  }

  private readonly destroyRef = inject(DestroyRef);
}

interface PaginatedResponse<T> {
  items: T[];
  hasMore: boolean;
  total?: number;
}
```

**Four patterns doing the work:**

- **`(scrolledIndexChange)`** fires whenever the topmost visible index changes — i.e., as the user scrolls. The handler runs once per "scroll tick," not per pixel.

- **The PREFETCH_BUFFER** — start loading the next page when the user is within 20 items of the end. Combined with fast network, the new items often land before the user reaches the spinner. Tune the buffer to your average per-item view time and network latency.

- **The `loading()` guard** prevents multiple concurrent fetches. Without it, every scroll event during the load would fire another fetch. The guard makes the load idempotent.

- **`hasMore` flag from the server.** The server tells you when there's nothing more to load; stop firing requests at that point. Many APIs use `null` or empty cursor instead — adapt to whatever your backend's pattern is.

### Composition with request-deduplication and retry

If multiple infinite lists could fetch the same page (rare but possible — two tabs on the same data), the [request-deduplication](../http/request-deduplication.md) interceptor returns one shared request. With [retry-with-backoff](../http/retry-with-backoff.md), transient failures don't break pagination — a flaky network blips, retry kicks in, the user doesn't see "Couldn't load more" unless retries actually fail.

---

## Bounded window — for truly massive datasets

The infinite-scroll pattern above accumulates items forever. If the user scrolls through 50,000 items, you have 50,000 in memory. For really big lists (logs, time-series, search results in a 100M-document index), this isn't acceptable.

The **bounded-window** pattern keeps only N items in memory at any time. As the user scrolls down, items at the top get unloaded. Scrolling back up triggers a re-fetch.

This is harder than infinite-scroll because:
- You need to know where in the dataset you are (offset, not just "page N")
- You need to handle scroll-up re-fetches
- The viewport's reported position is the only ground truth — it doesn't know about unloaded items

The CDK doesn't have a built-in bounded-window strategy; you implement it via a custom `DataSource`:

```typescript
import { DataSource, CollectionViewer } from '@angular/cdk/collections';
import { BehaviorSubject, Observable, Subscription } from 'rxjs';

export class BoundedWindowDataSource extends DataSource<Item | undefined> {
  private readonly pageSize = 50;
  private readonly windowSize = 500;  // max items in memory
  private readonly cache = new Map<number, Item>();  // index → item
  private readonly viewport$ = new BehaviorSubject<(Item | undefined)[]>([]);
  private subscription?: Subscription;

  constructor(
    private fetchPage: (page: number) => Observable<Item[]>,
    private totalCount: number,
  ) {
    super();
  }

  connect(viewer: CollectionViewer): Observable<(Item | undefined)[]> {
    this.subscription = viewer.viewChange.subscribe(range => {
      this.loadVisibleAndEvictOld(range);
    });
    return this.viewport$;
  }

  disconnect(): void {
    this.subscription?.unsubscribe();
  }

  private loadVisibleAndEvictOld(range: { start: number; end: number }): void {
    const startPage = Math.floor(range.start / this.pageSize);
    const endPage = Math.floor(range.end / this.pageSize);

    for (let page = startPage; page <= endPage; page++) {
      if (this.cache.has(page * this.pageSize)) continue;
      this.fetchPage(page).subscribe(items => {
        items.forEach((item, i) => {
          this.cache.set(page * this.pageSize + i, item);
        });
        this.evictBeyondWindow(range);
        this.emitViewport();
      });
    }
  }

  private evictBeyondWindow(range: { start: number; end: number }): void {
    const halfWindow = this.windowSize / 2;
    const keepStart = Math.max(0, range.start - halfWindow);
    const keepEnd = range.end + halfWindow;

    for (const index of this.cache.keys()) {
      if (index < keepStart || index > keepEnd) {
        this.cache.delete(index);
      }
    }
  }

  private emitViewport(): void {
    const array = new Array<Item | undefined>(this.totalCount);
    for (const [index, item] of this.cache) {
      array[index] = item;
    }
    this.viewport$.next(array);
  }
}
```

Usage in the component:

```typescript
@Component({
  template: `
    <cdk-virtual-scroll-viewport itemSize="60" class="viewport">
      <div
        *cdkVirtualFor="let item of dataSource"
        class="row"
      >
        @if (item) {
          {{ item.title }}
        } @else {
          <span class="placeholder">Loading…</span>
        }
      </div>
    </cdk-virtual-scroll-viewport>
  `,
})
export class BoundedListComponent {
  dataSource = new BoundedWindowDataSource(
    page => this.http.get<Item[]>(`/api/logs?page=${page}`),
    100_000,
  );
}
```

The `undefined` slots in the array represent "we haven't loaded this index yet." The template shows a placeholder; once the page loads, the slot fills in.

This is significantly more complex than the infinite-scroll pattern. Use it only when memory pressure is a real problem — log viewers, time-series dashboards, search-result pages over very large indexes. For most lists, infinite scroll with reasonable upper bounds is enough.

---

## Variations

### Sticky headers for grouped lists

When the list has groups (chat messages grouped by date, contacts grouped by initial, transactions grouped by month), sticky headers make navigation clearer. CDK doesn't have a built-in sticky-virtual-header, but the pattern is:

1. Include headers as items in the virtualized list (each header is a different item type)
2. Use CSS `position: sticky` on the header rows
3. Track headers separately so they don't disappear during scroll

The `position: sticky` interacts with the viewport's scroll mechanism — works correctly inside `cdk-virtual-scroll-viewport` because the viewport is itself a scrolling container.

### Horizontal virtual scroll

CDK supports horizontal orientation via the `orientation` input:

```html
<cdk-virtual-scroll-viewport
  orientation="horizontal"
  itemSize="200"
  class="horizontal-viewport"
>
  <div *cdkVirtualFor="let item of items()" class="card">
    {{ item.title }}
  </div>
</cdk-virtual-scroll-viewport>
```

Same patterns, different axis. The CSS must give the viewport a `width` (rather than `height`) and the item must have a fixed `width`.

### Reorderable virtual scroll

Drag-and-drop reordering inside a virtual scroll is hard — the dragged item needs to remain visible during drag, but virtual scroll wants to recycle DOM nodes that go out of view. The CDK `cdkDropList` integration is non-trivial; for most apps, either (a) constrain the dataset size to fit without virtualization, or (b) use a flat list with virtualization but no drag-drop.

If you genuinely need both, the Angular Material's CDK drag-drop docs have a `cdk-virtual-scroll-viewport + cdkDropList` example that's worth following carefully.

### Filtering and sorting

When the user filters or sorts, the dataset changes. Two correctness concerns:

```typescript
applyFilter(query: string): void {
  this.filtered.set(
    this.allItems().filter(item =>
      item.name.toLowerCase().includes(query.toLowerCase())
    )
  );
  // CRUCIAL: reset scroll position to the top
  this.viewport.scrollToIndex(0);
}
```

`scrollToIndex(0)` snaps the viewport back to the top. Without it, the user could be scrolled past the end of the filtered result, showing an empty viewport.

Same applies to sorting and to reloading data — anytime the array's items change identity, reset to a known scroll position.

---

## Trade-offs and common pitfalls

**Use virtual scrolling when:**

- The list has more than ~100 items (below that, virtualization overhead exceeds the saving)
- Items are visually similar (consistent layout makes virtualization predictable)
- Memory or performance with the full list is a measured problem

**Skip virtual scrolling when:**

- The list is small (<100 items); standard `@for` is faster and simpler
- Items are highly varied in size and complexity (cost of `autosize` measurement approaches the cost of just rendering all of them)
- You need browser-native features that virtualization breaks (Ctrl+F find, screen-reader sequential navigation through the full list, anchor links to specific items)

### Common pitfalls

- **No explicit height on the viewport.** The most common bug. Symptoms: empty container, no error, no log. Set `height` directly or use `flex: 1; min-height: 0;` inside a constrained flex parent.
- **`itemSize` doesn't match actual rendered height.** Scroll position drifts; items end up in the wrong place; viewport visually empties out at random scroll positions. Measure your row exactly and match.
- **Inline `trackBy` arrow function.** `trackBy: (i, x) => x.id` creates a new function reference per render, defeating the optimization. Use a stable class field.
- **No `trackBy` at all.** Default index-based tracking causes every row to re-render on any data change. The performance difference between "buttery scroll" and "stuttery scroll" is often just the `trackBy`.
- **Heavy components inside rows.** Virtualization helps with render count, not render cost. Each visible item still re-renders on every change-detection cycle. Use `OnPush` change detection or signals to avoid unnecessary work per row.
- **Loading indicator outside the viewport.** The user scrolls to the end, the spinner appears below the viewport in DOM order but the viewport keeps eating their scrolling. Put the indicator inside the viewport so it scrolls into view naturally.
- **Multiple concurrent fetches on scroll.** Without a `loading()` guard, every scroll event during a load fires another fetch. Five pages fetched for what should be one. Always gate fetches on the load flag.
- **Scroll position lost on filter/sort/refresh.** The user expects the list to "reset" when they apply a filter. Call `viewport.scrollToIndex(0)` after the data swap.
- **Accumulating items forever.** Infinite scroll without a bound eventually exhausts memory on long sessions. For very large datasets, switch to the bounded-window pattern or impose a max-items cap with a "see latest" button.
- **`autosize` with extreme height variance.** Performance degrades badly when items have very different heights — every measurement forces layout. If items group into a few discrete sizes, render each group as a separate fixed-size virtual list.
- **Reading from the signal inside the template's `*cdkVirtualFor` expression with side effects.** `*cdkVirtualFor="let item of users()"` invokes the signal — fine, it's a read. Don't call methods with side effects in that expression.
- **Setting `itemSize` based on a CSS variable.** CDK reads it once at directive initialization. Changing the CSS variable later doesn't update CDK's calculations. Use a fixed numeric value.

---

## See also

- [Components](../../components/components.md) — component basics, change detection, OnPush
- [Standalone components](../../components/standalone-components.md) — the v22 default; how CDK modules import into them
- [Signals](../../reactivity/signals.md) — the data source primitive for virtual lists
- [Request Deduplication](../http/request-deduplication.md) — composes with paginated fetches when multiple lists could fetch the same page
- [Retry with Backoff](../http/retry-with-backoff.md) — wraps page-fetch HTTP calls so transient failures don't break pagination
- [Race Conditions](../reactivity/race-conditions.md) — handles concurrent paginated fetches; the `exhaustMap` pattern for "don't fetch while one is in flight"

## References

- [`CdkVirtualScrollViewport` (Material CDK)](https://material.angular.io/cdk/scrolling/api#CdkVirtualScrollViewport) — the viewport directive
- [`CdkVirtualForOf` (Material CDK)](https://material.angular.io/cdk/scrolling/api#CdkVirtualForOf) — the iteration directive
- [`CdkFixedSizeVirtualScroll` (Material CDK)](https://material.angular.io/cdk/scrolling/api#FixedSizeVirtualScrollStrategy) — the fixed-size strategy
- [`DataSource` interface (Material CDK)](https://material.angular.io/cdk/collections/api#DataSource) — for custom data-source implementations including bounded windows
- [Virtual Scrolling overview (Material docs)](https://material.angular.io/cdk/scrolling/overview) — the canonical Angular reference

## Demo source

Synthesized from common production virtual-scroll patterns rather than a single demo file. The infinite-scroll-with-prefetch pattern is the most common case; the bounded-window pattern is included for log viewers, dashboards, and similar memory-constrained scenarios. All code is original.
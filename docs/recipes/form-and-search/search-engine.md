---
recipe_id: "search-engine"
title: "A Search Engine in Five Stages"
file: "recipes/forms-and-search/search-engine.md"
primary_concept: "reactivity/rxjs/rxjs"
related_concepts: ["reactivity/signals", "reactivity/to-signal", "http/http", "routing/routing"]
demo_repo: "https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/search-engine"
angular_baseline: "22"
difficulty: "advanced"
status:
  upgraded: true
  reviewed: false
---

# A Search Engine in Five Stages

> **What you'll build:** a search-as-you-type interface that starts as a
> 30-line debounce-and-switchMap and ends as a multi-filter, URL-synced,
> stale-while-revalidate cached search component. Each stage adds one
> capability so the architectural choices stay visible.
>
> **Concepts you'll touch:** [RxJS](../../reactivity/rxjs/rxjs.md), [Signals](../../reactivity/signals.md), [toSignal](../../reactivity/to-signal.md), [HTTP](../../http/http.md), [Routing](../../routing/routing.md)
>
> **Time:** ~30 minutes to read; an afternoon to extend to your own data
> shape.

---

## The scenario

You're building a search-as-you-type box that hits an API. Sounds easy.
The first version takes ten minutes. Then a user files a bug: "the search
fires on every keystroke and the results jump around as I type." OK, add
debounce. Then: "I want to press Enter to search immediately, not wait
300ms." OK, add a Subject. Then: "going back and forth, the same search
re-fetches every time." OK, cache. Then: "the cache UX shows a loader
even when we already have data." OK, switch to stale-while-revalidate.
Then: "we need filters, and the URL should be shareable." OK, that's
this recipe.

Each requirement is a five-minute story to write. The architectural
choices stack in interesting ways, and the difference between "works"
and "works well" lives in three or four idioms.

We'll walk through five stages. Each stage is a complete, working
component — drop it into a fresh standalone Angular component and run
it. Then move to the next.

---

## Stage 1 — debounce and `switchMap`

The foundation. Type into a box, the search fires 300ms after you stop
typing, the previous request is cancelled if a new one starts.

```typescript
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  debounceTime,
  distinctUntilChanged,
  switchMap,
  map,
  startWith,
  of,
  catchError,
} from 'rxjs';

interface User { id: number; name: string; }
interface SearchState { loading: boolean; data: User[]; error: boolean; }

@Component({
  selector: 'app-user-search',
  template: `
    <input
      (input)="searchTerm.set($any($event.target).value)"
      placeholder="Type to search..."
    />

    @if (searchState().loading) {
      <p>Loading...</p>
    }

    <ul>
      @for (user of searchState().data; track user.id) {
        <li>{{ user.name }}</li>
      }
    </ul>

    @if (searchState().error) {
      <p style="color: red;">Something went wrong.</p>
    }
  `,
})
export class UserSearchComponent {
  private readonly http = inject(HttpClient);
  readonly searchTerm = signal('');

  readonly searchState = toSignal(
    toObservable(this.searchTerm).pipe(
      debounceTime(300),                          // wait 300ms after last keystroke
      distinctUntilChanged(),                     // skip if same as last value
      switchMap(query => {
        if (!query) {
          return of<SearchState>({ loading: false, data: [], error: false });
        }
        return this.http.get<User[]>(`api/users?q=${query}`).pipe(
          map(res => ({ loading: false, data: res, error: false })),
          startWith({ loading: true, data: [], error: false }),
          catchError(() => of({ loading: false, data: [], error: true })),
        );
      }),
    ),
    { initialValue: { loading: false, data: [], error: false } },
  );
}
```

**The four idioms doing the work:**

- **`debounceTime(300)`** — collapses bursts of keystrokes into one
  emission, 300ms after the user stops typing. Without it, "react"
  fires five HTTP requests (one per character).
- **`distinctUntilChanged()`** — skips emissions that equal the previous.
  If the user deletes a character and retypes it, no new request fires.
- **`switchMap`** — when a new query arrives, **cancels** the in-flight
  HTTP request from the previous query. This is what prevents the
  classic bug where results "jump" because an older request finishes
  after a newer one.
- **`startWith({ loading: true, ... })` *inside* the switchMap** — the
  loading flag flips on for **this query's** request, then off when the
  response (or error) lands. Putting it outside the switchMap would
  produce a single loader at startup, not one per query.

That's the floor. Most search-as-you-type implementations stop here, and
for many cases it's enough.

---

## Stage 2 — instant search on Enter

The user wants to bypass the 300ms wait by pressing Enter. The pattern:
**merge** two streams — the debounced typing stream and an
immediate-fire stream backed by a `Subject` you `.next()` on Enter.

```typescript
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  Subject,
  merge,
  debounceTime,
  distinctUntilChanged,
  switchMap,
  map,
  startWith,
  of,
  catchError,
} from 'rxjs';

@Component({
  selector: 'app-user-search',
  template: `
    <input
      (input)="searchTerm.set($any($event.target).value)"
      (keyup.enter)="searchNow()"
      placeholder="Type to search or press Enter..."
    />

    @if (searchState().loading) { <p>Loading...</p> }
    <ul>
      @for (user of searchState().data; track user.id) {
        <li>{{ user.name }}</li>
      }
    </ul>
  `,
})
export class UserSearchComponent {
  private readonly http = inject(HttpClient);
  readonly searchTerm = signal('');
  private readonly forceSearch$ = new Subject<string>();  // ← the shortcut stream

  readonly searchState = toSignal(
    merge(
      // Stream A: debounced typing
      toObservable(this.searchTerm).pipe(
        debounceTime(300),
        distinctUntilChanged(),
      ),
      // Stream B: immediate fire on Enter
      this.forceSearch$,
    ).pipe(
      distinctUntilChanged(),                     // dedupe across both streams
      switchMap(query => /* same as Stage 1 */ this.runSearch(query)),
    ),
    { initialValue: { loading: false, data: [], error: false } },
  );

  searchNow(): void {
    this.forceSearch$.next(this.searchTerm());
  }

  private runSearch(query: string) {
    if (!query) return of({ loading: false, data: [], error: false });
    return this.http.get<User[]>(`api/users?q=${query}`).pipe(
      map(res => ({ loading: false, data: res, error: false })),
      startWith({ loading: true, data: [], error: false }),
      catchError(() => of({ loading: false, data: [], error: true })),
    );
  }
}

interface User { id: number; name: string; }
```

**Two things to absorb:**

- **The second `distinctUntilChanged()` after `merge` is intentional.**
  Without it, Enter pressed twice on the same query re-fetches. With it,
  pressing Enter on a value that just came through the debounce path is
  a no-op (good — no duplicate request). The trade-off: if you *want*
  Enter-to-refresh, drop the outer `distinctUntilChanged()` and accept
  that double-presses fire double requests.

- **`Subject` is the right primitive for "imperative push into a
  stream."** Components frequently need a pattern where an event
  handler (`searchNow()`) wants to inject a value into an RxJS pipeline.
  `Subject.next()` is exactly that. Don't be afraid of it because it
  has shared mutable state — this is the case it's designed for.

---

## Stage 3 — cache with TTL

Same query twice? Don't re-fetch. Cache the observable result, share it
between subscribers, and expire entries after a TTL.

### Step 3a — extract a reusable `withCache` operator

The caching logic is the same shape regardless of the URL. Package it
as a custom operator:

```typescript
// File: operators/cache.operator.ts
import { Observable, of } from 'rxjs';
import { map, shareReplay, startWith, catchError, tap } from 'rxjs/operators';

interface CachedState<T> {
  loading: boolean;
  data: T;
  error: boolean;
}

export function withCache<T>(
  key: string,
  cacheMap: Map<string, Observable<T>>,
  request$: Observable<T>,
  cacheDuration = 5 * 60 * 1000,    // 5 minutes
): Observable<CachedState<T>> {
  // 1. If not already cached, build the shared, auto-expiring request
  if (!cacheMap.has(key)) {
    const sharedRequest = request$.pipe(
      shareReplay(1),                              // replay latest to late subscribers
      tap(() => {                                  // schedule eviction after TTL
        setTimeout(() => cacheMap.delete(key), cacheDuration);
      }),
      catchError(err => {
        cacheMap.delete(key);                      // clear so next attempt can retry
        throw err;
      }),
    );
    cacheMap.set(key, sharedRequest);
  }

  // 2. Return a state-shaped stream
  return cacheMap.get(key)!.pipe(
    map(data => ({ loading: false, data, error: false })),
    startWith({ loading: true, data: [] as any, error: false }),
    catchError(() => of({ loading: false, data: [] as any, error: true })),
  );
}
```

**Three operators carrying the weight:**

- **`shareReplay(1)`** — the cache primitive. The first subscriber
  triggers the HTTP call; every subsequent subscriber receives the same
  cached value without re-fetching. `1` means "replay the last emitted
  value to late subscribers."
- **`tap`** with `setTimeout` — schedule eviction. After 5 minutes, the
  entry is removed from the Map; the next request for that key triggers
  a fresh HTTP call.
- **`catchError` that deletes the entry** — important. If a cached
  observable errors, we don't want it cached. Delete the key so the
  next attempt can succeed without us manually invalidating.

### Step 3b — use the operator in the component

```typescript
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  Subject,
  merge,
  Observable,
  debounceTime,
  distinctUntilChanged,
  switchMap,
  of,
} from 'rxjs';
import { withCache } from './operators/cache.operator';

@Component({
  selector: 'app-user-search',
  template: `
    <input
      (input)="searchTerm.set($any($event.target).value)"
      (keyup.enter)="searchNow()"
      placeholder="Type to search or press Enter..."
    />
    @if (searchState().loading) { <p>Loading...</p> }
    <ul>
      @for (user of searchState().data; track user.id) {
        <li>{{ user.name }}</li>
      }
    </ul>
  `,
})
export class UserSearchComponent {
  private readonly http = inject(HttpClient);
  readonly searchTerm = signal('');
  private readonly forceSearch$ = new Subject<string>();
  private readonly cache = new Map<string, Observable<User[]>>();

  readonly searchState = toSignal(
    merge(
      toObservable(this.searchTerm).pipe(debounceTime(300)),
      this.forceSearch$,
    ).pipe(
      distinctUntilChanged(),
      switchMap(query => {
        if (!query) {
          return of({ loading: false, data: [], error: false });
        }
        const request$ = this.http.get<User[]>(`api/users?q=${query}`);
        return withCache(query, this.cache, request$);
      }),
    ),
    { initialValue: { loading: false, data: [], error: false } },
  );

  searchNow(): void { this.forceSearch$.next(this.searchTerm()); }
  clearCache(): void { this.cache.clear(); }
}

interface User { id: number; name: string; }
```

Works. But — there's a UX problem with this design that the next stage
fixes.

### The cold-cache problem

Watch what happens when a user revisits a search they've done before:

1. User types "Alice" — `loading: true`, then data lands
2. User types "Bob" — `loading: true`, then data lands
3. User types "Alice" again — **`loading: true` again** (from the
   `startWith` in `withCache`), then data lands "instantly"

The user sees a loader for a value we already have. The data **is** in
the cache, but the `startWith({ loading: true })` runs unconditionally
on every subscription. The cache speeds up the network round-trip but
doesn't change the perceived UX — there's still a flash of loading.

---

## Stage 4 — Stale-While-Revalidate (SWR)

The fix is a different architecture: **always show whatever's in cache
immediately, even if it's stale, while firing a background request
for fresh data.** The component renders the stale data right away,
shows a subtle "refreshing" hint while the network call runs, and swaps
in fresh data when it arrives.

This is the **SWR pattern** (popularized by Vercel's `swr` library and
React Query, now ubiquitous across the JS ecosystem). It's a meaningful
UX shift — users see data faster than the network can deliver it,
because they're seeing what we already have.

### Step 4a — the SWR service

Pull caching out of the component and into a service. The service
returns a new state shape with an `isStale` flag:

```typescript
// File: services/cached-search.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, map, startWith, catchError, tap } from 'rxjs';

export interface SWRState<T> {
  loading: boolean;
  data: T | null;
  error: boolean;
  isStale?: boolean;    // ← the SWR signal: "this data is from cache, fresh is loading"
}

@Injectable({ providedIn: 'root' })
export class SearchService {
  private readonly http = inject(HttpClient);
  private readonly cache = new Map<string, unknown>();

  fetchSWR<T>(key: string, url: string): Observable<SWRState<T>> {
    const hasCache = this.cache.has(key);
    const staleData = this.cache.get(key) as T | undefined;

    const networkRequest$ = this.http.get<T>(url).pipe(
      tap(newData => this.cache.set(key, newData)),
      map(newData => ({
        loading: false,
        data: newData,
        error: false,
        isStale: false,
      })),
      catchError(() => of({
        loading: false,
        data: staleData ?? null,      // fall back to stale on error
        error: true,
        isStale: false,
      })),
    );

    return networkRequest$.pipe(
      startWith({
        loading: !hasCache,           // only show "loading" on FIRST visit
        data: staleData ?? null,      // show stale data immediately if we have it
        error: false,
        isStale: hasCache,            // flag it as stale if we're refreshing
      }),
    );
  }
}
```

**The mechanism in one paragraph.** When `fetchSWR(key, url)` is called,
the service checks the cache. If something's there, it immediately
emits a state with `data: staleData, isStale: true, loading: false`.
At the same time, the network request fires. When the response lands,
it emits a new state with `data: newData, isStale: false`. The cache
is updated for the next call. If the network errors **and** we have
stale data, we keep showing the stale data; only if there's no cache
at all do we surface a hard error.

### Step 4b — consume SWR state in the component

```typescript
import { Component, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  Subject,
  merge,
  debounceTime,
  distinctUntilChanged,
  switchMap,
  of,
} from 'rxjs';
import { SearchService } from './services/cached-search.service';

@Component({
  selector: 'app-user-search',
  template: `
    <div class="search-box">
      <input
        #searchInput
        (input)="searchTerm.set(searchInput.value)"
        (keyup.enter)="searchNow()"
        placeholder="Search users (press Enter for immediate search)..."
      />

      <!-- First-time loading: no data yet -->
      @if (searchState().loading) {
        <div class="loader">Connecting to server...</div>
      }

      <!-- SWR state: showing stale data while refresh runs -->
      <div [class.refreshing]="searchState().isStale">
        @if (searchState().isStale) {
          <p class="stale-hint">Showing cached data — fetching latest...</p>
        }

        <ul>
          @for (user of searchState().data ?? []; track user.id) {
            <li>{{ user.name }} — {{ user.email }}</li>
          } @empty {
            @if (!searchState().loading) {
              <li>No matches found.</li>
            }
          }
        </ul>
      </div>

      @if (searchState().error) {
        <div class="error-msg">⚠️ Failed to load data. Please try again.</div>
      }
    </div>
  `,
  styles: `
    .refreshing { opacity: 0.6; pointer-events: none; }
    .stale-hint { font-size: 12px; color: orange; font-style: italic; }
    .error-msg { color: red; font-weight: bold; }
    .loader { color: #007bff; }
    ul { list-style: none; padding: 0; }
    li { padding: 8px; border-bottom: 1px solid #eee; }
  `,
})
export class UserSearchComponent {
  private readonly searchService = inject(SearchService);
  readonly searchTerm = signal('');
  private readonly forceSearch$ = new Subject<string>();

  readonly searchState = toSignal(
    merge(
      toObservable(this.searchTerm).pipe(
        debounceTime(300),
        distinctUntilChanged(),
      ),
      this.forceSearch$,
    ).pipe(
      distinctUntilChanged(),
      switchMap(q => {
        if (!q.trim()) {
          return of({ loading: false, data: [], error: false, isStale: false });
        }
        return this.searchService.fetchSWR<User[]>(
          `search-${q}`,
          `https://jsonplaceholder.typicode.com/users?q=${encodeURIComponent(q)}`,
        );
      }),
    ),
    { initialValue: { loading: false, data: [], error: false, isStale: false } },
  );

  searchNow(): void { this.forceSearch$.next(this.searchTerm()); }
}

interface User { id: number; name: string; email: string; }
```

**The template now has three distinct visual states:**

1. **First-time load** (`loading: true`, `data: null`) — show a big
   loader. This is the only time the user waits without seeing anything.
2. **Stale-revalidating** (`loading: false`, `data: [...]`, `isStale:
   true`) — show the cached data with `opacity: 0.6` and a small
   "fetching latest" hint. Users can read while we refresh.
3. **Fresh** (`loading: false`, `data: [...]`, `isStale: false`) — show
   the data normally.

The user only sees a hard loading state once per cache lifetime. Every
subsequent visit feels instant. That's the SWR win.

---

## Stage 5 — multi-filter and URL sync

Real search has filters. The user wants to search "Alice" filtered by
gender "Female" within departments "Angular" and "Vue." And the URL
should reflect that state so they can share it.

### The architecture

- **One signal per source of state.** `searchTerm`, `filterGender`,
  `selectedDeps` — three signals, each owned by its UI control.
- **`combineLatest` over their observable projections** — produces a
  unified stream whenever any input changes. Query is debounced;
  filters apply immediately (the locked convention).
- **An `effect()` that pushes signal state back to the URL via
  `router.navigate`** — runs whenever any source signal changes, with
  `replaceUrl: true` so we don't pollute history on every keystroke.
- **Initial signal values hydrated from `route.snapshot.queryParamMap`**
  — so a shared URL restores the exact filtered state.

```typescript
import { Component, effect, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  Subject,
  combineLatest,
  merge,
  debounceTime,
  distinctUntilChanged,
  switchMap,
  of,
} from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import { SearchService, SWRState } from './services/cached-search.service';

interface User { id: number; name: string; email: string; }

@Component({
  selector: 'app-user-search',
  template: `
    <div class="search-box">
      <div class="container-search">
        <input
          #searchInput
          (input)="searchTerm.set(searchInput.value)"
          (keyup.enter)="searchNow()"
          placeholder="Search users (press Enter for immediate search)..."
        />

        <div class="container-deps">
          @for (dept of listDeps(); track dept.id) {
            <label>
              <input
                type="checkbox"
                [checked]="selectedDeps().includes(dept.id)"
                (change)="toggleDeps(dept.id)"
              />
              {{ dept.name }}
            </label>
          }
        </div>

        <div class="container-gender">
          @for (gender of listGender(); track gender.id) {
            <label>
              <input
                type="radio"
                [checked]="filterGender() === gender.id"
                (change)="changeGender(gender.id)"
              />
              {{ gender.name }}
            </label>
          }
        </div>
      </div>

      @if (searchState().loading) {
        <div class="loader">Connecting to server...</div>
      }

      <div [class.refreshing]="searchState().isStale">
        @if (searchState().isStale) {
          <p class="stale-hint">Showing cached data — fetching latest...</p>
        }

        <ul>
          @for (user of searchState().data ?? []; track user.id) {
            <li>{{ user.name }} — {{ user.email }}</li>
          } @empty {
            @if (!searchState().loading) {
              <li>No matches found.</li>
            }
          }
        </ul>
      </div>

      @if (searchState().error) {
        <div class="error-msg">⚠️ Failed to load data. Please try again.</div>
      }
    </div>
  `,
})
export class UserSearchComponent {
  private readonly searchService = inject(SearchService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  // 1. Source signals — hydrate from URL query params on construction
  readonly searchTerm = signal(this.route.snapshot.queryParamMap.get('q') ?? '');
  readonly filterGender = signal(this.route.snapshot.queryParamMap.get('gender') ?? 'all');
  readonly selectedDeps = signal<string[]>(
    this.route.snapshot.queryParamMap.getAll('deps') ?? [],
  );

  // Static lookup tables (could come from a service)
  readonly listGender = signal([
    { id: 'all',  name: 'All' },
    { id: '1', name: 'Male' },
    { id: '2', name: 'Female' },
    { id: '3', name: 'Other' },
  ]);
  readonly listDeps = signal([
    { id: '1', name: 'Angular' },
    { id: '2', name: 'React' },
    { id: '3', name: 'Vue' },
  ]);

  private readonly forceSearch$ = new Subject<string>();

  constructor() {
    // URL sync — any source signal change updates the query string.
    // replaceUrl: true keeps the back button sane.
    effect(() => {
      const q = this.searchTerm() || null;
      const gender = this.filterGender();
      const deps = this.selectedDeps();

      this.router.navigate([], {
        queryParams: {
          q,
          gender: gender === 'all' ? null : gender,
          deps: deps.length > 0 ? deps : null,
        },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    });
  }

  // 2. Combine all three input streams
  //    - query: debounced (search-as-you-type)
  //    - gender, deps: immediate (filters should apply on click)
  readonly searchState = toSignal(
    combineLatest({
      query: merge(
        toObservable(this.searchTerm).pipe(debounceTime(300)),
        this.forceSearch$,
      ).pipe(distinctUntilChanged()),
      gender: toObservable(this.filterGender),
      deps: toObservable(this.selectedDeps),
    }).pipe(
      switchMap(({ query, gender, deps }) => {
        // Skip when nothing to search by — empty query AND no filters active.
        // The original demo's guard ignored deps; this version includes it.
        const hasActiveFilters = gender !== 'all' || deps.length > 0;
        if (!query.trim() && !hasActiveFilters) {
          return of<SWRState<User[]>>({
            loading: false, data: [], error: false, isStale: false,
          });
        }

        // Cache key must include every dimension that affects results.
        // encodeURIComponent on each piece — values may contain & or =.
        const key = [
          'search',
          encodeURIComponent(query),
          gender,
          deps.join(','),
        ].join('-');

        const url = `api/users?q=${encodeURIComponent(query)}`
          + `&gender=${gender}`
          + `&deps=${deps.map(encodeURIComponent).join(',')}`;

        return this.searchService.fetchSWR<User[]>(key, url);
      }),
    ),
    { initialValue: { loading: false, data: [], error: false, isStale: false } },
  );

  // Imperative handlers
  searchNow(): void { this.forceSearch$.next(this.searchTerm()); }
  changeGender(g: string): void { this.filterGender.set(g); }
  toggleDeps(d: string): void {
    this.selectedDeps.update(curr =>
      curr.includes(d) ? curr.filter(x => x !== d) : [...curr, d],
    );
  }
}
```

**Three patterns worth absorbing:**

- **Debounce on query, immediate on filters.** Search-as-you-type needs
  the 300ms wait so we don't fire a request per keystroke. Filter
  toggles are deliberate user actions — apply them instantly. The
  `combineLatest` object form makes this composition explicit: only the
  `query` stream has `debounceTime` inside it.

- **Cache key includes every dimension that affects results.** If you
  search "alice" with gender="Female" and gender="Male", those are
  different result sets — they need different cache keys. The
  `'search-alice-2-1,3'` style key encodes every input.

- **`effect()` for one-way signal-to-URL sync.** Not `combineLatest` +
  `subscribe`, not `valueChanges` (no form here). Just an effect that
  reads signals and calls `router.navigate`. The framework re-runs the
  effect whenever any of the signals it reads changes. This is the
  v22-idiomatic shape for "side effects driven by signal state."

### Why `replaceUrl: true` matters

Without it, every keystroke creates a history entry. Press Back ten times
to undo "alice." With it, the URL updates in place — Back goes to the
previous *page*, not the previous *character*. Almost always what you
want for search-state-in-URL.

---

## Trade-offs and when NOT to use each stage

**Stage 1 (basic debounce/switchMap)** — use this when:

- Single search box, no filters
- No requirement to cache or share results across instances
- Server can handle one request per typing pause without strain

Don't add anything else if you don't need it.

**Stage 2 (Enter shortcut)** — add when:

- Users have asked for it (some won't, depending on your audience)
- Search latency is high enough that the 300ms wait feels long

**Stage 3 (TTL caching)** — add when:

- Backend cost per query is meaningful
- Same queries get repeated across navigation events
- BUT: think hard before adding it for true search — search results
  legitimately change over time (new users, new posts). A 5-minute
  cache can show 5-minute-old "no results" when results now exist.

**Stage 4 (SWR)** — add when:

- Stage 3's cold-cache UX (loader on every re-search) is unacceptable
- Stale data is "useful while we wait" rather than dangerous
- The backend supports the "fetch on every visit" load increase from
  always-revalidating

**Don't use SWR when:**

- Data must be **strictly fresh** (financial trading, dosing
  calculations, real-time game state). The "stale OK" assumption is
  load-bearing.
- The data is so cheap to compute that caching is overhead.

**Stage 5 (multi-filter + URL sync)** — add when:

- Users genuinely benefit from shareable URLs
- The filter combinations are meaningful navigation state
- BUT: think about the cardinality. If filters are 6 booleans, you have
  64 cacheable combinations — manageable. If filters are arbitrary
  text fields, the cache key space is unbounded; SWR becomes a memory
  leak.

### Common pitfalls across stages

- **`map` instead of `switchMap`** — runs all requests in parallel and
  preserves none of the cancellation guarantees. Stale responses
  overwrite fresh ones. Always `switchMap` for search-as-you-type.
- **Missing `distinctUntilChanged()` after `merge`** — same query
  through both streams fires the request twice. Add the second one.
- **Forgetting `encodeURIComponent`** — query containing `&` or `=`
  silently breaks. The demo's original `url = api/users?q=${query}` is
  vulnerable; this recipe encodes every interpolated value.
- **Cache key that drops a filter dimension** — silent bug. Add gender,
  searches return wrong results because the cache hit ignores it. List
  every dimension in the key, every time.
- **`replaceUrl: false` (default) when syncing on every keystroke** —
  history explosion. Always `replaceUrl: true` for state-in-URL.
- **Caching errors as if they were data** — store the cache entry only
  on success. The `catchError` should `cacheMap.delete(key)` or never
  set it in the first place.

---

## See also

- [RxJS — higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md) — `switchMap`, `mergeMap`, `concatMap`, `exhaustMap`
- [RxJS — combination operators](../../reactivity/rxjs/rxjs-combination.md) — `merge`, `combineLatest`, `zip`
- [Signals](../../reactivity/signals.md) — `signal()`, `computed()`, `effect()`
- [toSignal / toObservable](../../reactivity/to-signal.md) — bridging RxJS and signals
- [HTTP](../../http/http.md) — `HttpClient`, cancellation, error handling
- [Routing](../../routing/routing.md) — query params, `route.snapshot`, `withComponentInputBinding`
- [`takeUntilDestroyed`](../reactivity/take-until-destroyed.md) — companion recipe; the cleanup primitive that `toSignal` uses internally

## References

- [`switchMap` operator (RxJS)](https://rxjs.dev/api/operators/switchMap)
- [`shareReplay` operator (RxJS)](https://rxjs.dev/api/operators/shareReplay)
- [`combineLatest` (RxJS)](https://rxjs.dev/api/index/function/combineLatest)
- [`effect` API (angular.dev)](https://angular.dev/api/core/effect)
- [`Router.navigate` API (angular.dev)](https://angular.dev/api/router/Router#navigate)
- [SWR pattern (Vercel)](https://swr.vercel.app/docs/getting-started) — the React library that popularized the pattern
- [HTTP caching for the Wary](https://csswizardry.com/2019/03/cache-control-for-civilians/) — for the "when to cache at all" mental model

## Demo source

Adapted from [`AngularDemos/features/search-engine`](https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/search-engine). Six files in the original — `basic-search.component.ts`, `cached-search.component.ts`, `search.component.ts`, `full-search.component.ts`, `operators/cache.operator.ts`, and two service iterations (`cached-search-v1.service.ts` for TTL caching, `cached-search.service.ts` for SWR). Three bugs fixed silently (broken template literal in the SWR consumer, dead unreachable code after a `withCache` return, and the empty-deps case in the skip guard).
---
recipe_id: "optimistic-updates"
title: "Optimistic Updates: UI That Feels Instant Without Lying"
file: "recipes/forms-and-search/optimistic-updates.md"
primary_concept: "reactivity/signals"
related_concepts: ["reactivity/signals", "http/http", "reactivity/rxjs/rxjs-higher-order"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Optimistic Updates: UI That Feels Instant Without Lying

> **What you'll build:** four real-world optimistic-update patterns — like
> button toggle, add-to-cart with temporary IDs, inline rename, and
> multi-field form save. Each applies the user's intent locally
> immediately, fires the request in the background, and rolls back cleanly
> on failure. Signals make snapshot/restore almost free; composition with
> the [race-conditions](../reactivity/race-conditions.md) decision tree
> handles double-clicks; composition with the
> [request-deduplication](../http/request-deduplication.md) cache handles
> the "stale read after mutation" problem.
>
> **Concepts you'll touch:** [Signals](../../reactivity/signals.md), [HTTP](../../http/http.md), [Higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md)
>
> **Time:** ~25 minutes to read; ~2 hours to refactor a pessimistic
> update flow once you can see the patterns.

---

## The scenario

A user is scrolling a social feed on their phone. They tap the Like button on a post. Nothing happens for 400ms. They tap again, harder this time. Then the first tap registers, then the second tap registers — they've liked and immediately un-liked the post. From their perspective: "this app is laggy and broken."

What happened: the like button waits for the server's response before updating the UI. Even on a fast connection, 200–500ms of round-trip time is enough to feel broken. On a 4G connection in a metro tunnel, it can be seconds.

The fix is **optimistic UI**: assume the action will succeed, update the UI immediately, fire the request in the background, and roll back only on actual failure. Instagram, Twitter, Facebook, Slack — every modern app that "feels fast" does this. The user sees their tap register instantly. The server gets the request asynchronously. If something fails, the rollback is the rare case, not the common one.

Signals make this pattern almost trivial. The signal *is* the UI state; snapshotting it is reading it; restoring it is calling `.set()` with the snapshot. Half the work is in the visible code; the rest is handling the failure cases without confusing the user.

---

## The naive pessimistic approach

For comparison, the "wait for the server" version:

```typescript
@Component({ /* … */ })
export class FeedComponent {
  private readonly http = inject(HttpClient);
  readonly posts = signal<Post[]>([]);

  toggleLike(postId: string): void {
    const post = this.posts().find(p => p.id === postId);
    if (!post) return;

    // Wait for the server before updating UI
    this.http
      .post<Post>(`/api/posts/${postId}/${post.liked ? 'unlike' : 'like'}`, {})
      .subscribe(updated => {
        this.posts.update(posts =>
          posts.map(p => (p.id === postId ? updated : p)),
        );
      });
  }
}

interface Post {
  id: string;
  title: string;
  liked: boolean;
  likeCount: number;
}
```

Symptoms in practice:
- Tap → 400ms blank → button visually flips. The user already started doubting.
- Slow network → 2-second wait → many users tap again, doubling the action.
- Failed request → silent failure unless you wired up error handling.

**The pessimistic pattern is correct but slow.** The optimistic pattern is fast but requires handling the failure case.

---

## Pattern 1 — single-item toggle (Like button)

The simplest optimistic case: a boolean field flips, with rollback on failure.

```typescript
@Component({ /* … */ })
export class FeedComponent {
  private readonly http = inject(HttpClient);
  readonly posts = signal<Post[]>([]);

  toggleLike(postId: string): void {
    const before = this.posts();
    const post = before.find(p => p.id === postId);
    if (!post) return;

    const nextLiked = !post.liked;
    const delta = nextLiked ? 1 : -1;

    // Optimistic: apply locally first
    this.posts.update(posts =>
      posts.map(p =>
        p.id === postId
          ? { ...p, liked: nextLiked, likeCount: p.likeCount + delta }
          : p,
      ),
    );

    // Fire the request in the background
    this.http
      .post<Post>(`/api/posts/${postId}/${nextLiked ? 'like' : 'unlike'}`, {})
      .subscribe({
        next: serverPost => {
          // Reconcile with server response — handles cases where server
          // returns slightly different data (e.g., different likeCount
          // because someone else liked it concurrently)
          this.posts.update(posts =>
            posts.map(p => (p.id === postId ? serverPost : p)),
          );
        },
        error: () => {
          // Roll back to the pre-action snapshot
          this.posts.set(before);
          // Tell the user something went wrong (toast, banner, etc.)
        },
      });
  }
}
```

**Five things doing the work:**

- **`const before = this.posts();`** — snapshot the entire array. Signals return the same reference each call until updated, so this is a cheap pointer copy. Restoring is `this.posts.set(before)`.
- **`this.posts.update(posts => posts.map(...))`** — immutable update. The new array references different objects for the changed posts, same references for the rest. Angular's change detection sees the changed references and re-renders.
- **`next: serverPost =>`** — reconcile with server data, not just "trust local." The server might have authoritative data (a different `likeCount` because others liked concurrently). Apply it on success.
- **`error: () => this.posts.set(before)`** — rollback to the exact pre-action state. The snapshot captured the entire array; restoring is one line.
- **The button is responsive in the template** without `[disabled]` during the request. The user sees the like fire instantly; they can scroll, like other posts, navigate away — none of which is blocked by the in-flight request.

### The double-click race

The user taps Like twice rapidly. Two optimistic flips happen. Two requests fire. If the server uses idempotent endpoints (`PUT /likes/{userId}` is the same regardless of repeats), the end state is correct. If it uses non-idempotent endpoints, you can end up with mismatched UI and server state.

From the [race-conditions recipe](../reactivity/race-conditions.md#race-3--double-submit-the-two-charges-bug), the fix is `exhaustMap`:

```typescript
private readonly likeQueue = new Subject<string>();

constructor() {
  this.likeQueue.pipe(
    exhaustMap(postId => this.processToggle(postId)),
    takeUntilDestroyed(),
  ).subscribe();
}

toggleLike(postId: string): void {
  // The optimistic flip still happens immediately:
  this.applyOptimisticFlip(postId);
  // The actual request is queued:
  this.likeQueue.next(postId);
}
```

`exhaustMap` drops subsequent emissions while one is in flight. Combined with optimistic UI, the user sees their second tap register visually (toggling back) but the second HTTP request is queued for after the first completes. For idempotent endpoints, this works because the final state matches the last visible UI.

For most "Like"-class actions, **idempotent server endpoints + optimistic UI + no flow control** is the right combination. The pattern above is for cases where the server endpoint genuinely can't tolerate duplicate requests.

---

## Pattern 2 — list operations with temporary IDs

Adding an item to a cart: the local UI needs to show the item immediately, but the server hasn't assigned the real ID yet. Use a temporary ID, then replace it on success.

```typescript
interface CartItem {
  id: string;          // server ID after sync; temp ID before
  productId: string;
  quantity: number;
  syncing?: boolean;   // local-only marker
}

@Component({ /* … */ })
export class CartComponent {
  private readonly http = inject(HttpClient);
  readonly items = signal<CartItem[]>([]);

  addItem(productId: string, quantity: number): void {
    const tempId = `temp-${crypto.randomUUID()}`;
    const optimisticItem: CartItem = {
      id: tempId,
      productId,
      quantity,
      syncing: true,
    };

    // Optimistic add — shows up immediately at the end of the cart
    this.items.update(items => [...items, optimisticItem]);

    this.http.post<CartItem>('/api/cart', { productId, quantity }).subscribe({
      next: serverItem => {
        // Replace the temp item with the server's version
        this.items.update(items =>
          items.map(item =>
            item.id === tempId ? { ...serverItem, syncing: false } : item,
          ),
        );
      },
      error: () => {
        // Remove the optimistic item entirely
        this.items.update(items => items.filter(item => item.id !== tempId));
        // Toast: "Couldn't add to cart. Try again."
      },
    });
  }

  removeItem(itemId: string): void {
    const before = this.items();
    const item = before.find(i => i.id === itemId);
    if (!item) return;

    // Optimistic remove
    this.items.update(items => items.filter(i => i.id !== itemId));

    // Don't try to delete temp items that never reached the server
    if (itemId.startsWith('temp-')) return;

    this.http.delete(`/api/cart/${itemId}`).subscribe({
      error: () => this.items.set(before),
    });
  }
}
```

**Three patterns doing the work:**

- **Temporary IDs prefixed with `temp-`.** Server IDs come from the server (e.g., UUIDs assigned on insert, or auto-incremented integers). The local optimistic insert needs *something* to identify the item before the server response arrives. The `temp-` prefix makes them trivially detectable.

- **`syncing: true` local-only field.** UI can show a subtle indicator ("…") next to items that haven't yet synced. The field is filtered out before sending to the server (use a serializer if needed, or pick only the fields the server expects).

- **`removeItem` checks for temp-IDs.** If the user adds then immediately removes an item, the temp version may never have reached the server. Don't fire a DELETE for a non-existent ID — it would return 404 and break the rollback logic.

### The "user keeps editing while syncing" race

The user adds Item A. While the POST is in flight, they update its quantity. Two states diverge:

1. The local item now has the new quantity (the user's intent).
2. The server received the POST with the original quantity. It returns the saved item with the original.

If we naively replace on the POST response, we overwrite the user's local edit. The solution: **track which fields the user has locally edited, and merge selectively on server response.**

For simple cases (a counter), it's enough to ignore the server's value for that field if the local value differs:

```typescript
next: serverItem => {
  this.items.update(items =>
    items.map(item => {
      if (item.id !== tempId) return item;
      return {
        ...serverItem,
        // Preserve the local quantity if the user changed it during sync
        quantity: item.quantity !== optimisticItem.quantity
          ? item.quantity
          : serverItem.quantity,
        syncing: false,
      };
    }),
  );
}
```

For complex cases (a deeply-nested form), this gets messy. **Better**: queue local edits and apply them after the initial sync completes. The [race-conditions recipe](../reactivity/race-conditions.md#race-5--multi-source-race-auto-save-vs-explicit-save) covers the merge pattern.

---

## Pattern 3 — inline edit (rename)

A user double-clicks a post title to edit it. They type a new title, press Enter. The UI flips immediately to show the new title. The PATCH fires in the background.

```typescript
@Component({ /* … */ })
export class PostListComponent {
  private readonly http = inject(HttpClient);
  readonly posts = signal<Post[]>([]);

  renamePost(postId: string, newTitle: string): void {
    const trimmed = newTitle.trim();
    if (!trimmed) return;

    const before = this.posts();
    const oldPost = before.find(p => p.id === postId);
    if (!oldPost || oldPost.title === trimmed) return;

    // Optimistic update
    this.posts.update(posts =>
      posts.map(p => (p.id === postId ? { ...p, title: trimmed } : p)),
    );

    this.http
      .patch<Post>(`/api/posts/${postId}`, { title: trimmed })
      .subscribe({
        next: serverPost => {
          // Reconcile: server may have normalized the title (trimmed,
          // case-adjusted, stripped emojis, etc.)
          this.posts.update(posts =>
            posts.map(p => (p.id === postId ? serverPost : p)),
          );
        },
        error: () => {
          this.posts.set(before);
        },
      });
  }
}
```

The "reconcile on success" step matters here more than in Pattern 1: servers often normalize titles. The user types `"  My Post  "` with surrounding whitespace; the server stores `"My Post"`. Without reconciliation, the local state diverges (it has whitespace), which causes subtle bugs on the next edit (the user's "no change" looks like a change to the server).

### Cancellation if the user undoes

A common UX: the user starts editing, makes changes, then presses Escape to cancel. The optimistic update shouldn't fire at all. The component-side fix:

```typescript
@Component({ /* … */ })
export class EditablePostComponent {
  readonly post = input.required<Post>();
  readonly draftTitle = signal('');
  readonly isEditing = signal(false);

  startEdit(): void {
    this.draftTitle.set(this.post().title);
    this.isEditing.set(true);
  }

  commitEdit(): void {
    this.parent.renamePost(this.post().id, this.draftTitle());
    this.isEditing.set(false);
  }

  cancelEdit(): void {
    this.isEditing.set(false);
    // draftTitle is discarded; no request, no optimistic update
  }
}
```

`commitEdit` triggers the optimistic update + PATCH. `cancelEdit` just exits edit mode without touching anything. Two separate paths.

---

## Pattern 4 — multi-field form save

A profile-edit form: user changes their name, bio, and city, then clicks Save. The optimistic update applies all three changes locally, then fires one PATCH with all of them.

```typescript
@Component({ /* … */ })
export class ProfileEditComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly http = inject(HttpClient);
  readonly currentUser = signal<User | null>(null);

  readonly form = this.fb.group({
    name: this.fb.control(''),
    bio: this.fb.control(''),
    city: this.fb.control(''),
  });

  constructor() {
    // Initialize the form from the current user when it loads
    effect(() => {
      const user = this.currentUser();
      if (user) {
        this.form.patchValue({
          name: user.name,
          bio: user.bio,
          city: user.city,
        });
      }
    });
  }

  saveProfile(): void {
    const user = this.currentUser();
    if (!user || this.form.invalid) return;

    const updates = this.form.getRawValue();
    const before = user;
    const optimistic = { ...user, ...updates };

    // Optimistic — UI reflects the new values immediately
    this.currentUser.set(optimistic);

    this.http
      .patch<User>(`/api/users/${user.id}`, updates)
      .subscribe({
        next: serverUser => {
          // Reconcile with server (handles normalization, computed fields)
          this.currentUser.set(serverUser);
        },
        error: () => {
          this.currentUser.set(before);
          // The form still has the user's input — they can retry or cancel
        },
      });
  }
}
```

The form value remains the user's input even after the rollback. They can correct an issue (maybe the bio was too long and the server rejected it with a 400) and retry. **Don't reset the form on error** — that would lose their typing for no good reason.

---

## Composing with request-deduplication — invalidate on mutation

The [request-deduplication recipe](../http/request-deduplication.md) introduced a cache that survives across components. With optimistic updates, the cache holds the *old* version of the data; the next read returns stale state.

The pattern: **invalidate the relevant cache key when a mutation completes**:

```typescript
@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);
  private readonly cache = inject(HttpDedupRegistry);

  updateProfile(userId: string, updates: Partial<User>): Observable<User> {
    return this.http.patch<User>(`/api/users/${userId}`, updates).pipe(
      tap(() => {
        // The cached GET for this user is now stale.
        // Next read will hit the server.
        this.cache.invalidate(`GET:/api/users/${userId}`);
      }),
    );
  }
}
```

The optimistic update handles the immediate-UI case. The cache invalidation handles "user navigates away, comes back, reads again, sees the new data." Without invalidation, the user would see the optimistic value in the current component but the *old* value in a sibling component that reads from cache.

---

## UI feedback patterns

How much should the user know about the optimistic round-trip?

### Pattern A — pure optimistic (no indicator)

For low-stakes, high-frequency actions (Like, Follow, scroll-position), no indicator at all. The action looks instant; failures are rare and rollbacks are silent. The user might not even notice a rollback if the network glitched briefly.

When to use: actions where the worst-case (a brief visual flicker on rollback) is better than a constant "syncing" indicator.

### Pattern B — subtle syncing indicator

For medium-stakes actions (add to cart, draft save, profile edit), show a subtle dot/spinner next to the action while it syncs. The user can see "something's happening" without it being intrusive.

```html
<button (click)="like(post)">
  ♥ {{ post.likeCount }}
  @if (post.syncing) {
    <span class="syncing-dot" aria-label="Syncing"></span>
  }
</button>
```

The `syncing` field is a local-only marker, set to `true` when the optimistic update fires and `false` when the server response (or rollback) lands.

### Pattern C — explicit success/failure feedback

For high-stakes actions (payment, send-message, schedule), show full state — "Saving…", "Saved", or "Failed — Retry." The user is making a commitment; they want to know the system tracked it.

```html
@switch (saveState()) {
  @case ('idle')     {}
  @case ('saving')   { <span>Saving…</span> }
  @case ('saved')    { <span class="success">✓ Saved</span> }
  @case ('failed')   { <span class="error">✗ Couldn't save — <button (click)="retry()">Retry</button></span> }
}
```

Trade-off: more visual clutter, but the user has confidence in the system's behavior. For payments and sends, this is almost always the right pattern; for likes, it would be obnoxious.

---

## Variations

### Optimistic with retry on transient failure

Network errors are transient; the user's action shouldn't fail just because their connection flickered. Compose with the [retry recipe](../http/retry-with-backoff.md):

```typescript
toggleLike(postId: string): void {
  const before = this.posts();
  this.applyOptimisticFlip(postId);

  this.http.post(`/api/posts/${postId}/like`, {}).pipe(
    retryWithBackoff({ maxAttempts: 3 }),
  ).subscribe({
    error: () => this.posts.set(before),
  });
}
```

The optimistic UI shows the user's intent immediately. The retry handles transient failures. The rollback only fires after retries have been exhausted. The user only sees a rollback when the system has genuinely given up.

### Pending-operation queue (for high-stakes flows)

For workflows where multiple optimistic updates can stack (a chat app: typing, sending, queuing while offline), track pending operations explicitly. Each operation is a record of "what was attempted"; the queue processes them serially:

```typescript
interface PendingOp {
  id: string;
  type: 'send' | 'edit' | 'delete';
  payload: unknown;
  optimistic: () => void;
  rollback: () => void;
  request: () => Observable<unknown>;
}

@Injectable({ providedIn: 'root' })
export class OptimisticQueue {
  private readonly pending = signal<PendingOp[]>([]);
  private processing = false;

  enqueue(op: PendingOp): void {
    op.optimistic();
    this.pending.update(ops => [...ops, op]);
    this.process();
  }

  private async process(): Promise<void> {
    if (this.processing) return;
    this.processing = true;
    while (this.pending().length > 0) {
      const next = this.pending()[0];
      try {
        await firstValueFrom(next.request());
      } catch {
        next.rollback();
      } finally {
        this.pending.update(ops => ops.slice(1));
      }
    }
    this.processing = false;
  }
}
```

For chat apps, IDE-style undo stacks, or offline-first apps, this becomes essential. For most apps, the per-action snapshot/restore pattern is enough.

---

## Trade-offs and common pitfalls

**Use optimistic updates when:**

- The action is high-frequency or latency-sensitive (Like, scroll, navigate, type)
- The success rate is high enough that the rollback case is rare
- Rollbacks are visually acceptable (a brief flicker is fine for a like; not fine for "your payment failed")

**Skip optimistic updates when:**

- The action is rare and high-stakes (payment, account deletion, sending an email). The user expects to wait; they want confirmation.
- The server's response significantly transforms the input (e.g., "compute total" actions). Showing the user's input before transformation is misleading.
- Rollback would confuse the user (a complex state transition that's hard to undo cleanly).

### Common pitfalls

- **Showing "Saved" before the server confirms.** Users trust UI feedback. Showing success before confirmation, then silently rolling back, breaks that trust. For high-stakes actions, only show "Saved" after the server says yes.
- **Discarding form input on error.** The user just typed something — preserve it so they can fix and retry. Resetting the form to its pre-edit state loses their work.
- **Not reconciling with server response.** Local optimistic state diverges from server-canonical state (server normalized whitespace, capitalization, applied business rules). The next read shows different data than the UI promised. Always apply the server response on success, not just on error.
- **No rollback on silent failure.** A 4xx with a JSON error body might come through as an empty `error()` callback if the response handling drops it. Make sure every failure path triggers rollback.
- **Stacking optimistic updates without coordination.** User taps Like, then changes the post's category, then taps Like again — three optimistic updates layered. If any single one fails, rolling back is ambiguous (do we roll back to the state before that specific action, or the state at the start?). For complex flows, use the pending-operation queue pattern.
- **Memory leaks from accumulated subscriptions.** Every action creates a new HTTP subscription. Without `takeUntilDestroyed()`, a long-lived component leaks subscriptions. Apply on every HTTP call.
- **Temp IDs leaking into server payloads.** When the optimistic state has `id: "temp-..."`, subsequent operations on that item must not send the temp ID to the server. Filter `temp-` prefixed IDs in mutation methods (Pattern 2 shows the pattern).
- **Race between user's next action and the rollback.** The user taps Like (optimistic flip), waits, taps Unlike (optimistic flip). The first request fails — rollback flips it back, but now we're inconsistent with what the user sees from their second tap. Use idempotent endpoints to avoid having to coordinate, OR use a per-item lock/queue.
- **Telling the user "offline" when only one request failed.** A single failed Like doesn't mean the user is offline. Don't show "You're offline — changes won't sync" unless you've detected actual offline state (`navigator.onLine === false` or repeated failures).
- **Optimistic updates that don't compose with read caching.** The mutation went through but the cached read returns the old value. Invalidate on mutation (covered above).

---

## See also

- [Signals](../../reactivity/signals.md) — the storage primitive that makes snapshot/restore cheap
- [Race Conditions](../reactivity/race-conditions.md) — the `exhaustMap` pattern for double-click protection; the source-merge pattern for multi-source mutations
- [Request Deduplication](../http/request-deduplication.md) — the cache invalidation pattern that closes the read-after-write loop
- [Retry with Backoff](../http/retry-with-backoff.md) — composes inside the optimistic-update's HTTP call to handle transient failures
- [HTTP](../../http/http.md) — `HttpClient`, error handling, request configuration
- [Async Validation](./async-validation.md) — the optimistic-validity hint pattern for forms

## References

- [`signal` and `update` (angular.dev)](https://angular.dev/api/core/signal) — the primitive
- [Designing for offline (Google design)](https://design.google/library/designing-offline) — broader UX framework that optimistic UI is part of
- [TanStack Query — Optimistic Updates](https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates) — the canonical reference implementation; many patterns port directly
- [Slack engineering — Building Resilient Messaging](https://slack.engineering/) — production patterns for high-stakes optimistic UI
- [Linear's Pragmatic Approach to Optimistic UI](https://linear.app/blog) — case study from a product known for "instant" feel

## Demo source

Synthesized from common production optimistic-update patterns rather than a single demo file. The four-pattern taxonomy (toggle, list, inline edit, multi-field save) reflects the structure most apps converge on once they hit the "the UI feels slow" moment. The reconciliation-on-success pattern is the load-bearing detail that distinguishes "looks fast" optimistic UI from "lies to the user" optimistic UI. All code is original.
---
roadmap_node: "change-detection"
title: "Change Detection"
file: "components/change-detection.md"
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

# Change Detection

> **Lead with this:** Change detection is the process Angular uses to keep
> the DOM in sync with your component state. In Angular v22, this process
> has been re-engineered around signals: components default to `OnPush`,
> new apps run zoneless, and Angular updates only what actually changed
> rather than checking the entire tree.

## What it is

Every time data in your app changes — a button click, an HTTP response, a
signal update — Angular needs to figure out which template bindings now
display stale values and update them. The system that does this is **change
detection** (often shortened to "CD").

Two orthogonal axes determine when and how CD runs:

| Axis | Options |
| --- | --- |
| **Trigger (when does CD run?)** | **Zone-based** — Zone.js detects async events and schedules CD. <br> **Zoneless** — Angular runs CD only when signals, `markForCheck()`, or other explicit notifications fire. |
| **Strategy (how does CD walk the tree?)** | **Eager** (formerly `Default`) — check every component on every CD run. <br> **OnPush** — skip components that have not been marked dirty. |

In Angular v22:

- **OnPush is the default** for new components (was Eager before v22)
- **New apps run zoneless by default** — no Zone.js
- **`ChangeDetectionStrategy.Default` was renamed to `ChangeDetectionStrategy.Eager`**;
  `Default` still exists but is deprecated and the migration tool replaces it
- Signals fully integrate: a signal update both notifies Angular *and* tells
  it exactly which views to refresh

> The combination of OnPush + zoneless + signals is what Angular calls "the
> modern reactivity story." Each piece works alone, but they're designed to
> compose into a single, fine-grained reactivity system.

## How it works under the hood

### The two halves: "when" and "how"

Change detection has always had two halves: **when** to run it and **how**
to walk the tree once it does. These halves are independent — you can mix
and match.

#### "When" — the scheduler

In any Angular app, something has to decide that CD should run. That something
is a **scheduler**. Angular has had two:

**Zone-based scheduling.** Zone.js monkey-patches the browser's async APIs —
`setTimeout`, `setInterval`, `Promise.then`, event listeners, XHR, fetch.
Every time a patched async operation completes inside the Angular zone, Zone.js
notifies Angular. When there are no more pending microtasks
(`NgZone.onMicrotaskEmpty`), Angular calls `ApplicationRef.tick()` — which
walks the component tree and runs change detection.

This is the model Angular shipped with in 2016. It "just works" — any code
that mutates a component property gets reflected in the view. But it's
expensive: Zone.js is ~30KB raw / ~10KB gzipped, Angular doesn't know what
actually changed (so it has to check everything), and stack traces are
polluted with Zone.js internals.

**Zoneless scheduling.** Instead of monkey-patching, Angular relies on
**explicit notifications** to its `ChangeDetectionScheduler`. The notifications
come from a small, well-defined set of sources:

| Notification source | What triggers it |
| --- | --- |
| Signal write | `signal.set()`, `signal.update()`, `linkedSignal.set()`, `resource` state changes |
| `markForCheck()` | Explicit dirty marking, including from `AsyncPipe` |
| `ComponentRef.setInput()` | Dynamic component input updates |
| Template event listener | DOM events bound with `(click)`, `(input)`, etc. |
| View attach / create / insert | `ViewContainerRef.createComponent`, `ViewContainerRef.insert` |

When any of these fires, the scheduler **flips a dirty flag** on the
`ApplicationRef` and **schedules a microtask** (or animation frame, in some
cases) to run CD. Multiple notifications in the same synchronous block coalesce
into a single CD cycle.

This is faster, debuggable, and doesn't ship Zone.js — but requires that any
state your template reads goes through one of those notification sources. Code
that mutates state silently (without a signal or `markForCheck`) won't trigger
a refresh.

#### "How" — the strategies

Once CD is scheduled and runs, Angular walks the component tree top to bottom.
At each component, it checks the **change detection strategy** to decide
whether to refresh that view:

**`ChangeDetectionStrategy.Eager`** (formerly named `Default`). Every component
gets checked on every CD pass. Angular re-evaluates every template binding and
updates the DOM where it differs from the rendered output. Simple, predictable,
and wasteful at scale.

**`ChangeDetectionStrategy.OnPush`**. The component is only checked when one
of the following marks it dirty:

- An `@Input()` reference changes (not mutation — actual new reference)
- A signal it reads in its template changes
- A DOM event handler on the component or its children fires
- `ChangeDetectorRef.markForCheck()` is called explicitly
- An `AsyncPipe` in the template emits a new value (which calls `markForCheck`
  internally)

If none of those happens, Angular skips both this component and **all its
descendants** during that CD pass — even if a descendant has Eager strategy.
This is what makes OnPush valuable: the savings cascade down the tree.

### The dirty-marking algorithm

When something marks a component dirty, two flags get set on its view:

- **`RefreshView`** on the component's own view — "this view needs to be
  re-checked"
- **`HasChildViewsToRefresh`** on every ancestor up to the root — "somewhere
  in my subtree is a dirty view; traverse me to find it"

The next CD run traverses the tree. When it reaches a view:

1. If `RefreshView` is set → check this view's bindings and refresh it
2. If `HasChildViewsToRefresh` is set → traverse children but don't refresh
   this view itself
3. If neither is set → skip this view and its subtree entirely

This is why OnPush "cascades": only the path from root to dirty view is
traversed; everything else is skipped.

### Where signals fit

Signals integrate at both halves of the system.

**At the "when" half:** writing to a signal *always* schedules CD, regardless
of zone or strategy. The scheduler treats signal writes as one of its
notification sources.

**At the "how" half:** when a component's template reads a signal, Angular
records the read in a **ReactiveLViewConsumer** attached to that view. When
the signal later changes, only that specific view's `RefreshView` flag flips
— not the whole component. The CD pass refreshes exactly the views with
changed signal dependencies, plus their template-binding parents.

This is the "fine-grained" part of fine-grained reactivity. The component
doesn't have to be marked dirty; just the specific view that read the
specific signal that changed.

> **The bigger picture.** In a v22 zoneless app, change detection effectively
> becomes: "find the views whose signal dependencies changed, and refresh
> those." The traversal still happens, but the work at each view is gated
> precisely. The old "check every binding on every event" model is gone.

### From signal.set() to DOM update — the full chain

The previous sections explain "when" CD runs and "how" the traversal is gated.
But there's still a missing link: when a dirty view is actually checked, what
mutates the DOM? This is the question every developer asks when first
switching to zoneless — if Zone.js was the thing that "made the screen
update," what's doing that job now?

The full chain, end to end, from a signal write to a visible pixel change:

```
count.set(5)
   │
   ▼
1. Signal stores the new value internally
   │
   ▼
2. Signal notifies its consumers (the ReactiveLViewConsumers attached to
   every view that read count() during its last render)
   │
   ▼
3. Each notified view's RefreshView flag flips;
   each ancestor's HasChildViewsToRefresh flag flips
   │
   ▼
4. ChangeDetectionScheduler schedules a microtask
   (coalesces multiple signal writes into one tick)
   │
   ▼
5. Microtask runs → ApplicationRef.tick()
   │
   ▼
6. Tree traversal from root, gated by dirty flags — clean subtrees skipped
   │
   ▼
7. At each dirty view, the compiler-emitted template function runs in
   "update mode" — re-evaluating each binding expression
   │
   ▼
8. Each binding compares the new value to its cached previous value
   │
   ▼
9. If different → the binding calls into Renderer2 (or the default DOM renderer)
   │
   ▼
10. Renderer2 invokes the actual browser DOM API
    (element.textContent = ..., element.setAttribute(...), etc.)
   │
   ▼
11. Browser repaints on the next frame
```

The piece most developers haven't seen is **steps 7–10** — what the
"template function" actually is and how it talks to the DOM.

#### What the compiler emits

When Angular's compiler processes a component's template, it doesn't store
the template as HTML. It emits a **JavaScript function** containing
**template instructions** — calls into Angular's runtime that build and
update the DOM. The instructions are prefixed with `ɵɵ` (two Greek thetas)
to mark them as compiler-emitted internals not meant for user code.

For a tiny component:

```typescript
@Component({
  template: `
    <div>This is static</div>
    <div>This is updated {{ count() }}</div>
  `,
})
export class CounterComponent {
  count = signal(0);
}
```

The compiler emits something like:

```typescript
function CounterComponent_Template(rf, ctx) {
  if (rf & 1) {  // creation mode — runs once when view is created
    ɵɵelementStart(0, 'div');
    ɵɵtext(1, 'This is static');
    ɵɵelementEnd();
    ɵɵelementStart(2, 'div');
    ɵɵtext(3);                                       // empty text slot
    ɵɵelementEnd();
  }
  if (rf & 2) {  // update mode — runs every CD cycle
    ɵɵadvance(3);                                    // move cursor to text slot
    ɵɵtextInterpolate1('This is updated ', ctx.count(), '');
  }
}
```

Two key things from this output:

1. **The static `<div>` is created once and never touched again.** Its text
   node lives in the creation block (`rf & 1`), not the update block.
2. **Only the interpolated text node runs on every update.** The
   `ɵɵtextInterpolate1` instruction reads `ctx.count()`, compares the result
   to its cached previous value, and if different, writes the new text to
   the DOM node.

This is why fine-grained reactivity matters in practice: when `count`
changes, only the single text node updates. The static `<div>` isn't visited
at all. The compiler has already separated "build this once" from "update
this if the bound value changed."

You can see this in action by enabling Chrome DevTools' "Paint flashing" or
"Layout shift regions" — only the bound text node flashes when the signal
changes; the surrounding static DOM doesn't.

#### Renderer2 — the platform abstraction layer

Template instructions don't call browser DOM APIs directly. They go through
**`Renderer2`**, an injectable service that abstracts the actual rendering
target. This indirection is what lets Angular run on multiple platforms:

| Platform | Renderer | DOM API used |
| --- | --- | --- |
| Browser (default) | `DomRenderer` | `document.createElement`, `element.textContent`, etc. |
| Server (SSR) | `EmulatedDomRenderer` | Renders into a Domino DOM emulation, serializes to HTML string |
| NativeScript / Ionic Native | `NativeScriptRenderer` | Maps to native iOS/Android view APIs |
| Web Worker | `WorkerRenderer` | Messages a render thread that owns the real DOM |

When `ɵɵtextInterpolate1` decides a text node needs updating, it calls
something equivalent to `renderer.setValue(textNode, 'This is updated 5')`.
The browser renderer's implementation calls `textNode.nodeValue = ...`. The
server renderer's implementation appends to an HTML string buffer instead.
The same template function works on all of them.

You can use `Renderer2` directly when you need to imperatively modify the DOM
from a directive or component, and it's the right tool when you do — it
keeps your code platform-agnostic (so it survives SSR) and goes through
Angular's security pipeline:

```typescript
import { Directive, ElementRef, Renderer2, inject } from '@angular/core';

@Directive({
  selector: '[appHighlight]',
  standalone: true,
})
export class HighlightDirective {
  private el = inject(ElementRef);
  private renderer = inject(Renderer2);

  ngOnInit(): void {
    // Goes through Renderer2 — works in SSR, follows Angular's security model
    this.renderer.setStyle(this.el.nativeElement, 'background-color', 'yellow');
    this.renderer.addClass(this.el.nativeElement, 'highlighted');
  }
}
```

Compare to direct DOM access via `this.el.nativeElement.style.backgroundColor = 'yellow'`,
which would crash during SSR (no `style` object on server-side elements) and
breaks hydration on the client.

#### Old Zone.js model vs new signal-driven model — side by side

Same component update, two eras:

**Angular 2–15 with Zone.js + Default strategy:**
```
user.name = 'Bob'                          (plain property mutation)
   │
   ▼
Zone.js detects the click event handler finished
   │
   ▼
onMicrotaskEmpty fires
   │
   ▼
ApplicationRef.tick() — walks the ENTIRE component tree
   │
   ▼
Every component's template function runs in update mode
Every binding in every component re-evaluates
   │
   ▼
For each binding whose value changed:
  Renderer2 → DOM update
```

**Angular 22 with signals + zoneless + OnPush default:**
```
user.update(u => ({ ...u, name: 'Bob' }))  (signal write)
   │
   ▼
Signal notifies its specific ReactiveLViewConsumers
The one view that read user() flips RefreshView
Its ancestors flip HasChildViewsToRefresh
   │
   ▼
ChangeDetectionScheduler schedules microtask
   │
   ▼
ApplicationRef.tick() — walks only the dirty path
Skips entire clean subtrees
   │
   ▼
At the dirty view, only THAT view's template function runs in update mode
Only bindings that read changed signals re-evaluate
   │
   ▼
For each binding whose value changed:
  Renderer2 → DOM update
```

The work at the very end is identical — `Renderer2` calls into the browser's
DOM API to mutate text, attributes, classes, or styles. What changed
fundamentally is **how much of the tree gets to that final step**. In the old
model, every component was visited and every binding was re-evaluated, even
the ones that hadn't changed. In the new model, only the views that read
the changed signal are even touched.

This is the real performance story of signals + zoneless. The DOM update
step itself is no faster — it's still `textNode.nodeValue = '...'`. What
changes is how Angular finds out which DOM nodes need that update, and how
much wasted traversal it avoids on the way there.

## Basic usage

### Choosing the change detection strategy

In v22, new components are OnPush by default. You don't need to set anything:

```typescript
import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-counter',
  standalone: true,
  // No changeDetection field — defaults to OnPush in v22
  template: `
    <p>Count: {{ count() }}</p>
    <button (click)="increment()">+1</button>
  `,
})
export class CounterComponent {
  count = signal(0);
  increment() { this.count.update(c => c + 1); }
}
```

To opt into the old behavior — for example, a component that mutates state
without going through signals or `markForCheck` — set Eager explicitly:

```typescript
import {
  Component, ChangeDetectionStrategy
} from '@angular/core';

@Component({
  selector: 'app-legacy',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.Eager,
  template: `<p>{{ value }}</p>`,
})
export class LegacyComponent {
  value = 'hello';
  ngOnInit() {
    // Mutating a plain property — only works because Eager checks every CD pass
    setInterval(() => { this.value = new Date().toString(); }, 1000);
  }
}
```

### Going zoneless

For new apps, the CLI configures zoneless by default. For an existing app:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13)
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

@NgModule({
  imports: [BrowserModule],   // Zone.js included automatically
  bootstrap: [AppComponent],
})
export class AppModule {}
```

```typescript
// Standalone + zoneless (Angular 20.2+ stable)
import { bootstrapApplication } from '@angular/platform-browser';
import { provideZonelessChangeDetection } from '@angular/core';
import { AppComponent } from './app.component';

bootstrapApplication(AppComponent, {
  providers: [
    provideZonelessChangeDetection(),
  ],
});
```

Remove Zone.js from your bundle to claim the size savings:

```json
// angular.json — remove "zone.js" from polyfills
"polyfills": []
```

And remove the package entirely:

```bash
npm uninstall zone.js
```

### Triggering change detection manually

Three APIs on `ChangeDetectorRef` give you explicit control:

**`markForCheck()`** — schedule the component (and its ancestors) for the
next CD cycle. Does not run CD immediately. Safe to call many times — it's
just a flag flip.

**`detectChanges()`** — synchronously run CD on this component's subtree
*right now*. Use sparingly — it bypasses the scheduler's batching.

**`detach()` / `reattach()`** — remove or restore this component from CD
entirely. Useful for performance-critical leaf components that you'll update
imperatively.

```typescript
import {
  Component, ChangeDetectorRef, inject, ChangeDetectionStrategy
} from '@angular/core';

@Component({
  selector: 'app-realtime',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<p>{{ ticks }}</p>`,
})
export class RealtimeComponent {
  ticks = 0;
  private cdr = inject(ChangeDetectorRef);

  ngOnInit(): void {
    // Updating plain properties from setInterval doesn't auto-trigger CD in
    // either zoneless OR OnPush mode — we have to notify explicitly
    setInterval(() => {
      this.ticks++;
      this.cdr.markForCheck();
    }, 1000);
  }
}
```

> **In practice:** if you find yourself writing `markForCheck()` calls, ask
> first whether a signal would eliminate the need. `this.ticks = signal(0);
> setInterval(() => this.ticks.update(t => t + 1), 1000);` requires no
> `markForCheck` and works in zoneless without modification.

## Real-world patterns

### Pattern 1 — Migrating an existing OnPush + Observable component to signals

This is the most common modernization for production Angular apps. The old
pattern uses `OnPush` + `async` pipe:

```typescript
// Before — Observable + AsyncPipe (still works in v22, just not idiomatic)
@Component({
  selector: 'app-user-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (user$ | async; as user) {
      <p>{{ user.name }}</p>
    }
  `,
})
export class UserCardComponent {
  user$ = inject(UserService).getCurrentUser();
}
```

```typescript
// After — signals (or httpResource)
import { httpResource } from '@angular/common/http';

@Component({
  selector: 'app-user-card',
  standalone: true,
  // No changeDetection field — OnPush by default in v22
  template: `
    @if (userRes.hasValue()) {
      <p>{{ userRes.value().name }}</p>
    }
  `,
})
export class UserCardComponent {
  userRes = httpResource<User>(() => `/api/users/me`);
}
```

The signal version is simpler, has no subscription leak risk, and doesn't
need the `async` pipe to mark the component dirty.

### Pattern 2 — Running heavy work outside Angular's awareness

A canvas animation, a chart library that emits many internal events, a third-
party library that hammers events — you don't want every internal tick to
schedule a CD cycle. Use `NgZone.runOutsideAngular()` (still works) or, in
zoneless mode, simply don't touch any of Angular's notification sources:

```typescript
import { Component, NgZone, inject, ElementRef, viewChild } from '@angular/core';

@Component({
  selector: 'app-canvas',
  standalone: true,
  template: `<canvas #canvas width="800" height="600"></canvas>`,
})
export class CanvasComponent {
  canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private zone = inject(NgZone);

  ngAfterViewInit(): void {
    this.zone.runOutsideAngular(() => {
      const ctx = this.canvasRef().nativeElement.getContext('2d')!;
      const draw = () => {
        // 60 FPS animation — none of this triggers CD
        ctx.clearRect(0, 0, 800, 600);
        // ...render frame
        requestAnimationFrame(draw);
      };
      draw();
    });
  }
}
```

### Pattern 3 — When you DO need detectChanges (rare)

`detectChanges()` is the right tool exactly when you need synchronous DOM
updates before the next microtask — for example, before a measurement:

```typescript
@Component({ /* ... */ })
export class ResizeAwareComponent {
  private cdr = inject(ChangeDetectorRef);
  width = signal(0);

  measureAndAdjust(): void {
    // Force the DOM to update with the new layout NOW
    this.cdr.detectChanges();

    // Now we can safely measure
    const measured = this.host.nativeElement.offsetWidth;
    this.width.set(measured);
  }
}
```

This is rare. 95% of the time, `markForCheck()` or a signal write does the
job and lets the scheduler batch updates efficiently.

## Common mistakes

### Mistake 1 — Assuming all existing components will be OnPush after upgrading to v22

`ng update` adds `ChangeDetectionStrategy.Eager` to every existing component
that didn't have an explicit strategy set. Your old code keeps behaving
exactly as before; nothing breaks. But this also means **you don't
automatically get OnPush benefits** — you have to remove those Eager lines
deliberately, one by one, and verify each component works without eager
checking.

```typescript
// What ng update writes onto your old components:
@Component({
  selector: 'app-legacy',
  changeDetection: ChangeDetectionStrategy.Eager,   // ← added by migration
  template: `...`,
})

// To gain the v22 benefit, remove the line (one component at a time):
@Component({
  selector: 'app-modernized',
  // changeDetection removed — defaults to OnPush
  template: `...`,
})
```

The right strategy is to treat the migration-added `Eager` lines as a
**backlog**, not a conclusion. Pick one component at a time, remove the line,
verify it still works, and move on.

### Mistake 2 — Mutating reactive forms state without notifying CD in zoneless

This is the most common zoneless surprise. `FormGroup.setValue()`,
`patchValue()`, and `FormArray.push()` update form state and emit on
`valueChanges` — but they do **not** schedule CD by themselves:

```typescript
@Component({
  selector: 'app-form',
  standalone: true,
  template: `
    <input [formControl]="name">
    <p>Length: {{ name.value.length }}</p>   <!-- doesn't update in zoneless! -->
  `,
})
export class FormComponent {
  name = new FormControl('');

  reset() {
    this.name.setValue('');                  // form state changes
    // BUT: in zoneless, the template's "Length:" reading doesn't refresh
  }
}
```

**Two fixes**, in order of preference:

```typescript
// ✅ Option A — read form state via a signal
import { toSignal } from '@angular/core/rxjs-interop';

export class FormComponent {
  name = new FormControl('');
  nameValue = toSignal(this.name.valueChanges, { initialValue: '' });
}
```

```html
<!-- template uses the signal — Angular sees it and refreshes -->
<p>Length: {{ nameValue().length }}</p>
```

```typescript
// ✅ Option B — explicit markForCheck after the mutation
import { ChangeDetectorRef, inject } from '@angular/core';

export class FormComponent {
  name = new FormControl('');
  private cdr = inject(ChangeDetectorRef);

  reset() {
    this.name.setValue('');
    this.cdr.markForCheck();
  }
}
```

Long term, the right answer is Signal Forms (stable in v22), which removes
this whole class of problem.

### Mistake 3 — Calling detectChanges in a loop

`detectChanges()` runs CD synchronously, every time. Calling it inside a
loop means you run CD N times — and Angular cannot batch:

```typescript
// ❌ N change detection cycles — synchronous, blocking
items.forEach(item => {
  this.process(item);
  this.cdr.detectChanges();
});

// ✅ One CD cycle at the end of the synchronous batch
items.forEach(item => {
  this.process(item);
});
this.cdr.markForCheck();  // or just let the next scheduled tick handle it
```

`markForCheck()` is idempotent — calling it 1000 times is the same as calling
it once. Use it freely; reserve `detectChanges()` for the rare cases where
you genuinely need synchronous DOM updates before the next microtask.

### Mistake 4 — Object input mutation breaking OnPush

OnPush detects input changes by **reference identity**. Mutating a passed-in
object doesn't count:

```typescript
// Parent component
@Component({
  template: `<app-child [user]="user"></app-child>
             <button (click)="rename()">Rename</button>`,
})
class ParentComponent {
  user = { name: 'Alice', age: 30 };

  // ❌ Mutation — child won't see the change
  rename() {
    this.user.name = 'Bob';
  }

  // ✅ New reference — OnPush child sees the input change
  renameImmutable() {
    this.user = { ...this.user, name: 'Bob' };
  }
}
```

A signal solves this elegantly:

```typescript
class ParentComponent {
  user = signal({ name: 'Alice', age: 30 });
  rename() {
    this.user.update(u => ({ ...u, name: 'Bob' }));
  }
}
```

```html
<app-child [user]="user()"></app-child>
```

Reading `user()` in the template subscribes the parent's view to the signal;
the child's `[user]` input gets a new value; the OnPush check passes.

## How this evolved

> - **Angular 2–15 (2016–2022):** Zone.js was the default and effectively
>   required scheduler. `Default` strategy checked every component on every
>   tick. `OnPush` was opt-in, used by performance-conscious teams via
>   `async` pipe + immutable updates. The framework didn't know what
>   actually changed — Zone.js told it *something* had changed, and CD
>   re-evaluated every binding.
>
> - **Angular 16 (May 2023):** Signals introduced in developer preview. First
>   time Angular had a fine-grained reactivity primitive. CD didn't yet take
>   advantage of them; that came in later versions.
>
> - **Angular 17.1 (Jan 2024):** Internal change detection updates — signal
>   reads in templates began creating per-view reactive consumers, enabling
>   targeted view refreshes. The `ChangeDetectionScheduler` was introduced as
>   the unified notification entry point.
>
> - **Angular 18 (May 2024):** Zoneless shipped as **experimental**.
>   `provideExperimentalZonelessChangeDetection()` available. Hybrid scheduling
>   improvements: even in zone-based apps, signal writes and `markForCheck`
>   now reliably schedule CD regardless of zone context.
>
> - **Angular 19 (Nov 2024):** Zoneless API renamed to
>   `provideZonelessChangeDetection()` (removed the "experimental" prefix)
>   in developer preview.
>
> - **Angular 20.2 (Oct 2025):** Zoneless **stable**. SSR + zoneless
>   officially supported. Error handling improvements.
>
> - **Angular 21.2 (early 2026):** `ChangeDetectionStrategy.Default`
>   officially deprecated. `ChangeDetectionStrategy.Eager` introduced as the
>   replacement name, more accurately describing what the strategy does.
>
> - **Angular 22 (June 2026):** **OnPush is the default change detection
>   strategy.** Components without an explicit strategy are now OnPush. `ng
>   update` migrates existing components to explicit `Eager` to preserve
>   behavior. New apps are zoneless by default. The Angular team considers
>   the modern CD story complete: OnPush + signals + zoneless.

## See also

- [Signals](../reactivity/signals.md) — the foundational primitive driving
  modern CD
- [Signal Inputs](../reactivity/signal-inputs.md) — why `input()` doesn't
  need `markForCheck` plumbing
- [Lifecycle](./lifecycle.md) — how CD timing interacts with lifecycle hooks
- [Animations](./animations.md) — why OnPush + signals matters for animation
  triggers
- [Angular DevTools](./angular-devtools.md) — visualizing CD cycles in the
  Profiler tab
- [Official docs — Skipping component subtrees](https://angular.dev/best-practices/skipping-subtrees)
- [Official docs — Zoneless](https://angular.dev/guide/zoneless)
- [Official docs — ChangeDetectionStrategy API](https://angular.dev/api/core/ChangeDetectionStrategy)

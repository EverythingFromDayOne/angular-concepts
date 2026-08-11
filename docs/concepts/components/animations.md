---
roadmap_node: "animations"
title: "Animations"
file: "components/animations.md"
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

# Animations

> **Lead with this:** Angular's animation system is a state machine — you define
> named states and the transitions between them, and Angular handles the
> interpolation, timing, and cleanup automatically.

## What it is

Angular ships a dedicated animation DSL in `@angular/animations` that sits on
top of the browser's Web Animations API. Instead of writing CSS `@keyframes`
or manipulating `element.animate()` manually, you describe animations
declaratively inside `@Component` metadata using a small set of functions:
`trigger`, `state`, `transition`, `animate`, `style`, and a few orchestration
helpers.

The system is state-driven: a trigger watches a binding on a template element,
and when that binding's value changes, Angular looks up the matching transition
and plays it. This connects naturally to Angular's reactivity model — signals,
component state, and route changes can all drive animations.

`@angular/animations` is a separate package from `@angular/core`. It is
tree-shaken when you don't use it, and it must be explicitly provided in your
app configuration.

## How it works under the hood

Angular's animation system has three layers:

**1. The DSL layer.** The functions you write in `@Component` (`trigger`,
`state`, `transition`, etc.) are plain JavaScript function calls that return
metadata objects. At compile time, Angular's compiler extracts these metadata
objects from the `animations` array and attaches them to the component factory.

**2. The animation engine.** At runtime, `AnimationEngine` (inside
`@angular/animations/browser`) owns a registry of all active triggers across
the app. When change detection runs and Angular detects that a trigger binding
has changed value, it hands the old and new values to the engine. The engine
looks up the matching `transition()` rule, builds an animation plan, and
creates an `AnimationPlayer`.

**3. The player.** `AnimationPlayer` wraps the browser's
[Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API).
It calls `element.animate()` with the computed keyframes and timing options,
handles chaining for `sequence()` and parallelism for `group()`, and fires
lifecycle callbacks (`start`, `done`) that you can hook into from the template
or component class.

This layering means Angular animations work anywhere the Web Animations API is
available — which is all modern browsers — without polyfills.

**`:enter` and `:leave`** are aliases for the `void => *` and `* => void`
transitions respectively. Angular translates them during the build phase. When
an element enters the DOM (via `@if`, `@for`, `*ngIf`, `*ngFor`, or
`ViewContainerRef`), its state transitions from `void` to whatever the default
state is (`*`). When it leaves, the reverse happens — Angular waits for the
`:leave` animation to finish before actually removing the element from the DOM.

## Basic usage

### Setup — providing animations

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// NgModule approach (Angular 2–13)
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AppComponent } from './app.component';

@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    BrowserAnimationsModule, // required — adds the animation engine
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

```typescript
// Standalone approach (Angular 14+ — recommended)
import { bootstrapApplication } from '@angular/platform-browser';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { AppComponent } from './app.component';

bootstrapApplication(AppComponent, {
  providers: [
    provideAnimationsAsync(), // lazy-loads the animation engine — preferred
    // or: provideAnimations() — eager, synchronous, use if you animate on first paint
  ],
});
```

`provideAnimationsAsync()` (Angular 17+) defers loading the animation engine
until the first animation actually runs. For apps where animations are not on
the critical path, this reduces initial bundle cost.

### trigger, state, transition, animate

This is the core vocabulary. A `trigger` wraps one or more `state`s and
`transition`s. You bind it to a template element with `[@triggerName]`.

```typescript
import {
  Component, signal
} from '@angular/core';
import {
  trigger, state, style, transition, animate
} from '@angular/animations';

@Component({
  selector: 'app-toggle-box',
  standalone: true,
  template: `
    <button (click)="toggle()">
      {{ isOpen() ? 'Close' : 'Open' }}
    </button>

    <div [@expandCollapse]="isOpen() ? 'open' : 'closed'">
      <p>Content inside the animated panel.</p>
    </div>
  `,
  styles: [`
    div { overflow: hidden; background: #f0f4ff; padding: 0 16px; }
  `],
  animations: [
    trigger('expandCollapse', [

      // Named states — define the styles each state should have
      state('open', style({
        height: '*',      // '*' means "natural height" — computed at runtime
        opacity: 1,
        paddingTop: '16px',
        paddingBottom: '16px',
      })),

      state('closed', style({
        height: '0',
        opacity: 0,
        paddingTop: '0',
        paddingBottom: '0',
      })),

      // Transitions — animate between states in both directions
      transition('open <=> closed', [
        animate('300ms ease-in-out'),
      ]),
    ]),
  ],
})
export class ToggleBoxComponent {
  isOpen = signal(false);
  toggle() { this.isOpen.update(v => !v); }
}
```

`open <=> closed` is shorthand for both `open => closed` and `closed => open`.
You can write one-directional transitions if the enter and leave should animate
differently.

### :enter and :leave — animating elements entering and leaving the DOM

```typescript
import { Component, signal } from '@angular/core';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-notification',
  standalone: true,
  template: `
    @if (visible()) {
      <div class="toast" [@fadeSlide]>
        {{ message() }}
      </div>
    }

    <button (click)="show()">Show notification</button>
  `,
  styles: [`
    .toast {
      position: fixed; bottom: 24px; right: 24px;
      padding: 12px 20px; background: #333; color: white;
      border-radius: 8px;
    }
  `],
  animations: [
    trigger('fadeSlide', [
      // Element entering the DOM
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(16px)' }), // start here
        animate('200ms ease-out',
          style({ opacity: 1, transform: 'translateY(0)' })), // end here
      ]),
      // Element leaving the DOM — Angular waits for this to finish
      transition(':leave', [
        animate('150ms ease-in',
          style({ opacity: 0, transform: 'translateY(8px)' })),
      ]),
    ]),
  ],
})
export class NotificationComponent {
  visible = signal(false);
  message = signal('');

  show() {
    this.message.set('Saved successfully!');
    this.visible.set(true);
    setTimeout(() => this.visible.set(false), 3000);
  }
}
```

### keyframes — multi-step animations

`keyframes()` gives you full control over the animation timeline, similar to
CSS `@keyframes`:

```typescript
import { trigger, transition, animate, keyframes, style } from '@angular/animations';

trigger('shake', [
  transition(':enter', [
    animate('500ms', keyframes([
      style({ transform: 'translateX(0)',    offset: 0    }),
      style({ transform: 'translateX(-8px)', offset: 0.2  }),
      style({ transform: 'translateX(8px)',  offset: 0.4  }),
      style({ transform: 'translateX(-6px)', offset: 0.6  }),
      style({ transform: 'translateX(6px)',  offset: 0.8  }),
      style({ transform: 'translateX(0)',    offset: 1    }),
    ])),
  ]),
])
```

### stagger — list entry animations

`stagger()` animates items in sequence with a delay between each one, giving
you the "list fans in" effect:

```typescript
import {
  trigger, transition, style, animate,
  query, stagger
} from '@angular/animations';

@Component({
  selector: 'app-result-list',
  standalone: true,
  template: `
    <ul [@listAnimation]="items().length">
      @for (item of items(); track item.id) {
        <li>{{ item.name }}</li>
      }
    </ul>
  `,
  animations: [
    trigger('listAnimation', [
      transition('* => *', [   // fires whenever the list length changes
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(-10px)' }),
          stagger(60, [         // 60ms delay between each item
            animate('300ms ease-out',
              style({ opacity: 1, transform: 'translateY(0)' })),
          ]),
        ], { optional: true }), // optional: true — don't error if list is empty
      ]),
    ]),
  ],
})
export class ResultListComponent {
  items = signal<{ id: number; name: string }[]>([]);
}
```

The trigger is bound to `items().length` — when the list changes, the
transition fires, `query(':enter')` selects the newly added DOM elements, and
`stagger` staggers their entrance.

## Real-world patterns

### Pattern 1 — Route transition animations

Page transitions are the most impactful animation in most apps. Angular's
router doesn't animate by default, but you can add it by binding a trigger to
the `RouterOutlet`:

```typescript
// app.component.ts
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { trigger, transition, style, animate, query } from '@angular/animations';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <main [@routeTransition]="getRouteKey(outlet)">
      <router-outlet #outlet="outlet" />
    </main>
  `,
  animations: [
    trigger('routeTransition', [
      transition('* <=> *', [
        // Animate the outgoing page out
        query(':leave', [
          style({ position: 'absolute', width: '100%' }),
          animate('200ms ease-in', style({ opacity: 0 })),
        ], { optional: true }),
        // Animate the incoming page in
        query(':enter', [
          style({ opacity: 0 }),
          animate('200ms ease-out', style({ opacity: 1 })),
        ], { optional: true }),
      ]),
    ]),
  ],
})
export class AppComponent {
  getRouteKey(outlet: RouterOutlet): string {
    return outlet?.activatedRouteData?.['animation'] ?? '';
  }
}
```

```typescript
// routes — give each route an animation key
export const routes: Routes = [
  {
    path: 'home',
    component: HomeComponent,
    data: { animation: 'home' },
  },
  {
    path: 'about',
    component: AboutComponent,
    data: { animation: 'about' },
  },
];
```

### Pattern 2 — Listening to animation lifecycle events

Sometimes you need to know when an animation starts or finishes — to disable
a button during an animation, or to remove an element after it fades out:

```typescript
@Component({
  selector: 'app-card',
  standalone: true,
  template: `
    <div
      [@cardState]="state()"
      (@cardState.start)="onAnimationStart($event)"
      (@cardState.done)="onAnimationDone($event)"
    >
      <ng-content />
    </div>
  `,
  animations: [
    trigger('cardState', [
      transition(':leave', [
        animate('300ms ease-in', style({ opacity: 0, transform: 'scale(0.95)' })),
      ]),
    ]),
  ],
})
export class CardComponent {
  state = signal('visible');
  isAnimating = signal(false);

  onAnimationStart(event: AnimationEvent): void {
    this.isAnimating.set(true);
  }

  onAnimationDone(event: AnimationEvent): void {
    this.isAnimating.set(false);
  }
}
```

## Common mistakes

### Mistake 1 — Forgetting provideAnimations / BrowserAnimationsModule

Animations silently do nothing if you forget to set up the provider:

```typescript
// ❌ Missing animations setup — animations silently do nothing
bootstrapApplication(AppComponent, {
  providers: [
    // provideAnimationsAsync() not provided — no error, just no animations
  ],
});

// ✅ Correct
bootstrapApplication(AppComponent, {
  providers: [
    provideAnimationsAsync(),
  ],
});
```

If you want to verify this quickly, import `NoopAnimationsModule` /
`provideNoopAnimations()` intentionally in tests — it disables animations
without errors and speeds up test execution.

### Mistake 2 — Animating height from 0 to auto without using '*'

CSS cannot animate `height: auto` directly. Angular's `'*'` value solves this —
it computes the element's natural height at runtime:

```typescript
// ❌ CSS can't interpolate between 0 and auto — animation won't work
state('open',   style({ height: 'auto' })),
state('closed', style({ height: '0' })),

// ✅ Use '*' — Angular measures the actual height and animates to/from it
state('open',   style({ height: '*' })),
state('closed', style({ height: '0' })),
```

### Mistake 3 — Missing { optional: true } on query() for empty lists

`query()` throws an error if it finds no matching elements. For `:enter` and
`:leave` on lists that might be empty, always add `{ optional: true }`:

```typescript
// ❌ Throws error when list has no items
query(':enter', [
  stagger(60, [animate('300ms', style({ opacity: 1 }))]),
]),

// ✅ Safe for empty lists
query(':enter', [
  stagger(60, [animate('300ms', style({ opacity: 1 }))]),
], { optional: true }),
```

### Mistake 4 — Triggering animations from inside OnPush components

With `OnPush` change detection, Angular won't check a component unless its
inputs change, a signal it reads changes, or an event fires within it. If your
animation trigger is driven by a service value that didn't come through an
input or signal, the trigger change might not be detected:

```typescript
// ❌ Service state change may not trigger CD in OnPush — animation won't fire
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [trigger('fade', [...])],
  template: `<div [@fade]="notificationService.isVisible">`,
})

// ✅ Use a signal — OnPush automatically tracks signal reads
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [trigger('fade', [...])],
  template: `<div [@fade]="isVisible()">`,
})
export class MyComponent {
  isVisible = inject(NotificationService).isVisible; // signal
}
```

## How this evolved

> - **Angular 2 (2016):** Animation system launched with the full `trigger`,
>   `state`, `transition`, `animate`, `style` vocabulary. Required
>   `BrowserAnimationsModule`. Already built on the Web Animations API.
>
> - **Angular 4 (2017):** `query()`, `stagger()`, `group()`, `sequence()`,
>   and `animateChild()` added — making complex coordinated and list animations
>   possible without custom code.
>
> - **Angular 6 (2018):** `AnimationBuilder` service introduced — lets you
>   create and play animations imperatively in component code, outside the
>   `animations` metadata array.
>
> - **Angular 17 (2023):** `provideAnimationsAsync()` introduced — lazy-loads
>   the animation engine rather than bundling it eagerly. `:enter`/`:leave`
>   animations updated to work with the new `@if`/`@for` control flow blocks.
>
> - **Angular 22 (now):** The animation API is stable and unchanged in recent
>   versions. The team's effort has focused on signals and zoneless — animations
>   are fully compatible with both. The recommendation for new projects is
>   `provideAnimationsAsync()` over `BrowserAnimationsModule`, and signal-driven
>   trigger bindings over manual `ChangeDetectorRef` calls in OnPush components.

## See also

- [Lifecycle](./lifecycle.md) — `ngAfterViewInit` timing relative to when
  `:enter` animations can safely run
- [Change Detection](./change-detection.md) — why `OnPush` requires signals
  or explicit marks to trigger animation state changes
- [Control Flow](./templates/control-flow.md) — `@if`/`@for` and how they
  connect to `:enter`/`:leave` animations
- [Official docs — Animations](https://angular.dev/guide/animations)
- [Official docs — Route transitions](https://angular.dev/guide/animations/route-animations)

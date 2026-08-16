---
recipe_id: "multi-step-wizards"
description: "A wizard's state has to outlive its step components, which is why the form model belongs in a subtree-scoped service"
primary_concept: "forms/reactive-forms"
related_concepts: ["reactivity/signals", "routing/routing", "components/components"]
demo_repo: null
angular_baseline: "22.1.1"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Multi-Step Wizards: State That Survives the Back Button

> **What you'll build:** a working multi-step wizard architecture
> that handles the four things wizards always get wrong — data
> preservation across steps, back-button behavior, conditional
> branching (step 3 skipped if step 2 answered a certain way), and
> resume-where-you-left-off after the user closes the browser and
> comes back. Subtree-scoped state service; per-step forms via
> `FormArray`-of-`FormGroups`; navigation guards for
> "you have unsaved changes"; step-completion tracking that
> prevents jumping ahead.
>
> **Concepts you'll touch:** [Reactive Forms](../../concepts/forms/reactive-forms.md), [Signals](../../concepts/reactivity/signals.md), [Routing](../../concepts/routing/routing.md), Components
>
> **Time:** ~25 minutes to read; ~4 hours to implement a real
> wizard including persistence and edge-case testing.

---

## The scenario

A B2B SaaS onboarding wizard: five steps to configure a new project. Step 1 collects the project name and team. Step 2 asks about billing (skipped if the team is on the enterprise plan). Step 3 picks integrations. Step 4 imports data. Step 5 confirms and creates the project.

You build it. Users start using it. Support tickets:

- **"I filled out steps 1-3, hit back, and step 3 was blank when I returned."** Component destruction wiped the form state.
- **"I clicked step 5 directly in the sidebar and it let me submit an empty project."** No enforcement of step completion order.
- **"I closed my browser after step 4 to check something. When I came back, I had to start over."** No persistence across sessions.
- **"I upgraded to enterprise mid-wizard and step 2 still shows billing questions."** Conditional branching didn't re-evaluate.
- **"I clicked away accidentally and lost all my progress."** No "unsaved changes" guard.
- **"The submit button doesn't work if I skipped a step, but doesn't tell me which one is missing."** No completion feedback.

Every one of these is a specific design mistake. The recipe walks through the architecture that avoids them — a subtree-scoped state service that owns wizard data, per-step routes with completion guards, and localStorage persistence with a proper resume flow.

---

## The three architectural decisions

Before code, the choices that determine everything else:

**1. Where does wizard state live?**

- ❌ In each step component's local state → wiped when component unmounts
- ❌ In `providedIn: 'root'` service → leaks between different wizard instances, persists after wizard closes
- ✅ **Subtree-scoped service** provided on the wizard shell component → lives for the wizard's lifetime, dies when wizard closes

**2. How is navigation between steps handled?**

- ❌ Show/hide via conditional templates → the URL doesn't change, no back-button, no deep linking
- ❌ Manual "current step" signal in the shell without routing → same problem, plus refresh loses position
- ✅ **Routes per step**, with a shared parent route that provides the state service → back button works naturally, URLs are shareable, refresh keeps you on the current step

**3. How is data persisted across page reloads?**

- ❌ Skip it, hope the user doesn't close the tab → they will
- ❌ Save on every field change → too chatty; localStorage is synchronous
- ✅ **Save on step transitions** to localStorage → checkpoints; enough to resume

These three decisions are correlated. Subtree-scoped service naturally works with routes-per-step. Both integrate with localStorage checkpointing at step-transition time.

---

## The wizard state service

The heart of the architecture. One service, subtree-scoped, owning all wizard state.

```typescript
// File: onboarding/wizard-state.service.ts
import { Injectable, computed, effect, inject, signal } from '@angular/core';

export interface WizardStep {
  id: 'project' | 'billing' | 'integrations' | 'import' | 'confirm';
  label: string;
  completed: boolean;
  optional?: boolean;
  visible?: boolean;
}

export interface WizardData {
  project: { name: string; team: string; plan: 'basic' | 'pro' | 'enterprise' } | null;
  billing: { cardLast4: string; billingEmail: string } | null;
  integrations: { slack: boolean; github: boolean; jira: boolean } | null;
  importSource: { type: 'csv' | 'api' | 'none'; url?: string } | null;
}

const EMPTY_DATA: WizardData = {
  project: null,
  billing: null,
  integrations: null,
  importSource: null,
};

const STORAGE_KEY = 'onboarding-wizard-state';

@Injectable()  // NOT providedIn: 'root' — provided per wizard instance
export class WizardStateService {
  private readonly _data = signal<WizardData>(EMPTY_DATA);
  private readonly _currentStepIndex = signal(0);

  readonly data = this._data.asReadonly();
  readonly currentStepIndex = this._currentStepIndex.asReadonly();

  // Steps definition — computed because visibility depends on data
  readonly steps = computed<WizardStep[]>(() => {
    const data = this._data();
    const isEnterprise = data.project?.plan === 'enterprise';

    return [
      { id: 'project', label: 'Project', completed: !!data.project },
      {
        id: 'billing',
        label: 'Billing',
        completed: !!data.billing,
        // Enterprise plans skip billing (invoicing handled elsewhere)
        visible: !isEnterprise,
      },
      { id: 'integrations', label: 'Integrations', completed: !!data.integrations, optional: true },
      { id: 'import', label: 'Import Data', completed: !!data.importSource, optional: true },
      { id: 'confirm', label: 'Confirm', completed: false },
    ];
  });

  readonly visibleSteps = computed(() =>
    this.steps().filter(s => s.visible !== false),
  );

  readonly currentStep = computed(() =>
    this.visibleSteps()[this._currentStepIndex()],
  );

  readonly progress = computed(() => {
    const steps = this.visibleSteps();
    const completed = steps.filter(s => s.completed).length;
    return {
      current: this._currentStepIndex() + 1,
      total: steps.length,
      completed,
      percentage: Math.round((completed / steps.length) * 100),
    };
  });

  readonly canProceed = computed(() => {
    const step = this.currentStep();
    return step?.completed || step?.optional;
  });

  readonly canSubmit = computed(() => {
    const required = this.visibleSteps().filter(s => !s.optional && s.id !== 'confirm');
    return required.every(s => s.completed);
  });

  constructor() {
    this.restoreFromStorage();

    // Persist to localStorage on every state change
    effect(() => {
      const snapshot = {
        data: this._data(),
        currentStepIndex: this._currentStepIndex(),
        timestamp: Date.now(),
      };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
      } catch {
        // Storage may be unavailable (private mode, quota); in-memory only is fine
      }
    });
  }

  updateStep<K extends keyof WizardData>(step: K, value: WizardData[K]): void {
    this._data.update(current => ({ ...current, [step]: value }));
  }

  goToStep(index: number): boolean {
    const steps = this.visibleSteps();
    if (index < 0 || index >= steps.length) return false;

    // Prevent jumping past incomplete required steps
    for (let i = 0; i < index; i++) {
      const step = steps[i];
      if (!step.completed && !step.optional) return false;
    }

    this._currentStepIndex.set(index);
    return true;
  }

  next(): boolean {
    return this.goToStep(this._currentStepIndex() + 1);
  }

  previous(): boolean {
    return this.goToStep(this._currentStepIndex() - 1);
  }

  reset(): void {
    this._data.set(EMPTY_DATA);
    this._currentStepIndex.set(0);
    localStorage.removeItem(STORAGE_KEY);
  }

  hasStoredProgress(): boolean {
    return localStorage.getItem(STORAGE_KEY) !== null;
  }

  private restoreFromStorage(): void {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return;

      const snapshot = JSON.parse(stored) as {
        data: WizardData;
        currentStepIndex: number;
        timestamp: number;
      };

      // Expire snapshots older than 7 days
      const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
      if (Date.now() - snapshot.timestamp > MAX_AGE_MS) {
        localStorage.removeItem(STORAGE_KEY);
        return;
      }

      this._data.set(snapshot.data);
      this._currentStepIndex.set(snapshot.currentStepIndex);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
}
```

**Seven things doing the work:**

- **`@Injectable()` without `providedIn`** — the service is provided per-wizard-instance, not globally. Registered on the wizard shell component's `providers` array; created when the wizard mounts, destroyed when it unmounts.
- **`_data` signal + `data.asReadonly()`** — components read state reactively; only the service can mutate via `updateStep()`.
- **`steps` computed with visibility rules** — steps that shouldn't apply (e.g., billing for enterprise plans) are filtered out via `visible: false`. The `visibleSteps` computed handles the filtering; the rest of the code sees only the applicable ones.
- **`canProceed` and `canSubmit` computed signals** — UI reads them directly; buttons enable/disable reactively. `canProceed` handles per-step forward navigation; `canSubmit` handles the final submission.
- **`goToStep` with step-order enforcement** — jumping to step 4 before step 2 is completed is rejected. Users can't circumvent the flow by clicking directly on a sidebar step number.
- **`effect(() => localStorage.setItem(...))`** — auto-persist on every state change. Not debounced because localStorage writes are fast and steps don't change hundreds of times per second (compare to typing in a search box, which would need debounce).
- **7-day expiry on restored state** — a user who abandoned the wizard 3 months ago probably doesn't want their old state auto-restored. Bounded staleness prevents confusing "why is this data pre-filled?" moments.

---

## The route structure

Routes per step, with a parent route that provides the wizard shell:

```typescript
// File: onboarding/onboarding.routes.ts
import { Routes } from '@angular/router';
import { WizardStateService } from './wizard-state.service';
import { OnboardingShellComponent } from './onboarding-shell.component';
import { stepGuard } from './step.guard';

export const onboardingRoutes: Routes = [
  {
    path: '',
    component: OnboardingShellComponent,
    providers: [WizardStateService],  // ← subtree-scoped state
    children: [
      { path: '', redirectTo: 'project', pathMatch: 'full' },
      {
        path: 'project',
        loadComponent: () => import('./steps/project-step.component')
          .then(c => c.ProjectStepComponent),
      },
      {
        path: 'billing',
        loadComponent: () => import('./steps/billing-step.component')
          .then(c => c.BillingStepComponent),
        canActivate: [stepGuard('billing')],  // enforces order
      },
      {
        path: 'integrations',
        loadComponent: () => import('./steps/integrations-step.component')
          .then(c => c.IntegrationsStepComponent),
        canActivate: [stepGuard('integrations')],
      },
      {
        path: 'import',
        loadComponent: () => import('./steps/import-step.component')
          .then(c => c.ImportStepComponent),
        canActivate: [stepGuard('import')],
      },
      {
        path: 'confirm',
        loadComponent: () => import('./steps/confirm-step.component')
          .then(c => c.ConfirmStepComponent),
        canActivate: [stepGuard('confirm')],
      },
    ],
  },
];
```

**Three things worth absorbing:**

- **`providers: [WizardStateService]` on the parent route** — the service is instantiated when the parent activates; destroyed when the user navigates away. Child routes inject the same instance.
- **Lazy-loaded step components** — each step's code is a separate chunk. Users who abandon at step 2 never download step 5's code. Composes with the [bundle-splitting recipe](../performance/bundle-splitting-strategies.md).
- **`canActivate: [stepGuard(...)]`** — the guard checks whether previous steps are completed before allowing navigation to a later step.

### The step guard

```typescript
// File: onboarding/step.guard.ts
import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { WizardStateService } from './wizard-state.service';

export function stepGuard(stepId: string): CanActivateFn {
  return () => {
    const wizardState = inject(WizardStateService);
    const router = inject(Router);

    const steps = wizardState.visibleSteps();
    const targetIndex = steps.findIndex(s => s.id === stepId);
    if (targetIndex === -1) {
      router.navigate(['/onboarding']);
      return false;
    }

    // Check that all previous required steps are completed
    for (let i = 0; i < targetIndex; i++) {
      const step = steps[i];
      if (!step.completed && !step.optional) {
        // Redirect to the first incomplete required step
        router.navigate(['/onboarding', step.id]);
        return false;
      }
    }

    return true;
  };
}
```

Functional guard from the [routing recipe conventions](../auth/app-initialization.md#the-companion--authguard-with-canactivatefn). Users who deep-link to `/onboarding/confirm` without completing prior steps get redirected to the first incomplete step.

---

## A step component

Each step has its own form and its own component. The step reads/writes wizard state through the shared service:

```typescript
// File: onboarding/steps/project-step.component.ts
import { Component, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { WizardStateService } from '../wizard-state.service';

@Component({
  selector: 'app-project-step',
  imports: [ReactiveFormsModule],
  template: `
    <h2>Project Details</h2>

    <form [formGroup]="form" (submit)="onNext()">
      <label>
        Project name
        <input formControlName="name" />
      </label>

      <label>
        Team
        <select formControlName="team">
          <option value="">Select a team</option>
          @for (team of availableTeams(); track team.id) {
            <option [value]="team.id">{{ team.name }}</option>
          }
        </select>
      </label>

      <label>
        Plan
        <select formControlName="plan">
          <option value="basic">Basic</option>
          <option value="pro">Professional</option>
          <option value="enterprise">Enterprise</option>
        </select>
      </label>

      <div class="actions">
        <button type="submit" [disabled]="form.invalid">Continue →</button>
      </div>
    </form>
  `,
})
export class ProjectStepComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly wizardState = inject(WizardStateService);
  private readonly router = inject(Router);

  readonly availableTeams = signal([
    { id: 't1', name: 'Engineering' },
    { id: 't2', name: 'Design' },
  ]);

  readonly form = this.fb.group({
    name: this.fb.control('', [Validators.required, Validators.minLength(3)]),
    team: this.fb.control('', Validators.required),
    plan: this.fb.control<'basic' | 'pro' | 'enterprise'>('basic', Validators.required),
  });

  constructor() {
    // Restore existing data if the user is returning to this step
    const existing = this.wizardState.data().project;
    if (existing) {
      this.form.patchValue(existing);
    }
  }

  onNext(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    this.wizardState.updateStep('project', value);
    this.wizardState.next();

    // Navigate to the next step's route
    const next = this.wizardState.currentStep();
    if (next) {
      this.router.navigate(['/onboarding', next.id]);
    }
  }
}
```

**Three patterns worth absorbing:**

- **Constructor restoration** — `this.form.patchValue(existing)` on component mount. Users returning to this step see their previous input, not an empty form. This is the "back button preserves data" requirement in code.
- **`markAllAsTouched` on invalid submit** — reveals validation errors immediately, since the user just tried to submit. Without this, first-time visitors don't see red error borders because they never touched the fields.
- **State updated in the shared service, then navigate** — the step component doesn't navigate on its own via `next()` internally; it saves data first, then routes to the URL corresponding to the next step. Two concerns, two lines.

### The wizard shell

Provides the layout — stepper indicator, current step outlet, action buttons:

```typescript
// File: onboarding/onboarding-shell.component.ts
import { Component, inject } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { WizardStateService } from './wizard-state.service';

@Component({
  selector: 'app-onboarding-shell',
  imports: [RouterOutlet],
  template: `
    <div class="wizard">
      <aside class="stepper">
        <h3>Onboarding</h3>
        <ol>
          @for (step of wizard.visibleSteps(); track step.id; let i = $index) {
            <li
              [class.active]="wizard.currentStep()?.id === step.id"
              [class.completed]="step.completed"
              (click)="jumpTo(i, step)"
            >
              <span class="marker">{{ i + 1 }}</span>
              <span class="label">{{ step.label }}</span>
              @if (step.optional) { <em>(optional)</em> }
            </li>
          }
        </ol>

        <div class="progress">
          {{ wizard.progress().current }} of {{ wizard.progress().total }} —
          {{ wizard.progress().percentage }}% complete
        </div>
      </aside>

      <main class="content">
        <router-outlet />
      </main>
    </div>
  `,
})
export class OnboardingShellComponent {
  protected readonly wizard = inject(WizardStateService);
  private readonly router = inject(Router);

  jumpTo(index: number, step: WizardStep): void {
    // Only allow jumping if the step is reachable (completed or previous is completed)
    if (this.wizard.goToStep(index)) {
      this.router.navigate(['/onboarding', step.id]);
    }
  }
}
```

Signal reads in the template (`wizard.visibleSteps()`, `wizard.progress()`, `wizard.currentStep()`) automatically update as state changes. No subscriptions, no async pipes.

---

## The resume flow

When a user reopens the wizard after a break, prompt to resume:

```typescript
// File: onboarding/entry.component.ts
@Component({
  selector: 'app-onboarding-entry',
  template: `
    @if (hasProgress()) {
      <div class="resume-card">
        <h3>You have unfinished onboarding</h3>
        <p>Would you like to continue where you left off?</p>
        <button (click)="resume()">Continue</button>
        <button (click)="startFresh()">Start over</button>
      </div>
    } @else {
      <button (click)="start()">Start onboarding</button>
    }
  `,
})
export class OnboardingEntryComponent {
  private readonly wizard = inject(WizardStateService);
  private readonly router = inject(Router);

  readonly hasProgress = signal(this.wizard.hasStoredProgress());

  resume(): void {
    // Restore already happened in the service's constructor;
    // just navigate to the current step
    const step = this.wizard.currentStep();
    this.router.navigate(['/onboarding', step?.id ?? 'project']);
  }

  startFresh(): void {
    this.wizard.reset();
    this.router.navigate(['/onboarding', 'project']);
    this.hasProgress.set(false);
  }

  start(): void {
    this.router.navigate(['/onboarding', 'project']);
  }
}
```

The user sees "You have unfinished onboarding — continue or start over?" — respectful and clear about the state.

**Two things worth absorbing:**

- **The signal `hasProgress` is initialized once** at construction. Updating it after `startFresh` requires the explicit `set(false)`. Alternatively, use a computed reading from a service signal for reactive updates.
- **The service's constructor already restored the state** — `resume()` doesn't need to do anything special; navigation is enough. The state is ready to render.

---

## Confirm-on-leave with `CanDeactivate`

If the user has unsaved changes on the current step and tries to navigate away, ask first:

```typescript
// File: onboarding/leave.guard.ts
import { CanDeactivateFn } from '@angular/router';

export interface HasPendingChanges {
  hasPendingChanges(): boolean;
}

export const leaveGuard: CanDeactivateFn<HasPendingChanges> = (component) => {
  if (component.hasPendingChanges()) {
    return confirm('You have unsaved changes on this step. Leave anyway?');
  }
  return true;
};
```

Step components implement the interface:

```typescript
@Component({ /* … */ })
export class ProjectStepComponent implements HasPendingChanges {
  // …existing code…

  hasPendingChanges(): boolean {
    return this.form.dirty && !this.savedSinceDirty;
  }

  private savedSinceDirty = false;

  onNext(): void {
    // …existing submit logic…
    this.savedSinceDirty = true;
  }
}
```

Register the guard on the step routes:

```typescript
{
  path: 'project',
  loadComponent: () => import('./steps/project-step.component').then(c => c.ProjectStepComponent),
  canDeactivate: [leaveGuard],
},
```

Note: `confirm()` (browser dialog) is used here for brevity. A production app should use a custom modal — better UX, cross-browser consistent, matches the app's design system. The recipe stays focused on the guard mechanism.

---

## Conditional / branching steps

The `visible` flag in the step definition is how conditional steps work. As data changes, the computed `steps` signal re-runs; steps become visible or hidden.

**Concrete example — enterprise plans skip billing**:

```typescript
readonly steps = computed<WizardStep[]>(() => {
  const data = this._data();
  const isEnterprise = data.project?.plan === 'enterprise';

  return [
    { id: 'project', label: 'Project', completed: !!data.project },
    {
      id: 'billing',
      label: 'Billing',
      completed: !!data.billing,
      visible: !isEnterprise,   // ← conditional
    },
    { id: 'integrations', label: 'Integrations', completed: !!data.integrations, optional: true },
    { id: 'import', label: 'Import Data', completed: !!data.importSource, optional: true },
    { id: 'confirm', label: 'Confirm', completed: false },
  ];
});
```

If the user starts on the basic plan, fills billing, then goes back to step 1 and upgrades to enterprise, the billing data is preserved in state but the step disappears from the stepper. If they downgrade back to basic, the step re-appears with the previous data intact.

**Two subtleties:**

- **Preserved data**: hiding a step doesn't clear its data. If the user re-enters visibility, their previous input is still there. This is usually what you want — users who oscillate between choices don't lose their work.
- **The `currentStepIndex` may point to a hidden step**: if the user is on step 2 (billing) and upgrades to enterprise, the billing step disappears and the index would point past the current visible step count. Handle this in the effect that watches for step-visibility changes:

```typescript
constructor() {
  this.restoreFromStorage();

  // If the current step becomes hidden, move forward to the next visible one
  effect(() => {
    const visible = this.visibleSteps();
    const currentIdx = this._currentStepIndex();
    if (currentIdx >= visible.length) {
      this._currentStepIndex.set(Math.max(0, visible.length - 1));
    }
  });
  
  // ...localStorage persistence effect...
}
```

The effect runs whenever step visibility changes. If the current index is out of bounds, snap to the last visible step.

---

## Trade-offs and common pitfalls

**Use this wizard architecture when:**

- Wizards have 3+ steps (below that, a single form with sections is simpler)
- Users need to return to a step and see their input intact
- Some steps are conditional based on earlier answers
- The wizard is important enough that users abandoning mid-flow is a real cost (onboarding, checkout, complex configuration)

**Skip when:**

- The "wizard" is really a single form split visually with `@if` — no persistence, no back button needed
- The user's data doesn't need to persist across sessions (kiosk-style flows)
- The workflow has < 3 steps and step order doesn't matter

### Common pitfalls

- **`providedIn: 'root'` for wizard state.** Leaks between wizard instances (open two wizards in different tabs), persists after the wizard closes (state pollution for the next wizard-open). Always subtree-scoped.
- **Storing form controls in the wizard service.** Tempting because "everything is here," but form controls are UI-tied and don't serialize to localStorage cleanly. Store the plain data; each step's component owns its own form and hydrates from the data on mount.
- **Not clearing state on successful submit.** The wizard completes; localStorage still has the stale data; the next time the user opens the wizard, they see "You have unfinished onboarding." Call `wizard.reset()` after successful submission.
- **Race between navigation and state update.** `wizardState.next(); router.navigate(...)` — if next fails, the router still navigates. Do the state update first; check for success; only navigate if it worked.
- **Skipping the step-order guard.** Users deep-linking to `/onboarding/confirm` shouldn't work without prior steps. The `stepGuard` is essential.
- **Storing sensitive data in localStorage.** Payment info, SSNs, passwords — never. If the wizard collects sensitive fields, either transmit immediately (no local persistence) or accept that the resume-across-sessions feature doesn't apply to those specific fields.
- **7-day expiry too long or too short.** A month is often too long (users forget context); a day is often too short (weekend workflow). Tune based on domain; 3-7 days is typical.
- **`effect()` writing localStorage without try/catch.** Some browsers throw when localStorage is full or in privacy mode. Wrap the write in try/catch — the wizard should still work in-memory even if persistence fails.
- **Confirm-on-leave that fires for programmatic navigation too.** `router.navigate` for going to the next step should not trigger the confirm dialog. Set `savedSinceDirty = true` (or clear `form.dirty`) before navigating.
- **Not showing progress in the stepper.** The sidebar showing "Step 3 of 5" is the load-bearing UX cue that this is a wizard, not a series of unrelated pages. Progress signals are cheap; use them prominently.
- **Conditional steps that reset previous data.** Hiding a step should not clear its data. Users who oscillate should not lose work.

---

## See also

- [Dynamic Forms](./dynamic-forms.md) — form shape variations within a step (conditional sub-forms, FormArray)
- [Optimistic Updates](./optimistic-updates.md) — for wizards that save intermediate state to the server (save on step transition, retry on failure)
- [Component Communication](../components/component-communication.md) — the subtree-scoped service pattern (Pattern 4)
- [App Initialization](../auth/app-initialization.md) — the `CanActivateFn` pattern used by `stepGuard`
- [Routing](../../concepts/routing/routing.md) — `provideRouter`, nested routes, guards
- [Signals](../../concepts/reactivity/signals.md) — the state primitive

## References

- [`CanDeactivateFn` (angular.dev)](https://angular.dev/api/router/CanDeactivateFn) — the guard for confirm-on-leave
- [Route providers (angular.dev)](https://angular.dev/guide/routing/router-reference#route-providers) — the subtree-provider pattern
- [`Storage` API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Storage) — localStorage for persistence
- [Nielsen Norman Group — Wizard Design Patterns](https://www.nngroup.com/articles/wizards/) — UX principles for multi-step flows

## Demo source

Synthesized from common production wizard patterns rather than a single demo file. The subtree-scoped service + routes-per-step + step-order guard architecture is the structure most teams converge on after their first wizard. The seven-day localStorage expiry, the "resume where you left off" flow, and the conditional visibility with preserved-on-hide data are the patterns that separate polished wizards from frustrating ones. All code is original.
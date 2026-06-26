---
roadmap_node: "dependency-injection"
title: "Dependency Injection"
file: "dependency-injection/dependency-injection.md"
source_days: [15, 16, 48]
original_authors: ["Tiep Phan", "Hien Pham"]
status:
  translated: true
  upgraded: true
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Dependency Injection

> **⚡ What changed since the original**
>
> This article was first written for Angular 9 (2020). The DI **mental model** — injectors, providers, dependencies, hierarchical lookup, tree-shakable services, `forwardRef`, the four provider shapes — is unchanged in Angular v22. What changed is **how you express it in code**:
>
> - **`inject()` replaces constructor parameters** as the idiomatic way to grab a dependency. Constructor injection still compiles, but `inject()` works in places constructors can't reach: functional route guards, functional HTTP interceptors, resolvers, `effect()` callbacks, factory providers, and anywhere inside `runInInjectionContext()`.
> - **Standalone components are the default** — `@NgModule` is no longer needed for most apps. Providers live on `bootstrapApplication()`, on components, on routes, or in environment injectors.
> - **Signal inputs (`input()`) and outputs (`output()`)** replace `@Input()` / `@Output()` decorators.
> - **Built-in control flow (`@if`, `@for`, `@switch`)** replaces `*ngIf` / `*ngFor` in templates.
> - **Signal queries (`viewChild()`, `contentChildren()`)** replace `@ViewChild()` / `@ContentChildren()` decorators.
> - **`TestBed.inject()`** replaces the removed `TestBed.get()`, and **`await fixture.whenStable()`** is preferred over synchronous `fixture.detectChanges()` for assertions.
>
> Every Angular 9 example below is preserved with its `<!-- legacy -->` marker, followed by a v22 equivalent so you can see how the same DI concept maps to today's syntax. The article closes with a mechanism reflection digging into **why** `inject()` and the injection context exist at all — that's the most consequential change since Angular 9.
>
> **See also**: [Modern DI with `inject()`](../di-modern.md) · [DI Tokens](../di-tokens.md) · [Environment Injector](../environment-injector.md) · [Standalone Migration](../standalone-migration.md) · [Signal Inputs](../signal-inputs.md) · [Signal Queries](../signal-queries.md) · [Control Flow](../control-flow.md)

---

Dependency Injection (DI) is a foundational pattern in backend frameworks like Spring and ASP.NET — and it's equally important in frontend architecture. Angular has its own DI framework designed around the framework's component tree and module system.

## What is DI?

Imagine an e-commerce cart app. Business logic often lives in services to keep components thin and logic reusable:

```ts
class ProductModel {
  sku: string;
  name: string;
  price: number;
}

interface CartItem {
  product: ProductModel;
  quantity: number;
}

class CartService {
  selectedProducts: CartItem[] = [];
  calculateTotal(): number {
    return this.selectedProducts.reduce(
      (total, item) => item.product.price * item.quantity + total,
      0
    );
  }
  addToCart(): void {
    // logic here
  }
}

class ProductComponent {
  cartService: CartService;
}
```

`ProductComponent` depends on `CartService`. To call cart methods, it needs a `CartService` instance.

### Instantiating inside the component

```ts
class ProductComponent {
  cartService: CartService;
  constructor() {
    this.cartService = new CartService();
  }
}

// equivalent to

class ProductComponent {
  cartService: CartService = new CartService();
}
```

This creates **tight coupling**. Swapping `CartService` for another implementation forces changes in `ProductComponent` and retesting both classes.

### Injection (requesting an instance)

Instead, request the dependency from a container:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
class ProductComponent {
  cartService: CartService;
  constructor(cartService: CartService) {
    this.cartService = cartService;
  }
}

// TypeScript shorthand
class ProductComponent {
  constructor(public cartService: CartService) {}
}
```

```ts
// ── v22 equivalent: inject() function ─────────────────────────────────────
import { inject } from '@angular/core';

class ProductComponent {
  // class-field inject() is the most common v22 style — no constructor needed
  readonly cartService = inject(CartService);
}
```

A container creates and provides instances:

```ts
(function container() {
  const service = new CartService(); // and CartService's dependencies, if any
  const productComp = new ProductComponent(service);
  // other code logic
})();
```

`ProductComponent` no longer knows how `CartService` is constructed. It requests an instance from an **Inversion of Control (IoC)** container. Swapping implementations doesn't require rewriting `ProductComponent`. The Angular 9 version is **constructor injection**; the v22 version uses the **`inject()` function** — they're functionally equivalent, but `inject()` doesn't require a constructor parameter list and works in non-class contexts too (see the mechanism reflection at the end of this article).

## DI in Angular

Angular DI has three parts:

- **Injector** — object with APIs to retrieve or create dependency instances
- **Provider** — recipe telling the injector how to create a dependency
- **Dependency** — the object (class, function, or plain value) to be created

Provide injectors with providers at multiple levels:

- `@Injectable()` on a service
- `providers` in `bootstrapApplication()` (replaces app-wide `@NgModule.providers`)
- `providers` in a route definition (lazy, scoped to that route subtree)
- `providers` in `@Component()` or `@Directive()`

Example:

```ts
@Injectable({
  providedIn: 'root',
})
export class CartService {
  // properties and methods
}
```

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@Component({
  selector: 'app-product',
  templateUrl: './product.component.html',
  styleUrls: ['./product.component.css'],
})
export class ProductComponent implements OnInit {
  constructor(private cartService: CartService) {}

  ngOnInit() {
    console.log(this.cartService.calculateTotal());
  }
}
```

```ts
// ── v22 equivalent: standalone + inject() ─────────────────────────────────
import { Component, inject, OnInit } from '@angular/core';

@Component({
  selector: 'app-product',
  templateUrl: './product.component.html',
  styleUrl: './product.component.css',
  // standalone: true is the v22 default — no need to spell it out
})
export class ProductComponent implements OnInit {
  private readonly cartService = inject(CartService);

  ngOnInit() {
    console.log(this.cartService.calculateTotal());
  }
}
```

`@Injectable` adds metadata so Angular knows how to create `CartService` when something like `ProductComponent` requests it. `providedIn: 'root'` registers a single app-wide singleton — this is **tree-shakable**, meaning if no component ever asks for `CartService`, the bundler can drop it from the build.

## Overriding providers

If the cart must call an external API instead of computing locally, implement the same public API with a different class:

```ts
@Injectable()
export class CartExtService {
  calculateTotal(): number {
    // call external datasource
    return Math.random() * 100;
  }
  addToCart(): void {
    // logic here
  }
}
```

Override without touching `ProductComponent`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@NgModule({
  // other metadata
  providers: [
    {
      provide: CartService,
      useClass: CartExtService,
    },
  ],
})
export class AppModule {}
```

```ts
// ── v22 equivalent: providers on bootstrapApplication() ───────────────────
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, {
  providers: [
    {
      provide: CartService,
      useClass: CartExtService,
    },
    // other app-wide providers (router, http, etc.)
  ],
});
```

You can also scope the override to a single component or a route subtree, which wasn't as ergonomic in the `@NgModule` era:

```ts
// Scoped to one component and its children:
@Component({
  selector: 'app-checkout',
  providers: [{ provide: CartService, useClass: CartExtService }],
  // ...
})
export class CheckoutComponent {}

// Scoped to a lazy route — only loaded when that route activates:
const routes: Routes = [
  {
    path: 'pro',
    loadComponent: () => import('./pro.component').then(m => m.ProComponent),
    providers: [{ provide: CartService, useClass: CartExtService }],
  },
];
```

Or pin the override on the service itself:

```ts
@Injectable({
  providedIn: 'root',
  useClass: CartExtService,
})
export class CartService {
  // logic here
}
```

## Injecting a parent component into a child

An Angular app is a component tree:

![components tree](assets/components-tree.jpg) <!-- TODO: asset -->

Because DI works at the component level, a child can inject its parent. Consider a tabs component: `TabGroupComponent` manages panels; each `TabPanelComponent` registers itself on init and unregisters on destroy.

```html
<app-tab-group>
  <app-tab-panel title="Tab 1">content tab 1</app-tab-panel>
  <app-tab-panel title="Tab 2">content tab 2</app-tab-panel>
  <app-tab-panel title="Tab 3">content tab 3</app-tab-panel>
</app-tab-group>
```

You could use `EventEmitter` to notify the parent, or inject the parent and call its methods directly.

> **Sidebar — `contentChildren()` is the modern alternative for *this specific use case*.** In v22, a tabs component is often built with `contentChildren(TabPanelComponent)` on the parent, which returns a `Signal<readonly TabPanelComponent[]>` — no parent injection from the child needed. We're sticking with parent injection here because it's what's being taught as a DI pattern, but be aware that for composite components like tabs, accordions, or steppers, signal queries are often the cleaner v22 idiom. See [Signal Queries](../signal-queries.md).

**tab-group.component.ts**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@Component({
  selector: 'app-tab-group',
  templateUrl: './tab-group.component.html',
  styleUrls: ['./tab-group.component.css'],
})
export class TabGroupComponent implements OnInit {
  tabPanelList: TabPanelComponent[] = [];

  @Input() tabActiveIndex = 0;
  @Output() tabActiveChange = new EventEmitter<number>();
  constructor() {}

  ngOnInit() {}

  selectItem(idx: number) {
    this.tabActiveIndex = idx;
    this.tabActiveChange.emit(idx);
  }

  addTabPanel(tab: TabPanelComponent) {
    this.tabPanelList.push(tab);
  }
  removeTabPanel(tab: TabPanelComponent) {
    let index = -1;
    const tabPanelList: TabPanelComponent[] = [];
    this.tabPanelList.forEach((item, idx) => {
      if (tab === item) {
        index = idx;
        return;
      }
      tabPanelList.push(item);
    });
    this.tabPanelList = tabPanelList;
    if (index !== -1) {
      this.selectItem(0);
    }
  }
}
```

```ts
// ── v22 equivalent: signal inputs/outputs + signal state ──────────────────
import { Component, input, model, signal } from '@angular/core';
import { TabPanelComponent } from './tab-panel.component';

@Component({
  selector: 'app-tab-group',
  templateUrl: './tab-group.component.html',
  styleUrl: './tab-group.component.css',
})
export class TabGroupComponent {
  // `model()` gives us a two-way bindable signal — one declaration replaces
  // the @Input/@Output pair and powers [(tabActiveIndex)] in templates.
  readonly tabActiveIndex = model(0);

  // Internal panel registry as a writable signal — readers in the template
  // pick up changes automatically without manual change detection.
  readonly tabPanelList = signal<TabPanelComponent[]>([]);

  selectItem(idx: number) {
    this.tabActiveIndex.set(idx);
  }

  addTabPanel(tab: TabPanelComponent) {
    this.tabPanelList.update(list => [...list, tab]);
  }

  removeTabPanel(tab: TabPanelComponent) {
    const next = this.tabPanelList().filter(item => item !== tab);
    this.tabPanelList.set(next);
    if (next.length > 0) {
      this.selectItem(0);
    }
  }
}
```

**tab-group.component.html**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<div class="tab-header">
  <div
    class="tab-item-header"
    role="presentation"
    *ngFor="let tab of tabPanelList; index as idx"
    (click)="selectItem(idx)"
  >
    {{tab.title}}
  </div>
</div>

<div class="tab-body">
  <ng-container *ngFor="let tab of tabPanelList; index as idx">
    <div *ngIf="idx === tabActiveIndex">
      <ng-container *ngTemplateOutlet="tab.panelBody"></ng-container>
    </div>
  </ng-container>
</div>
```

```html
<!-- v22 equivalent: @for / @if built-in control flow -->
<div class="tab-header">
  @for (tab of tabPanelList(); track tab; let idx = $index) {
    <div
      class="tab-item-header"
      role="presentation"
      [attr.data-testid]="'tab-header-' + idx"
      (click)="selectItem(idx)"
    >
      {{ tab.title() }}
    </div>
  }
</div>

<div class="tab-body">
  @for (tab of tabPanelList(); track tab; let idx = $index) {
    @if (idx === tabActiveIndex()) {
      <ng-container [ngTemplateOutlet]="tab.panelBody()!"></ng-container>
    }
  }
</div>
```

> Note the parentheses on `tabPanelList()`, `tab.title()`, and `tabActiveIndex()` — those are signal reads. The `@for` block requires a `track` expression (no silent identity fallback like `*ngFor` had). And `data-testid` replaces the old `ng-reflect-*` selectors that tests used to scrape — those reflection attributes were removed in Angular 20.

**tab-panel.component.ts** — inject the parent and register:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```ts
@Component({
  selector: 'app-tab-panel',
  template: `
    <ng-template>
      <ng-content></ng-content>
    </ng-template>
  `,
  styles: [''],
})
export class TabPanelComponent implements OnInit, OnDestroy {
  @Input() title: string;
  @ViewChild(TemplateRef, { static: true }) panelBody: TemplateRef<unknown>;
  constructor(private tabGroup: TabGroupComponent) {}

  ngOnInit() {
    this.tabGroup.addTabPanel(this);
  }
  ngOnDestroy() {
    this.tabGroup.removeTabPanel(this);
  }
}
```

```ts
// ── v22 equivalent: signal input + signal query + inject() ────────────────
import {
  Component,
  DestroyRef,
  TemplateRef,
  inject,
  input,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TabGroupComponent } from './tab-group.component';

@Component({
  selector: 'app-tab-panel',
  template: `
    <ng-template>
      <ng-content></ng-content>
    </ng-template>
  `,
})
export class TabPanelComponent {
  // Signal input — readers call title() in templates. `.required` is also
  // available if you want to enforce that callers always pass a value.
  readonly title = input<string>('');

  // Signal query — viewChild returns Signal<TemplateRef<unknown> | undefined>.
  readonly panelBody = viewChild(TemplateRef);

  // Parent injection still works — same DI lookup as constructor injection,
  // just expressed via inject(). The component decorator opens an injection
  // context, so calling inject() at the field level is legal here.
  private readonly tabGroup = inject(TabGroupComponent);

  constructor() {
    // Register on creation, deregister on destroy. DestroyRef + the
    // takeUntilDestroyed operator is the v22 idiom for "do something
    // when this component is torn down" — no ngOnDestroy hook needed.
    this.tabGroup.addTabPanel(this);

    inject(DestroyRef).onDestroy(() => {
      this.tabGroup.removeTabPanel(this);
    });
  }
}
```

## Providing an alternate tab group with the same API

The basic tab group has minimal styling. To match Bootstrap, Ant Design, or another design system while reusing `TabPanelComponent`, override the provider:

**bs-tab-group.component.ts**

```ts
@Component({
  selector: 'app-bs-tab-group',
  templateUrl: './bs-tab-group.component.html',
  styleUrl: './bs-tab-group.component.css',
  providers: [
    {
      provide: TabGroupComponent,
      useExisting: BsTabGroupComponent,
    },
  ],
})
export class BsTabGroupComponent extends TabGroupComponent {}
```

**bs-tab-group.component.html**

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```html
<ul class="nav nav-tabs" role="tablist">
  <li
    class="nav-item"
    role="presentation"
    *ngFor="let tab of tabPanelList; index as idx"
    (click)="selectItem(idx)"
  >
    <a
      class="nav-link"
      [class.active]="idx === tabActiveIndex"
      role="tab"
      aria-selected="true"
      >{{tab.title}}</a
    >
  </li>
</ul>

<div class="tab-content">
  <ng-container *ngFor="let tab of tabPanelList; index as idx">
    <div class="tab-pane active" role="tabpanel" *ngIf="idx === tabActiveIndex">
      <ng-container *ngTemplateOutlet="tab.panelBody"></ng-container>
    </div>
  </ng-container>
</div>
```

```html
<!-- v22 equivalent -->
<ul class="nav nav-tabs" role="tablist">
  @for (tab of tabPanelList(); track tab; let idx = $index) {
    <li
      class="nav-item"
      role="presentation"
      [attr.data-testid]="'bs-tab-header-' + idx"
      (click)="selectItem(idx)"
    >
      <a
        class="nav-link"
        [class.active]="idx === tabActiveIndex()"
        role="tab"
        aria-selected="true"
        >{{ tab.title() }}</a
      >
    </li>
  }
</ul>

<div class="tab-content">
  @for (tab of tabPanelList(); track tab; let idx = $index) {
    @if (idx === tabActiveIndex()) {
      <div class="tab-pane active" role="tabpanel">
        <ng-container [ngTemplateOutlet]="tab.panelBody()!"></ng-container>
      </div>
    }
  }
</div>
```

Usage:

```html
<app-bs-tab-group>
  <app-tab-panel title="Tab 1">content tab 1</app-tab-panel>
  <app-tab-panel title="Tab 2">content tab 2</app-tab-panel>
  <app-tab-panel title="Tab 3">content tab 3</app-tab-panel>
</app-bs-tab-group>
```

Angular uses this pattern internally for forms — see [`NgForm`](https://github.com/angular/angular/blob/main/packages/forms/src/directives/ng_form.ts) and [`NgModelGroup`](https://github.com/angular/angular/blob/main/packages/forms/src/directives/ng_model_group.ts).

## `forwardRef`

Angular form directives sometimes use `forwardRef` — and this is one of the few v22 patterns that looks identical to its Angular 9 counterpart. In ES2015/TypeScript, a class can only reference itself after declaration. Extracting a provider to a variable **before** the class causes an error:

```ts
const BsTabGroupProvider = {
  provide: TabGroupComponent,
  useExisting: BsTabGroupComponent,
};

@Component({
  selector: 'app-bs-tab-group',
  templateUrl: './bs-tab-group.component.html',
  styleUrl: './bs-tab-group.component.css',
  providers: [BsTabGroupProvider],
})
export class BsTabGroupComponent extends TabGroupComponent {}
```

> Error: Class 'BsTabGroupComponent' used before its declaration.

Use `forwardRef` — a function called after the class exists:

```ts
const BsTabGroupProvider = {
  provide: TabGroupComponent,
  useExisting: forwardRef(() => BsTabGroupComponent),
};
```

Inline providers in the decorator work because class decorators run **after** the class is defined — conceptually:

```ts
let SomeClass = class SomeClass {};
SomeClass = SomeDecorator(SomeClass);
```

## Provider syntax

Provider shapes (same for the `providers` array on `bootstrapApplication`, route definitions, `@Component`, and `@Directive` — and still the same as Angular 9):

**`useClass`** — shorthand and long form:

```ts
bootstrapApplication(AppComponent, {
  providers: [SomeClass]
});
```

```ts
bootstrapApplication(AppComponent, {
  providers: [{ provide: SomeClass, useClass: SomeClass }]
});
```

**`useExisting`**

```ts
@Component({
  providers: [
    {
      provide: SomeClass,
      useExisting: OtherClass
    }
  ]
})
```

**`useFactory`** — in v22, factories can use `inject()` directly instead of declaring a `deps` array:

```ts
@Component({
  providers: [
    {
      provide: SomeClass,
      useFactory: () => {
        // inject() works inside a factory — no deps array needed
        const config = inject(AppConfig);
        return new SomeClass(config);
      },
    },
  ],
})
```

The Angular 9 `deps`-array style still works:

```ts
@Component({
  providers: [
    {
      provide: SomeClass,
      useFactory: (config: AppConfig) => new SomeClass(config),
      deps: [AppConfig],
    },
  ],
})
```

**`useValue`**

```ts
@Component({
  providers: [
    {
      provide: SomeToken,
      useValue: someValue
    }
  ]
})
```

## Reducing duplication with DI and `ActivatedRoute`

A common pattern repeats across routed components: read route params, query params, or resolver data from `ActivatedRoute`. The code works, but unit tests require mocking `ActivatedRoute` — often with a stub like the [official testing guide](https://angular.dev/guide/testing) describes.

DI with factory functions and injection tokens cleans this up.

### Step 1: Factory functions for `ActivatedRoute`

Create `activated-route.factories.ts` once and reuse it:

```typescript
import { inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Observable, map } from 'rxjs';

// Observable from route paramMap by param key
// For route '/customers/:customerId', call routeParamFactory('customerId')
export function routeParamFactory(paramKey: string) {
  return (): Observable<string | null> => {
    const route = inject(ActivatedRoute);
    return route.paramMap.pipe(map(param => param.get(paramKey)));
  };
}

// Snapshot from route paramMap
export function routeParamSnapshotFactory(paramKey: string) {
  return (): string | null => {
    return inject(ActivatedRoute).snapshot.paramMap.get(paramKey);
  };
}

// Observable from queryParamMap
// For route 'customers?from=USA', call queryParamFactory('from')
export function queryParamFactory(paramKey: string) {
  return (): Observable<string | null> => {
    const route = inject(ActivatedRoute);
    return route.queryParamMap.pipe(map(param => param.get(paramKey)));
  };
}

// Snapshot from queryParamMap
export function queryParamSnapshotFactory(paramKey: string) {
  return (): string | null => {
    return inject(ActivatedRoute).snapshot.queryParamMap.get(paramKey);
  };
}
```

Note that the v22 version doesn't take `route` as a parameter — the factory grabs it via `inject()` at call time. That's why no `deps` array is needed in the provider config below.

### Step 2: Injection token and component provider

```typescript
export const APP_SOME_ID = new InjectionToken<Observable<string | null>>(
  'stream of id from route param',
);

@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.template.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: APP_SOME_ID,
      useFactory: routeParamFactory('id'),
      // No `deps` needed — the factory uses inject() internally
    }
  ]
})
export class MyComponent {}
```

The `'id'` key matches your route config:

```typescript
const routes: Routes = [
  {
    path: ':id',
    loadComponent: () => import('./my-component').then(m => m.MyComponent),
  }
];
```

### Step 3: Inject and use the token

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
export const APP_SOME_ID = new InjectionToken<Observable<string>>(
  'stream of id from route param',
);

@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.template.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: APP_SOME_ID,
      useFactory: routeParamFactory('id'),
      deps: [ActivatedRoute],
    },
  ],
})
export class MyComponent {
  constructor(
    @Inject(APP_SOME_ID)
    private readonly id$: Observable<string>
  ) {}

  // then do something with this.id$
}
```

```typescript
// ── v22 equivalent: inject() takes any token, no @Inject() decorator needed
import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.template.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: APP_SOME_ID,
      useFactory: routeParamFactory('id'),
    },
  ],
})
export class MyComponent {
  // For an observable token, inject() returns the observable directly:
  private readonly id$ = inject(APP_SOME_ID);

  // Bonus: convert to a signal for ergonomic template reads as {{ id() }}:
  readonly id = toSignal(this.id$);
}
```

Unit tests become simpler — provide the observable directly instead of mocking `ActivatedRoute`:

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
describe('MyComponent', () => {
  let fixture: ComponentFixture<MyComponent>;
  let component: MyComponent;

  beforeEach(async () => {
    TestBed.overrideComponent(MyComponent, {
      set: {
        providers: [{
          provide: APP_SOME_ID,
          useValue: scheduled(of('1234'), asyncScheduler)
        }]
      }
    });

    await TestBed.configureTestingModule({
      declarations: [MyComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(MyComponent);
    component = fixture.componentInstance;
  });

  it('should get :id from route param', (done) => {
    fixture.detectChanges();

    component.id$.subscribe(id => {
      expect(id).toBe('1234');
      done();
    });
  });
});
```

```typescript
// ── v22 equivalent: standalone import, whenStable, firstValueFrom ─────────
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { firstValueFrom, of } from 'rxjs';
import { MyComponent, APP_SOME_ID } from './my-component';

describe('MyComponent', () => {
  let fixture: ComponentFixture<MyComponent>;
  let component: MyComponent;

  beforeEach(async () => {
    TestBed.overrideComponent(MyComponent, {
      set: {
        providers: [{
          provide: APP_SOME_ID,
          useValue: of('1234'),
        }],
      },
    });

    await TestBed.configureTestingModule({
      // Standalone components go in `imports`, not `declarations`
      imports: [MyComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(MyComponent);
    component = fixture.componentInstance;
  });

  it('should get :id from route param', async () => {
    await fixture.whenStable();

    const id = await firstValueFrom(component['id$']);
    expect(id).toBe('1234');
  });
});
```

Benefits:

- Less duplicated route-reading logic — cleaner, easier to maintain
- Simpler tests — inject the banana, not the whole jungle (and the monkey holding it)
- The v22 `inject()` style means factories can themselves call `inject()` for sub-dependencies, so even moderately complex provider chains stay readable

### Bonus: chained tokens for customer details

```typescript
export const APP_CUSTOMER_ID = new InjectionToken<Observable<string | null>>(
  'stream of id from route param',
);

export const APP_CUSTOMER_DETAILS = new InjectionToken<Observable<Customer>>(
  'stream of customer details'
);

export const PROVIDERS: Provider[] = [
  {
    provide: APP_CUSTOMER_ID,
    useFactory: routeParamFactory('id'),
  },
  {
    provide: APP_CUSTOMER_DETAILS,
    useFactory: () => {
      // Chained inject — the factory pulls both upstream tokens itself
      const id$ = inject(APP_CUSTOMER_ID);
      const apiService = inject(ApiService);
      return id$.pipe(
        switchMap((id) => apiService.getCustomerById(id!)),
      );
    },
  },
];

@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.template.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [PROVIDERS],
})
export class MyComponent {
  private readonly customer$ = inject(APP_CUSTOMER_DETAILS);
  readonly customer = toSignal(this.customer$);

  // then do something with this.customer() in the template
}
```

---

## Mechanism reflection — how DI evolved from Angular 9 to v22

DI in Angular has had one truly load-bearing change since 2020: the introduction of the **`inject()` function and the injection context**. Everything else — standalone components, signal inputs, control flow — is layered on top of it. It's worth digging into how DI actually worked then versus now, because the "why" makes the "what" much easier to reason about.

### How DI worked in Angular 2–13 — constructor injection via Reflect metadata

In Angular 9, the *only* way to ask for a dependency was through a class constructor:

```ts
constructor(private cartService: CartService) {}
```

For this to work, Angular needed to know at runtime that the first parameter of `ProductComponent`'s constructor wants a `CartService`. TypeScript types are erased at compile time, so the type `CartService` doesn't survive into the JavaScript output. Angular relied on **two TypeScript compiler options** to bridge the gap:

```jsonc
// tsconfig.json (Angular 9 era)
{
  "compilerOptions": {
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true  // ← this is the load-bearing one
  }
}
```

With `emitDecoratorMetadata` on, the TypeScript compiler emitted extra calls into the compiled JavaScript that recorded the constructor parameter types using the `Reflect.metadata` API:

```js
// What TS actually emitted for ProductComponent in Angular 9
let ProductComponent = class ProductComponent {
  constructor(cartService) {
    this.cartService = cartService;
  }
};
ProductComponent = __decorate([
  Component({ /* ... */ }),
  __metadata("design:paramtypes", [CartService])  // ← the type info, captured
], ProductComponent);
```

At runtime, Angular's injector read `Reflect.getMetadata('design:paramtypes', ProductComponent)` to find out that slot 0 wants a `CartService`, then looked `CartService` up in the injector tree and passed it in. This is also why Angular 9 apps needed `core-js/es7/reflect` in `polyfills.ts` — the `Reflect.metadata` API isn't part of standard JavaScript.

The big limitation: **this only worked at class boundaries**. A route guard had to be a class implementing `CanActivate` because the only way to get hold of an injector was via a constructor parameter. The same was true for interceptors, resolvers, and any other "callback-shaped" extension point — they all became classes purely so DI could reach them.

### What changed in Angular 14+ — `inject()` and the injection context

In Angular 14, the team shipped a function called `inject()`:

```ts
import { inject } from '@angular/core';

class ProductComponent {
  private cartService = inject(CartService);
}
```

This looks like a small syntactic convenience, but mechanically it's a different model. `inject()` doesn't read type metadata — it takes the token as a runtime argument. What makes it tick is the **injection context**: an internal stack maintained by the framework that tracks "which injector should `inject()` resolve against right now?"

Conceptually:

```ts
// Internal pseudocode for what the framework does when creating a component
function createComponent(componentDef, parentInjector) {
  pushInjectionContext(parentInjector);
  try {
    const instance = new componentDef.type();  // field initializers run here,
                                                // and inject() reads the context
  } finally {
    popInjectionContext();
  }
}
```

The framework opens an injection context **before** the class is instantiated, and closes it after. Anything that runs while the context is open — constructor body, class field initializers (which TS compiles into the constructor), explicit `inject()` calls — can resolve dependencies against the current injector.

Crucially, the framework also opens injection contexts in places that aren't class construction:

- Before invoking a **factory provider** (`useFactory`)
- Before running a **functional route guard, resolver, or matcher**
- Before invoking a **functional HTTP interceptor**
- Inside the `effect()` callback's initial sync execution
- Anywhere you explicitly wrap code with `runInInjectionContext(injector, fn)`

This is the unlock. Functional guards, functional interceptors, and `resource()`/`httpResource()` all became possible because they can call `inject()` directly:

```ts
// v22 — a functional route guard, no class required
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.isLoggedIn() || router.parseUrl('/login');
};
```

In Angular 9, this had to be a class implementing `CanActivate` — the only way to get hold of `AuthService` was through a constructor parameter. The function above can't have a constructor, but `inject()` doesn't need one. It just needs the injection context to be open, which the router framework guarantees before invoking the guard.

### What stayed exactly the same

The runtime DI **algorithm** is unchanged:

1. Look up the requested token in the current injector
2. If not found, walk up the parent injector chain
3. If the token has a `providedIn` hint, fall back to the platform / root injector
4. If still not found, throw `NullInjectorError` — unless the lookup was `{ optional: true }`, in which case return `null`

`providedIn: 'root'` tree-shaking, hierarchical scoping, `forwardRef` for self-references, the four provider shapes (`useClass` / `useExisting` / `useFactory` / `useValue`), and `InjectionToken` for non-class dependencies — these are all identical between Angular 9 and v22. If you understood the injector tree in 2020, you understand it now.

### What got removed or deprecated

- **`ReflectiveInjector`** — removed. It was the old runtime-reflection-based injector class; the static (compile-time-resolved) injector replaced it.
- **`TestBed.get()`** — removed in Angular 9 (actually marked deprecated earlier). Replaced by `TestBed.inject()`, which has better type inference.
- **`emitDecoratorMetadata` requirement** — no longer needed for DI to work, because `inject()` doesn't read parameter type metadata. (TypeScript projects may still enable it for other libraries.)
- **`flushEffects()`** in tests — deprecated in favor of `TestBed.tick()`, which advances both effects and signal-driven view updates in a single call.
- **`ng-reflect-*` DOM attributes** — removed in Angular 20. They were never meant for production scraping; use `data-testid` instead.

### The mental shift

The shift from constructor injection to `inject()` looks cosmetic but reflects a deeper move: DI used to be tied to the **class lifecycle** (something gets injected when something else is constructed). In v22, DI is tied to an **injection context** that the framework opens around any code that needs dependencies — class construction, factory execution, guard invocation, effect setup. That decoupling is what lets the rest of the modern API (functional guards, functional interceptors, the `effect()` API, signal-based resources, `resource()`/`httpResource()`) exist at all.

---

## Summary

We've covered DI concepts, Angular's injector/provider model, provider overrides, parent-component injection, `forwardRef`, the full provider syntax, and using factory providers with injection tokens to DRY up `ActivatedRoute` access — and we've seen the v22 expressions for every one of these. The takeaway is that the **DI model is unchanged** since Angular 9; what's new is `inject()` and the injection context, which extend DI to non-class contexts and unlock the functional APIs that define modern Angular.

## See also (related gap articles)

- [Modern DI with `inject()`](../di-modern.md) — deep dive into `inject()`, injection context, and `runInInjectionContext()`
- [DI Tokens](../di-tokens.md) — `InjectionToken<T>`, multi-providers, and design patterns
- [Environment Injector](../environment-injector.md) — root vs platform vs route-level injectors, lazy boundaries
- [Standalone Migration](../standalone-migration.md) — migrating off `@NgModule`
- [Signal Inputs](../signal-inputs.md) — `input()`, `output()`, `model()` in depth
- [Signal Queries](../signal-queries.md) — `viewChild()`, `viewChildren()`, `contentChild()`, `contentChildren()`
- [Control Flow](../control-flow.md) — `@if`, `@for`, `@switch`, `@let`
- [Router (modern)](../router-modern.md) — functional guards/resolvers that lean on `inject()`
- [Unit Tests](../unit-tests.md) — `TestBed.inject()`, `TestBed.tick()`, `await fixture.whenStable()`

## Further reading

- [Dependency injection in Angular](https://www.tiepphan.com/thu-nghiem-voi-angular-dependency-injection-trong-angular/) (Vietnamese — original author)
- [Angular DI guide (angular.dev)](https://angular.dev/guide/di)
- [Hierarchical injectors (angular.dev)](https://angular.dev/guide/di/hierarchical-dependency-injection)
- [Dependency Injection in Angular (thoughtram)](https://blog.thoughtram.io/angular/2015/05/18/dependency-injection-in-angular-2.html)
- [Private providers (Angular in Depth)](https://indepth.dev/posts/1306/private-providers)
- [Leveraging DI to reduce duplicated code (Angular in Depth)](https://indepth.dev/posts/1471/leveraging-dependency-injection-to-reduce-duplicated-code-in-angular)

## Youtube Video

[![Introduction to DI](https://img.youtube.com/vi/_JnUGhVhq_o/0.jpg)](https://youtu.be/_JnUGhVhq_o) <!-- TODO: asset -->

[![DI in Angular Apps](https://img.youtube.com/vi/hTsn6L8vcVg/0.jpg)](https://youtu.be/hTsn6L8vcVg) <!-- TODO: asset -->

## Code sample

- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-15?file=src/app/di.ts
- https://stackblitz.com/edit/angular-ivy-100-days-of-code-day-16?file=src%2Fapp%2Ftab-panel%2Ftab-panel.component.ts
- https://github.com/phhien203/ngx-router

## Author

Tiep Phan — https://github.com/tieppt

Hien Pham — https://twitter.com/HienHuuPham

*Translated from the original Vietnamese as part of the angular-concepts project. Modernized to Angular v22 in the Phase 2 upgrade pass.*

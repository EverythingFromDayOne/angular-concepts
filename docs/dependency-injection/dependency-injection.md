---
roadmap_node: "dependency-injection"
title: "Dependency Injection"
file: "dependency-injection/dependency-injection.md"
source_days: [15, 16, 48]
original_authors: ["Tiep Phan", "Hien Pham"]
status:
  translated: true
  upgraded: false
  reviewed: false
angular_when_written: "9"
angular_baseline: "22"
---

# Dependency Injection

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

A container creates and provides instances:

```ts
(function container() {
  const service = new CartService(); // and CartService's dependencies, if any
  const productComp = new ProductComponent(service);
  // other code logic
})();
```

`ProductComponent` no longer knows how `CartService` is constructed. It requests an instance from an **Inversion of Control (IoC)** container. Swapping implementations doesn't require rewriting `ProductComponent`. This is **constructor injection** — the most common DI style.

## DI in Angular

Angular DI has three parts:

- **Injector** — object with APIs to retrieve or create dependency instances
- **Provider** — recipe telling the injector how to create a dependency
- **Dependency** — the object (class, function, or plain value) to be created

Provide injectors with providers at multiple levels:

- `@Injectable()` on a service
- `providers` in `@NgModule()`
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

`@Injectable` adds metadata so Angular knows how to create `CartService` when something like `ProductComponent` requests it. `providedIn: 'root'` registers a single app-wide singleton.

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

Or on the service itself:

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

**tab-group.component.ts**

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

## Providing an alternate tab group with the same API

The basic tab group has minimal styling. To match Bootstrap, Ant Design, or another design system while reusing `TabPanelComponent`, override the provider:

**bs-tab-group.component.ts**

```ts
@Component({
  selector: 'app-bs-tab-group',
  templateUrl: './bs-tab-group.component.html',
  styleUrls: ['./bs-tab-group.component.css'],
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

Usage:

```html
<app-bs-tab-group>
  <app-tab-panel title="Tab 1">content tab 1</app-tab-panel>
  <app-tab-panel title="Tab 2">content tab 2</app-tab-panel>
  <app-tab-panel title="Tab 3">content tab 3</app-tab-panel>
</app-bs-tab-group>
```

Angular uses this pattern internally for forms — see [ngForm](https://github.com/angular/angular/blob/9.1.x/packages/forms/src/directives/ng_form.ts) and [ngModelGroup](https://github.com/angular/angular/blob/9.1.x/packages/forms/src/directives/ng_model_group.ts).

## `forwardRef`

Angular form directives sometimes use `forwardRef`. In ES2015/TypeScript, a class can only reference itself after declaration. Extracting a provider to a variable **before** the class causes an error:

```ts
const BsTabGroupProvider = {
  provide: TabGroupComponent,
  useExisting: BsTabGroupComponent,
};

@Component({
  selector: 'app-bs-tab-group',
  templateUrl: './bs-tab-group.component.html',
  styleUrls: ['./bs-tab-group.component.css'],
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

Provider shapes (same for `@NgModule`, `@Component`, `@Directive`):

**`useClass`** — shorthand and long form:

```ts
@NgModule({
  providers: [SomeClass]
})
```

```ts
@NgModule({
  providers: [{ provide: SomeClass, useClass: SomeClass}]
})
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

**`useFactory`**

```ts
@Component({
  providers: [
    {
      provide: SomeClass,
      useFactory: function() {
        return aValue;
      }
    }
  ]
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

A common pattern repeats across routed components: read route params, query params, or resolver data from `ActivatedRoute`. The code works, but unit tests require mocking `ActivatedRoute` — often with a stub like the [official testing guide](https://angular.io/guide/testing-components-scenarios#activatedroutestub) describes.

DI with factory functions and injection tokens cleans this up.

### Step 1: Factory functions for `ActivatedRoute`

Create `activated-route.factories.ts` once and reuse it:

```typescript
import {ActivatedRoute} from '@angular/router';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

// Observable from route paramMap by param key
// For route '/customers/:customerId', call routeParamFactory('customerId')
export function routeParamFactory(
  paramKey: string
): (route: ActivatedRoute) => Observable<string | null> {
  return (route: ActivatedRoute): Observable<string | null> => {
    return route.paramMap.pipe(map(param => param.get(paramKey)));
  };
}

// Snapshot from route paramMap
export function routeParamSnapshotFactory(
  paramKey: string
): (route: ActivatedRoute) => string | null {
  return (route: ActivatedRoute): string | null => {
    return route.snapshot.paramMap.get(paramKey);
  };
}

// Observable from queryParamMap
// For route 'customers?from=USA', call queryParamFactory('from')
export function queryParamFactory(
  paramKey: string
): (route: ActivatedRoute) => Observable<string | null> {
  return (route: ActivatedRoute): Observable<string | null> => {
    return route.queryParamMap.pipe(map(param => param.get(paramKey)));
  };
}

// Snapshot from queryParamMap
export function queryParamSnapshotFactory(
  paramKey: string
): (route: ActivatedRoute) => string | null {
  return (route: ActivatedRoute): string | null => {
    return route.snapshot.queryParamMap.get(paramKey);
  };
}
```

### Step 2: Injection token and component provider

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
      deps: [ActivatedRoute]
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
    component: MyComponent
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

Unit tests become simpler — provide the observable directly instead of mocking `ActivatedRoute`:

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

Benefits:

- Less duplicated route-reading logic — cleaner, easier to maintain
- Simpler tests — inject the banana, not the whole jungle (and the monkey holding it)

### Bonus: chained tokens for customer details

```typescript
export const APP_CUSTOMER_ID = new InjectionToken<Observable<string>>(
  'stream of id from route param',
);

export const APP_CUSTOMER_DETAILS = new InjectionToken<Observable<Customer>>(
  'stream of customer details'
);

export const PROVIDERS: Provider[] = [
  {
    provide: APP_CUSTOMER_ID,
    useFactory: routeParamFactory('id'),
    deps: [ActivatedRoute],
  },
  {
    provide: APP_CUSTOMER_DETAILS,
    useFactory: (id$: Observable<string>, apiService: ApiService) => {
      return id$.pipe(
        switchMap((id: string) => apiService.getCustomerById(id)),
      );
    },
    deps: [APP_CUSTOMER_ID, ApiService]
  }
];

@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.template.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [PROVIDERS],
})
export class MyComponent {
  constructor(
    @Inject(APP_CUSTOMER_DETAILS)
    private readonly customer$: Observable<Customer>
  ) {}

  // then do something with this.customer$
}
```

## Summary

We've introduced DI concepts, Angular's injector/provider model, provider overrides, parent-component injection, `forwardRef`, the full provider syntax, and using factory providers with injection tokens to DRY up `ActivatedRoute` access.

Further reading:

- [Dependency injection in Angular](https://www.tiepphan.com/thu-nghiem-voi-angular-dependency-injection-trong-angular/) (Vietnamese)
- https://angular.io/guide/glossary#injector
- https://angular.io/guide/dependency-injection
- https://blog.thoughtram.io/angular/2015/05/18/dependency-injection-in-angular-2.html
- https://indepth.dev/posts/1306/private-providers
- https://indepth.dev/posts/1471/leveraging-dependency-injection-to-reduce-duplicated-code-in-angular

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

*Translated from the original Vietnamese as part of the angular-concepts project.*

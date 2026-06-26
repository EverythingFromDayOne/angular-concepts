---
roadmap_node: "ionic"
title: "Ionic"
file: "tooling/ionic.md"
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
> Written fresh for Angular v22, Ionic 8, Capacitor 8.

# Ionic

> **Lead with this:** Ionic gives your Angular app a mobile-native UI layer —
> platform-aware components that look and feel like iOS or Android — and
> Capacitor compiles the whole thing into a real native app you publish to
> the App Store and Google Play.

## What it is

Ionic is a three-layer stack:

| Layer | Package | What it does |
| --- | --- | --- |
| **UI components** | `@ionic/angular` | Mobile-native components: tabs, modals, lists, inputs, toasts — all platform-adaptive |
| **Angular** | `@angular/core` | Routing, DI, templates, change detection — everything Angular |
| **Native runtime** | `@capacitor/core` | Wraps the compiled web app in a native shell; exposes camera, GPS, push notifications, file system |

You write one Angular codebase. `ionic serve` runs it in the browser during
development. `ionic capacitor run ios` builds the Angular app, copies it into
an Xcode project, and launches it in the iOS simulator (or on a physical
device). The same code produces the Android APK, the iOS IPA, and a PWA from
a single source.

## How it works under the hood

### Old approach — native apps for each platform

Before cross-platform tools matured, building for iOS and Android meant
maintaining two entirely separate codebases:

```
iOS app:   Swift / Objective-C in Xcode
             ↓ review, ship
           App Store

Android:   Kotlin / Java in Android Studio
             ↓ review, ship
           Google Play
```

A new feature — a button, a form field, a screen — meant implementing it
twice, in two different languages, with two different UI frameworks,
reviewed and shipped separately. A bug in shared business logic meant fixing
it in two places. Teams either specialized (iOS engineer, Android engineer)
or one person maintained both, working at half speed on each.

### Ionic's approach — one web app, three targets

Ionic compiles your Angular app to static web assets (HTML, JS, CSS), then
Capacitor wraps those assets in a native shell per platform:

```
Angular source (single codebase)
         ↓
ng build → dist/
         ↓
Capacitor copies dist/ into iOS/Android projects
         ↓
iOS:     Xcode builds → WKWebView renders your app
Android: Android Studio builds → WebView renders your app
Web/PWA: Browser renders directly
```

**WKWebView (iOS) and WebView (Android)** are high-performance browser
engines embedded in native containers. Your Angular code runs in these
engines — the full browser runtime, with access to JavaScript APIs and
modern CSS. Capacitor bridges between this web runtime and native platform
APIs via a thin plugin system: JavaScript calls → JSON bridge → native Swift/Kotlin code → native platform API.

**Ionic's UI components** are custom web components (built on Web Components)
that adapt their appearance based on the host platform. An `<ion-button>` on
iOS renders with iOS ripple effects and fonts; on Android, it renders with
Material Design ripple effects. The same template produces platform-appropriate
output.

### NgModule vs standalone imports

<!-- legacy: written for Angular 9 (2020) — modernized in the upgrade pass -->
```typescript
// Old approach (Ionic 6 / Angular 9–13) — IonicModule.forRoot() in NgModule
@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    IonicModule.forRoot(),    // imports all Ionic components — large bundle
    AppRoutingModule,
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

```typescript
// Modern approach (Ionic 7+ / Angular 14+) — standalone per component
// Import ONLY the Ionic components your component uses
import { IonHeader, IonToolbar, IonTitle, IonContent } from '@ionic/angular/standalone';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [IonHeader, IonToolbar, IonTitle, IonContent],
  template: `...`,
})
export class HomePage {}
```

The standalone import path is `@ionic/angular/standalone` — not
`@ionic/angular`. This is a separate entry point that enables tree-shaking:
only the Ionic components you import get bundled. With `IonicModule.forRoot()`,
all ~100 Ionic components entered the bundle whether you used them or not.

## Setup

### New project

```bash
npm install -g @ionic/cli
ionic start myApp tabs --type=angular
cd myApp
ionic serve      # opens browser at http://localhost:8100
```

The `tabs` starter gives you a three-tab shell — the most common mobile
navigation pattern. Other starters: `blank`, `sidemenu`, `list`.

### Add Capacitor for native targets

```bash
# Add native platforms
ionic capacitor add ios
ionic capacitor add android

# Build the Angular app, sync to native projects, open Xcode
ionic capacitor build ios

# Build, sync, and run in iOS simulator (no Xcode needed)
ionic capacitor run ios

# Live reload on a physical device — edits reflect instantly
ionic capacitor run ios -l --external
```

After adding Capacitor, your project structure gains:

```
myApp/
├── ios/                 ← Xcode project (check into source control)
├── android/             ← Android Studio project (check into source control)
├── capacitor.config.ts  ← Capacitor configuration
└── src/                 ← Angular source (unchanged)
```

Both `ios/` and `android/` should be checked into source control — they're
part of your app, not generated artifacts.

## Basic usage — a typical page

```typescript
// home.page.ts
import { Component, signal, inject } from '@angular/core';
import {
  IonHeader, IonToolbar, IonTitle, IonContent,
  IonList, IonItem, IonLabel, IonButton,
  IonFab, IonFabButton, IonIcon,
  IonRefresher, IonRefresherContent,
  RefresherCustomEvent,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { add, refresh } from 'ionicons/icons';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    IonHeader, IonToolbar, IonTitle, IonContent,
    IonList, IonItem, IonLabel, IonButton,
    IonFab, IonFabButton, IonIcon,
    IonRefresher, IonRefresherContent,
    RouterLink,
  ],
  template: `
    <ion-header [translucent]="true">
      <ion-toolbar>
        <ion-title>My App</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content [fullscreen]="true">
      <!-- Pull-to-refresh -->
      <ion-refresher slot="fixed" (ionRefresh)="handleRefresh($event)">
        <ion-refresher-content />
      </ion-refresher>

      <ion-list>
        @for (item of items(); track item.id) {
          <ion-item [routerLink]="['/detail', item.id]" detail>
            <ion-label>
              <h2>{{ item.title }}</h2>
              <p>{{ item.subtitle }}</p>
            </ion-label>
          </ion-item>
        }
      </ion-list>

      <!-- Floating action button -->
      <ion-fab slot="fixed" vertical="bottom" horizontal="end">
        <ion-fab-button (click)="addItem()">
          <ion-icon name="add" />
        </ion-fab-button>
      </ion-fab>
    </ion-content>
  `,
})
export class HomePage {
  items = signal<Item[]>([]);

  constructor() {
    // Register icons you use in this component
    addIcons({ add, refresh });
  }

  async handleRefresh(event: RefresherCustomEvent): Promise<void> {
    await this.loadItems();
    event.target.complete();
  }
}
```

### Tab navigation

Tabs are the most common mobile navigation pattern. Ionic + Angular Router
handle tab state automatically:

```typescript
// tabs.page.ts
import { Component } from '@angular/core';
import {
  IonTabs, IonTabBar, IonTabButton, IonIcon, IonLabel
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { homeOutline, searchOutline, personOutline } from 'ionicons/icons';

@Component({
  selector: 'app-tabs',
  standalone: true,
  imports: [IonTabs, IonTabBar, IonTabButton, IonIcon, IonLabel],
  template: `
    <ion-tabs>
      <!-- IonRouterOutlet renders the active tab's page -->
      <ion-tab-bar slot="bottom">
        <ion-tab-button tab="home">
          <ion-icon name="home-outline" />
          <ion-label>Home</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="search">
          <ion-icon name="search-outline" />
          <ion-label>Search</ion-label>
        </ion-tab-button>
        <ion-tab-button tab="profile">
          <ion-icon name="person-outline" />
          <ion-label>Profile</ion-label>
        </ion-tab-button>
      </ion-tab-bar>
    </ion-tabs>
  `,
})
export class TabsPage {
  constructor() {
    addIcons({ homeOutline, searchOutline, personOutline });
  }
}
```

```typescript
// Tab routes
export const routes: Routes = [
  {
    path: 'tabs',
    component: TabsPage,
    children: [
      { path: 'home',    loadComponent: () => import('./home.page').then(m => m.HomePage) },
      { path: 'search',  loadComponent: () => import('./search.page').then(m => m.SearchPage) },
      { path: 'profile', loadComponent: () => import('./profile.page').then(m => m.ProfilePage) },
      { path: '', redirectTo: '/tabs/home', pathMatch: 'full' },
    ],
  },
  { path: '', redirectTo: '/tabs/home', pathMatch: 'full' },
];
```

### Accessing native device APIs via Capacitor

Capacitor plugins provide typed TypeScript APIs for native features:

```typescript
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { Geolocation } from '@capacitor/geolocation';
import { PushNotifications } from '@capacitor/push-notifications';

// Camera — works in browser (getUserMedia), iOS, and Android
async takePhoto(): Promise<void> {
  const photo = await Camera.getPhoto({
    resultType: CameraResultType.DataUrl,
    source: CameraSource.Camera,
    quality: 80,
  });
  this.imageUrl.set(photo.dataUrl ?? null);
}

// Geolocation — works everywhere
async getLocation(): Promise<void> {
  const position = await Geolocation.getCurrentPosition();
  console.log(position.coords.latitude, position.coords.longitude);
}

// Push notifications — requires native (iOS/Android) — no-op on web
async registerPush(): Promise<void> {
  let permission = await PushNotifications.requestPermissions();
  if (permission.receive === 'granted') {
    await PushNotifications.register();
  }
}
```

Install Capacitor plugins individually:

```bash
npm install @capacitor/camera
npm install @capacitor/geolocation
npm install @capacitor/push-notifications
ionic capacitor sync   # copies to native projects
```

## Real-world patterns

### Pattern 1 — Modal bottom sheet

Opening a modal in Ionic is imperative — the `ModalController` service creates
and presents the modal component:

```typescript
import { Component, inject } from '@angular/core';
import { ModalController, IonButton, IonContent, IonHeader, IonToolbar, IonTitle } from '@ionic/angular/standalone';
import { EditProfilePage } from '../edit-profile/edit-profile.page';

@Component({
  standalone: true,
  imports: [IonButton, IonContent, IonHeader, IonToolbar, IonTitle],
  template: `
    <ion-header><ion-toolbar><ion-title>Profile</ion-title></ion-toolbar></ion-header>
    <ion-content>
      <ion-button (click)="openEditModal()">Edit Profile</ion-button>
    </ion-content>
  `,
})
export class ProfilePage {
  private modalCtrl = inject(ModalController);

  async openEditModal(): Promise<void> {
    const modal = await this.modalCtrl.create({
      component: EditProfilePage,
      componentProps: { userId: 'current' },
      breakpoints: [0, 0.5, 1],         // iOS-style sheet — snap to 50% or full
      initialBreakpoint: 0.5,
    });

    await modal.present();
    const { data } = await modal.onWillDismiss();
    if (data?.updated) this.loadProfile();
  }
}
```

### Pattern 2 — Platform detection for conditional behavior

Your code runs in browser, iOS, and Android. Use Capacitor's `Capacitor` object
to gate platform-specific behavior:

```typescript
import { Capacitor } from '@capacitor/core';

@Injectable({ providedIn: 'root' })
export class PhotoService {
  async pickPhoto(): Promise<string | null> {
    if (Capacitor.isNativePlatform()) {
      // Native: use the device camera/gallery
      const photo = await Camera.getPhoto({
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Photos,
      });
      return photo.dataUrl ?? null;
    } else {
      // Browser: use a file input
      return this.pickFromFileInput();
    }
  }

  private pickFromFileInput(): Promise<string | null> {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.onchange = () => {
        const file = input.files?.[0];
        if (!file) { resolve(null); return; }
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(file);
      };
      input.click();
    });
  }
}
```

## Common mistakes

### Mistake 1 — Importing from @ionic/angular instead of @ionic/angular/standalone

In standalone components, all Ionic imports come from `@ionic/angular/standalone`.
Importing from `@ionic/angular` brings in the NgModule-based barrel and causes
compilation errors or unexpected behavior:

```typescript
// ❌ Wrong path for standalone components
import { IonHeader } from '@ionic/angular';

// ✅ Correct path for standalone components
import { IonHeader } from '@ionic/angular/standalone';
```

### Mistake 2 — Forgetting addIcons() for Ionicons

Ionic's standalone icon system requires you to register each icon's SVG data
before using it. Omitting `addIcons()` shows a broken icon with no error:

```typescript
// ❌ Icon used in template but never registered — silently renders nothing
@Component({
  template: `<ion-icon name="heart" />`,
})
export class LikeButton {}

// ✅ Register in constructor
import { addIcons } from 'ionicons';
import { heart } from 'ionicons/icons';

@Component({ template: `<ion-icon name="heart" />` })
export class LikeButton {
  constructor() { addIcons({ heart }); }
}
```

### Mistake 3 — Testing PWA features with ionic serve

`ionic serve` runs the Angular dev server in a regular browser tab. Native
Capacitor features (Camera, Geolocation on some browsers, Push Notifications)
won't behave identically to a real device. Always test on a physical device
or simulator before shipping:

```bash
# ❌ Browser simulation — not representative
ionic serve

# ✅ Physical iOS device with live reload
ionic capacitor run ios -l --external

# ✅ iOS simulator
ionic capacitor run ios
```

### Mistake 4 — Not syncing Capacitor after installing plugins

After `npm install @capacitor/some-plugin`, you must sync the native projects:

```bash
npm install @capacitor/camera
ionic capacitor sync    # ← easy to forget; native projects won't have the plugin
```

Without `sync`, the native project doesn't know about the plugin and the app
crashes on launch.

## How this evolved

> - **Ionic 1–3 (2013–2017):** AngularJS (v1), then Angular. Cordova as the
>   only native runtime — a WebView wrapper with a JavaScript bridge. Worked
>   but suffered from Cordova's maintenance burden and fragmented plugin
>   ecosystem.
>
> - **Ionic 4 (2018):** Complete rewrite. Web Components (Stencil.js) for UI
>   components — no longer Angular-only, now also React and Vue. Capacitor
>   introduced as a modern Cordova alternative. Angular integration via
>   `@ionic/angular`.
>
> - **Ionic 5–6 (2020–2022):** Stability and component polish. `IonicModule.forRoot()`
>   still required — all components loaded regardless of usage.
>
> - **Ionic 7 (2023):** Standalone component support introduced. New import
>   path `@ionic/angular/standalone`. Tree-shakeable imports — only components
>   you import ship in the bundle. `addIcons()` required for Ionicons.
>
> - **Ionic 8 / Capacitor 8 (2024–2025):** Angular 18+ official support.
>   Capacitor 8 adopts Swift Package Manager (SPM) as the default iOS
>   dependency manager, replacing CocoaPods for new projects. Capacitor reaches
>   nearly one million downloads per week.
>
> - **With Angular 22 (now):** Ionic 8 is compatible with Angular 22. The
>   recommended stack is: `@ionic/angular/standalone` imports + Angular signals
>   for state + Capacitor 8 for native features. Cordova is fully deprecated —
>   all new projects should use Capacitor.

## See also

- [PWA](./pwa.md) — Ionic apps are also PWAs; the service worker story applies
- [Angular Elements](./angular-elements.md) — Ionic components are Web
  Components built with Stencil — same underlying spec
- [Signals](../reactivity/signals.md) — signals work inside Ionic components
  just like any Angular component
- [Official Ionic Angular docs](https://ionicframework.com/docs/angular/overview)
- [Capacitor docs](https://capacitorjs.com/docs)
- [Ionic component reference](https://ionicframework.com/docs/components)
- [Ionicons](https://ionic.io/ionicons)

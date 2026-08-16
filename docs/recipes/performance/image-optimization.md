---
recipe_id: "image-optimization"
description: "NgOptimizedImage handles the sizing, format, and priority hints that most LCP problems come down to, without rewriting the page"
primary_concept: "components/components"
related_concepts: ["performance/performance-auditing", "routing/routing", "ssr/ssr-hydration"]
demo_repo: null
angular_baseline: "22.1.1"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Image Optimization: LCP Wins Without Rewriting Everything

> **What you'll build:** an image strategy that gets LCP under 1.5s
> on typical mobile connections — the `NgOptimizedImage` directive
> with its priority hints and automatic `srcset`, image loaders for
> Cloudinary/Imgix/ImageKit or a custom CDN, the `fill` attribute
> for hero images, blur-up placeholders while images load,
> alternatives when you can't use the directive (background images,
> canvas), and the "NG02xxx" warnings that tell you what to fix.
>
> **Concepts you'll touch:** Components, [Performance Auditing](./performance-auditing.md), [Routing](../../concepts/routing/routing.md), [SSR / Hydration](../../concepts/rendering/ssr-hydration.md)
>
> **Time:** ~20 minutes to read; ~2 hours to retrofit an image-heavy
> page and measure the LCP improvement.

---

## The scenario

Lighthouse LCP: 4.8 seconds. The Performance panel shows the culprit — the hero image on your homepage is 2.1MB. It's a JPEG. Users on 4G wait 4+ seconds before seeing content. Conversion rates suffer.

The image needs to be:

- **Sized correctly** for the display (not 4K delivered to a 400px viewport)
- **In a modern format** (WebP/AVIF cuts size 30-50% vs JPEG)
- **Prioritized in the browser** (`fetchpriority="high"`) so the browser downloads it first
- **Preloaded** so the download starts before the JS parses
- **Reserving layout space** so the page doesn't jump when it arrives (no CLS)

Doing this by hand — writing `<picture>` elements with `srcset` for each breakpoint, converting to WebP with a build tool, adding preload tags, matching CSS aspect ratios — is fiddly and easy to get wrong. Angular's `NgOptimizedImage` directive does most of it declaratively; a CDN with format negotiation covers the rest.

The recipe walks through the setup, the LCP-critical patterns, and the debugging story when things don't optimize as expected.

---

## The `NgOptimizedImage` directive

Import from `@angular/common` (standalone-friendly since v14):

```typescript
import { NgOptimizedImage } from '@angular/common';

@Component({
  imports: [NgOptimizedImage],
  template: `
    <img
      ngSrc="/assets/hero.jpg"
      alt="Product hero"
      width="1200"
      height="600"
      priority
    />
  `,
})
export class HomePageComponent {}
```

**Four things doing the work:**

- **`ngSrc` instead of `src`** — opts into the directive. Without `ngSrc`, the directive doesn't apply; the image is just a regular `<img>`.
- **`width` and `height` are REQUIRED** — the directive throws if they're missing. They set the intrinsic aspect ratio; the browser can reserve layout space before the image loads → no CLS.
- **`priority` attribute for above-the-fold images** — adds `fetchpriority="high"` and `loading="eager"`. Tells the browser this image is LCP-critical.
- **Automatic `loading="lazy"` on non-priority images** — anything without `priority` gets lazy-loaded by default. Below-the-fold images don't compete with critical resources.

### The width / height mystery

The `width` and `height` are **not the CSS display size**. They're the intrinsic dimensions used for aspect-ratio calculation and layout reservation. CSS controls the actual displayed size:

```html
<img
  ngSrc="/assets/hero.jpg"
  alt="…"
  width="1200"     ← intrinsic width (aspect ratio calc)
  height="600"     ← intrinsic height
  style="width: 100%; max-width: 800px; height: auto;"   ← displayed size via CSS
/>
```

The browser sees width:height as 2:1, reserves that aspect ratio in layout, then applies CSS for actual size. When the image loads, no reflow.

**Rules of thumb:**

- Use the original image's natural dimensions for `width` and `height`.
- Never omit them (the directive throws NG02952 in dev mode).
- CSS is where you control display size responsively.

### The `fill` attribute (for hero images)

For images that fill their container — hero banners, card images, backgrounds behind text — the natural dimensions don't matter:

```html
<div class="hero-container">
  <img
    ngSrc="/assets/hero.jpg"
    alt="…"
    fill
    priority
    style="object-fit: cover;"
  />
</div>

<style>
.hero-container {
  position: relative;
  width: 100%;
  height: 400px;   /* parent needs explicit dimensions */
}

img[fill] {
  position: absolute;  /* the directive handles this */
  object-fit: cover;
}
</style>
```

**Two things worth absorbing:**

- **`fill` mode uses `position: absolute` inside the parent** — the parent must be `position: relative` (or absolute, sticky, fixed).
- **The parent must have explicit dimensions** — otherwise both parent and image try to size to each other, layout collapses to zero.

Use `fill` for containers with dynamic content; use explicit `width`/`height` for images with known dimensions.

---

## Priority images and LCP

The single highest-impact change: **mark your LCP image with `priority`**. Almost always one image per page — the hero, the product photo, the article's cover.

```html
<!-- Above the fold — priority -->
<img ngSrc="/hero.jpg" width="1200" height="600" priority alt="…" />

<!-- Below the fold — no priority; lazy-loaded automatically -->
<img ngSrc="/testimonial-1.jpg" width="400" height="400" alt="…" />
<img ngSrc="/testimonial-2.jpg" width="400" height="400" alt="…" />
```

**What `priority` does under the hood:**

1. Sets `fetchpriority="high"` on the `<img>` — the browser prioritizes it over other resources
2. Sets `loading="eager"` — no lazy-loading behavior
3. Injects a `<link rel="preload" as="image">` into the `<head>` — the browser starts downloading before parsing the page's JS
4. When an image loader is configured, preloads the responsive variant (from the srcset) that the current viewport would use

**Rules for priority:**

- **1-2 priority images per page**, not more. Marking everything as priority means nothing is priority (browser can't prioritize among 20 things).
- **Only above-the-fold images** — anything the user has to scroll to see shouldn't be priority.
- **Usually just the LCP element** — the biggest image visible on first paint.

The directive warns (**NG02955**) if it detects an LCP element that doesn't have priority. It also warns (**NG02956**) if there are too many priority images.

---

## Image loaders — the responsive image win

Without an image loader, `ngSrc` fetches the image as-is. Every viewport downloads the same file. Mobile users get a 1200px-wide image that displays at 400px.

**With an image loader**, the directive generates a `srcset` at multiple widths, and the browser picks the appropriate one. The loader is a URL-generator function: given a source path and a width, it returns the URL for that width.

### Built-in loaders

For popular CDNs:

```typescript
// File: app.config.ts
import { ApplicationConfig } from '@angular/core';
import {
  provideCloudinaryLoader,
  provideImgixLoader,
  provideImageKitLoader,
  provideCloudflareLoader,
  provideNetlifyLoader,
} from '@angular/common';

export const appConfig: ApplicationConfig = {
  providers: [
    // Pick ONE based on your CDN
    provideCloudinaryLoader('https://res.cloudinary.com/your-cloud'),
    // provideImgixLoader('https://your-app.imgix.net'),
    // provideImageKitLoader('https://ik.imagekit.io/your-account'),
    // provideCloudflareLoader('https://your-account.cloudflare.com'),
  ],
};
```

Now `<img ngSrc="hero.jpg" width="1200" height="600" priority />` generates:

```html
<img
  src="https://res.cloudinary.com/your-cloud/image/upload/f_auto,q_auto,w_1200/hero.jpg"
  srcset="
    https://.../w_640/hero.jpg 640w,
    https://.../w_750/hero.jpg 750w,
    https://.../w_828/hero.jpg 828w,
    https://.../w_1080/hero.jpg 1080w,
    https://.../w_1200/hero.jpg 1200w
  "
  sizes="100vw"
  fetchpriority="high"
  loading="eager"
  ...
/>
```

The `f_auto` in the URL tells Cloudinary to negotiate format — the browser announces support for WebP/AVIF via `Accept` header; the CDN serves the best format. **You upload one JPEG; users get the best available format for their browser.**

### Custom loader

For a custom CDN or an in-house image server:

```typescript
// File: image-loader.ts
import { ImageLoaderConfig } from '@angular/common';

export function customImageLoader(config: ImageLoaderConfig): string {
  // config.src         = the ngSrc value (e.g., "hero.jpg")
  // config.width       = the responsive-srcset width (undefined for the base <img src>)
  // config.loaderParams = optional per-usage params

  const baseUrl = 'https://cdn.mysite.com/images';
  const width = config.width ?? 'auto';

  // Format negotiation via query param your CDN supports
  const format = config.loaderParams?.['format'] ?? 'auto';

  // Quality tuning per usage
  const quality = config.loaderParams?.['quality'] ?? 80;

  return `${baseUrl}/${config.src}?w=${width}&f=${format}&q=${quality}`;
}
```

```typescript
// File: app.config.ts
import { IMAGE_LOADER } from '@angular/common';
import { customImageLoader } from './image-loader';

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: IMAGE_LOADER, useValue: customImageLoader },
  ],
};
```

Per-usage overrides via `loaderParams`:

```html
<img
  ngSrc="hero.jpg"
  width="1200"
  height="600"
  priority
  [loaderParams]="{ quality: 95, format: 'avif' }"
/>
```

Higher quality for the LCP image; use standard settings elsewhere.

---

## Responsive `sizes` for accurate srcset selection

The browser uses `sizes` to pick which srcset entry to download. Default is `100vw` (image is as wide as the viewport). Set it explicitly when the image doesn't fill the viewport:

```html
<!-- Card image inside a 3-column layout -->
<img
  ngSrc="/product.jpg"
  width="400"
  height="400"
  alt="…"
  sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
/>
```

The `sizes` attribute reads: "at ≥1024px viewport, the image is 33% of viewport width; at ≥640px, 50%; below that, 100%." The browser picks the smallest srcset entry that satisfies the layout.

Without accurate `sizes`, the browser assumes `100vw` and downloads oversized images for constrained layouts. On a 1400px desktop showing a 3-column grid where each column is ~400px, the browser would download a 1200w image instead of a 640w one. 3x the bandwidth for no visual improvement.

**Rules:**

- **Set `sizes` for any image that isn't full-viewport.**
- Match the media queries in your responsive CSS.
- The directive doesn't warn about missing `sizes` (yet); this is a manual optimization.

---

## Blur-up placeholders

The `placeholder` attribute enables a low-quality image placeholder while the full image loads:

```html
<img
  ngSrc="/hero.jpg"
  width="1200"
  height="600"
  priority
  placeholder
  alt="…"
/>
```

**How it works** (with an image loader):

1. Directive requests a small blurred version via the loader (`w=30`)
2. Renders the tiny image with CSS filter blur
3. When the full image loads, fades in
4. If no loader, uses a solid-color placeholder based on the image's implicit color hints

Trade-off: an extra tiny request (5-10KB). For LCP-critical images, the perceived-performance win is real — the user sees content immediately, then quality improves.

**For LCP images**: yes, use placeholder. The blurred preview counts as visible content for Lighthouse purposes; LCP measures the actual paint of the largest text/image, which happens when the full image arrives, but users perceive the placeholder as "loading" not "broken."

**For non-LCP images**: probably don't. The extra request cost exceeds the visual win.

### Custom placeholder — LQIP as base64

For finer control, provide your own base64-encoded placeholder:

```html
<img
  ngSrc="/hero.jpg"
  width="1200"
  height="600"
  priority
  [placeholder]="lqipDataUrl"
/>
```

```typescript
readonly lqipDataUrl = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAA...';
```

Common workflow: generate LQIP at build time (via a script or CDN feature); embed the base64 in the response; the placeholder appears instantly with no network request.

---

## Below-the-fold — lazy loading composes with `@defer`

Non-priority images get `loading="lazy"` automatically. The browser doesn't download them until they scroll near the viewport. This is table-stakes optimization.

For entire image-heavy sections that shouldn't load at all until visible, combine with `@defer`:

```html
<header>...</header>
<main>
  <!-- Above-the-fold: renders immediately with priority image -->
  <section class="hero">
    <img ngSrc="/hero.jpg" width="1200" height="600" priority alt="…" />
  </section>

  <!-- Below-the-fold: entire section deferred -->
  @defer (on viewport) {
    <section class="gallery">
      @for (photo of photos(); track photo.id) {
        <img
          [ngSrc]="photo.url"
          [width]="photo.width"
          [height]="photo.height"
          [alt]="photo.alt"
          sizes="(min-width: 1024px) 33vw, 50vw"
        />
      }
    </section>
  }
</main>
```

The gallery's component code AND its images only load when the section scrolls into view. Neither the JS bundle nor the image bandwidth is spent for users who never scroll.

Composes with [`@defer` in the bundle-splitting recipe](./bundle-splitting-strategies.md#strategy-2--defer-blocks-for-below-the-fold).

---

## Background images — the alternative pattern

`NgOptimizedImage` doesn't work with CSS `background-image: url(...)`. If your hero uses `background-image`, you don't get automatic srcset, priority, or preload.

**Two options:**

### Option 1 — convert to an `<img>` with absolute positioning

```html
<div class="hero-container">
  <img
    ngSrc="/hero-bg.jpg"
    fill
    priority
    alt=""
    style="object-fit: cover; z-index: -1;"
  />
  <div class="hero-content">
    <h1>Welcome</h1>
    <p>...</p>
  </div>
</div>

<style>
.hero-container {
  position: relative;
  width: 100%;
  height: 500px;
}

.hero-content {
  position: relative;
  z-index: 1;
  padding: 60px;
}
</style>
```

The image sits behind (`z-index: -1`); the content sits above. Semantically an `img`; visually a background. Now you get all the `NgOptimizedImage` benefits.

**Downside**: extra DOM element. For truly decorative images with `alt=""`, screen readers ignore them; no accessibility loss.

### Option 2 — manual `<link rel="preload">` for background images

If you must use CSS `background-image` (existing design system, complex CSS interactions), add a manual preload:

```typescript
// In your route component's constructor or via SSR
inject(Meta).addTags([
  {
    rel: 'preload',
    as: 'image',
    href: '/assets/hero-bg.webp',
    type: 'image/webp',
  },
]);
```

The browser downloads the image before parsing the CSS that references it. Faster LCP, but you lose responsive srcset — the CSS applies the same background regardless of viewport.

For most sites, converting to `<img>` (Option 1) is worth the DOM change.

---

## Debugging — the NG02xxx warnings

The directive emits development-mode warnings when it detects suboptimal usage. Look in the Chrome console for warnings prefixed with `NG02`:

| Warning | Meaning | Fix |
| --- | --- | --- |
| **NG02952** | Image missing intrinsic dimensions | Add `width` and `height` attributes |
| **NG02955** | LCP element doesn't have `priority` | Add `priority` to the LCP image |
| **NG02956** | Too many priority images | Remove `priority` from below-the-fold images |
| **NG02960** | Image is oversized (natural size >> displayed size) | Serve a smaller variant; check `sizes` attribute |
| **NG02961** | Distorted aspect ratio (displayed proportions differ significantly from intrinsic) | Fix CSS or update `width`/`height` |
| **NG02951** | `srcset` is misconfigured | Check custom loader implementation |

The warnings only fire in development builds. Production builds strip them (they're inside `ngDevMode` checks). Fix them during development; ignore in production monitoring.

**The oversized-image warning (NG02960) is the highest-value one.** It tells you when the browser is downloading a 2MB image to display it at 400px. Almost always an easy win — resize the source, or set `sizes` correctly, or check that your image loader is generating URLs for the responsive widths.

---

## Images inside virtual scroll

The [virtual scrolling recipe](../components/virtual-scrolling.md) handles rendering only visible items. What about images inside virtualized rows?

```html
<cdk-virtual-scroll-viewport itemSize="80" class="viewport">
  <div *cdkVirtualFor="let product of products(); trackBy: trackById" class="row">
    <img
      [ngSrc]="product.thumbnailUrl"
      width="64"
      height="64"
      [alt]="product.name"
      sizes="64px"
    />
    <span>{{ product.name }}</span>
  </div>
</cdk-virtual-scroll-viewport>
```

**Two things worth absorbing:**

- **No `priority` inside virtual scroll** — items rendered inside the viewport don't count as LCP-critical (they change as the user scrolls). Priority would preload images the user may never see.
- **Fixed `sizes` value** (`sizes="64px"`) — thumbnails are the same size regardless of viewport. Tells the browser to fetch only the smallest srcset entry.

The directive doesn't clash with virtual scrolling — CDK handles which rows render; the directive handles how images within rows load. They compose naturally.

---

## Trade-offs and common pitfalls

**Use `NgOptimizedImage` when:**

- The app has ≥1 image that shows above the fold on initial route
- LCP metrics matter (marketing pages, e-commerce, media sites)
- The team can adopt a small syntax change (`src` → `ngSrc`) across templates

**Skip when:**

- The app has no critical images (dashboards, admin tools with mostly text/tables)
- All images are decorative CSS backgrounds and rewriting them to `<img>` isn't feasible
- The team can't provide `width`/`height` for every image (some legacy setups)

### Common pitfalls

- **Missing `width` and `height`.** The directive throws in dev mode; production silently misbehaves (CLS jumps). Always provide them.
- **Using original 4K dimensions for `width`/`height`.** These are for aspect ratio, not delivered size. Match the natural dimensions of the source image, not what you want to display.
- **Marking every image as `priority`.** Browser can't prioritize among 20 priority images. 1-2 per page maximum.
- **Missing `sizes` for non-full-width images.** Browser assumes 100vw and downloads oversized variants. Set `sizes` for constrained-width images.
- **Forgetting to configure an image loader.** Without a loader, `ngSrc` fetches the raw URL — no responsive srcset, no format negotiation. The `priority` and `loading="lazy"` benefits still work, but the biggest wins (responsive + WebP/AVIF) are gone.
- **Custom loader not handling the `undefined` width case.** The base `src` attribute (no width) is used when `srcset` isn't applicable (some browsers, some contexts). Return a sensible URL for that case.
- **`fill` mode without a positioned parent.** The image sizes to zero. Parent must have `position: relative` and explicit dimensions.
- **Data URLs / base64 for large images.** They inflate the JS/HTML bundle, don't cache separately, and can't be responsive. Only use for tiny (< 5KB) images or LQIP placeholders.
- **Priority images inside virtual scroll.** Preloads images the user may never see. Never priority in virtualized lists.
- **CSS `background-image` for LCP.** No preload, no srcset via the directive. Convert to `<img>` with `fill`, or add manual preload.
- **Preloading below-the-fold images.** Waste of bandwidth and priority. Never priority images the user has to scroll to see.
- **Legacy `<picture>` element with `NgOptimizedImage`.** Redundant — the directive already handles srcset via the loader. Use one or the other, not both.
- **Ignoring the NG02960 oversized warning.** Almost always indicates a real bandwidth waste. Investigate every one that appears in dev mode.
- **`ng-src` (dash) vs `ngSrc` (camelCase).** Wrong — the correct attribute is `ngSrc` (camelCase). `ng-src` is a completely different, unrelated legacy AngularJS attribute.

---

## See also

- [Performance Auditing](./performance-auditing.md) — LCP diagnosis; this recipe is the tactical follow-up for image-driven LCP issues
- [Bundle Splitting Strategies](./bundle-splitting-strategies.md) — `@defer` blocks for below-the-fold sections including image galleries
- [SSR + Hydration](../ssr/ssr-hydration-deep-dive.md) — priority image preloading via `<link rel="preload">` composes with SSR; server-rendered pages benefit most from proper image priority
- [Virtual Scrolling](../components/virtual-scrolling.md) — images inside virtualized lists
- Components — standalone-imports for the directive

## References

- [`NgOptimizedImage` (angular.dev)](https://angular.dev/api/common/NgOptimizedImage) — the directive's full API
- [`IMAGE_LOADER` (angular.dev)](https://angular.dev/api/common/IMAGE_LOADER) — the loader injection token
- [Built-in loaders (angular.dev)](https://angular.dev/guide/image-optimization#configuring-an-image-loader-for-ngoptimizedimage) — Cloudinary, Imgix, ImageKit, Cloudflare, Netlify
- [Core Web Vitals — LCP (web.dev)](https://web.dev/articles/lcp) — the metric this recipe primarily improves
- [Priority Hints (web.dev)](https://web.dev/articles/fetch-priority) — the `fetchpriority` attribute behind `priority`
- [Responsive Images (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#responsive_images) — the underlying `srcset` + `sizes` mechanics
- [Cloudinary Image Optimization](https://cloudinary.com/documentation/image_optimization) — for CDN-side format negotiation

## Demo source

Synthesized from real-world Angular image-optimization patterns rather than a single demo file. The directive's LCP-focused defaults (auto lazy-load, srcset generation, preload for priority) make most image work "just works" — the recipe focuses on the edge cases (background images, virtual scroll, custom CDNs) that need manual attention. The NG02xxx warning table is the practical debugging shortcut most teams don't discover on their own. All code is original.
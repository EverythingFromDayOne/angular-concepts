---
recipe_id: "progress-tracking"
title: "Upload and Download Progress with HttpClient"
file: "recipes/http/progress-tracking.md"
primary_concept: "http/http"
related_concepts: ["reactivity/rxjs/rxjs", "reactivity/rxjs/rxjs-higher-order", "reactivity/signals", "reactivity/to-signal"]
demo_repo: "https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/self-rewrite-code"
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# Upload and Download Progress with `HttpClient`

> **What you'll build:** a reusable `trackProgress` RxJS operator that
> turns HttpClient's noisy event stream into a clean
> `{ status, progress, data }` shape — works for both uploads and
> downloads, handles servers that don't send `Content-Length`, and lets
> consumer components drive a progress bar in three lines.
>
> **Concepts you'll touch:** [HTTP](../../http/http.md), [RxJS](../../reactivity/rxjs/rxjs.md), [Higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md), [Signals](../../reactivity/signals.md)
>
> **Time:** ~15 minutes to read; ~30 minutes to integrate into an upload form.

---

## The scenario

A user uploads a 200MB video. The browser shows nothing for 90 seconds.
They reload the page, ask if the upload is broken, file a support
ticket. That's the experience without progress tracking. A progress bar
turns "is this broken?" into "I have 70 seconds left" — same wait,
fundamentally different feel.

HttpClient supports progress events natively, but the raw event stream
is verbose. To show a percentage, the consumer needs to filter to
just the progress events, calculate `loaded / total`, handle the
final response separately, and deal with servers that don't expose
content-length. The teaching moment is the operator that hides all of
that and exposes `{ status, progress, data }` instead.

## The Fetch vs XHR backend gap

Before we get to the operator, **the backend choice matters**. Angular
v22's default HTTP backend is **Fetch**, and **Fetch doesn't expose
upload progress events** — the browser's `fetch()` API just doesn't
have them. You can listen for download chunks via the response body's
`ReadableStream`, but for *uploads* the spec hasn't shipped a progress
hook to most browsers yet.

XHR (`XMLHttpRequest`) does expose upload progress via
`xhr.upload.onprogress`. Has done so since IE 8.

If your app needs upload progress, you must opt into the **XHR backend**:

```typescript
// app.config.ts
import { provideHttpClient, withXhr } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withXhr()),   // ← opt back into XHR for upload progress
  ],
};
```

`withXhr()` is the v22 escape hatch for the Fetch default. It exists
specifically for this case. The trade-off: server-side XHR was
deprecated in v22 and will be removed in v23, so this configuration
won't work for SSR-rendered routes that issue XHR uploads. In practice
uploads happen client-side from interactive routes, so this is rarely
the constraint that blocks you.

> **See also:** [HTTP](../../http/http.md) for the full Fetch/XHR
> transition timeline and the trade-offs of each backend.

**Download progress works on both backends** — Fetch can stream the
response body. So if you only need download progress (large file
downloads, paginated dataset streams), you can stay on the Fetch
default.

---

## The operator

The operator does two things: **filter** the event stream to only the
events we care about, and **map** each one to a clean state shape.

```typescript
// File: operators/track-progress.operator.ts
import { HttpEvent, HttpEventType, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { filter, map } from 'rxjs/operators';

// A clean shape for templates to consume — no HttpEventType union to switch on.
export interface ProgressResult<T> {
  status: 'uploading' | 'downloading' | 'completed';
  progress?: number;     // 0–100, or undefined when total is unknown
  loaded?: number;       // bytes loaded so far
  data?: T;              // populated only on 'completed'
}

export function trackProgress<T>() {
  return (source: Observable<HttpEvent<T>>): Observable<ProgressResult<T>> =>
    source.pipe(
      // 1. Narrow the event stream to just the three types we care about.
      filter(event =>
        event.type === HttpEventType.UploadProgress ||
        event.type === HttpEventType.DownloadProgress ||
        event.type === HttpEventType.Response,
      ),

      // 2. Project each event into the ProgressResult shape.
      map((event): ProgressResult<T> => {
        if (event.type === HttpEventType.UploadProgress) {
          return {
            status: 'uploading',
            progress: Math.round(100 * event.loaded / (event.total || 1)),
            loaded: event.loaded,
          };
        }

        if (event.type === HttpEventType.DownloadProgress) {
          return {
            status: 'downloading',
            // event.total may be undefined when the server omits Content-Length
            // (chunked encoding, streaming responses). Templates can show an
            // indeterminate progress bar in that case.
            progress: event.total
              ? Math.round(100 * event.loaded / event.total)
              : undefined,
            loaded: event.loaded,
          };
        }

        // Past the filter, not Upload/DownloadProgress — must be Response.
        // TypeScript can't narrow this far through the filter callback, so
        // we cast. Safe because of the upstream filter.
        return {
          status: 'completed',
          data: (event as HttpResponse<T>).body as T,
        };
      }),
    );
}
```

### Why the filter step matters

`HttpClient` with `observe: 'events'` emits **six** event types:

| `HttpEventType` | When |
| --- | --- |
| `Sent` | Request was sent to the server |
| `UploadProgress` | An upload-progress event fired |
| `ResponseHeader` | Response headers received (before body) |
| `DownloadProgress` | A download-progress event fired |
| `Response` | Full response (headers + body) received |
| `User` | Custom events from interceptors |

A consumer that just wants "show me a progress percentage" doesn't care
about `Sent`, `ResponseHeader`, or `User`. The filter narrows to the
three relevant types and lets the map function ignore the rest.

### Why the indeterminate-progress case matters

Look at the download branch:

```typescript
progress: event.total
  ? Math.round(100 * event.loaded / event.total)
  : undefined,
```

Returning `undefined` instead of a number is deliberate. Templates can
treat it as "indeterminate" and show a spinner or a striped progress
bar — the same way native `<progress>` does when its `value` attribute
is omitted.

This case fires more often than you'd expect:

- **Chunked transfer encoding** (`Transfer-Encoding: chunked`) — server
  doesn't know the total length, doesn't send `Content-Length`
- **Server-side streaming** — long-running endpoints that flush data
  as it's produced
- **CDN configurations** — some CDNs strip `Content-Length` for
  certain content types
- **Servers behind reverse proxies** that buffer responses

For uploads, `event.total` is almost always set (the browser knows
the size of the local file). For downloads, it's coin-flip.

### Why the `Response` case needs a cast

The filter allows three event types through; the `if` chain handles
two; therefore the third branch must be `Response`. TypeScript's
control-flow analysis can't carry the filter's discriminant down into
the `map` function — the filter callback returns a `boolean`, not a
type predicate. So we cast `event as HttpResponse<T>` at the end. Safe
because of the upstream guarantee, but worth knowing why the cast is
there and not a missing narrowing.

> **Bonus pattern:** if the cast irritates you, replace the filter
> callback with a **type predicate** (`event is HttpUploadProgressEvent
> \| HttpDownloadProgressEvent \| HttpResponse<T>`). TypeScript narrows
> through type predicates, so the cast inside the `map` goes away.
> The runtime behavior is identical; it's purely a type-system
> ergonomics thing.

---

## Step 1 — upload with progress

The consumer side. A file input, a progress bar, and the operator
turning HTTP events into UI state.

```typescript
// File: file-upload.component.ts
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { trackProgress, ProgressResult } from './operators/track-progress.operator';

@Component({
  selector: 'app-file-upload',
  template: `
    <input type="file" (change)="onFileSelected($event)" />

    @if (state(); as s) {
      @switch (s.status) {
        @case ('uploading') {
          <p>Uploading… {{ s.progress }}%</p>
          <progress [value]="s.progress" max="100"></progress>
        }
        @case ('completed') {
          <p>✅ Upload complete!</p>
          <pre>{{ s.data | json }}</pre>
        }
      }
    }
  `,
})
export class FileUploadComponent {
  private readonly http = inject(HttpClient);

  // Hold the latest progress state. signal() lets the template react
  // without subscribe/async-pipe ceremony.
  readonly state = signal<ProgressResult<UploadResponse> | null>(null);

  onFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    this.http.post<UploadResponse>('https://api.example.com/upload', formData, {
      reportProgress: true,         // tell HttpClient to emit progress events
      observe: 'events',            // give us the full event stream, not just the body
    }).pipe(
      trackProgress<UploadResponse>(),
      takeUntilDestroyed(),         // cancel the upload if the component is destroyed
    ).subscribe({
      next: (result) => this.state.set(result),
      error: (err) => console.error('Upload failed:', err),
    });
  }
}

interface UploadResponse { url: string; size: number; }
```

**Three things doing the work:**

- **`reportProgress: true`** is the opt-in. Without it, HttpClient doesn't
  emit `UploadProgress` events even if XHR could.
- **`observe: 'events'`** changes the return type from
  `Observable<UploadResponse>` to `Observable<HttpEvent<UploadResponse>>`.
  The operator expects the latter.
- **`takeUntilDestroyed()`** ensures the upload is cancelled if the user
  navigates away mid-upload. See the
  [companion recipe](../reactivity/take-until-destroyed.md) for the deep
  dive on `takeUntilDestroyed`.

### The template's three states

The `@switch` covers what the operator can emit. Notice there's no
`'downloading'` case here — uploads don't emit download-progress
events. If you want to handle a single component reused for both, add
the case; otherwise leaving it out is fine and TypeScript won't
complain.

---

## Step 2 — download with progress

The other direction. A large file (image, video, dataset) downloaded with
a progress bar so the user knows the page hasn't frozen.

```typescript
// File: file-download.component.ts
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { trackProgress, ProgressResult } from './operators/track-progress.operator';

@Component({
  selector: 'app-file-download',
  template: `
    <button (click)="startDownload()" [disabled]="state()?.status === 'downloading'">
      Download large file
    </button>

    @if (state(); as s) {
      @switch (s.status) {
        @case ('downloading') {
          @if (s.progress !== undefined) {
            <p>Downloading… {{ s.progress }}%</p>
            <progress [value]="s.progress" max="100"></progress>
          } @else {
            <!-- Server didn't send Content-Length — show bytes and a spinner -->
            <p>Downloading… {{ formatBytes(s.loaded) }}</p>
            <progress></progress>
          }
        }
        @case ('completed') {
          <p>✅ Downloaded {{ formatBytes(s.data?.size ?? 0) }}</p>
          <a [href]="objectUrl()" download="file.bin">Save to disk</a>
        }
      }
    }
  `,
})
export class FileDownloadComponent {
  private readonly http = inject(HttpClient);

  readonly state = signal<ProgressResult<Blob> | null>(null);
  readonly objectUrl = signal<string | null>(null);

  startDownload(): void {
    this.http.get('https://api.example.com/large-file', {
      reportProgress: true,
      observe: 'events',
      responseType: 'blob',         // we want a Blob, not parsed JSON
    }).pipe(
      trackProgress<Blob>(),
      takeUntilDestroyed(),
    ).subscribe({
      next: (result) => {
        this.state.set(result);
        if (result.status === 'completed' && result.data) {
          // URL.createObjectURL gives the browser a temporary URL for the blob.
          // The <a download> below lets the user save it.
          this.objectUrl.set(URL.createObjectURL(result.data));
        }
      },
      error: (err) => console.error('Download failed:', err),
    });
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}
```

**Things to absorb:**

- **`responseType: 'blob'`** — without it, HttpClient tries to parse the
  response as JSON and fails. For binary downloads always specify
  `'blob'`, `'arraybuffer'`, or `'text'` as appropriate.
- **The `progress === undefined` branch** — see indeterminate-progress
  discussion above. `<progress>` with no `value` attribute is the
  native HTML way to show an indeterminate state.
- **`URL.createObjectURL(blob)`** — gives the `<a download>` something
  to link to. For very large files (>500MB), consider revoking the URL
  with `URL.revokeObjectURL(url)` after the user clicks save, to free
  memory. The recipe omits this for clarity; a production component
  would handle it in a `DestroyRef.onDestroy()` callback.

---

## Variations

### Cancellation via button click

The current recipes use `takeUntilDestroyed` for "cancel if the
component goes away." For "cancel because the user clicked Cancel,"
add a Subject and `takeUntil`:

```typescript
import { Subject, takeUntil } from 'rxjs';

@Component({ /* ... */ })
export class FileUploadComponent {
  private readonly cancelUpload$ = new Subject<void>();
  // ...

  onFileSelected(event: Event): void {
    // ... build FormData
    this.http.post(/* ... */).pipe(
      trackProgress(),
      takeUntil(this.cancelUpload$),       // cancel on demand
      takeUntilDestroyed(),                // AND on component destroy
    ).subscribe(/* ... */);
  }

  cancel(): void {
    this.cancelUpload$.next();
  }
}
```

Both `takeUntil` operators are needed — they handle different cancellation
sources. The component template adds a `<button (click)="cancel()">`
that's only visible while uploading.

### Surfacing progress as a separate signal

If multiple components need to react to upload progress (a global header
indicator + the upload form), expose progress from a service:

```typescript
@Injectable({ providedIn: 'root' })
export class UploadService {
  private readonly http = inject(HttpClient);
  readonly currentUpload = signal<ProgressResult<unknown> | null>(null);

  upload<T>(url: string, formData: FormData): Observable<ProgressResult<T>> {
    return this.http.post<T>(url, formData, {
      reportProgress: true,
      observe: 'events',
    }).pipe(
      trackProgress<T>(),
      tap(result => this.currentUpload.set(result)),
    );
  }
}
```

Every consumer can read `uploadService.currentUpload()` to drive its own
UI. Components that initiate uploads `.subscribe()` to the returned
observable to get the result.

### Bytes-per-second indicator

Add elapsed-time tracking inside the operator (or in a small extension)
to compute throughput:

```typescript
import { scan } from 'rxjs/operators';

interface ProgressWithSpeed<T> extends ProgressResult<T> {
  bytesPerSecond?: number;
}

export function trackProgressWithSpeed<T>() {
  const startTime = Date.now();
  return (source: Observable<HttpEvent<T>>): Observable<ProgressWithSpeed<T>> =>
    source.pipe(
      trackProgress<T>(),
      map(result => {
        if (result.loaded !== undefined && result.status !== 'completed') {
          const elapsedSec = (Date.now() - startTime) / 1000;
          return {
            ...result,
            bytesPerSecond: elapsedSec > 0 ? result.loaded / elapsedSec : undefined,
          };
        }
        return result;
      }),
    );
}
```

Each call to `trackProgressWithSpeed()` captures its own `startTime` —
calling the factory once per upload gives accurate throughput.

---

## Trade-offs and when NOT to use this

**Use this pattern when:**

- Uploads are large enough that the user notices the wait (>5MB
  rule of thumb; smaller files complete before a progress bar would
  even render)
- Downloads are large enough or slow enough that the user wonders if
  the page is responsive
- You want one consistent progress UI across the app

**Reach for a different approach when:**

- **Upload is small** (form data, a few KB). Don't add progress for
  the sake of it — a loading spinner is enough, and the progress bar
  would flash to 100% before the user perceived it.
- **You need *resumable* uploads** (>1GB, unreliable connections).
  `HttpClient` doesn't support resume natively; you need either a
  multi-part upload protocol like S3's multipart, or a library like
  `tus-js-client`. Progress tracking is the simplest part of that
  story.
- **You're shipping to a strict-Fetch-only environment.** If you can't
  enable `withXhr()` (SSR-heavy app, strict CSP, deployment
  constraints), upload progress isn't available. Fall back to a
  "uploading…" message without a percentage.
- **The response is a stream you process incrementally.** For
  Server-Sent Events or chunked JSON streams, the operator's
  "wait for the Response event with full body" doesn't fit. Use
  `HttpClient.get(..., { observe: 'events' })` raw and handle
  `DownloadProgress` chunks as they arrive.

### Common pitfalls

- **Forgetting `reportProgress: true`** — silent failure. The events
  just don't fire; the operator never emits anything. Easy mistake;
  default to `true` in your service wrapper.
- **Using Fetch backend and wondering why upload progress doesn't
  work.** Check `app.config.ts` for `withXhr()`. The browser-level
  Fetch limitation is the most common source of "but the operator
  looks right" head-scratching.
- **Forgetting `responseType: 'blob'` for binary downloads.**
  HttpClient tries to parse as JSON, throws a SyntaxError on binary
  bytes. The operator never sees the `Response` event because the
  error fires upstream.
- **Not setting `Content-Type` for `FormData`** — actually a good
  thing. **Don't** set it manually for FormData; the browser sets it
  automatically with the right multipart boundary. Setting it to
  `multipart/form-data` without the boundary breaks the request.
- **Leaking object URLs.** `URL.createObjectURL(blob)` reserves
  memory; the browser only frees it when you call
  `URL.revokeObjectURL(url)` or close the page. For repeated
  downloads in a long-lived SPA, revoke when the user navigates away.
- **Trusting `progress` to be defined.** Always handle the `undefined`
  case for downloads. Templates that assume `progress` is a number
  produce broken bars on chunked-encoded responses.

---

## See also

- [HTTP](../../http/http.md) — the full HttpClient story, Fetch vs XHR backend choice, transfer cache
- [RxJS — higher-order operators](../../reactivity/rxjs/rxjs-higher-order.md) — `map`, `filter`, custom operator patterns
- [`takeUntilDestroyed`](../reactivity/take-until-destroyed.md) — the cleanup primitive used here, and the companion "custom operator" recipe
- [Signals](../../reactivity/signals.md) — `signal()` for component state
- [`HttpEvent` API (angular.dev)](https://angular.dev/api/common/http/HttpEvent) — the full event-type catalogue

## References

- [`HttpClient` request options (angular.dev)](https://angular.dev/api/common/http/HttpClient)
- [`withXhr()` API (angular.dev)](https://angular.dev/api/common/http/withXhr)
- [`HttpEventType` enum (angular.dev)](https://angular.dev/api/common/http/HttpEventType)
- [Fetch upload progress proposal (whatwg)](https://github.com/whatwg/fetch/issues/607) — long-running discussion on why Fetch still doesn't expose upload progress
- [`URL.createObjectURL` (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static) — and the importance of revoking when done
- [`FormData` (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/FormData) — multipart upload essentials

## Demo source

Adapted from [`AngularDemos/features/self-rewrite-code`](https://github.com/EverythingFromDayOne/AngularDemos/tree/development/apps/angular-demos/src/app/features/self-rewrite-code) — the `custom-operators/trackProgress.operator.ts` file. The companion `fetch-xhr.ts` (a custom XHR-based fetch wrapper) is out of scope for this recipe; for 95% of upload-progress cases, `provideHttpClient(withXhr())` from `@angular/common/http` is the right answer without needing a custom HTTP layer.
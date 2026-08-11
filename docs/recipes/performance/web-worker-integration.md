---
recipe_id: "web-worker-integration"
title: "Web Workers: Heavy Computation Without Freezing the UI"
file: "recipes/performance/web-worker-integration.md"
primary_concept: "components/components"
related_concepts: ["performance/performance-auditing", "reactivity/signals", "http/http"]
demo_repo: null
angular_baseline: "22"
difficulty: "advanced"
status:
  upgraded: true
  reviewed: false
---

# Web Workers: Heavy Computation Without Freezing the UI

> **What you'll build:** a Web Worker integration that runs
> CPU-heavy work off the main thread — CSV import that parses 100k
> rows without freezing the browser, PDF generation that doesn't
> block scrolling, image processing that runs in parallel. Raw
> `postMessage` protocol shown briefly, then Comlink for RPC-style
> ergonomics, progress reporting back to the UI, cancellation via
> terminate-and-respawn, worker pools for parallelism, and the
> Angular integration patterns (service wrappers, signal-based
> progress signals, clean shutdown on service destroy).
>
> **Concepts you'll touch:** Components, [Performance Auditing](./performance-auditing.md), [Signals](../../concepts/reactivity/signals.md), [HTTP](../../concepts/http/http.md)
>
> **Time:** ~30 minutes to read; ~1 day to add workers to a real
> feature with proper cancellation and cleanup.

---

## Web workers vs service workers — the constant confusion

Before code: these are unrelated features that share "worker" in their names.

| Feature | Service Worker | Web Worker |
| --- | --- | --- |
| **Purpose** | Network layer; offline; caching | Compute thread; runs JS off the main thread |
| **Lifetime** | Persists across page loads and tab closes | Only exists while the tab is open |
| **DOM access** | No | No |
| **Network** | Intercepts fetch events | Makes fetch calls |
| **Angular API** | `@angular/service-worker` | No specific API; native + Comlink |
| **Solves** | "App breaks when offline" | "App freezes during heavy computation" |

The [Service Worker recipe](../pwa/service-worker-offline-first.md) covers offline-first patterns. **This recipe is different** — it's about moving CPU-heavy JavaScript off the main thread so the UI stays responsive.

---

## The scenario

A user imports a 40MB CSV file into your admin panel. They click Import. The UI freezes for 6 seconds — no scrolling, no button response, the tab shows "Not Responding" on some browsers. When it thaws, the data has loaded.

You look at the code:

```typescript
onImport(file: File) {
  const text = await file.text();
  const rows = parseCsv(text);        // 5.5 seconds of blocking work
  this.processRows(rows);              // another 300ms
  this.showResults();
}
```

`parseCsv` runs synchronously on the main thread. While it runs, no other JavaScript can execute — no click handlers, no rendering, no `requestAnimationFrame`, no signals updating. The browser marks the tab as unresponsive.

The [performance-auditing recipe](./performance-auditing.md#symptom-4--slow-click--action) covers deferring work with `setTimeout(0)` — for short work, that suffices. For long work like CSV parsing, `setTimeout` doesn't help — the work still blocks when it eventually runs. The fix is **moving it to a Web Worker**, a separate thread where blocking work doesn't affect the main thread.

---

## Web worker basics

A Web Worker is a JavaScript file that runs in a separate thread. It has:

- **No DOM access** — no `document`, `window`, `HTMLElement`, or anything else UI-related
- **Its own global scope** — `self` refers to the worker itself
- **Access to `fetch`, `postMessage`, `setTimeout`, `console`** — most non-DOM APIs
- **Communication only via messages** — the main thread sends messages; the worker responds

### Scaffolding with the Angular CLI

Angular has a `ng generate web-worker` schematic:

```bash
ng generate web-worker csv-parser
```

This creates:

- `src/app/csv-parser.worker.ts` — the worker script
- Updates `tsconfig.worker.json` for worker-specific TypeScript config
- Updates `angular.json` with the worker build

Or manually, create the file and import it via URL syntax:

```typescript
// File: src/app/csv-parser.worker.ts
addEventListener('message', event => {
  const text: string = event.data;
  const rows = text.split('\n').map(line => line.split(','));
  postMessage(rows);
});
```

```typescript
// File: src/app/csv-parser.service.ts
@Injectable({ providedIn: 'root' })
export class CsvParserService {
  private readonly worker = new Worker(
    new URL('./csv-parser.worker', import.meta.url),
    { type: 'module' },
  );
}
```

The `new URL(..., import.meta.url)` syntax is what bundlers (esbuild in v17+) recognize as "this is a worker file; emit it as a separate bundle." Without this exact syntax, the bundler treats the string as a runtime path and things silently break.

---

## The raw `postMessage` pattern (and its pain)

The most basic worker communication — the main thread sends, the worker responds:

```typescript
// File: csv-parser.worker.ts
addEventListener('message', event => {
  const text: string = event.data;
  const rows = text.split('\n').map(line => line.split(','));
  postMessage(rows);
});
```

```typescript
// File: csv-parser.service.ts
@Injectable({ providedIn: 'root' })
export class CsvParserService {
  private readonly worker = new Worker(
    new URL('./csv-parser.worker', import.meta.url),
    { type: 'module' },
  );

  parse(text: string): Promise<string[][]> {
    return new Promise((resolve, reject) => {
      const handler = (event: MessageEvent) => {
        this.worker.removeEventListener('message', handler);
        this.worker.removeEventListener('error', errorHandler);
        resolve(event.data);
      };
      const errorHandler = (event: ErrorEvent) => {
        this.worker.removeEventListener('message', handler);
        this.worker.removeEventListener('error', errorHandler);
        reject(event.error);
      };
      this.worker.addEventListener('message', handler);
      this.worker.addEventListener('error', errorHandler);
      this.worker.postMessage(text);
    });
  }
}
```

**This works. It's also painful.** Every method needs a promise wrapper that adds and removes listeners. Multiple in-flight requests need request-IDs to route responses. Type safety is manual. Callbacks (like progress reports) require complex bidirectional messaging.

For anything nontrivial, use Comlink — a small library from the Chrome team that handles all of this.

---

## Pattern 1 — Comlink for RPC-style ergonomics

Comlink turns worker communication into method calls on a proxy object. Install:

```bash
npm install comlink
```

The worker exposes a class or object:

```typescript
// File: csv-parser.worker.ts
/// <reference lib="webworker" />
import * as Comlink from 'comlink';

class CsvParser {
  parse(text: string): string[][] {
    return text.split('\n').map(line => line.split(','));
  }

  async parseWithHeader(text: string): Promise<Record<string, string>[]> {
    const rows = text.split('\n').map(line => line.split(','));
    const headers = rows[0];
    return rows.slice(1).map(row => {
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => { obj[h] = row[i]; });
      return obj;
    });
  }
}

Comlink.expose(new CsvParser());
```

The service wraps it:

```typescript
// File: csv-parser.service.ts
import { Injectable, inject, DestroyRef, signal } from '@angular/core';
import * as Comlink from 'comlink';
import type { CsvParser } from './csv-parser.worker';

@Injectable({ providedIn: 'root' })
export class CsvParserService {
  private readonly destroyRef = inject(DestroyRef);
  private readonly worker = new Worker(
    new URL('./csv-parser.worker', import.meta.url),
    { type: 'module' },
  );
  private readonly proxy = Comlink.wrap<CsvParser>(this.worker);

  constructor() {
    this.destroyRef.onDestroy(() => this.worker.terminate());
  }

  parse(text: string): Promise<string[][]> {
    return this.proxy.parse(text);
  }

  parseWithHeader(text: string): Promise<Record<string, string>[]> {
    return this.proxy.parseWithHeader(text);
  }
}
```

Component usage:

```typescript
@Component({ /* … */ })
export class ImportComponent {
  private readonly parser = inject(CsvParserService);
  readonly rows = signal<Record<string, string>[]>([]);
  readonly parsing = signal(false);

  async onFileSelected(file: File): Promise<void> {
    this.parsing.set(true);
    try {
      const text = await file.text();
      const parsed = await this.parser.parseWithHeader(text);
      this.rows.set(parsed);
    } finally {
      this.parsing.set(false);
    }
  }
}
```

**Five things doing the work:**

- **`Comlink.expose(new CsvParser())`** in the worker publishes the object; Comlink handles the postMessage plumbing internally.
- **`Comlink.wrap<CsvParser>(worker)`** in the main thread returns a proxy that looks like the worker's class. Method calls on the proxy are RPC calls to the worker.
- **`import type { CsvParser }`** — types-only import; the worker code isn't included in the main bundle, but TypeScript checks that method signatures match.
- **Returns are Promises** — every worker call is async because it involves a postMessage round-trip. Even sync methods on the worker become async on the proxy.
- **`destroyRef.onDestroy(() => this.worker.terminate())`** — clean shutdown when the service is destroyed. For `providedIn: 'root'` services this runs on app shutdown; for subtree-scoped services on component destroy. Always terminate — un-terminated workers leak.

The type-safety win is significant: rename a method on the worker, the compiler flags the service that calls it. No runtime "unknown method 'parse'" errors.

---

## Pattern 2 — progress reporting from workers

For long-running work, the UI wants updates: "45% complete, 30 seconds remaining." Comlink's `Comlink.proxy` wraps callbacks so they can be passed to the worker and invoked back:

```typescript
// File: csv-parser.worker.ts
class CsvParser {
  async parseWithProgress(
    text: string,
    onProgress: (percent: number) => void,
  ): Promise<Record<string, string>[]> {
    const lines = text.split('\n');
    const total = lines.length;
    const headers = lines[0].split(',');
    const results: Record<string, string>[] = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      const obj: Record<string, string> = {};
      headers.forEach((h, idx) => { obj[h] = values[idx]; });
      results.push(obj);

      // Report progress every 1000 rows
      if (i % 1000 === 0) {
        onProgress(Math.round((i / total) * 100));
      }
    }

    onProgress(100);
    return results;
  }
}

Comlink.expose(new CsvParser());
```

The main-thread call wraps the callback with `Comlink.proxy`:

```typescript
@Injectable({ providedIn: 'root' })
export class CsvParserService {
  // …existing setup…

  readonly progress = signal(0);
  readonly parsing = signal(false);

  async parseWithProgress(text: string): Promise<Record<string, string>[]> {
    this.parsing.set(true);
    this.progress.set(0);
    try {
      const result = await this.proxy.parseWithProgress(
        text,
        Comlink.proxy((pct: number) => this.progress.set(pct)),
      );
      return result;
    } finally {
      this.parsing.set(false);
    }
  }
}
```

Component:

```html
@if (parser.parsing()) {
  <div class="progress-bar">
    <div [style.width.%]="parser.progress()"></div>
  </div>
  <p>{{ parser.progress() }}% complete</p>
}
```

**Three things worth absorbing:**

- **`Comlink.proxy(callback)`** wraps a function so Comlink can transfer it across the worker boundary. Without the wrapper, functions can't cross (they're not structured-cloneable).
- **The callback runs in the main thread**, not the worker. When the worker invokes `onProgress(50)`, Comlink posts a message; the main thread's proxy'd version fires, updating the signal.
- **Signal updates from the callback work reactively** — the progress bar re-renders automatically. The worker doesn't need to know anything about signals or DOM.

### Reporting granularity

Reporting every row would flood the main thread with messages (`postMessage` has overhead — a few microseconds per call, adds up over 100k rows). Report at intervals: every 1000 rows for a 100k-row file, or every 5% for a smaller one. Rule of thumb: 20-50 progress updates over the whole operation is enough for smooth UI feedback.

---

## Pattern 3 — cancellation via terminate + respawn

Web workers don't have a native `AbortController` equivalent. The two approaches:

### Approach A — terminate and respawn (simple)

```typescript
@Injectable({ providedIn: 'root' })
export class CsvParserService {
  private worker: Worker | null = null;
  private proxy: Comlink.Remote<CsvParser> | null = null;

  private spawnWorker(): void {
    this.worker = new Worker(
      new URL('./csv-parser.worker', import.meta.url),
      { type: 'module' },
    );
    this.proxy = Comlink.wrap<CsvParser>(this.worker);
  }

  constructor() {
    this.spawnWorker();
    inject(DestroyRef).onDestroy(() => this.worker?.terminate());
  }

  async parse(text: string): Promise<string[][]> {
    if (!this.proxy) throw new Error('Worker not available');
    return this.proxy.parse(text);
  }

  cancel(): void {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
      this.proxy = null;
      this.spawnWorker();  // fresh worker ready for next call
    }
  }
}
```

**Terminate kills the worker mid-computation.** Any in-flight promises are abandoned (they never resolve or reject — memory leaks if you're not careful). The respawn creates a new worker ready for the next call.

**Handle the abandoned-promise problem** by tracking pending promises and rejecting them on terminate:

```typescript
private pendingRejects: Array<(err: Error) => void> = [];

async parse(text: string): Promise<string[][]> {
  return new Promise(async (resolve, reject) => {
    this.pendingRejects.push(reject);
    try {
      const result = await this.proxy!.parse(text);
      resolve(result);
    } catch (err) {
      reject(err);
    } finally {
      const idx = this.pendingRejects.indexOf(reject);
      if (idx >= 0) this.pendingRejects.splice(idx, 1);
    }
  });
}

cancel(): void {
  for (const reject of this.pendingRejects) {
    reject(new Error('CANCELLED'));
  }
  this.pendingRejects = [];

  if (this.worker) {
    this.worker.terminate();
    this.spawnWorker();
  }
}
```

Callers `catch` the `CANCELLED` error and treat it as a non-event (not a failure toast).

### Approach B — cooperative cancellation (advanced)

For workers that support it, pass a shared cancellation flag via `SharedArrayBuffer`:

```typescript
// Main thread
const cancelFlag = new SharedArrayBuffer(1);
const cancelView = new Uint8Array(cancelFlag);

// Pass to worker
proxy.parseWithCancel(text, Comlink.transfer(cancelFlag, [cancelFlag]));

// To cancel:
cancelView[0] = 1;
```

```typescript
// Worker
class CsvParser {
  async parseWithCancel(text: string, cancelFlag: SharedArrayBuffer): Promise<any[]> {
    const view = new Uint8Array(cancelFlag);
    for (const row of rows) {
      if (view[0] === 1) throw new Error('CANCELLED');
      // …process row…
    }
  }
}
```

**Advantages**: worker stays alive; no respawn cost. **Disadvantages**: `SharedArrayBuffer` requires cross-origin isolation (`Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy` headers); some deployments can't set them. Only use when you need it.

For most apps, **terminate + respawn (Approach A) is enough.**

---

## Pattern 4 — worker pools for parallel work

For processing many independent items (100 images, 1000 documents), running them in one worker is serial. A pool of N workers processes N items in parallel:

```typescript
// File: worker-pool.ts
import * as Comlink from 'comlink';

export class WorkerPool<T> {
  private readonly workers: Array<Comlink.Remote<T>> = [];
  private readonly available: Array<Comlink.Remote<T>> = [];
  private readonly waiting: Array<(worker: Comlink.Remote<T>) => void> = [];

  constructor(
    workerFactory: () => Worker,
    poolSize: number = Math.max(1, navigator.hardwareConcurrency - 1),
  ) {
    for (let i = 0; i < poolSize; i++) {
      const w = workerFactory();
      const proxy = Comlink.wrap<T>(w);
      this.workers.push(proxy);
      this.available.push(proxy);
    }
  }

  async run<R>(task: (worker: Comlink.Remote<T>) => Promise<R>): Promise<R> {
    const worker = await this.acquire();
    try {
      return await task(worker);
    } finally {
      this.release(worker);
    }
  }

  private acquire(): Promise<Comlink.Remote<T>> {
    if (this.available.length > 0) {
      return Promise.resolve(this.available.pop()!);
    }
    return new Promise(resolve => this.waiting.push(resolve));
  }

  private release(worker: Comlink.Remote<T>): void {
    if (this.waiting.length > 0) {
      const next = this.waiting.shift()!;
      next(worker);
    } else {
      this.available.push(worker);
    }
  }

  terminate(): void {
    for (const worker of this.workers) {
      (worker as any)[Comlink.releaseProxy]();
    }
    this.workers.length = 0;
    this.available.length = 0;
    this.waiting.length = 0;
  }
}
```

Usage:

```typescript
@Injectable({ providedIn: 'root' })
export class BatchImageProcessor {
  private readonly pool = new WorkerPool<ImageProcessor>(
    () => new Worker(new URL('./image-processor.worker', import.meta.url), { type: 'module' }),
    4,  // 4 parallel workers
  );

  constructor() {
    inject(DestroyRef).onDestroy(() => this.pool.terminate());
  }

  async processAll(images: ImageData[]): Promise<Blob[]> {
    return Promise.all(
      images.map(img =>
        this.pool.run(worker => worker.process(img)),
      ),
    );
  }
}
```

**Three things worth absorbing:**

- **`navigator.hardwareConcurrency - 1`** as default pool size — leave one core for the main thread. On a 4-core device, use 3 workers.
- **`acquire` / `release` semantics** — the pool serializes across a fixed number of workers. `Promise.all` on the tasks fires them all at once, but the pool queues them across N workers.
- **`Comlink.releaseProxy`** cleans up Comlink's internal tracking. Combined with `worker.terminate()` (which the underlying `Comlink.wrap` doesn't do — you'd need to hold the original worker reference), it's the full cleanup.

---

## Angular-specific limitations

Web workers don't have access to Angular's DI system. This has implications:

### Cannot inject services

`inject()` doesn't work in workers. The worker has no NgModule, no root injector, no providers. If your heavy computation needs services, you have two options:

1. **Pass the data via method arguments** — call the worker method with plain data; the worker computes on it; returns plain data. No DI needed.
2. **Duplicate small utilities** — pure functions that don't need DI can be copied into the worker file.

For HTTP calls from a worker, use `fetch` directly:

```typescript
class DataFetcher {
  async fetchAndProcess(url: string): Promise<Result> {
    const response = await fetch(url);
    const data = await response.json();
    return this.process(data);
  }
}
```

No `HttpClient`, no interceptors. If you need interceptor behavior (auth headers, retry logic), replicate what you need in the worker.

### Signals don't cross the boundary

Signals are Angular-specific reactivity primitives; the worker doesn't have Angular's runtime. **Don't try to pass signals to workers**. Pass the current value (`this.myData()`), receive updates as method return values or callback invocations.

### Async pipes and template subscriptions

Templates can subscribe to the worker's progress via signal updates (as shown above), but the signal lives in the service (main thread), not the worker. The worker's callbacks update the signal; the template re-renders reactively.

### Router, HttpClient, Forms — not available

Any Angular service that needs the injector is out. This is usually fine — heavy computation shouldn't be tangled with Router state or Form values. Pass the data in, get the result out.

---

## When to reach for a Web Worker

The right tool for the right job:

| Situation | Worker? |
| --- | --- |
| Parsing large data (CSV/JSON >10MB) | ✅ Yes — sync parsing blocks for seconds |
| Image processing (resize, filter, convert) | ✅ Yes — pixel manipulation is CPU-bound |
| PDF generation from JSON | ✅ Yes — layout calculation blocks the UI |
| Cryptographic operations | ✅ Yes — hashing, encryption are slow |
| Complex regex over large text | ✅ Yes — backtracking can freeze the tab |
| Compression / decompression | ✅ Yes — zip, gzip, brotli operations |
| Client-side ML inference | ✅ Yes — model runs can take seconds |
| Physics or animation calculations | ✅ Yes — off-main-thread keeps 60 FPS |
| Small computations (<10ms) | ❌ No — `postMessage` overhead exceeds win |
| DOM manipulation | ❌ Impossible — workers have no DOM |
| Latency-sensitive input (typing) | ❌ No — round-trip adds delay |
| API-response-transform (already async) | ❌ Usually no — RxJS pipes are fine |

**Rule of thumb**: if a single synchronous operation blocks the main thread for >100ms, it's a candidate. Under 50ms, don't bother — the postMessage cost eats the win.

---

## Debugging web workers

Web workers have their own context in Chrome DevTools:

1. Open DevTools → **Sources** tab
2. In the left sidebar, look for the **Threads** section (may need to expand)
3. Workers appear as separate entries; click one to switch context
4. Now the console, breakpoints, and profiler apply to the worker

**Console messages from workers** show up in the main console with a `[worker]` prefix (depending on browser). Sourcemap-linked stack traces work if your build emits worker sourcemaps.

**Common issue**: worker errors go silently unnoticed. Add an error listener:

```typescript
this.worker.addEventListener('error', event => {
  console.error('Worker error:', event.message, event.filename, event.lineno);
});
```

Without it, workers can crash and you'd never see the error in the console.

---

## Trade-offs and common pitfalls

**Use Web Workers when:**

- Single synchronous operation blocks the main thread for >100ms
- The work is genuinely computational (not I/O-bound; async I/O doesn't block)
- You can pass data in and receive data out (no DOM dependencies)

**Skip when:**

- The work is <50ms; postMessage overhead exceeds the win
- The work is I/O-bound (already async; workers add complexity for no gain)
- You need DOM access or Angular DI (worker can't provide either)
- Simpler options work: `setTimeout(fn, 0)` for chunking, `requestIdleCallback` for background work, virtual scrolling for rendering

### Common pitfalls

- **`new Worker('./worker.js')` without the `new URL(...)` wrapper.** Bundlers don't recognize the plain string as a worker import; the file isn't emitted; runtime fails. Always use `new URL('./worker', import.meta.url)`.
- **Forgetting `{ type: 'module' }`.** Without it, the worker script is treated as a classic (non-module) script; `import` statements don't work. Modern workers should always be modules.
- **Not terminating on service destroy.** Un-terminated workers leak — the browser holds them (and their memory) forever. Always `worker.terminate()` in a cleanup handler.
- **Callbacks without `Comlink.proxy`.** Passing a bare function to a Comlink method silently fails; the worker never invokes it. Wrap with `Comlink.proxy(callback)`.
- **Serialization cost for large data.** Passing a 40MB CSV as a string via `postMessage` costs ~50ms — the browser has to structured-clone it. For very large transfers, use `Transferable` objects (ArrayBuffer, MessagePort) which transfer ownership rather than copying.
- **Reporting progress too often.** Every `postMessage` costs a few microseconds; 100k calls to `onProgress` from a tight loop can itself become the bottleneck. Report at intervals (every 1000 items, or 5% steps).
- **Assuming DOM APIs work.** `document`, `window`, `alert`, `HTMLElement` — none exist in workers. `console`, `setTimeout`, `fetch` do. If you copy code from main-thread into a worker, audit for DOM references.
- **`inject()` in worker code.** Fails silently — the worker has no Angular injector. Pass what you need as method arguments.
- **Terminate + respawn overhead in tight loops.** Each spawn costs ~50-100ms. Don't terminate for every operation; hold the worker alive across many calls.
- **Cross-origin isolation for SharedArrayBuffer.** Requires COOP + COEP headers. Many hosting setups don't set them by default. For cooperative cancellation via SharedArrayBuffer, verify your headers first.
- **Nested workers.** Workers can spawn other workers, but the tree gets confusing fast. For most needs, a flat pool is simpler.
- **Assuming worker throughput scales linearly.** 4 workers rarely means 4x throughput — cores share L3 cache, memory bandwidth, and OS scheduling. Measure; don't assume.
- **Type imports pulling worker code into main bundle.** `import { HeavyProcessor } from './worker'` (without `type`) can include the worker's implementation. Always `import type` for worker classes referenced only for typing.
- **Console.log inside a tight loop in a worker.** Console messages cross the postMessage boundary; a million `console.log`s in a worker is a million postMessages. Strip debug logging before production.

---

## See also

- [Performance Auditing](./performance-auditing.md) — Symptom 4 (slow click → action) diagnosis; this recipe is the fix for CPU-bound cases
- [Service Worker + Offline-First](../pwa/service-worker-offline-first.md) — the OTHER kind of worker (network layer, not compute)
- [Progress Tracking](../http/progress-tracking.md) — for HTTP progress; the progress-reporting pattern here is similar in shape
- [Optimistic Updates](../form-and-search/optimistic-updates.md) — long-running worker operations can compose with optimistic UI (show the result immediately, refine when the real result arrives)
- [Signals](../../concepts/reactivity/signals.md) — the primitive for signaling progress from the worker back to templates

## References

- [`Worker` API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Worker) — the browser primitive
- [Web Workers (angular.dev)](https://angular.dev/ecosystem/web-workers) — Angular's guidance including the `ng generate` schematic
- [Comlink (GitHub)](https://github.com/GoogleChromeLabs/comlink) — the RPC wrapper library used throughout this recipe
- [Transferable Objects (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Transferable_objects) — for zero-copy data transfer
- [`navigator.hardwareConcurrency` (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/hardwareConcurrency) — for tuning pool size
- [SharedArrayBuffer (MDN)](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer) — for cooperative cancellation and shared-memory patterns
- [Cross-origin isolation (web.dev)](https://web.dev/articles/cross-origin-isolation-guide) — the COOP/COEP headers needed for SharedArrayBuffer

## Demo source

Synthesized from real-world web-worker integration patterns rather than a single demo file. The Comlink-based pattern is the modern default (raw postMessage is unwieldy for anything more than one method). The worker-pool implementation and the cooperative-cancellation-via-SharedArrayBuffer pattern reflect what teams converge on when they scale worker usage past one-off computations. All code is original.
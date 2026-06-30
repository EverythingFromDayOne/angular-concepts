---
recipe_id: "websocket-real-time"
title: "WebSocket Integration: Real-Time Data Without the Reconnection Hell"
file: "recipes/http/websocket-real-time.md"
primary_concept: "http/http"
related_concepts: ["reactivity/signals", "reactivity/rxjs/rxjs", "dependency-injection/dependency-injection"]
demo_repo: null
angular_baseline: "22"
difficulty: "intermediate"
status:
  upgraded: true
  reviewed: false
---

# WebSocket Integration: Real-Time Data Without the Reconnection Hell

> **What you'll build:** a real-time data layer that survives the real
> world — one shared connection across multiple subscribers (not N
> connections for N components), automatic reconnection with backoff
> when the network blips, type-safe message dispatch by discriminated
> union, authentication via first-message handshake, and the
> heartbeat trick that keeps proxies from silently killing the
> connection. Plus the **Server-Sent Events** alternative for the
> common case where you only need server-to-client updates.
>
> **Concepts you'll touch:** [HTTP](../../http/http.md), [Signals](../../reactivity/signals.md), [RxJS](../../reactivity/rxjs/rxjs.md), [Dependency Injection](../../dependency-injection/dependency-injection.md)
>
> **Time:** ~30 minutes to read; ~3 hours to wire up against a real
> backend including the auth handshake and verify reconnection works.

---

## The scenario

A team chat app. New messages should appear instantly without the user refreshing. The product spec says "use WebSockets." You write:

```typescript
@Component({ /* … */ })
export class ChatComponent {
  readonly messages = signal<Message[]>([]);

  constructor() {
    const socket = new WebSocket('wss://api.example.com/chat');
    socket.onmessage = event => {
      const msg = JSON.parse(event.data);
      this.messages.update(current => [...current, msg]);
    };
  }
}
```

Within a week of testing:

1. **The user opens the chat list AND a specific chat → two WebSocket connections open** to the same server. The page that has both visible is silently doubling the data flow and the bandwidth.
2. **The user's wifi drops for 3 seconds → the WebSocket dies and never reconnects.** They keep using the app, see no new messages, eventually refresh out of frustration.
3. **The user logs out → the WebSocket stays open** for the old user, the server keeps streaming events, the new user (after re-login on the same page) sees the previous user's data briefly.
4. **The server's load balancer drops idle connections after 60 seconds** of no traffic. The user is on the chat list, no one sends a message, after 60 seconds the connection is silently dead. The next message arrives 5 minutes later (when the server itself notices) instead of in real time.
5. **The auth token expires mid-connection.** The server starts rejecting messages but the connection stays open. The user sends a message, sees "✓ sent," but it never lands.

This recipe walks through the patterns that solve all five. The substance is in the architecture — one connection, multiple subscribers, robust reconnection — not in the WebSocket API itself.

---

## Why a single shared service

The fundamental architectural decision: **the WebSocket connection should live in a service, not a component.** Components subscribe to the service; the service owns the connection lifecycle.

This produces:

- One connection per browser tab, regardless of how many components want messages
- Connection survives navigation (chat list → chat detail → settings → chat list = one connection throughout)
- Lifecycle controlled by the service, not by which components happen to be mounted
- Authentication state in one place (the service); components don't care

The alternative — each component opens its own — is fundamentally wrong. Multiple components = multiple connections = N× the bandwidth + N× the auth handshakes + N× the reconnection logic. The "obvious" approach of WebSocket-per-component scales linearly with screen complexity, in the wrong direction.

---

## Pattern 1 — the basic service

```typescript
// File: services/realtime.service.ts
import { Injectable, inject, signal, computed } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { TokenService } from '../auth/token.service';

// Discriminated union of all possible server messages.
// One per real-time event the server can send.
export type ServerMessage =
  | { type: 'chat:message';     payload: { conversationId: string; text: string; userId: string; timestamp: number } }
  | { type: 'chat:typing';      payload: { conversationId: string; userId: string } }
  | { type: 'presence:update';  payload: { userId: string; online: boolean } }
  | { type: 'notification';     payload: { id: string; text: string; severity: 'info' | 'warn' | 'error' } }
  | { type: 'auth:success';     payload: { userId: string } }
  | { type: 'auth:failure';     payload: { reason: string } }
  | { type: 'pong';             payload: { timestamp: number } };

// Discriminated union of messages the client can send.
export type ClientMessage =
  | { type: 'auth';             payload: { token: string } }
  | { type: 'chat:send';        payload: { conversationId: string; text: string } }
  | { type: 'chat:typing';      payload: { conversationId: string } }
  | { type: 'ping';             payload: { timestamp: number } };

type ConnectionStatus = 'disconnected' | 'connecting' | 'authenticating' | 'connected' | 'reconnecting';

@Injectable({ providedIn: 'root' })
export class RealtimeService {
  private readonly tokenService = inject(TokenService);

  private socket: WebSocket | null = null;
  private readonly incoming = new Subject<ServerMessage>();
  private readonly _status = signal<ConnectionStatus>('disconnected');

  readonly status = this._status.asReadonly();
  readonly isConnected = computed(() => this._status() === 'connected');

  /** All incoming messages — broadcast to multiple subscribers. */
  readonly messages$: Observable<ServerMessage> = this.incoming.asObservable();

  /**
   * Type-safe filter: subscribe only to a specific message type.
   * `messagesOfType('chat:message')` returns Observable<{type: 'chat:message'; payload: {...}}>
   */
  messagesOfType<K extends ServerMessage['type']>(
    type: K,
  ): Observable<Extract<ServerMessage, { type: K }>> {
    return this.incoming.pipe(
      filter((msg): msg is Extract<ServerMessage, { type: K }> => msg.type === type),
    );
  }

  connect(): void {
    if (this.socket && this._status() !== 'disconnected') return;

    this._status.set('connecting');
    this.socket = new WebSocket('wss://api.example.com/realtime');

    this.socket.onopen = () => {
      // Send auth as the first message after connection opens
      this._status.set('authenticating');
      const token = this.tokenService.getToken();
      if (token) {
        this.send({ type: 'auth', payload: { token } });
      }
    };

    this.socket.onmessage = event => {
      try {
        const message = JSON.parse(event.data) as ServerMessage;

        // Handle auth responses internally before broadcasting
        if (message.type === 'auth:success') {
          this._status.set('connected');
        } else if (message.type === 'auth:failure') {
          this.disconnect();
          return;
        }

        this.incoming.next(message);
      } catch (err) {
        console.error('Invalid WebSocket message', event.data);
      }
    };

    this.socket.onclose = () => {
      this._status.set('disconnected');
      this.socket = null;
    };

    this.socket.onerror = () => {
      // onclose will fire right after, with the actual cleanup
    };
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this._status.set('disconnected');
  }

  send(message: ClientMessage): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected; message dropped', message);
      return;
    }
    this.socket.send(JSON.stringify(message));
  }
}
```

**Five patterns doing the work:**

- **Discriminated union for messages**, both directions. `type` field narrows TypeScript automatically. `messagesOfType('chat:message')` returns a fully-typed stream — no manual casting in components.

- **`Subject<ServerMessage>` for multicasting.** Multiple components subscribe to `messages$` or `messagesOfType('foo')`; each receives every message. The Subject doesn't replay (no history for late subscribers, which is what you want for real-time events — old messages are stale).

- **`signal<ConnectionStatus>`** with `asReadonly()` for component reads. Components show "Connecting…" / "Connected" / "Reconnecting…" based on this signal; UI is reactive without subscriptions.

- **Auth as first message after `onopen`**, not via URL query param. Tokens in URLs leak through logs, browser history, and HTTP referer headers. The first-message handshake is the standard production pattern; the server validates and either replies with `auth:success` or closes the connection.

- **`computed(() => this._status() === 'connected')`** for the derived flag. Components that just want to know "is it connected?" don't have to compare strings.

### Components subscribe by message type

```typescript
@Component({ /* … */ })
export class ConversationComponent {
  private readonly realtime = inject(RealtimeService);
  protected readonly conversationId = input.required<string>();
  protected readonly messages = signal<Message[]>([]);

  constructor() {
    // Type-safe — TypeScript knows msg.payload has conversationId, text, etc.
    this.realtime.messagesOfType('chat:message').pipe(
      filter(msg => msg.payload.conversationId === this.conversationId()),
      takeUntilDestroyed(),
    ).subscribe(msg => {
      this.messages.update(current => [...current, {
        id: crypto.randomUUID(),
        text: msg.payload.text,
        userId: msg.payload.userId,
        timestamp: msg.payload.timestamp,
      }]);
    });
  }

  sendMessage(text: string): void {
    this.realtime.send({
      type: 'chat:send',
      payload: { conversationId: this.conversationId(), text },
    });
  }
}
```

Six components on the page subscribing to `messagesOfType('chat:message')` = one WebSocket connection, six subscribers on the Subject. The connection's bandwidth is shared; the dispatch is in-memory.

---

## Pattern 2 — reconnection with backoff

Networks drop. Mobile users move between cell towers. Wifi flakes. Proxies time out. **A real-time connection that doesn't reconnect is a real-time connection that breaks frequently.**

Add reconnection to the service:

```typescript
@Injectable({ providedIn: 'root' })
export class RealtimeService {
  // …existing fields…

  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly MAX_RECONNECT_ATTEMPTS = 8;
  private readonly BASE_DELAY_MS = 1000;
  private readonly MAX_DELAY_MS = 30_000;

  connect(): void {
    if (this.socket && this._status() !== 'disconnected') return;
    this.clearReconnectTimer();

    this._status.set(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');
    this.socket = new WebSocket('wss://api.example.com/realtime');

    this.socket.onopen = () => {
      this._status.set('authenticating');
      const token = this.tokenService.getToken();
      if (token) {
        this.send({ type: 'auth', payload: { token } });
      }
    };

    this.socket.onmessage = event => {
      try {
        const message = JSON.parse(event.data) as ServerMessage;

        if (message.type === 'auth:success') {
          this._status.set('connected');
          this.reconnectAttempts = 0;  // reset on successful auth
        } else if (message.type === 'auth:failure') {
          this.disconnect();
          return;
        }

        this.incoming.next(message);
      } catch (err) {
        console.error('Invalid WebSocket message', event.data);
      }
    };

    this.socket.onclose = event => {
      this.socket = null;

      // 1000 = normal closure (called .close() ourselves); don't reconnect
      // 1001 = going away (browser tab closing); don't reconnect
      // 4xxx = application-defined (we use 4001 for "auth expired"); reconnect after refresh
      if (event.code === 1000 || event.code === 1001) {
        this._status.set('disconnected');
        return;
      }

      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      this._status.set('disconnected');
      // Give up; user must manually reconnect (refresh page, or a "Reconnect" button)
      return;
    }

    this._status.set('reconnecting');
    this.reconnectAttempts++;

    // Exponential backoff with jitter, capped at MAX_DELAY_MS
    const exponential = Math.min(
      this.BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts - 1),
      this.MAX_DELAY_MS,
    );
    const jitter = Math.random() * exponential * 0.25;
    const delay = exponential + jitter;

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  disconnect(): void {
    this.clearReconnectTimer();
    this.reconnectAttempts = 0;
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this._status.set('disconnected');
  }
}
```

**The reconnection logic uses the same exponential-backoff-with-jitter math as the [`retry-with-backoff` recipe](./retry-with-backoff.md)**. Worth re-reading that recipe for the rationale — particularly the jitter explanation. Without jitter, 1,000 users who lost connection at the same moment all reconnect at exactly second 1, second 3, second 7… synchronizing into retry storms that DDoS your own server.

**Three subtleties:**

- **Close codes matter.** `1000` is "normal" closure; `1001` is "going away" (typically the browser tab closing). Neither should trigger reconnection. Anything else (transient network errors, server-initiated disconnects, timeouts) gets reconnect logic. The application-defined `4xxx` range can carry semantics: `4001` = "auth expired, refresh and reconnect" is a common convention.

- **Reset attempt counter on successful auth, not on `onopen`.** The connection opens, then auth fails for some reason (token revoked) — if we reset on `onopen`, the next disconnect starts at attempt 1 again instead of incrementing. Reset only when we've confirmed end-to-end the connection is healthy.

- **Cap the attempts.** After 8 attempts (with exponential backoff capping at 30 seconds each), total elapsed time is roughly 2 minutes. If the connection still isn't working, the user should be informed and given an explicit "Reconnect" button. Infinite background retry burns battery and gives the user no signal that something is wrong.

---

## Pattern 3 — heartbeat / keep-alive

Many proxies (load balancers, CDNs, corporate firewalls) close "idle" WebSocket connections after some timeout — often 60 seconds. The server hasn't disconnected; the proxy in between dropped the connection. The browser doesn't notice immediately, sometimes for minutes.

**The fix: send a ping every N seconds to keep the connection visible to the proxy as active.**

```typescript
@Injectable({ providedIn: 'root' })
export class RealtimeService {
  // …existing fields…

  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private lastPongTimestamp = 0;
  private readonly HEARTBEAT_INTERVAL_MS = 30_000;  // every 30s — well under typical proxy timeout
  private readonly PONG_TIMEOUT_MS = 10_000;        // if no pong within 10s, treat as dead

  connect(): void {
    // …existing connect code…

    this.socket.onmessage = event => {
      try {
        const message = JSON.parse(event.data) as ServerMessage;

        if (message.type === 'pong') {
          this.lastPongTimestamp = message.payload.timestamp;
          return;  // don't broadcast internal heartbeat messages
        }

        // …rest of onmessage handler…
      } catch (err) { /* … */ }
    };
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      const now = Date.now();
      this.send({ type: 'ping', payload: { timestamp: now } });

      // If we haven't received a pong in PONG_TIMEOUT_MS, assume connection is dead
      setTimeout(() => {
        if (Date.now() - this.lastPongTimestamp > this.HEARTBEAT_INTERVAL_MS + this.PONG_TIMEOUT_MS) {
          console.warn('Heartbeat timeout — forcing reconnect');
          if (this.socket) {
            this.socket.close(4002, 'Heartbeat timeout');
            // onclose will fire and trigger scheduleReconnect
          }
        }
      }, this.PONG_TIMEOUT_MS);
    }, this.HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // Call startHeartbeat() inside auth:success handler;
  // call stopHeartbeat() inside onclose, disconnect, and scheduleReconnect
}
```

**Three patterns worth absorbing:**

- **The heartbeat interval is shorter than typical proxy timeouts.** 30s is conservative — many proxies are at 60s, some Azure/AWS configurations at 4 minutes. 30s is well under all of them; the network cost is negligible (40 bytes per ping every 30 seconds = 80 B/min ≈ nothing).

- **Pong-timeout triggers a forced close, not a direct reconnect.** Closing the socket triggers `onclose`, which triggers `scheduleReconnect`. One code path for "the connection died," whether the cause is network failure, proxy timeout, or heartbeat miss.

- **`pong` messages are filtered out before broadcasting.** They're internal — components don't need to see them. The handler short-circuits and returns before `this.incoming.next(message)`.

The server side needs to respond to pings with pongs. If you control the backend, this is one route. If you're consuming a third-party WebSocket API that doesn't implement ping/pong, you're stuck — you can still send `ping` messages but no application-level pong; you have to rely on the lower-level WebSocket protocol's built-in ping/pong (which most browsers don't expose, frustratingly).

---

## Pattern 4 — Server-Sent Events alternative

WebSockets are bidirectional. If you only need server-to-client streaming (notifications, status updates, live dashboards, stock prices), **Server-Sent Events (SSE) is significantly simpler.**

The browser handles reconnection automatically. The protocol is text-based. There's no ping/pong dance. There's no auth-handshake message — auth is via cookies or a URL token (same as a regular HTTP request).

```typescript
@Injectable({ providedIn: 'root' })
export class NotificationStreamService {
  private eventSource: EventSource | null = null;
  private readonly incoming = new Subject<Notification>();
  readonly notifications$ = this.incoming.asObservable();

  connect(): void {
    if (this.eventSource) return;

    // SSE uses regular HTTP; cookies are sent automatically.
    // Auth via cookies works without any custom handshake.
    this.eventSource = new EventSource('/api/notifications/stream', {
      withCredentials: true,  // include cookies for auth
    });

    this.eventSource.onmessage = event => {
      try {
        const notification = JSON.parse(event.data) as Notification;
        this.incoming.next(notification);
      } catch (err) {
        console.error('Invalid SSE message', event.data);
      }
    };

    this.eventSource.onerror = () => {
      // Browser auto-reconnects after errors — no manual logic needed.
      // It may take a few seconds; the EventSource exponential-backs-off internally.
      console.warn('SSE connection error; browser will retry');
    };
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

**That's the entire implementation.** No reconnection logic, no heartbeat, no auth handshake. Compare with the ~150 lines for the WebSocket equivalent.

### When SSE is the right choice

| Need | WebSocket | SSE |
| --- | --- | --- |
| Server → client streaming | ✅ | ✅ (simpler) |
| Client → server messages | ✅ | ❌ (use regular HTTP for sends) |
| Binary data | ✅ (via ArrayBuffer) | ❌ (text only) |
| Auto-reconnect | Manual | Built-in |
| Cookie auth | Manual handshake | Native |
| Browser support | Universal | Universal |
| HTTP/2 multiplexing | ❌ (separate TCP connection) | ✅ |
| Per-domain connection limit | ~250 (high) | 6 (in HTTP/1.1) — but lifted in HTTP/2 |

**For chat apps, collaborative editors, multiplayer games**: WebSocket — you need bidirectional.

**For dashboards, notification feeds, deployment-status pages, build logs, stock tickers, live sports scores**: SSE — server-to-client only, much less code.

A common pattern: **use SSE for the data streaming, regular HTTP POSTs for the client→server messages.** This combines SSE's reconnection simplicity with HTTP's request/response clarity. Chat sends use `POST /api/chat/messages`; chat receives come over SSE.

---

## Composition with auth and re-auth

The token storage and refresh patterns from the [auth recipes](../auth/token-storage-security.md) compose with WebSocket auth:

```typescript
@Injectable({ providedIn: 'root' })
export class RealtimeService {
  private readonly tokenService = inject(TokenService);
  private readonly authService = inject(AuthService);

  constructor() {
    // When the access token changes (login, logout, refresh), reconnect.
    // The signal-effect bridge makes this declarative.
    effect(() => {
      const token = this.tokenService.getTokenSignal()();  // reactive read

      if (token && this._status() === 'disconnected') {
        this.connect();
      } else if (!token && this._status() !== 'disconnected') {
        this.disconnect();
      }
    });
  }

  // …rest of service…
}
```

If the server sends an `auth:failure` with code `4001` (token expired), trigger a refresh and reconnect:

```typescript
this.socket.onmessage = event => {
  const message = JSON.parse(event.data) as ServerMessage;

  if (message.type === 'auth:failure' && message.payload.reason === 'token_expired') {
    this.authService.refreshToken().subscribe({
      next: () => this.connect(),  // reconnect with new token
      error: () => this.authService.logout().subscribe(),
    });
    return;
  }

  // …rest of handler…
};
```

The composition is clean: `AuthService` knows how to refresh; `RealtimeService` knows how to reconnect; neither needs to know much about the other.

---

## Trade-offs and common pitfalls

**Use WebSockets when:**

- Bidirectional, low-latency communication is genuinely needed (chat, collaborative editing, multiplayer)
- The interaction pattern is rapid back-and-forth (HTTP polling overhead would dominate)
- The server is sending frequent updates that the client needs in real time

**Skip WebSockets (use SSE or polling) when:**

- Only server-to-client streaming is needed → SSE
- Updates are infrequent (every minute or more) → polling is simpler
- The team doesn't have backend WebSocket expertise → polling is operationally easier
- Behind a corporate proxy that strips WebSocket upgrades → polling or long-polling

### Common pitfalls

- **One WebSocket per component instead of a shared service.** Six components on the page = six connections. Symptom: server logs show 6N active connections where N is the number of active users; bandwidth usage scales weird. The fix is always "lift to a singleton service."
- **Forgetting to close on logout.** The connection stays open under the previous user's session; the server keeps streaming events. The next user (or the same user re-logging) sees confusing data. Always wire `logout()` to `realtime.disconnect()`.
- **No reconnection logic.** Wifi blips, the connection dies, the app silently breaks. Users don't get an error — they just stop seeing new data. The reconnection pattern from Pattern 2 is mandatory in production.
- **Exponential backoff without jitter.** All disconnected clients retry at exactly second 1, second 3, second 7. The server is DDoS'd by its own users. Jitter is the difference between graceful recovery and outage cascade.
- **Reconnecting forever without backoff cap.** If the server is genuinely down, reconnecting every second for hours burns the user's battery and pings the server uselessly. Cap at 8 attempts with exponential growth to ~30s max.
- **Heartbeat too infrequent for the proxy.** If the proxy times out at 60s and the heartbeat is at 90s, the heartbeat never gets a chance to keep the connection alive. Set heartbeat shorter than the shortest proxy timeout in your path.
- **Treating WebSocket messages as ordered + delivered.** WebSockets guarantee in-order delivery within a single connection. They do NOT survive reconnection — messages sent during a disconnect are lost. For "at-least-once" semantics, the server needs to support catch-up queries (e.g., `GET /messages?since=<timestamp>`) and the client should call this after reconnect.
- **Auth token in URL query param.** Tokens in URLs leak through logs, browser history, HTTP referer headers, and analytics. The first-message handshake is the production pattern.
- **Not handling auth-token refresh mid-connection.** Token expires, server starts rejecting messages, connection stays open. Subscribe to token changes; reconnect on refresh.
- **Mixed `http://` + `ws://` in production.** A page loaded over HTTPS can't open a `ws://` connection (browser blocks it as insecure mixed content). Always use `wss://` for production WebSockets.
- **Subject without `takeUntilDestroyed()` in subscribers.** Component subscribes to `messagesOfType('foo')`; component is destroyed; subscription leaks; the message handler still runs on every incoming message of that type, calling `.set()` on a destroyed component's signal. Same rule as everywhere: `takeUntilDestroyed()` on every component subscription.
- **EventSource (SSE) 6-connection-per-domain limit in HTTP/1.1.** If your site uses 6 separate EventSource streams for different feeds, the 7th tab can't open one. Either consolidate streams into one SSE endpoint that multiplexes message types, or ensure your server is HTTP/2 (which lifts the limit).
- **Backpressure ignored.** Server sends faster than the client can process. The browser buffers, memory grows, the tab eventually freezes. For high-rate streams (1000+ msg/sec), the client needs sampling or batching — drop intermediate events rather than queueing them forever.
- **Console.log on every message.** Production builds with logging cause significant overhead on high-rate streams. Strip in production, or use a debug flag.

---

## See also

- [Retry with Backoff](./retry-with-backoff.md) — shares the exponential-backoff-with-jitter math; the reconnection logic is the same pattern
- [Token Storage Security](../auth/token-storage-security.md) — the auth state the WebSocket service consumes via `effect()`
- [Race Conditions](../reactivity/race-conditions.md) — message handlers that mutate state need the same operator discipline as HTTP responses
- [Component Communication](../components/component-communication.md) — when to use Subject-based services vs signal-based services (Pattern 2 of that recipe)
- [HTTP](../../http/http.md) — for comparison; when to choose HTTP polling vs WebSockets vs SSE
- [Signals](../../reactivity/signals.md) — `signal`, `computed`, `effect` patterns used throughout the service

## References

- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket) — the browser primitive
- [WebSocket close codes (IANA)](https://www.iana.org/assignments/websocket/websocket.xhtml) — the standard codes (`1000`, `1001`, etc.) plus the application-defined `4xxx` range
- [EventSource API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — the SSE primitive
- [Server-Sent Events spec (WHATWG)](https://html.spec.whatwg.org/multipage/server-sent-events.html) — the standard
- [`webSocket` (RxJS)](https://rxjs.dev/api/webSocket/webSocket) — RxJS's built-in wrapper; an alternative starting point if you prefer Observable-first
- [Socket.IO](https://socket.io/) — the library if you don't want to build the reconnection/heartbeat layer yourself; adds a protocol layer on top of WebSocket
- [Designing reliable WebSocket connections (AWS)](https://aws.amazon.com/blogs/compute/announcing-websocket-apis-in-amazon-api-gateway/) — production reference for the patterns in this recipe

## Demo source

Synthesized from common production WebSocket patterns rather than a single demo file. The single-service-multiple-subscribers architecture, exponential-reconnect-with-jitter, and heartbeat-for-proxy-keepalive reflect the consensus across high-availability real-time applications. The SSE alternative is included because most teams reach for WebSockets when SSE would have served them better — the decision table makes the right choice mechanical. All code is original.
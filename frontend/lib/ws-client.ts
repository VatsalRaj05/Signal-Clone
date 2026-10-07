/**
 * WebSocket client abstraction.
 *
 * Provides a reconnecting WebSocket wrapper that:
 * - Auto-reconnects with exponential backoff
 * - Dispatches typed events to registered listeners
 * - Can be connected to the backend WS endpoint in later phases
 *
 * Usage (future):
 *   wsClient.connect(token);
 *   wsClient.on("new_message", (payload) => { ... });
 *   wsClient.send({ type: "typing", payload: { conversationId: "..." } });
 */

import type { WSEvent, WSEventType } from "@/types";

type EventHandler<T = unknown> = (payload: T) => void;

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

const MAX_RECONNECT_DELAY_MS = 30_000;
const INITIAL_RECONNECT_DELAY_MS = 1_000;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners = new Map<WSEventType, Set<EventHandler>>();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private _token: string | null = null;

  /** Connect to the WebSocket server. */
  connect(token: string): void {
    if (
      this._token === token &&
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return; // Already connecting or connected with this token
    }

    this._token = token;
    this.reconnectAttempts = 0;
    this.establishConnection();
  }

  /** Cleanly disconnect and stop reconnection attempts. */
  disconnect(): void {
    this.clearReconnectTimer();
    this.clearPingInterval();
    this._token = null;
    if (this.socket) {
      this.socket.onclose = null; // prevent auto-reconnect
      this.socket.onerror = null;
      this.socket.close();
      this.socket = null;
    }
  }

  /** Send a typed event to the server. */
  send<T>(event: WSEvent<T>): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(event));
      } catch {
        // Socket send error
      }
    }
  }

  /** Register a listener for a specific event type. */
  on<T = unknown>(type: WSEventType, handler: EventHandler<T>): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    const handlers = this.listeners.get(type)!;
    handlers.add(handler as EventHandler);

    // Return unsubscribe function
    return () => {
      handlers.delete(handler as EventHandler);
    };
  }

  /** Remove all listeners for a specific event type. */
  off(type: WSEventType): void {
    this.listeners.delete(type);
  }

  /** Whether the socket is currently open. */
  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  // ── Private ──────────────────────────────────────────────────────

  private establishConnection(): void {
    if (!this._token) return;

    // Clean up previous socket if any
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.onerror = null;
      this.socket.close();
      this.socket = null;
    }

    try {
      this.socket = new WebSocket(`${WS_BASE_URL}?token=${encodeURIComponent(this._token)}`);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.startPingInterval();
    };

    this.socket.onmessage = (event: MessageEvent) => {
      try {
        const wsEvent = JSON.parse(event.data) as WSEvent;
        this.dispatch(wsEvent);
      } catch {
        // Ignore malformed messages
      }
    };

    this.socket.onclose = () => {
      this.clearPingInterval();
      this.scheduleReconnect();
    };

    this.socket.onerror = () => {
      this.socket?.close();
    };
  }

  private dispatch(event: WSEvent): void {
    const handlers = this.listeners.get(event.type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(event.payload);
        } catch (e) {
          console.error("Error in WS handler for", event.type, e);
        }
      });
    }
  }

  private startPingInterval(): void {
    this.clearPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.send({ type: "ping" as WSEventType, payload: {} });
      }
    }, 25_000);
  }

  private clearPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (!this._token) return;

    this.clearReconnectTimer();
    const delay = Math.min(
      INITIAL_RECONNECT_DELAY_MS * 2 ** this.reconnectAttempts,
      MAX_RECONNECT_DELAY_MS
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.establishConnection();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

/** Singleton WebSocket client instance. */
export const wsClient = new WebSocketClient();

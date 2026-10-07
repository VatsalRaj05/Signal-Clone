import { useEffect, useCallback } from "react";
import { wsClient } from "@/lib/ws-client";
import type { WSEventType, WSEvent } from "@/types";

export function useWebSocket(token: string | null) {
  useEffect(() => {
    if (token) {
      wsClient.connect(token);
    }
    // Note: Do not disconnect on simple unmount to keep connection persistent across route changes
  }, [token]);

  const send = useCallback(<T>(event: WSEvent<T>) => {
    wsClient.send(event);
  }, []);

  const on = useCallback(<T = unknown>(type: WSEventType, handler: (payload: T) => void) => {
    return wsClient.on<T>(type, handler);
  }, []);

  return {
    isConnected: wsClient.isConnected,
    send,
    on,
  };
}

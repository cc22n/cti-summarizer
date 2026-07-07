import { useCallback, useEffect, useRef, useState } from "react";

interface AlertEvent {
  event: string;
  source: string;
  count: number;
  alerts: Array<{ id: number; title: string; severity: string }>;
}

const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ??
  "ws://localhost:8000/ws/alerts";

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useRealtimeAlerts() {
  const [newCount, setNewCount] = useState(0);
  const [lastEvent, setLastEvent] = useState<AlertEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (attemptsRef.current >= MAX_RECONNECT_ATTEMPTS) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data as string) as AlertEvent;
          setLastEvent(data);
          setNewCount((prev) => prev + (data.count ?? 1));
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (unmountedRef.current) return;
        attemptsRef.current += 1;
        // eslint-disable-next-line react-hooks/immutability
        setTimeout(connect, RECONNECT_DELAY_MS);
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onopen = () => {
        attemptsRef.current = 0;
      };
    } catch {
      // WebSocket not supported or URL invalid — silently skip
    }
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  const clearCount = useCallback(() => setNewCount(0), []);

  return { newCount, lastEvent, clearCount };
}

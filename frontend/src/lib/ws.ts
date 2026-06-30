"use client";

import { useEffect, useRef, useState } from "react";
import { tokenStore, WS_BASE } from "./api";
import type { RideStatus, WsEvent } from "./types";

export interface LivePoint { lat: number; lng: number; }
export interface LiveRideState {
  connected: boolean;
  status: RideStatus | null;
  driverLocation: LivePoint | null;
  lastEventAt: string | null;
}

/**
 * Subscribe to a ride's real-time channel. Parses the backend event envelope
 * ({type,data,ts}) and exposes the live status + driver position. Reconnects
 * with backoff while the ride id is set.
 */
export function useRideSocket(rideId: string | null): LiveRideState {
  const [state, setState] = useState<LiveRideState>({
    connected: false, status: null, driverLocation: null, lastEventAt: null,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedRef = useRef(false);

  useEffect(() => {
    if (!rideId) return;
    closedRef.current = false;

    const connect = () => {
      const token = tokenStore.access;
      if (!token) return;
      const ws = new WebSocket(`${WS_BASE}/rides/${rideId}?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setState((s) => ({ ...s, connected: true }));
      };
      ws.onmessage = (ev) => {
        let msg: WsEvent;
        try { msg = JSON.parse(ev.data as string) as WsEvent; } catch { return; }
        setState((s) => {
          const next = { ...s, lastEventAt: msg.ts };
          const d = msg.data as Record<string, unknown>;
          if (msg.type === "snapshot") {
            next.status = (d.status as RideStatus) ?? s.status;
            const loc = d.driver_location as LivePoint | null | undefined;
            if (loc && typeof loc.lat === "number") next.driverLocation = { lat: loc.lat, lng: loc.lng };
          } else if (msg.type === "ride_status") {
            next.status = (d.status as RideStatus) ?? s.status;
          } else if (msg.type === "location") {
            if (typeof d.lat === "number" && typeof d.lng === "number")
              next.driverLocation = { lat: d.lat as number, lng: d.lng as number };
          }
          return next;
        });
      };
      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (closedRef.current) return;
        retryRef.current = Math.min(retryRef.current + 1, 6);
        setTimeout(connect, 500 * retryRef.current);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closedRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [rideId]);

  return state;
}

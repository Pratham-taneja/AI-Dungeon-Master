"use client";

import { useEffect, useState } from "react";
import { subscribeWorldEvents } from "@/lib/api";

export interface WorldEventEntry {
  id: string;
  text: string;
  timestamp: number;
}

/**
 * Subscribes to the autonomous world-event SSE channel for a session.
 * The Celery beat worker fires these independently of player actions.
 */
export function useWorldEvents(sessionId: string | null) {
  const [events, setEvents] = useState<WorldEventEntry[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    const source = subscribeWorldEvents(sessionId, {
      onOpen: () => setConnected(true),
      onError: () => setConnected(false),
      onMessage: (message) => {
        if (message.type === "connected") {
          setConnected(true);
        } else if (message.type === "world_event" && message.text) {
          setEvents((prev) =>
            [
              { id: `w-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, text: message.text!, timestamp: Date.now() },
              ...prev,
            ].slice(0, 10)
          );
        }
      },
    });

    return () => {
      source.close();
      setConnected(false);
    };
  }, [sessionId]);

  return { events, connected };
}

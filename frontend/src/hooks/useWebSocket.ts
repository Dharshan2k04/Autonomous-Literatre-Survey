import { useEffect, useRef, useState, useCallback } from "react";
import type { ProgressEvent } from "@/types";

const WS_URL = import.meta.env.VITE_WS_URL || "";

export function useWebSocket(surveyId: string | undefined) {
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!surveyId) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    const wsUrl = `${WS_URL || `ws://${window.location.host}`}/ws/surveys/${surveyId}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setProgress(data);
      } catch {
        console.warn("Invalid WS message:", event.data);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [surveyId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { progress, isConnected, disconnect };
}

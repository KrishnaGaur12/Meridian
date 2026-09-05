import { useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../services/api';

export type BackendEventType =
  | 'DISPUTE_CREATED'
  | 'DISPUTE_ANALYSIS_STARTED'
  | 'ML_ANALYSIS_COMPLETED'
  | 'DEEPSEEK_ANALYSIS_COMPLETED'
  | 'DISPUTE_ANALYSIS_COMPLETED'
  | 'EVIDENCE_APPROVED'
  | 'DISPUTE_STAGE_CHANGED'
  | 'DASHBOARD_UPDATED'
  | 'ping'
  | string;

export interface RealtimeEventData {
  event_type?: string;
  dispute_id?: string;
  transaction_id?: string;
  amount?: number;
  currency?: string;
  status?: string;
  stage?: string;
  workflow_stage?: string;
  fraud_probability?: number;
  win_probability?: number;
  confidence?: string;
  recommendation?: string;
  timestamp?: string;
  message?: string;
  [key: string]: any;
}

export interface UseRealtimeEventsOptions {
  onEvent?: (eventType: BackendEventType, data: RealtimeEventData) => void;
  onRefresh?: () => void;
  disputeId?: string;
  enabled?: boolean;
}

export const useRealtimeEvents = ({
  onEvent,
  onRefresh,
  disputeId: _disputeId,
  enabled = true,
}: UseRealtimeEventsOptions = {}) => {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  const handleIncomingEvent = useCallback(
    (type: string, rawData: string) => {
      let data: RealtimeEventData = {};
      try {
        data = rawData ? JSON.parse(rawData) : {};
      } catch {
        data = { message: rawData };
      }

      // Notify global/local listeners for real-time background sync
      onEvent?.(type, data);
      onRefresh?.();
    },
    [onEvent, onRefresh]
  );

  useEffect(() => {
    if (!enabled) return;

    const connectSSE = () => {
      try {
        const sseUrl = `${API_BASE_URL}/events`;
        const es = new EventSource(sseUrl);
        eventSourceRef.current = es;

        const eventTypes: BackendEventType[] = [
          'DISPUTE_CREATED',
          'DISPUTE_ANALYSIS_STARTED',
          'ML_ANALYSIS_COMPLETED',
          'DEEPSEEK_ANALYSIS_COMPLETED',
          'DISPUTE_ANALYSIS_COMPLETED',
          'EVIDENCE_APPROVED',
          'DISPUTE_STAGE_CHANGED',
          'DASHBOARD_UPDATED',
        ];

        eventTypes.forEach((evtName) => {
          es.addEventListener(evtName, (e: MessageEvent) => {
            handleIncomingEvent(evtName, e.data);
          });
        });

        es.onmessage = (e: MessageEvent) => {
          handleIncomingEvent('message', e.data);
        };

        es.onerror = () => {
          es.close();
          // Schedule reconnect attempt silently without UI popups
          reconnectTimeoutRef.current = setTimeout(() => {
            connectSSE();
          }, 5000);
        };
      } catch {
        // Silently schedule retry
        reconnectTimeoutRef.current = setTimeout(() => {
          connectSSE();
        }, 5000);
      }
    };

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [enabled, handleIncomingEvent]);
};


import { useEffect, useRef } from 'react';
import { useDatabaseMode } from '../context/DatabaseModeContext';
import { useRealtimeEvents } from './useRealtimeEvents';

export const useRealtimeRefresh = (
  onRefresh?: () => void,
  intervalMs: number = 8000,
  enabled: boolean = true
) => {
  const { isLive } = useDatabaseMode();
  const onRefreshRef = useRef(onRefresh);

  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  // Primary: Realtime SSE listener for instant updates
  useRealtimeEvents({
    enabled: enabled && isLive,
    onRefresh: () => onRefreshRef.current?.(),
  });

  // Secondary: Heartbeat refresh for reliable sync
  useEffect(() => {
    if (!enabled || !isLive) return;

    const timer = setInterval(() => {
      if (!document.hidden) {
        onRefreshRef.current?.();
      }
    }, intervalMs);

    return () => clearInterval(timer);
  }, [enabled, isLive, intervalMs]);
};


import React, { useEffect, useState } from 'react';
import { disputeService } from '../../services/disputeService';
import { DisputeTimelineEvent } from '../../types/dispute';
import { Card } from '../../components/common/Card';
import { Skeleton } from '../../components/common/Skeleton';
import { useDatabaseMode } from '../../context/DatabaseModeContext';
import { formatDate } from '../../utils/formatters';

export const SimulatorActivityPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [events, setEvents] = useState<DisputeTimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    disputeService
      .getDisputes()
      .then(async (disputes) => {
        if (!isMounted) return;
        const allEvents: DisputeTimelineEvent[] = [];
        for (const d of disputes.slice(0, 10)) {
          try {
            const logs = await disputeService.getAuditLog(d.dispute_id);
            allEvents.push(...logs);
          } catch {}
        }
        allEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        if (isMounted) {
          setEvents(allEvents);
        }
      })
      .catch(() => {
        if (isMounted) setEvents([]);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [modeVersion]);

  return (
    <div className="w-full space-y-4">
      <div className="pb-1 border-b border-slate-200/60">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-slate-900">Network Activity Log</h1>
          <span
            className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
              isLive
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            {isLive ? 'LIVE DATABASE' : 'DEMO DATABASE'}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">
          Real-time event stream across gateway boundaries and merchant responses in active mode
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : (
        <Card className="p-4 bg-white space-y-3 border-slate-200">
          {events.length === 0 ? (
            <p className="text-xs text-slate-500 py-4 text-center">No operational events recorded in active mode.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {events.map((evt, idx) => (
                <div key={idx} className="py-2.5 flex items-start justify-between gap-4 text-xs">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900">{evt.title}</span>
                      <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.2 rounded text-slate-600">
                        Case: {evt.dispute_id}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px]">{evt.description}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[10px] text-slate-400 font-mono">{formatDate(evt.timestamp)}</span>
                    <div className="text-[10px] text-slate-500 font-mono">Actor: {evt.actor_type || 'SYSTEM'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

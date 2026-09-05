import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { disputeService } from '../services/disputeService';
import { Dispute } from '../types/dispute';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { useDatabaseMode } from '../context/DatabaseModeContext';
import { formatCurrency, formatReasonCode, formatStatus, formatDate } from '../utils/formatters';

export const HistoryPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [resolvedDisputes, setResolvedDisputes] = useState<Dispute[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchHistory = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const disputes = await disputeService.getDisputes();
        if (!isMounted) return;

        const resolved = disputes.filter((d) => {
          const status = (d.status || '').toUpperCase();
          const stage = (d.workflow_stage || '').toUpperCase();
          return status === 'WON' || status === 'LOST' || status === 'CLOSED' || stage === 'RESOLVED';
        });
        setResolvedDisputes(resolved);
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load history');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [modeVersion]);

  return (
    <div className="w-full flex-1 flex flex-col space-y-4">
      {/* Header */}
      <div className="pb-1 border-b border-slate-200/60">
        <div className="flex items-center gap-2">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Dispute History</h1>
          <span
            className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
              isLive
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            {isLive ? 'LIVE MODE' : 'DEMO MODE'}
          </span>
        </div>
        <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
          Archived record of all completed, won, lost, and conceded dispute outcomes
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2.5 flex-1">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : error ? (
        <Card className="text-center py-10 flex-1 flex flex-col items-center justify-center">
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : resolvedDisputes.length === 0 ? (
        <Card className="text-center py-14 bg-white flex-1 flex flex-col items-center justify-center border-slate-200">
          <div className="w-9 h-9 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center mx-auto mb-2 text-sm">
            📁
          </div>
          <h3 className="text-sm font-semibold text-slate-900">No resolved disputes yet</h3>
          <p className="text-xs text-slate-500 mt-0.5 max-w-sm">
            {isLive
              ? 'No disputes have reached a resolved state in Live mode yet.'
              : 'Resolved demo dispute outcomes will appear here.'}
          </p>
        </Card>
      ) : (
        <div className="space-y-2.5 flex-1">
          {resolvedDisputes.map((d) => {
            const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);

            return (
              <Card
                key={d.dispute_id}
                hoverEffect
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3.5 border-slate-200 bg-white"
              >
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-xs sm:text-sm text-slate-900 font-mono">{d.dispute_id}</span>
                    <span className="text-xs font-semibold text-slate-700">· {formatReasonCode(d.reason_code)}</span>
                    <span className="text-xs font-bold text-slate-900">· {formatCurrency(d.amount, d.currency || 'INR')}</span>

                    <span className={`px-2 py-0.5 text-[10px] sm:text-[11px] font-semibold rounded border ml-auto sm:ml-2 ${statusInfo.colorClass}`}>
                      {statusInfo.label}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-y-1 gap-x-3.5 text-xs text-slate-500">
                    <span>Customer: <strong className="text-slate-700 font-normal">{d.customer_id}</strong></span>
                    <span>Transaction: <strong className="text-slate-700 font-normal">{d.transaction_id}</strong></span>
                    <span>Resolved Date: {formatDate(d.ai_last_checked || d.created_at)}</span>
                  </div>
                </div>

                <div className="shrink-0 flex items-center justify-end">
                  <Button
                    onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                    variant="outline"
                    size="sm"
                    className="w-full sm:w-auto font-semibold"
                  >
                    View Case Summary &rarr;
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

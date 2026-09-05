import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { disputeService, DisputeSummary } from '../services/disputeService';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { useDatabaseMode } from '../context/DatabaseModeContext';
import { formatCurrency, formatReasonCode, formatPriority, formatStatus, formatDeadlineText, formatDate } from '../utils/formatters';

export const DisputesPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [disputes, setDisputes] = useState<DisputeSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Minimal filter state
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await disputeService.getDisputes({ status: statusFilter === 'ALL' ? undefined : statusFilter as any });
      setDisputes(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to dispute service');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData, modeVersion]);

  return (
    <div className="space-y-6 flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-slate-700/50 relative shrink-0">
        <div className="absolute -bottom-px left-0 w-1/4 h-px bg-gradient-to-r from-violet-500/50 to-transparent"></div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>
            Active Dispute Cases
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage, review, and triage open chargebacks and retrieval requests.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900/60 text-slate-300 text-xs font-semibold px-3 py-2 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all cursor-pointer"
          >
            <option value="ALL">All Active Statuses</option>
            <option value="OPEN">Open (New)</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="SUBMITTED">Submitted</option>
          </select>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-28 w-full bg-slate-800/50 rounded-xl" />
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center cyber-card rounded-2xl flex flex-col items-center justify-center">
            <div className="w-10 h-10 rounded-full bg-rose-900/30 text-rose-400 flex items-center justify-center mx-auto mb-3 font-bold text-lg border border-rose-500/30">
              !
            </div>
            <h3 className="text-sm font-bold text-slate-200">Failed to load disputes</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">{error}</p>
            <Button onClick={loadData} variant="primary" size="sm" className="mt-4 bg-cyan-600 hover:bg-cyan-500">
              Try again
            </Button>
          </div>
        ) : disputes.length === 0 ? (
          <div className="p-12 text-center cyber-card rounded-2xl flex flex-col items-center justify-center mt-4">
            <div className="w-12 h-12 rounded-full bg-emerald-900/30 text-emerald-400 flex items-center justify-center mb-4 font-bold text-lg border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              ✓
            </div>
            <h3 className="text-lg font-bold text-white tracking-wide">No disputes found</h3>
            <p className="text-sm text-slate-400 mt-2 max-w-md">
              {isLive && statusFilter === 'ALL'
                ? 'No active disputes in Live mode yet. You can use the Gateway Simulator to simulate an inbound chargeback.'
                : 'No dispute cases match the selected filter.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3 pb-8">
            {disputes.map((d) => {
              const priority = formatPriority(d.urgency_level, d.remaining_hours, d.merchant_attention_state);
              const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
              const deadlineStr = formatDeadlineText(d.respond_by, d.remaining_hours);

              return (
                <div
                  key={d.dispute_id}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cyber-card rounded-xl hover:border-violet-500/40 group transition-all"
                >
                  <div className="space-y-2.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-bold text-sm text-white font-mono">{d.dispute_id}</span>
                      <span className="text-xs font-semibold text-slate-400">· {formatReasonCode(d.reason_code)}</span>
                      <span className="text-xs font-bold text-emerald-400">· {formatCurrency(d.amount, d.currency || 'INR')}</span>

                      <div className="flex items-center gap-2 ml-auto sm:ml-4">
                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${priority.colorClass.replace('bg-rose-50', 'bg-rose-900/30 text-rose-300 border-rose-500/50')}`}>
                          {priority.label}
                        </span>
                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${statusInfo.colorClass.replace('bg-blue-50', 'bg-blue-900/30 text-blue-300 border-blue-500/50')}`}>
                          {statusInfo.label}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-400">
                      <span className="font-semibold text-rose-400 drop-shadow-[0_0_5px_rgba(244,63,94,0.3)]">{deadlineStr}</span>
                      <span>Customer: <strong className="text-slate-200 font-medium">{d.customer_id}</strong></span>
                      <span>Txn: <strong className="text-slate-200 font-medium">{d.transaction_id}</strong></span>
                      <span className="font-mono text-[9px] bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300 border border-slate-700">
                        {d.merchant_attention_state || 'REVIEW_RECOMMENDED'}
                      </span>
                    </div>

                    {d.attention_reason && (
                      <p className="text-xs text-slate-300 bg-slate-900/50 p-2.5 rounded-lg border border-slate-700/50 leading-relaxed line-clamp-1 group-hover:line-clamp-none transition-all">
                        {d.attention_reason}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center justify-end">
                    <button
                      onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                      className="bg-slate-800 hover:bg-violet-600 border border-slate-600 hover:border-violet-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all group-hover:shadow-[0_0_15px_-3px_rgba(139,92,246,0.4)]"
                    >
                      Open Case
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

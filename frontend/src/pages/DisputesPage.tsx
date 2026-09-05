import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { disputeService } from '../services/disputeService';
import { Dispute } from '../types/dispute';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { useDatabaseMode } from '../context/DatabaseModeContext';
import { formatCurrency, formatReasonCode, formatPriority, formatStatus, formatDeadlineText, formatDate } from '../utils/formatters';

export const DisputesPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'needs_attention' | 'in_review' | 'resolved'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    let isMounted = true;

    const fetchDisputes = async () => {
      try {
        // If disputes are already in memory, don't show full skeleton
        if (disputes.length === 0) {
          setIsLoading(true);
        }
        setError(null);
        const data = await disputeService.getDisputes(undefined, controller.signal);
        if (isMounted) {
          setDisputes(data);
        }
      } catch (err: any) {
        if (err.name === 'CanceledError' || err.name === 'AbortError' || err.code === 'ERR_CANCELED') {
          return;
        }
        if (isMounted) {
          setError(err.message || 'Failed to load disputes.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchDisputes();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [modeVersion]);


  const filteredDisputes = useMemo(() => {
    return disputes.filter((d) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        d.dispute_id.toLowerCase().includes(q) ||
        d.transaction_id.toLowerCase().includes(q) ||
        d.customer_id.toLowerCase().includes(q) ||
        (d.reason_code && d.reason_code.toLowerCase().includes(q));

      if (!matchesSearch) return false;

      const status = (d.status || '').toUpperCase();
      const stage = (d.workflow_stage || '').toUpperCase();
      const attention = (d.merchant_attention_state || '').toUpperCase();

      if (activeTab === 'needs_attention') {
        return (
          attention === 'ACTION_REQUIRED' ||
          attention === 'REVIEW_RECOMMENDED' ||
          stage === 'MERCHANT_REVIEW'
        );
      }
      if (activeTab === 'in_review') {
        return stage === 'SUBMITTED' || status === 'UNDER_REVIEW' || attention === 'WAITING';
      }
      if (activeTab === 'resolved') {
        return status === 'WON' || status === 'LOST' || status === 'CLOSED' || stage === 'RESOLVED';
      }
      return true;
    });
  }, [disputes, activeTab, searchQuery]);

  return (
    <div className="w-full flex-1 flex flex-col space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-1 border-b border-slate-200/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Disputes</h1>
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
            Manage incoming chargebacks, AI-collected evidence, and response packages
          </p>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1 overflow-x-auto">
          {[
            { id: 'all', label: `All (${disputes.length})` },
            { id: 'needs_attention', label: 'Needs Attention' },
            { id: 'in_review', label: 'Under Review' },
            { id: 'resolved', label: 'Resolved' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-slate-900 text-white shadow-2xs font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter list..."
            className="w-full bg-white text-xs text-slate-900 placeholder-slate-400 rounded-lg px-3 py-1.5 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 shadow-2xs"
          />
        </div>
      </div>

      {/* Disputes List */}
      {isLoading ? (
        <div className="space-y-2.5 flex-1">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : error ? (
        <Card className="text-center py-10 flex-1 flex flex-col items-center justify-center">
          <p className="text-sm text-rose-600">{error}</p>
        </Card>
      ) : filteredDisputes.length === 0 ? (
        <Card className="text-center py-12 bg-white flex-1 flex flex-col items-center justify-center border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">No disputes found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            {isLive && disputes.length === 0
              ? 'No active disputes in Live mode yet. You can use the Razorpay Simulator to simulate an inbound chargeback.'
              : 'No dispute cases match the selected filter.'}
          </p>
        </Card>
      ) : (
        <div className="space-y-2.5 flex-1">
          {filteredDisputes.map((d) => {
            const priority = formatPriority(d.urgency_level, d.remaining_hours, d.merchant_attention_state);
            const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
            const deadlineStr = formatDeadlineText(d.respond_by, d.remaining_hours);

            return (
              <Card
                key={d.dispute_id}
                hoverEffect
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3.5 border-slate-200 bg-white"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-xs sm:text-sm text-slate-900 font-mono">{d.dispute_id}</span>
                    <span className="text-xs font-semibold text-slate-700">· {formatReasonCode(d.reason_code)}</span>
                    <span className="text-xs font-bold text-slate-900">· {formatCurrency(d.amount, d.currency || 'INR')}</span>

                    <div className="flex items-center gap-1.5 ml-auto sm:ml-2">
                      <span className={`px-2 py-0.5 text-[10px] sm:text-[11px] font-bold rounded border ${priority.colorClass}`}>
                        {priority.label}
                      </span>
                      <span className={`px-2 py-0.5 text-[10px] sm:text-[11px] font-semibold rounded border ${statusInfo.colorClass}`}>
                        {statusInfo.label}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-y-1 gap-x-3.5 text-xs text-slate-500">
                    <span className="font-semibold text-slate-700">{deadlineStr}</span>
                    <span>Customer: <strong className="text-slate-800 font-normal">{d.customer_id}</strong></span>
                    <span>Transaction: <strong className="text-slate-800 font-normal">{d.transaction_id}</strong></span>
                    <span>Received: {formatDate(d.created_at)}</span>
                  </div>
                </div>

                <div className="shrink-0 flex items-center justify-end">
                  <Button
                    onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                    variant={statusInfo.isActionable ? 'primary' : 'outline'}
                    size="sm"
                    className="w-full sm:w-auto font-semibold"
                  >
                    {statusInfo.isActionable ? 'Review Case →' : 'View Details →'}
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

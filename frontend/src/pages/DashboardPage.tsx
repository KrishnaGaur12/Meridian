import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { dashboardService, DashboardData } from '../services/dashboardService';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { useDatabaseMode } from '../context/DatabaseModeContext';
import { formatCurrency, formatReasonCode, formatPriority, formatStatus, formatDeadlineText, formatDate } from '../utils/formatters';

export const DashboardPage: React.FC = () => {
  const { isLive, modeVersion } = useDatabaseMode();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeAttentionTab, setActiveAttentionTab] = useState<'ALL' | 'ACTION_REQUIRED' | 'REVIEW_RECOMMENDED' | 'AI_HANDLING' | 'SUBMITTED'>('ALL');
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await dashboardService.getDashboardData();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to dispute service');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData, modeVersion]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  if (isLoading && !data) {
    return (
      <div className="space-y-4 animate-in fade-in duration-150 flex-1">
        <div className="space-y-1">
          <Skeleton className="h-6 w-56" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <Card className="p-6 text-center max-w-lg mx-auto my-6 flex-1 flex flex-col items-center justify-center">
        <div className="w-9 h-9 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-2 font-bold text-sm">
          !
        </div>
        <h3 className="text-sm font-semibold text-slate-900">Couldn't load dashboard data</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          {error}
        </p>
        <div className="mt-4">
          <Button onClick={loadData} variant="primary" size="sm">
            Try again
          </Button>
        </div>
      </Card>
    );
  }

  const { stats, buckets, needsAttentionDisputes, recentDisputes, allDisputes } = data || {
    stats: {
      activeCount: 0,
      actionRequiredCount: 0,
      reviewRecommendedCount: 0,
      aiHandlingCount: 0,
      submittedCount: 0,
      resolvedCount: 0,
      totalAtRiskAmount: 0,
      totalRecoveredAmount: 0,
      currency: 'INR',
    },
    buckets: {
      actionRequired: [],
      reviewRecommended: [],
      aiHandling: [],
      submitted: [],
      resolved: [],
    },
    needsAttentionDisputes: [],
    recentDisputes: [],
    resolvedDisputes: [],
    allDisputes: [],
  };

  // Filter disputes according to active attention bucket tab
  const displayedDisputes =
    activeAttentionTab === 'ACTION_REQUIRED'
      ? buckets.actionRequired
      : activeAttentionTab === 'REVIEW_RECOMMENDED'
      ? buckets.reviewRecommended
      : activeAttentionTab === 'AI_HANDLING'
      ? buckets.aiHandling
      : activeAttentionTab === 'SUBMITTED'
      ? buckets.submitted
      : needsAttentionDisputes.length > 0
      ? needsAttentionDisputes
      : allDisputes.filter(
          (d) =>
            d.status !== 'WON' &&
            d.status !== 'LOST' &&
            d.status !== 'CLOSED' &&
            d.workflow_stage !== 'RESOLVED'
        );

  return (
    <div className="space-y-4 flex-1 flex flex-col">
      {/* 1. Header & Dynamic Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-1 border-b border-slate-200/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {getGreeting()}, Acme Merchant
            </h1>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                isLive
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            >
              {isLive ? 'LIVE RAZORPAY MODE' : 'DEMO WORKSPACE'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated chargeback triage, AI evidence synthesis, and representation management.
          </p>
        </div>

        {/* Primary Operational CTA */}
        {needsAttentionDisputes.length > 0 && (
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-medium text-slate-600">
              <strong className="text-indigo-600 font-bold">{needsAttentionDisputes.length}</strong> cases ready for merchant review
            </span>
            <Button
              onClick={() => {
                const el = document.getElementById('needs-attention-queue');
                el?.scrollIntoView({ behavior: 'smooth' });
              }}
              variant="primary"
              size="sm"
            >
              Review Cases &darr;
            </Button>
          </div>
        )}
      </div>

      {/* 2. Merchant Attention State Metric Buckets */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Bucket 1: ACTION REQUIRED */}
        <Card
          onClick={() => setActiveAttentionTab('ACTION_REQUIRED')}
          className={`p-3.5 border transition cursor-pointer ${
            activeAttentionTab === 'ACTION_REQUIRED'
              ? 'border-rose-500 bg-rose-50/60 ring-1 ring-rose-300'
              : 'border-rose-200 bg-rose-50/20 hover:bg-rose-50/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-rose-800 uppercase tracking-wide font-mono">
              Action Required
            </span>
            <span className="w-2 h-2 rounded-full bg-rose-500" />
          </div>
          <div className="text-2xl font-black text-rose-900 mt-1">
            {stats.actionRequiredCount}
          </div>
          <div className="text-[11px] text-rose-700 mt-0.5 font-medium">
            Immediate evidence or blocker
          </div>
        </Card>

        {/* Bucket 2: REVIEW RECOMMENDED */}
        <Card
          onClick={() => setActiveAttentionTab('REVIEW_RECOMMENDED')}
          className={`p-3.5 border transition cursor-pointer ${
            activeAttentionTab === 'REVIEW_RECOMMENDED'
              ? 'border-amber-500 bg-amber-50/60 ring-1 ring-amber-300'
              : 'border-amber-200 bg-amber-50/20 hover:bg-amber-50/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wide font-mono">
              Review Recommended
            </span>
            <span className="w-2 h-2 rounded-full bg-amber-500" />
          </div>
          <div className="text-2xl font-black text-amber-900 mt-1">
            {stats.reviewRecommendedCount}
          </div>
          <div className="text-[11px] text-amber-700 mt-0.5 font-medium">
            AI evaluated · Ready for merchant sign-off
          </div>
        </Card>

        {/* Bucket 3: AI HANDLING */}
        <Card
          onClick={() => setActiveAttentionTab('AI_HANDLING')}
          className={`p-3.5 border transition cursor-pointer ${
            activeAttentionTab === 'AI_HANDLING'
              ? 'border-blue-500 bg-blue-50/60 ring-1 ring-blue-300'
              : 'border-blue-200 bg-blue-50/20 hover:bg-blue-50/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-800 uppercase tracking-wide font-mono">
              AI Handling
            </span>
            <span className="w-2 h-2 rounded-full bg-blue-500" />
          </div>
          <div className="text-2xl font-black text-blue-900 mt-1">
            {stats.aiHandlingCount}
          </div>
          <div className="text-[11px] text-blue-700 mt-0.5 font-medium">
            Background evidence retrieval
          </div>
        </Card>

        {/* Bucket 4: SUBMITTED */}
        <Card
          onClick={() => setActiveAttentionTab('SUBMITTED')}
          className={`p-3.5 border transition cursor-pointer ${
            activeAttentionTab === 'SUBMITTED'
              ? 'border-slate-800 bg-slate-100 ring-1 ring-slate-400'
              : 'border-slate-200 bg-white hover:bg-slate-50'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wide font-mono">
              Submitted
            </span>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">
            {stats.submittedCount}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5 font-medium">
            Awaiting Razorpay gateway review
          </div>
        </Card>
      </div>

      {/* 3. Primary Operational Queue: Attention-Filtered Cases */}
      <div id="needs-attention-queue" className="space-y-3 pt-1">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>Merchant Review Queue</span>
              {activeAttentionTab !== 'ALL' && (
                <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full font-mono">
                  Filtered: {activeAttentionTab.replace(/_/g, ' ')}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-500">
              Click any card to enter the Merchant Control Center and review AI findings
            </p>
          </div>

          <div className="flex items-center gap-1">
            {activeAttentionTab !== 'ALL' && (
              <button
                onClick={() => setActiveAttentionTab('ALL')}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer underline mr-2"
              >
                Clear filter
              </button>
            )}
            <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
              {displayedDisputes.length} {displayedDisputes.length === 1 ? 'case' : 'cases'}
            </span>
          </div>
        </div>

        {displayedDisputes.length === 0 ? (
          <Card className="p-8 text-center bg-white border-slate-200">
            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-2 font-bold text-xs">
              ✓
            </div>
            <h3 className="text-xs font-semibold text-slate-900">Queue is clear</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              No dispute cases match the selected attention state.
            </p>
          </Card>
        ) : (
          <div className="grid gap-2.5">
            {displayedDisputes.map((d) => {
              const priority = formatPriority(d.urgency_level, d.remaining_hours, d.merchant_attention_state);
              const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
              const deadlineStr = formatDeadlineText(d.respond_by, d.remaining_hours);

              return (
                <Card
                  key={d.dispute_id}
                  hoverEffect
                  className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 border-slate-200 bg-white"
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

                    <div className="flex flex-wrap items-center gap-y-0.5 gap-x-3.5 text-xs text-slate-500">
                      <span className="font-semibold text-rose-700">{deadlineStr}</span>
                      <span>Customer: <strong className="text-slate-800 font-medium">{d.customer_id}</strong></span>
                      <span>Transaction: <strong className="text-slate-800 font-medium">{d.transaction_id}</strong></span>
                      <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.2 rounded text-slate-600">
                        {d.merchant_attention_state || 'REVIEW_RECOMMENDED'}
                      </span>
                    </div>

                    {d.attention_reason && (
                      <p className="text-xs text-slate-600 bg-slate-50 p-2 rounded-md border border-slate-100 leading-relaxed">
                        {d.attention_reason}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center justify-end">
                    <Button
                      onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                      variant="primary"
                      size="sm"
                      className="w-full sm:w-auto font-semibold shadow-xs"
                    >
                      Open Review &rarr;
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. Recent Activity & Historical Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
        {/* Recent Activity */}
        <Card className="p-4 bg-white border-slate-200">
          <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide font-mono">Recent Activity</h3>
            <span className="text-[10px] text-slate-400 font-mono">Live event stream</span>
          </div>

          <div className="space-y-1.5">
            {recentDisputes.length === 0 ? (
              <p className="text-xs text-slate-400 py-2">No recent dispute activity recorded.</p>
            ) : (
              recentDisputes.slice(0, 4).map((d) => (
                <div
                  key={d.dispute_id}
                  className="flex items-center justify-between text-xs py-1 border-b border-slate-100 last:border-0"
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 shrink-0" />
                    <span className="text-slate-700 truncate text-xs">
                      Dispute {d.status === 'WON' ? 'won' : d.status === 'LOST' ? 'lost' : d.workflow_stage === 'SUBMITTED' ? 'submitted' : 'received'} · <strong className="font-semibold text-slate-900 font-mono">{d.dispute_id}</strong>
                    </span>
                  </div>
                  <span className="text-slate-400 shrink-0 text-[10px] ml-2 font-mono">
                    {formatDate(d.created_at)}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Dispute History Summary */}
        <Card className="p-4 flex flex-col justify-between bg-white border-slate-200">
          <div>
            <div className="flex items-center justify-between mb-1 pb-1.5 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide font-mono">Resolved Archive</h3>
              <Link to="/history" className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
                View all &rarr;
              </Link>
            </div>
            <p className="text-xs text-slate-500">
              Access closed, won, lost, or conceded cases without cluttering your active review queue.
            </p>

            <div className="mt-3 p-2.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between text-xs">
              <div>
                <span className="text-slate-500 text-[11px]">Resolved Cases</span>
                <div className="text-sm font-bold text-slate-900">{stats.resolvedCount} cases</div>
              </div>
              <div className="text-right">
                <span className="text-slate-500 text-[11px]">Recovered Value</span>
                <div className="text-sm font-bold text-emerald-700">
                  {formatCurrency(stats.totalRecoveredAmount, stats.currency)}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-100 flex justify-end">
            <Button onClick={() => navigate('/history')} variant="outline" size="sm">
              Open History Archive &rarr;
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};

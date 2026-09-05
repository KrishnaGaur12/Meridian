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
          <Skeleton className="h-6 w-56 bg-slate-800/50" />
          <Skeleton className="h-4 w-40 bg-slate-800/50" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Skeleton className="h-24 bg-slate-800/50" />
          <Skeleton className="h-24 bg-slate-800/50" />
          <Skeleton className="h-24 bg-slate-800/50" />
          <Skeleton className="h-24 bg-slate-800/50" />
        </div>
        <Skeleton className="h-64 bg-slate-800/50" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-6 text-center max-w-lg mx-auto my-6 flex-1 flex flex-col items-center justify-center cyber-card rounded-2xl">
        <div className="w-12 h-12 rounded-full bg-rose-900/30 text-rose-400 flex items-center justify-center mx-auto mb-3 font-bold text-lg border border-rose-500/30">
          !
        </div>
        <h3 className="text-sm font-semibold text-slate-200">Couldn't load dashboard data</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
          {error}
        </p>
        <div className="mt-5">
          <Button onClick={loadData} variant="primary" size="sm" className="bg-cyan-600 hover:bg-cyan-500">
            Try again
          </Button>
        </div>
      </div>
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
    buckets: { actionRequired: [], reviewRecommended: [], aiHandling: [], submitted: [], resolved: [] },
    needsAttentionDisputes: [], recentDisputes: [], resolvedDisputes: [], allDisputes: [],
  };

  const displayedDisputes =
    activeAttentionTab === 'ACTION_REQUIRED' ? buckets.actionRequired
      : activeAttentionTab === 'REVIEW_RECOMMENDED' ? buckets.reviewRecommended
      : activeAttentionTab === 'AI_HANDLING' ? buckets.aiHandling
      : activeAttentionTab === 'SUBMITTED' ? buckets.submitted
      : needsAttentionDisputes.length > 0 ? needsAttentionDisputes
      : allDisputes.filter(d => d.status !== 'WON' && d.status !== 'LOST' && d.status !== 'CLOSED' && d.workflow_stage !== 'RESOLVED');

  return (
    <div className="space-y-6 flex-1 flex flex-col">
      {/* 1. Header & Dynamic Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-slate-700/50 relative">
        <div className="absolute -bottom-px left-0 w-1/3 h-px bg-gradient-to-r from-cyan-500/50 to-transparent"></div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white tracking-tight drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
              {getGreeting()}, Nexus Electronics
            </h1>
            <span
              className={`px-2.5 py-0.5 text-[10px] font-bold rounded-md border ${
                isLive
                  ? 'bg-emerald-900/40 text-emerald-300 border-emerald-500/50 shadow-[0_0_10px_-2px_rgba(16,185,129,0.3)]'
                  : 'bg-slate-800 text-slate-300 border-slate-600'
              }`}
            >
              {isLive ? 'LIVE GATEWAY MODE' : 'DEMO WORKSPACE'}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1.5 max-w-2xl">
            Automated chargeback triage, AI evidence synthesis, and representation management framework.
          </p>
        </div>

        {/* Primary Operational CTA */}
        {needsAttentionDisputes.length > 0 && (
          <div className="flex items-center gap-3 bg-violet-900/20 p-2 pl-4 rounded-xl border border-violet-500/20">
            <span className="text-sm font-medium text-violet-200">
              <strong className="text-violet-400 font-black text-lg drop-shadow-[0_0_5px_rgba(139,92,246,0.5)]">{needsAttentionDisputes.length}</strong> cases ready for review
            </span>
            <button
              onClick={() => {
                document.getElementById('needs-attention-queue')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-[0_0_15px_-3px_rgba(139,92,246,0.5)] transition-all"
            >
              Review Queue &darr;
            </button>
          </div>
        )}
      </div>

      {/* 2. Merchant Attention State Metric Buckets */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Bucket 1: ACTION REQUIRED */}
        <div
          onClick={() => setActiveAttentionTab('ACTION_REQUIRED')}
          className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 ${
            activeAttentionTab === 'ACTION_REQUIRED'
              ? 'bg-rose-900/40 border border-rose-500 shadow-[0_0_20px_-5px_rgba(244,63,94,0.4)] transform -translate-y-1'
              : 'cyber-card hover:cyber-card-danger'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-rose-300 uppercase tracking-widest font-mono">
              Action Required
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)] animate-pulse" />
          </div>
          <div className="text-4xl font-black text-white mt-3 tracking-tight drop-shadow-md">
            {stats.actionRequiredCount}
          </div>
          <div className="text-xs text-rose-200 mt-1.5 font-medium opacity-80">
            Immediate evidence or blocker
          </div>
        </div>

        {/* Bucket 2: REVIEW RECOMMENDED */}
        <div
          onClick={() => setActiveAttentionTab('REVIEW_RECOMMENDED')}
          className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 ${
            activeAttentionTab === 'REVIEW_RECOMMENDED'
              ? 'bg-amber-900/40 border border-amber-500 shadow-[0_0_20px_-5px_rgba(245,158,11,0.4)] transform -translate-y-1'
              : 'cyber-card hover:cyber-card-warning'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-amber-300 uppercase tracking-widest font-mono">
              Review Recommended
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]" />
          </div>
          <div className="text-4xl font-black text-white mt-3 tracking-tight drop-shadow-md">
            {stats.reviewRecommendedCount}
          </div>
          <div className="text-xs text-amber-200 mt-1.5 font-medium opacity-80">
            AI evaluated · Ready for sign-off
          </div>
        </div>

        {/* Bucket 3: AI HANDLING */}
        <div
          onClick={() => setActiveAttentionTab('AI_HANDLING')}
          className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 ${
            activeAttentionTab === 'AI_HANDLING'
              ? 'bg-violet-900/40 border border-violet-500 shadow-[0_0_20px_-5px_rgba(139,92,246,0.4)] transform -translate-y-1'
              : 'cyber-card hover:cyber-card-ai'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-violet-300 uppercase tracking-widest font-mono">
              AI Handling
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.8)]" />
          </div>
          <div className="text-4xl font-black text-white mt-3 tracking-tight drop-shadow-md">
            {stats.aiHandlingCount}
          </div>
          <div className="text-xs text-violet-200 mt-1.5 font-medium opacity-80">
            Background evidence retrieval
          </div>
        </div>

        {/* Bucket 4: SUBMITTED */}
        <div
          onClick={() => setActiveAttentionTab('SUBMITTED')}
          className={`p-5 rounded-2xl cursor-pointer transition-all duration-300 ${
            activeAttentionTab === 'SUBMITTED'
              ? 'bg-cyan-900/40 border border-cyan-500 shadow-[0_0_20px_-5px_rgba(6,182,212,0.4)] transform -translate-y-1'
              : 'cyber-card hover:border-cyan-500/40'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-cyan-300 uppercase tracking-widest font-mono">
              Submitted
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
          </div>
          <div className="text-4xl font-black text-white mt-3 tracking-tight drop-shadow-md">
            {stats.submittedCount}
          </div>
          <div className="text-xs text-cyan-200 mt-1.5 font-medium opacity-80">
            Awaiting Gateway review
          </div>
        </div>
      </div>

      {/* 3. Primary Operational Queue */}
      <div id="needs-attention-queue" className="space-y-4 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-3">
              <span>Merchant Review Queue</span>
              {activeAttentionTab !== 'ALL' && (
                <span className="text-[10px] font-bold text-cyan-300 bg-cyan-900/50 border border-cyan-500/30 px-2 py-0.5 rounded uppercase tracking-widest shadow-[0_0_8px_rgba(6,182,212,0.2)]">
                  Filter: {activeAttentionTab.replace(/_/g, ' ')}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Select a case to enter the Merchant Control Center and review AI findings
            </p>
          </div>

          <div className="flex items-center gap-3">
            {activeAttentionTab !== 'ALL' && (
              <button
                onClick={() => setActiveAttentionTab('ALL')}
                className="text-xs text-rose-400 hover:text-rose-300 font-semibold cursor-pointer underline transition-colors"
              >
                Clear filter
              </button>
            )}
            <span className="text-xs font-semibold text-cyan-400 bg-cyan-900/30 px-3 py-1.5 rounded-lg border border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.1)]">
              {displayedDisputes.length} {displayedDisputes.length === 1 ? 'case' : 'cases'}
            </span>
          </div>
        </div>

        {displayedDisputes.length === 0 ? (
          <div className="p-12 text-center cyber-card rounded-2xl flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-emerald-900/30 text-emerald-400 flex items-center justify-center mb-4 font-bold text-lg border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              ✓
            </div>
            <h3 className="text-lg font-bold text-white tracking-wide">Queue is clear</h3>
            <p className="text-sm text-slate-400 mt-2">
              No dispute cases match the selected attention state.
            </p>
          </div>
        ) : (
          <div className="grid gap-3">
            {displayedDisputes.map((d) => {
              const priority = formatPriority(d.urgency_level, d.remaining_hours, d.merchant_attention_state);
              const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
              const deadlineStr = formatDeadlineText(d.respond_by, d.remaining_hours);

              return (
                <div
                  key={d.dispute_id}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cyber-card rounded-xl hover:border-cyan-500/50 group"
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
                      <p className="text-xs text-slate-300 bg-slate-900/50 p-2.5 rounded-lg border border-slate-700/50 leading-relaxed">
                        {d.attention_reason}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center justify-end">
                    <button
                      onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                      className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-[0_0_15px_-3px_rgba(6,182,212,0.5)] transition-all group-hover:scale-105"
                    >
                      Open Terminal &rarr;
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. Recent Activity & Historical Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 pb-8">
        {/* Recent Activity */}
        <div className="p-5 cyber-card rounded-2xl flex flex-col h-full">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-700/50 relative">
            <h3 className="text-xs font-bold text-white uppercase tracking-widest font-mono">Recent Activity</h3>
            <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
              Live stream
            </span>
          </div>

          <div className="space-y-1 flex-1">
            {recentDisputes.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">No recent activity detected.</p>
            ) : (
              recentDisputes.slice(0, 5).map((d) => (
                <div
                  key={d.dispute_id}
                  className="flex items-center justify-between text-xs py-2.5 border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 px-2 rounded-md transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400 shrink-0 shadow-[0_0_8px_rgba(167,139,250,0.8)]" />
                    <span className="text-slate-300 truncate text-[12px]">
                      Dispute {d.status === 'WON' ? 'won' : d.status === 'LOST' ? 'lost' : d.workflow_stage === 'SUBMITTED' ? 'submitted' : 'received'} · <strong className="font-semibold text-white font-mono">{d.dispute_id}</strong>
                    </span>
                  </div>
                  <span className="text-slate-500 shrink-0 text-[10px] ml-3 font-mono">
                    {formatDate(d.created_at)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Dispute History Summary */}
        <div className="p-5 flex flex-col justify-between cyber-card rounded-2xl h-full">
          <div>
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-slate-700/50">
              <h3 className="text-xs font-bold text-white uppercase tracking-widest font-mono">Resolved Archive</h3>
              <Link to="/history" className="text-[10px] font-bold text-cyan-400 hover:text-cyan-300 transition-colors uppercase tracking-widest">
                Access Data &rarr;
              </Link>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Access closed, won, lost, or conceded cases without cluttering your active operational queue.
            </p>

            <div className="mt-5 p-3.5 bg-slate-900/60 rounded-xl border border-slate-700/50 flex items-center justify-between">
              <div>
                <span className="text-slate-500 text-[10px] uppercase tracking-wider font-mono">Resolved Cases</span>
                <div className="text-xl font-black text-white mt-0.5 tracking-tight">{stats.resolvedCount} <span className="text-sm font-normal text-slate-500">cases</span></div>
              </div>
              <div className="text-right">
                <span className="text-slate-500 text-[10px] uppercase tracking-wider font-mono">Recovered Value</span>
                <div className="text-xl font-black text-emerald-400 mt-0.5 tracking-tight drop-shadow-[0_0_5px_rgba(52,211,153,0.3)]">
                  {formatCurrency(stats.totalRecoveredAmount, stats.currency)}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-700/50 flex justify-end">
            <button 
              onClick={() => navigate('/history')}
              className="bg-transparent border border-cyan-500/30 text-cyan-400 hover:bg-cyan-900/30 text-xs font-bold px-4 py-2 rounded-lg transition-all"
            >
              Open Archive Database
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

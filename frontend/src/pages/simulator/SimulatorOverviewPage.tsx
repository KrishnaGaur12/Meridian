import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { dashboardService, DashboardData } from '../../services/dashboardService';
import { transactionService } from '../../services/transactionService';
import { Transaction } from '../../types/transaction';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Skeleton } from '../../components/common/Skeleton';
import { useDatabaseMode } from '../../context/DatabaseModeContext';
import { formatCurrency, formatReasonCode, formatStatus } from '../../utils/formatters';

export const SimulatorOverviewPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [data, setData] = useState<DashboardData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const loadOpsData = async () => {
      try {
        setIsLoading(true);
        const [dashData, txnData] = await Promise.all([
          dashboardService.getDashboardData(),
          transactionService.getTransactions().catch(() => []),
        ]);
        if (isMounted) {
          setData(dashData);
          setTransactions(txnData);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    loadOpsData();
    return () => {
      isMounted = false;
    };
  }, [modeVersion]);

  if (isLoading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      </div>
    );
  }

  const stats = data?.stats || {
    activeCount: 0,
    needsReviewCount: 0,
    submittedCount: 0,
    resolvedCount: 0,
    totalAtRiskAmount: 0,
    totalRecoveredAmount: 0,
    currency: 'INR',
  };

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-4 sm:p-5 rounded-xl shadow-xs border border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-indigo-700 uppercase tracking-widest font-semibold">
              Razorpay Operations Console
            </span>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                isLive
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            >
              {isLive ? 'LIVE NETWORK' : 'DEMO SANDBOX'}
            </span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold text-slate-900 mt-0.5">Network Simulation & Dispute Dispatcher</h1>
          <p className="text-xs text-slate-500 mt-0.5 max-w-xl">
            Simulate incoming bank chargebacks against merchant transactions. Monitor autonomous AI triage and representation generation in real time.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            onClick={() => navigate('/simulator/raise-dispute')}
            variant="primary"
            size="sm"
            className="bg-rose-600 hover:bg-rose-700 font-semibold shadow-xs"
          >
            + Raise New Dispute &rarr;
          </Button>
        </div>
      </div>

      {/* Operational Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="p-3.5 bg-white">
          <div className="text-[11px] font-medium text-slate-500">Total Transactions</div>
          <div className="text-xl font-bold text-slate-900 mt-0.5">{transactions.length}</div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">In active database</div>
        </Card>

        <Card className="p-3.5 bg-white">
          <div className="text-[11px] font-medium text-slate-500">Active Disputes</div>
          <div className="text-xl font-bold text-indigo-600 mt-0.5">{stats.activeCount}</div>
          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">Dispute registry</div>
        </Card>

        <Card className="p-3.5 bg-white">
          <div className="text-[11px] font-medium text-amber-800">Awaiting Merchant</div>
          <div className="text-xl font-bold text-amber-900 mt-0.5">{stats.needsReviewCount}</div>
          <div className="text-[10px] text-amber-700/80 mt-0.5 font-mono">Pending evidence</div>
        </Card>

        <Card className="p-3.5 bg-white">
          <div className="text-[11px] font-medium text-blue-800">Submitted</div>
          <div className="text-xl font-bold text-blue-900 mt-0.5">{stats.submittedCount}</div>
          <div className="text-[10px] text-blue-700/80 mt-0.5 font-mono">In gateway review</div>
        </Card>

        <Card className="p-3.5 bg-white">
          <div className="text-[11px] font-medium text-emerald-800">Resolved Cases</div>
          <div className="text-xl font-bold text-emerald-900 mt-0.5">{stats.resolvedCount}</div>
          <div className="text-[10px] text-emerald-700/80 mt-0.5 font-mono">Won / Lost / Conceded</div>
        </Card>
      </div>

      {/* Recent Disputes & Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Active Simulation Disputes */}
        <Card className="p-4 space-y-2.5 bg-white">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Recent Network Disputes
            </h3>
            <Link to="/simulator/disputes" className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold">
              View all &rarr;
            </Link>
          </div>

          <div className="space-y-1.5">
            {(data?.allDisputes || []).length === 0 ? (
              <p className="text-xs text-slate-400 py-3 text-center">No disputes registered in active mode.</p>
            ) : (
              (data?.allDisputes || []).slice(0, 4).map((d) => {
                const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
                return (
                  <div
                    key={d.dispute_id}
                    className="flex items-center justify-between p-2 bg-slate-50 rounded-lg border border-slate-100 text-xs"
                  >
                    <div>
                      <div className="font-bold text-slate-900 flex items-center gap-1.5">
                        <span className="font-mono">{d.dispute_id}</span>
                        <span className="font-normal text-slate-500 font-mono text-[10px]">[{d.case_source}]</span>
                      </div>
                      <div className="text-[11px] text-slate-500">{formatReasonCode(d.reason_code)}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-slate-900">{formatCurrency(d.amount, d.currency || 'INR')}</div>
                      <span className={`text-[10px] font-semibold ${statusInfo.colorClass.split(' ')[0]}`}>
                        {statusInfo.label}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* Available Transactions for Simulation */}
        <Card className="p-4 space-y-2.5 bg-white">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Transactions in Database
            </h3>
            <Link to="/simulator/transactions" className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold">
              Browse all &rarr;
            </Link>
          </div>

          <div className="space-y-1.5">
            {transactions.slice(0, 4).map((t) => (
              <div
                key={t.transaction_id}
                className="flex items-center justify-between p-2 bg-slate-50 rounded-lg border border-slate-100 text-xs"
              >
                <div>
                  <div className="font-mono font-bold text-slate-900">{t.transaction_id}</div>
                  <div className="text-[11px] text-slate-500">{t.customer_id} · {t.payment_method?.toUpperCase()}</div>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="font-semibold text-slate-900">{formatCurrency(t.amount, t.currency)}</span>
                  <Link
                    to={`/simulator/raise-dispute?txn=${t.transaction_id}`}
                    className="px-2 py-0.5 text-[11px] font-semibold bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 rounded transition"
                  >
                    + Dispute
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

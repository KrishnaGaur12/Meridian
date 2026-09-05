import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { disputeService } from '../../services/disputeService';
import { Dispute } from '../../types/dispute';
import { Card } from '../../components/common/Card';
import { Skeleton } from '../../components/common/Skeleton';
import { useDatabaseMode } from '../../context/DatabaseModeContext';
import { formatCurrency, formatReasonCode, formatStatus } from '../../utils/formatters';

export const SimulatorDisputesPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    disputeService
      .getDisputes()
      .then((data) => {
        if (isMounted) setDisputes(data);
      })
      .catch(() => {
        if (isMounted) setDisputes([]);
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
      <div className="flex items-center justify-between pb-1 border-b border-slate-200/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Network Dispute Registry</h1>
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
            Operational overview of all chargeback cases stored in the active database
          </p>
        </div>

        <Link
          to="/simulator/raise-dispute"
          className="px-3 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-md transition shadow-2xs"
        >
          + Raise Dispute
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : disputes.length === 0 ? (
        <Card className="p-10 text-center bg-white border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">No disputes registered in active mode</h3>
          <p className="text-xs text-slate-500 mt-1">
            {isLive
              ? 'No disputes exist in the Live database. Click "+ Raise Dispute" to simulate an incoming chargeback.'
              : 'No demo disputes found.'}
          </p>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden bg-white border-slate-200">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-3.5 py-2.5 font-semibold">Dispute ID</th>
                  <th className="px-3.5 py-2.5 font-semibold">Source</th>
                  <th className="px-3.5 py-2.5 font-semibold">Transaction</th>
                  <th className="px-3.5 py-2.5 font-semibold">Reason</th>
                  <th className="px-3.5 py-2.5 font-semibold">Amount</th>
                  <th className="px-3.5 py-2.5 font-semibold">Stage</th>
                  <th className="px-3.5 py-2.5 font-semibold">Status</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">Merchant View</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {disputes.map((d) => {
                  const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
                  return (
                    <tr key={d.dispute_id} className="hover:bg-slate-50/80 transition">
                      <td className="px-3.5 py-2.5 font-mono font-bold text-slate-900">{d.dispute_id}</td>
                      <td className="px-3.5 py-2.5">
                        <span className="px-1.5 py-0.2 text-[10px] font-mono rounded bg-slate-100 text-slate-600 font-medium">
                          {d.case_source}
                        </span>
                      </td>
                      <td className="px-3.5 py-2.5 font-mono text-slate-600">{d.transaction_id}</td>
                      <td className="px-3.5 py-2.5 text-slate-700">{formatReasonCode(d.reason_code)}</td>
                      <td className="px-3.5 py-2.5 font-semibold text-slate-900">
                        {formatCurrency(d.amount, d.currency || 'INR')}
                      </td>
                      <td className="px-3.5 py-2.5 font-mono text-[11px] text-slate-500">{d.workflow_stage}</td>
                      <td className="px-3.5 py-2.5">
                        <span className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${statusInfo.colorClass}`}>
                          {statusInfo.label}
                        </span>
                      </td>
                      <td className="px-3.5 py-2.5 text-right">
                        <Link
                          to={`/disputes/${d.dispute_id}`}
                          className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                        >
                          Workspace &rarr;
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import { transactionService } from '../../services/transactionService';
import { Card } from '../../components/common/Card';
import { Skeleton } from '../../components/common/Skeleton';
import { useDatabaseMode } from '../../context/DatabaseModeContext';
import { formatCurrency } from '../../utils/formatters';

export const SimulatorCustomersPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [customers, setCustomers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    transactionService
      .getTransactions()
      .then((txns) => {
        if (!isMounted) return;
        const map = new Map<string, { customer_id: string; txnCount: number; totalSpent: number; country: string }>();
        for (const t of txns) {
          const entry = map.get(t.customer_id) || {
            customer_id: t.customer_id,
            txnCount: 0,
            totalSpent: 0,
            country: t.transaction_country || 'IN',
          };
          entry.txnCount += 1;
          entry.totalSpent += t.amount || 0;
          map.set(t.customer_id, entry);
        }
        setCustomers(Array.from(map.values()));
      })
      .catch(() => {
        if (isMounted) setCustomers([]);
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
          <h1 className="text-xl font-bold text-slate-900">Registered Customers</h1>
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
          Customer transaction volumes and historical chargeback profiles in active database
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : customers.length === 0 ? (
        <Card className="p-10 text-center bg-white border-slate-200">
          <p className="text-xs text-slate-500">No customer records in active database.</p>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden bg-white border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-3.5 py-2.5 font-semibold">Customer ID</th>
                <th className="px-3.5 py-2.5 font-semibold">Total Orders</th>
                <th className="px-3.5 py-2.5 font-semibold">Cumulative Spend</th>
                <th className="px-3.5 py-2.5 font-semibold">Country</th>
                <th className="px-3.5 py-2.5 font-semibold">Account Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {customers.map((c) => (
                <tr key={c.customer_id} className="hover:bg-slate-50/80 transition">
                  <td className="px-3.5 py-2.5 font-mono font-bold text-slate-900">{c.customer_id}</td>
                  <td className="px-3.5 py-2.5 text-slate-700">{c.txnCount} orders</td>
                  <td className="px-3.5 py-2.5 font-semibold text-slate-900">{formatCurrency(c.totalSpent)}</td>
                  <td className="px-3.5 py-2.5 font-mono text-slate-500">{c.country}</td>
                  <td className="px-3.5 py-2.5">
                    <span className="px-2 py-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 rounded border border-emerald-200">
                      Active Verified
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
};

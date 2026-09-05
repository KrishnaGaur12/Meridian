import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { transactionService } from '../../services/transactionService';
import { Transaction } from '../../types/transaction';
import { Card } from '../../components/common/Card';
import { Skeleton } from '../../components/common/Skeleton';
import { useDatabaseMode } from '../../context/DatabaseModeContext';
import { formatCurrency } from '../../utils/formatters';

export const SimulatorTransactionsPage: React.FC = () => {
  const { modeVersion, isLive } = useDatabaseMode();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    transactionService
      .getTransactions()
      .then((txns) => {
        if (isMounted) setTransactions(txns);
      })
      .catch(() => {
        if (isMounted) setTransactions([]);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [modeVersion]);

  const filtered = transactions.filter(
    (t) =>
      t.transaction_id.toLowerCase().includes(search.toLowerCase()) ||
      t.customer_id.toLowerCase().includes(search.toLowerCase()) ||
      (t.payment_method && t.payment_method.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-slate-200/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Network Transactions</h1>
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
            Real transactions stored in the active database available for simulated chargeback dispute injection
          </p>
        </div>

        <input
          type="text"
          placeholder="Filter by TXN ID, customer..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:w-60 text-xs bg-white border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 shadow-2xs"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-10 text-center bg-white border-slate-200">
          <p className="text-xs text-slate-500">No transactions match your search filter.</p>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden bg-white border-slate-200">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-3.5 py-2.5 font-semibold">Transaction ID</th>
                  <th className="px-3.5 py-2.5 font-semibold">Customer</th>
                  <th className="px-3.5 py-2.5 font-semibold">Amount</th>
                  <th className="px-3.5 py-2.5 font-semibold">Payment Method</th>
                  <th className="px-3.5 py-2.5 font-semibold">Status</th>
                  <th className="px-3.5 py-2.5 font-semibold">Country</th>
                  <th className="px-3.5 py-2.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((t) => (
                  <tr key={t.transaction_id} className="hover:bg-slate-50/80 transition">
                    <td className="px-3.5 py-2.5 font-mono font-bold text-slate-900">{t.transaction_id}</td>
                    <td className="px-3.5 py-2.5 text-slate-700">{t.customer_id}</td>
                    <td className="px-3.5 py-2.5 font-semibold text-slate-900">{formatCurrency(t.amount, t.currency)}</td>
                    <td className="px-3.5 py-2.5 text-slate-600 uppercase font-mono text-[11px]">{t.payment_method}</td>
                    <td className="px-3.5 py-2.5">
                      <span className="px-2 py-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 rounded border border-emerald-200">
                        {t.transaction_status || 'SUCCESS'}
                      </span>
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-slate-500">{t.transaction_country || 'IN'}</td>
                    <td className="px-3.5 py-2.5 text-right">
                      <Link
                        to={`/simulator/raise-dispute?txn=${t.transaction_id}`}
                        className="px-2 py-0.5 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded transition"
                      >
                        + Dispute
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

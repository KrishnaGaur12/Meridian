import React from 'react';
import { Card } from '../common/Card';
import { formatCurrency, formatDate } from '../../utils/formatters';

interface OutcomeCardProps {
  status: string;
  amount: number;
  currency: string;
  resolvedAt?: string;
  keyFactors?: string[];
  reasonDescription?: string;
}

export const OutcomeCard: React.FC<OutcomeCardProps> = ({
  status,
  amount,
  currency,
  resolvedAt,
  keyFactors = [],
  reasonDescription,
}) => {
  const normalized = status.toUpperCase();
  const isWon = normalized === 'WON';
  const isLost = normalized === 'LOST';
  const isAccepted = normalized === 'CLOSED' || normalized === 'ACCEPTED';

  if (!isWon && !isLost && !isAccepted) return null;

  return (
    <Card
      className={`p-5 border ${
        isWon
          ? 'bg-emerald-50/40 border-emerald-200'
          : isLost
          ? 'bg-rose-50/40 border-rose-200'
          : 'bg-slate-50 border-slate-200'
      }`}
    >
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 pb-3.5 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isWon ? 'bg-emerald-500' : isLost ? 'bg-rose-500' : 'bg-slate-500'
              }`}
            />
            <h3 className="text-lg font-bold text-slate-900">
              {isWon
                ? 'Simulated Gateway Outcome: Dispute Won'
                : isLost
                ? 'Simulated Gateway Outcome: Dispute Lost'
                : 'Dispute Resolved (Merchant Conceded)'}
            </h3>
          </div>
          <p className="text-xs text-slate-600 mt-0.5">
            {isWon
              ? 'Card issuing bank evaluated the submitted representation and ruled in favor of the merchant.'
              : isLost
              ? 'Issuing network determined the evidence did not fully refute the cardholder claim.'
              : 'Merchant chose not to challenge this dispute claim.'}
          </p>
        </div>

        <div className="text-left md:text-right">
          <div className="text-[11px] text-slate-500 font-medium">
            {isWon ? 'Recovered Revenue' : 'Unrecovered Value'}
          </div>
          <div
            className={`text-lg font-bold ${
              isWon ? 'text-emerald-700' : isLost ? 'text-rose-700' : 'text-slate-700'
            }`}
          >
            {formatCurrency(amount, currency)}
          </div>
        </div>
      </div>

      <div className="py-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div>
          <h4 className="font-bold text-slate-900 mb-1">
            {isWon ? 'Decisive Winning Factors' : 'Key Factor in Decision'}
          </h4>
          <ul className="space-y-1 text-slate-700">
            {keyFactors.length > 0 ? (
              keyFactors.map((f, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <span className={isWon ? 'text-emerald-600 font-bold' : 'text-rose-600 font-bold'}>•</span>
                  <span>{f}</span>
                </li>
              ))
            ) : (
              <>
                <li className="flex items-start gap-1.5">
                  <span className="text-emerald-600 font-bold">•</span>
                  <span>Verified carrier delivery tracking with recipient signature</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-emerald-600 font-bold">•</span>
                  <span>Authenticated 3D-Secure transaction gateway authorization</span>
                </li>
              </>
            )}
          </ul>
        </div>

        <div className="p-3 bg-white rounded-xl border border-slate-200">
          <h4 className="font-bold text-slate-900 mb-0.5">Gateway Resolution Note</h4>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            {isWon
              ? 'Fulfilling comprehensive evidence with carrier proof within the deadline window ensured successful recovery.'
              : 'Attaching recipient communications and pre-order terms helps increase defense success rates.'}
          </p>
        </div>
      </div>

      <div className="pt-2.5 border-t border-slate-200/80 text-[10px] text-slate-400 font-mono flex justify-between">
        <span>Gateway Decision Processed</span>
        <span>{formatDate(resolvedAt || new Date().toISOString())}</span>
      </div>
    </Card>
  );
};

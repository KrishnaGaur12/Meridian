import React from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Dispute, DisputeTimelineEvent } from '../../types/dispute';
import { CaseAnalysis } from '../../types/commandCenter';
import { formatCurrency, formatDate } from '../../utils/formatters';

interface CaseOutcomeTabProps {
  dispute: Dispute;
  analysis: CaseAnalysis;
  auditTrail: DisputeTimelineEvent[];
  onBackToReview: () => void;
  onGoToDisputes: () => void;
}

export const CaseOutcomeTab: React.FC<CaseOutcomeTabProps> = ({
  dispute,
  analysis,
  auditTrail,
  onBackToReview,
  onGoToDisputes,
}) => {
  const normStatus = (dispute.status || '').toUpperCase();
  const isWon = normStatus === 'WON';
  const isLost = normStatus === 'LOST';
  const isClosed = normStatus === 'CLOSED';

  const amount = dispute.amount || analysis.amount || 0;
  const currency = dispute.currency || analysis.currency || 'INR';

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* Outcome Banner Card */}
      <Card
        className={`p-6 border shadow-2xs space-y-4 ${
          isWon
            ? 'bg-emerald-50/50 border-emerald-300'
            : isLost
            ? 'bg-rose-50/50 border-rose-300'
            : 'bg-slate-50/80 border-slate-300'
        }`}
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
          <div>
            <span
              className={`text-[10px] font-mono font-bold uppercase tracking-wider ${
                isWon ? 'text-emerald-700' : isLost ? 'text-rose-700' : 'text-slate-600'
              }`}
            >
              Step 7 · Final Outcome
            </span>
            <h2 className="text-xl font-bold text-slate-900 mt-0.5 flex items-center gap-2">
              <span>
                {isWon
                  ? 'Dispute Won — Funds Recovered'
                  : isLost
                  ? 'Dispute Lost'
                  : 'Dispute Conceded & Closed'}
              </span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                  isWon
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : isLost
                    ? 'bg-rose-100 text-rose-800 border-rose-300'
                    : 'bg-slate-200 text-slate-700 border-slate-300'
                }`}
              >
                {dispute.status}
              </span>
            </h2>
          </div>
          <span className="text-[10px] font-mono text-slate-500 bg-white px-2 py-1 rounded border border-slate-200">
            Simulated Gateway Outcome
          </span>
        </div>

        {/* Financial & Summary Grid */}
        <div className="p-4 bg-white rounded-xl border border-slate-200/80 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <span className="text-[10px] font-mono text-slate-400 block">Financial Impact:</span>
            <strong
              className={`text-base font-bold ${
                isWon ? 'text-emerald-700' : isLost ? 'text-rose-700' : 'text-slate-700'
              }`}
            >
              {isWon ? `+${formatCurrency(amount, currency)} Recovered` : `-${formatCurrency(amount, currency)} Lost`}
            </strong>
          </div>
          <div>
            <span className="text-[10px] font-mono text-slate-400 block">Resolution Date:</span>
            <strong className="text-slate-900">{formatDate(dispute.ai_last_checked || dispute.created_at)}</strong>
          </div>
          <div>
            <span className="text-[10px] font-mono text-slate-400 block">Decision Mechanism:</span>
            <span className="font-semibold text-indigo-700 font-mono">Issuing Bank Final Decision</span>
          </div>
        </div>
      </Card>

      {/* Persisted Chronological Audit Stream */}
      <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
            Persisted Chronological Case Audit Trail ({auditTrail.length} Events)
          </h3>
          <span className="text-[10px] font-mono text-slate-400">Database Record Stream</span>
        </div>

        {auditTrail.length === 0 ? (
          <p className="text-xs text-slate-400 py-3">No audit records persisted for this case.</p>
        ) : (
          <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto pr-1">
            {auditTrail.map((evt, idx) => (
              <div key={evt.event_id || idx} className="py-2.5 flex items-start justify-between gap-4 text-xs">
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{evt.title}</span>
                    <span className="font-mono text-[9px] bg-slate-100 px-1.5 py-0.2 rounded text-slate-600">
                      Actor: {evt.actor_type || 'SYSTEM'}
                    </span>
                  </div>
                  <p className="text-slate-600 text-[11px] leading-relaxed">{evt.description}</p>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-[10px] text-slate-400 font-mono block">
                    {formatDate(evt.timestamp)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between pt-2">
        <Button onClick={onBackToReview} variant="outline" size="md">
          &larr; Back to Gateway Review
        </Button>
        <Button onClick={onGoToDisputes} variant="primary" size="md" className="font-semibold shadow-xs">
          Return to Disputes Queue &rarr;
        </Button>
      </div>
    </div>
  );
};

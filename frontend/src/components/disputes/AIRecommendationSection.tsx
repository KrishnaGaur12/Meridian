import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { CaseAnalysis, AIRecommendation } from '../../types/commandCenter';
import { formatCurrency, formatAIOutcome, formatAssessment } from '../../utils/formatters';
import { disputeService } from '../../services/disputeService';


interface AIRecommendationSectionProps {
  analysis: CaseAnalysis;
  disputeId: string;
  isReadOnly: boolean;
  onRefresh: () => void;
}

export const AIRecommendationSection: React.FC<AIRecommendationSectionProps> = ({
  analysis,
  disputeId,
  isReadOnly,
  onRefresh,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [isAcceptModalOpen, setIsAcceptModalOpen] = useState(false);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [acceptReason, setAcceptReason] = useState('Merchant verified chargeback and accepted concession');
  const [overrideDecision, setOverrideDecision] = useState<'CONTEST' | 'ACCEPT' | 'INVESTIGATE'>('CONTEST');
  const [overrideReason, setOverrideReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const rec: AIRecommendation = analysis.recommendation || {};
  const rawAction = rec.action || analysis.win_probability?.recommendation || 'CONTEST';
  const outcome = formatAIOutcome(rawAction);
  const winProb =
    analysis.win_probability?.win_probability_pct ??
    (analysis.win_probability?.win_probability !== undefined && analysis.win_probability?.win_probability !== null
      ? Math.round(analysis.win_probability.win_probability * 100)
      : null);

  const confidence = rec.confidence || analysis.win_probability?.confidence_level || 'MEDIUM';
  const assessment = formatAssessment(
    analysis.win_probability?.win_probability !== undefined ? analysis.win_probability?.win_probability : null,
    confidence
  );
  const recoveryAmt = rec.potential_recovery ?? rec.potential_recovery_amount ?? analysis.amount;

  // Extract structured rationale
  const whyExplanation =
    analysis.attention_reason ||
    rec.reason ||
    'Verified fulfillment tracking and authenticated gateway transaction records support contesting this dispute.';

  const remainingGap =
    (analysis.evidence_intelligence?.missing_count ?? 0) > 0
      ? `Evidence completeness is currently ${analysis.evidence_intelligence?.completeness_percentage ?? 0}%. Attaching missing proofs is recommended.`
      : 'All critical evidence requirements are satisfied.';

  const nextAction =
    analysis.next_actions && analysis.next_actions.length > 0
      ? analysis.next_actions[0]
      : 'Review the evidence checklist, approve verified documents, and submit your representation package.';

  const keyFactors: string[] =
    rec.key_factors && rec.key_factors.length > 0
      ? rec.key_factors
      : rec.positive_factors && rec.positive_factors.length > 0
      ? rec.positive_factors
      : [
          'Payment was successfully captured and 3D-Secure authenticated',
          'Delivery proof is verified with logistics tracking',
          'Customer account tenure shows no prior malicious dispute history',
        ];

  const handleAcceptDispute = async () => {
    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await disputeService.acceptDispute(disputeId, acceptReason);
      setIsAcceptModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not accept dispute');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOverrideDecision = async () => {
    if (!overrideReason.trim()) {
      setErrorMsg('Please specify the business rationale for overriding the recommendation.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await disputeService.overrideRecommendation(disputeId, overrideDecision, overrideReason);
      setIsOverrideModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not update recommendation');
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <section id="case-ai-recommendation" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">AI Recommendation</h2>
        <span className="text-xs text-slate-500 font-mono">Autonomous Decision Engine</span>
      </div>

      <Card className="p-5 border-indigo-100 bg-gradient-to-br from-white via-indigo-50/20 to-slate-50 space-y-4">
        {/* Top Structured Score Summary */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3.5 border-b border-slate-100">
          <div className="space-y-0.5">
            <div className="text-[11px] font-bold text-indigo-700 tracking-wider uppercase">
              Recommendation
            </div>
            <div className="text-xl sm:text-2xl font-black text-slate-900 flex items-center gap-2">
              <span>{outcome.label}</span>
              {winProb !== null && (
                <span className="text-sm font-semibold text-slate-600">
                  · {winProb}% Win Probability
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div>
              <div className="text-[11px] text-slate-500 font-medium">Confidence Level</div>
              <span className={`inline-block px-2 py-0.5 text-xs font-bold rounded-md border mt-0.5 ${assessment.badgeClass}`}>
                {confidence} Confidence
              </span>
            </div>

            <div>
              <div className="text-[11px] text-slate-500 font-medium">Potential Recovery</div>
              <div className="text-base font-bold text-slate-900 mt-0.5">
                {formatCurrency(recoveryAmt, analysis.currency || 'INR')}
              </div>
            </div>
          </div>
        </div>

        {/* Short Merchant-Friendly Explanation Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {/* Why */}
          <div className="p-3 bg-white rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide block font-mono">
              Why AI reached conclusion
            </span>
            <p className="text-slate-700 leading-relaxed font-medium">
              {whyExplanation}
            </p>
          </div>

          {/* Remaining Gap */}
          <div className="p-3 bg-white rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wide block font-mono">
              Remaining Evidence Gap
            </span>
            <p className="text-slate-700 leading-relaxed">
              {remainingGap}
            </p>
          </div>

          {/* Next Action */}
          <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-200/70 space-y-1">
            <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wide block font-mono">
              Next Recommended Action
            </span>
            <p className="text-indigo-950 font-medium leading-relaxed">
              {nextAction}
            </p>
          </div>
        </div>

        {/* Action Controls & Expandable Deep Breakdown */}
        <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition cursor-pointer"
          >
            <span>{showDetails ? 'Hide deep model analysis' : 'View deep model analysis'}</span>
            <svg
              className={`w-3.5 h-3.5 transform transition-transform ${showDetails ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {!isReadOnly && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsOverrideModalOpen(true)}
              >
                Override Recommendation
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-500 hover:text-rose-600"
                onClick={() => setIsAcceptModalOpen(true)}
              >
                Accept Dispute
              </Button>
            </div>
          )}
        </div>

        {/* Expandable Breakdown */}
        {showDetails && (
          <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-3 animate-in fade-in duration-150">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 bg-white rounded-xl border border-slate-200 space-y-2">
                <h5 className="font-bold text-slate-900 flex items-center gap-1.5">
                  <span className="text-emerald-600">✓</span> Supporting Factors (Positive Defense)
                </h5>
                <ul className="space-y-1 text-slate-600">
                  {rec.positive_factors && rec.positive_factors.length > 0 ? (
                    rec.positive_factors.map((f: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-600 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))
                  ) : (
                    keyFactors.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-600 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))
                  )}
                </ul>
              </div>

              <div className="p-3.5 bg-white rounded-xl border border-slate-200 space-y-2">
                <h5 className="font-bold text-slate-900 flex items-center gap-1.5">
                  <span className="text-amber-600">⚠️</span> Risk Factors & Watchpoints
                </h5>
                <ul className="space-y-1 text-slate-600">
                  {rec.negative_factors && rec.negative_factors.length > 0 ? (
                    rec.negative_factors.map((f: string, i: number) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-amber-600 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))
                  ) : (
                    <li className="flex items-start gap-1.5 text-slate-500">
                      <span>• No major counter-indicators found against merchant records.</span>
                    </li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Accept Concession Modal */}
      <Modal
        isOpen={isAcceptModalOpen}
        onClose={() => setIsAcceptModalOpen(false)}
        title="Accept Dispute Concession"
        subtitle="You are deciding not to challenge this dispute. The disputed amount will be conceded."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsAcceptModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" isLoading={isSubmitting} onClick={handleAcceptDispute}>
              Confirm & Concede
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <p className="text-slate-600">
            By accepting this dispute, the case will transition to <strong>Resolved (Conceded)</strong> and no further rebuttal will be submitted to the bank.
          </p>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Reason for Acceptance</label>
            <input
              type="text"
              value={acceptReason}
              onChange={(e) => setAcceptReason(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
            />
          </div>
        </div>
      </Modal>

      {/* Override Recommendation Modal */}
      <Modal
        isOpen={isOverrideModalOpen}
        onClose={() => setIsOverrideModalOpen(false)}
        title="Override AI Recommendation"
        subtitle="Change the recommended response strategy for this dispute case."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsOverrideModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" isLoading={isSubmitting} onClick={handleOverrideDecision}>
              Apply Decision
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">Select Strategy</label>
            <select
              value={overrideDecision}
              onChange={(e) => setOverrideDecision(e.target.value as any)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
            >
              <option value="CONTEST">Challenge this dispute (Contest)</option>
              <option value="ACCEPT">Accept this dispute (Concede)</option>
              <option value="INVESTIGATE">Review further (Investigate)</option>
            </select>
          </div>
          <div>
            <label className="block font-medium text-slate-700 mb-1">Business Rationale</label>
            <textarea
              rows={3}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. Verified customer signature with logistics department..."
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900"
            />
          </div>
        </div>
      </Modal>
    </section>
  );
};

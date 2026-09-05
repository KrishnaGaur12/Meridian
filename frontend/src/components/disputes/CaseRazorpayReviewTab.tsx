import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Dispute } from '../../types/dispute';
import { CaseAnalysis } from '../../types/commandCenter';
import { formatCurrency, formatDate } from '../../utils/formatters';
import { disputeService } from '../../services/disputeService';

interface CaseRazorpayReviewTabProps {
  dispute: Dispute;
  analysis: CaseAnalysis;
  onRefresh: () => void;
  onBackToSubmission: () => void;
  onViewOutcome: () => void;
  isResolved: boolean;
}

export const CaseRazorpayReviewTab: React.FC<CaseRazorpayReviewTabProps> = ({
  dispute,
  analysis,
  onRefresh,
  onBackToSubmission,
  onViewOutcome,
  isResolved,
}) => {
  const [isSimulatingOutcome, setIsSimulatingOutcome] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSimulateOutcome = async () => {
    try {
      setIsSimulatingOutcome(true);
      setErrorMsg(null);
      await disputeService.simulateOutcome(dispute.dispute_id);
      onRefresh();
      onViewOutcome();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not simulate outcome.');
    } finally {
      setIsSimulatingOutcome(false);
    }
  };


  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <Card className="p-6 bg-white border-blue-200 shadow-2xs space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-mono font-bold text-blue-700 uppercase tracking-wider">
              Step 6 · Gateway Review
            </span>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
              Awaiting Razorpay & Bank Review
            </h2>
          </div>
          <span className="px-2.5 py-0.5 text-xs font-bold rounded-md bg-blue-50 text-blue-700 border border-blue-200">
            UNDER REVIEW
          </span>
        </div>

        {/* Gateway Submission Details */}
        <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-200 text-xs space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <span className="text-[10px] font-mono text-slate-400 block">Gateway Reference ID:</span>
              <strong className="font-mono text-slate-900 text-sm">
                REF-{dispute.dispute_id.replace(/^DSP_/, '')}
              </strong>
            </div>
            <div>
              <span className="text-[10px] font-mono text-slate-400 block">Submission Timestamp:</span>
              <strong className="text-slate-900">{formatDate(dispute.ai_last_checked || dispute.created_at)}</strong>
            </div>
            <div>
              <span className="text-[10px] font-mono text-slate-400 block">Contested Amount:</span>
              <strong className="text-slate-900">{formatCurrency(dispute.amount || analysis.amount, dispute.currency || analysis.currency || 'INR')}</strong>
            </div>
          </div>

          <p className="text-slate-600 text-[11px] leading-relaxed pt-1 border-t border-blue-200/60">
            The merchant representation rebuttal statement and verified evidence bundle have been transmitted across the Razorpay Gateway API boundary and forwarded to the cardholder issuing bank.
          </p>
        </div>

        {/* Gateway Resolution Simulator Section */}
        {!isResolved && (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-bold text-slate-900">Simulate Bank & Network Outcome</h4>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  Advance the case to test deterministic gateway resolution (Simulated WON or LOST).
                </p>
              </div>
              <Button
                onClick={handleSimulateOutcome}
                variant="primary"
                size="sm"
                isLoading={isSimulatingOutcome}
                className="bg-indigo-600 hover:bg-indigo-700 font-bold shadow-xs shrink-0"
              >
                Trigger Simulated Outcome &rarr;
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between pt-2">
        <Button onClick={onBackToSubmission} variant="outline" size="md">
          &larr; View Submission Manifest
        </Button>

        {isResolved && (
          <Button onClick={onViewOutcome} variant="primary" size="md" className="font-bold shadow-xs">
            View Final Outcome &rarr;
          </Button>
        )}
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { Dispute } from '../../types/dispute';
import { CaseAnalysis, PackageInspection } from '../../types/commandCenter';
import { EvidenceItem } from '../../types/evidence';
import { formatCurrency, formatAIOutcome, formatAssessment } from '../../utils/formatters';
import { disputeService } from '../../services/disputeService';

interface CaseMerchantReviewTabProps {
  dispute: Dispute;
  analysis: CaseAnalysis;
  evidenceList: EvidenceItem[];
  packageInspection?: PackageInspection;
  onRefresh: () => void;
  onBack: () => void;
  onContinue: () => void;
  isReadOnly: boolean;
}

export const CaseMerchantReviewTab: React.FC<CaseMerchantReviewTabProps> = ({
  dispute,
  analysis,
  evidenceList,
  packageInspection: _packageInspection,
  onRefresh,
  onBack,
  onContinue,
  isReadOnly,
}) => {
  const [selectedDecision, setSelectedDecision] = useState<'CONTEST' | 'ACCEPT'>('CONTEST');
  const [isAcceptModalOpen, setIsAcceptModalOpen] = useState(false);
  const [acceptReason, setAcceptReason] = useState('Merchant accepted chargeback concession.');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const rec = analysis.recommendation || {};
  const outcome = formatAIOutcome(rec.action || 'CONTEST');

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

  const approvedEvidence = evidenceList.filter((item) => {
    const dataObj =
      typeof item.evidence_data === 'object'
        ? item.evidence_data
        : typeof (item as any).data === 'object'
        ? (item as any).data
        : {};

    return (
      item.verification_status === 'APPROVED' ||
      dataObj?.merchant_approval_status === 'APPROVED' ||
      dataObj?.merchant_approved === true
    );
  });

  const pendingEvidence = evidenceList.filter((item) => {
    const dataObj =
      typeof item.evidence_data === 'object'
        ? item.evidence_data
        : typeof (item as any).data === 'object'
        ? (item as any).data
        : {};

    const isApp =
      item.verification_status === 'APPROVED' ||
      dataObj?.merchant_approval_status === 'APPROVED' ||
      dataObj?.merchant_approved === true;

    return !isApp;
  });

  const handleConfirmAccept = async () => {
    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await disputeService.acceptDispute(dispute.dispute_id, acceptReason);
      setIsAcceptModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not accept dispute.');
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* Merchant Decision Card */}
      <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
              Step 4 · Final Merchant Position
            </span>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
              Merchant Position & Strategy Review
            </h2>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-mono text-slate-400 block">AI Recommended Strategy</span>
            <span className="text-xs font-bold text-indigo-700">{outcome.label}</span>
          </div>
        </div>

        {/* Executive Summary Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">ML Risk Evaluation</span>
            <div className="text-sm font-bold text-slate-900">
              {winProb !== null ? `${winProb}% Win Probability` : 'Assessment In Progress'}
            </div>
            <div className="text-[11px] text-slate-500">Confidence: {confidence}</div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Evidence Approval Status</span>
            <div className="text-sm font-bold text-emerald-700">
              {approvedEvidence.length} / {evidenceList.length} Approved
            </div>
            <div className="text-[11px] text-slate-500">
              {pendingEvidence.length > 0 ? `${pendingEvidence.length} item(s) pending review` : 'All items approved'}
            </div>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Contested Value</span>
            <div className="text-sm font-bold text-slate-900">
              {formatCurrency(dispute.amount || analysis.amount, dispute.currency || analysis.currency || 'INR')}
            </div>
            <div className="text-[11px] text-slate-500">Subject to representation</div>
          </div>
        </div>

        {/* AI Guidance Summary */}
        <div className="p-3.5 bg-indigo-50/50 rounded-xl border border-indigo-200/70 text-xs space-y-1">
          <span className="text-[10px] font-mono font-bold text-indigo-900 uppercase tracking-wider block">
            DeepSeek Strategic Reasoning
          </span>
          <p className="text-slate-700 leading-relaxed font-medium">
            {analysis.attention_reason || rec.reason || 'Verified fulfillment records strongly support contesting this chargeback.'}
          </p>
        </div>

        {/* Decision Selector */}
        {!isReadOnly && (
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <label className="block text-xs font-bold text-slate-900">
              Confirm Merchant Defense Decision *
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                onClick={() => setSelectedDecision('CONTEST')}
                className={`p-3.5 rounded-xl border cursor-pointer transition select-none flex items-start gap-3 ${
                  selectedDecision === 'CONTEST'
                    ? 'border-indigo-600 bg-indigo-50/60 ring-1 ring-indigo-500/20'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name="merchant_decision"
                  checked={selectedDecision === 'CONTEST'}
                  onChange={() => setSelectedDecision('CONTEST')}
                  className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <strong className="text-xs font-bold text-slate-900 block">
                    Contest Dispute (Challenge Claim)
                  </strong>
                  <span className="text-[11px] text-slate-500 block mt-0.5">
                    Submit approved evidence and rebuttal package to bank to recover contested funds.
                  </span>
                </div>
              </label>

              <label
                onClick={() => setSelectedDecision('ACCEPT')}
                className={`p-3.5 rounded-xl border cursor-pointer transition select-none flex items-start gap-3 ${
                  selectedDecision === 'ACCEPT'
                    ? 'border-rose-600 bg-rose-50/60 ring-1 ring-rose-500/20'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name="merchant_decision"
                  checked={selectedDecision === 'ACCEPT'}
                  onChange={() => setSelectedDecision('ACCEPT')}
                  className="mt-0.5 text-rose-600 focus:ring-rose-500"
                />
                <div>
                  <strong className="text-xs font-bold text-slate-900 block">
                    Accept Dispute (Concede Claim)
                  </strong>
                  <span className="text-[11px] text-slate-500 block mt-0.5">
                    Concede the disputed amount. Case will close without submission.
                  </span>
                </div>
              </label>
            </div>
          </div>
        )}
      </Card>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between pt-2">
        <Button onClick={onBack} variant="outline" size="md">
          &larr; Back to Evidence Workspace
        </Button>

        {selectedDecision === 'ACCEPT' && !isReadOnly ? (
          <Button
            onClick={() => setIsAcceptModalOpen(true)}
            variant="danger"
            size="md"
            className="font-bold shadow-xs"
          >
            Confirm & Concede Dispute &rarr;
          </Button>
        ) : (
          <Button onClick={onContinue} variant="primary" size="md" className="font-semibold shadow-xs">
            Continue to Final Submission &rarr;
          </Button>
        )}
      </div>

      {/* Concede Modal */}
      <Modal
        isOpen={isAcceptModalOpen}
        onClose={() => setIsAcceptModalOpen(false)}
        title="Confirm Dispute Acceptance"
        subtitle="You are deciding to concede this dispute."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsAcceptModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" isLoading={isSubmitting} onClick={handleConfirmAccept}>
              Confirm Acceptance
            </Button>
          </>
        }
      >
        <div className="space-y-3 text-xs text-slate-600">
          <p>
            The case will be marked as <strong>Resolved (Conceded)</strong> and no submission will be made to Razorpay.
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
    </div>
  );
};

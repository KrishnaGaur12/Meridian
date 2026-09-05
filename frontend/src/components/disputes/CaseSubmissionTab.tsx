import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { Dispute, DisputeCaseReadiness } from '../../types/dispute';
import { CaseAnalysis, PackageInspection } from '../../types/commandCenter';
import { EvidenceItem } from '../../types/evidence';
import { formatCurrency, formatAIOutcome, formatDate } from '../../utils/formatters';
import { disputeService } from '../../services/disputeService';

interface CaseSubmissionTabProps {
  dispute: Dispute;
  analysis: CaseAnalysis;
  evidenceList: EvidenceItem[];
  readiness?: DisputeCaseReadiness;
  packageInspection?: PackageInspection;
  onRefresh: () => void;
  onBack: () => void;
  onGoToEvidence: () => void;
  onSubmittedSuccess: () => void;
  isReadOnly: boolean;
}

export const CaseSubmissionTab: React.FC<CaseSubmissionTabProps> = ({
  dispute,
  analysis,
  evidenceList,
  readiness,
  packageInspection,
  onRefresh: _onRefresh,
  onBack,
  onGoToEvidence,
  onSubmittedSuccess,
  isReadOnly,
}) => {
  const [isEditingResponse, setIsEditingResponse] = useState(false);
  const [customResponse, setCustomResponse] = useState('');
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const defaultRebuttal =
    packageInspection?.rebuttal?.rebuttal_text ||
    packageInspection?.rebuttal?.rebuttal_letter ||
    `We hereby contest the chargeback for transaction ${dispute.transaction_id}. All goods/services were fulfilled in strict compliance with agreed terms, and delivery confirmation was verified. Supporting records are attached herewith.`;

  const activeRebuttal = customResponse || defaultRebuttal;

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

  const hasUnapprovedEvidence = pendingEvidence.length > 0;
  const hasNoEvidence = evidenceList.length === 0;

  const canSubmit =
    !hasNoEvidence &&
    !hasUnapprovedEvidence &&
    (readiness?.can_submit ?? true) &&
    !isReadOnly;

  const handleFinalSubmit = async () => {
    try {
      setIsSubmitting(true);
      setErrorMsg(null);
      await disputeService.submitDispute(dispute.dispute_id);
      setIsReviewModalOpen(false);
      onSubmittedSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not submit dispute package.');
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-4">
        {/* Step Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
              Step 5 · Submission Package & Readiness Gate
            </span>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
              Representation Package Manifest
            </h2>
          </div>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-md border font-semibold ${
              canSubmit
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : 'bg-amber-50 text-amber-800 border-amber-300'
            }`}
          >
            {canSubmit ? '✓ Ready for Gateway Submission' : 'Evidence Review Required'}
          </span>
        </div>

        {/* Readiness Status Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs">
          <div>
            <span className="text-[10px] font-mono text-slate-400 uppercase">Package Readiness</span>
            <div className="text-sm font-bold text-slate-900 mt-0.5">
              {approvedEvidence.length} of {evidenceList.length} Evidence Records Approved
            </div>
          </div>
          <div className="flex items-center gap-5">
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Disputed Value</span>
              <strong className="text-slate-900 text-sm">
                {formatCurrency(dispute.amount || analysis.amount, dispute.currency || analysis.currency || 'INR')}
              </strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Gateway Boundary</span>
              <strong className="text-indigo-700 text-xs font-mono">Razorpay Gateway API</strong>
            </div>
          </div>
        </div>

        {/* Blocking Warning if Unapproved Evidence Exists */}
        {hasUnapprovedEvidence && (
          <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 space-y-2">
            <div className="font-bold flex items-center gap-1.5 text-amber-950">
              <span>⚠️ Evidence Review Required Before Submission</span>
            </div>
            <p className="text-amber-800 leading-relaxed text-[11px]">
              Only explicitly approved evidence may be included in the representation package. The following items require merchant approval:
            </p>
            <ul className="list-disc list-inside space-y-1 text-amber-950 font-medium pl-1">
              {pendingEvidence.map((p, idx) => (
                <li key={idx} className="flex items-center justify-between">
                  <span>
                    <strong>{p.title || p.evidence_type}</strong> ({p.evidence_type?.replace(/_/g, ' ')})
                  </span>
                  <button
                    type="button"
                    onClick={onGoToEvidence}
                    className="text-indigo-700 hover:text-indigo-900 font-bold underline cursor-pointer ml-3"
                  >
                    Approve in Evidence Tab &rarr;
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Approved Evidence Manifest */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
            Approved Evidence Manifest (Included in Package)
          </h3>

          {approvedEvidence.length === 0 ? (
            <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-500 border border-slate-200">
              No approved evidence items attached. Please return to the Evidence tab to approve items.
            </div>
          ) : (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 text-xs text-slate-700">
              {approvedEvidence.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between py-1 border-b border-slate-200/60 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="text-emerald-600 font-bold">✓</span>
                    <span className="font-semibold text-slate-900">{item.title}</span>
                    <span className="text-slate-400 font-mono text-[10px]">({item.evidence_type?.replace(/_/g, ' ')})</span>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    APPROVED FOR SUBMISSION
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Rebuttal Statement Preview */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
              Merchant Representation Defense Letter
            </h3>
            {!isReadOnly && (
              <button
                type="button"
                onClick={() => setIsEditingResponse(!isEditingResponse)}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 cursor-pointer"
              >
                {isEditingResponse ? 'Done Editing' : 'Edit Letter'}
              </button>
            )}
          </div>

          {isEditingResponse ? (
            <textarea
              rows={4}
              value={activeRebuttal}
              onChange={(e) => setCustomResponse(e.target.value)}
              className="w-full text-xs font-mono bg-white border border-indigo-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 text-slate-800 leading-relaxed"
            />
          ) : (
            <div className="p-3.5 bg-slate-50/70 border border-slate-200/80 rounded-xl text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">
              {activeRebuttal}
            </div>
          )}
        </div>
      </Card>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2">
        <Button onClick={onBack} variant="outline" size="md">
          &larr; Back to Merchant Review
        </Button>

        <Button
          onClick={() => setIsReviewModalOpen(true)}
          disabled={!canSubmit}
          variant="primary"
          size="md"
          className="font-bold shadow-xs"
        >
          Review & Submit Representation &rarr;
        </Button>
      </div>

      {/* FINAL CONFIRMATION MODAL */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        title="Confirm Dispute Representation Submission"
        subtitle="Review the final representation package before dispatching to Razorpay."
        footer={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsReviewModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleFinalSubmit}
              className="bg-indigo-600 hover:bg-indigo-700 font-bold shadow-xs"
            >
              Confirm & Submit to Razorpay
            </Button>
          </>
        }
      >
        <div className="space-y-3.5 text-xs">
          {/* Summary */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 grid grid-cols-2 gap-2.5 text-slate-700">
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Dispute ID:</span>
              <strong className="font-mono text-slate-900">{dispute.dispute_id}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Transaction ID:</span>
              <strong className="font-mono text-slate-900">{dispute.transaction_id}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Contested Value:</span>
              <strong className="text-slate-900">
                {formatCurrency(dispute.amount || analysis.amount, dispute.currency || analysis.currency || 'INR')}
              </strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Approved Evidence:</span>
              <strong className="text-emerald-700">{approvedEvidence.length} Verified Records</strong>
            </div>
          </div>

          {/* Defense Statement Preview */}
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-slate-500 uppercase">
              Representation Defense Letter
            </span>
            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-slate-700 text-[11px] leading-relaxed max-h-32 overflow-y-auto">
              {activeRebuttal}
            </div>
          </div>

          <p className="text-slate-500 text-[11px] leading-relaxed">
            By submitting, this representation package will be transmitted to Razorpay and forwarded to the issuing bank for formal arbitration.
          </p>
        </div>
      </Modal>
    </div>
  );
};

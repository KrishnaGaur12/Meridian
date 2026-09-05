import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { PackageInspection } from '../../types/commandCenter';
import { DisputeCaseReadiness } from '../../types/dispute';
import { EvidenceItem } from '../../types/evidence';
import { formatCurrency, formatAIOutcome } from '../../utils/formatters';

interface FinalReviewSectionProps {
  packageInspection?: PackageInspection;
  readiness?: DisputeCaseReadiness;
  evidenceList: EvidenceItem[];
  disputeId: string;
  amount: number;
  currency: string;
  recommendationAction?: string;
  isReadOnly: boolean;
  onOpenSubmitModal: () => void;
  onScrollToEvidence: () => void;
}

export const FinalReviewSection: React.FC<FinalReviewSectionProps> = ({
  packageInspection,
  readiness,
  evidenceList,
  amount,
  currency,
  recommendationAction = 'CONTEST',
  isReadOnly,
  onOpenSubmitModal,
  onScrollToEvidence,
}) => {
  const [isEditingResponse, setIsEditingResponse] = useState(false);
  const [customResponse, setCustomResponse] = useState<string>('');

  const defaultRebuttal =
    packageInspection?.rebuttal?.rebuttal_text ||
    packageInspection?.rebuttal?.rebuttal_letter ||
    `We hereby contest the chargeback for transaction. All goods/services were fulfilled in strict compliance with agreed terms, and delivery confirmation was verified. Supporting records are attached herewith.`;

  const activeRebuttal = customResponse || defaultRebuttal;

  // Filter approved items
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

  // Can submit only if: readiness gate passes AND there is at least one approved item AND no pending items block review
  const canSubmit =
    !hasNoEvidence &&
    !hasUnapprovedEvidence &&
    (readiness?.can_submit ?? true);

  const completeness = readiness?.readiness_percentage ?? (hasUnapprovedEvidence ? 60 : 100);
  const outcome = formatAIOutcome(recommendationAction);

  return (
    <section id="case-final-review" className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
          Final Review & Submission Gate
        </h2>
        <span className="text-xs text-slate-500 font-mono">Strict Merchant Approval Gate</span>
      </div>

      <Card className="p-5 space-y-4 border-slate-200 bg-white shadow-2xs">
        {/* Top Summary Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200/80">
          <div>
            <div className="text-[11px] font-bold text-indigo-700 uppercase tracking-wide font-mono">
              Representation Package Status
            </div>
            <div className="text-sm sm:text-base font-bold text-slate-900 mt-0.5 flex items-center gap-2">
              <span>{canSubmit ? 'Ready for Gateway Dispatch' : 'Evidence Review Required'}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded border font-semibold ${
                  canSubmit
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                    : 'bg-amber-50 text-amber-800 border-amber-300'
                }`}
              >
                {canSubmit ? '✓ All Approved' : 'Action Required'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs">
            <div>
              <span className="text-slate-500 text-[11px]">Contested Value</span>
              <div className="text-sm font-bold text-slate-900">{formatCurrency(amount, currency)}</div>
            </div>
            <div>
              <span className="text-slate-500 text-[11px]">Approved Evidence</span>
              <div className="text-sm font-bold text-emerald-700">
                {approvedEvidence.length} / {evidenceList.length} Items
              </div>
            </div>
          </div>
        </div>

        {/* Blocking Warning if Evidence is Pending Approval */}
        {hasUnapprovedEvidence && (
          <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 space-y-2">
            <div className="font-bold flex items-center gap-1.5 text-amber-900">
              <span>⚠️ Evidence Review Required Before Submission</span>
            </div>
            <p className="text-amber-800 text-[11px] leading-relaxed">
              Under chargeback rules, AI validation is not a substitute for merchant authorization. The following evidence items must be explicitly reviewed and approved before submission:
            </p>
            <ul className="list-disc list-inside space-y-1 text-amber-900 text-xs font-medium pl-1">
              {pendingEvidence.map((p, idx) => (
                <li key={idx} className="flex items-center justify-between">
                  <span>
                    <strong>{p.title || p.evidence_type}</strong> ({p.evidence_type?.replace(/_/g, ' ')}) — <span className="font-mono text-[10px] text-amber-700">Pending Approval</span>
                  </span>
                  <button
                    type="button"
                    onClick={onScrollToEvidence}
                    className="text-indigo-700 hover:text-indigo-900 font-bold underline text-xs cursor-pointer ml-3"
                  >
                    Review in Workspace &rarr;
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Blocking Issues from Backend Readiness Gate */}
        {readiness && readiness.blocking_issues && readiness.blocking_issues.length > 0 && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 space-y-1.5">
            <div className="font-bold flex items-center gap-1 text-rose-700">
              <span>⚠️ Gateway Compliance Issues:</span>
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-rose-800 text-[11px]">
              {readiness.blocking_issues.map((issue, idx) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Approved Evidence Manifest */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
            Approved Evidence Manifest (Included in Submission)
          </h3>

          {approvedEvidence.length === 0 ? (
            <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-500 border border-slate-200">
              No approved evidence items attached. Please approve items in the Evidence Workspace above.
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
                    APPROVED FOR TRANSMISSION
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI-Generated Rebuttal Statement */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
              Merchant Representation Defense Letter
            </h3>
            {!isReadOnly && (
              <button
                onClick={() => setIsEditingResponse(!isEditingResponse)}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 cursor-pointer"
              >
                {isEditingResponse ? 'Done Editing' : 'Edit Statement'}
              </button>
            )}
          </div>

          {isEditingResponse ? (
            <textarea
              rows={5}
              value={activeRebuttal}
              onChange={(e) => setCustomResponse(e.target.value)}
              className="w-full text-xs font-mono bg-white border border-indigo-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 text-slate-800 leading-relaxed"
            />
          ) : (
            <div className="p-3.5 bg-slate-50/70 border border-slate-200/80 rounded-xl text-xs text-slate-700 leading-relaxed font-sans whitespace-pre-wrap">
              {activeRebuttal}
            </div>
          )}
        </div>

        {/* Action Controls */}
        {!isReadOnly && (
          <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs text-slate-500">
              Only explicitly approved evidence will be packaged and transmitted to Razorpay.
            </div>

            <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
              <Button onClick={onScrollToEvidence} variant="outline" size="sm">
                + Add / Review Evidence
              </Button>
              <Button
                onClick={onOpenSubmitModal}
                disabled={!canSubmit}
                variant="primary"
                size="md"
                className="font-semibold shadow-xs"
              >
                Approve & Submit Representation &rarr;
              </Button>
            </div>
          </div>
        )}
      </Card>
    </section>
  );
};

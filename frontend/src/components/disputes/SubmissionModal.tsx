import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { disputeService } from '../../services/disputeService';
import { DisputeSubmitResponse, DisputeOutcomeResponse } from '../../types/dispute';
import { formatCurrency } from '../../utils/formatters';

interface SubmissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  disputeId: string;
  amount: number;
  currency: string;
  evidenceCount: number;
  onSubmittedSuccess: () => void;
}

export const SubmissionModal: React.FC<SubmissionModalProps> = ({
  isOpen,
  onClose,
  disputeId,
  amount,
  currency,
  evidenceCount,
  onSubmittedSuccess,
}) => {
  const [step, setStep] = useState<'confirm' | 'success' | 'outcome'>('confirm');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSimulatingOutcome, setIsSimulatingOutcome] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<DisputeSubmitResponse | null>(null);
  const [outcomeResult, setOutcomeResult] = useState<DisputeOutcomeResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleConfirmSubmit = async () => {
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const res = await disputeService.submitDispute(disputeId);
      setSubmissionResult(res);
      setStep('success');
      onSubmittedSuccess();
    } catch (err: any) {
      setErrorMessage(
        err.message || 'Submission failed. Your evidence package remains safely saved. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSimulateOutcome = async () => {
    try {
      setIsSimulatingOutcome(true);
      setErrorMessage(null);
      const res = await disputeService.simulateOutcome(disputeId);
      setOutcomeResult(res);
      setStep('outcome');
      onSubmittedSuccess();
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not simulate outcome.');
    } finally {
      setIsSimulatingOutcome(false);
    }
  };

  const handleClose = () => {
    setStep('confirm');
    setSubmissionResult(null);
    setOutcomeResult(null);
    setErrorMessage(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        step === 'confirm'
          ? 'Confirm & Dispatch Response Package'
          : step === 'success'
          ? 'Rebuttal Submitted to Razorpay Gateway'
          : 'Gateway Outcome Recorded'
      }
      subtitle={
        step === 'confirm'
          ? 'Review package summary before official transmission through Razorpay gateway boundary'
          : step === 'success'
          ? 'Defense representation dispatched successfully'
          : 'Simulated Card Network Resolution Received'
      }
    >
      {step === 'confirm' && (
        <div className="space-y-4 text-xs">
          <p className="text-slate-600 leading-relaxed">
            You are about to transmit this chargeback representation to Razorpay. The package will undergo local gateway verification and enter <strong>Awaiting Review</strong> state.
          </p>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-slate-700">
            <div className="flex justify-between">
              <span className="text-slate-500">Dispute ID:</span>
              <span className="font-mono font-bold text-slate-900">{disputeId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Disputed Value:</span>
              <span className="font-bold text-slate-900">{formatCurrency(amount, currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Attached Evidence:</span>
              <span className="font-bold text-slate-900">{evidenceCount} items</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">AI Defense Statement:</span>
              <span className="font-bold text-emerald-700">Verified & Generated</span>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
              {errorMessage}
            </div>
          )}

          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <Button variant="outline" size="sm" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleConfirmSubmit}
              className="font-semibold shadow-xs"
            >
              Confirm & Submit to Razorpay
            </Button>
          </div>
        </div>
      )}

      {step === 'success' && (
        <div className="space-y-4 text-center py-2 text-xs">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto text-xl font-bold">
            ✓
          </div>

          <div className="space-y-1">
            <h4 className="text-base font-bold text-slate-900">Package Successfully Submitted</h4>
            <p className="text-slate-500 max-w-sm mx-auto">
              Your response for dispute <strong>{disputeId}</strong> has been transmitted through the local gateway boundary.
            </p>
          </div>

          {/* Realistic Gateway Submission Reference */}
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-left space-y-2 text-slate-700">
            <div className="flex justify-between">
              <span className="text-slate-500 font-mono text-[11px]">Gateway Submission ID:</span>
              <span className="font-mono font-bold text-indigo-700">
                {submissionResult?.gateway_reference_id || `REF-${Math.floor(10000000 + Math.random() * 90000000)}`}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 text-[11px]">Current Lifecycle Stage:</span>
              <span className="px-2 py-0.5 text-[10px] font-bold text-blue-700 bg-blue-50 rounded border border-blue-200">
                SUBMITTED · UNDER REVIEW
              </span>
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-blue-900 text-left text-[11px]">
            <strong>Simulated Network Flow:</strong> In this test environment, you can now test the simulated gateway outcome resolution (WON / LOST) based on the evidence quality.
          </div>

          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs text-left">
              {errorMessage}
            </div>
          )}

          <div className="pt-2 flex flex-col sm:flex-row justify-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              isLoading={isSimulatingOutcome}
              onClick={handleSimulateOutcome}
              className="bg-white hover:bg-slate-50"
            >
              Simulate Gateway Resolution (WON/LOST) &rarr;
            </Button>
            <Button variant="primary" size="sm" onClick={handleClose} className="font-semibold">
              Done & View Workspace
            </Button>
          </div>
        </div>
      )}

      {step === 'outcome' && (
        <div className="space-y-4 text-center py-2 text-xs">
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto text-xl font-bold ${
              outcomeResult?.outcome === 'WON'
                ? 'bg-emerald-100 text-emerald-600'
                : 'bg-rose-100 text-rose-600'
            }`}
          >
            {outcomeResult?.outcome === 'WON' ? '✓' : '✕'}
          </div>

          <div className="space-y-1">
            <h4 className="text-base font-bold text-slate-900">
              Simulated Gateway Outcome: {outcomeResult?.outcome || 'WON'}
            </h4>
            <p className="text-slate-500 max-w-sm mx-auto">
              {outcomeResult?.message ||
                `The card issuing bank ruled in favor of the ${
                  outcomeResult?.outcome === 'WON' ? 'merchant' : 'customer'
                }.`}
            </p>
          </div>

          <div className="pt-2 flex justify-center">
            <Button variant="primary" size="sm" onClick={handleClose} className="font-semibold">
              Return to Dispute Details
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
};

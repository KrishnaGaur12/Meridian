import React from 'react';
import { WorkflowStage, DisputeStatus } from '../../types/dispute';

interface ProgressStepperProps {
  stage: WorkflowStage;
  status: DisputeStatus;
  attentionState?: string;
}

export const ProgressStepper: React.FC<ProgressStepperProps> = ({ stage, status, attentionState }) => {
  const normalizedStatus = (status || '').toUpperCase();
  const normalizedStage = (stage || '').toUpperCase();

  const steps = [
    { id: 'DISPUTE_RAISED', label: 'Dispute Received' },
    { id: 'AI_ANALYSIS', label: 'AI Analysis' },
    { id: 'EVIDENCE', label: 'Evidence' },
    { id: 'MERCHANT_REVIEW', label: 'Merchant Review' },
    { id: 'SUBMISSION', label: 'Submission' },
    { id: 'RAZORPAY_REVIEW', label: 'Razorpay Review' },
    { id: 'OUTCOME', label: 'Outcome' },
  ];

  let currentIndex = 0;

  if (normalizedStatus === 'WON' || normalizedStatus === 'LOST' || normalizedStatus === 'CLOSED' || normalizedStage === 'RESOLVED') {
    currentIndex = 6;
  } else if (normalizedStage === 'SUBMITTED' || normalizedStatus === 'UNDER_REVIEW' || attentionState === 'WAITING') {
    currentIndex = 5;
  } else if (normalizedStage === 'READY_FOR_SUBMISSION') {
    currentIndex = 4;
  } else if (normalizedStage === 'MERCHANT_REVIEW' || attentionState === 'REVIEW_RECOMMENDED') {
    currentIndex = 3;
  } else if (normalizedStage === 'EVIDENCE_COLLECTION' || normalizedStage === 'EVIDENCE_BUNDLE_CREATED') {
    currentIndex = 2;
  } else {
    currentIndex = 1;
  }

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200/90 py-3 px-4 shadow-2xs">
      <div className="relative flex items-center justify-between">
        {/* Connecting Line */}
        <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-0.5 bg-slate-200 -z-0" />

        {steps.map((step, idx) => {
          const isCompleted = idx < currentIndex;
          const isCurrent = idx === currentIndex;

          return (
            <div key={step.id} className="relative z-10 flex flex-col items-center group">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-150 ${
                  isCompleted
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : isCurrent
                    ? 'bg-indigo-600 text-white ring-3 ring-indigo-100 checkpoint-current'
                    : 'bg-slate-200 text-slate-500 border border-white'
                }`}
              >
                {isCompleted ? '✓' : idx + 1}
              </div>
              <span
                className={`text-[10px] sm:text-[11px] font-medium mt-1 whitespace-nowrap hidden sm:block ${
                  isCurrent
                    ? 'text-indigo-600 font-bold'
                    : isCompleted
                    ? 'text-slate-700'
                    : 'text-slate-400'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

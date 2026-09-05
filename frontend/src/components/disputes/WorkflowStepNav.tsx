import React from 'react';

export type WorkflowStepId =
  | 'overview'
  | 'review'
  | 'razorpay_review'
  | 'outcome'
  // Technical backwards-compatibility aliases (map to review)
  | 'ai_analysis'
  | 'evidence'
  | 'merchant_review'
  | 'submission';

interface StepDefinition {
  id: WorkflowStepId;
  label: string;
  shortLabel: string;
  stepNumber: number;
}

const PRIMARY_STEPS: StepDefinition[] = [
  { id: 'overview', label: '1. Overview', shortLabel: 'Overview', stepNumber: 1 },
  { id: 'review', label: '2. Review & Control Center', shortLabel: 'Review', stepNumber: 2 },
  { id: 'razorpay_review', label: '3. Gateway Review', shortLabel: 'Gateway', stepNumber: 3 },
  { id: 'outcome', label: '4. Final Outcome', shortLabel: 'Outcome', stepNumber: 4 },
];

interface WorkflowStepNavProps {
  activeStep: WorkflowStepId;
  onSelectStep: (step: WorkflowStepId) => void;
  status?: string;
  workflowStage?: string;
}

export const WorkflowStepNav: React.FC<WorkflowStepNavProps> = ({
  activeStep,
  onSelectStep,
  status = '',
  workflowStage = '',
}) => {
  const normStatus = status.toUpperCase();
  const normStage = workflowStage.toUpperCase();

  const isSubmittedOrResolved =
    normStatus === 'WON' ||
    normStatus === 'LOST' ||
    normStatus === 'CLOSED' ||
    normStage === 'SUBMITTED' ||
    normStage === 'RESOLVED' ||
    normStatus === 'UNDER_REVIEW';

  const isResolved =
    normStatus === 'WON' || normStatus === 'LOST' || normStatus === 'CLOSED' || normStage === 'RESOLVED';

  // Normalize technical step aliases to primary merchant steps
  const normalizedActive =
    activeStep === 'ai_analysis' || activeStep === 'evidence' || activeStep === 'merchant_review' || activeStep === 'submission'
      ? 'review'
      : activeStep;

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200 p-2 shadow-2xs">
      <div className="flex items-center justify-between gap-1 overflow-x-auto no-scrollbar">
        {PRIMARY_STEPS.map((s, idx) => {
          const isActive = normalizedActive === s.id;
          let isComplete = false;

          if (s.id === 'overview' && normalizedActive !== 'overview') isComplete = true;
          if (s.id === 'review' && isSubmittedOrResolved) isComplete = true;
          if (s.id === 'razorpay_review' && isResolved) isComplete = true;

          const isClickable =
            s.id === 'overview' ||
            s.id === 'review' ||
            (s.id === 'razorpay_review' && isSubmittedOrResolved) ||
            (s.id === 'outcome' && isResolved);

          return (
            <React.Fragment key={s.id}>
              <button
                type="button"
                onClick={() => onSelectStep(s.id)}
                disabled={!isClickable}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap select-none ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-2xs font-bold'
                    : isComplete
                    ? 'text-slate-700 hover:bg-slate-100 cursor-pointer'
                    : isClickable
                    ? 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 cursor-pointer'
                    : 'text-slate-400 opacity-60 cursor-not-allowed'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-mono font-bold shrink-0 ${
                    isActive
                      ? 'bg-white text-indigo-700'
                      : isComplete
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {isComplete && !isActive ? '✓' : s.stepNumber}
                </div>
                <span>{s.label}</span>
              </button>

              {idx < PRIMARY_STEPS.length - 1 && (
                <div className="w-4 h-0.5 bg-slate-200 shrink-0 hidden sm:block" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { disputeService } from '../services/disputeService';
import { evidenceService } from '../services/evidenceService';
import { CommandCenterSnapshot } from '../types/commandCenter';
import { DisputeCaseReadiness } from '../types/dispute';
import { EvidenceItem } from '../types/evidence';
import { CaseHeader } from '../components/disputes/CaseHeader';
import { WorkflowStepNav, WorkflowStepId } from '../components/disputes/WorkflowStepNav';
import { CaseOverviewTab } from '../components/disputes/CaseOverviewTab';
import { CaseMerchantControlCenter } from '../components/disputes/CaseMerchantControlCenter';
import { CaseRazorpayReviewTab } from '../components/disputes/CaseRazorpayReviewTab';
import { CaseOutcomeTab } from '../components/disputes/CaseOutcomeTab';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Skeleton } from '../components/common/Skeleton';
import { useDatabaseMode } from '../context/DatabaseModeContext';
import { useRealtimeEvents } from '../hooks/useRealtimeEvents';

export const DisputeDetailPage: React.FC = () => {
  const { disputeId } = useParams<{ disputeId: string }>();
  const navigate = useNavigate();
  const { modeVersion } = useDatabaseMode();

  const [snapshot, setSnapshot] = useState<CommandCenterSnapshot | null>(null);
  const [readiness, setReadiness] = useState<DisputeCaseReadiness | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [activeStep, setActiveStep] = useState<WorkflowStepId>('review');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCaseData = useCallback(async (isSilent = false, signal?: AbortSignal) => {
    if (!disputeId) return;
    try {
      if (!isSilent) setIsLoading(true);
      setError(null);

      // 1. Fetch Command Center snapshot (Authoritative source of truth, cached & deduplicated)
      const centerData = await disputeService.getCommandCenter(disputeId, signal);
      setSnapshot(centerData);

      // 2. Fetch Readiness Gate in parallel or fallback
      try {
        const readinessData = await disputeService.getReadiness(disputeId, signal);
        setReadiness(readinessData);
      } catch {
        // Fallback readiness
      }

      // 3. Extract evidence records directly from authoritative backend response
      let rawEvidence: EvidenceItem[] = [];
      if (Array.isArray(centerData.evidence) && centerData.evidence.length > 0) {
        rawEvidence = centerData.evidence;
      } else if (Array.isArray(centerData.package_inspection?.evidence_package?.evidence)) {
        rawEvidence = centerData.package_inspection.evidence_package.evidence;
      } else if (Array.isArray(centerData.case_analysis?.evidence_intelligence?.evidence)) {
        rawEvidence = centerData.case_analysis.evidence_intelligence.evidence;
      } else {
        try {
          const evPkg = await evidenceService.generateEvidencePackage(disputeId);
          if (Array.isArray(evPkg?.evidence)) {
            rawEvidence = evPkg.evidence;
          }
        } catch {
          rawEvidence = [];
        }
      }

      setEvidenceList(rawEvidence);

      // Default tab routing based on backend status
      if (!isSilent) {
        const status = (centerData.dispute.status || '').toUpperCase();
        const stage = (centerData.dispute.workflow_stage || '').toUpperCase();

        if (status === 'WON' || status === 'LOST' || status === 'CLOSED' || stage === 'RESOLVED') {
          setActiveStep('outcome');
        } else if (stage === 'SUBMITTED' || status === 'UNDER_REVIEW') {
          setActiveStep('razorpay_review');
        } else {
          setActiveStep('review');
        }
      }
    } catch (err: any) {
      if (err.name === 'CanceledError' || err.name === 'AbortError' || err.code === 'ERR_CANCELED') {
        return;
      }
      setError(err.message || `Could not load dispute case ${disputeId}`);
    } finally {
      if (!isSilent) setIsLoading(false);
    }
  }, [disputeId]);

  useEffect(() => {
    const controller = new AbortController();
    loadCaseData(false, controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadCaseData, modeVersion]);


  // Real-time backend event listener for automatic updates
  useRealtimeEvents({
    disputeId,
    enabled: true,
    onEvent: (type, data) => {
      if (data.dispute_id && data.dispute_id !== disputeId) return;

      if (
        type === 'ML_ANALYSIS_COMPLETED' ||
        type === 'DEEPSEEK_ANALYSIS_COMPLETED' ||
        type === 'DISPUTE_ANALYSIS_COMPLETED' ||
        type === 'EVIDENCE_APPROVED' ||
        type === 'DISPUTE_STAGE_CHANGED' ||
        type === 'EVIDENCE_UPLOADED' ||
        type === 'EVIDENCE_UPDATED' ||
        type === 'EVIDENCE_DELETED'
      ) {
        loadCaseData(true);
      }
    },
    onRefresh: () => {
      loadCaseData(true);
    },
  });

  if (isLoading && !snapshot) {
    return (
      <div className="space-y-4 animate-in fade-in duration-150 flex-1">
        <Skeleton className="h-24" />
        <Skeleton className="h-12" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error || !snapshot) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Card className="text-center py-10 px-8 max-w-md w-full border-slate-200">
          <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-3 font-bold">
            !
          </div>
          <h3 className="text-sm font-semibold text-slate-900">Couldn't load dispute case</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {error || `Case ${disputeId} could not be located.`}
          </p>
          <div className="mt-5 flex justify-center gap-3">
            <Button onClick={() => navigate('/disputes')} variant="outline" size="sm">
              &larr; Back to Disputes
            </Button>
            <Button onClick={() => loadCaseData()} variant="primary" size="sm">
              Try again
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const { dispute, case_analysis, package_inspection, audit_trail } = snapshot;

  const isSubmittedOrResolved =
    (dispute.status || '').toUpperCase() === 'WON' ||
    (dispute.status || '').toUpperCase() === 'LOST' ||
    (dispute.status || '').toUpperCase() === 'CLOSED' ||
    (dispute.workflow_stage || '').toUpperCase() === 'SUBMITTED' ||
    (dispute.workflow_stage || '').toUpperCase() === 'RESOLVED' ||
    dispute.merchant_attention_state === 'WAITING';

  const isResolved =
    (dispute.status || '').toUpperCase() === 'WON' ||
    (dispute.status || '').toUpperCase() === 'LOST' ||
    (dispute.status || '').toUpperCase() === 'CLOSED' ||
    (dispute.workflow_stage || '').toUpperCase() === 'RESOLVED';

  // Normalize active step
  const isReviewMode =
    activeStep === 'review' ||
    activeStep === 'ai_analysis' ||
    activeStep === 'evidence' ||
    activeStep === 'merchant_review' ||
    activeStep === 'submission';

  return (
    <div className="space-y-4 pb-8 flex-1 flex flex-col">
      {/* 1. Case Header */}
      <CaseHeader dispute={dispute} onRefresh={() => loadCaseData(true)} />

      {/* 2. Merchant Journey Step Navigation */}
      <WorkflowStepNav
        activeStep={activeStep}
        onSelectStep={(step) => setActiveStep(step)}
        status={dispute.status}
        workflowStage={dispute.workflow_stage}
      />

      {/* 3. Primary Workspace Container */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Step 1: Overview */}
        {activeStep === 'overview' && (
          <CaseOverviewTab
            dispute={dispute}
            analysis={case_analysis}
            auditTrail={audit_trail || []}
            packageInspection={package_inspection}
            onContinue={() => setActiveStep('review')}
          />
        )}

        {/* Step 2: Review (The Unified Merchant Control Center) */}
        {isReviewMode && (
          <CaseMerchantControlCenter
            dispute={dispute}
            analysis={case_analysis}
            evidenceList={evidenceList}
            readiness={readiness || undefined}
            packageInspection={package_inspection}
            onRefresh={() => loadCaseData(true)}
            onSubmittedSuccess={() => {
              loadCaseData(true);
              setActiveStep('razorpay_review');
            }}
            isReadOnly={isSubmittedOrResolved}
          />
        )}

        {/* Step 3: Razorpay Gateway Review */}
        {activeStep === 'razorpay_review' && (
          <CaseRazorpayReviewTab
            dispute={dispute}
            analysis={case_analysis}
            onRefresh={() => loadCaseData(true)}
            onBackToSubmission={() => setActiveStep('review')}
            onViewOutcome={() => setActiveStep('outcome')}
            isResolved={isResolved}
          />
        )}

        {/* Step 4: Final Outcome & Chronological Audit Stream */}
        {activeStep === 'outcome' && (
          <CaseOutcomeTab
            dispute={dispute}
            analysis={case_analysis}
            auditTrail={audit_trail || []}
            onBackToReview={() => setActiveStep('razorpay_review')}
            onGoToDisputes={() => navigate('/disputes')}
          />
        )}
      </div>
    </div>
  );
};
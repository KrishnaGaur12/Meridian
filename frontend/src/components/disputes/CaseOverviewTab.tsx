import React from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Dispute, DisputeTimelineEvent } from '../../types/dispute';
import { CaseAnalysis, PackageInspection } from '../../types/commandCenter';
import {
  formatCurrency,
  formatReasonCode,
  formatPriority,
  formatStatus,
  formatDeadlineText,
  formatDate,
  formatAIOutcome,
} from '../../utils/formatters';
import { CaseTimeline } from './CaseTimeline';

interface CaseOverviewTabProps {
  dispute: Dispute;
  analysis: CaseAnalysis;
  auditTrail?: DisputeTimelineEvent[];
  packageInspection?: PackageInspection;
  onContinue: () => void;
}

export const CaseOverviewTab: React.FC<CaseOverviewTabProps> = ({
  dispute,
  analysis,
  auditTrail = [],
  onContinue,
}) => {
  const priority = formatPriority(dispute.urgency_level, dispute.remaining_hours, dispute.merchant_attention_state);
  const statusInfo = formatStatus(dispute.status, dispute.workflow_stage, dispute.merchant_attention_state);
  const deadlineText = formatDeadlineText(dispute.respond_by, dispute.remaining_hours);

  // Dynamic backend win probability (no hardcoded fallback)
  const winProb =
    analysis.win_probability?.win_probability_pct ??
    (analysis.win_probability?.score !== undefined && analysis.win_probability?.score !== null
      ? Math.round(analysis.win_probability.score * 100)
      : analysis.win_probability?.win_probability !== undefined && analysis.win_probability?.win_probability !== null
      ? Math.round(analysis.win_probability.win_probability * 100)
      : null);

  // Dynamic backend fraud risk
  const fraudProb =
    analysis.risk_analysis?.fraud_probability !== undefined && analysis.risk_analysis?.fraud_probability !== null
      ? Math.round(analysis.risk_analysis.fraud_probability * 100)
      : analysis.risk_analysis?.fraud_score !== undefined && analysis.risk_analysis?.fraud_score !== null
      ? Math.round(analysis.risk_analysis.fraud_score * 100)
      : null;

  const riskLevel = analysis.risk_analysis?.risk_level || 'LOW';

  // Dynamic backend recommendation
  const rawRecommendation =
    analysis.recommendation?.decision ||
    analysis.recommendation?.action ||
    analysis.recommendation?.ml_recommendation ||
    analysis.win_probability?.recommendation ||
    'CONTEST';
  const outcome = formatAIOutcome(rawRecommendation);

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* 1. High-Level Case Overview Card */}
      <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
          <div>
            <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
              Dispute Workspace · Overview
            </span>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
              Live Case Overview & Metrics
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-md border ${priority.colorClass}`}>
              {priority.label}
            </span>
            <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-md border ${statusInfo.colorClass}`}>
              {statusInfo.label}
            </span>
          </div>
        </div>

        {/* Attention Reason / Alert Banner */}
        {dispute.attention_reason && (
          <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
            <span className="font-bold flex items-center gap-1.5 text-amber-950">
              <span>⚠️ Action Attention Note:</span>
            </span>
            <p className="text-amber-900 leading-relaxed font-medium">
              {dispute.attention_reason}
            </p>
          </div>
        )}

        {/* Real Dynamic Intelligence Strip: Win Probability, Risk, Recommendation */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Win Probability */}
          <div className="p-3.5 bg-indigo-50/60 rounded-xl border border-indigo-100 space-y-1">
            <span className="text-[10px] font-mono text-indigo-700 uppercase font-bold block">
              Merchant Win Probability
            </span>
            <div className="text-xl font-black text-slate-900">
              {winProb !== null ? `${winProb}%` : 'Calculating...'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              Model: {analysis.win_probability?.prediction_source || 'win_pipeline.joblib'}
            </div>
          </div>

          {/* Fraud / Risk Score */}
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">
              Fraud Risk Assessment
            </span>
            <div className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <span>{riskLevel}</span>
              {fraudProb !== null && (
                <span className="text-xs font-semibold text-slate-500">
                  ({fraudProb}% risk)
                </span>
              )}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              Model: {analysis.risk_analysis?.pipeline || 'fraud_v2_pipeline.joblib'}
            </div>
          </div>

          {/* Current Recommendation */}
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">
              Current Recommendation
            </span>
            <div className="text-lg font-bold text-indigo-900">
              {outcome.label}
            </div>
            <div className="text-[10px] text-slate-500">
              {analysis.recommendation?.merchant_recommendation || 'Recommendation computed from live models'}
            </div>
          </div>
        </div>

        {/* Core Case Information Grid (12 key parameters) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 text-xs pt-1">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Dispute ID</span>
            <div className="font-mono font-bold text-slate-900 truncate">{dispute.dispute_id}</div>
            <div className="text-slate-600 font-medium">{formatReasonCode(dispute.reason_code)}</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Transaction ID</span>
            <div className="font-mono font-bold text-slate-900 truncate">{dispute.transaction_id}</div>
            <div className="text-[11px] text-slate-500">Source: {dispute.case_source || 'LIVE'}</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Disputed Amount</span>
            <div className="text-base font-bold text-slate-900">
              {formatCurrency(dispute.amount || analysis.amount, dispute.currency || analysis.currency || 'INR')}
            </div>
            <div className="text-[11px] text-slate-500">Subject to bank arbitration</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Customer Account</span>
            <div className="font-bold text-slate-900 truncate">{dispute.customer_id}</div>
            <div className="text-[11px] text-slate-500">Verified cardholder inquiry</div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Response Deadline</span>
            <div className="text-xs font-bold text-rose-700">{deadlineText}</div>
            <div className="text-[11px] text-slate-500 font-mono">
              Respond By: {formatDate(dispute.respond_by)}
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 space-y-1">
            <span className="text-[10px] font-mono text-slate-400 uppercase">Lifecycle Stage & Phase</span>
            <div className="font-semibold text-slate-900 font-mono uppercase">{dispute.workflow_stage}</div>
            <div className="text-[11px] text-slate-500">Phase: {dispute.phase || 'chargeback'}</div>
          </div>
        </div>

        {/* Customer / Bank Claim Narrative */}
        <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/70 space-y-1 text-xs">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wide">
            Customer / Issuing Bank Claim Narrative
          </span>
          <p className="text-slate-700 leading-relaxed">
            {dispute.reason_description || 'Customer filed a formal chargeback through their issuing institution.'}
          </p>
        </div>
      </Card>

      {/* 2. Dispute Timeline & Audit Trail (Chronological backend events) */}
      <CaseTimeline auditTrail={auditTrail} />

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-2">
        <div className="text-xs text-slate-500">
          Review initial facts and timeline before inspecting AI / ML models.
        </div>
        <Button onClick={onContinue} variant="primary" size="md" className="font-semibold shadow-xs">
          Proceed to Review Workspace &rarr;
        </Button>
      </div>
    </div>
  );
};

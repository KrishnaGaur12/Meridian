import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { CaseAnalysis, AIRecommendation } from '../../types/commandCenter';
import { formatAIOutcome, formatAssessment } from '../../utils/formatters';

interface CaseAIAnalysisTabProps {
  analysis: CaseAnalysis;
  disputeId: string;
  isAnalyzing?: boolean;
  onBack: () => void;
  onContinue: () => void;
}

export const CaseAIAnalysisTab: React.FC<CaseAIAnalysisTabProps> = ({
  analysis,
  disputeId,
  isAnalyzing = false,
  onBack,
  onContinue,
}) => {
  const [showDeepBreakdown, setShowDeepBreakdown] = useState(false);

  // If analysis is in progress, display active analyzing lifecycle state
  if (isAnalyzing) {
    return (
      <div className="space-y-4 animate-in fade-in duration-200">
        <Card className="p-8 bg-white border-indigo-200 shadow-sm text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center mx-auto text-indigo-600 animate-spin">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">AI Analysis</h3>
            <p className="text-xs text-indigo-600 font-medium mt-1">Analyzing dispute...</p>
          </div>
          <div className="max-w-md mx-auto p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-left text-xs space-y-2">
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider font-mono">
              Live Analysis Pipeline:
            </div>
            <div className="space-y-1 text-slate-600 text-[11px]">
              <div className="flex items-center gap-2 text-indigo-700 font-medium">
                <span className="w-2 h-2 rounded-full bg-indigo-600 animate-ping" />
                <span>1. Evidence Engine Analysis & Gap Detection</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>2. Fraud Model V2 Inference</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>3. Win Probability Model Inference (win_pipeline.joblib)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>4. Confidence Calculation & Risk Decision</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>5. DeepSeek Reasoning & Recommendation Conflict Detection</span>
              </div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const rec: AIRecommendation = analysis.recommendation || {};

  // 1. Core Recommendations & Conflict
  const mlRec = rec.ml_recommendation || analysis.win_probability?.recommendation || 'CONTEST';
  const aiRec = rec.ai_recommendation || rec.action || 'CONTEST';
  const finalDecision = rec.decision || rec.action || mlRec || 'CONTEST';
  const conflictDetected = rec.conflict_detected ?? (mlRec !== aiRec);

  const finalOutcome = formatAIOutcome(finalDecision);
  const mlOutcome = formatAIOutcome(mlRec);
  const aiOutcome = formatAIOutcome(aiRec);

  // 2. Real Win Probability from backend (models/win_pipeline.joblib)
  const winProbValue =
    analysis.win_probability?.win_probability_pct ??
    (analysis.win_probability?.score !== undefined && analysis.win_probability?.score !== null
      ? Math.round(analysis.win_probability.score * 100)
      : analysis.win_probability?.win_probability !== undefined && analysis.win_probability?.win_probability !== null
      ? Math.round(analysis.win_probability.win_probability * 100)
      : null);

  // 3. Real ML Confidence from backend
  const confidenceScore =
    analysis.win_probability?.confidence_score !== undefined && analysis.win_probability?.confidence_score !== null
      ? Math.round(analysis.win_probability.confidence_score * 100)
      : null;

  const rawConfidenceLevel =
    analysis.win_probability?.confidence_level ||
    rec.confidence ||
    (confidenceScore && confidenceScore >= 80 ? 'HIGH' : confidenceScore && confidenceScore >= 50 ? 'MEDIUM' : 'LOW');

  const assessment = formatAssessment(
    analysis.win_probability?.score ?? analysis.win_probability?.win_probability ?? null,
    rawConfidenceLevel
  );

  const confidenceExplanation =
    analysis.win_probability?.confidence_explanation ||
    `Statistical confidence level: ${rawConfidenceLevel}${confidenceScore !== null ? ` (${confidenceScore}%)` : ''}`;

  // 4. Fraud Risk from backend (Fraud V2)
  const rawFraudProb = analysis.risk_analysis?.fraud_probability ?? analysis.risk_analysis?.fraud_score ?? null;
  const fraudScorePct = rawFraudProb !== null ? Math.round(rawFraudProb * 100) : null;
  const riskLevel = analysis.risk_analysis?.risk_level || 'LOW';

  // 5. DeepSeek Reasoning vs Fallback Provenance
  const aiSource = (rec.ai_source || (rec as any).ai_status || '').toUpperCase();
  const isFallback = aiSource === 'FALLBACK' || aiSource === 'DETERMINISTIC_FALLBACK';

  const reasoningText =
    rec.reasoning ||
    rec.explanation ||
    rec.reason ||
    analysis.attention_reason ||
    'AI analysis evaluated transaction parameters, authenticated evidence records, and cardholder dispute narrative.';

  // 6. Evidence Gaps from backend
  const missingEvidenceList = analysis.evidence_intelligence?.missing_evidence || [];
  const unverifiedEvidenceList = analysis.evidence_intelligence?.unverified_evidence || [];
  const completenessPct =
    analysis.evidence_intelligence?.completeness_percentage ??
    (analysis.evidence_intelligence?.evidence_completeness !== undefined
      ? Math.round((analysis.evidence_intelligence.evidence_completeness <= 1 ? analysis.evidence_intelligence.evidence_completeness * 100 : analysis.evidence_intelligence.evidence_completeness))
      : null);

  // 7. Recommended Action & Guidance
  const merchantGuidance =
    rec.merchant_recommendation ||
    (finalDecision === 'CONTEST' ? 'Challenge this dispute' : finalDecision === 'ACCEPT' ? 'Accept dispute concession' : 'Investigate case further');

  const nextActionsList =
    analysis.next_actions && analysis.next_actions.length > 0
      ? analysis.next_actions
      : ['Review available evidence records in the next workspace tab.', 'Approve verified documents for the representation package.'];

  const positiveFactors = rec.positive_factors && rec.positive_factors.length > 0 ? rec.positive_factors : rec.key_factors || [];
  const negativeFactors = rec.negative_factors || [];

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* ------------------------------
          AI / ML ANALYSIS
      ------------------------------ */}
      <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
          <div>
            <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
              Dispute Workspace · Step 2
            </span>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
              AI / ML ANALYSIS
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              Win Pipeline: {analysis.win_probability?.pipeline || 'win_pipeline.joblib'}
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              Fraud: {analysis.risk_analysis?.pipeline || 'fraud_v2_pipeline.joblib'}
            </span>
          </div>
        </div>

        {/* 6 Authoritative Backend Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* 1. Fraud Risk */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">
              Fraud Risk
            </span>
            <div className="text-base font-bold text-slate-900">
              {riskLevel}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              {fraudScorePct !== null ? `${fraudScorePct}% probability` : 'Calculated'}
            </div>
          </div>

          {/* 2. Merchant Win Probability */}
          <div className="p-3 bg-indigo-50/70 rounded-xl border border-indigo-100 space-y-1">
            <span className="text-[10px] font-mono text-indigo-700 uppercase font-bold block">
              Merchant Win Probability
            </span>
            <div className="text-xl font-black text-slate-900">
              {winProbValue !== null ? `${winProbValue}%` : 'Calculating...'}
            </div>
            <div className="text-[10px] text-indigo-600 font-mono">
              win_pipeline.joblib
            </div>
          </div>

          {/* 3. Confidence */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">
              Confidence
            </span>
            <div>
              <span className={`inline-block px-2 py-0.5 text-xs font-bold rounded border ${assessment.badgeClass}`}>
                {rawConfidenceLevel}
              </span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono truncate">
              {confidenceScore !== null ? `${confidenceScore}% certainty` : 'Statistical gate'}
            </div>
          </div>

          {/* 4. ML Recommendation */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">
              ML Recommendation
            </span>
            <div className="text-sm font-bold text-slate-900">
              {mlOutcome.label}
            </div>
            <div className="text-[10px] text-slate-500">
              Deterministic Classifier
            </div>
          </div>

          {/* 5. DeepSeek Recommendation */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold block">
              DeepSeek Rec.
            </span>
            <div className="text-sm font-bold text-slate-900">
              {aiOutcome.label}
            </div>
            <div className="text-[10px] text-slate-500">
              Language Intelligence
            </div>
          </div>

          {/* 6. Recommendation Conflict */}
          <div className={`p-3 rounded-xl border space-y-1 ${conflictDetected ? 'bg-amber-50/80 border-amber-300' : 'bg-slate-50 border-slate-200/80'}`}>
            <span className="text-[10px] font-mono uppercase font-bold block text-slate-500">
              Conflict Status
            </span>
            <div className={`text-xs font-bold ${conflictDetected ? 'text-amber-800' : 'text-emerald-700'}`}>
              {conflictDetected ? '⚠️ Conflict Detected' : '✓ No Conflict'}
            </div>
            <div className="text-[10px] text-slate-500">
              {conflictDetected ? 'ML & AI diverge' : 'Models in agreement'}
            </div>
          </div>
        </div>

        {/* Confidence Explanation Banner */}
        {analysis.win_probability?.confidence_explanation && (
          <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/70 text-xs text-slate-600 font-mono">
            <strong>Confidence Explanation:</strong> {analysis.win_probability.confidence_explanation}
          </div>
        )}
      </Card>

      {/* ------------------------------
          AI REASONING
      ------------------------------ */}
      <Card className="p-5 bg-gradient-to-br from-white via-indigo-50/20 to-slate-50 border-indigo-100 shadow-2xs space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
              Reasoning Engine
            </span>
            <h3 className="text-base font-bold text-slate-900">
              AI REASONING
            </h3>
          </div>

          {/* AI Provenance Label: Transparent DeepSeek vs Fallback Indicator */}
          {isFallback ? (
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
              AI reasoning: Fallback
            </span>
          ) : (
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-900 border border-indigo-300">
              DeepSeek AI Reasoning
            </span>
          )}
        </div>

        {/* Why this case should be contested / reasoning */}
        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-2xs space-y-2 text-xs">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
            Why this case looks this way / Rationale
          </span>
          <p className="text-slate-800 leading-relaxed text-xs sm:text-sm font-medium whitespace-pre-line">
            {reasoningText}
          </p>
        </div>

        {/* Supporting Factors Breakdown Toggle */}
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowDeepBreakdown(!showDeepBreakdown)}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer select-none"
          >
            <span>{showDeepBreakdown ? 'Hide factor analysis' : 'View supporting & risk factor breakdown'}</span>
            <svg
              className={`w-3.5 h-3.5 transform transition-transform ${showDeepBreakdown ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showDeepBreakdown && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs animate-in fade-in duration-150">
              <div className="p-3.5 bg-white rounded-xl border border-slate-200 space-y-2">
                <span className="font-bold text-slate-900 flex items-center gap-1 text-[11px]">
                  <span className="text-emerald-600">✓</span> Supporting Factors (Defense Strength)
                </span>
                <ul className="space-y-1 text-slate-600">
                  {positiveFactors.length > 0 ? (
                    positiveFactors.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-600 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-slate-500">• Authenticated payment verification and carrier tracking present.</li>
                  )}
                </ul>
              </div>

              <div className="p-3.5 bg-white rounded-xl border border-slate-200 space-y-2">
                <span className="font-bold text-slate-900 flex items-center gap-1 text-[11px]">
                  <span className="text-amber-600">⚠️</span> Risk Factors & Watchpoints
                </span>
                <ul className="space-y-1 text-slate-600">
                  {negativeFactors.length > 0 ? (
                    negativeFactors.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-amber-600 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))
                  ) : (
                    <li className="text-slate-500">• No severe counter-indicators flagged against merchant records.</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* ------------------------------
          EVIDENCE GAPS & RECOMMENDED ACTION
      ------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ------------------------------
            EVIDENCE GAPS
        ------------------------------ */}
        <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold text-amber-700 uppercase tracking-wider">
                Completeness
              </span>
              <h3 className="text-sm font-bold text-slate-900">
                EVIDENCE GAPS
              </h3>
            </div>
            {completenessPct !== null && (
              <span className="text-[10px] font-mono font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                Completeness: {completenessPct}%
              </span>
            )}
          </div>

          <div className="space-y-2 text-xs">
            {missingEvidenceList.length > 0 ? (
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-amber-900 block">
                  Missing Evidence Items:
                </span>
                <ul className="space-y-1 text-slate-700">
                  {missingEvidenceList.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 p-2 bg-amber-50/60 rounded-lg border border-amber-200/70">
                      <span className="text-amber-600 font-bold">⚠️</span>
                      <span className="capitalize">{item.replace(/_/g, ' ')}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="p-3 bg-emerald-50/70 rounded-xl border border-emerald-200 text-emerald-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <span>✓</span> All Required Evidence Present
                </div>
                <p className="text-[11px] text-emerald-800">
                  All critical defense evidence items have been identified and retrieved from system records.
                </p>
              </div>
            )}

            {unverifiedEvidenceList.length > 0 && (
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-600 space-y-0.5">
                <span className="font-semibold text-slate-700 block">Unverified Items Pending Review:</span>
                <p>{unverifiedEvidenceList.map((i) => i.replace(/_/g, ' ')).join(', ')}</p>
              </div>
            )}
          </div>
        </Card>

        {/* ------------------------------
            RECOMMENDED ACTION
        ------------------------------ */}
        <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
                Strategy
              </span>
              <h3 className="text-sm font-bold text-slate-900">
                RECOMMENDED ACTION
              </h3>
            </div>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                finalOutcome.intent === 'contest'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : finalOutcome.intent === 'accept'
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
            >
              {finalOutcome.label}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            {/* Merchant Guidance */}
            <div className="p-3.5 bg-indigo-50/60 rounded-xl border border-indigo-100 space-y-1">
              <span className="text-[10px] font-mono font-bold text-indigo-900 uppercase tracking-wide block">
                Merchant Guidance
              </span>
              <p className="text-slate-800 font-medium leading-relaxed">
                {merchantGuidance}
              </p>
            </div>

            {/* Step-by-step next actions */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-semibold text-slate-700 block">
                Next Best Actions:
              </span>
              <ul className="space-y-1 text-slate-600">
                {nextActionsList.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 p-2 bg-slate-50 rounded-lg border border-slate-200/70">
                    <span className="text-indigo-600 font-bold font-mono">{idx + 1}.</span>
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between pt-2">
        <Button onClick={onBack} variant="outline" size="md">
          &larr; Back to Overview
        </Button>
        <Button onClick={onContinue} variant="primary" size="md" className="font-semibold shadow-xs">
          Continue to Evidence Workspace &rarr;
        </Button>
      </div>
    </div>
  );
};

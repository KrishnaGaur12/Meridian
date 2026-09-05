import { Dispute, DisputeTimelineEvent } from './dispute';
import { EvidenceItem } from './evidence';

export interface AIRecommendation {
  decision?: 'CONTEST' | 'ACCEPT' | 'INVESTIGATE' | string;
  action?: 'CONTEST' | 'ACCEPT' | 'INVESTIGATE' | string;
  action_label?: string;
  ml_recommendation?: 'CONTEST' | 'ACCEPT' | 'INVESTIGATE' | string;
  ai_recommendation?: 'CONTEST' | 'ACCEPT' | 'INVESTIGATE' | string;
  conflict_detected?: boolean;
  merchant_recommendation?: string;
  explanation?: string;
  reasoning?: string;
  reason?: string;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  assessment_label?: 'Strong' | 'Moderate' | 'Needs Review' | 'Low' | string;
  ai_source?: 'DEEPSEEK' | 'FALLBACK' | 'LIVE_MODEL' | string;
  ai_status?: string;
  headline?: string;
  potential_recovery?: number;
  potential_recovery_amount?: number;
  currency?: string;
  key_factors?: string[];
  positive_factors?: string[];
  negative_factors?: string[];
  rebuttal_preview?: string;
}

export interface AIExplainability {
  dispute_id?: string;
  transaction_id?: string;
  fraud_explainability?: Record<string, any>;
  win_explainability?: Record<string, any>;
}

export interface RiskAnalysis {
  fraud_probability?: number;
  fraud_score?: number;
  risk_level?: string;
  decision?: string;
  model_version?: string;
  pipeline?: string;
  prediction_source?: string;
  ml_status?: string;
}

export interface EvidenceIntelligence {
  evidence_completeness?: number;
  evidence_quality?: string;
  missing_evidence?: string[];
  unverified_evidence?: string[];
  approved_evidence_count?: number;
  contradictions_count?: number;
  contradiction_severity?: string;
  evidence_count?: number;
  available_count?: number;
  missing_count?: number;
  completeness_percentage?: number;
  evidence_items?: EvidenceItem[];
  evidence?: EvidenceItem[];
}

export interface WinProbability {
  score?: number;
  win_probability?: number;
  win_probability_pct?: number;
  confidence_score?: number;
  confidence_level?: string;
  confidence_explanation?: string;
  recommendation?: string;
  prediction_source?: string;
  pipeline?: string;
  ml_status?: string;
}

export interface CaseAnalysis {
  dispute_id: string;
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  status: string;
  phase: string;
  workflow_stage: string;
  case_source: string;
  merchant_attention_state: string;
  ai_last_checked?: string;
  attention_reason?: string;
  respond_by?: string;
  remaining_hours?: number;
  remaining_time_human?: string;
  is_overdue?: boolean;
  deadline_status?: string;
  urgency_level?: string;
  case_summary?: Record<string, any>;
  risk_analysis?: RiskAnalysis;
  evidence_intelligence?: EvidenceIntelligence;
  win_probability?: WinProbability;
  recommendation?: AIRecommendation;
  next_actions?: string[];
}

export interface NextBestAction {
  action_type: string;
  priority: string;
  title: string;
  reason: string;
  why_asking?: string;
  trigger_data_summary?: string;
  expected_impact: string;
  confidence?: string;
  what_if_nothing?: string;
  if_you_do_nothing?: string;
  next_step_after?: string;
  blocking_items: string[];
  target_stage?: string;
  target_route?: string;
}

export interface PackageInspection {
  package_metadata?: Record<string, any>;
  customer?: Record<string, any>;
  transaction?: Record<string, any>;
  payment?: Record<string, any>;
  order?: Record<string, any>;
  fulfillment?: Record<string, any>;
  evidence_intelligence?: EvidenceItem[];
  evidence_package?: {
    evidence?: EvidenceItem[];
  };
  ai_analysis?: Record<string, any>;
  rebuttal?: {
    rebuttal_text?: string;
    rebuttal_letter?: string;
    executive_summary?: string;
    key_defense_arguments?: string[];
    suggested_edits?: string;
  };
  readiness_gate?: {
    can_submit?: boolean;
    readiness_percentage?: number;
    blocking_issues?: string[];
    warnings?: string[];
  };
  local_gateway_boundary?: string;
}

export interface CommandCenterSnapshot {
  dispute_id: string;
  dispute: Dispute;
  case_analysis: CaseAnalysis;
  explainability: AIExplainability;
  next_action: NextBestAction;
  package_inspection: PackageInspection;
  audit_trail: DisputeTimelineEvent[];
  evidence?: EvidenceItem[];
  evidence_summary?: Record<string, any>;
  required_evidence?: string[];
  missing_evidence?: string[];
  submission_readiness?: string;
  submission_blockers?: string[];
  merchant_attention_state?: string;
}
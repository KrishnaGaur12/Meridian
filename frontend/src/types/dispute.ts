export type DisputeStatus = 'OPEN' | 'UNDER_REVIEW' | 'WON' | 'LOST' | 'CLOSED' | 'under_review';
export type DisputePhase = 'retrieval' | 'chargeback' | 'pre_arbitration' | 'arbitration' | 'fraud';
export type WorkflowStage =
  | 'DISPUTE_RAISED'
  | 'EVIDENCE_COLLECTION'
  | 'EVIDENCE_BUNDLE_CREATED'
  | 'MERCHANT_REVIEW'
  | 'READY_FOR_SUBMISSION'
  | 'SUBMITTED'
  | 'RESOLVED';

export type MerchantAttentionState =
  | 'ACTION_REQUIRED'
  | 'REVIEW_RECOMMENDED'
  | 'AI_HANDLING'
  | 'WAITING';

export type CaseSource = 'DEMO' | 'SIMULATED_RAZORPAY' | 'REAL_RAZORPAY';

export type PriorityLevel = 'URGENT' | 'IMPORTANT' | 'READY' | 'NORMAL';

export interface Dispute {
  dispute_id: string;
  transaction_id: string;
  customer_id: string;
  reason_code: string;
  reason_description: string;
  status: DisputeStatus;
  phase: DisputePhase;
  respond_by?: string | null;
  workflow_stage: WorkflowStage;
  case_source: CaseSource;
  merchant_attention_state: MerchantAttentionState;
  ai_last_checked?: string | null;
  attention_reason?: string | null;
  created_at: string;
  remaining_hours?: number | null;
  remaining_time_human?: string | null;
  is_overdue: boolean;
  deadline_status: string;
  urgency_level: string;
  amount?: number | null;
  currency?: string | null;
}

export interface DisputeTimelineEvent {
  event_id: string;
  dispute_id: string;
  event_type: string;
  title: string;
  description: string;
  timestamp: string;
  actor_type?: string;
  previous_stage?: string;
  new_stage?: string;
  metadata?: Record<string, any>;
}

export interface DisputeCaseReadiness {
  dispute_id: string;
  readiness_status: string;
  readiness_percentage: number;
  can_submit: boolean;
  blocking_issues: string[];
  warnings: string[];
  completed_requirements: string[];
  next_actions: string[];
  evidence_mapping: Array<{
    evidence_type: string;
    label: string;
    is_available: boolean;
    verification_status: string;
    evidence_id?: string;
  }>;
  deadline_info: {
    respond_by?: string;
    remaining_hours?: number;
    urgency_level?: string;
    is_overdue?: boolean;
  };
}

export interface DisputeSubmitResponse {
  dispute_id: string;
  workflow_stage: string;
  status: string;
  is_submitted?: boolean;
  gateway_reference_id?: string;
  submission_boundary_notice?: string;
  event?: Record<string, any>;
}

export interface DisputeOutcomeResponse {
  dispute_id: string;
  outcome: 'WON' | 'LOST';
  new_status: 'WON' | 'LOST';
  workflow_stage: 'RESOLVED';
  merchant_attention_state: 'WAITING';
  message: string;
  event?: Record<string, any>;
}

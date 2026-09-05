export type EvidenceType =
  | 'payment_confirmation'
  | 'proof_of_delivery'
  | 'customer_communication'
  | 'refund_policy'
  | 'ip_address_log'
  | 'invoice'
  | 'tos_acceptance'
  | 'cancellation_policy'
  | 'merchant_notes'
  | string;

export type VerificationStatus =
  | 'AVAILABLE'
  | 'VERIFIED'
  | 'UNVERIFIED'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'INVALID'
  | 'MISSING'
  | string;

export type ApprovalStatus = 'APPROVED' | 'PENDING_APPROVAL' | 'REJECTED' | string;

export type EvidenceSource = 'DATABASE' | 'MERCHANT_UPLOAD' | 'MERCHANT_FILE_UPLOAD' | 'SYSTEM' | string;

export interface EvidenceItem {
  evidence_id?: string;
  dispute_id?: string;
  transaction_id?: string;
  evidence_type: string;
  title?: string;
  description?: string;
  source?: EvidenceSource;
  verification_status?: VerificationStatus;
  approval_status?: ApprovalStatus;
  merchant_approval_status?: ApprovalStatus;
  ai_analysis_status?: string;
  ai_relevance?: string;
  why_it_matters?: string;
  extracted_facts?: Record<string, any>;
  status?: string;
  verification_details?: string;
  evidence_data?: Record<string, any>;
  data?: Record<string, any>;
  approved_at?: string;
  approved_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ImpactDelta {
  win_probability_before?: number;
  win_probability_after?: number;
  win_probability_delta?: number | string;
  fraud_score_before?: number;
  fraud_score_after?: number;
  attention_state_before?: string;
  attention_state_after?: string;
  attention_state_changed?: boolean;
  message?: string;
  recommendation_before?: string;
  recommendation_after?: string;
}

export interface CreateEvidencePayload {
  dispute_id: string;
  evidence_type: string;
  title: string;
  description?: string;
  verification_status?: string;
  approval_status?: string;
  evidence_data?: Record<string, any>;
  transaction_id?: string;
}

export interface UpdateEvidencePayload {
  title?: string;
  description?: string;
  evidence_type?: string;
  verification_status?: string;
  approval_status?: string;
  evidence_data?: Record<string, any>;
}

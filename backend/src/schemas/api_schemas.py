"""
Pydantic Schemas for FastAPI Endpoints.
Input validation & output response serialization.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# --- TRANSACTION SCHEMAS ---
class TransactionCreateSchema(BaseModel):
    transaction_id: Optional[str] = Field(None, description="Unique transaction ID. Generated if omitted.")
    customer_id: Optional[str] = Field(None, description="Customer ID. Defaults to CUST_DEFAULT if omitted.")
    merchant_id: str = Field(default="MERCHANT_001")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD")
    payment_method: str = Field(default="credit_card")
    merchant_category: str = Field(default="retail")
    transaction_country: str = Field(default="US")
    transaction_status: str = Field(default="SUCCESS")

    # ML Model Required Parameters
    transaction_hour: int = Field(default=12, ge=0, le=23)
    account_age_days: int = Field(default=180, ge=0)
    previous_chargebacks: int = Field(default=0, ge=0)
    device_type: str = Field(default="mobile")
    is_international: int = Field(default=0, ge=0, le=1)
    is_high_risk_merchant: int = Field(default=0, ge=0, le=1)
    transaction_velocity_1h: int = Field(default=0, ge=0)
    transaction_velocity_24h: int = Field(default=0, ge=0)
    avg_transaction_amount_30d: float = Field(default=100.0, gt=0)

    # Optional nested payloads
    payment: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    fulfillment: Optional[Dict[str, Any]] = None

class TransactionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    customer_id: str
    merchant_id: str
    amount: float
    currency: str
    timestamp: str
    payment_method: str
    merchant_category: str
    transaction_country: str
    transaction_status: str
    transaction_hour: int
    account_age_days: int
    previous_chargebacks: int
    device_type: str
    is_international: int
    is_high_risk_merchant: int
    transaction_velocity_1h: int
    transaction_velocity_24h: int
    avg_transaction_amount_30d: float

# --- DISPUTE SCHEMAS ---
class DisputeCreateSchema(BaseModel):
    dispute_id: Optional[str] = Field(None, description="Dispute ID. Generated if omitted.")
    transaction_id: str = Field(..., description="Associated transaction ID")
    reason_code: str = Field(..., description="e.g. product_not_received, fraudulent_transaction, duplicate_charge, refund_not_processed")
    reason_description: Optional[str] = Field(default="", description="Detailed dispute description")
    status: str = Field(default="OPEN", description="Official bank status: OPEN, UNDER_REVIEW, WON, LOST, CLOSED")
    phase: str = Field(default="chargeback", description="Razorpay dispute phase: retrieval, chargeback, pre_arbitration, arbitration, fraud")
    workflow_stage: Optional[str] = Field(default="DISPUTE_RAISED", description="Internal AI workflow stage")
    case_source: Optional[str] = Field(default="SIMULATED_RAZORPAY", description="DEMO, SIMULATED_RAZORPAY, REAL_RAZORPAY")
    merchant_attention_state: Optional[str] = Field(default="ACTION_REQUIRED", description="ACTION_REQUIRED, REVIEW_RECOMMENDED, AI_HANDLING, WAITING")

class DisputeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dispute_id: str
    transaction_id: str
    customer_id: str
    reason_code: str
    reason_description: str
    status: str
    phase: str = "chargeback"
    respond_by: Optional[str] = None
    workflow_stage: str = "DISPUTE_RAISED"
    case_source: str = "SIMULATED_RAZORPAY"
    merchant_attention_state: str = "ACTION_REQUIRED"
    ai_last_checked: Optional[str] = None
    attention_reason: Optional[str] = None
    created_at: str
    remaining_hours: Optional[float] = None
    remaining_time_human: Optional[str] = None
    is_overdue: bool = False
    deadline_status: str = "ON_TRACK"
    urgency_level: str = "SAFE"
    amount: Optional[float] = None
    currency: Optional[str] = None

class DisputeTimelineEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    dispute_id: str
    event_type: str
    title: str
    description: str
    timestamp: str

class DisputeWorkflowTransitionSchema(BaseModel):
    target_stage: str = Field(..., description="Target InternalWorkflowStage")
    event_title: Optional[str] = Field(None, description="Optional title for timeline event")
    event_desc: Optional[str] = Field(None, description="Optional description for timeline event")

class DisputeCaseReadinessSchema(BaseModel):
    dispute_id: str
    readiness_status: str
    readiness_percentage: int
    can_submit: bool
    blocking_issues: List[str]
    warnings: List[str]
    completed_requirements: List[str]
    next_actions: List[str]
    evidence_mapping: List[Dict[str, Any]]
    deadline_info: Dict[str, Any]

class DisputeSubmitRequestSchema(BaseModel):
    merchant_position: Optional[str] = Field(default="CONTEST", description="Merchant representment position: CONTEST or ACCEPT")
    response_text: Optional[str] = Field(default=None, description="Optional custom response / rebuttal statement override")

class DisputeSubmitResponseSchema(BaseModel):
    dispute_id: str
    workflow_stage: str
    status: str
    is_submitted: bool
    submission_id: Optional[str] = None
    gateway_reference_id: Optional[str] = None
    merchant_position: Optional[str] = "CONTEST"
    submitted_at: Optional[str] = None
    submission_boundary_notice: str = "Submission recorded locally via Local Gateway Integration Boundary (Simulated Razorpay Gateway)."
    event: Dict[str, Any] = {}
    dispute: Optional[Dict[str, Any]] = None
    timeline: Optional[List[Dict[str, Any]]] = None

class DisputeOutcomeResponseSchema(BaseModel):
    dispute_id: str
    previous_status: str
    final_status: str
    workflow_stage: str
    merchant_attention_state: str
    outcome_reason: str
    is_simulated: bool
    win_probability: float
    evidence_completeness: float
    event: Dict[str, Any]

class DisputeCaseAnalysisSchema(BaseModel):
    dispute_id: str
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    status: str
    phase: str
    workflow_stage: str
    case_source: str = "SIMULATED_RAZORPAY"
    merchant_attention_state: str = "ACTION_REQUIRED"
    ai_last_checked: Optional[str] = None
    attention_reason: Optional[str] = None
    respond_by: Optional[str] = None
    remaining_hours: Optional[float] = None
    remaining_time_human: str
    is_overdue: bool
    deadline_status: str
    urgency_level: str = "SAFE"
    case_summary: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    evidence_intelligence: Dict[str, Any]
    win_probability: Dict[str, Any]
    recommendation: Dict[str, Any]
    next_actions: List[str]

class AIExplainabilitySchema(BaseModel):
    dispute_id: str
    transaction_id: str
    fraud_explainability: Dict[str, Any]
    win_explainability: Dict[str, Any]

class NextBestActionSchema(BaseModel):
    action_type: str
    priority: str
    title: str
    reason: str
    why_asking: Optional[str] = None
    trigger_data_summary: Optional[str] = None
    expected_impact: str
    confidence: Optional[str] = "HIGH"
    what_if_nothing: Optional[str] = None
    if_you_do_nothing: Optional[str] = None
    next_step_after: Optional[str] = None
    blocking_items: List[str]
    target_stage: str
    target_route: str

class DisputeAuditEventSchema(BaseModel):
    event_id: str
    dispute_id: str
    event_type: str
    title: str
    description: str
    timestamp: str
    actor_type: str = "SYSTEM"
    previous_stage: Optional[str] = None
    new_stage: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ChargebackPackageInspectionSchema(BaseModel):
    package_metadata: Dict[str, Any]
    customer: Dict[str, Any]
    transaction: Dict[str, Any]
    payment: Dict[str, Any]
    order: Dict[str, Any]
    fulfillment: Dict[str, Any]
    evidence_intelligence: List[Dict[str, Any]]
    ai_analysis: Dict[str, Any]
    rebuttal: Dict[str, Any]
    readiness_gate: Dict[str, Any]
    local_gateway_boundary: str

class CommandCenterSnapshotSchema(BaseModel):
    dispute_id: str
    dispute: DisputeResponseSchema
    case_analysis: Dict[str, Any]
    explainability: Dict[str, Any]
    next_action: Dict[str, Any]
    package_inspection: Dict[str, Any]
    audit_trail: List[Dict[str, Any]]
    evidence: Optional[List[Dict[str, Any]]] = None
    evidence_summary: Optional[Dict[str, Any]] = None
    required_evidence: Optional[List[str]] = None
    missing_evidence: Optional[List[str]] = None
    package: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    submission_readiness: Optional[str] = None
    submission_blockers: Optional[List[str]] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    merchant_attention_state: Optional[str] = None

class MLModelHealthSchema(BaseModel):
    fraud_model: Dict[str, Any]
    win_model: Dict[str, Any]




# --- RISK ASSESSMENT SCHEMAS ---
class RiskAssessmentResponseSchema(BaseModel):
    transaction_id: str
    risk_score: float
    risk_level: str
    decision: str
    model_version: str

# --- ERROR RESPONSE SCHEMA ---
class ErrorDetailSchema(BaseModel):
    message: str
    error_code: str

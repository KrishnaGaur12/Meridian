"""
Global Settings & Configuration for Razorpay AI Risk Manager.
Uses pathlib for OS-agnostic path management.
"""

from pathlib import Path
from enum import Enum

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SYNTHETIC_DATA_DIR = DATA_DIR / "synthetic"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

# Ensure essential directories exist
for path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, SYNTHETIC_DATA_DIR, EXTERNAL_DATA_DIR, MODELS_DIR, REPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Standardized Dispute Reasons
class DisputeReason(str, Enum):
    GOODS_NOT_RECEIVED = "GOODS_NOT_RECEIVED"
    GOODS_NOT_AS_DESCRIBED = "GOODS_NOT_AS_DESCRIBED"
    UNAUTHORIZED_TRANSACTION = "UNAUTHORIZED_TRANSACTION"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    REFUND_NOT_RECEIVED = "REFUND_NOT_RECEIVED"
    OTHER = "OTHER"

# Business Decision Thresholds & Bands
WIN_PROBABILITY_HIGH = 0.60
WIN_PROBABILITY_LOW = 0.35

FRAUD_PROBABILITY_HIGH = 0.70
FRAUD_PROBABILITY_MEDIUM = 0.40

COMPLETENESS_HIGH = 0.75
COMPLETENESS_LOW = 0.40

# Model File Paths (Fraud V1 & Win Model)
FRAUD_MODEL_PATH = MODELS_DIR / "fraud_model.pkl"
FRAUD_PIPELINE_PATH = MODELS_DIR / "fraud_pipeline.joblib"

# Model File Paths (Fraud V2 - Public Dataset)
FRAUD_V2_DATASET_PATH = EXTERNAL_DATA_DIR / "fraud_dataset.csv"
FRAUD_V2_PIPELINE_PATH = MODELS_DIR / "fraud_v2_pipeline.joblib"

WIN_MODEL_PATH = MODELS_DIR / "win_probability_model.pkl"
WIN_PIPELINE_PATH = MODELS_DIR / "win_pipeline.joblib"

# LLM & AI Language Layer Configuration (DeepSeek & Ollama)
import os

# Auto-load .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT_SECONDS = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "15"))
AI_CACHE_TTL_SECONDS = int(os.getenv("AI_CACHE_TTL_SECONDS", "3600"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")

# Guardrail Merchant Recommendation Constants
MERCHANT_RECOMMENDATION_CONTEST = "Challenge this dispute"
MERCHANT_RECOMMENDATION_ACCEPT = "Accept this dispute"
MERCHANT_RECOMMENDATION_REVIEW = "Review further"


# Feature Names for Fraud Model V1 (Synthetic Dispute-Centric)
FRAUD_FEATURE_NAMES = [
    "transaction_amount",
    "customer_avg_amount",
    "amount_deviation_ratio",
    "dispute_amount",
    "customer_dispute_count",
    "merchant_dispute_rate",
    "days_since_payment",
    "dispute_velocity_24h",
    "dispute_velocity_7d",
    "is_duplicate_flag",
    "transaction_hour",
    "transaction_day_of_week",
    "reason_code_encoded",
    "merchant_high_risk_flag",
    "customer_account_age_days",
    "ip_billing_mismatch"
]

# Feature Names for Fraud Model V2 (Public Transaction-Level Dataset)
FRAUD_V2_NUMERIC_FEATURES = [
    "transaction_hour",
    "account_age_days",
    "previous_chargebacks",
    "transaction_amount",
    "transaction_velocity_1h",
    "transaction_velocity_24h",
    "avg_transaction_amount_30d"
]

FRAUD_V2_CATEGORICAL_FEATURES = [
    "merchant_category",
    "transaction_country",
    "device_type"
]

FRAUD_V2_BINARY_FEATURES = [
    "is_international",
    "is_high_risk_merchant"
]

FRAUD_V2_ALL_FEATURES = FRAUD_V2_NUMERIC_FEATURES + FRAUD_V2_CATEGORICAL_FEATURES + FRAUD_V2_BINARY_FEATURES

# Feature Names for Win Probability Model
WIN_FEATURE_NAMES = [
    "reason_code_encoded",
    "evidence_completeness_score",
    "has_invoice",
    "has_shipping_proof",
    "has_proof_of_delivery",
    "has_customer_communication",
    "contradiction_count",
    "contradiction_max_severity",
    "fraud_probability",
    "merchant_historical_win_rate",
    "previous_disputes_won_count",
    "dispute_amount",
    "evidence_quality_score"
]

# Official Razorpay Dispute Statuses & Phases (Verified against official Razorpay Developer Docs)
class RazorpayDisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    WON = "won"
    LOST = "lost"
    CLOSED = "closed"

class RazorpayDisputePhase(str, Enum):
    RETRIEVAL = "retrieval"
    CHARGEBACK = "chargeback"
    PRE_ARBITRATION = "pre_arbitration"
    ARBITRATION = "arbitration"
    FRAUD = "fraud"

# Internal Application Urgency Thresholds (Distinct from official bank response deadlines)
class ApplicationUrgencyLevel(str, Enum):
    SAFE = "SAFE"                 # > 72 hours remaining
    APPROACHING = "APPROACHING"   # <= 72 hours and > 24 hours remaining
    URGENT = "URGENT"             # <= 24 hours remaining
    OVERDUE = "OVERDUE"           # <= 0 hours remaining
    RESPONDED = "RESPONDED"       # Case submitted or resolved

# Internal AI & Evidence Lifecycle Workflow Stages (Distinct from official bank status)
class InternalWorkflowStage(str, Enum):
    DISPUTE_RAISED = "DISPUTE_RAISED"
    MERCHANT_NOTIFIED = "MERCHANT_NOTIFIED"
    CASE_OPENED = "CASE_OPENED"
    AI_ANALYSIS = "AI_ANALYSIS"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    EVIDENCE_ANALYSIS = "EVIDENCE_ANALYSIS"
    WIN_PROBABILITY = "WIN_PROBABILITY"
    AI_RECOMMENDATION = "AI_RECOMMENDATION"
    MERCHANT_REVIEW = "MERCHANT_REVIEW"
    AI_RESPONSE_GENERATED = "AI_RESPONSE_GENERATED"
    EVIDENCE_BUNDLE_CREATED = "EVIDENCE_BUNDLE_CREATED"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    RESOLVED = "RESOLVED"

# Valid workflow stage transitions (allows forward progress and rework/re-analysis)
ALLOWED_WORKFLOW_TRANSITIONS = {
    InternalWorkflowStage.DISPUTE_RAISED: [InternalWorkflowStage.MERCHANT_NOTIFIED, InternalWorkflowStage.CASE_OPENED, InternalWorkflowStage.AI_ANALYSIS],
    InternalWorkflowStage.MERCHANT_NOTIFIED: [InternalWorkflowStage.CASE_OPENED, InternalWorkflowStage.AI_ANALYSIS],
    InternalWorkflowStage.CASE_OPENED: [InternalWorkflowStage.AI_ANALYSIS, InternalWorkflowStage.RISK_ASSESSMENT],
    InternalWorkflowStage.AI_ANALYSIS: [InternalWorkflowStage.RISK_ASSESSMENT, InternalWorkflowStage.EVIDENCE_REQUIRED, InternalWorkflowStage.EVIDENCE_COLLECTION],
    InternalWorkflowStage.RISK_ASSESSMENT: [InternalWorkflowStage.EVIDENCE_REQUIRED, InternalWorkflowStage.EVIDENCE_COLLECTION],
    InternalWorkflowStage.EVIDENCE_REQUIRED: [InternalWorkflowStage.EVIDENCE_COLLECTION, InternalWorkflowStage.EVIDENCE_ANALYSIS],
    InternalWorkflowStage.EVIDENCE_COLLECTION: [InternalWorkflowStage.EVIDENCE_ANALYSIS, InternalWorkflowStage.MERCHANT_REVIEW],
    InternalWorkflowStage.EVIDENCE_ANALYSIS: [InternalWorkflowStage.EVIDENCE_COLLECTION, InternalWorkflowStage.WIN_PROBABILITY, InternalWorkflowStage.AI_RECOMMENDATION, InternalWorkflowStage.MERCHANT_REVIEW],
    InternalWorkflowStage.WIN_PROBABILITY: [InternalWorkflowStage.AI_RECOMMENDATION, InternalWorkflowStage.MERCHANT_REVIEW],
    InternalWorkflowStage.AI_RECOMMENDATION: [InternalWorkflowStage.MERCHANT_REVIEW, InternalWorkflowStage.AI_RESPONSE_GENERATED],
    InternalWorkflowStage.MERCHANT_REVIEW: [InternalWorkflowStage.EVIDENCE_COLLECTION, InternalWorkflowStage.AI_RESPONSE_GENERATED, InternalWorkflowStage.EVIDENCE_BUNDLE_CREATED, InternalWorkflowStage.READY_FOR_SUBMISSION],
    InternalWorkflowStage.AI_RESPONSE_GENERATED: [InternalWorkflowStage.MERCHANT_REVIEW, InternalWorkflowStage.EVIDENCE_BUNDLE_CREATED, InternalWorkflowStage.READY_FOR_SUBMISSION],
    InternalWorkflowStage.EVIDENCE_BUNDLE_CREATED: [InternalWorkflowStage.MERCHANT_REVIEW, InternalWorkflowStage.READY_FOR_SUBMISSION, InternalWorkflowStage.SUBMITTED],
    InternalWorkflowStage.READY_FOR_SUBMISSION: [InternalWorkflowStage.MERCHANT_REVIEW, InternalWorkflowStage.SUBMITTED],
    InternalWorkflowStage.SUBMITTED: [InternalWorkflowStage.RESOLVED],
    InternalWorkflowStage.RESOLVED: []
}

# Configurable Response Deadline Windows (in calendar days per dispute phase)
# Primary source: Official Razorpay Dispute Representment Rules
RAZORPAY_DISPUTE_DEADLINE_DAYS = {
    RazorpayDisputePhase.RETRIEVAL: 5,
    RazorpayDisputePhase.CHARGEBACK: 7,
    RazorpayDisputePhase.PRE_ARBITRATION: 5,
    RazorpayDisputePhase.ARBITRATION: 7,
    RazorpayDisputePhase.FRAUD: 3
}


def format_pct(val: float) -> int:
    """Consistently rounds float probability (0.0 to 1.0) to integer percentage (0 to 100)."""
    return int(round(float(val) * 100))


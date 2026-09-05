"""
SQLAlchemy ORM Data Models for Razorpay AI Risk Manager.
Defines schema for Customers, Transactions, Payments, Orders, Fulfillments, Disputes, Evidence, and Risk Assessments.
"""

from datetime import datetime, timezone
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from src.database.database import Base

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True, index=True)
    account_age_days = Column(Integer, default=180)
    verification_status = Column(String, default="VERIFIED")
    country = Column(String, default="US")
    previous_chargebacks = Column(Integer, default=0)
    avg_transaction_amount_30d = Column(Float, default=100.0)
    created_at = Column(String, default=utc_now_iso)

    # Relationships
    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    disputes = relationship("Dispute", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    merchant_id = Column(String, default="MERCHANT_001")
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    timestamp = Column(String, default=utc_now_iso)
    payment_method = Column(String, default="credit_card")
    merchant_category = Column(String, default="retail")
    transaction_country = Column(String, default="US")
    transaction_status = Column(String, default="SUCCESS")

    # Required ML Model V2 parameters
    transaction_hour = Column(Integer, default=12)
    account_age_days = Column(Integer, default=180)
    previous_chargebacks = Column(Integer, default=0)
    device_type = Column(String, default="mobile")
    is_international = Column(Integer, default=0)
    is_high_risk_merchant = Column(Integer, default=0)
    transaction_velocity_1h = Column(Integer, default=0)
    transaction_velocity_24h = Column(Integer, default=0)
    avg_transaction_amount_30d = Column(Float, default=100.0)

    # Relationships
    customer = relationship("Customer", back_populates="transactions")
    payments = relationship("Payment", back_populates="transaction", cascade="all, delete-orphan")
    order = relationship("Order", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    disputes = relationship("Dispute", back_populates="transaction", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="transaction", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="transaction", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    payment_method = Column(String, default="credit_card")
    card_network = Column(String, default="visa")
    last4 = Column(String, default="4242")
    avs_match = Column(String, default="Y")
    cvv_match = Column(String, default="Y")
    auth_code = Column(String, default="AUTH123456")
    payment_status = Column(String, default="CAPTURED")
    created_at = Column(String, default=utc_now_iso)

    # Relationships
    transaction = relationship("Transaction", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False, unique=True, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    product_description = Column(String, default="Digital Electronics / Goods")
    order_amount = Column(Float, nullable=False)
    order_status = Column(String, default="COMPLETED")
    created_at = Column(String, default=utc_now_iso)

    # Relationships
    transaction = relationship("Transaction", back_populates="order")
    customer = relationship("Customer", back_populates="orders")
    fulfillment = relationship("Fulfillment", back_populates="order", uselist=False, cascade="all, delete-orphan")

class Fulfillment(Base):
    __tablename__ = "fulfillments"

    fulfillment_id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False, unique=True, index=True)
    shipping_status = Column(String, default="SHIPPED")
    tracking_number = Column(String, nullable=True, default=None)
    shipped_at = Column(String, nullable=True)
    delivered_at = Column(String, nullable=True)
    delivery_status = Column(String, nullable=True, default=None)

    # Relationships
    order = relationship("Order", back_populates="fulfillment")

class Dispute(Base):
    __tablename__ = "disputes"

    dispute_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False, index=True)
    reason_code = Column(String, nullable=False, index=True)
    reason_description = Column(String, default="")
    status = Column(String, default="OPEN", index=True) # Bank/Razorpay status (OPEN, UNDER_REVIEW, WON, LOST, CLOSED)
    phase = Column(String, default="chargeback", index=True) # Razorpay dispute phase (retrieval, chargeback, pre_arbitration, arbitration, fraud)
    respond_by = Column(String, nullable=True, index=True) # UTC ISO timestamp deadline calculated by backend
    workflow_stage = Column(String, default="DISPUTE_RAISED", index=True) # Internal AI lifecycle stage
    case_source = Column(String, default="SIMULATED_RAZORPAY", index=True) # DEMO, SIMULATED_RAZORPAY, REAL_RAZORPAY
    merchant_attention_state = Column(String, default="ACTION_REQUIRED", index=True) # ACTION_REQUIRED, REVIEW_RECOMMENDED, AI_HANDLING, WAITING
    ai_last_checked = Column(String, default=utc_now_iso) # ISO timestamp when AI Autopilot last processed
    created_at = Column(String, default=utc_now_iso, index=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="disputes")
    customer = relationship("Customer", back_populates="disputes")
    evidence_records = relationship("Evidence", back_populates="dispute", cascade="all, delete-orphan")
    events = relationship("DisputeEvent", back_populates="dispute", cascade="all, delete-orphan")
    assessments = relationship("DisputeAssessment", back_populates="dispute", cascade="all, delete-orphan")

class DisputeEvent(Base):
    __tablename__ = "dispute_events"

    event_id = Column(String, primary_key=True, index=True)
    dispute_id = Column(String, ForeignKey("disputes.dispute_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    timestamp = Column(String, default=utc_now_iso, index=True)
    actor_type = Column(String, default="SYSTEM") # SYSTEM, AI_ENGINE, MERCHANT, LOCAL_GATEWAY
    previous_stage = Column(String, nullable=True)
    new_stage = Column(String, nullable=True)
    metadata_json = Column(Text, default="{}")

    # Relationships
    dispute = relationship("Dispute", back_populates="events")

    @property
    def event_metadata(self) -> dict:
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}

    @event_metadata.setter
    def event_metadata(self, val: dict):
        self.metadata_json = json.dumps(val if val is not None else {})


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(String, primary_key=True, index=True)
    dispute_id = Column(String, ForeignKey("disputes.dispute_id"), nullable=False, index=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    evidence_type = Column(String, nullable=False, index=True)
    title = Column(String, default="")
    description = Column(String, default="")
    source = Column(String, default="DATABASE")
    source_reference_id = Column(String, nullable=True, default=None)
    file_path = Column(String, nullable=True, default=None)
    mime_type = Column(String, nullable=True, default=None)
    file_size = Column(Integer, default=0)
    document_hash = Column(String, nullable=True, default=None, index=True)
    content_hash = Column(String, nullable=True, default=None, index=True)
    raw_content = Column(Text, nullable=True, default=None)
    extracted_text = Column(Text, nullable=True, default=None)
    content_json = Column(Text, default="{}")
    key_entities_json = Column(Text, default="{}")
    evidence_data_json = Column(Text, default="{}")
    verification_status = Column(String, default="UNVERIFIED", index=True) # UNVERIFIED, VERIFIED, INVALID, UNREADABLE, REJECTED, NEEDS_REVIEW, FAILED
    verification_confidence = Column(Float, default=1.0)
    verification_errors_json = Column(Text, default="[]")
    approval_status = Column(String, default="PENDING_APPROVAL", index=True) # PENDING_APPROVAL, APPROVED, REJECTED
    approved_at = Column(String, nullable=True)
    approved_by = Column(String, nullable=True) # MERCHANT, SYSTEM
    
    # AI Evidence Analysis Integration
    ai_analysis_json = Column(Text, default="{}")
    ai_analysis_status = Column(String, default="PENDING", index=True) # PENDING, ANALYZING, VERIFIED, REJECTED, NEEDS_REVIEW, FAILED
    ai_analyzed_at = Column(String, nullable=True)
    ai_error = Column(Text, nullable=True)

    created_at = Column(String, default=utc_now_iso, index=True)
    updated_at = Column(String, default=utc_now_iso)
    is_deleted = Column(Integer, default=0, index=True)

    # Relationships
    dispute = relationship("Dispute", back_populates="evidence_records")
    transaction = relationship("Transaction", back_populates="evidence_records")

    @property
    def ai_analysis(self) -> dict:
        try:
            return json.loads(self.ai_analysis_json or "{}")
        except Exception:
            return {}

    @ai_analysis.setter
    def ai_analysis(self, val: dict):
        self.ai_analysis_json = json.dumps(val if val is not None else {})

    @property
    def evidence_data(self) -> dict:
        try:
            if self.evidence_data_json and self.evidence_data_json != "{}":
                return json.loads(self.evidence_data_json)
            if self.content_json and self.content_json != "{}":
                return json.loads(self.content_json)
            return {}
        except Exception:
            return {}

    @evidence_data.setter
    def evidence_data(self, val: dict):
        dumped = json.dumps(val if val is not None else {})
        self.evidence_data_json = dumped
        self.content_json = dumped

    @property
    def content(self) -> dict:
        return self.evidence_data

    @content.setter
    def content(self, val: dict):
        self.evidence_data = val

    @property
    def key_entities(self) -> dict:
        try:
            return json.loads(self.key_entities_json or "{}")
        except Exception:
            return {}

    @key_entities.setter
    def key_entities(self, val: dict):
        self.key_entities_json = json.dumps(val if val is not None else {})

    @property
    def verification_errors(self) -> list:
        try:
            return json.loads(self.verification_errors_json or "[]")
        except Exception:
            return []

    @verification_errors.setter
    def verification_errors(self, val: list):
        self.verification_errors_json = json.dumps(val if val is not None else [])

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    model_version = Column(String, default="fraud-model-v2")
    created_at = Column(String, default=utc_now_iso)

    # Relationships
    transaction = relationship("Transaction", back_populates="risk_assessments")

class ChargebackPackage(Base):
    __tablename__ = "chargeback_packages"

    package_id = Column(String, primary_key=True, index=True)
    dispute_id = Column(String, ForeignKey("disputes.dispute_id"), nullable=False, index=True)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    package_status = Column(String, nullable=False, default="READY_FOR_REVIEW")
    merchant_position = Column(String, nullable=False, default="CONTEST")
    response_text = Column(Text, default="")
    package_data_json = Column(Text, default="{}")
    generator_version = Column(String, default="1.0")
    created_at = Column(String, default=utc_now_iso)

    @property
    def package_data(self) -> dict:
        try:
            return json.loads(self.package_data_json or "{}")
        except Exception:
            return {}

    @package_data.setter
    def package_data(self, val: dict):
        self.package_data_json = json.dumps(val if val is not None else {})


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id = Column(String, primary_key=True, index=True)
    idempotency_key = Column(String, index=True, nullable=True)
    event_type = Column(String, nullable=False, default="payment.dispute.created")
    payload_json = Column(Text, default="{}")
    status = Column(String, default="RECEIVED")  # RECEIVED, PROCESSED, FAILED, DUPLICATE
    dispute_id = Column(String, nullable=True, index=True)
    created_at = Column(String, default=utc_now_iso)
    processed_at = Column(String, nullable=True)

    @property
    def payload(self) -> dict:
        try:
            return json.loads(self.payload_json or "{}")
        except Exception:
            return {}

    @payload.setter
    def payload(self, val: dict):
        self.payload_json = json.dumps(val if val is not None else {})


class DisputeAssessment(Base):
    __tablename__ = "dispute_assessments"

    assessment_id = Column(String, primary_key=True, index=True)
    dispute_id = Column(String, ForeignKey("disputes.dispute_id"), nullable=False, index=True)
    analysis_version = Column(Integer, default=1)
    trigger = Column(String, default="DISPUTE_CREATED")
    risk_score = Column(Float, default=0.0)
    fraud_probability = Column(Float, default=0.0)
    win_probability = Column(Float, default=0.5)
    confidence = Column(Float, default=0.5)
    confidence_level = Column(String, default="MEDIUM")
    ml_recommendation = Column(String, default="REVIEW")
    ai_recommendation = Column(String, default="REVIEW")
    conflict_detected = Column(Integer, default=0)
    ml_results_json = Column(Text, default="{}")
    deepseek_results_json = Column(Text, default="{}")
    evidence_analysis_json = Column(Text, default="{}")
    model_versions_json = Column(Text, default="{}")
    generated_at = Column(String, default=utc_now_iso)

    # Relationships
    dispute = relationship("Dispute", back_populates="assessments")

    @property
    def ml_results(self) -> dict:
        try:
            return json.loads(self.ml_results_json or "{}")
        except Exception:
            return {}

    @ml_results.setter
    def ml_results(self, val: dict):
        self.ml_results_json = json.dumps(val if val is not None else {})

    @property
    def deepseek_results(self) -> dict:
        try:
            return json.loads(self.deepseek_results_json or "{}")
        except Exception:
            return {}

    @deepseek_results.setter
    def deepseek_results(self, val: dict):
        self.deepseek_results_json = json.dumps(val if val is not None else {})

    @property
    def evidence_analysis(self) -> dict:
        try:
            return json.loads(self.evidence_analysis_json or "{}")
        except Exception:
            return {}

    @evidence_analysis.setter
    def evidence_analysis(self, val: dict):
        self.evidence_analysis_json = json.dumps(val if val is not None else {})

    @property
    def model_versions(self) -> dict:
        try:
            return json.loads(self.model_versions_json or "{}")
        except Exception:
            return {}

    @model_versions.setter
    def model_versions(self, val: dict):
        self.model_versions_json = json.dumps(val if val is not None else {})


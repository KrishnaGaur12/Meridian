"""
Database Repositories for Razorpay AI Risk Manager.
Encapsulates CRUD operations for SQLAlchemy models.
"""

from typing import Optional, List, Dict, Any
import uuid
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session, joinedload
from config.settings import (
    RAZORPAY_DISPUTE_DEADLINE_DAYS, RazorpayDisputePhase, InternalWorkflowStage, ApplicationUrgencyLevel, ALLOWED_WORKFLOW_TRANSITIONS
)

from src.database.models import (
    Customer, Transaction, Payment, Order, Fulfillment, Dispute, DisputeEvent, Evidence, RiskAssessment, ChargebackPackage, utc_now_iso
)
from src.utils.id_generator import (
    generate_dispute_id, generate_evidence_id, generate_reference_id,
    generate_event_id, generate_package_id, generate_transaction_id,
    generate_customer_id, generate_payment_id, generate_order_id, generate_fulfillment_id
)




# --- CUSTOMER ---
def get_customer(db: Session, customer_id: str) -> Optional[Customer]:
    return db.query(Customer).filter(Customer.customer_id == customer_id).first()

def create_customer(db: Session, data: Dict[str, Any]) -> Customer:
    cid = data.get("customer_id") or f"CUST_{uuid.uuid4().hex[:8].upper()}"
    customer = Customer(
        customer_id=cid,
        account_age_days=data.get("account_age_days", 180),
        verification_status=data.get("verification_status", "VERIFIED"),
        country=data.get("country", "US"),
        previous_chargebacks=data.get("previous_chargebacks", 0),
        avg_transaction_amount_30d=data.get("avg_transaction_amount_30d", 100.0)
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

def get_or_create_customer(db: Session, data: Dict[str, Any]) -> Customer:
    cid = data.get("customer_id")
    if cid:
        cust = get_customer(db, cid)
        if cust:
            return cust
    return create_customer(db, data)

# --- TRANSACTION ---
def get_transaction(db: Session, transaction_id: str) -> Optional[Transaction]:
    return db.query(Transaction).options(
        joinedload(Transaction.customer),
        joinedload(Transaction.payments),
        joinedload(Transaction.order).joinedload(Order.fulfillment),
        joinedload(Transaction.disputes),
        joinedload(Transaction.risk_assessments),
        joinedload(Transaction.evidence_records)
    ).filter(Transaction.transaction_id == transaction_id).first()

def get_all_transactions(db: Session) -> List[Transaction]:
    return db.query(Transaction).options(
        joinedload(Transaction.customer),
        joinedload(Transaction.payments),
        joinedload(Transaction.order).joinedload(Order.fulfillment)
    ).order_by(Transaction.timestamp.desc()).all()

def get_eligible_transactions(db: Session) -> List[Transaction]:
    """
    Retrieves transactions that are eligible for dispute simulation:
    - transaction_status is 'SUCCESS' or 'CAPTURED'
    - no active dispute exists on this transaction
    """
    all_txs = get_all_transactions(db)
    active_disputes = db.query(Dispute).filter(
        Dispute.status.notin_(["WON", "LOST", "CLOSED"])
    ).all()
    disputed_tx_ids = {d.transaction_id for d in active_disputes}

    return [
        tx for tx in all_txs
        if (tx.transaction_status or "").upper() in ["SUCCESS", "CAPTURED"]
        and tx.transaction_id not in disputed_tx_ids
    ]

def create_transaction(db: Session, data: Dict[str, Any]) -> Transaction:
    # Ensure customer exists
    cust_id = data.get("customer_id") or "CUST_DEFAULT"
    cust = get_customer(db, cust_id)
    if not cust:
        cust = create_customer(db, {
            "customer_id": cust_id,
            "account_age_days": data.get("account_age_days", 180),
            "country": data.get("transaction_country", "US"),
            "previous_chargebacks": data.get("previous_chargebacks", 0),
            "avg_transaction_amount_30d": data.get("avg_transaction_amount_30d", 100.0)
        })

    tx_id = data.get("transaction_id") or f"TXN_{uuid.uuid4().hex[:8].upper()}"
    existing_tx = get_transaction(db, tx_id)
    if existing_tx:
        return existing_tx

    tx = Transaction(
        transaction_id=tx_id,
        customer_id=cust.customer_id,
        merchant_id=data.get("merchant_id", "MERCHANT_001"),
        amount=float(data.get("amount", data.get("transaction_amount", 100.0))),
        currency=data.get("currency", "USD"),
        timestamp=data.get("timestamp", data.get("transaction_timestamp", utc_now_iso())),
        payment_method=data.get("payment_method", "credit_card"),
        merchant_category=data.get("merchant_category", "retail"),
        transaction_country=data.get("transaction_country", "US"),
        transaction_status=data.get("transaction_status", "SUCCESS"),
        
        # 12 ML Model parameters
        transaction_hour=int(data.get("transaction_hour", 12)),
        account_age_days=int(data.get("account_age_days", cust.account_age_days)),
        previous_chargebacks=int(data.get("previous_chargebacks", cust.previous_chargebacks)),
        device_type=str(data.get("device_type", "mobile")),
        is_international=int(data.get("is_international", 0)),
        is_high_risk_merchant=int(data.get("is_high_risk_merchant", 0)),
        transaction_velocity_1h=int(data.get("transaction_velocity_1h", 0)),
        transaction_velocity_24h=int(data.get("transaction_velocity_24h", 0)),
        avg_transaction_amount_30d=float(data.get("avg_transaction_amount_30d", cust.avg_transaction_amount_30d))
    )
    db.add(tx)
    db.commit()

    # Create associated payment if payment details provided or default
    pay_info = data.get("payment") or {}
    if pay_info or "payment_method" in data or data.get("payment") is None:
        create_payment(db, {
            "payment_id": pay_info.get("payment_id") or f"PAY_{uuid.uuid4().hex[:8].upper()}",
            "transaction_id": tx.transaction_id,
            "customer_id": cust.customer_id,
            "payment_method": pay_info.get("payment_method", tx.payment_method),
            "card_network": pay_info.get("card_network", "visa"),
            "last4": pay_info.get("last4", "4242"),
            "avs_match": pay_info.get("avs_match", "Y"),
            "cvv_match": pay_info.get("cvv_match", "Y"),
            "auth_code": pay_info.get("auth_code", "AUTH123456"),
            "payment_status": pay_info.get("payment_status", "CAPTURED")
        })

    # Create order & fulfillment if order info provided
    order_info = data.get("order") or {}
    if order_info or "product_description" in data:
        ord_id = order_info.get("order_id") or f"ORD_{uuid.uuid4().hex[:8].upper()}"
        order = create_order(db, {
            "order_id": ord_id,
            "transaction_id": tx.transaction_id,
            "customer_id": cust.customer_id,
            "product_description": order_info.get("product_description", data.get("product_description", "Digital Goods / Software License")),
            "order_amount": float(order_info.get("order_amount", tx.amount)),
            "order_status": order_info.get("order_status", "COMPLETED")
        })

        ful_info = order_info.get("fulfillment") or data.get("fulfillment") or {}
        if ful_info or "shipping_status" in order_info:
            create_fulfillment(db, {
                "fulfillment_id": ful_info.get("fulfillment_id") or f"FUL_{uuid.uuid4().hex[:8].upper()}",
                "order_id": order.order_id,
                "shipping_status": ful_info.get("shipping_status", "SHIPPED"),
                "tracking_number": ful_info.get("tracking_number"),
                "shipped_at": ful_info.get("shipped_at"),
                "delivered_at": ful_info.get("delivered_at"),
                "delivery_status": ful_info.get("delivery_status")
            })

    db.refresh(tx)
    return tx

# --- PAYMENT ---
def create_payment(db: Session, data: Dict[str, Any]) -> Payment:
    pid = data.get("payment_id") or f"PAY_{uuid.uuid4().hex[:8].upper()}"
    payment = Payment(
        payment_id=pid,
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        payment_method=data.get("payment_method", "credit_card"),
        card_network=data.get("card_network", "visa"),
        last4=data.get("last4", "4242"),
        avs_match=data.get("avs_match", "Y"),
        cvv_match=data.get("cvv_match", "Y"),
        auth_code=data.get("auth_code", "AUTH123456"),
        payment_status=data.get("payment_status", "CAPTURED")
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

def get_payments_for_transaction(db: Session, transaction_id: str) -> List[Payment]:
    return db.query(Payment).filter(Payment.transaction_id == transaction_id).all()

def create_order(db: Session, data: Dict[str, Any]) -> Order:
    existing = db.query(Order).filter(
        (Order.order_id == data.get("order_id")) | (Order.transaction_id == data.get("transaction_id"))
    ).first()
    if existing:
        existing.product_description = data.get("product_description", existing.product_description)
        existing.order_amount = float(data.get("order_amount", existing.order_amount))
        existing.order_status = data.get("order_status", existing.order_status)
        db.commit()
        db.refresh(existing)
        return existing

    oid = data.get("order_id") or f"ORD_{uuid.uuid4().hex[:8].upper()}"
    order = Order(
        order_id=oid,
        transaction_id=data["transaction_id"],
        customer_id=data["customer_id"],
        product_description=data.get("product_description", "Digital Goods"),
        order_amount=float(data.get("order_amount", 100.0)),
        order_status=data.get("order_status", "COMPLETED")
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def create_fulfillment(db: Session, data: Dict[str, Any]) -> Fulfillment:
    existing = db.query(Fulfillment).filter(
        (Fulfillment.fulfillment_id == data.get("fulfillment_id")) | (Fulfillment.order_id == data.get("order_id"))
    ).first()
    if existing:
        existing.shipping_status = data.get("shipping_status", existing.shipping_status)
        existing.tracking_number = data.get("tracking_number", existing.tracking_number)
        existing.shipped_at = data.get("shipped_at", existing.shipped_at)
        existing.delivered_at = data.get("delivered_at", existing.delivered_at)
        existing.delivery_status = data.get("delivery_status", existing.delivery_status)
        db.commit()
        db.refresh(existing)
        return existing

    fid = data.get("fulfillment_id") or f"FUL_{uuid.uuid4().hex[:8].upper()}"
    fulfillment = Fulfillment(
        fulfillment_id=fid,
        order_id=data["order_id"],
        shipping_status=data.get("shipping_status", "SHIPPED"),
        tracking_number=data.get("tracking_number"),
        shipped_at=data.get("shipped_at"),
        delivered_at=data.get("delivered_at"),
        delivery_status=data.get("delivery_status")
    )
    db.add(fulfillment)
    db.commit()
    db.refresh(fulfillment)
    return fulfillment

# --- DISPUTE & DEADLINE ENGINE ---
def calculate_dispute_deadline(created_at_iso: str, phase: str = "chargeback") -> str:
    """Calculates UTC ISO respond_by deadline based on phase and Razorpay representment rules."""
    try:
        dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    days = RAZORPAY_DISPUTE_DEADLINE_DAYS.get(phase, 7)
    deadline_dt = dt + timedelta(days=days)
    return deadline_dt.isoformat()

def calculate_deadline_info(respond_by_iso: Optional[str], status: str = "OPEN", workflow_stage: str = "DISPUTE_RAISED") -> Dict[str, Any]:
    """Calculates remaining hours, human-readable time, overdue flag, and deterministic urgency_level."""
    if (status and status.upper() in ["WON", "LOST", "CLOSED"]) or (workflow_stage and workflow_stage.upper() in ["SUBMITTED", "RESOLVED"]):
        return {
            "respond_by": respond_by_iso,
            "remaining_hours": 0.0,
            "remaining_time_human": "Case Responded",
            "is_overdue": False,
            "deadline_status": "RESPONDED",
            "urgency_level": "RESPONDED"
        }

    if not respond_by_iso:
        return {
            "respond_by": None,
            "remaining_hours": None,
            "remaining_time_human": "No Deadline Specified",
            "is_overdue": False,
            "deadline_status": "ON_TRACK",
            "urgency_level": "SAFE"
        }

    try:
        now = datetime.now(timezone.utc)
        deadline = datetime.fromisoformat(respond_by_iso.replace("Z", "+00:00"))
        delta = deadline - now
        total_seconds = delta.total_seconds()
        remaining_hours = round(total_seconds / 3600.0, 1)

        if total_seconds <= 0:
            return {
                "respond_by": respond_by_iso,
                "remaining_hours": 0.0,
                "remaining_time_human": "OVERDUE",
                "is_overdue": True,
                "deadline_status": "OVERDUE",
                "urgency_level": "OVERDUE"
            }

        days = int(delta.days)
        hours = int((total_seconds % 86400) // 3600)
        
        if days > 0:
            human_str = f"{days}d {hours}h remaining"
        else:
            human_str = f"{hours}h remaining"

        if remaining_hours <= 24.0:
            urgency_level = "URGENT"
            deadline_status = "APPROACHING"
        elif remaining_hours <= 72.0:
            urgency_level = "APPROACHING"
            deadline_status = "APPROACHING"
        else:
            urgency_level = "SAFE"
            deadline_status = "ON_TRACK"

        return {
            "respond_by": respond_by_iso,
            "remaining_hours": remaining_hours,
            "remaining_time_human": human_str,
            "is_overdue": False,
            "deadline_status": deadline_status,
            "urgency_level": urgency_level
        }
    except Exception:
        return {
            "respond_by": respond_by_iso,
            "remaining_hours": None,
            "remaining_time_human": "Invalid Deadline Format",
            "is_overdue": False,
            "deadline_status": "ON_TRACK",
            "urgency_level": "SAFE"
        }


def create_dispute_event(
    db: Session,
    dispute_id: str,
    event_type: str,
    title: str,
    description: str = "",
    timestamp: Optional[str] = None,
    actor_type: str = "SYSTEM",
    previous_stage: Optional[str] = None,
    new_stage: Optional[str] = None,
    metadata: Optional[dict] = None
) -> DisputeEvent:
    """Logs a real dispute timeline/audit event that actually occurred."""
    ev_id = generate_event_id()
    evt = DisputeEvent(
        event_id=ev_id,
        dispute_id=dispute_id,
        event_type=event_type,
        title=title,
        description=description,
        timestamp=timestamp or utc_now_iso(),
        actor_type=actor_type,
        previous_stage=previous_stage,
        new_stage=new_stage
    )
    if metadata:
        evt.event_metadata = metadata
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt

def get_dispute_timeline(db: Session, dispute_id: str) -> List[DisputeEvent]:
    """Retrieves chronological timeline logs for a dispute."""
    return db.query(DisputeEvent).filter(
        DisputeEvent.dispute_id == dispute_id
    ).order_by(DisputeEvent.timestamp.asc()).all()

def get_dispute_audit_trail(db: Session, dispute_id: str) -> List[Dict[str, Any]]:
    """Retrieves formatted chronological audit trail logs for a dispute."""
    events = get_dispute_timeline(db, dispute_id)
    audit_logs = []
    for evt in events:
        audit_logs.append({
            "event_id": evt.event_id,
            "dispute_id": evt.dispute_id,
            "event_type": evt.event_type,
            "title": evt.title,
            "description": evt.description,
            "timestamp": evt.timestamp,
            "actor_type": evt.actor_type or "SYSTEM",
            "previous_stage": evt.previous_stage,
            "new_stage": evt.new_stage,
            "metadata": evt.event_metadata
        })
    return audit_logs


def get_dispute(db: Session, dispute_id: str) -> Optional[Dispute]:
    return db.query(Dispute).options(
        joinedload(Dispute.transaction).joinedload(Transaction.customer),
        joinedload(Dispute.transaction).joinedload(Transaction.payments),
        joinedload(Dispute.transaction).joinedload(Transaction.order).joinedload(Order.fulfillment),
        joinedload(Dispute.evidence_records),
        joinedload(Dispute.events)
    ).filter(Dispute.dispute_id == dispute_id).first()

def get_all_disputes(
    db: Session,
    case_source: Optional[str] = None,
    status: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    merchant_attention_state: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dispute]:
    """
    Retrieves dispute records efficiently with lightweight transaction loading.
    Decoupled from heavy evidence records to ensure instant list rendering.
    Supports filtering and pagination.
    """
    query = db.query(Dispute).options(
        joinedload(Dispute.transaction)
    )

    if case_source:
        query = query.filter(Dispute.case_source == case_source)
    if status:
        query = query.filter(Dispute.status == status)
    if workflow_stage:
        query = query.filter(Dispute.workflow_stage == workflow_stage)
    if merchant_attention_state:
        query = query.filter(Dispute.merchant_attention_state == merchant_attention_state)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Dispute.dispute_id.ilike(s)) |
            (Dispute.transaction_id.ilike(s)) |
            (Dispute.customer_id.ilike(s)) |
            (Dispute.reason_code.ilike(s)) |
            (Dispute.reason_description.ilike(s))
        )

    query = query.order_by(Dispute.created_at.desc())

    if offset is not None and offset > 0:
        query = query.offset(offset)
    if limit is not None and limit > 0:
        query = query.limit(limit)

    return query.all()

def get_disputes_count(
    db: Session,
    case_source: Optional[str] = None,
    status: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    merchant_attention_state: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """Returns total count of disputes matching criteria for pagination."""
    query = db.query(Dispute)
    if case_source:
        query = query.filter(Dispute.case_source == case_source)
    if status:
        query = query.filter(Dispute.status == status)
    if workflow_stage:
        query = query.filter(Dispute.workflow_stage == workflow_stage)
    if merchant_attention_state:
        query = query.filter(Dispute.merchant_attention_state == merchant_attention_state)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Dispute.dispute_id.ilike(s)) |
            (Dispute.transaction_id.ilike(s)) |
            (Dispute.customer_id.ilike(s)) |
            (Dispute.reason_code.ilike(s)) |
            (Dispute.reason_description.ilike(s))
        )
    return query.count()

def create_dispute(db: Session, data: Dict[str, Any], enforce_eligibility: bool = False, auto_process: bool = False) -> Dispute:
    tx = get_transaction(db, data["transaction_id"])
    if not tx:
        raise ValueError(f"Transaction '{data['transaction_id']}' not found in database.")

    # If enforce_eligibility is requested (e.g. in Live mode simulation)
    if enforce_eligibility:
        if (tx.transaction_status or "").upper() not in ["SUCCESS", "CAPTURED"]:
            raise ValueError(f"Transaction '{tx.transaction_id}' is not in SUCCESS/CAPTURED status (current: {tx.transaction_status}).")

        active_disputes = db.query(Dispute).filter(
            Dispute.transaction_id == tx.transaction_id,
            Dispute.status.notin_(["WON", "LOST", "CLOSED"])
        ).all()
        if active_disputes:
            raise ValueError(
                f"Transaction '{tx.transaction_id}' already has an active dispute ({active_disputes[0].dispute_id}). "
                "Duplicate active disputes on the same transaction are prohibited."
            )

    # Validate reason code 'other' requires non-empty description
    reason_code = data.get("reason_code", "fraudulent_transaction")
    reason_desc = (data.get("reason_description") or "").strip()
    if reason_code.lower() == "other" and not reason_desc:
        raise ValueError("reason_description is mandatory when dispute reason code is 'other'.")

    did = data.get("dispute_id") or generate_dispute_id()
    created_at = data.get("created_at") or utc_now_iso()
    phase = data.get("phase", "chargeback")
    respond_by = data.get("respond_by") or calculate_dispute_deadline(created_at, phase)
    workflow_stage = data.get("workflow_stage", "DISPUTE_RAISED")
    case_source = data.get("case_source", "SIMULATED_RAZORPAY")
    attention_state = data.get("merchant_attention_state", "ACTION_REQUIRED")

    dispute = Dispute(
        dispute_id=did,
        transaction_id=tx.transaction_id,
        customer_id=tx.customer_id,
        reason_code=reason_code,
        reason_description=reason_desc or "Cardholder disputes charge",
        status=data.get("status", "OPEN"),
        phase=phase,
        respond_by=respond_by,
        workflow_stage=workflow_stage,
        case_source=case_source,
        merchant_attention_state=attention_state,
        ai_last_checked=created_at,
        created_at=created_at
    )
    db.add(dispute)
    db.commit()

    # Log initial timeline events representing real actions taken
    create_dispute_event(
        db, did, "DISPUTE_RAISED", "Dispute Case Created",
        f"Dispute case {did} filed for transaction {tx.transaction_id} (Source: {case_source}).", created_at
    )
    create_dispute_event(
        db, did, "MERCHANT_NOTIFIED", "Merchant Notified",
        f"Merchant notified. Response required by {respond_by}.", created_at
    )
    create_dispute_event(
        db, did, "AI_ANALYSIS_STARTED", "AI Case Analysis Started",
        "Razorpay AI Risk Manager initiated risk analysis and evidence checklist evaluation.", created_at
    )

    if auto_process:
        # Automatically generate dispute-specific evidence records in DB
        try:
            from src.evidence.evidence_factory import EvidenceFactory
            EvidenceFactory.create_evidence_for_dispute(db, did)
        except Exception as ev_err:
            pass

        # Automatically execute authoritative AI & ML analysis, response, package generation & readiness calculation
        try:
            from src.pipeline.analysis_service import analyze_dispute
            analyze_dispute(did, db, trigger="DISPUTE_CREATED", broadcast=True)
        except Exception as ana_err:
            pass

    db.refresh(dispute)
    return dispute



def get_dispute_case_analysis(db: Session, dispute_id: str) -> Dict[str, Any]:
    """
    Assembles comprehensive AI Case & Evidence Intelligence using real database entities,
    Fraud V2 ML model, Evidence Engine, Win Probability Model, and DeepSeek AI reasoning.
    Delegates to authoritative analyze_dispute service.
    """
    from src.pipeline.analysis_service import analyze_dispute
    return analyze_dispute(dispute_id=dispute_id, db=db, trigger="CASE_ANALYSIS", broadcast=False)




# --- EVIDENCE ---
def create_evidence(db: Session, data: Dict[str, Any]) -> Evidence:
    eid = data.get("evidence_id") or generate_evidence_id()
    evd = Evidence(
        evidence_id=eid,
        dispute_id=data["dispute_id"],
        transaction_id=data["transaction_id"],
        evidence_type=data["evidence_type"],
        title=data.get("title", ""),
        description=data.get("description", ""),
        source=data.get("source", "DATABASE"),
        verification_status=data.get("verification_status", "UNVERIFIED")
    )
    evd.evidence_data = data.get("evidence_data", {})
    db.add(evd)
    db.commit()
    db.refresh(evd)
    return evd

def get_evidence_by_dispute(db: Session, dispute_id: str) -> List[Evidence]:
    return db.query(Evidence).filter(Evidence.dispute_id == dispute_id).all()

def approve_dispute_evidence(db: Session, dispute_id: str, evidence_id: str, approved_by: str = "MERCHANT") -> Dict[str, Any]:
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id
    ).first()
    if not evidence:
        raise ValueError(f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")

    ver_status = (evidence.verification_status or "UNVERIFIED").upper()
    if ver_status in ["INVALID", "UNREADABLE"]:
        raise ValueError(f"Cannot approve evidence with verification status '{ver_status}'. Please replace document.")

    # Elevate status to VERIFIED if was UNVERIFIED or AVAILABLE
    if ver_status in ["UNVERIFIED", "AVAILABLE"]:
        evidence.verification_status = "VERIFIED"

    now = utc_now_iso()
    evidence.approval_status = "APPROVED"
    evidence.approved_at = now
    evidence.approved_by = approved_by

    # Record dispute timeline audit event
    evt = DisputeEvent(
        event_id=generate_event_id(),
        dispute_id=dispute_id,
        event_type="EVIDENCE_APPROVED",
        title="Evidence Approved by Merchant",
        description=f"Merchant approved evidence item '{evidence.title}' ({evidence.evidence_type}).",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage=dispute.workflow_stage,
        metadata_json=json.dumps({
            "evidence_id": evidence_id,
            "evidence_type": evidence.evidence_type,
            "verification_status": evidence.verification_status,
            "approval_status": "APPROVED",
            "approved_at": now,
            "approved_by": approved_by
        })
    )
    db.add(evt)
    db.commit()
    db.refresh(evidence)

    return {
        "evidence_id": evidence.evidence_id,
        "dispute_id": evidence.dispute_id,
        "transaction_id": evidence.transaction_id,
        "evidence_type": evidence.evidence_type,
        "title": evidence.title,
        "description": evidence.description,
        "verification_status": evidence.verification_status,
        "approval_status": evidence.approval_status,
        "approved_at": evidence.approved_at,
        "approved_by": evidence.approved_by,
        "source": evidence.source,
        "data": evidence.evidence_data,
        "created_at": evidence.created_at
    }

def reject_dispute_evidence(db: Session, dispute_id: str, evidence_id: str, reason: str = "") -> Dict[str, Any]:
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id
    ).first()
    if not evidence:
        raise ValueError(f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")

    evidence.approval_status = "REJECTED"
    now = utc_now_iso()

    evt = DisputeEvent(
        event_id=generate_event_id(),
        dispute_id=dispute_id,
        event_type="EVIDENCE_REJECTED",
        title="Evidence Rejected by Merchant",
        description=f"Merchant rejected evidence item '{evidence.title}' ({evidence.evidence_type}). {reason}".strip(),
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage=dispute.workflow_stage,
        metadata_json=json.dumps({
            "evidence_id": evidence_id,
            "evidence_type": evidence.evidence_type,
            "approval_status": "REJECTED",
            "reason": reason
        })
    )
    db.add(evt)
    db.commit()
    db.refresh(evidence)

    return {
        "evidence_id": evidence.evidence_id,
        "dispute_id": evidence.dispute_id,
        "transaction_id": evidence.transaction_id,
        "evidence_type": evidence.evidence_type,
        "title": evidence.title,
        "description": evidence.description,
        "verification_status": evidence.verification_status,
        "approval_status": evidence.approval_status,
        "approved_at": evidence.approved_at,
        "approved_by": evidence.approved_by,
        "source": evidence.source,
        "data": evidence.evidence_data,
        "created_at": evidence.created_at
    }


# --- RISK ASSESSMENT ---
def create_risk_assessment(db: Session, data: Dict[str, Any]) -> RiskAssessment:
    aid = data.get("assessment_id") or f"ASM_{uuid.uuid4().hex[:8].upper()}"
    assessment = RiskAssessment(
        assessment_id=aid,
        transaction_id=data["transaction_id"],
        risk_score=float(data["risk_score"]),
        risk_level=data["risk_level"],
        decision=data["decision"],
        model_version=data.get("model_version", "fraud-model-v2")
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment

def get_latest_risk_assessment(db: Session, transaction_id: str) -> Optional[RiskAssessment]:
    return db.query(RiskAssessment).filter(
        RiskAssessment.transaction_id == transaction_id
    ).order_by(RiskAssessment.created_at.desc()).first()

# --- WORKFLOW TRANSITIONS & EVIDENCE MAPPING ---
def transition_dispute_workflow_stage(
    db: Session,
    dispute_id: str,
    target_stage: str,
    event_title: Optional[str] = None,
    event_desc: Optional[str] = None,
    force: bool = False
) -> Dispute:
    """
    Executes controlled workflow stage transitions with validation and atomic event persistence.
    Allows forward progress and rework/re-analysis.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    current_stage = dispute.workflow_stage or "DISPUTE_RAISED"

    if current_stage == target_stage:
        return dispute

    # Validate transition against allowed graph unless administrative override is enabled
    allowed_next = ALLOWED_WORKFLOW_TRANSITIONS.get(current_stage, [])
    if not force and allowed_next and target_stage not in allowed_next:
        raise ValueError(
            f"Invalid workflow transition from '{current_stage}' to '{target_stage}'. "
            f"Allowed next stages: {', '.join(allowed_next)}."
        )

    dispute.workflow_stage = target_stage
    db.commit()

    # Log immutable timeline event
    title = event_title or f"Stage Advanced to {target_stage.replace('_', ' ').title()}"
    desc = event_desc or f"Workflow stage updated from {current_stage} to {target_stage}."
    create_dispute_event(db, dispute_id, target_stage, title, desc)

    db.refresh(dispute)
    return dispute

def get_required_evidence_mapping(db: Session, dispute_id: str) -> List[Dict[str, Any]]:
    """
    Maps dispute reason-code requirements against real database evidence records.
    Returns granular evidence intelligence, verification status, and recommendations.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    from src.evidence.rules import get_required_evidence_types
    required_types = get_required_evidence_types(dispute.reason_code)
    existing_evidence = get_evidence_by_dispute(db, dispute_id)

    mapped_results = []
    # Build dictionary of existing evidence items grouped by type
    ev_by_type = {}
    for ev in existing_evidence:
        ev_by_type.setdefault(ev.evidence_type, []).append(ev)

    # 1. Evaluate Required Evidence Types
    for req_type in required_types:
        records = ev_by_type.get(req_type, [])
        if records:
            ver_status = records[0].verification_status or "VERIFIED"
            matched_records = [
                {
                    "evidence_id": r.evidence_id,
                    "title": r.title,
                    "description": r.description,
                    "source": r.source,
                    "verification_status": r.verification_status,
                    "data": r.evidence_data
                } for r in records
            ]
            mapped_results.append({
                "required_type": req_type,
                "title": req_type.replace("_", " ").title(),
                "is_required": True,
                "exists": True,
                "matched_records": matched_records,
                "verification_status": ver_status,
                "contradiction_status": "NONE",
                "evidence_strength": "STRONG" if ver_status in ["AVAILABLE", "VERIFIED"] else "MODERATE",
                "explanation": f"Verified {req_type.replace('_', ' ')} record loaded from database.",
                "recommended_action": "Record verified. Ready for representment inclusion."
            })
        else:
            mapped_results.append({
                "required_type": req_type,
                "title": req_type.replace("_", " ").title(),
                "is_required": True,
                "exists": False,
                "matched_records": [],
                "verification_status": "MISSING",
                "contradiction_status": "NONE",
                "evidence_strength": "MISSING",
                "explanation": f"Mandatory evidence type '{req_type}' is missing from database.",
                "recommended_action": f"Upload or attach {req_type.replace('_', ' ')} documentation to improve win probability."
            })

    return mapped_results


def get_case_readiness_and_gate(db: Session, dispute_id: str) -> Dict[str, Any]:
    """
    Evaluates real database entities to compute deterministic case readiness and submission eligibility.
    Enforces a strict submission gate to prevent premature or incomplete dispute submissions.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    tx = dispute.transaction
    evidence_mapping = get_required_evidence_mapping(db, dispute_id)
    package = get_chargeback_package_by_dispute(db, dispute_id)
    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)

    blocking_issues = []
    warnings = []
    completed_requirements = []

    # 1. Transaction Linkage Check
    if not tx:
        blocking_issues.append("Missing associated transaction record in database.")
    else:
        completed_requirements.append("Transaction linkage verified.")

    # 2. Required Evidence & Approval Check
    for item in evidence_mapping:
        if not item.get("is_required"):
            continue
        title = item.get("title", item.get("required_type", "Required evidence"))
        matched = item.get("matched_records", [])

        if not item.get("exists") or not matched:
            blocking_issues.append(f"{title} evidence is missing.")
            continue

        rec = matched[0]
        rec_id = rec.get("evidence_id")
        ev_obj = db.query(Evidence).filter(Evidence.evidence_id == rec_id, Evidence.is_deleted == 0).first() if rec_id else None

        if not ev_obj:
            blocking_issues.append(f"{title} evidence is missing.")
        elif (ev_obj.verification_status or "").upper() in ["INVALID", "UNREADABLE"]:
            blocking_issues.append(f"{title} is unreadable or failed verification.")
        elif (ev_obj.approval_status or "").upper() == "REJECTED":
            blocking_issues.append(f"{title} was rejected by merchant.")
        elif (ev_obj.verification_status or "").upper() in ["VERIFIED", "AVAILABLE"]:
            if (ev_obj.approval_status or "").upper() == "APPROVED":
                completed_requirements.append(f"{title} verified and approved.")
            else:
                completed_requirements.append(f"{title} verified.")
        else:
            blocking_issues.append(f"{title} failed verification.")

    # 3. AI Response / Rebuttal Check
    if not package or not package.response_text:
        warnings.append("AI rebuttal response statement not yet generated.")
    else:
        completed_requirements.append("AI rebuttal response statement generated.")

    # 4. Package Generation Check
    if not package:
        warnings.append("Evidence bundle package not yet created.")
    else:
        completed_requirements.append("Chargeback package bundle created.")

    # 5. Deadline Check
    if deadline_info.get("is_overdue"):
        blocking_issues.append("Dispute representment deadline is OVERDUE.")

    # Compute Deterministic Readiness Score (0 to 100)
    total_checks = max(1.0, float(len(evidence_mapping) + 3))
    passed_checks = len(completed_requirements)
    readiness_percentage = int(round((passed_checks / total_checks) * 100))

    can_submit = (len(blocking_issues) == 0) and (package is not None)

    if can_submit:
        readiness_status = "READY"
        readiness_percentage = max(readiness_percentage, 100)
    elif blocking_issues:
        readiness_status = "BLOCKED"
    else:
        readiness_status = "NOT_READY"

    next_actions = []
    if blocking_issues:
        next_actions.extend([f"Fix blocker: {issue}" for issue in blocking_issues])
    if warnings:
        next_actions.extend([f"Review warning: {warn}" for warn in warnings])
    if can_submit:
        next_actions.append("Case is READY. Click 'Submit to Razorpay Gateway' to finalize representment submission.")

    return {
        "dispute_id": dispute.dispute_id,
        "readiness_status": readiness_status,
        "readiness_percentage": readiness_percentage,
        "can_submit": can_submit,
        "blocking_issues": blocking_issues,
        "submission_blockers": blocking_issues,
        "warnings": warnings,
        "completed_requirements": completed_requirements,
        "next_actions": next_actions,
        "evidence_mapping": evidence_mapping,
        "deadline_info": deadline_info
    }

# --- CHARGEBACK PACKAGE (IDEMPOTENT UPSERT) ---
def create_chargeback_package(db: Session, data: Dict[str, Any]) -> ChargebackPackage:
    """
    Idempotently creates or updates a chargeback package bundle for a dispute.
    Lookup is performed by dispute_id to prevent duplicate package creation or UNIQUE constraint failures.
    """
    dispute_id = data["dispute_id"]
    existing = get_chargeback_package_by_dispute(db, dispute_id)

    if existing:
        existing.package_status = data.get("package_status", existing.package_status)
        existing.merchant_position = data.get("merchant_position", existing.merchant_position)
        existing.response_text = data.get("response_text", existing.response_text)
        existing.generator_version = data.get("generator_version", existing.generator_version)
        if "package_data" in data:
            existing.package_data = data["package_data"]
        db.commit()

        # Update workflow stage to EVIDENCE_BUNDLE_CREATED idempotently if in early stage
        dispute = get_dispute(db, dispute_id)
        if dispute and dispute.workflow_stage not in ["DISPUTE_RAISED", "MERCHANT_REVIEW", "READY_FOR_SUBMISSION", "SUBMITTED", "RESOLVED"]:
            dispute.workflow_stage = "EVIDENCE_BUNDLE_CREATED"
            db.commit()

        create_dispute_event(
            db, dispute_id, "EVIDENCE_BUNDLE_UPDATED", "Evidence Bundle Package Updated",
            f"Updated existing package {existing.package_id} for dispute {dispute_id}."
        )
        db.refresh(existing)
        return existing

    pkg_id = data.get("package_id") or generate_package_id()
    pkg = ChargebackPackage(
        package_id=pkg_id,
        dispute_id=dispute_id,
        transaction_id=data["transaction_id"],
        package_status=data.get("package_status", "READY_FOR_REVIEW"),
        merchant_position=data.get("merchant_position", "CONTEST"),
        response_text=data.get("response_text", ""),
        generator_version=data.get("generator_version", "1.0")
    )
    pkg.package_data = data.get("package_data", {})
    db.add(pkg)
    db.commit()

    # Update dispute workflow stage
    dispute = get_dispute(db, dispute_id)
    if dispute and dispute.workflow_stage not in ["DISPUTE_RAISED", "MERCHANT_REVIEW", "READY_FOR_SUBMISSION", "SUBMITTED", "RESOLVED"]:
        dispute.workflow_stage = "EVIDENCE_BUNDLE_CREATED"
        db.commit()

    create_dispute_event(
        db, dispute_id, "EVIDENCE_BUNDLE_CREATED", "Evidence Bundle Package Created",
        f"Assembled evidence bundle package {pkg_id} for dispute {dispute_id}."
    )

    db.refresh(pkg)
    return pkg

def submit_dispute_package(db: Session, dispute_id: str, merchant_position: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the hard backend submission gate.
    Validates case readiness, records merchant position, generates unique gateway reference ID,
    advances workflow_stage to SUBMITTED, and creates PACKAGE_SUBMITTED audit event.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    if dispute.workflow_stage == "SUBMITTED" or (dispute.status or "").upper() in ["WON", "LOST", "CLOSED"]:
        raise ValueError(f"Dispute '{dispute_id}' has already been submitted or closed.")

    gate_result = get_case_readiness_and_gate(db, dispute_id)
    if not gate_result["can_submit"]:
        issues = "; ".join(gate_result["blocking_issues"])
        raise ValueError(f"Submission BLOCKED by gate: {issues}")

    position = merchant_position or "CONTEST"
    reference_id = generate_reference_id()
    submission_id = f"sub_{uuid.uuid4().hex[:12]}"
    submitted_at = utc_now_iso()

    dispute.workflow_stage = "SUBMITTED"
    dispute.status = "under_review"
    dispute.merchant_attention_state = "WAITING"
    db.commit()

    # Update Package status and metadata
    pkg = get_chargeback_package_by_dispute(db, dispute_id)
    if pkg:
        pkg.package_status = "SUBMITTED"
        pkg.merchant_position = position
        pkg_data = pkg.package_data or {}
        pkg_data["submission_id"] = submission_id
        pkg_data["gateway_reference_id"] = reference_id
        pkg_data["submitted_at"] = submitted_at
        pkg.package_data = pkg_data
        db.commit()

    # Log immutable timeline event
    submission_event = create_dispute_event(
        db, dispute_id, "PACKAGE_SUBMITTED", "Submitted to Razorpay Gateway (Simulated Boundary)",
        f"Dispute package submitted to gateway. Submission ID: {submission_id}, Gateway Reference ID: {reference_id}. Position: {position}.",
        actor_type="MERCHANT",
        previous_stage="READY_FOR_SUBMISSION",
        new_stage="SUBMITTED",
        metadata={
            "submission_id": submission_id,
            "gateway_reference_id": reference_id,
            "merchant_position": position,
            "submitted_at": submitted_at
        }
    )

    try:
        from src.api.routes.events import publish_realtime_event
        publish_realtime_event("DISPUTE_STAGE_CHANGED", dispute_id=dispute_id, data={"new_stage": "SUBMITTED", "gateway_reference_id": reference_id, "submission_id": submission_id})
        publish_realtime_event("DASHBOARD_UPDATED", dispute_id=dispute_id, data={"trigger": "PACKAGE_SUBMITTED"})
    except Exception:
        pass

    timeline = get_dispute_timeline(db, dispute_id)
    timeline_dicts = [
        {
            "event_id": t.event_id,
            "dispute_id": t.dispute_id,
            "event_type": t.event_type,
            "title": t.title,
            "description": t.description,
            "timestamp": t.timestamp
        }
        for t in timeline
    ]

    return {
        "dispute_id": dispute_id,
        "workflow_stage": "SUBMITTED",
        "status": dispute.status,
        "is_submitted": True,
        "submission_id": submission_id,
        "gateway_reference_id": reference_id,
        "merchant_position": position,
        "submitted_at": submitted_at,
        "submission_boundary_notice": "Submission recorded locally via Local Gateway Integration Boundary (Simulated Razorpay Gateway).",
        "event": {
            "event_id": submission_event.event_id,
            "title": submission_event.title,
            "timestamp": submission_event.timestamp
        },
        "dispute": {
            "dispute_id": dispute.dispute_id,
            "transaction_id": dispute.transaction_id,
            "status": dispute.status,
            "workflow_stage": dispute.workflow_stage,
            "merchant_attention_state": dispute.merchant_attention_state
        },
        "timeline": timeline_dicts
    }


def simulate_dispute_outcome(db: Session, dispute_id: str) -> Dict[str, Any]:
    """
    Simulates the lifecycle transition from SUBMITTED -> UNDER_REVIEW -> WON / LOST.
    Outcome is deterministic based on evidence completeness, win probability, fraud risk, and merchant position.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    pkg = get_chargeback_package_by_dispute(db, dispute_id)
    merchant_pos = pkg.merchant_position if pkg else "CONTEST"

    # Fetch AI analysis metrics
    analysis = get_dispute_case_analysis(db, dispute_id)
    win_prob = analysis.get("win_probability", {}).get("score", 0.5)
    completeness = analysis.get("evidence_intelligence", {}).get("evidence_completeness", 0.5)
    risk_level = analysis.get("risk_analysis", {}).get("risk_level", "LOW")
    missing = analysis.get("evidence_intelligence", {}).get("missing_evidence", [])

    # Deterministic resolution
    if merchant_pos.upper() == "ACCEPT" or dispute.status.upper() == "CLOSED":
        final_status = "LOST"
        outcome_reason = "Merchant accepted dispute claim. Representment conceded."
    elif win_prob >= 0.55 and completeness >= 0.70 and not missing and risk_level != "HIGH":
        final_status = "WON"
        outcome_reason = "Card issuer reviewed defense representation and ruled in merchant favor based on complete verified fulfillment and authentication records."
    else:
        final_status = "LOST"
        outcome_reason = f"Card issuer rejected defense representation due to insufficient mandatory evidence ({', '.join(missing) if missing else 'unresolved claim factors'})."

    previous_status = dispute.status
    previous_stage = dispute.workflow_stage

    dispute.status = final_status
    dispute.workflow_stage = "RESOLVED"
    dispute.merchant_attention_state = "WAITING"
    db.commit()

    # Log outcome event
    event_type = f"DISPUTE_{final_status}"
    outcome_event = create_dispute_event(
        db, dispute_id,
        event_type=event_type,
        title=f"Dispute Gateway Resolution: {final_status}",
        description=outcome_reason,
        actor_type="LOCAL_GATEWAY",
        previous_stage=previous_stage,
        new_stage="RESOLVED",
        metadata={
            "final_status": final_status,
            "outcome_reason": outcome_reason,
            "win_probability": win_prob,
            "evidence_completeness": completeness,
            "is_simulated": True
        }
    )

    try:
        from src.api.routes.events import publish_realtime_event
        publish_realtime_event("DISPUTE_STAGE_CHANGED", dispute_id=dispute_id, data={"new_stage": "RESOLVED", "status": final_status})
        publish_realtime_event("DASHBOARD_UPDATED", dispute_id=dispute_id, data={"trigger": "OUTCOME_RECEIVED"})
    except Exception:
        pass

    return {
        "dispute_id": dispute_id,
        "previous_status": previous_status,
        "final_status": final_status,
        "workflow_stage": "RESOLVED",
        "merchant_attention_state": "WAITING",
        "outcome_reason": outcome_reason,
        "is_simulated": True,
        "win_probability": win_prob,
        "evidence_completeness": completeness,
        "event": {
            "event_id": outcome_event.event_id,
            "title": outcome_event.title,
            "timestamp": outcome_event.timestamp
        }
    }


def get_dispute_explainability(db: Session, dispute_id: str) -> Dict[str, Any]:

    """Retrieves AI explainability for Fraud Model V2 and Win Probability model."""
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    tx = dispute.transaction
    risk_asm = get_latest_risk_assessment(db, dispute.transaction_id)
    evidence_records = dispute.evidence_records

    from src.explainability.engine import AIExplainabilityEngine
    fraud_expl = AIExplainabilityEngine.explain_fraud_risk(tx, risk_asm)

    # Estimate win probability score
    from src.database.repository import get_dispute_case_analysis
    try:
        case_analysis = get_dispute_case_analysis(db, dispute_id)
        win_score = case_analysis["win_probability"]["score"]
    except Exception:
        win_score = 0.75

    win_expl = AIExplainabilityEngine.explain_win_probability(dispute, evidence_records, win_score)

    return {
        "dispute_id": dispute_id,
        "transaction_id": dispute.transaction_id,
        "fraud_explainability": fraud_expl,
        "win_explainability": win_expl
    }

def get_dispute_next_action(db: Session, dispute_id: str) -> Dict[str, Any]:
    """Computes deterministic Next Best Action for the merchant."""
    gate = get_case_readiness_and_gate(db, dispute_id)
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    pkg = get_chargeback_package_by_dispute(db, dispute_id)
    from src.response.service import ResponseGeneratorService
    try:
        resp = ResponseGeneratorService().generate_response_for_dispute(db, dispute_id)
        has_ai_response = bool(resp and resp.response_text)
    except Exception:
        has_ai_response = False

    missing_types = [item["required_type"] for item in gate["evidence_mapping"] if item["is_required"] and not item["exists"]]

    from src.actions.engine import NextBestActionEngine
    action_res = NextBestActionEngine.evaluate_next_action(
        dispute_id=dispute_id,
        workflow_stage=dispute.workflow_stage or "DISPUTE_RAISED",
        urgency_level=gate["deadline_info"].get("urgency_level", "SAFE"),
        recommendation_decision=dispute.status,
        can_submit=gate["can_submit"],
        blocking_issues=gate["blocking_issues"],
        warnings=gate["warnings"],
        missing_evidence=missing_types,
        has_contradictions=len(gate["warnings"]) > 0 and "contradiction" in "".join(gate["warnings"]).lower(),
        has_ai_response=has_ai_response,
        has_package=pkg is not None
    )
    return action_res

def get_dispute_command_center(db: Session, dispute_id: str) -> Dict[str, Any]:
    """
    Aggregates a complete, single coherent Operations Command Center snapshot for a dispute.
    Consumed directly by DisputeDetailPage.tsx for high-performance rendering.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute '{dispute_id}' not found.")

    from src.chargeback.service import ChargebackPackageService
    analysis = get_dispute_case_analysis(db, dispute_id)
    explainability = get_dispute_explainability(db, dispute_id)
    next_action = get_dispute_next_action(db, dispute_id)
    audit_trail = get_dispute_audit_trail(db, dispute_id)
    package_inspection = ChargebackPackageService().inspect_chargeback_package(db, dispute_id)

    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)
    dispute_dict = {
        "dispute_id": dispute.dispute_id,
        "transaction_id": dispute.transaction_id,
        "customer_id": dispute.customer_id,
        "reason_code": dispute.reason_code,
        "reason_description": dispute.reason_description or "",
        "status": dispute.status,
        "phase": dispute.phase or "chargeback",
        "respond_by": dispute.respond_by,
        "workflow_stage": dispute.workflow_stage or "DISPUTE_RAISED",
        "created_at": dispute.created_at,
        "remaining_hours": deadline_info["remaining_hours"],
        "remaining_time_human": deadline_info["remaining_time_human"],
        "is_overdue": deadline_info["is_overdue"],
        "deadline_status": deadline_info["deadline_status"],
        "urgency_level": deadline_info["urgency_level"],
        "amount": dispute.transaction.amount if dispute.transaction else None,
        "currency": dispute.transaction.currency if dispute.transaction else "USD"
    }

    from src.evidence.engine import EvidenceEngine
    evidence_pkg = EvidenceEngine().evaluate_dispute_evidence(db, dispute_id)
    evidence_dict = evidence_pkg.model_dump()
    readiness = get_case_readiness_and_gate(db, dispute_id)

    return {
        "dispute_id": dispute_id,
        "dispute": dispute_dict,
        "case_analysis": analysis,
        "explainability": explainability,
        "next_action": next_action,
        "evidence": evidence_dict.get("evidence", []),
        "evidence_summary": {
            "evidence_count": evidence_dict.get("evidence_count", 0),
            "available_count": evidence_dict.get("available_count", 0),
            "missing_count": evidence_dict.get("missing_count", 0),
            "unverified_count": evidence_dict.get("unverified_count", 0),
            "invalid_count": evidence_dict.get("invalid_count", 0)
        },
        "required_evidence": analysis.get("evidence_intelligence", {}).get("missing_evidence", []) + [e.get("evidence_type") for e in evidence_dict.get("evidence", []) if e.get("status") == "AVAILABLE"],
        "missing_evidence": analysis.get("evidence_intelligence", {}).get("missing_evidence", []),
        "package_inspection": package_inspection,
        "package": package_inspection.get("package_metadata", {}),
        "response": package_inspection.get("rebuttal", {}),
        "submission_readiness": readiness.get("readiness_status", "NOT_READY"),
        "submission_blockers": readiness.get("blocking_issues", []),
        "timeline": audit_trail,
        "audit_trail": audit_trail,
        "merchant_attention_state": dispute.merchant_attention_state
    }



def get_chargeback_package(db: Session, package_id: str) -> Optional[ChargebackPackage]:
    return db.query(ChargebackPackage).filter(ChargebackPackage.package_id == package_id).first()

def get_chargeback_package_by_dispute(db: Session, dispute_id: str) -> Optional[ChargebackPackage]:
    return db.query(ChargebackPackage).filter(
        ChargebackPackage.dispute_id == dispute_id
    ).order_by(ChargebackPackage.created_at.desc()).first()


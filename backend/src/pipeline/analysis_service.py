"""
Authoritative Dispute Analysis Service — Razorpay AI Risk Manager.
Single source of truth for end-to-end dispute intelligence, executing:
1. Evidence Engine evaluation
2. Real Fraud V2 ML inference (models/fraud_v2_pipeline.joblib)
3. Real Win Probability ML inference (models/win_pipeline.joblib)
4. Deterministic model & data confidence calculation
5. Quantitative ML recommendation
6. DeepSeek AI reasoning & merchant guidance (with guaranteed fallback)
7. ML vs AI recommendation conflict detection
8. Versioned DisputeAssessment persistence
9. Real-time Server-Sent Event (SSE) broadcasting
10. Immutable timeline audit logging
"""

from typing import Dict, Any, Optional, List
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.database.models import (
    Dispute, Transaction, Customer, Payment, Order, Fulfillment,
    Evidence, DisputeEvent, DisputeAssessment, utc_now_iso
)
from src.database.repository import (
    get_dispute, create_dispute_event, calculate_deadline_info
)
from src.components.fraud_model_v2 import FraudModelV2Wrapper
from src.components.win_probability import WinProbabilityModelWrapper
from src.evidence.engine import EvidenceEngine
from src.explainability.engine import AIExplainabilityEngine
from src.api.routes.events import publish_realtime_event
from src.utils.logger import get_logger

logger = get_logger("DisputeAnalysisService")

# Singletons for ML and Evidence components
_fraud_v2_model = FraudModelV2Wrapper()
_win_model = WinProbabilityModelWrapper()
_evidence_engine = EvidenceEngine()


def compute_deterministic_confidence(
    win_prob: float,
    fraud_prob: float,
    evidence_completeness: float,
    is_win_trained: bool,
    is_fraud_trained: bool
) -> tuple[float, str, str]:
    """
    Computes system confidence score (0.0 - 1.0) and level ('HIGH', 'MEDIUM', 'LOW')
    deterministically derived from model prediction certainty and data completeness.
    """
    win_margin = abs(win_prob - 0.50)
    fraud_margin = abs(fraud_prob - 0.50)

    # Base certainty from distance to decision boundary
    certainty_score = (win_margin * 1.2) + (fraud_margin * 0.8)
    data_score = evidence_completeness * 0.4
    model_readiness = 0.2 if (is_win_trained and is_fraud_trained) else 0.1

    raw_score = min(0.98, max(0.20, certainty_score + data_score + model_readiness))
    conf_score = round(raw_score, 4)

    if conf_score >= 0.75 and win_margin >= 0.15:
        conf_level = "HIGH"
        explanation = f"High confidence ({int(conf_score*100)}%): Strong model certainty with complete case evidence."
    elif conf_score >= 0.50:
        conf_level = "MEDIUM"
        explanation = f"Moderate confidence ({int(conf_score*100)}%): Reasonable certainty based on available signals."
    else:
        conf_level = "LOW"
        explanation = f"Low confidence ({int(conf_score*100)}%): Close to 50/50 decision boundary or missing evidence."

    return conf_score, conf_level, explanation


def determine_ml_recommendation(win_prob: float, fraud_prob: float, missing_evidence: List[str]) -> str:
    """
    Authoritative quantitative ML decision rule:
    - CONTEST: Win probability >= 0.58 AND fraud probability < 0.55
    - ACCEPT: Win probability < 0.35 OR fraud probability >= 0.70
    - INVESTIGATE: Ambiguous cases requiring human merchant review
    """
    if fraud_prob >= 0.70:
        return "ACCEPT"
    if win_prob >= 0.58 and fraud_prob < 0.55:
        return "CONTEST"
    if win_prob < 0.35:
        return "ACCEPT"
    return "INVESTIGATE"


def compute_attention_state(
    dispute_status: str,
    workflow_stage: str,
    missing_evidence: List[str],
    contradictions_count: int,
    risk_level: str,
    urgency_level: str,
    evidence_completeness: float,
    win_prob: float
) -> tuple[str, str]:
    """Deterministically classifies merchant attention queue and explanation."""
    status_upper = (dispute_status or "OPEN").upper()
    stage_upper = (workflow_stage or "DISPUTE_RAISED").upper()

    if status_upper in ["WON", "LOST", "CLOSED"] or stage_upper in ["SUBMITTED", "RESOLVED"]:
        return "WAITING", "Submitted to local gateway boundary. Awaiting bank resolution."

    if missing_evidence:
        return "ACTION_REQUIRED", f"Missing mandatory evidence: {', '.join(missing_evidence[:3])}"
    if contradictions_count > 0:
        return "ACTION_REQUIRED", "Evidence contradiction detected across transaction records."
    if risk_level == "CRITICAL" or risk_level == "HIGH":
        return "ACTION_REQUIRED", "High fraud risk transaction requires manual merchant investigation."
    if urgency_level in ["URGENT", "OVERDUE"]:
        return "ACTION_REQUIRED", f"Representment deadline is {urgency_level.lower()} — immediate action required."

    if stage_upper in ["MERCHANT_REVIEW", "AI_RESPONSE_GENERATED", "READY_FOR_SUBMISSION"]:
        return "REVIEW_RECOMMENDED", "AI has prepared defense representation. Merchant review recommended."

    if evidence_completeness >= 0.60 and win_prob >= 0.45:
        return "AI_HANDLING", "AI Autopilot is actively monitoring evidence coverage and deadlines."

    return "ACTION_REQUIRED", "AI analysis completed. Case requires attention."


def analyze_dispute(
    dispute_id: str,
    db: Session,
    trigger: str = "MANUAL_REASSESSMENT",
    broadcast: bool = True
) -> Dict[str, Any]:
    """
    Authoritative single-source-of-truth analysis pipeline for dispute cases.
    Called on DISPUTE_CREATED, EVIDENCE_ADDED, EVIDENCE_APPROVED, etc.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute with ID '{dispute_id}' not found in active database.")

    logger.info(f"Starting authoritative dispute analysis for {dispute_id} (Trigger: {trigger})")

    if broadcast:
        publish_realtime_event("DISPUTE_ANALYSIS_STARTED", dispute_id=dispute_id, data={"trigger": trigger})

    tx = dispute.transaction
    cust = tx.customer if tx else None
    order = tx.order if tx else None
    fulfillment = order.fulfillment if order else None
    payments = tx.payments if tx else []
    payment = payments[0] if payments else None

    # 1. Evaluate Evidence Engine
    evidence_pkg = _evidence_engine.evaluate_dispute_evidence(db, dispute_id)
    evidence_dict = evidence_pkg.model_dump()
    evidence_items = evidence_dict.get("evidence", [])

    available_evidence = [e for e in evidence_items if e.get("status") in ["AVAILABLE", "VERIFIED"]]
    missing_evidence = [e.get("evidence_type") for e in evidence_items if e.get("status") == "MISSING"]
    unverified_evidence = [e.get("evidence_type") for e in evidence_items if e.get("status") == "UNVERIFIED"]
    approved_evidence = [e for e in evidence_items if e.get("approval_status") == "APPROVED"]

    evidence_completeness = float(evidence_dict.get("completeness_score", 0.0))
    evidence_quality = str(evidence_dict.get("quality_score", "MEDIUM"))
    quality_numeric = 0.85 if evidence_quality == "HIGH" else (0.60 if evidence_quality == "MEDIUM" else 0.35)
    contradictions_count = len(evidence_dict.get("contradictions", []))
    contradiction_severity = "NONE" if contradictions_count == 0 else "MEDIUM"

    # 2. Extract Exact Fraud V2 ML Features & Predict
    fraud_payload = {
        "transaction_hour": tx.transaction_hour if tx else 12,
        "account_age_days": cust.account_age_days if cust else (tx.account_age_days if tx else 180),
        "previous_chargebacks": cust.previous_chargebacks if cust else (tx.previous_chargebacks if tx else 0),
        "transaction_amount": tx.amount if tx else 100.0,
        "transaction_velocity_1h": tx.transaction_velocity_1h if tx else 0,
        "transaction_velocity_24h": tx.transaction_velocity_24h if tx else 0,
        "avg_transaction_amount_30d": cust.avg_transaction_amount_30d if cust else (tx.avg_transaction_amount_30d if tx else 100.0),
        "merchant_category": tx.merchant_category if tx else "retail",
        "transaction_country": tx.transaction_country if tx else "US",
        "device_type": tx.device_type if tx else "mobile",
        "is_international": tx.is_international if tx else 0,
        "is_high_risk_merchant": tx.is_high_risk_merchant if tx else 0
    }

    try:
        fraud_pred = _fraud_v2_model.predict(fraud_payload)
        fraud_prob = float(fraud_pred["fraud_probability"])
        risk_level = str(fraud_pred["risk_level"])
        fraud_model_trained = bool(fraud_pred.get("is_model_trained", True))
        fraud_source = "MODEL" if fraud_model_trained else "FALLBACK"
        fraud_status = "OK"
    except Exception as e:
        logger.error(f"Fraud V2 inference failed: {e}")
        fraud_prob = 0.25
        risk_level = "LOW"
        fraud_model_trained = False
        fraud_source = "FALLBACK"
        fraud_status = "FAILED"

    # 3. Extract Exact Win Probability ML Features & Predict
    try:
        win_pred = _win_model.predict(
            dispute_payload={
                "reason_code": dispute.reason_code,
                "dispute_reason": dispute.reason_code,
                "dispute_amount": tx.amount if tx else 100.0,
                "transaction_amount": tx.amount if tx else 100.0,
                "merchant_historical_win_rate": 0.65,
                "previous_disputes_won_count": 5
            },
            completeness_score=evidence_completeness,
            evidence_quality_score=quality_numeric,
            contradiction_count=contradictions_count,
            contradiction_severity=contradiction_severity,
            fraud_prob=fraud_prob,
            available_evidence=available_evidence
        )
        win_prob = float(win_pred["win_probability"])
        win_model_trained = bool(win_pred.get("is_model_trained", True))
        win_source = "MODEL" if win_model_trained else "RULE_FALLBACK"
        win_status = win_pred.get("ml_status", "OK")
    except Exception as e:
        logger.error(f"Win Probability inference failed: {e}")
        win_prob = 0.50
        win_model_trained = False
        win_source = "RULE_FALLBACK"
        win_status = "FAILED"

    # 4. Confidence Calculation
    confidence_score, confidence_level, confidence_expl = compute_deterministic_confidence(
        win_prob=win_prob,
        fraud_prob=fraud_prob,
        evidence_completeness=evidence_completeness,
        is_win_trained=win_model_trained,
        is_fraud_trained=fraud_model_trained
    )

    # 5. Quantitative ML Recommendation
    ml_rec = determine_ml_recommendation(win_prob, fraud_prob, missing_evidence)

    if broadcast:
        publish_realtime_event("ML_ANALYSIS_COMPLETED", dispute_id=dispute_id, data={
            "fraud_probability": fraud_prob,
            "win_probability": win_prob,
            "confidence": confidence_score,
            "confidence_level": confidence_level,
            "ml_recommendation": ml_rec
        })

    # 6. DeepSeek AI Language Layer Execution
    from src.services.ai.service import AIService
    ai_service = AIService()

    # Invalidate cached AI outputs on reassessment
    ai_service.invalidate_cache(dispute_id)

    try:
        explanation_obj = ai_service.get_case_explanation(db, dispute_id)
        explanation_text = getattr(explanation_obj, "plain_english_explanation", getattr(explanation_obj, "summary", ""))
        reasoning_list = getattr(explanation_obj, "recommendation_reasoning", [])
        reasoning_text = "\n".join(reasoning_list) if isinstance(reasoning_list, list) else str(reasoning_list)
        ai_rec_raw = getattr(explanation_obj, "recommendation_code", "CONTEST")
        ai_rec = "CONTEST" if "CONTEST" in str(ai_rec_raw).upper() else ("ACCEPT" if "ACCEPT" in str(ai_rec_raw).upper() else "REVIEW")
        ai_source = "DEEPSEEK" if getattr(explanation_obj, "_is_fallback", False) is False and ai_service.client.is_available() else "FALLBACK"
        ai_status = "OK" if ai_source == "DEEPSEEK" else "FALLBACK"
    except Exception as e:
        logger.warning(f"DeepSeek call failed: {e}. Utilizing fallback reasoning.")
        explanation_text = f"Dispute for {dispute.reason_code.replace('_', ' ')} evaluated. Win probability is {int(win_prob*100)}%."
        reasoning_text = f"Decision driven by {len(available_evidence)} available evidence items and {int(evidence_completeness*100)}% completeness."
        ai_rec = ml_rec
        ai_source = "FALLBACK"
        ai_status = "FALLBACK"

    # Fetch AI Evidence Guidance & Structured Rebuttal
    try:
        evidence_guidance = ai_service.get_evidence_guidance(db, dispute_id)
        evidence_guidance_list = [g.model_dump() for g in evidence_guidance]
    except Exception:
        evidence_guidance_list = []

    try:
        structured_rebuttal = ai_service.generate_structured_response(db, dispute_id)
        rebuttal_dict = structured_rebuttal.model_dump()
    except Exception:
        rebuttal_dict = {}

    if broadcast:
        publish_realtime_event("DEEPSEEK_ANALYSIS_COMPLETED", dispute_id=dispute_id, data={
            "ai_source": ai_source,
            "ai_status": ai_status,
            "ai_recommendation": ai_rec
        })

    # 7. Conflict Detection between ML & DeepSeek
    conflict_detected = (ml_rec != ai_rec)

    # 8. Compute Deadline and Operational Attention State
    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)
    attention_state, attention_reason = compute_attention_state(
        dispute_status=dispute.status,
        workflow_stage=dispute.workflow_stage,
        missing_evidence=missing_evidence,
        contradictions_count=contradictions_count,
        risk_level=risk_level,
        urgency_level=deadline_info.get("urgency_level", "SAFE"),
        evidence_completeness=evidence_completeness,
        win_prob=win_prob
    )

    # 9. Persist Updated Dispute State
    dispute.merchant_attention_state = attention_state
    dispute.ai_last_checked = utc_now_iso()
    db.commit()

    # 10. Persist Versioned DisputeAssessment
    latest_assessment = db.query(DisputeAssessment).filter(
        DisputeAssessment.dispute_id == dispute_id
    ).order_by(DisputeAssessment.analysis_version.desc()).first()
    next_version = (latest_assessment.analysis_version + 1) if latest_assessment else 1

    assessment = DisputeAssessment(
        assessment_id=f"ASM_{uuid.uuid4().hex[:8].upper()}",
        dispute_id=dispute_id,
        analysis_version=next_version,
        trigger=trigger,
        risk_score=round(fraud_prob * 100.0, 2),
        fraud_probability=fraud_prob,
        win_probability=win_prob,
        confidence=confidence_score,
        confidence_level=confidence_level,
        ml_recommendation=ml_rec,
        ai_recommendation=ai_rec,
        conflict_detected=1 if conflict_detected else 0,
        ml_results_json=json.dumps({
            "fraud_probability": fraud_prob,
            "risk_level": risk_level,
            "prediction_source": fraud_source,
            "ml_status": fraud_status,
            "win_probability": win_prob,
            "win_source": win_source,
            "win_status": win_status,
            "confidence": confidence_score,
            "confidence_level": confidence_level,
            "ml_recommendation": ml_rec
        }),
        deepseek_results_json=json.dumps({
            "ai_source": ai_source,
            "ai_status": ai_status,
            "ai_recommendation": ai_rec,
            "explanation": explanation_text,
            "reasoning": reasoning_text,
            "evidence_guidance": evidence_guidance_list,
            "rebuttal_draft": rebuttal_dict.get("defense_statement", "")
        }),
        evidence_analysis_json=json.dumps({
            "completeness_score": evidence_completeness,
            "quality_score": evidence_quality,
            "available_evidence": available_evidence,
            "missing_evidence": missing_evidence,
            "unverified_evidence": unverified_evidence,
            "approved_evidence": approved_evidence,
            "contradictions_count": contradictions_count
        }),
        model_versions_json=json.dumps({
            "fraud_model": "fraud_v2_pipeline.joblib",
            "win_model": "win_pipeline.joblib",
            "ai_model": "deepseek-chat"
        }),
        generated_at=utc_now_iso()
    )
    db.add(assessment)
    db.commit()

    # 11. Create Dispute Audit Event
    create_dispute_event(
        db, dispute_id,
        event_type="AI_REASSESSMENT",
        title=f"AI Reassessed Case (v{next_version})",
        description=(
            f"Evaluated case via Fraud V2 ({int(fraud_prob*100)}%), Win Probability ({int(win_prob*100)}%), "
            f"and DeepSeek AI ({ai_source}). Recommendation: {ml_rec}."
        ),
        actor_type="AI_ENGINE",
        previous_stage=dispute.workflow_stage,
        new_stage=dispute.workflow_stage,
        metadata={
            "analysis_version": next_version,
            "trigger": trigger,
            "fraud_probability": fraud_prob,
            "win_probability": win_prob,
            "confidence_score": confidence_score,
            "ml_recommendation": ml_rec,
            "ai_recommendation": ai_rec,
            "conflict_detected": conflict_detected,
            "ai_source": ai_source
        }
    )

    # 11b. Update Dispute Workflow Stage to MERCHANT_REVIEW if in early processing
    if dispute.workflow_stage in ["AI_ANALYSIS", "EVIDENCE_COLLECTION"]:
        dispute.workflow_stage = "MERCHANT_REVIEW"
        db.commit()

    # 12. Regenerate / Synchronize Chargeback Package Idempotently
    package_data = None
    try:
        from src.chargeback.service import ChargebackPackageService
        pkg_schema = ChargebackPackageService().generate_and_save_package(db, dispute_id, force_regenerate=True)
        package_data = pkg_schema.model_dump()
    except Exception as pkg_err:
        logger.warning(f"Package generation error during analysis: {pkg_err}")

    # 13. Calculate Authoritative Submission Readiness & Blockers
    from src.database.repository import get_case_readiness_and_gate
    readiness = get_case_readiness_and_gate(db, dispute_id)

    # 14. Build Consolidated Snapshot
    case_summary = {
        "dispute_id": dispute.dispute_id,
        "transaction_id": dispute.transaction_id,
        "customer_id": dispute.customer_id,
        "account_age_days": cust.account_age_days if cust else (tx.account_age_days if tx else 180),
        "product_description": order.product_description if order else "N/A",
        "order_amount": order.order_amount if order else (tx.amount if tx else 100.0),
        "shipping_status": fulfillment.shipping_status if fulfillment else "N/A",
        "delivery_status": fulfillment.delivery_status if fulfillment else "N/A",
        "tracking_number": fulfillment.tracking_number if fulfillment else None,
        "auth_code": payment.auth_code if payment else None,
        "avs_match": payment.avs_match if payment else "Y",
        "cvv_match": payment.cvv_match if payment else "Y",
        "reason_code": dispute.reason_code,
        "reason_description": dispute.reason_description
    }

    result = {
        "dispute_id": dispute.dispute_id,
        "transaction_id": dispute.transaction_id,
        "customer_id": dispute.customer_id,
        "amount": tx.amount if tx else 0.0,
        "currency": tx.currency if tx else "USD",
        "status": dispute.status,
        "phase": dispute.phase or "chargeback",
        "workflow_stage": dispute.workflow_stage or "MERCHANT_REVIEW",
        "case_source": getattr(dispute, "case_source", "SIMULATED_RAZORPAY") or "SIMULATED_RAZORPAY",
        "merchant_attention_state": attention_state,
        "ai_last_checked": dispute.ai_last_checked,
        "attention_reason": attention_reason,
        "respond_by": dispute.respond_by,
        "remaining_hours": deadline_info["remaining_hours"],
        "remaining_time_human": deadline_info["remaining_time_human"],
        "is_overdue": deadline_info["is_overdue"],
        "deadline_status": deadline_info["deadline_status"],
        "urgency_level": deadline_info.get("urgency_level", "SAFE"),
        "submission_readiness": readiness.get("readiness_status", "NOT_READY"),
        "submission_blockers": readiness.get("blocking_issues", []),
        "case_readiness": readiness,
        "package": package_data,
        "case_summary": case_summary,
        "risk_analysis": {
            "fraud_probability": fraud_prob,
            "risk_level": risk_level,
            "model_version": "v2",
            "pipeline": "fraud_v2_pipeline.joblib",
            "prediction_source": fraud_source,
            "ml_status": fraud_status
        },
        "evidence_intelligence": {
            "evidence_completeness": evidence_completeness,
            "evidence_quality": evidence_quality,
            "missing_evidence": missing_evidence,
            "unverified_evidence": unverified_evidence,
            "approved_evidence_count": len(approved_evidence),
            "contradictions_count": contradictions_count,
            "contradiction_severity": contradiction_severity
        },
        "win_probability": {
            "score": win_prob,
            "confidence_score": confidence_score,
            "confidence_level": confidence_level,
            "confidence_explanation": confidence_expl,
            "prediction_source": win_source,
            "ml_status": win_status
        },
        "recommendation": {
            "decision": ml_rec,
            "ml_recommendation": ml_rec,
            "ai_recommendation": ai_rec,
            "conflict_detected": conflict_detected,
            "merchant_recommendation": "Challenge this dispute" if ml_rec == "CONTEST" else ("Accept this dispute" if ml_rec == "ACCEPT" else "Review further"),
            "explanation": explanation_text,
            "reasoning": reasoning_text,
            "ai_source": ai_source,
            "ai_status": ai_status
        },
        "evidence_guidance": evidence_guidance_list,
        "rebuttal_draft": rebuttal_dict,
        "next_actions": [
            f"Upload missing required evidence: {', '.join(missing_evidence)}" if missing_evidence else "All required evidence collected.",
            f"Review evidence contradiction ({contradictions_count} found)" if contradictions_count > 0 else "Evidence integrity verified.",
            "Proceed to merchant review and approve evidence." if ml_rec == "CONTEST" else ("Review further before representment." if ml_rec == "REVIEW" else "Accept dispute claim or provide additional proof.")
        ],
        "assessment_version": next_version,
        "reassessed_at": utc_now_iso()
    }

    if broadcast:
        publish_realtime_event("DISPUTE_ANALYSIS_COMPLETED", dispute_id=dispute_id, data=result)
        publish_realtime_event("DASHBOARD_UPDATED", dispute_id=dispute_id, data={"trigger": trigger})

    logger.info(f"Completed authoritative analysis for {dispute_id}: ML={ml_rec}, Win={win_prob:.2f}, Fraud={fraud_prob:.2f}")
    return result

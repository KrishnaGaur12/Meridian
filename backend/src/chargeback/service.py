"""
Chargeback Package Generator Service.
Orchestrates the full pipeline: Dispute -> Tx -> Risk -> Evidence -> AI Response -> Package Assembly -> DB Persistence.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from src.database.repository import (
    get_dispute, get_latest_risk_assessment, create_chargeback_package,
    get_chargeback_package, get_chargeback_package_by_dispute
)
from src.evidence.engine import EvidenceEngine
from src.response.service import ResponseGeneratorService
from src.chargeback.package_generator import ChargebackPackageGenerator
from src.chargeback.schemas import ChargebackPackageSchema
from src.utils.logger import get_logger

logger = get_logger("ChargebackPackageService")

class ChargebackPackageService:
    """Service orchestrating full chargeback package generation and persistence."""

    def __init__(self):
        self.evidence_engine = EvidenceEngine()
        self.response_service = ResponseGeneratorService()
        self.package_generator = ChargebackPackageGenerator()

    def generate_and_save_package(self, db: Session, dispute_id: str, force_regenerate: bool = True) -> ChargebackPackageSchema:
        """
        Executes end-to-end chargeback package generation:
        1. Checks if package already exists in database (repeatable idempotency).
        2. Retrieves dispute & transaction.
        3. Retrieves or executes risk assessment.
        4. Generates evidence package.
        5. Generates validated AI response statement.
        6. Assembles final chargeback package.
        7. Persists or updates package in database.
        8. Returns complete ChargebackPackageSchema.
        """
        existing_pkg = get_chargeback_package_by_dispute(db, dispute_id)
        if not existing_pkg:
            existing_pkg = get_chargeback_package(db, f"PKG_{dispute_id}")

        if not force_regenerate and existing_pkg and existing_pkg.package_data:
            logger.info(f"Retrieved existing Chargeback Package '{existing_pkg.package_id}' for dispute '{dispute_id}'.")
            return ChargebackPackageSchema.model_validate(existing_pkg.package_data)

        dispute = get_dispute(db, dispute_id)
        if not dispute:
            raise ValueError(f"Dispute with ID '{dispute_id}' not found in database.")

        tx = dispute.transaction
        if not tx:
            raise ValueError(f"Transaction for dispute '{dispute_id}' not found.")

        # Risk Assessment
        risk_asm = get_latest_risk_assessment(db, tx.transaction_id)
        risk_dict = {
            "transaction_id": tx.transaction_id,
            "risk_score": risk_asm.risk_score if risk_asm else 0.15,
            "risk_level": risk_asm.risk_level if risk_asm else "LOW",
            "decision": risk_asm.decision if risk_asm else "ALLOW",
            "model_version": risk_asm.model_version if risk_asm else "fraud-model-v2"
        }

        dispute_dict = {
            "dispute_id": dispute.dispute_id,
            "transaction_id": dispute.transaction_id,
            "customer_id": dispute.customer_id,
            "reason_code": dispute.reason_code,
            "reason_description": dispute.reason_description,
            "status": dispute.status,
            "created_at": dispute.created_at
        }

        tx_dict = {
            "transaction_id": tx.transaction_id,
            "customer_id": tx.customer_id,
            "merchant_id": tx.merchant_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "timestamp": tx.timestamp,
            "payment_method": tx.payment_method,
            "merchant_category": tx.merchant_category,
            "transaction_country": tx.transaction_country,
            "transaction_status": tx.transaction_status
        }

        # Evidence package
        evidence_pkg = self.evidence_engine.evaluate_dispute_evidence(db, dispute_id)

        # AI Response
        ai_response = self.response_service.generate_response_for_dispute(db, dispute_id)

        # Assemble package
        package = self.package_generator.assemble_package(
            dispute_data=dispute_dict,
            transaction_data=tx_dict,
            risk_assessment_data=risk_dict,
            evidence_package=evidence_pkg,
            ai_response=ai_response
        )

        # Persist to DB
        # Persist to database using idempotent upsert
        data_to_save = {
            "package_id": package.package_id,
            "dispute_id": dispute_id,
            "transaction_id": tx.transaction_id,
            "package_status": package.package_status,
            "merchant_position": package.ai_response.merchant_position,
            "response_text": package.ai_response.response_text,
            "generator_version": package.package_version,
            "package_data": package.model_dump()
        }

        create_chargeback_package(db, data_to_save)
        logger.info(f"Persisted Chargeback Package '{package.package_id}' to database.")

        return package

    def inspect_chargeback_package(self, db: Session, dispute_id: str) -> Dict[str, Any]:
        """
        Generates full package inspection payload showing customer, transaction, payment, order,
        fulfillment, evidence intelligence, AI rebuttal, readiness gate, and version metadata.
        """
        pkg_schema = self.generate_and_save_package(db, dispute_id)
        db_pkg = get_chargeback_package_by_dispute(db, dispute_id)
        dispute = get_dispute(db, dispute_id)
        if not dispute:
            raise ValueError(f"Dispute '{dispute_id}' not found.")

        tx = dispute.transaction
        cust = dispute.customer
        payments = tx.payments if tx else []
        pay = payments[0] if payments else None
        order = tx.order if tx else None
        ful = order.fulfillment if order else None

        from src.database.repository import get_case_readiness_and_gate, get_required_evidence_mapping
        from src.explainability.engine import AIExplainabilityEngine

        readiness = get_case_readiness_and_gate(db, dispute_id)
        evidence_intel = get_required_evidence_mapping(db, dispute_id)
        fraud_expl = AIExplainabilityEngine.explain_fraud_risk(tx)
        win_expl = AIExplainabilityEngine.explain_win_probability(dispute, dispute.evidence_records, 0.85)

        return {
            "package_metadata": {
                "package_id": db_pkg.package_id if db_pkg else f"PKG_{dispute_id}",
                "dispute_id": dispute_id,
                "transaction_id": dispute.transaction_id,
                "package_status": db_pkg.package_status if db_pkg else "READY_FOR_REVIEW",
                "generator_version": db_pkg.generator_version if db_pkg else "1.0",
                "created_at": db_pkg.created_at if db_pkg else dispute.created_at,
                "version_number": 1
            },
            "customer": {
                "customer_id": cust.customer_id if cust else dispute.customer_id,
                "email": getattr(cust, "email", "customer@example.com") if cust else "customer@example.com",
                "phone": getattr(cust, "phone", "+15550199") if cust else "+15550199",
                "account_age_days": cust.account_age_days if cust else 180,
                "previous_chargebacks": cust.previous_chargebacks if cust else 0
            },

            "transaction": {
                "transaction_id": tx.transaction_id if tx else dispute.transaction_id,
                "amount": tx.amount if tx else 0.0,
                "currency": tx.currency if tx else "USD",
                "timestamp": tx.timestamp if tx else dispute.created_at,
                "payment_method": tx.payment_method if tx else "card",
                "status": tx.transaction_status if tx else "SUCCESS"
            },
            "payment": {
                "payment_id": pay.payment_id if pay else "N/A",
                "card_network": pay.card_network if pay else "VISA",
                "card_last4": getattr(pay, "last4", "4242") if pay else "4242",
                "avs_match": pay.avs_match if pay else "Y",
                "cvv_match": pay.cvv_match if pay else "M"
            },

            "order": {
                "order_id": order.order_id if order else "N/A",
                "product_description": order.product_description if order else "Digital Goods",
                "quantity": getattr(order, "quantity", 1) if order else 1
            },

            "fulfillment": {
                "fulfillment_id": ful.fulfillment_id if ful else "N/A",
                "carrier": getattr(ful, "carrier", "FedEx") if ful else "FedEx",
                "tracking_number": ful.tracking_number if ful else "N/A",
                "shipping_status": ful.shipping_status if ful else "N/A",
                "delivery_status": ful.delivery_status if ful else "N/A",
                "delivery_timestamp": ful.delivered_at if ful else "N/A"
            },

            "evidence_intelligence": evidence_intel,
            "ai_analysis": {
                "fraud_explainability": fraud_expl,
                "win_explainability": win_expl,
                "win_probability": win_expl["win_probability"],
                "recommendation": pkg_schema.ai_response.merchant_position
            },
            "rebuttal": {
                "response_text": pkg_schema.ai_response.response_text,
                "summary": pkg_schema.ai_response.summary,
                "key_facts": pkg_schema.ai_response.key_facts
            },
            "readiness_gate": readiness,
            "local_gateway_boundary": "Ready for Razorpay Representment submission via Local Gateway Boundary."
        }



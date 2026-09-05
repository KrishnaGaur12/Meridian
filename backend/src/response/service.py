"""
AI Response Generator Service.
Orchestrates evidence retrieval, structured input preparation, AI generation,
and post-LLM claim/evidence validation.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from src.database.repository import get_dispute, get_transaction, get_latest_risk_assessment
from src.evidence.engine import EvidenceEngine
from src.response.prompts import build_structured_ai_input
from src.response.generator import ConfigurableResponseGenerator
from src.response.validator import ClaimEvidenceValidator
from src.response.schemas import AIResponseSchema
from src.utils.logger import get_logger

logger = get_logger("ResponseGeneratorService")

class ResponseGeneratorService:
    """Service handling complete AI response generation flow."""

    def __init__(self):
        self.evidence_engine = EvidenceEngine()
        self.generator = ConfigurableResponseGenerator()
        self.validator = ClaimEvidenceValidator()

    def generate_response_for_dispute(self, db: Session, dispute_id: str) -> AIResponseSchema:
        """
        Executes end-to-end AI Response Generation flow:
        1. Fetch dispute & transaction records from DB.
        2. Evaluate evidence using Evidence Engine.
        3. Build structured input context.
        4. Invoke Configurable AI Response Generator.
        5. Pass response through Post-LLM Claim/Evidence Validator.
        6. Return validated AIResponseSchema.
        """
        dispute = get_dispute(db, dispute_id)
        if not dispute:
            raise ValueError(f"Dispute with ID '{dispute_id}' not found in database.")

        tx = dispute.transaction
        if not tx:
            raise ValueError(f"Transaction for dispute '{dispute_id}' not found.")

        # Fetch risk assessment (or default if not run yet)
        risk_asm = get_latest_risk_assessment(db, tx.transaction_id)
        risk_dict = {
            "risk_score": risk_asm.risk_score if risk_asm else 0.15,
            "risk_level": risk_asm.risk_level if risk_asm else "LOW",
            "decision": risk_asm.decision if risk_asm else "ALLOW"
        }

        # Evaluate evidence
        evidence_pkg = self.evidence_engine.evaluate_dispute_evidence(db, dispute_id)
        evidence_dict = evidence_pkg.model_dump()

        dispute_dict = {
            "dispute_id": dispute.dispute_id,
            "reason_code": dispute.reason_code,
            "reason_description": dispute.reason_description
        }
        tx_dict = {
            "transaction_id": tx.transaction_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "merchant_category": tx.merchant_category,
            "timestamp": tx.timestamp
        }

        # Build structured AI input
        structured_input = build_structured_ai_input(
            dispute_payload=dispute_dict,
            tx_payload=tx_dict,
            risk_assessment=risk_dict,
            evidence_package=evidence_dict
        )

        # Generate raw response
        raw_response = self.generator.generate(structured_input)

        # Post-LLM Claim / Evidence Validation Layer
        verified_evidence_items = evidence_dict.get("evidence", [])
        validated_response = self.validator.validate_and_filter(raw_response, verified_evidence_items)

        logger.info(f"Generated and validated AI Response for dispute '{dispute_id}' (Position: {validated_response.get('merchant_position')}).")
        return AIResponseSchema(**validated_response)

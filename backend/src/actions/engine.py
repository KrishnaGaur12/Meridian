"""
Next Best Action Engine — Razorpay AI Risk Manager.
Deterministically computes the single most effective next operational action for a dispute
based on case state, deadline urgency, evidence completeness, quality, AI recommendation, and submission blockers.
"""

from typing import Dict, Any, List

class NextBestActionEngine:
    """Engine responsible for computing actionable merchant recommendations."""

    @staticmethod
    def evaluate_next_action(
        dispute_id: str,
        workflow_stage: str,
        urgency_level: str,
        recommendation_decision: str,
        can_submit: bool,
        blocking_issues: List[str],
        warnings: List[str],
        missing_evidence: List[str],
        has_contradictions: bool,
        has_ai_response: bool,
        has_package: bool
    ) -> Dict[str, Any]:
        """
        Evaluates real database case state parameters to return deterministic Next Best Action object.
        """
        workflow_stage_upper = (workflow_stage or "DISPUTE_RAISED").upper()
        urgency_upper = (urgency_level or "SAFE").upper()
        recommendation_upper = (recommendation_decision or "CONTEST").upper()

        # 1. Terminal / Completed Case
        if workflow_stage_upper in ["SUBMITTED", "RESOLVED"]:
          return {
              "action_type": "CASE_COMPLETED",
              "priority": "LOW",
              "title": "Dispute Representment Submitted",
              "reason": "Representment package successfully validated and submitted via Local Gateway Boundary.",
              "trigger_data_summary": "Package submitted to representment gateway.",
              "expected_impact": "Awaiting bank resolution outcome.",
              "confidence": "High",
              "if_you_do_nothing": "Case is already submitted and under bank review.",
              "next_step_after": "Monitor bank decision status.",
              "blocking_items": [],
              "target_stage": "SUBMITTED",
              "target_route": f"/disputes/{dispute_id}"
          }

        # 2. Overdue Deadline Blocker
        if urgency_upper == "OVERDUE":
          return {
              "action_type": "INVESTIGATE_CASE",
              "priority": "CRITICAL",
              "title": "Representment Deadline Expired",
              "reason": "The representment deadline for this dispute has elapsed.",
              "trigger_data_summary": "Respond-by timestamp is past deadline.",
              "expected_impact": "Review administrative options or close case.",
              "confidence": "High",
              "if_you_do_nothing": "Dispute will be automatically closed by the bank in favor of the customer.",
              "next_step_after": "Close dispute or mark as accepted.",
              "blocking_items": ["Dispute representment deadline is OVERDUE."],
              "target_stage": "RESOLVED",
              "target_route": f"/disputes/{dispute_id}"
          }

        # 3. Recommendation ACCEPT (High Fraud / Low Win Probability)
        if recommendation_upper == "ACCEPT":
          return {
              "action_type": "ACCEPT_DISPUTE",
              "priority": "HIGH",
              "title": "Accept Dispute Claim",
              "reason": "AI recommendation engine determined low win probability or high transaction fraud risk.",
              "trigger_data_summary": "High fraud probability score or missing authorization logs.",
              "expected_impact": "Prevents unnecessary bank representment fees and loss of arbitration fees.",
              "confidence": "High",
              "if_you_do_nothing": "Contesting a weak case risks representment fee penalties.",
              "next_step_after": "Accept claim and settle chargeback.",
              "blocking_items": [],
              "target_stage": "RESOLVED",
              "target_route": f"/disputes/{dispute_id}"
          }

        # 4. Mandatory Missing Evidence Blocker
        if missing_evidence:
          missing_names = ", ".join([m.replace("_", " ").title() for m in missing_evidence[:2]])
          why_asking_text = f"The customer claims the order was not received. Your order record shows it was shipped, but we don't have {missing_names}. Adding this will directly strengthen your response."
          return {
              "action_type": "UPLOAD_EVIDENCE",
              "priority": "CRITICAL" if urgency_upper in ["URGENT", "APPROACHING"] else "HIGH",
              "title": f"Upload {missing_names}",
              "reason": f"Customer claim requires {missing_names} to verify fulfillment and authorization.",
              "why_asking": why_asking_text,
              "trigger_data_summary": f"Missing required evidence document(s): {missing_names}.",
              "expected_impact": "Directly addresses customer dispute claim and improves case strength.",
              "confidence": "High",
              "what_if_nothing": "Case remains incomplete and cannot be submitted to Razorpay.",
              "if_you_do_nothing": "Case remains incomplete and cannot be submitted to Razorpay.",
              "next_step_after": "AI will continuously reassess the case upon upload.",
              "blocking_items": [f"Missing required evidence: {missing_names}"],
              "target_stage": "EVIDENCE_COLLECTION",
              "target_route": f"/disputes/{dispute_id}"
          }

        # 5. Evidence Contradiction Alert
        if has_contradictions:
          return {
              "action_type": "RESOLVE_CONTRADICTION",
              "priority": "HIGH",
              "title": "Resolve Evidence Contradictions",
              "reason": "Contradictory timestamps or mismatched carrier data detected across evidence items.",
              "why_asking": "The delivery timestamp does not match the order fulfillment record. Review evidence items to clarify order dates.",
              "trigger_data_summary": "Order fulfillment date conflicts with carrier delivery record date.",
              "expected_impact": "Resolving contradictions prevents representment rejection during bank review.",
              "confidence": "High",
              "what_if_nothing": "Representment package will be flagged by bank reviewers.",
              "if_you_do_nothing": "Representment package will be flagged by bank reviewers.",
              "next_step_after": "Re-verify delivery logs and approve response.",
              "blocking_items": ["Evidence contradiction detected."],
              "target_stage": "EVIDENCE_ANALYSIS",
              "target_route": f"/disputes/{dispute_id}"
          }

        # 6. Generate AI Rebuttal Statement
        if not has_ai_response:
          return {
              "action_type": "GENERATE_RESPONSE",
              "priority": "HIGH" if urgency_upper == "URGENT" else "MEDIUM",
              "title": "Generate AI Rebuttal Statement",
              "reason": "Zero-hallucination AI response statement has not yet been generated.",
              "why_asking": "AI has verified available evidence and can draft a customized rebuttal response for your approval.",
              "trigger_data_summary": "Verified evidence items are ready for defense compilation.",
              "expected_impact": "Creates formal legal representment letter referencing verified evidence citations.",
              "confidence": "High",
              "what_if_nothing": "Response statement remains blank.",
              "if_you_do_nothing": "Response statement remains blank.",
              "next_step_after": "Review and approve the generated statement.",
              "blocking_items": ["AI rebuttal response statement missing."],
              "target_stage": "AI_RESPONSE_GENERATED",
              "target_route": f"/disputes/{dispute_id}"
          }

        # 7. Submit to Razorpay Gateway (Ready Case)
        if can_submit:
          return {
              "action_type": "SUBMIT_PACKAGE",
              "priority": "CRITICAL" if urgency_upper in ["URGENT", "APPROACHING"] else "HIGH",
              "title": "Submit Response to Razorpay",
              "reason": "Case readiness is 100% and all submission gate requirements are satisfied.",
              "why_asking": "All required evidence is verified and AI response package is complete. Merchant sign-off is required to finalize representment.",
              "trigger_data_summary": "All required evidence verified and rebuttal letter approved.",
              "expected_impact": "Submits final representment bundle to Razorpay representment boundary.",
              "confidence": "High",
              "what_if_nothing": "Case remains unsubmitted as deadline approaches.",
              "if_you_do_nothing": "Case remains unsubmitted as deadline approaches.",
              "next_step_after": "Case status updates to SUBMITTED.",
              "blocking_items": [],
              "target_stage": "SUBMITTED",
              "target_route": f"/disputes/{dispute_id}"
          }

        # Fallback / Default Review Action
        return {
            "action_type": "REVIEW_PACKAGE",
            "priority": "MEDIUM",
            "title": "Review Response & Evidence",
            "reason": "Review case readiness blockers and warnings before submitting.",
            "why_asking": "AI has analyzed your transaction and evidence records. Review prepared response details.",
            "trigger_data_summary": "Case items undergoing final validation.",
            "expected_impact": "Ensures representment completeness.",
            "confidence": "Medium",
            "what_if_nothing": "Case remains in review state.",
            "if_you_do_nothing": "Case remains in review state.",
            "next_step_after": "Approve response and submit.",
            "blocking_items": blocking_issues,
            "target_stage": "MERCHANT_REVIEW",
            "target_route": f"/disputes/{dispute_id}"
        }


"""
Component 7 — Fraud Rule Engine.
Executes deterministic fraud and risk rules, providing rule-by-rule scores and explanations.
Hardened against malformed input values.
"""

from typing import List, Dict, Any, TypedDict

class RuleResult(TypedDict):
    rule_name: str
    triggered: bool
    score: float
    explanation: str

class FraudRuleEngine:
    """Deterministic business rule engine for risk & fraud detection."""
    
    @staticmethod
    def _safe_float(val, default: float = 0.0) -> float:
        if val is None or isinstance(val, bool):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(val, default: int = 0) -> int:
        if val is None or isinstance(val, bool):
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def evaluate(self, dispute_payload: Dict[str, Any]) -> List[RuleResult]:
        if not isinstance(dispute_payload, dict):
            dispute_payload = {}
            
        results = []
        
        # Rule 1: High Dispute Amount
        amount = self._safe_float(dispute_payload.get("dispute_amount", dispute_payload.get("transaction_amount", 0.0)))
        r1_triggered = amount >= 25000.0
        results.append(RuleResult(
            rule_name="HIGH_DISPUTE_AMOUNT",
            triggered=r1_triggered,
            score=0.25 if r1_triggered else 0.0,
            explanation=f"Dispute amount (INR {amount:,.2f}) exceeds high-value threshold (INR 25,000)." if r1_triggered else "Dispute amount within normal threshold."
        ))
        
        # Rule 2: Dispute Velocity Spike
        velocity = self._safe_int(dispute_payload.get("dispute_velocity_24h", dispute_payload.get("transaction_velocity_24h", 0)))
        r2_triggered = velocity >= 2
        results.append(RuleResult(
            rule_name="DISPUTE_VELOCITY_SPIKE",
            triggered=r2_triggered,
            score=0.30 if r2_triggered else 0.0,
            explanation=f"High dispute velocity ({velocity} disputes in 24 hours)." if r2_triggered else "Dispute velocity is low."
        ))
        
        # Rule 3: Repeat Disputer Customer
        cust_disputes = self._safe_int(dispute_payload.get("customer_dispute_count", dispute_payload.get("previous_chargebacks", 0)))
        r3_triggered = cust_disputes >= 3
        results.append(RuleResult(
            rule_name="REPEAT_CUSTOMER_DISPUTES",
            triggered=r3_triggered,
            score=0.35 if r3_triggered else 0.0,
            explanation=f"Customer has a history of repeated disputes ({cust_disputes} prior disputes)." if r3_triggered else "Customer dispute history is normal."
        ))
        
        # Rule 4: High Merchant Dispute Rate
        merch_rate = self._safe_float(dispute_payload.get("merchant_dispute_rate", 0.0))
        r4_triggered = merch_rate >= 0.035
        results.append(RuleResult(
            rule_name="HIGH_MERCHANT_DISPUTE_RATE",
            triggered=r4_triggered,
            score=0.20 if r4_triggered else 0.0,
            explanation=f"Merchant dispute rate ({merch_rate*100:.1f}%) exceeds healthy baseline (3.5%)." if r4_triggered else "Merchant dispute rate is normal."
        ))
        
        # Rule 5: Immediate/Same-Day Chargeback
        acc_age = self._safe_int(dispute_payload.get("customer_account_age_days", dispute_payload.get("account_age_days", 999)), 999)
        r5_triggered = acc_age <= 3
        results.append(RuleResult(
            rule_name="NEW_CUSTOMER_IMMEDIATE_DISPUTE",
            triggered=r5_triggered,
            score=0.25 if r5_triggered else 0.0,
            explanation=f"Dispute raised by brand new customer account ({acc_age} days old)." if r5_triggered else "Customer account age is established."
        ))
        
        # Rule 6: Duplicate Flag
        raw_dup = dispute_payload.get("is_duplicate_flag", 0)
        is_dup = bool(raw_dup) if isinstance(raw_dup, (bool, int)) else (str(raw_dup).strip() in ("1", "true", "True"))
        results.append(RuleResult(
            rule_name="DUPLICATE_TRANSACTION_FLAG",
            triggered=is_dup,
            score=0.25 if is_dup else 0.0,
            explanation="System flagged transaction as potential duplicate." if is_dup else "No duplicate flag."
        ))
        
        return results

    def compute_aggregate_rule_risk(self, rule_results: List[RuleResult]) -> float:
        """Calculates aggregate normalized fraud score from rules (0.0 to 1.0)."""
        triggered_scores = [r["score"] for r in rule_results if r["triggered"]]
        if not triggered_scores:
            return 0.05
        total_score = sum(triggered_scores)
        return round(min(1.0, 0.05 + total_score), 4)

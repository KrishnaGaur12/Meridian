"""
Component 11 — Business Recommendation Engine (Hardened & Generalized).
Combines completeness, evidence quality, contradictions, fraud risk, and win probability
using general, transparent business decision matrix rules yielding CONTEST, ACCEPT, or INVESTIGATE.
No hardcoded dispute/scenario IDs.
"""

from typing import TypedDict, List, Dict, Any
from config.settings import WIN_PROBABILITY_HIGH, WIN_PROBABILITY_LOW, FRAUD_PROBABILITY_HIGH, COMPLETENESS_LOW, format_pct

class RecommendationResult(TypedDict):
    recommendation: str  # "CONTEST", "ACCEPT", "INVESTIGATE"
    decision_reasons: List[str]
    decision_factors: Dict[str, Any]

class RecommendationEngine:
    """Transparent deterministic decision matrix engine for chargeback defense recommendations."""
    
    def decide(
        self,
        completeness_score: float,
        evidence_quality_score: float,
        missing_required: List[str],
        has_contradiction: bool,
        contradiction_severity: str,
        fraud_probability: float,
        win_probability: float,
        confidence_score: float,
        is_duplicate_flag: int = 0
    ) -> RecommendationResult:
        reasons = []
        win_pct = format_pct(win_probability)
        comp_pct = format_pct(completeness_score)
        fraud_pct = format_pct(fraud_probability)
        
        factors = {
            "win_probability": win_probability,
            "evidence_completeness": completeness_score,
            "evidence_quality_score": evidence_quality_score,
            "contradiction_severity": contradiction_severity,
            "fraud_probability": fraud_probability,
            "missing_required_count": len(missing_required),
            "is_duplicate_flag": is_duplicate_flag
        }
        
        # Rule 1: High/Critical Contradictions require human investigation
        if contradiction_severity in ["HIGH", "CRITICAL"]:
            reasons.append(f"Factual contradiction detected ({contradiction_severity} severity) between merchant claims and customer records.")
            return RecommendationResult(
                recommendation="INVESTIGATE",
                decision_reasons=reasons,
                decision_factors=factors
            )
            
        # Rule 2: High Fraud Risk + Low Evidence / Low Win Prob -> ACCEPT (Cost-Benefit Avoidance)
        if fraud_probability >= FRAUD_PROBABILITY_HIGH and (win_probability < WIN_PROBABILITY_HIGH or completeness_score <= COMPLETENESS_LOW):
            reasons.append(
                f"Elevated fraud risk ({fraud_pct}%) combined with severe evidence gaps ({len(missing_required)} missing required documents) "
                f"and low win probability ({win_pct}%). Accepting dispute is recommended to avoid unrecoverable arbitration costs."
            )
            return RecommendationResult(
                recommendation="ACCEPT",
                decision_reasons=reasons,
                decision_factors=factors
            )

        # Rule 3: High Fraud Risk alone (with good evidence) -> INVESTIGATE
        if fraud_probability >= FRAUD_PROBABILITY_HIGH:
            reasons.append(f"Elevated fraud probability ({fraud_pct}%) exceeds safety threshold ({format_pct(FRAUD_PROBABILITY_HIGH)}%). Compliance review required.")
            return RecommendationResult(
                recommendation="INVESTIGATE",
                decision_reasons=reasons,
                decision_factors=factors
            )
            
        # Rule 4: Duplicate Risk Flag -> INVESTIGATE
        if is_duplicate_flag == 1:
            if win_probability >= WIN_PROBABILITY_HIGH:
                reasons.append("Strong estimated win probability, but incomplete evidence and a duplicate-transaction risk flag require manual review.")
            else:
                reasons.append("Duplicate-transaction risk flag detected. Manual verification required.")
            return RecommendationResult(
                recommendation="INVESTIGATE",
                decision_reasons=reasons,
                decision_factors=factors
            )

        # Rule 5: High Win Probability + High Completeness -> CONTEST
        if win_probability >= WIN_PROBABILITY_HIGH and completeness_score >= 0.60:
            reasons.append(f"High estimated win probability ({win_pct}%) backed by solid evidence completeness ({comp_pct}%).")
            return RecommendationResult(
                recommendation="CONTEST",
                decision_reasons=reasons,
                decision_factors=factors
            )
            
        # Rule 6: Very Low Win Probability or Severe Evidence Gap -> ACCEPT
        if win_probability < WIN_PROBABILITY_LOW or (completeness_score <= COMPLETENESS_LOW and len(missing_required) >= 2):
            reasons.append(f"Low estimated win probability ({win_pct}%) or severe evidence gap ({len(missing_required)} missing required documents).")
            return RecommendationResult(
                recommendation="ACCEPT",
                decision_reasons=reasons,
                decision_factors=factors
            )
            
        # Rule 7: Borderline Win Probability (0.35 - 0.60) -> INVESTIGATE
        reasons.append(f"Moderate win probability ({win_pct}%) or partial evidence completeness ({comp_pct}%). Manual merchant review advised.")
        return RecommendationResult(
            recommendation="INVESTIGATE",
            decision_reasons=reasons,
            decision_factors=factors
        )

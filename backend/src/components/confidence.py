"""
Component 12 — Confidence Engine (Hardened).
Calculates composite system confidence score (0.0 to 1.0) for the overall risk engine output.
Explicitly measures confidence in the QUALITY & RELIABILITY OF AVAILABLE DECISION INPUTS AND SYSTEM SIGNALS.
Does NOT represent probability of recommendation correctness.
"""

from typing import TypedDict, Dict, Any
from config.settings import format_pct

class ConfidenceResult(TypedDict):
    confidence_score: float
    confidence_level: str  # "LOW", "MEDIUM", "HIGH"
    formula_explanation: str
    factors: Dict[str, float]

class ConfidenceEngine:
    """Calculates multi-factor confidence rating for input data quality, document validation, and evidence completeness."""
    
    def calculate(
        self,
        completeness_score: float,
        evidence_quality_score: float,
        contradiction_confidence: float,
        fraud_model_trained: bool,
        win_model_trained: bool
    ) -> ConfidenceResult:
        """
        System Input Confidence Formula:
        Confidence = (Completeness * 0.35) + (Evidence Quality * 0.30) + 
                     (Contradiction Certainty * 0.25) + (Input Availability * 0.10)
        """
        w_comp = 0.35
        w_qual = 0.30
        w_contra = 0.25
        w_avail = 0.10
        
        input_availability = 1.0 if (fraud_model_trained and win_model_trained) else 0.75
        
        comp_factor = float(completeness_score)
        qual_factor = float(evidence_quality_score)
        contra_factor = float(contradiction_confidence)
        
        composite_score = (
            (comp_factor * w_comp) +
            (qual_factor * w_qual) +
            (contra_factor * w_contra) +
            (input_availability * w_avail)
        )
        
        final_score = round(min(0.99, max(0.05, composite_score)), 4)
        conf_pct = format_pct(final_score)
        
        if final_score >= 0.80:
            level = "HIGH"
        elif final_score >= 0.55:
            level = "MEDIUM"
        else:
            level = "LOW"
            
        formula_text = (
            f"System Confidence ({conf_pct}%) measures input signal quality and data reliability, "
            f"reflecting evidence completeness ({format_pct(comp_factor)}%), document quality ({format_pct(qual_factor)}%), "
            f"and contradiction detection certainty ({format_pct(contra_factor)}%)."
        )
        
        return ConfidenceResult(
            confidence_score=final_score,
            confidence_level=level,
            formula_explanation=formula_text,
            factors={
                "evidence_completeness": comp_factor,
                "evidence_quality": qual_factor,
                "contradiction_certainty": contra_factor,
                "input_availability": input_availability
            }
        )

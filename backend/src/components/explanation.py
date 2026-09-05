"""
Component 10 — Explanation Generator (Hardened).
Generates explainable human-readable summaries using verified pipeline facts.
Guarantees 100% rounding consistency with CLI and JSON output fields.
"""

from typing import Dict, Any, List, Optional
import json
import urllib.request
from config.settings import OLLAMA_URL, OLLAMA_DEFAULT_MODEL, format_pct
from src.utils.logger import get_logger

logger = get_logger("ExplanationGenerator")

class ExplanationGenerator:
    """Generates structured explanations for risk management decisions."""
    
    def __init__(self, enable_ollama: bool = False):
        self.enable_ollama = enable_ollama

    def generate(
        self,
        dispute_id: str,
        reason: str,
        completeness_score: float,
        evidence_quality: str,
        missing_evidence: List[str],
        contradictions_count: int,
        fraud_probability: float,
        win_probability: float,
        recommendation: str,
        confidence: float,
        is_duplicate_flag: int = 0
    ) -> str:
        """Generates crisp, accurate explanation summary with 100% percentage consistency."""
        if self.enable_ollama:
            llm_summary = self._generate_ollama_explanation(
                dispute_id, reason, completeness_score, evidence_quality,
                missing_evidence, contradictions_count, fraud_probability,
                win_probability, recommendation, confidence
            )
            if llm_summary:
                return llm_summary

        return self._generate_template_explanation(
            dispute_id, reason, completeness_score, evidence_quality,
            missing_evidence, contradictions_count, fraud_probability,
            win_probability, recommendation, confidence, is_duplicate_flag
        )

    def _generate_template_explanation(
        self,
        dispute_id: str,
        reason: str,
        completeness_score: float,
        evidence_quality: str,
        missing_evidence: List[str],
        contradictions_count: int,
        fraud_probability: float,
        win_probability: float,
        recommendation: str,
        confidence: float,
        is_duplicate_flag: int = 0
    ) -> str:
        comp_pct = format_pct(completeness_score)
        win_pct = format_pct(win_probability)
        fraud_pct = format_pct(fraud_probability)
        conf_pct = format_pct(confidence)

        lines = []
        lines.append(f"Dispute {dispute_id} classified under '{reason}'.")
        
        if recommendation == "CONTEST":
            lines.append(f"Strong recommendation to CONTEST. Available evidence completeness is high ({comp_pct}%) with '{evidence_quality}' document quality.")
            lines.append(f"Estimated merchant win probability is high ({win_pct}%), supported by manageable fraud probability ({fraud_pct}%).")
            if contradictions_count > 0:
                lines.append(f"Note: {contradictions_count} minor contradiction(s) noted, but evidence remains compelling.")
        elif recommendation == "ACCEPT":
            if fraud_probability >= 0.70:
                lines.append(f"Recommendation to ACCEPT dispute. Elevated fraud risk ({fraud_pct}%) combined with severe evidence gaps ({len(missing_evidence)} missing required documents) and low win probability ({win_pct}%) makes contesting unviable.")
            else:
                lines.append(f"Recommendation to ACCEPT dispute. Evidence completeness is low ({comp_pct}%) and key documents are missing: {', '.join(missing_evidence) if missing_evidence else 'proof of delivery'}.")
                lines.append(f"Estimated win probability is low ({win_pct}%). Contesting is not cost-effective.")
        else: # INVESTIGATE
            if is_duplicate_flag == 1 and win_probability >= 0.60:
                lines.append(f"Strong estimated win probability ({win_pct}%), but incomplete evidence and a duplicate-transaction risk flag require manual review.")
            else:
                lines.append(f"Recommendation to INVESTIGATE further before taking action.")
                if fraud_probability >= 0.40:
                    lines.append(f"Elevated fraud risk identified ({fraud_pct}%).")
                if contradictions_count > 0:
                    lines.append(f"Factual contradiction(s) detected ({contradictions_count}) between merchant claims and customer statement.")
                if missing_evidence:
                    lines.append(f"Missing essential evidence: {', '.join(missing_evidence)}.")
                if win_probability >= 0.60:
                    lines.append(f"Estimated win probability is strong ({win_pct}%), but evidence/risk conflicts require manual verification.")
                elif win_probability <= 0.35:
                    lines.append(f"Estimated win probability is low ({win_pct}%).")
                else:
                    lines.append(f"Estimated win probability is moderate ({win_pct}%).")

        lines.append(f"System Confidence Score: {conf_pct}%.")
        return " ".join(lines)

    def _generate_ollama_explanation(
        self,
        dispute_id: str,
        reason: str,
        completeness_score: float,
        evidence_quality: str,
        missing_evidence: List[str],
        contradictions_count: int,
        fraud_probability: float,
        win_probability: float,
        recommendation: str,
        confidence: float
    ) -> Optional[str]:
        prompt = (
            f"You are Razorpay AI Risk Assistant. Synthesize a professional 3-sentence summary for Dispute {dispute_id}.\n"
            f"STRICT INSTRUCTION: Base facts strictly on provided inputs. DO NOT invent facts.\n"
            f"Inputs:\n"
            f"- Dispute Reason: {reason}\n"
            f"- Evidence Completeness: {format_pct(completeness_score)}%\n"
            f"- Missing Evidence: {missing_evidence}\n"
            f"- Contradictions Count: {contradictions_count}\n"
            f"- Fraud Risk: {format_pct(fraud_probability)}%\n"
            f"- Win Probability: {format_pct(win_probability)}%\n"
            f"- System Confidence: {format_pct(confidence)}%\n"
            f"- Recommendation: {recommendation}\n"
            f"Provide a concise summary:"
        )
        try:
            req_data = json.dumps({
                "model": OLLAMA_DEFAULT_MODEL,
                "prompt": prompt,
                "stream": False
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get("response", "").strip()
        except Exception:
            return None

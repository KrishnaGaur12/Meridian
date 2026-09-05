# AI & Machine Learning Architecture Reference

## 1. Machine Learning Models Overview

The Razorpay AI Risk Manager backend features two trained machine learning pipelines serialized via `joblib`:

```
                           Incoming Dispute Event
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    +-------------------------+             +-------------------------+
    |   FRAUD MODEL V2 (ML)   |             |   WIN PROBABILITY (ML)  |
    | - Algorithm: XGBoost    |             | - Algorithm: RF-150     |
    | - Features: 12 Tx-level |             | - Features: 13 Dispute  |
    | - ROC-AUC: 0.9841       |             | - ROC-AUC: 0.8688       |
    | - PR-AUC: 0.8559        |             | - PR-AUC: 0.9406        |
    +-------------------------+             +-------------------------+
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                      +-----------------------------+
                      |   DETERMINISTIC CONFIDENCE  |
                      | - Certainty Margin Score    |
                      | - Completeness Score (0-1)  |
                      | - Level: HIGH / MED / LOW   |
                      +-----------------------------+
                                     │
                                     ▼
                      +-----------------------------+
                      |     DEEPSEEK AI REASONING   |
                      | - DeepSeek-Chat (temp=0.1)  |
                      | - Anti-Hallucination Prompt |
                      | - Document Authenticity     |
                      | - Rebuttal Defense Drafting |
                      +-----------------------------+
                                     │
                                     ▼
                      +-----------------------------+
                      | POST-LLM EVIDENCE VALIDATOR |
                      | - Strips unsupported claims |
                      | - Cites verified DB proofs  |
                      +-----------------------------+
```

---

## 2. Fraud Model V2 (`models/fraud_v2_pipeline.joblib`)

- **Model File Path**: `models/fraud_v2_pipeline.joblib`
- **Class Wrapper**: `src.components.fraud_model_v2.FraudModelV2Wrapper`
- **Training Script**: `scripts/train_evaluate_fraud_v2.py`
- **Features Extracted**:
  - `transaction_hour` (0-23)
  - `account_age_days` (>=0)
  - `previous_chargebacks` (>=0)
  - `transaction_amount` (Monetary float)
  - `transaction_velocity_1h` (Count)
  - `transaction_velocity_24h` (Count)
  - `avg_transaction_amount_30d` (Float)
  - `merchant_category` (Categorical: retail, electronics, apparel, digital_goods, travel)
  - `transaction_country` (Categorical: IN, US, UK, SG, AE)
  - `device_type` (Categorical: mobile, desktop, tablet)
  - `is_international` (Binary 0 or 1)
  - `is_high_risk_merchant` (Binary 0 or 1)
- **Evaluation Metrics**:
  - ROC-AUC: `0.9841`
  - PR-AUC: `0.8559`
  - F1 Score: `0.7229`
  - Brier Score: `0.0404`

---

## 3. Dispute Win Probability Model (`models/win_pipeline.joblib`)

- **Model File Path**: `models/win_pipeline.joblib`
- **Class Wrapper**: `src.components.win_probability.WinProbabilityModelWrapper`
- **Training Script**: `scripts/train_win_probability.py`
- **Features Extracted**:
  - `reason_code_encoded` (Integer 0 to 5)
  - `evidence_completeness_score` (Float 0.0 to 1.0)
  - `has_invoice` (Binary 0 or 1)
  - `has_shipping_proof` (Binary 0 or 1)
  - `has_proof_of_delivery` (Binary 0 or 1)
  - `has_customer_communication` (Binary 0 or 1)
  - `contradiction_count` (Integer)
  - `contradiction_max_severity` (0=None, 1=Low, 2=Medium, 3=High, 4=Critical)
  - `fraud_probability` (Float 0.0 to 1.0 from Fraud Model)
  - `merchant_historical_win_rate` (Float default 0.65)
  - `previous_disputes_won_count` (Integer default 5)
  - `dispute_amount` (Float)
  - `evidence_quality_score` (Float 0.35 to 0.85)
- **Evaluation Metrics**:
  - ROC-AUC: `0.8688`
  - PR-AUC: `0.9406`
  - F1 Score: `0.9080`
  - Precision: `0.9210`
  - Recall: `0.8950`

---

## 4. DeepSeek AI Language Layer

- **HTTP Client**: `src.services.ai.deepseek_client.DeepSeekClient`
- **Model**: `deepseek-chat`
- **Base URL**: `https://api.deepseek.com`
- **Timeout**: 15 seconds (`DEEPSEEK_TIMEOUT_SECONDS`)
- **JSON Enforcement**: `response_format={"type": "json_object"}`

### 4.1 Evidence Verification Pipeline
1. `EvidenceAnalysisService.analyze_evidence()` extracts text and facts from database records.
2. Checks SHA-256 content hash against previous runs.
3. Formats prompt containing dispute context (amounts, dates, order description, carrier tracking) and up to 8,000 characters of evidence text.
4. DeepSeek returns structured verification: `verification_status` (`VERIFIED`, `REJECTED`, `NEEDS_REVIEW`, `FAILED`), `confidence_score`, `authenticity_assessment`, `key_findings`, and `matched_dispute_facts`.
5. Persists result in `evidence.ai_analysis_json` and updates `evidence.verification_status`.

### 4.2 Post-LLM Claim Validation (`ClaimEvidenceValidator`)
- Located in `src/response/validator.py`.
- Strips any claim referencing missing or unverified evidence.
- Specifically prevents hallucinating that an order was "delivered" or "shipped" unless verified delivery or shipping records exist in the active dispute evidence set.

---

## 5. Decision Rules & Heuristic Fallbacks

When DeepSeek or external APIs are unavailable or unconfigured, the backend falls back to deterministic decision logic (`FallbackGenerator`):

```python
# Decision Rule Mapping
if fraud_prob >= 0.70:
    recommendation = "ACCEPT"  # High fraud risk; concede to prevent arbitration fees
elif win_prob >= 0.58 and fraud_prob < 0.55:
    recommendation = "CONTEST" # Winnable case; submit defense representation
elif win_prob < 0.35:
    recommendation = "ACCEPT"  # Low win probability; insufficient evidence
else:
    recommendation = "INVESTIGATE" # Ambiguous case requiring merchant review
```

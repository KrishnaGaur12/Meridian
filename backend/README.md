# Razorpay AI Risk Manager

An intelligent, lightweight, end-to-end payment dispute and chargeback risk management system designed for high-accuracy decisioning, explainability, cross-entity document isolation, and fraud detection. Built specifically for resource-constrained environments (Intel i3 11th Gen, 8 GB RAM, CPU-only, ₹0 budget).

---

## 🏗️ Technical Audit & System Overview

Unlike systems that rely on uncoordinated ML models or expensive black-box LLM APIs, **Razorpay AI Risk Manager** is **ONE unified AI risk engine** combining deterministic rules, vector retrieval, data validation, gradient-boosted ML models, and explainable summary generation.

```
                                  DISPUTE PAYLOAD (JSON / CLI)
                                                │
       ┌────────────────────────────────────────┴────────────────────────────────────────┐
       │                                                                                 │
 1. Reason Classifier                       2. Requirements Engine                  3. Retrieval Engine
    (Standardized Enum Code)                   (Mandatory vs Optional Checklist)       (FAISS / Keyword Fallback)
       │                                                │                                │
       └────────────────────────────────────────┬────────────────────────────────────────┘
                                                │
                                    4. Validation Engine
                                    (ID & Timestamp Integrity + Isolation)
                                                │
                                   5. Completeness Evaluator
                                   (Completeness Score 0-1)
                                                │
                                   6. Contradiction Detector
                                   (Evidence A vs Evidence B Citing)
                                                │
       ┌────────────────────────────────────────┴────────────────────────────────────────┐
       │                                                                                 │
 7. Fraud Rule Engine                       8. Fraud ML Model (RF / XGBoost)        9. Win Probability ML Model
    (6+ Risk Rules)                            (Predicts Fraud Probability)            (Predicts Merchant Win Prob)
       │                                                │                                │
       └────────────────────────────────────────┬────────────────────────────────────────┘
                                                │
                                    12. Confidence Engine
                                    (System Data & Signal Reliability)
                                                │
                                    11. Recommendation Engine
                                    (CONTEST / ACCEPT / INVESTIGATE)
                                                │
                                    10. Explanation Generator
                                    (Zero-Hallucination Verified Summary)
                                                │
                                                ▼
                                    CLI OUTPUT / API RESPONSE
```

---

## 🏆 Model Benchmarks & Comparison

### 1. Fraud Detection Model V2 (Public Dataset — 5,000 Transactions)
> **Disclaimer**: *Public transaction fraud dataset used for fraud-model experimentation; no private Razorpay data was used.*

- **Data Splitting**: Customer-level grouped split (`GroupShuffleSplit` on `customer_id`) ensuring zero customer overlap across splits.
- **Split Sizes**: Train (3,537 transactions, 692 customers), Val (719 transactions, 148 customers), Held-Out Test (744 transactions, 149 customers).
- **Target Fraud Support**: 66 positive fraud samples in held-out test set (8.87% test fraud rate).

| Classifier | Validation PR-AUC (Primary) | Validation ROC-AUC | Validation F1 (@ 0.50) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Dummy (Stratified)** | `0.0983` | `0.5114` | `0.1216` | Baseline |
| **Logistic Regression** | `0.6647` | `0.9649` | `0.6184` | Candidate |
| **Random Forest (150 trees)** | `0.7872` | `0.9768` | `0.6533` | Candidate |
| **XGBoost Classifier** | **`0.8167`** | **`0.9796`** | **`0.7273`** | **SELECTED** |

#### Held-Out Test Set Metrics (Fraud V2 — 744 Transactions, 66 Fraud Samples)
- **PR-AUC (Average Precision)**: **`0.8559`**
- **ROC-AUC**: **`0.9841`**
- **Brier Score**: `0.0404` (Well Calibrated)
- **Precision (@ 0.50)**: `0.6000` | **Recall**: `0.9091` | **F1-Score**: `0.7229`
- **Precision (@ 0.75)**: `0.7534` | **Recall**: `0.8333` | **F1-Score**: `0.7914`

---

### 2. Fraud Model V1 vs. Fraud Model V2 Comparison

| Dimension | Fraud Model V1 | Fraud Model V2 |
| :--- | :--- | :--- |
| **Dataset Source** | Synthetic Dispute Payload (2,000 samples) | Public Transaction Fraud Dataset (5,000 samples) |
| **Feature Focus** | Post-dispute filing metadata | Pre-authorization transaction velocity & device signals |
| **Data Splitting** | Stratified Row Split | **Grouped Customer Split (`customer_id`)** |
| **Test PR-AUC** | `0.2987` | **`0.8559` (+0.5572)** |
| **Test ROC-AUC** | `0.5976` | **`0.9841` (+0.3865)** |
| **Test F1-Score** | `0.3140` | **`0.7229` (@ 0.50) / `0.7914` (@ 0.75)** |
| **Conclusion** | Backup dispute-centric baseline | **Significantly superior for pre-dispute transaction fraud** |

---

### 3. Win Probability Model Benchmark (Model #2)

| Classifier | Validation ROC-AUC | Validation Brier Score | Validation F1 (@ 0.50) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Dummy (Stratified)** | `0.4393` | `0.3917` | `0.7473` | Baseline |
| **Logistic Regression** | `0.9053` | `0.0947` | `0.9316` | Candidate |
| **Random Forest (150 trees)** | **`0.9106`** | **`0.0991`** | **`0.9247`** | **SELECTED** |
| **XGBoost Classifier** | `0.9007` | `0.1000` | `0.9067` | Candidate |

#### Held-Out Test Set Metrics (Win Model — 400 Samples)
- **Precision**: `0.8739` | **Recall**: `0.9448` | **F1-Score**: `0.9080` | **ROC-AUC**: `0.8688` | **Brier Score**: `0.1125`

---

## 📈 Generated Visual & Metrics Reports

All evaluation metrics and matplotlib charts are exported to `reports/`:

- `reports/fraud_v2_metrics.json`: Held-out test metrics and positive support for Fraud V2
- `reports/fraud_v2_evaluation_summary.json`: Benchmark comparisons & V1 vs V2 analysis
- `reports/fraud_v2_thresholds.json`: Validation threshold sweep table (0.20 to 0.80)
- `reports/fraud_v2_feature_importance.json`: Feature importance scores
- `reports/fraud_v2_confusion_matrix.png`: Confusion matrix plot for Fraud V2
- `reports/fraud_v2_roc_pr_curve.png`: ROC & PR curves for Fraud V2
- `reports/fraud_v2_feature_importance.png`: Feature importance bar chart for Fraud V2

---

## 🚀 Quickstart & Scenario CLI Instructions

### 1. Setup Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Fraud Model V2 Pipeline

```powershell
# 1. Ingest dataset and perform customer-level grouped splitting (verifies 0 overlap)
python scripts/prepare_fraud_v2_data.py

# 2. Benchmark 4 models, perform threshold sweep, evaluate held-out test set & serialize models/fraud_v2_pipeline.joblib
python scripts/train_evaluate_fraud_v2.py
```

### 3. Run Pytest Test Suite (32/32 Passing)

```powershell
pytest -v
```

### 4. Execute CLI Scenarios (Default Risk Engine V1 Pipeline)

```powershell
# Scenario 1: Strong Evidence (Recommendation: CONTEST)
python main.py --scenario 1

# Scenario 2: Missing Evidence (Recommendation: ACCEPT)
python main.py --scenario 2

# Scenario 3: Conflicting Delivery Claims (Recommendation: INVESTIGATE)
python main.py --scenario 3

# Scenario 4: High Fraud Indicators (Recommendation: INVESTIGATE / ACCEPT)
python main.py --scenario 4

# Scenario 5: Duplicate Dispute Flag (Recommendation: INVESTIGATE)
python main.py --scenario 5

# JSON Output Mode
python main.py --scenario 1 --json
```

---

## 📌 Data Provenance & Scientific Honesty Disclaimer

- **Dataset Provenance**: *Public transaction fraud dataset used for fraud-model experimentation; no private Razorpay data was used.*
- **Zero Customer Leakage**: Customer-level grouped splitting ensures zero `customer_id` overlap between training, validation, and testing sets.
- **Model Separation**: Fraud V2 predicts transaction fraud probability, while Win Probability predicts merchant dispute win probability. They operate as distinct complementary signals without score conflation.

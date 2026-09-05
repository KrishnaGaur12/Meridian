# Backend API Reference

Comprehensive specification of all 38 REST API endpoints in the Razorpay AI Risk Manager backend.

---

## 1. Health & ML Model Status

### `GET /health`
- **Purpose**: System liveness check.
- **Response `200 OK`**:
  ```json
  { "status": "ok" }
  ```
- **Source**: `src/api/routes/health.py:9`

### `GET /ml/model-health` (Alias: `GET /health/models`)
- **Purpose**: Returns baseline validation metrics and training parameters for Fraud Model V2 and Win Model.
- **Response `200 OK`**:
  ```json
  {
    "fraud_model": {
      "model_name": "Fraud Model V2 (XGBoost)",
      "model_version": "fraud-model-v2",
      "required_features_count": 12,
      "metrics": {
        "pr_auc": 0.8559,
        "roc_auc": 0.9841,
        "f1_score": 0.7229
      },
      "status": "HEALTHY_BASELINE"
    },
    "win_model": {
      "model_name": "Dispute Win Probability (Random Forest)",
      "model_version": "win-rf-150",
      "required_features_count": 13,
      "metrics": {
        "roc_auc": 0.8688,
        "pr_auc": 0.9406,
        "f1_score": 0.9080
      },
      "status": "HEALTHY_BASELINE"
    }
  }
  ```
- **Source**: `src/api/routes/health.py:14`

---

## 2. Database Mode & System Management

### `GET /mode` & `GET /system/mode`
- **Purpose**: Inspects active database mode (`DEMO` or `LIVE`), total transactions, and dispute counts.
- **Response `200 OK`**:
  ```json
  {
    "active_mode": "DEMO",
    "database_file": "demo_database.db",
    "total_transactions": 6,
    "total_disputes": 6,
    "isolation_guarantee": "STRICT_ISOLATION",
    "description": "Currently operating on DEMO SQLite database."
  }
  ```
- **Source**: `src/api/routes/mode.py:24`, `src/api/routes/system.py:14`

### `POST /mode`
- **Purpose**: Switches global backend database mode (`DEMO` or `LIVE`).
- **Request Body**:
  ```json
  { "mode": "LIVE" }
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "active_mode": "LIVE",
    "database_file": "live_database.db",
    "total_transactions": 15,
    "total_disputes": 0,
    "message": "Backend database mode successfully switched to LIVE."
  }
  ```
- **Source**: `src/api/routes/mode.py:44`

### `POST /system/reset-live`
- **Purpose**: Developer utility: clears all simulated live disputes and resets to the 15 clean live transactions.
- **Source**: `src/api/routes/system.py:34`

---

## 3. Transactions & Risk

### `GET /transactions`
- **Purpose**: Lists transactions in active database.
- **Source**: `src/api/routes/transactions.py:18`

### `GET /transactions/eligible`
- **Purpose**: Lists dispute-eligible transactions (`SUCCESS`/`CAPTURED` status without active disputes).
- **Source**: `src/api/routes/transactions.py:23`

### `POST /transactions`
- **Purpose**: Creates new transaction with customer, payment, order, and fulfillment records.
- **Request Schema**: `TransactionCreateSchema` (`src/schemas/api_schemas.py:10`).
- **Response `201 Created`**: `TransactionResponseSchema`.
- **Source**: `src/api/routes/transactions.py:49`

### `POST /transactions/{transaction_id}/risk-assessment`
- **Purpose**: Runs Fraud Model V2 prediction and decision logic; persists `RiskAssessment`.
- **Response `200 OK`**:
  ```json
  {
    "transaction_id": "TXN_LIVE_001",
    "risk_score": 0.0825,
    "risk_level": "LOW",
    "decision": "ALLOW",
    "model_version": "fraud-model-v2"
  }
  ```
- **Source**: `src/api/routes/risk.py:19`

---

## 4. Disputes & Operations Command Center

### `GET /disputes`
- **Purpose**: Lists dispute cases with calculated deadline urgency, filtering, and pagination.
- **Query Parameters**:
  - `case_source` (`DEMO`, `SIMULATED_RAZORPAY`, `REAL_RAZORPAY`)
  - `status` (`OPEN`, `UNDER_REVIEW`, `WON`, `LOST`, `CLOSED`)
  - `workflow_stage` (`DISPUTE_RAISED`, `MERCHANT_REVIEW`, `SUBMITTED`, etc.)
  - `merchant_attention_state` (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`)
  - `search` (Search query across IDs and reason descriptions)
  - `page`, `page_size`, `limit`, `offset`
- **Response `200 OK`**: `List[DisputeResponseSchema]`.
- **Source**: `src/api/routes/disputes.py:56`

### `GET /disputes/{dispute_id}/command-center`
- **Purpose**: Aggregates the single consolidated operations snapshot for `DisputeDetailPage.tsx`.
- **Response `200 OK`**: `CommandCenterSnapshotSchema` (`src/schemas/api_schemas.py:227`).
- **Source**: `src/api/routes/disputes.py:277`

### `GET /disputes/{dispute_id}/analysis`
- **Purpose**: Executes authoritative risk, win probability, evidence intelligence, and recommendation pipeline.
- **Response `200 OK`**: `DisputeCaseAnalysisSchema` (`src/schemas/api_schemas.py:154`).
- **Source**: `src/api/routes/disputes.py:136`

### `GET /disputes/{dispute_id}/readiness`
- **Purpose**: Computes deterministic readiness score (0-100%) and submission blockers.
- **Response `200 OK`**: `DisputeCaseReadinessSchema` (`src/schemas/api_schemas.py:112`).
- **Source**: `src/api/routes/disputes.py:175`

### `POST /disputes/{dispute_id}/submit`
- **Purpose**: Validates readiness gate, advances stage to `SUBMITTED`, sets status to `under_review`, and issues gateway reference ID.
- **Request Body**:
  ```json
  { "merchant_position": "CONTEST" }
  ```
- **Response `200 OK`**: `DisputeSubmitResponseSchema` (`src/schemas/api_schemas.py:128`).
- **Source**: `src/api/routes/disputes.py:189`

### `POST /disputes/{dispute_id}/simulate-outcome`
- **Purpose**: Simulates issuer card network outcome (`WON` or `LOST`) based on evidence completeness.
- **Response `200 OK`**: `DisputeOutcomeResponseSchema` (`src/schemas/api_schemas.py:142`).
- **Source**: `src/api/routes/disputes.py:211`

---

## 5. Evidence Engine

### `POST /disputes/{dispute_id}/evidence/upload`
- **Purpose**: Uploads evidence file, extracts text, computes SHA-256 hash, and triggers DeepSeek AI verification.
- **Form Data**:
  - `file`: Multipart binary document (PDF, PNG, JPG, TXT, DOCX)
  - `evidence_type`: Optional preferred type
  - `title`, `description`: Optional metadata
- **Response `201 Created`**: Complete evidence object with extracted facts and AI verification result.
- **Source**: `src/api/routes/evidence.py:267`

### `POST /disputes/{dispute_id}/evidence/{evidence_id}/approve`
- **Purpose**: Merchant approves evidence item for representment inclusion.
- **Response `200 OK`**: Refreshed dispute state with updated win probability and readiness score.
- **Source**: `src/api/routes/evidence.py:848`

### `POST /disputes/{dispute_id}/evidence/{evidence_id}/reject`
- **Purpose**: Merchant rejects evidence item, excluding it from defense bundle.
- **Source**: `src/api/routes/evidence.py:979`

### `POST /disputes/{dispute_id}/evidence/{evidence_id}/verify`
- **Purpose**: Explicitly triggers or retries DeepSeek AI evidence verification.
- **Response `200 OK`**: `EvidenceAnalysisResultSchema`.
- **Source**: `src/api/routes/evidence.py:681`

---

## 6. Real-Time Events (Server-Sent Events)

### `GET /events`
- **Purpose**: Real-time event stream (`text/event-stream`).
- **Events Broadcasted**:
  - `DISPUTE_CREATED`
  - `DISPUTE_ANALYSIS_STARTED`
  - `ML_ANALYSIS_COMPLETED`
  - `DEEPSEEK_ANALYSIS_COMPLETED`
  - `DISPUTE_ANALYSIS_COMPLETED`
  - `EVIDENCE_APPROVED`
  - `DISPUTE_STAGE_CHANGED`
  - `DASHBOARD_UPDATED`
- **Source**: `src/api/routes/events.py:80`

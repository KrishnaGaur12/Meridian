# BACKEND ARCHITECTURE & FRONTEND INTEGRATION SPECIFICATION
## Razorpay AI Risk Manager — Merchant-First AI Chargeback Operations Platform

> **VERSION**: 2.0  
> **TARGET AUDIENCE**: Frontend Engineers, Full-Stack Developers, & Integration Specialists  
> **BASE URL**: `http://localhost:8000` (Local Dev) | `http://127.0.0.1:8000`  
> **API PROTOCOL**: REST HTTP / JSON  

---

## 1. EXECUTIVE BACKEND ARCHITECTURE OVERVIEW

The **Razorpay AI Risk Manager Backend** is an event-driven AI orchestration engine built on **FastAPI (Python 3.11+)**, **SQLAlchemy ORM**, **SQLite**, and **Scikit-Learn / XGBoost ML Models**.

It transforms payment chargeback management from manual spreadsheet processing into an automated, proactive pipeline.

```text
                                 FULL-STACK SYSTEM BOUNDARY
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   React 19 / TypeScript 6 Frontend (Vite 8 + Tailwind CSS v4)                            │
│                          │                                                              │
│                          ▼                                                              │
│   Frontend API Layer (Axios Services / dashboardService.ts & disputeService.ts)         │
│                          │                                                              │
│                          ▼  REST HTTP / JSON (CORS Enabled)                             │
│   FastAPI Gateway Router (src/api/router.py / main.py)                                  │
│                          │                                                              │
│             ┌────────────┴────────────┐                                                 │
│             ▼                         ▼                                                 │
│   Business Logic & Pipeline     AI / ML Engine                                          │
│   (src/evidence/, src/response/) (Fraud V2 XGBoost, Win Model Random Forest)            │
│             │                         │                                                 │
│             └────────────┬────────────┘                                                 │
│                          ▼                                                              │
│   SQLAlchemy ORM Repositories (src/database/repository.py)                              │
│                          │                                                              │
│                          ▼                                                              │
│   SQLite Database (data/app_database.db)                                                │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Core Architecture Pillars

1. **Central AI Autopilot (`AIAutopilot`)**:
   - Automatically triages every dispute into one of 4 merchant attention states (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`).
   - Dynamically recalculates risk scores, evidence completeness, win probability, Next Best Action, and readiness upon every evidence mutation (add/update/delete).
2. **Strict 3-Tier Data Architecture**:
   - `DEMO`: Seeded showcase scenario records.
   - `SIMULATED_RAZORPAY`: Local simulation disputes created via the `/demo` simulation generator.
   - `REAL_RAZORPAY`: Reserved tier for future external webhook integrations.
3. **Human-in-the-Loop Submission Policy**:
   - AI generates rebuttal text and package metadata, but final submission requires explicit merchant sign-off (`POST /disputes/{id}/submit`).
4. **Strict Dispute Case Isolation**:
   - Every dispute operates as an isolated workspace identified by `dispute_id` (e.g. `DSP_1001`). All queries are scoped strictly to the target case ID.
5. **Local Gateway Boundary Submission**:
   - Dispatched submissions record `Submitted — Local Gateway Boundary` to ensure clean separation from live payment network API calls.

---

## 2. DATA MODELS & ENTITY SCHEMA REFERENCE

### Database Entities (`src/database/models.py`)

#### 1. `Dispute` (`disputes` table)
| Field | Type | Required | Description / Enum Values |
| :--- | :--- | :--- | :--- |
| `dispute_id` | String | PK | Unique dispute identifier (e.g., `DSP_1001`) |
| `transaction_id` | String | FK | Foreign key to `transactions.transaction_id` |
| `customer_id` | String | FK | Foreign key to `customers.customer_id` |
| `reason_code` | String | Yes | `product_not_received`, `fraudulent_transaction`, `duplicate_charge`, `refund_not_processed` |
| `reason_description` | String | No | Detailed customer/bank dispute claim statement |
| `status` | String | Yes | Bank Status: `OPEN`, `UNDER_REVIEW`, `WON`, `LOST`, `CLOSED` |
| `phase` | String | Yes | Razorpay Phase: `retrieval`, `chargeback`, `pre_arbitration`, `arbitration`, `fraud` |
| `respond_by` | String | No | ISO 8601 UTC deadline string (e.g., `2026-09-07T20:00:00Z`) |
| `workflow_stage` | String | Yes | `DISPUTE_RAISED`, `EVIDENCE_COLLECTION`, `MERCHANT_REVIEW`, `READY_FOR_SUBMISSION`, `SUBMITTED`, `RESOLVED` |
| `case_source` | String | Yes | Data tier: `DEMO`, `SIMULATED_RAZORPAY`, `REAL_RAZORPAY` |
| `merchant_attention_state` | String | Yes | Operational Attention Queue: `ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING` |
| `ai_last_checked` | String | No | ISO timestamp when AI Autopilot last processed the case |
| `created_at` | String | Yes | ISO timestamp of record creation |

#### 2. `Transaction` (`transactions` table)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String | PK | Unique transaction ID (e.g., `TXN_2001`) |
| `customer_id` | String | FK | Customer ID |
| `merchant_id` | String | Yes | Merchant ID (default: `MERCHANT_001`) |
| `amount` | Float | Yes | Transaction monetary value |
| `currency` | String | Yes | `USD`, `INR`, `EUR`, etc. |
| `payment_method` | String | Yes | `credit_card`, `upi`, `netbanking`, `debit_card` |
| `merchant_category` | String | Yes | `retail`, `digital_goods`, `travel`, etc. |
| `transaction_country` | String | Yes | 2-letter ISO country code (`US`, `IN`, etc.) |
| `transaction_status` | String | Yes | `SUCCESS`, `FAILED`, `PENDING` |
| `transaction_hour` | Integer | Yes | Hour of day (0-23) for ML Fraud Model V2 |
| `account_age_days` | Integer | Yes | Customer account tenure in days |
| `previous_chargebacks` | Integer | Yes | Count of prior chargebacks by customer |
| `device_type` | String | Yes | `mobile`, `desktop`, `tablet` |
| `is_international` | Integer | Yes | `0` (domestic) or `1` (international) |
| `is_high_risk_merchant` | Integer | Yes | `0` (normal) or `1` (high risk category) |
| `transaction_velocity_1h` | Integer | Yes | Transactions in prior 1 hour |
| `transaction_velocity_24h` | Integer | Yes | Transactions in prior 24 hours |
| `avg_transaction_amount_30d` | Float | Yes | Merchant's 30-day average transaction amount |

#### 3. `Evidence` (`evidence` table)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `evidence_id` | String | PK | Unique evidence ID (e.g., `EVD_1001`) |
| `dispute_id` | String | FK | Foreign key to `disputes.dispute_id` |
| `transaction_id` | String | FK | Foreign key to `transactions.transaction_id` |
| `evidence_type` | String | Yes | `proof_of_delivery`, `customer_communication`, `refund_policy`, `ip_address_log`, `invoice`, `tos_acceptance` |
| `title` | String | Yes | Human readable document title |
| `description` | String | No | Document summary or merchant note |
| `source` | String | Yes | `DATABASE`, `MERCHANT_UPLOAD`, `SYSTEM` |
| `evidence_data_json` | Text | No | Serialized JSON payload containing granular proof attributes |
| `verification_status` | String | Yes | `AVAILABLE`, `VERIFIED`, `UNVERIFIED`, `REJECTED` |

#### 4. `DisputeEvent` (`dispute_events` table)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | String | PK | Unique event ID |
| `dispute_id` | String | FK | Foreign key to `disputes.dispute_id` |
| `event_type` | String | Yes | `SYSTEM_CREATED`, `EVIDENCE_ADDED`, `EVIDENCE_UPDATED`, `EVIDENCE_REMOVED`, `MERCHANT_ACCEPTED`, `MERCHANT_OVERRIDE`, `SUBMITTED` |
| `title` | String | Yes | Short title for activity feed |
| `description` | Text | Yes | Complete event narrative |
| `timestamp` | String | Yes | ISO timestamp |
| `actor_type` | String | Yes | `SYSTEM`, `AI_ENGINE`, `MERCHANT`, `LOCAL_GATEWAY` |
| `previous_stage` | String | No | Workflow stage before event |
| `new_stage` | String | No | Workflow stage after event |
| `metadata_json` | Text | No | Additional JSON metadata payload |

---

## 3. CORE ENUMS & OPERATIONAL STATES

### 1. `merchant_attention_state` (4 Core Dashboard Queues)
- `ACTION_REQUIRED`: High-priority attention needed (e.g. missing required delivery proof, customer complaint present).
- `REVIEW_RECOMMENDED`: AI finished analysis, evidence is complete, waiting for merchant final review.
- `AI_HANDLING`: AI Autopilot actively evaluating, fetching automated database proofs, or generating rebuttal.
- `WAITING`: Case closed, submitted, or waiting for bank response.

### 2. `workflow_stage` (Internal Lifecycle)
- `DISPUTE_RAISED`: New dispute received.
- `EVIDENCE_COLLECTION`: Gathering required proof documents.
- `MERCHANT_REVIEW`: Case ready for merchant decision/review.
- `READY_FOR_SUBMISSION`: Package 100% complete and passed backend readiness gate.
- `SUBMITTED`: Response sent through local gateway boundary.
- `RESOLVED`: Case closed or accepted.

### 3. `case_source` (3-Tier Data Architecture)
- `DEMO`: Seeded showcase dataset.
- `SIMULATED_RAZORPAY`: Local simulation created via `/demo/simulate-dispute`.
- `REAL_RAZORPAY`: External live webhook data stream.

---

## 4. COMPLETE API ENDPOINTS SPECIFICATION

### A. Disputes Router (`/disputes`)

#### 1. List Disputes
- **HTTP Method**: `GET`
- **Path**: `/disputes`
- **Query Parameters**: `case_source` (optional: `DEMO`, `SIMULATED_RAZORPAY`, `REAL_RAZORPAY`)
- **Response Model**: `List[DisputeResponseSchema]`
- **Status Code**: `200 OK`
- **Description**: Returns all dispute cases with calculated remaining hours, deadline urgency, amount, and attention state.

#### 2. Create Dispute
- **HTTP Method**: `POST`
- **Path**: `/disputes`
- **Request Body**: `DisputeCreateSchema`
  ```json
  {
    "transaction_id": "TXN_2001",
    "reason_code": "product_not_received",
    "reason_description": "Customer claims non-delivery",
    "phase": "chargeback",
    "case_source": "SIMULATED_RAZORPAY"
  }
  ```
- **Response Model**: `DisputeResponseSchema`
- **Status Code**: `201 Created`

#### 3. Get Dispute by ID
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}`
- **Response Model**: `DisputeResponseSchema`
- **Status Code**: `200 OK`

#### 4. Get Operations Command Center Snapshot
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/command-center`
- **Response Model**: `CommandCenterSnapshotSchema`
- **Status Code**: `200 OK`
- **Description**: Single-call aggregator endpoint returning `dispute`, `case_analysis`, `explainability`, `next_action`, `package_inspection`, and `audit_trail`. Perfect for single-page dispute workspace load!

#### 5. Get AI Case Analysis
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/analysis`
- **Response Model**: `DisputeCaseAnalysisSchema`
- **Status Code**: `200 OK`
- **Description**: Runs full AI intelligence pipeline including Fraud Model V2 prediction, Win Probability calculation, evidence completeness scoring, and AI recommendation.

#### 6. Get AI Explainability Metrics
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/explainability`
- **Response Model**: `AIExplainabilitySchema`
- **Status Code**: `200 OK`
- **Description**: Returns top contributing ML features, SHAP-style breakdown, positive factors, and negative factors for both Fraud and Win models.

#### 7. Get Deterministic Next Best Action
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/next-action`
- **Response Model**: `NextBestActionSchema`
- **Status Code**: `200 OK`
- **Description**: Returns top recommended action, priority, `why_asking` explanation, expected win probability impact, and blocking items.

#### 8. Get Case Readiness & Gate Status
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/readiness`
- **Response Model**: `DisputeCaseReadinessSchema`
- **Status Code**: `200 OK`
- **Description**: Evaluates readiness percentage (0-100%), `can_submit` boolean, missing required proofs, blocking issues, and evidence mapping.

#### 9. Inspect Chargeback Package
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/package-inspection`
- **Response Model**: `ChargebackPackageInspectionSchema`
- **Status Code**: `200 OK`
- **Description**: Preview exact JSON payload that will be submitted to the local gateway boundary.

#### 10. Submit Dispute Package (Hard Submission Gate)
- **HTTP Method**: `POST`
- **Path**: `/disputes/{dispute_id}/submit`
- **Response Model**: `DisputeSubmitResponseSchema`
- **Status Code**: `200 OK`
- **Description**: Validates readiness gate. If `can_submit=true`, advances workflow to `SUBMITTED`, sets attention state to `WAITING`, and records `Submitted — Local Gateway Boundary` event.

#### 11. Accept Dispute (Merchant Concede)
- **HTTP Method**: `POST`
- **Path**: `/disputes/{dispute_id}/accept`
- **Request Body**: `{"reason": "Merchant accepted dispute"}`
- **Status Code**: `200 OK`
- **Description**: Merchant decides not to contest. Closes case (`status=CLOSED`, `workflow_stage=RESOLVED`).

#### 12. Override AI Recommendation
- **HTTP Method**: `POST`
- **Path**: `/disputes/{dispute_id}/override-recommendation`
- **Request Body**: `{"override_decision": "CONTEST", "reason": "Merchant verified package delivery tracking manually"}`
- **Status Code**: `200 OK`
- **Description**: Overrides AI decision (`CONTEST`, `ACCEPT`, `INVESTIGATE`) and updates workflow/attention states accordingly.

#### 13. Reassess Dispute Case
- **HTTP Method**: `POST`
- **Path**: `/disputes/{dispute_id}/reassess`
- **Status Code**: `200 OK`
- **Description**: Manually triggers AI Autopilot re-evaluation and returns updated case analysis with impact delta.

#### 14. Get Chronological Audit Log Stream
- **HTTP Method**: `GET`
- **Path**: `/disputes/{dispute_id}/audit`
- **Response Model**: `List[DisputeAuditEventSchema]`
- **Status Code**: `200 OK`

---

### B. Evidence Router (`/evidence` & `/disputes/{id}/evidence`)

#### 1. Upload / Add Merchant Evidence
- **HTTP Method**: `POST`
- **Path**: `/evidence`
- **Request Body**:
  ```json
  {
    "dispute_id": "DSP_1001",
    "evidence_type": "proof_of_delivery",
    "title": "FedEx Delivery Receipt",
    "description": "Signed delivery receipt by customer",
    "verification_status": "AVAILABLE",
    "evidence_data": {
      "carrier": "FedEx",
      "tracking_number": "TRK99887766",
      "delivered_at": "2026-08-25T14:30:00Z"
    }
  }
  ```
- **Status Code**: `201 Created`
- **Returns**: Created evidence record plus **Before vs After `impact_delta`** (win probability increase, attention state shift).

#### 2. Update Evidence Item
- **HTTP Method**: `PUT`
- **Path**: `/evidence/{evidence_id}`
- **Request Body**: `UpdateEvidenceRequest`
- **Status Code**: `200 OK`
- **Returns**: Updated evidence record plus updated `impact_delta`.

#### 3. Delete Evidence Item
- **HTTP Method**: `DELETE`
- **Path**: `/evidence/{evidence_id}`
- **Status Code**: `200 OK`
- **Returns**: Deletion status plus `impact_delta` showing potential score drop.

#### 4. Generate Evaluated Evidence Package
- **HTTP Method**: `POST`
- **Path**: `/disputes/{dispute_id}/evidence`
- **Status Code**: `200 OK`

---

### C. Razorpay Demo Simulation Router (`/demo`)

#### 1. List Eligible Simulation Transactions
- **HTTP Method**: `GET`
- **Path**: `/demo/available-transactions`
- **Status Code**: `200 OK`
- **Description**: Returns all database transactions with flag `has_active_simulated_dispute`.

#### 2. Simulate Incoming Razorpay Dispute
- **HTTP Method**: `POST`
- **Path**: `/demo/simulate-dispute`
- **Request Body**:
  ```json
  {
    "transaction_id": "TXN_2002",
    "reason_code": "product_not_received",
    "reason_description": "Customer claims package never arrived",
    "phase": "chargeback"
  }
  ```
- **Status Code**: `201 Created`
- **Description**: Instantly creates a `SIMULATED_RAZORPAY` dispute, triggers AI Autopilot analysis, and returns complete initial snapshot.

---

### D. Transactions & Risk Routers (`/transactions`)

#### 1. List All Transactions
- **HTTP Method**: `GET`
- **Path**: `/transactions`
- **Status Code**: `200 OK`

#### 2. Create Transaction
- **HTTP Method**: `POST`
- **Path**: `/transactions`
- **Request Body**: `TransactionCreateSchema`
- **Status Code**: `201 Created`

#### 3. Get Transaction by ID
- **HTTP Method**: `GET`
- **Path**: `/transactions/{transaction_id}`
- **Status Code**: `200 OK`

#### 4. Run Risk Assessment
- **HTTP Method**: `POST`
- **Path**: `/transactions/{transaction_id}/risk-assessment`
- **Response Model**: `RiskAssessmentResponseSchema`
- **Status Code**: `200 OK`
- **Description**: Runs Fraud Model V2 prediction and returns risk score, risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and decision (`ALLOW`, `REVIEW`, `BLOCK`).

---

### E. Health & Model Health Routers (`/health` & `/health/models`)

#### 1. Application Health Check
- **HTTP Method**: `GET`
- **Path**: `/health`
- **Status Code**: `200 OK`
- **Response**: `{"status": "ok"}`

#### 2. ML Models Health Check
- **HTTP Method**: `GET`
- **Path**: `/health/models`
- **Status Code**: `200 OK`
- **Description**: Returns model names, versions, PR-AUC, ROC-AUC, F1 scores, required feature counts, and health status for UI header indicator.

---

## 5. FRONTEND INTEGRATION & DATA FLOW PATTERNS

### 1. Axios Service Architecture (`src/services/api.ts`)
```typescript
import axios from 'axios';

export const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### 2. Loading Dispute Case Workspace (`DisputeDetailPage.tsx`)
Instead of making 6 separate API calls on page load, use the Command Center endpoint:
```typescript
export const fetchDisputeCommandCenter = async (disputeId: string) => {
  const response = await api.get(`/disputes/${disputeId}/command-center`);
  return response.data; // Contains dispute, case_analysis, explainability, next_action, package_inspection, audit_trail
};
```

### 3. Dynamic Real-Time Reassessment Pattern (Evidence Upload)
When a merchant uploads evidence in the UI:
1. Call `POST /evidence` with payload.
2. Receive response containing `impact_delta` (e.g. `win_probability_delta: +25%`, `attention_state_changed: true`).
3. Render toast/banner displaying the exact Impact Delta ("Win probability increased from 62% to 87%!").
4. Refresh command center or local state to reflect updated queue and readiness.

### 4. Razorpay Simulation Workflow (`RazorpayDemoPage.tsx`)
1. User clicks "Simulate Dispute" on Razorpay Demo page.
2. Frontend calls `POST /demo/simulate-dispute`.
3. Backend creates case, runs AI pipeline, and logs initial timeline events.
4. Frontend redirects user to `/disputes/:id` workspace or updates dashboard queues instantly.

---

## 6. ERROR HANDLING & HTTP CODES REFERENCE

| HTTP Code | Error Code / Cause | Frontend Action |
| :--- | :--- | :--- |
| `400 Bad Request` | Hard submission gate failure (e.g. missing required proof) | Display error alert modal showing blocking issues |
| `404 Not Found` | Target `dispute_id` or `transaction_id` does not exist | Redirect to `/disputes` with notification |
| `422 Unprocessable Entity` | Pydantic schema validation failure | Check missing body parameters |
| `500 Internal Server Error` | Pipeline execution exception | Display retry toast message |

---

## 7. SUMMARY CHECKLIST FOR FRONTEND DEVELOPERS

- [x] **Base URL**: Ensure Axios `baseURL` points to `http://localhost:8000`.
- [x] **Dispute List Filters**: Filter disputes by `case_source` (`DEMO`, `SIMULATED_RAZORPAY`, `REAL_RAZORPAY`).
- [x] **Dashboard Cards**: Group disputes by `merchant_attention_state` (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`).
- [x] **Dispute Detail**: Use `GET /disputes/{id}/command-center` for optimal load performance.
- [x] **Evidence Modals**: Post to `/evidence` and handle `impact_delta` in response for instant visual feedback.
- [x] **Submission**: Submit via `POST /disputes/{id}/submit` and display local gateway notice.

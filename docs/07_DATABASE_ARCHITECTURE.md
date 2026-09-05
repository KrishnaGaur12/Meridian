# DATABASE ARCHITECTURE

## Overview

**Database Technology:** SQLite (development) / PostgreSQL-ready (production)

**ORM Framework:** SQLAlchemy 2.0+ with declarative mapping

**Models:** 11 core entities with relationships

**Total Tables:** 11 + junction tables for many-to-many relationships

**Schema Version:** 2.0.0 (implicit, no migration tracking)

---

## DATABASE SCHEMA - ENTITY RELATIONSHIP DIAGRAM

```
┌─────────────────┐
│   CUSTOMERS     │
│─────────────────│
│ customer_id (PK)│◄─────────────┐
│ account_age     │              │
│ verification    │              │
│ country         │              │
│ prev_chargebacks│              │
│ avg_amount_30d  │              │
│ created_at      │              │
└─────────────────┘              │
         │                        │
         │ 1:N                    │
         │                        │
         ▼                        │
┌─────────────────┐              │
│  TRANSACTIONS   │              │
│─────────────────│              │
│ transaction_id  │◄─────┐       │
│  (PK, FK→CUST)  │      │       │
│ customer_id (FK)├──────┼──────┘
│ merchant_id     │      │
│ amount          │      │
│ currency        │      │
│ timestamp       │      │
│ payment_method  │      │ 1:N
│ merchant_cat    │      │
│ transaction_cntr│      │
│ status          │      │
│ ML features...  │      │
│ created_at      │      │
└─────────────────┘      │
         │               │
    1:N  │               │
    ┌────┴──────┬────────┴─┬─────────────┐
    │           │          │             │
    ▼           ▼          ▼             ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│PAYMENTS│ │ ORDERS │ │DISPUTES│ │RISK_        │
│────────│ │────────│ │────────│ │ASSESSMENTS  │
│payment │ │order_id│ │dispute │ │─────────────│
│_id(PK) │ │ (PK,FK)│ │_id(PK) │ │assessment_id│
│ (FK)   │ │ (FK)   │ │ (PK)   │ │(PK)        │
│txn_id  │ │ (FK)   │ │ (FK→tx)│ │(FK→txn)    │
│cust_id │ │tx_id   │ │cust_id │ │risk_score  │
│payment │ │cust_id │ │(FK→cst)│ │risk_level  │
│method  │ │product │ │reason_ │ │decision    │
│card_net│ │descr   │ │code    │ │model_ver   │
│last4   │ │amount  │ │status  │ │created_at  │
│avs_mtch│ │status  │ │phase   │ │            │
│cvv_mtch│ │created │ │respond │ │            │
│auth_cd │ │created │ │_by     │ │            │
│status  │ │created │ │workflow│ │            │
│created │ │created │ │_stage  │ │            │
└────────┘ │        │ │case_src│ │            │
           │        │ │merchant│ │            │
           │        │ │_attn   │ │            │
           │        │ │ai_last │ │            │
           │        │ │created │ │            │
           │        │ │        │ │            │
           └────────┘ └────────┘ │            │
                          │      │            │
                     1:N  │      │            │
              ┌───────────┘      │            │
              │                  │            │
              ▼                  ▼            │
         ┌──────────────┐  ┌─────────────────┤
         │   EVIDENCE   │  │DISPUTE_         │
         │──────────────│  │ASSESSMENTS      │
         │evidence_id   │  │─────────────────│
         │(PK)         │  │assessment_id    │
         │dispute_id   │  │(PK)            │
         │(FK)         │  │dispute_id (FK)  │
         │transaction_ │  │analysis_version │
         │id (FK)      │  │trigger          │
         │evidence_type│  │risk_score       │
         │title        │  │fraud_prob       │
         │description  │  │win_prob         │
         │source       │  │confidence       │
         │source_ref   │  │confidence_lvl   │
         │file_path    │  │ml_recommend     │
         │mime_type    │  │ai_recommend     │
         │file_size    │  │conflict_detect  │
         │doc_hash     │  │ml_results_json  │
         │content_hash │  │deepseek_results │
         │raw_content  │  │evidence_analysis│
         │extracted_tx │  │model_versions   │
         │content_json │  │generated_at     │
         │key_entities │  │                 │
         │verification │  │                 │
         │_status      │  │                 │
         │approval_stus│  │                 │
         │approved_at  │  │                 │
         │approved_by  │  │                 │
         │ai_analysis_ │  │                 │
         │json         │  │                 │
         │ai_analysis_ │  │                 │
         │status       │  │                 │
         │ai_analyzed_ │  │                 │
         │at           │  │                 │
         │ai_error     │  │                 │
         │created_at   │  │                 │
         │updated_at   │  │                 │
         │is_deleted   │  │                 │
         └──────────────┘  └─────────────────┘
              │                    │
              │ 1:N                │
              └────────┬───────────┘
                       │
                       ▼
           ┌──────────────────────┐
           │   DISPUTE_EVENTS     │
           │──────────────────────│
           │ event_id (PK)        │
           │ dispute_id (FK)      │
           │ event_type           │
           │ title                │
           │ description          │
           │ timestamp            │
           │ actor_type           │
           │ previous_stage       │
           │ new_stage            │
           │ metadata_json        │
           └──────────────────────┘
                       │
                       │ 1:N
                       │
           ┌───────────────────────┐
           │CHARGEBACK_PACKAGES    │
           │───────────────────────│
           │ package_id (PK)       │
           │ dispute_id (FK)       │
           │ transaction_id (FK)   │
           │ package_status        │
           │ merchant_position     │
           │ response_text         │
           │ package_data_json     │
           │ generator_version     │
           │ created_at            │
           └───────────────────────┘

           ┌──────────────────────┐
           │  WEBHOOK_EVENTS      │
           │──────────────────────│
           │ event_id (PK)        │
           │ idempotency_key      │
           │ event_type           │
           │ payload_json         │
           │ status               │
           │ dispute_id (FK, opt) │
           │ created_at           │
           │ processed_at         │
           └──────────────────────┘
           (NOT CONNECTED - Independent)
```

---

## TABLE DEFINITIONS

### 1. CUSTOMERS

```sql
CREATE TABLE customers (
    customer_id VARCHAR PRIMARY KEY,
    account_age_days INTEGER DEFAULT 180,
    verification_status VARCHAR DEFAULT 'VERIFIED',
    country VARCHAR DEFAULT 'US',
    previous_chargebacks INTEGER DEFAULT 0,
    avg_transaction_amount_30d FLOAT DEFAULT 100.0,
    created_at VARCHAR DEFAULT utc_now_iso()
);
```

**Purpose:** Merchant/customer profile data

**Columns:**
- `customer_id` — Unique merchant identifier
- `account_age_days` — Days since account created
- `verification_status` — VERIFIED, UNVERIFIED, FLAGGED
- `country` — Merchant country (ISO code)
- `previous_chargebacks` — Historical chargeback count
- `avg_transaction_amount_30d` — Average transaction size
- `created_at` — UTC timestamp

**Indexes:** customer_id (PK)

**Relationships:**
- 1:N with transactions
- 1:N with orders
- 1:N with disputes
- 1:N with payments

**Usage:** Profile lookups, chargeback history, risk scoring

---

### 2. TRANSACTIONS

```sql
CREATE TABLE transactions (
    transaction_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR FK,
    merchant_id VARCHAR,
    amount FLOAT NOT NULL,
    currency VARCHAR DEFAULT 'USD',
    timestamp VARCHAR,
    payment_method VARCHAR,
    merchant_category VARCHAR,
    transaction_country VARCHAR,
    transaction_status VARCHAR DEFAULT 'SUCCESS',
    
    -- ML Model V2 Features
    transaction_hour INTEGER,
    account_age_days INTEGER,
    previous_chargebacks INTEGER,
    device_type VARCHAR,
    is_international INTEGER,
    is_high_risk_merchant INTEGER,
    transaction_velocity_1h INTEGER,
    transaction_velocity_24h INTEGER,
    avg_transaction_amount_30d FLOAT
);
```

**Purpose:** Payment transaction records with ML features

**Columns:** (39 total, listed above)

**Indexes:** 
- transaction_id (PK)
- customer_id (FK)
- timestamp
- transaction_status

**Relationships:**
- N:1 with customers (FK)
- 1:N with payments
- 1:N with orders
- 1:N with disputes
- 1:N with risk_assessments
- 1:N with evidence

**Usage:** Transaction lookup, fraud model input, dispute context

**Critical:** All 11 features for fraud_v2_pipeline.joblib are stored here

---

### 3. PAYMENTS

```sql
CREATE TABLE payments (
    payment_id VARCHAR PRIMARY KEY,
    transaction_id VARCHAR FK,
    customer_id VARCHAR FK,
    payment_method VARCHAR,
    card_network VARCHAR,
    last4 VARCHAR,
    avs_match VARCHAR,
    cvv_match VARCHAR,
    auth_code VARCHAR,
    payment_status VARCHAR DEFAULT 'CAPTURED',
    created_at VARCHAR
);
```

**Purpose:** Payment method & authorization details

**Relationships:** N:1 with transactions, N:1 with customers

**Usage:** Card verification, AVS/CVV matching, payment proof

---

### 4. ORDERS

```sql
CREATE TABLE orders (
    order_id VARCHAR PRIMARY KEY,
    transaction_id VARCHAR FK UNIQUE,
    customer_id VARCHAR FK,
    product_description VARCHAR,
    order_amount FLOAT,
    order_status VARCHAR DEFAULT 'COMPLETED',
    created_at VARCHAR
);
```

**Purpose:** Order/fulfillment metadata

**Relationships:** 1:1 with transactions, N:1 with customers

**Usage:** Order confirmation, product proof, fulfillment tracking

---

### 5. FULFILLMENTS

```sql
CREATE TABLE fulfillments (
    fulfillment_id VARCHAR PRIMARY KEY,
    order_id VARCHAR FK,
    tracking_number VARCHAR,
    carrier VARCHAR,
    shipped_date VARCHAR,
    delivery_date VARCHAR,
    delivery_confirmation VARCHAR,
    delivery_address VARCHAR,
    creation_at VARCHAR
);
```

**Purpose:** Shipping & delivery proof

**Relationships:** 1:1 with orders

**Usage:** Evidence for dispute resolution

---

### 6. DISPUTES

```sql
CREATE TABLE disputes (
    dispute_id VARCHAR PRIMARY KEY,
    transaction_id VARCHAR FK,
    customer_id VARCHAR FK,
    reason_code VARCHAR NOT NULL,
    reason_description VARCHAR,
    status VARCHAR DEFAULT 'OPEN',
    phase VARCHAR DEFAULT 'chargeback',
    respond_by VARCHAR,
    workflow_stage VARCHAR DEFAULT 'DISPUTE_RAISED',
    case_source VARCHAR DEFAULT 'SIMULATED_RAZORPAY',
    merchant_attention_state VARCHAR DEFAULT 'ACTION_REQUIRED',
    ai_last_checked VARCHAR,
    created_at VARCHAR
);
```

**Purpose:** Chargeback dispute records

**Key Columns:**
- `status` — OPEN, UNDER_REVIEW, WON, LOST, CLOSED
- `phase` — retrieval, chargeback, pre_arbitration, arbitration, fraud
- `workflow_stage` — DISPUTE_RAISED, EVIDENCE_COLLECTION, AI_ANALYSIS, MERCHANT_REVIEW, SUBMITTED
- `respond_by` — Deadline timestamp
- `merchant_attention_state` — ACTION_REQUIRED, REVIEW_RECOMMENDED, AI_HANDLING, WAITING
- `case_source` — DEMO, SIMULATED_RAZORPAY, REAL_RAZORPAY

**Indexes:**
- dispute_id (PK)
- transaction_id (FK)
- customer_id (FK)
- status
- workflow_stage
- created_at

**Relationships:**
- N:1 with transactions
- N:1 with customers
- 1:N with evidence
- 1:N with dispute_events
- 1:N with dispute_assessments

**Usage:** Main dispute tracking entity

---

### 7. DISPUTE_EVENTS

```sql
CREATE TABLE dispute_events (
    event_id VARCHAR PRIMARY KEY,
    dispute_id VARCHAR FK,
    event_type VARCHAR NOT NULL,
    title VARCHAR,
    description TEXT,
    timestamp VARCHAR,
    actor_type VARCHAR DEFAULT 'SYSTEM',
    previous_stage VARCHAR,
    new_stage VARCHAR,
    metadata_json TEXT DEFAULT '{}'
);
```

**Purpose:** Audit timeline of dispute workflow events

**Actor Types:** SYSTEM, AI_ENGINE, MERCHANT, LOCAL_GATEWAY

**Indexes:**
- event_id (PK)
- dispute_id (FK)
- timestamp
- event_type

**Usage:** Timeline display, audit trail, state history

---

### 8. EVIDENCE

```sql
CREATE TABLE evidence (
    evidence_id VARCHAR PRIMARY KEY,
    dispute_id VARCHAR FK,
    transaction_id VARCHAR FK,
    evidence_type VARCHAR NOT NULL,
    title VARCHAR,
    description VARCHAR,
    source VARCHAR DEFAULT 'DATABASE',
    source_reference_id VARCHAR,
    file_path VARCHAR,
    mime_type VARCHAR,
    file_size INTEGER,
    document_hash VARCHAR,
    content_hash VARCHAR,
    raw_content TEXT,
    extracted_text TEXT,
    content_json TEXT DEFAULT '{}',
    key_entities_json TEXT DEFAULT '{}',
    evidence_data_json TEXT DEFAULT '{}',
    verification_status VARCHAR DEFAULT 'UNVERIFIED',
    approval_status VARCHAR DEFAULT 'PENDING_APPROVAL',
    approved_at VARCHAR,
    approved_by VARCHAR,
    ai_analysis_json TEXT DEFAULT '{}',
    ai_analysis_status VARCHAR DEFAULT 'PENDING',
    ai_analyzed_at VARCHAR,
    ai_error TEXT,
    created_at VARCHAR,
    updated_at VARCHAR,
    is_deleted INTEGER DEFAULT 0
);
```

**Purpose:** Evidence items & AI analysis results

**Key Columns:**
- `evidence_type` — delivery_proof, order_confirmation, communication, payment_receipt, customer_complaint_response, invoice, shipping_label, return_documentation, tracking, photo_proof, etc.
- `verification_status` — UNVERIFIED, VERIFIED, INVALID, UNREADABLE, REJECTED, NEEDS_REVIEW, FAILED
- `approval_status` — PENDING_APPROVAL, APPROVED, REJECTED
- `ai_analysis_json` — DeepSeek AI analysis results
- `extracted_text` — OCR/PDF text extraction
- `is_deleted` — Soft delete flag

**Indexes:**
- evidence_id (PK)
- dispute_id (FK)
- transaction_id (FK)
- verification_status
- ai_analysis_status
- created_at
- document_hash (for deduplication)
- content_hash (for deduplication)

**Relationships:** N:1 with disputes, N:1 with transactions

**Usage:** Central evidence storage, AI analysis results

---

### 9. RISK_ASSESSMENTS

```sql
CREATE TABLE risk_assessments (
    assessment_id VARCHAR PRIMARY KEY,
    transaction_id VARCHAR FK,
    risk_score FLOAT NOT NULL,
    risk_level VARCHAR NOT NULL,
    decision VARCHAR NOT NULL,
    model_version VARCHAR DEFAULT 'fraud-model-v2',
    created_at VARCHAR
);
```

**Purpose:** Fraud model evaluation results

**Columns:**
- `risk_score` — Raw fraud probability (0.0-1.0)
- `risk_level` — LOW (0-0.3), MEDIUM (0.3-0.7), HIGH (0.7-1.0)
- `decision` — ACCEPT, REVIEW, BLOCK
- `model_version` — fraud-model-v2

**Relationships:** N:1 with transactions

**Usage:** Fraud detection results, risk dashboard

---

### 10. DISPUTE_ASSESSMENTS

```sql
CREATE TABLE dispute_assessments (
    assessment_id VARCHAR PRIMARY KEY,
    dispute_id VARCHAR FK,
    analysis_version INTEGER DEFAULT 1,
    trigger VARCHAR DEFAULT 'DISPUTE_CREATED',
    risk_score FLOAT,
    fraud_probability FLOAT,
    win_probability FLOAT,
    confidence FLOAT,
    confidence_level VARCHAR DEFAULT 'MEDIUM',
    ml_recommendation VARCHAR,
    ai_recommendation VARCHAR,
    conflict_detected INTEGER DEFAULT 0,
    ml_results_json TEXT DEFAULT '{}',
    deepseek_results_json TEXT DEFAULT '{}',
    evidence_analysis_json TEXT DEFAULT '{}',
    model_versions_json TEXT DEFAULT '{}',
    generated_at VARCHAR
);
```

**Purpose:** AI case analysis results

**Key Columns:**
- `fraud_probability` — From fraud model (0-1)
- `win_probability` — From win model (0-1)
- `confidence` — Confidence score (0-1)
- `confidence_level` — LOW, MEDIUM, HIGH
- `ml_recommendation` — CONTEST, ACCEPT, INVESTIGATE, FRAUD
- `ai_recommendation` — CONTEST, ACCEPT, INVESTIGATE, FRAUD
- `conflict_detected` — 1 if ML ≠ AI
- `trigger` — DISPUTE_CREATED, EVIDENCE_ADDED, MERCHANT_REQUEST

**Relationships:** N:1 with disputes

**Usage:** Assessment display, recommendation engine, model consensus tracking

---

### 11. CHARGEBACK_PACKAGES

```sql
CREATE TABLE chargeback_packages (
    package_id VARCHAR PRIMARY KEY,
    dispute_id VARCHAR FK,
    transaction_id VARCHAR FK,
    package_status VARCHAR DEFAULT 'READY_FOR_REVIEW',
    merchant_position VARCHAR DEFAULT 'CONTEST',
    response_text TEXT DEFAULT '',
    package_data_json TEXT DEFAULT '{}',
    generator_version VARCHAR DEFAULT '1.0',
    created_at VARCHAR
);
```

**Purpose:** Generated response packages for submission

**Columns:**
- `merchant_position` — CONTEST, ACCEPT, INVESTIGATE
- `package_data_json` — Evidence summary, claim refutation, remediation
- `generator_version` — Package generator version

**Relationships:** N:1 with disputes, N:1 with transactions

**Usage:** Package generation, submission preparation

---

### 12. WEBHOOK_EVENTS

```sql
CREATE TABLE webhook_events (
    event_id VARCHAR PRIMARY KEY,
    idempotency_key VARCHAR UNIQUE,
    event_type VARCHAR DEFAULT 'payment.dispute.created',
    payload_json TEXT DEFAULT '{}',
    status VARCHAR DEFAULT 'RECEIVED',
    dispute_id VARCHAR,
    created_at VARCHAR,
    processed_at VARCHAR
);
```

**Purpose:** Webhook event tracking

**Status:** RECEIVED, PROCESSED, FAILED, DUPLICATE

**Relationships:** Optional FK to disputes (for correlation)

**Usage:** Webhook idempotency, event audit trail

---

## QUERY PATTERNS

### Frequent Queries

```python
# 1. Get all disputes for merchant
SELECT * FROM disputes 
WHERE customer_id = ? 
ORDER BY created_at DESC
LIMIT ?

# 2. Get dispute with all context
SELECT d.*, t.*, c.* 
FROM disputes d
JOIN transactions t ON d.transaction_id = t.transaction_id
JOIN customers c ON d.customer_id = c.customer_id
WHERE d.dispute_id = ?

# 3. Get all evidence for dispute
SELECT * FROM evidence
WHERE dispute_id = ? AND is_deleted = 0
ORDER BY created_at DESC

# 4. Get latest assessment for dispute
SELECT * FROM dispute_assessments
WHERE dispute_id = ?
ORDER BY generated_at DESC
LIMIT 1

# 5. Get transaction with all events
SELECT t.*, d.*, de.*, ra.*
FROM transactions t
LEFT JOIN disputes d ON t.transaction_id = d.transaction_id
LEFT JOIN dispute_events de ON d.dispute_id = de.dispute_id
LEFT JOIN risk_assessments ra ON t.transaction_id = ra.transaction_id
WHERE t.transaction_id = ?
```

### Potential N+1 Queries
⚠️ Dispute list formatting may trigger:
```
SELECT * FROM disputes → N disputes
  FOR EACH dispute:
    SELECT * FROM transactions WHERE transaction_id = ?
    SELECT * FROM customers WHERE customer_id = ?
    SELECT * FROM dispute_assessments WHERE dispute_id = ?
```

**Fix:** Use SQLAlchemy eager loading (joinedload, selectinload)

---

## INDEXING STRATEGY

### Recommended Indexes

| Table | Column | Type | Reason |
|-------|--------|------|--------|
| disputes | dispute_id | PK | Primary key |
| disputes | customer_id | FK | Join lookups |
| disputes | transaction_id | FK | Join lookups |
| disputes | status | Regular | Filtering |
| disputes | workflow_stage | Regular | Filtering |
| disputes | created_at | Regular | Sorting, filtering |
| evidence | dispute_id | FK | Join lookups |
| evidence | evidence_id | PK | Primary key |
| evidence | verification_status | Regular | Filtering |
| evidence | created_at | Regular | Sorting |
| transactions | customer_id | FK | Join lookups |
| transactions | timestamp | Regular | Sorting, filtering |
| dispute_assessments | dispute_id | FK | Latest assessment |
| dispute_events | dispute_id | FK | Timeline queries |
| dispute_events | timestamp | Regular | Sorting |

---

## PERFORMANCE CONSIDERATIONS

### Query Optimization
- Add pagination to prevent large result sets
- Use query batching for related entities
- Implement database connection pooling
- Monitor query execution times

### Scaling Strategy
- SQLite → PostgreSQL migration path clear
- No sharding keys needed yet
- Consider replication for HA
- Add read replicas for analytics

### Data Growth
- Evidence table may grow large (files stored as BLOBS)
- Consider archiving old disputes
- Implement data retention policies

---

**Document Status:** Complete schema documentation
**Last Updated:** September 2, 2026

# Backend Database Architecture & Schema Reference

## 1. Database Overview & Dual-Store Isolation

The backend utilizes **SQLAlchemy 2.x Declarative ORM** backed by **SQLite 3**. It implements a dual-database architecture ensuring total physical isolation between demonstration data and live operations:

| Database File | Connection URL | Primary Purpose |
|---|---|---|
| `data/demo_database.db` | `sqlite:///data/demo_database.db` | Seeded showcase scenarios (`DSP_SCENARIO_01` to `05`) and default sample cases. |
| `data/live_database.db` | `sqlite:///data/live_database.db` | Clean sandbox holding 15 realistic live transactions with 0 initial disputes; receives real webhook cases. |

---

## 2. Entity Schema Reference

### 2.1 Table: `customers`
- `customer_id` (VARCHAR, PK, Indexed)
- `account_age_days` (INTEGER, Default: 180)
- `verification_status` (VARCHAR, Default: 'VERIFIED')
- `country` (VARCHAR, Default: 'US')
- `previous_chargebacks` (INTEGER, Default: 0)
- `avg_transaction_amount_30d` (FLOAT, Default: 100.0)
- `created_at` (VARCHAR, ISO UTC)

### 2.2 Table: `transactions`
- `transaction_id` (VARCHAR, PK, Indexed)
- `customer_id` (VARCHAR, FK `customers.customer_id`, Indexed, Nullable: False)
- `merchant_id` (VARCHAR, Default: 'MERCHANT_001')
- `amount` (FLOAT, Nullable: False)
- `currency` (VARCHAR, Default: 'USD')
- `timestamp` (VARCHAR, ISO UTC)
- `payment_method` (VARCHAR, Default: 'credit_card')
- `merchant_category` (VARCHAR, Default: 'retail')
- `transaction_country` (VARCHAR, Default: 'US')
- `transaction_status` (VARCHAR, Default: 'SUCCESS')
- **12 ML Model Parameters**:
  - `transaction_hour` (INTEGER, Default: 12)
  - `account_age_days` (INTEGER, Default: 180)
  - `previous_chargebacks` (INTEGER, Default: 0)
  - `device_type` (VARCHAR, Default: 'mobile')
  - `is_international` (INTEGER, 0 or 1)
  - `is_high_risk_merchant` (INTEGER, 0 or 1)
  - `transaction_velocity_1h` (INTEGER, Default: 0)
  - `transaction_velocity_24h` (INTEGER, Default: 0)
  - `avg_transaction_amount_30d` (FLOAT, Default: 100.0)

### 2.3 Table: `payments`
- `payment_id` (VARCHAR, PK, Indexed)
- `transaction_id` (VARCHAR, FK `transactions.transaction_id`, Indexed, Nullable: False)
- `customer_id` (VARCHAR, FK `customers.customer_id`, Nullable: False)
- `payment_method` (VARCHAR, Default: 'credit_card')
- `card_network` (VARCHAR, Default: 'visa')
- `last4` (VARCHAR, Default: '4242')
- `avs_match` (VARCHAR, Default: 'Y')
- `cvv_match` (VARCHAR, Default: 'Y')
- `auth_code` (VARCHAR, Default: 'AUTH123456')
- `payment_status` (VARCHAR, Default: 'CAPTURED')
- `created_at` (VARCHAR, ISO UTC)

### 2.4 Table: `orders` & `fulfillments`
- **`orders`**:
  - `order_id` (VARCHAR, PK, Indexed)
  - `transaction_id` (VARCHAR, FK `transactions.transaction_id`, Unique, Indexed)
  - `customer_id` (VARCHAR, FK `customers.customer_id`)
  - `product_description` (VARCHAR)
  - `order_amount` (FLOAT, Nullable: False)
  - `order_status` (VARCHAR, Default: 'COMPLETED')
- **`fulfillments`**:
  - `fulfillment_id` (VARCHAR, PK, Indexed)
  - `order_id` (VARCHAR, FK `orders.order_id`, Unique, Indexed)
  - `shipping_status` (VARCHAR, Default: 'SHIPPED')
  - `tracking_number` (VARCHAR, Nullable: True)
  - `shipped_at` (VARCHAR, ISO UTC)
  - `delivered_at` (VARCHAR, ISO UTC)
  - `delivery_status` (VARCHAR, Nullable: True)

### 2.5 Table: `disputes`
- `dispute_id` (VARCHAR, PK, Indexed)
- `transaction_id` (VARCHAR, FK `transactions.transaction_id`, Indexed, Nullable: False)
- `customer_id` (VARCHAR, FK `customers.customer_id`, Indexed, Nullable: False)
- `reason_code` (VARCHAR, Indexed, Nullable: False)
- `reason_description` (VARCHAR, Default: '')
- `status` (VARCHAR, Default: 'OPEN', Indexed)
- `phase` (VARCHAR, Default: 'chargeback', Indexed)
- `respond_by` (VARCHAR, ISO UTC Deadline, Indexed)
- `workflow_stage` (VARCHAR, Default: 'DISPUTE_RAISED', Indexed)
- `case_source` (VARCHAR, Default: 'SIMULATED_RAZORPAY', Indexed)
- `merchant_attention_state` (VARCHAR, Default: 'ACTION_REQUIRED', Indexed)
- `ai_last_checked` (VARCHAR, ISO UTC)
- `created_at` (VARCHAR, ISO UTC, Indexed)

### 2.6 Table: `evidence`
- `evidence_id` (VARCHAR, PK, Indexed)
- `dispute_id` (VARCHAR, FK `disputes.dispute_id`, Indexed, Nullable: False)
- `transaction_id` (VARCHAR, FK `transactions.transaction_id`, Indexed, Nullable: False)
- `evidence_type` (VARCHAR, Indexed, Nullable: False)
- `title` (VARCHAR)
- `description` (VARCHAR)
- `source` (VARCHAR, Default: 'DATABASE')
- `source_reference_id` (VARCHAR, Nullable: True)
- `file_path` (VARCHAR, Nullable: True)
- `mime_type` (VARCHAR, Nullable: True)
- `file_size` (INTEGER, Default: 0)
- `document_hash` (VARCHAR, SHA-256 Digest, Indexed)
- `content_hash` (VARCHAR, SHA-256 Digest of text+facts, Indexed)
- `raw_content` (TEXT, Nullable: True)
- `extracted_text` (TEXT, Nullable: True)
- `content_json` (TEXT, Default: '{}')
- `key_entities_json` (TEXT, Default: '{}')
- `evidence_data_json` (TEXT, Default: '{}')
- `verification_status` (VARCHAR, Default: 'UNVERIFIED', Indexed)
- `verification_confidence` (FLOAT, Default: 1.0)
- `verification_errors_json` (TEXT, Default: '[]')
- `approval_status` (VARCHAR, Default: 'PENDING_APPROVAL', Indexed)
- `approved_at` (VARCHAR, Nullable: True)
- `approved_by` (VARCHAR, Nullable: True)
- `ai_analysis_json` (TEXT, Default: '{}')
- `ai_analysis_status` (VARCHAR, Default: 'PENDING', Indexed)
- `ai_analyzed_at` (VARCHAR, Nullable: True)
- `ai_error` (TEXT, Nullable: True)
- `created_at` (VARCHAR, ISO UTC, Indexed)
- `updated_at` (VARCHAR, ISO UTC)
- `is_deleted` (INTEGER, Default: 0, Indexed)

### 2.7 Table: `dispute_assessments`
- `assessment_id` (VARCHAR, PK, Indexed)
- `dispute_id` (VARCHAR, FK `disputes.dispute_id`, Indexed, Nullable: False)
- `analysis_version` (INTEGER, Default: 1)
- `trigger` (VARCHAR, Default: 'DISPUTE_CREATED')
- `risk_score` (FLOAT, Default: 0.0)
- `fraud_probability` (FLOAT, Default: 0.0)
- `win_probability` (FLOAT, Default: 0.5)
- `confidence` (FLOAT, Default: 0.5)
- `confidence_level` (VARCHAR, Default: 'MEDIUM')
- `ml_recommendation` (VARCHAR, Default: 'REVIEW')
- `ai_recommendation` (VARCHAR, Default: 'REVIEW')
- `conflict_detected` (INTEGER, Default: 0)
- `ml_results_json` (TEXT, Default: '{}')
- `deepseek_results_json` (TEXT, Default: '{}')
- `evidence_analysis_json` (TEXT, Default: '{}')
- `model_versions_json` (TEXT, Default: '{}')
- `generated_at` (VARCHAR, ISO UTC)

### 2.8 Table: `dispute_events` (Audit Trail)
- `event_id` (VARCHAR, PK, Indexed)
- `dispute_id` (VARCHAR, FK `disputes.dispute_id`, Indexed, Nullable: False)
- `event_type` (VARCHAR, Indexed, Nullable: False)
- `title` (VARCHAR, Nullable: False)
- `description` (TEXT, Default: '')
- `timestamp` (VARCHAR, ISO UTC, Indexed)
- `actor_type` (VARCHAR, Default: 'SYSTEM')
- `previous_stage` (VARCHAR, Nullable: True)
- `new_stage` (VARCHAR, Nullable: True)
- `metadata_json` (TEXT, Default: '{}')

### 2.9 Table: `chargeback_packages`
- `package_id` (VARCHAR, PK, Indexed)
- `dispute_id` (VARCHAR, FK `disputes.dispute_id`, Indexed, Nullable: False)
- `transaction_id` (VARCHAR, FK `transactions.transaction_id`, Indexed, Nullable: False)
- `package_status` (VARCHAR, Default: 'READY_FOR_REVIEW')
- `merchant_position` (VARCHAR, Default: 'CONTEST')
- `response_text` (TEXT, Default: '')
- `package_data_json` (TEXT, Default: '{}')
- `generator_version` (VARCHAR, Default: '1.0')
- `created_at` (VARCHAR, ISO UTC)

### 2.10 Table: `webhook_events`
- `event_id` (VARCHAR, PK, Indexed)
- `idempotency_key` (VARCHAR, Indexed, Nullable: True)
- `event_type` (VARCHAR, Default: 'payment.dispute.created')
- `payload_json` (TEXT, Default: '{}')
- `status` (VARCHAR, Default: 'RECEIVED')
- `dispute_id` (VARCHAR, Indexed, Nullable: True)
- `created_at` (VARCHAR, ISO UTC)
- `processed_at` (VARCHAR, Nullable: True)

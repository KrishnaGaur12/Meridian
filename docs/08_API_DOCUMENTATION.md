# COMPLETE API DOCUMENTATION

## API Overview

**Base URL:** `http://localhost:8000` (development)

**API Version:** 2.0.0

**Framework:** FastAPI with Pydantic validation

**Authentication:** None (demo mode) / Bearer Token ready (production)

**Content-Type:** application/json

**CORS:** Enabled for localhost:5173

---

## ENDPOINT CATALOG

### 1. HEALTH & SYSTEM ENDPOINTS

#### GET /health
Health check endpoint
```
Request: GET /health
Response: 200 OK
  {
    "status": "healthy",
    "timestamp": "2026-09-02T10:00:00Z",
    "uptime_seconds": 3600
  }
```

#### GET /system/status
System configuration and status
```
Request: GET /system/status
Response: 200 OK
  {
    "mode": "demo",  // or "production"
    "deepseek_enabled": true,
    "ml_models_loaded": true,
    "database_status": "connected",
    "version": "2.0.0"
  }
```

#### GET /system/config
Configuration details
```
Request: GET /system/config?include_api_keys=false
Response: 200 OK
  {
    "deepseek_model": "deepseek-chat",
    "fraud_model": "fraud_v2_pipeline.joblib",
    "win_model": "win_pipeline.joblib",
    "features": ["fraud_detection", "evidence_analysis", "win_probability"]
  }
```

---

### 2. DISPUTE ENDPOINTS

#### GET /disputes
List all disputes with pagination and filtering
```
Request: GET /disputes?page=1&page_size=20&status=OPEN&workflow_stage=DISPUTE_RAISED
Query Params:
  - page (int): 1-indexed page number
  - page_size (int): items per page (1-200, default 20)
  - limit (int): max items to return
  - offset (int): skip N items
  - status (str): OPEN, UNDER_REVIEW, WON, LOST, CLOSED
  - workflow_stage (str): DISPUTE_RAISED, EVIDENCE_COLLECTION, AI_ANALYSIS, MERCHANT_REVIEW, SUBMITTED
  - case_source (str): DEMO, SIMULATED_RAZORPAY, REAL_RAZORPAY
  - merchant_attention_state (str): ACTION_REQUIRED, REVIEW_RECOMMENDED, AI_HANDLING, WAITING
  - search (str): search by dispute_id or transaction_id

Response: 200 OK - Array[DisputeResponseSchema]
  [
    {
      "dispute_id": "DISPUTE_001",
      "transaction_id": "TXN_001",
      "customer_id": "CUST_001",
      "reason_code": "chargeback",
      "reason_description": "Customer claims unauthorized transaction",
      "status": "OPEN",
      "phase": "chargeback",
      "respond_by": "2026-09-09T10:00:00Z",
      "workflow_stage": "DISPUTE_RAISED",
      "merchant_attention_state": "ACTION_REQUIRED",
      "amount": 99.99,
      "currency": "USD",
      "remaining_hours": 120,
      "remaining_time_human": "5 days",
      "is_overdue": false,
      "deadline_status": "PENDING",
      "urgency_level": "MEDIUM",
      "created_at": "2026-09-02T10:00:00Z"
    }
  ]

Status Codes:
  - 200: Success
  - 400: Bad request (invalid query params)
  - 500: Server error
```

**PERFORMANCE NOTE:** [NOT VERIFIED - POTENTIAL BOTTLENECK]
Disputes list may load slowly when returning large result sets without proper pagination. No confirmed N+1 queries detected but response serialization may be heavy.

#### POST /disputes
Create a new dispute
```
Request: POST /disputes
Body: DisputeCreateSchema
  {
    "transaction_id": "TXN_001",
    "reason_code": "chargeback",
    "reason_description": "Customer claims unauthorized transaction",
    "respond_by": "2026-09-09T10:00:00Z",
    "case_source": "SIMULATED_RAZORPAY"
  }

Response: 201 Created - DisputeResponseSchema
  (same as GET /disputes response item)

Status Codes:
  - 201: Created
  - 400: Invalid transaction or missing fields
  - 404: Transaction not found
  - 500: Server error
```

#### GET /disputes/{dispute_id}
Get single dispute details
```
Request: GET /disputes/{dispute_id}
Response: 200 OK - DisputeResponseSchema

Status Codes:
  - 200: Success
  - 404: Dispute not found
  - 500: Server error
```

#### GET /disputes/{dispute_id}/timeline
Get dispute event timeline
```
Request: GET /disputes/{dispute_id}/timeline
Response: 200 OK - Array[DisputeTimelineEventSchema]
  [
    {
      "event_id": "EVT_001",
      "timestamp": "2026-09-02T10:00:00Z",
      "event_type": "DISPUTE_CREATED",
      "title": "Dispute raised by Razorpay",
      "description": "New chargeback dispute created",
      "actor_type": "SYSTEM",
      "previous_stage": null,
      "new_stage": "DISPUTE_RAISED"
    }
  ]

Status Codes:
  - 200: Success
  - 404: Dispute not found
  - 500: Server error
```

#### GET /disputes/{dispute_id}/analysis
Get AI case analysis (triggers full analysis)
```
Request: GET /disputes/{dispute_id}/analysis
Response: 200 OK - DisputeCaseAnalysisSchema
  {
    "dispute_id": "DISPUTE_001",
    "analysis_version": 1,
    "fraud_probability": 0.15,
    "risk_level": "LOW",
    "evidence_completeness": 0.75,
    "evidence_quality": "GOOD",
    "win_probability": 0.82,
    "confidence": 0.88,
    "confidence_level": "HIGH",
    "ml_recommendation": "CONTEST",
    "ai_recommendation": "CONTEST",
    "contradictions": 0,
    "decision_reasons": [
      "Low fraud probability indicates legitimate transaction",
      "Strong evidence of delivery provided by merchant",
      "Consistent narrative across all evidence"
    ],
    "explanation": "AI analysis indicates strong case for contesting this chargeback...",
    "generated_at": "2026-09-02T10:05:00Z"
  }

Status Codes:
  - 200: Success
  - 404: Dispute not found
  - 500: Server error (if AI analysis fails)

IMPORTANT: This endpoint triggers:
1. Full fraud model evaluation
2. DeepSeek LLM evidence analysis
3. Win probability calculation
4. ML model consensus check
May take 3-5 seconds if DeepSeek API involved
```

#### POST /disputes/{dispute_id}/transition
Transition dispute to new workflow stage
```
Request: POST /disputes/{dispute_id}/transition
Body: DisputeWorkflowTransitionSchema
  {
    "target_stage": "EVIDENCE_COLLECTION",
    "event_title": "Merchant beginning evidence upload",
    "event_desc": "Transitioned by merchant"
  }

Response: 200 OK - DisputeResponseSchema

Valid Stage Transitions:
  DISPUTE_RAISED → EVIDENCE_COLLECTION
  EVIDENCE_COLLECTION → AI_ANALYSIS
  AI_ANALYSIS → MERCHANT_REVIEW
  MERCHANT_REVIEW → SUBMITTED
  (and various re-do/rework transitions)

Status Codes:
  - 200: Success
  - 400: Invalid state transition
  - 404: Dispute not found
  - 500: Server error
```

#### GET /disputes/{dispute_id}/readiness
Check submission readiness
```
Request: GET /disputes/{dispute_id}/readiness
Response: 200 OK - DisputeCaseReadinessSchema
  {
    "dispute_id": "DISPUTE_001",
    "readiness_score": 0.85,
    "readiness_level": "READY",
    "can_submit": true,
    "missing_requirements": [],
    "evidence_summary": {
      "total_evidence": 4,
      "verified_evidence": 4,
      "rejected_evidence": 0
    },
    "validation_errors": [],
    "next_recommended_action": "SUBMIT"
  }

Status Codes:
  - 200: Success
  - 404: Dispute not found
  - 500: Server error
```

#### POST /disputes/{dispute_id}/submit
Submit dispute to Razorpay
```
Request: POST /disputes/{dispute_id}/submit
Body: DisputeSubmitRequestSchema (optional)
  {
    "merchant_position": "CONTEST",
    "note": "Strong evidence supports full reversal"
  }

Response: 200 OK - DisputeSubmitResponseSchema
  {
    "dispute_id": "DISPUTE_001",
    "submission_status": "SUBMITTED",
    "submission_timestamp": "2026-09-02T10:10:00Z",
    "gateway_reference_id": "GWY_REF_XXXXX",
    "package_id": "PKG_001"
  }

Status Codes:
  - 200: Success
  - 400: Not ready to submit / validation failed
  - 404: Dispute not found
  - 500: Server error
```

---

### 3. EVIDENCE ENDPOINTS

#### GET /disputes/{dispute_id}/evidence
Get evidence package for dispute
```
Request: GET /disputes/{dispute_id}/evidence
Response: 200 OK - EvidencePackageSchema
  {
    "dispute_id": "DISPUTE_001",
    "evidence_items": [
      {
        "evidence_id": "EVI_001",
        "evidence_type": "delivery_proof",
        "title": "Shipment Tracking",
        "verification_status": "VERIFIED",
        "created_at": "2026-09-02T10:00:00Z"
      }
    ],
    "total_items": 4,
    "verified_items": 4,
    "rejected_items": 0,
    "completeness_score": 0.85,
    "quality_assessment": "GOOD"
  }

Status Codes:
  - 200: Success
  - 404: Dispute not found
  - 500: Server error
```

#### POST /disputes/{dispute_id}/evidence
Upload new evidence
```
Request: POST /disputes/{dispute_id}/evidence
Content-Type: multipart/form-data

Form Data:
  - file (binary): PDF, image, or text file
  - evidence_type (str): delivery_proof, order_confirmation, communication, payment_receipt, etc.
  - title (str): Evidence title/name
  - description (str): Optional description
  - source (str): MERCHANT_UPLOAD (default)

Response: 200 OK - EvidenceDetailSchema
  {
    "evidence_id": "EVI_002",
    "dispute_id": "DISPUTE_001",
    "evidence_type": "delivery_proof",
    "title": "Tracking Document",
    "verification_status": "UNVERIFIED",
    "ai_analysis_status": "PENDING",
    "ai_analysis": null,
    "created_at": "2026-09-02T10:05:00Z"
  }

Triggers:
  1. File extraction (PyPDF for PDF, OCR for images)
  2. Text extraction and storage
  3. DeepSeek LLM analysis (async or background)
  4. Dispute assessment recalculation

Status Codes:
  - 200: Success
  - 400: Invalid file or missing fields
  - 404: Dispute not found
  - 413: File too large (>10MB)
  - 500: Server error (file processing failure)
```

#### GET /disputes/{dispute_id}/evidence/{evidence_id}
Get single evidence item
```
Request: GET /disputes/{dispute_id}/evidence/{evidence_id}
Response: 200 OK - EvidenceDetailSchema
  {
    "evidence_id": "EVI_001",
    "dispute_id": "DISPUTE_001",
    "evidence_type": "delivery_proof",
    "title": "Tracking",
    "description": "UPS tracking confirming delivery",
    "verification_status": "VERIFIED",
    "approval_status": "APPROVED",
    "approved_at": "2026-09-02T10:06:00Z",
    "approved_by": "MERCHANT",
    "extracted_text": "[extracted PDF/image text]",
    "data": { },
    "ai_analysis": {
      "completeness_score": 85,
      "completeness_summary": "Evidence shows clear delivery confirmation...",
      "missing_evidence": [],
      "contradictions": [],
      "key_entities": { "carrier": "UPS", "date_delivered": "2026-09-01" },
      "claims_validation": { "claim": "Item delivered", "status": "VERIFIED" },
      "risk_flags": [],
      "overall_assessment": "SUFFICIENT"
    },
    "ai_analysis_status": "COMPLETE",
    "ai_analyzed_at": "2026-09-02T10:05:30Z",
    "created_at": "2026-09-02T10:00:00Z"
  }

Status Codes:
  - 200: Success
  - 404: Evidence or dispute not found
  - 500: Server error
```

#### POST /disputes/{dispute_id}/evidence/{evidence_id}/approve
Approve evidence item
```
Request: POST /disputes/{dispute_id}/evidence/{evidence_id}/approve
Body: ApproveEvidenceRequest
  {
    "approved_by": "MERCHANT"
  }

Response: 200 OK - EvidenceApprovalResponseSchema

Status Codes:
  - 200: Success
  - 404: Evidence not found
  - 400: Invalid state transition
  - 500: Server error

Effect:
  - Sets evidence.approval_status = "APPROVED"
  - Sets evidence.approved_at = current timestamp
  - Triggers dispute assessment recalculation
```

#### POST /disputes/{dispute_id}/evidence/{evidence_id}/reject
Reject evidence item
```
Request: POST /disputes/{dispute_id}/evidence/{evidence_id}/reject
Body: RejectEvidenceRequest
  {
    "reason": "Does not support merchant claims"
  }

Response: 200 OK

Status Codes:
  - 200: Success
  - 404: Evidence not found
  - 400: Invalid state
  - 500: Server error

Effect:
  - Sets evidence.verification_status = "REJECTED"
  - Marks evidence as deleted (soft delete)
  - Recalculates dispute assessment
```

---

### 4. TRANSACTION & RISK ENDPOINTS

#### GET /transactions
List transactions
```
Request: GET /transactions?limit=20&offset=0&customer_id=CUST_001
Response: 200 OK - Array[TransactionSchema]

Status Codes:
  - 200: Success
  - 400: Bad query params
  - 500: Server error
```

#### POST /transactions
Create transaction
```
Request: POST /transactions
Body: TransactionCreateSchema
  {
    "customer_id": "CUST_001",
    "amount": 99.99,
    "currency": "USD",
    "payment_method": "credit_card",
    "merchant_category": "retail"
  }

Response: 201 Created - TransactionSchema

Status Codes:
  - 201: Created
  - 400: Invalid request
  - 500: Server error

Note: Auto-triggers fraud model evaluation
```

#### GET /transactions/{transaction_id}/risk
Get transaction risk assessment
```
Request: GET /transactions/{transaction_id}/risk
Response: 200 OK
  {
    "transaction_id": "TXN_001",
    "fraud_probability": 0.15,
    "risk_level": "LOW",
    "risk_score": 0.15,
    "model_version": "fraud-model-v2",
    "timestamp": "2026-09-02T10:00:00Z"
  }

Status Codes:
  - 200: Success
  - 404: Transaction not found
  - 500: Server error
```

---

### 5. AI & RECOMMENDATION ENDPOINTS

#### POST /ai/analyze-evidence
Analyze evidence with DeepSeek
```
Request: POST /ai/analyze-evidence
Body:
  {
    "evidence_text": "Tracking shows delivery on Sept 1...",
    "evidence_type": "delivery_proof",
    "dispute_context": { "reason": "chargeback", "amount": 99.99 }
  }

Response: 200 OK - EvidenceAnalysisResultSchema
  {
    "completeness_score": 85,
    "completeness_summary": "Sufficient evidence of delivery",
    "missing_evidence": ["customer_signature", "photo_proof"],
    "contradictions": [],
    "key_entities": { "date": "2026-09-01", "carrier": "UPS" },
    "claims_validation": [
      { "claim": "Item delivered", "status": "VERIFIED", "evidence": "Tracking shows delivered" }
    ],
    "risk_flags": [],
    "overall_assessment": "SUFFICIENT"
  }

Status Codes:
  - 200: Success
  - 400: Invalid input
  - 503: DeepSeek unavailable (fallback response)
  - 500: Server error

Performance:
  - Typical: 1-3 seconds (if DeepSeek available)
  - Fallback: <100ms (rule-based analysis)
```

---

### 6. PACKAGE & RESPONSE ENDPOINTS

#### POST /package/generate
Generate chargeback response package
```
Request: POST /package/generate
Body:
  {
    "dispute_id": "DISPUTE_001",
    "merchant_position": "CONTEST",
    "tone": "professional"
  }

Response: 200 OK - ChargebackPackageSchema
  {
    "package_id": "PKG_001",
    "dispute_id": "DISPUTE_001",
    "status": "READY_FOR_REVIEW",
    "merchant_position": "CONTEST",
    "response_text": "[Generated response content]",
    "package_data": {
      "evidence_summary": { ... },
      "claim_refutation": "...",
      "remediation": "..."
    },
    "created_at": "2026-09-02T10:00:00Z"
  }

Status Codes:
  - 200: Success
  - 404: Dispute not found
  - 400: Cannot generate package
  - 500: Server error
```

---

### 7. DEMO & SIMULATION ENDPOINTS

#### GET /demo/scenarios
List available demo scenarios
```
Request: GET /demo/scenarios
Response: 200 OK
  [
    { "id": 1, "name": "Contest (Legitimate Transaction)", "file": "scenario_1_contest.json" },
    { "id": 2, "name": "Accept (Refund Case)", "file": "scenario_2_accept.json" },
    { "id": 3, "name": "Investigate (Unclear)", "file": "scenario_3_investigate.json" },
    { "id": 4, "name": "Fraud", "file": "scenario_4_high_fraud.json" },
    { "id": 5, "name": "Duplicate", "file": "scenario_5_duplicate.json" }
  ]

Status Codes:
  - 200: Success
  - 500: Server error
```

#### POST /demo/run/{scenario_id}
Run demo scenario
```
Request: POST /demo/run/1
Response: 200 OK - RiskAnalysisResultSchema
  (Full analysis result for that scenario)

Status Codes:
  - 200: Success
  - 404: Scenario not found
  - 500: Server error
```

---

## API RESPONSE SCHEMAS

### DisputeResponseSchema
```
{
  "dispute_id": str,
  "transaction_id": str,
  "customer_id": str,
  "reason_code": str,
  "reason_description": str,
  "status": str,  # OPEN, UNDER_REVIEW, WON, LOST, CLOSED
  "phase": str,  # retrieval, chargeback, pre_arbitration, arbitration, fraud
  "respond_by": str,  # UTC ISO timestamp
  "workflow_stage": str,
  "merchant_attention_state": str,
  "amount": float,
  "currency": str,
  "remaining_hours": int,
  "remaining_time_human": str,
  "is_overdue": bool,
  "deadline_status": str,
  "urgency_level": str,
  "created_at": str,
  "ai_last_checked": str
}
```

### DisputeCaseAnalysisSchema
```
{
  "dispute_id": str,
  "fraud_probability": float,  # 0-1
  "risk_level": str,  # LOW, MEDIUM, HIGH
  "evidence_completeness": float,  # 0-1
  "evidence_quality": str,  # POOR, FAIR, GOOD, EXCELLENT
  "win_probability": float,  # 0-1
  "confidence": float,  # 0-1
  "confidence_level": str,  # LOW, MEDIUM, HIGH
  "ml_recommendation": str,  # CONTEST, ACCEPT, INVESTIGATE, FRAUD
  "ai_recommendation": str,  # CONTEST, ACCEPT, INVESTIGATE, FRAUD
  "contradictions": int,
  "decision_reasons": list[str],
  "explanation": str,
  "generated_at": str
}
```

---

## ERROR HANDLING

### Standard Error Response
```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE"
}
```

### Common HTTP Status Codes
- **200:** OK - Request successful
- **201:** Created - Resource created
- **400:** Bad Request - Invalid input/parameters
- **404:** Not Found - Resource doesn't exist
- **422:** Unprocessable Entity - Validation error
- **500:** Internal Server Error - Server error
- **503:** Service Unavailable - External service down (e.g., DeepSeek)

---

## PERFORMANCE CHARACTERISTICS

| Endpoint | Typical Latency | Max Latency | Notes |
|----------|-----------------|-------------|-------|
| GET /disputes | 50-200ms | 2000ms | May slow with large result sets |
| GET /disputes/{id}/analysis | 2000-5000ms | 30000ms | Includes DeepSeek LLM call |
| POST /disputes/{id}/evidence | 500-2000ms | 35000ms | Includes file processing + AI analysis |
| GET /transactions/{id}/risk | 10-50ms | 500ms | Fast model inference |
| POST /ai/analyze-evidence | 1000-3000ms | 30000ms | DeepSeek API dependent |

---

**API Documentation Status:** Complete
**Last Updated:** September 2, 2026

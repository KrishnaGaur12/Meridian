# Backend Testing & Quality Assurance Reference

## 1. Test Suite Overview

The backend maintains an automated testing suite comprising **29 test files** with **176 test cases** achieving a **100% pass rate**.

- **Test Runner**: Pytest 9.1.1
- **Python Version**: Python 3.13.1
- **Async Testing**: `anyio` (4.14.2)
- **Execution Command**: `.venv\Scripts\pytest` or `pytest`

```
================ 176 passed, 6124 warnings in 89.67s ================
```

---

## 2. Test File Breakdown & Scope

| Test Suite File | Tests | Primary Scope & Verified Behavior |
|---|---|---|
| `test_ai_response.py` | 4 | Structured AI rebuttal response generation and schema compliance. |
| `test_api_database.py` | 4 | Database session injection, SQLite transactions, and model CRUD operations. |
| `test_api_integration_production.py` | 10 | Production endpoint integration, sanitized error handling, and header propagation. |
| `test_api_routes.py` | 7 | REST API route status codes, query parameter filtering, and payload serialization. |
| `test_backend_evidence_lifecycle_fix.py` | 10 | Evidence file upload, SHA-256 hashing, unreadable file rejection, and replacement. |
| `test_chargeback_package.py` | 2 | Chargeback package assembly and idempotent persistence. |
| `test_components.py` | 9 | Core components: completeness, confidence, explanation, recommendation, and reason classifier. |
| `test_deepseek_ai_service.py` | 11 | DeepSeek LLM client communication, prompt building, response parsing, and cache invalidation. |
| `test_delivery_fabrication_fix.py` | 6 | Anti-hallucination verification ensuring no fabricated delivery claims when POD is missing. |
| `test_dispute_lifecycle.py` | 1 | Dispute state transitions and deadline calculations. |
| `test_e2e_full_package.py` | 1 | Complete end-to-end representment bundle creation. |
| `test_e2e_workflow.py` | 1 | End-to-end dispute ingestion, analysis, and resolution workflow. |
| `test_evidence_ai_verification.py` | 6 | DeepSeek evidence verification pipeline, fact extraction, and status persistence. |
| `test_evidence_approval_and_real_ml.py` | 5 | Evidence merchant approval triggering real ML win probability recalculation. |
| `test_evidence_engine.py` | 5 | EvidenceEngine requirements mapping against database records. |
| `test_final_phase.py` | 6 | Final lifecycle phases: pre-arbitration, arbitration, and fraud. |
| `test_fraud_v2.py` | 8 | XGBoost Fraud Model V2 prediction accuracy and 12-feature extraction. |
| `test_fraud_v2_integration.py` | 14 | Integration of Fraud V2 with transaction schema and database models. |
| `test_live_backend_e2e.py` | 17 | Comprehensive live backend operations: Webhooks, live seed, reset, and gate checks. |
| `test_merchant_productization.py` | 3 | Merchant attention states (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`). |
| `test_models.py` | 2 | SQLAlchemy ORM model relationships, foreign keys, and cascading deletes. |
| `test_package_api_routes.py` | 4 | Package generation, inspection, and retrieval endpoints. |
| `test_pipeline.py` | 1 | Risk engine pipeline integration. |
| `test_productization_final.py` | 16 | Production readiness: submission gate, deadline info, and outcome simulation. |
| `test_real_dispute_lifecycle_architecture.py` | 9 | Real dispute lifecycle architecture and event audit trail logging. |
| `test_round2_workflow.py` | 2 | Second-round dispute workflow and representment rework. |
| `test_scenarios.py` | 5 | Verification across all 5 benchmark dispute scenarios. |
| `test_semantic_rules.py` | 7 | Contradiction detector and rule-based heuristics. |

---

## 3. Running Automated Tests

```bash
# Run entire test suite
pytest

# Run specific test file
pytest tests/test_live_backend_e2e.py

# Run with verbose output
pytest -v

# Run with stdout printing enabled
pytest -s
```

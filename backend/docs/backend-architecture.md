# Backend Architecture Reference

## 1. Architectural Overview

The **Razorpay AI Risk Manager** backend is structured around a decoupled, 6-layer architecture designed for high availability, deterministic risk analysis, and anti-hallucinatory AI defense generation.

```
+-------------------------------------------------------------------------------+
|                            1. CLIENT & INTEGRATION                            |
|  - RiskDesk Dashboard (Vite/React)       - Razorpay Gateway Webhooks (HTTP)  |
|  - CLI Interface (main.py)               - Real-Time SSE Stream (/events)     |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
|                             2. API & ROUTER LAYER                             |
|  - main.py (Lifespan, CORS, Custom Error Handlers)                            |
|  - src/api/router.py (12 Modular Domain Sub-Routers)                          |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
|                        3. VALIDATION & CONTEXT LAYER                          |
|  - Pydantic V2 Request & Response Schemas (src/schemas/api_schemas.py)        |
|  - Database Mode Resolution: DEMO vs LIVE (src/database/database.py)          |
+-------------------------------------------------------------------------------+
                                        │
                                        ▼
+-------------------------------------------------------------------------------+
|                        4. SERVICE & ORCHESTRATION LAYER                       |
|  - Dispute Analysis Service:  src/pipeline/analysis_service.py                |
|  - AI Autopilot Engine:       src/pipeline/autopilot.py                       |
|  - Chargeback Package Engine: src/chargeback/service.py                       |
|  - AI Language Coordinator:   src/services/ai/service.py                      |
|  - Action Decision Engine:    src/actions/engine.py                           |
|  - Explainability Engine:     src/explainability/engine.py                    |
+-------------------+-----------------------+-----------------------------------+
                    │                       │
                    ▼                       ▼
+-----------------------+       +-----------------------+
|  5a. ML / AI ENGINES  |       | 5b. EVIDENCE PIPELINE |
| - XGBoost Fraud V2    |       | - PyPDF Text Parser   |
| - Win Model (RF-150)  |       | - Pillow Metadata     |
| - DeepSeek LLM Client |       | - Fact Extractor      |
| - Fallback Heuristics |       | - SHA-256 Hasher      |
+-----------------------+       +-----------------------+
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
+-------------------------------------------------------------------------------+
|                        6. REPOSITORY & PERSISTENCE LAYER                      |
|  - src/database/repository.py (Encapsulated CRUD, Joins, Gate Enforcement)    |
|  - SQLAlchemy 2.0 Declarative Models (src/database/models.py)                 |
|  - Isolated Dual SQLite Stores: data/demo_database.db & data/live_database.db |
+-------------------------------------------------------------------------------+
```

---

## 2. Layer Responsibilities & Source Evidence

### 2.1 API & Router Layer
- **Location**: `src/api/router.py`, `src/api/routes/`
- **Responsibility**: Exposes 38 REST endpoints across 12 domain routers:
  - `health.py`: System health and ML baseline health metrics.
  - `mode.py` & `system.py`: Context-aware SQLite database mode switching.
  - `transactions.py` & `risk.py`: Transaction creation, retrieval, and risk scoring.
  - `disputes.py`: Dispute CRUD, timeline retrieval, readiness gate calculation, and submission.
  - `evidence.py`: Evidence uploading, parsing, verification, editing, replacing, approving, and deleting.
  - `webhooks.py`: Real-time Razorpay webhook ingestion with idempotency.
  - `events.py`: Server-Sent Events (SSE) broadcaster.
  - `package.py` & `response.py`: Chargeback representment bundle generation.
  - `demo.py`: Demo scenario dispute simulation.

### 2.2 Service & Pipeline Layer
- **Location**: `src/pipeline/`, `src/services/`, `src/chargeback/`, `src/actions/`
- **Key Symbols**:
  - `src.pipeline.analysis_service.analyze_dispute`: Executes the authoritative dispute intelligence pipeline on every state transition.
  - `src.pipeline.autopilot.AIAutopilot`: Manages automated case reassessments and before/after impact deltas.
  - `src.actions.engine.NextBestActionEngine`: Deterministically calculates the next operational priority for the merchant.
  - `src.explainability.engine.AIExplainabilityEngine`: Provides model-derived and rule-derived feature explanations for Fraud V2 and Win Probability.

### 2.3 Machine Learning Subsystem
- **Location**: `src/components/`, `models/`
- **Key Symbols**:
  - `src.components.fraud_model_v2.FraudModelV2Wrapper`: XGBoost classifier trained on 10,000 transaction samples across 12 features.
  - `src.components.win_probability.WinProbabilityModelWrapper`: Random Forest classifier trained on 13 dispute features predicting defense win likelihood.

### 2.4 AI Language & Verification Subsystem
- **Location**: `src/services/ai/`, `src/response/`
- **Key Symbols**:
  - `src.services.ai.deepseek_client.DeepSeekClient`: Timeout-bounded HTTP client for DeepSeek OpenAI-compatible chat completions.
  - `src.services.ai.prompt_builder.PromptBuilder`: Constructs anti-hallucination prompts injecting parsed document text and dispute context.
  - `src.services.ai.evidence_analysis_service.EvidenceAnalysisService`: Evaluates evidence authenticity, relevance, and fact-matching.
  - `src.response.validator.ClaimEvidenceValidator`: Post-LLM verification gate that rejects any generated claim not backed by verified database evidence.

### 2.5 Data Access & Repository Layer
- **Location**: `src/database/repository.py`, `src/database/models.py`, `src/database/database.py`
- **Key Symbols**:
  - `src.database.models.*`: 12 SQLAlchemy ORM entities.
  - `src.database.repository.get_all_disputes`: High-performance query with lightweight `joinedload(Dispute.transaction)`.
  - `src.database.repository.get_case_readiness_and_gate`: Computes 0-100% readiness score and blocks premature submissions.
  - `src.database.repository.submit_dispute_package`: Issues gateway reference ID and transitions case to `SUBMITTED`.

---

## 3. Database Isolation Architecture

The backend implements strict physical isolation between demo cases and real live data:

```
                  Client Request
                        │
                        ▼
         resolve_database_mode(request)
          (Precedence: Header 'X-Database-Mode' > Query 'mode' > Global Server State)
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       Mode: "DEMO"           Mode: "LIVE"
             │                     │
             ▼                     ▼
    DemoSessionLocal()     LiveSessionLocal()
             │                     │
             ▼                     ▼
    data/demo_database.db  data/live_database.db
```

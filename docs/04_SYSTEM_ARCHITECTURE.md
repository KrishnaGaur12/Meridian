# SYSTEM ARCHITECTURE — RAZORPAY AI RISK MANAGER

## 1. HIGH-LEVEL SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ React 19 Frontend Application (localhost:5173)                        │  │
│  │ • TypeScript + Vite + Tailwind CSS                                   │  │
│  │ • Merchant Dashboard                                                 │  │
│  │ • Dispute Management UI                                              │  │
│  │ • Evidence Upload & Management                                       │  │
│  │ • AI Analysis Visualization                                          │  │
│  │ • Real-time Status Updates                                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↕
                        (REST API / JSON over HTTP)
                                    ↕
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API LAYER                                           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Application (localhost:8000)                                 │  │
│  │                                                                       │  │
│  │ Router Modules:                                                      │  │
│  │ • Health Check (/health)                                             │  │
│  │ • Mode Configuration (/mode)                                         │  │
│  │ • System Status (/system)                                            │  │
│  │ • Transactions (/transactions)                                       │  │
│  │ • Disputes (/disputes)                                               │  │
│  │ • Evidence (/evidence)                                               │  │
│  │ • Risk Assessment (/risk)                                            │  │
│  │ • AI Response (/response)                                            │  │
│  │ • Chargeback Package (/package)                                      │  │
│  │ • Webhooks (/webhooks)                                               │  │
│  │ • Events (/events)                                                   │  │
│  │ • Demo Mode (/demo)                                                  │  │
│  │                                                                       │  │
│  │ CORS Configuration:                                                  │  │
│  │ • localhost:5173                                                     │  │
│  │ • localhost:127.0.0.1:5173                                           │  │
│  │ • All HTTP methods allowed                                           │  │
│  │                                                                       │  │
│  │ Error Handling:                                                      │  │
│  │ • HTTP Exception Handler                                             │  │
│  │ • Validation Error Handler                                           │  │
│  │ • Database Error Handler                                             │  │
│  │ • Unhandled Exception Handler                                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                                           │
│                                                                              │
│  ┌────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ Repository Pattern         │  │ Service Classes                      │ │
│  │ • Dispute Repository       │  │ • AIService                          │ │
│  │ • Evidence Repository      │  │ • EvidenceAnalysisService            │ │
│  │ • Transaction Repository   │  │ • EvidenceEngine                     │ │
│  │ • Assessment Repository    │  │ • ChargebackPackageService           │ │
│  └────────────────────────────┘  │ • RiskEngine                         │ │
│                                   │ • DeepSeekClient                     │ │
│                                   │ • PromptBuilder                      │ │
│                                   │ • ResponseParser                     │ │
│                                   │ • EvidenceFileProcessor              │ │
│                                   └──────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ML/AI Services                                                         │ │
│  │ • FraudModelV2 (XGBoost inference)                                     │ │
│  │ • WinProbabilityModel (XGBoost inference)                              │ │
│  │ • EvidenceAnalyzer (DeepSeek LLM calls)                                │ │
│  │ • PromptBuilder (evidence → prompt construction)                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ SQLAlchemy ORM Layer                                                 │  │
│  │                                                                       │  │
│  │ Database: SQLite (development) / PostgreSQL (production ready)        │  │
│  │                                                                       │  │
│  │ Tables:                                                              │  │
│  │ • customers — Merchant/customer profile data                         │  │
│  │ • transactions — Payment transaction records                         │  │
│  │ • payments — Payment card/method details                             │  │
│  │ • orders — Order/fulfillment metadata                                │  │
│  │ • fulfillments — Shipping/delivery info                              │  │
│  │ • disputes — Chargeback disputes                                     │  │
│  │ • dispute_events — Workflow timeline events                          │  │
│  │ • evidence — Evidence items & analysis results                       │  │
│  │ • risk_assessments — Fraud risk scores                               │  │
│  │ • dispute_assessments — AI case analysis results                     │  │
│  │ • chargeback_packages — Generated response packages                  │  │
│  │ • webhook_events — Razorpay webhook records                          │  │
│  │                                                                       │  │
│  │ Features:                                                            │  │
│  │ • Auto-incrementing timestamps (UTC ISO format)                      │  │
│  │ • Cascade delete relationships                                       │  │
│  │ • Foreign key constraints                                            │  │
│  │ • Indexed columns for query performance                              │  │
│  │ • JSON column support for flexible schema                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                                         │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ DeepSeek LLM API                    │                                │  │
│  │ Base URL: https://api.deepseek.com  │                                │  │
│  │ Model: deepseek-chat                │                                │  │
│  │ Purpose: Evidence analysis & validation                              │  │
│  │                                                                       │  │
│  │ Features:                                                            │  │
│  │ • JSON mode for structured output                                    │  │
│  │ • Temperature: 0.2 (low randomness)                                  │  │
│  │ • Max tokens: 1500                                                   │  │
│  │ • Timeout: 30s per request                                           │  │
│  │ • Retry logic on failure                                             │  │
│  │ • Graceful fallback when unavailable                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. FRONTEND ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│ React 19 + TypeScript + Vite                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  App.tsx (Main Application)                                    │
│    ├── Router Setup (React Router v7)                          │
│    ├── Layout (AppLayout)                                      │
│    └── Pages/Routes                                            │
│                                                                 │
├─ pages/                                                        │
│  ├── Dashboard (transaction risk view, dispute list)          │
│  ├── DisputeDetails (case overview, timeline)                 │
│  ├── EvidenceManagement (upload, list, analyze)               │
│  ├── AIAnalysis (AI recommendations, analysis results)        │
│  ├── MerchantReview (evidence review & decision)              │
│  └── SubmissionConfirm (final review before submit)           │
│                                                                 │
├─ components/                                                   │
│  ├── disputes/                                                 │
│  │  ├── CaseHeader (dispute info header)                      │
│  │  ├── CaseOverviewTab (dispute details)                     │
│  │  ├── EvidenceSection (evidence list & mgmt)                │
│  │  ├── CaseAIAnalysisTab (AI analysis display)               │
│  │  ├── AIRecommendationSection (recommendation widget)       │
│  │  ├── CaseMerchantReviewTab (merchant review)               │
│  │  ├── CaseSubmissionTab (submission workflow)               │
│  │  ├── SubmissionModal (final submit confirmation)           │
│  │  ├── OutcomeCard (outcome/result display)                  │
│  │  └── WorkflowStepNav (workflow progress indicator)         │
│  ├── common/                                                   │
│  │  ├── Card, Button, Badge (UI primitives)                   │
│  │  ├── Modal, SearchBar (common components)                  │
│  │  ├── Skeleton (loading states)                             │
│  │  └── Table (data display)                                  │
│  └── layout/                                                   │
│     ├── Header (top navigation)                               │
│     └── SimulatorLayout (layout wrapper)                      │
│                                                                 │
├─ services/                                                     │
│  ├── api.ts (Axios HTTP client setup)                         │
│  ├── disputeService.ts (dispute API calls)                    │
│  ├── evidenceService.ts (evidence API calls)                  │
│  ├── transactionService.ts (transaction API calls)            │
│  ├── dashboardService.ts (dashboard data fetch)               │
│  ├── simulationService.ts (demo mode API)                     │
│  └── cacheService.ts (local state caching)                    │
│                                                                 │
├─ types/                                                        │
│  ├── dispute.ts (Dispute interfaces)                          │
│  ├── evidence.ts (Evidence interfaces)                         │
│  ├── transaction.ts (Transaction interfaces)                  │
│  ├── commandCenter.ts (Command center types)                  │
│  └── simulation.ts (Simulation mode types)                    │
│                                                                 │
└─ styles/                                                       │
   ├── tailwind.config (Tailwind configuration)                 │
   └── index.css (global styles)                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. BACKEND ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────┐
│ Python FastAPI Backend                                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
├─ main.py                                                        │
│  ├── FastAPI app initialization                                │
│  ├── CORS middleware setup                                     │
│  ├── Error handlers                                            │
│  ├── Database initialization                                  │
│  └── CLI interface                                             │
│                                                                 │
├─ src/                                                          │
│  ├── api/                                                      │
│  │  ├── router.py (main router orchestration)                 │
│  │  └── routes/                                               │
│  │     ├── health.py (health check endpoint)                  │
│  │     ├── disputes.py (dispute CRUD endpoints)               │
│  │     ├── evidence.py (evidence management)                  │
│  │     ├── transactions.py (transaction endpoints)            │
│  │     ├── risk.py (risk assessment)                          │
│  │     ├── response.py (response generation)                  │
│  │     ├── package.py (chargeback package generation)         │
│  │     ├── webhooks.py (webhook handling)                     │
│  │     ├── events.py (event streaming)                        │
│  │     ├── system.py (system status)                          │
│  │     ├── mode.py (mode configuration)                       │
│  │     └── demo.py (demo/simulation endpoints)                │
│  │                                                             │
│  ├── database/                                                │
│  │  ├── database.py (SQLAlchemy setup)                        │
│  │  ├── models.py (ORM models)                                │
│  │  ├── repository.py (data access layer)                     │
│  │  ├── seed.py (demo data seeding)                           │
│  │  └── live_seed.py (production data initialization)         │
│  │                                                             │
│  ├── services/                                                │
│  │  └── ai/                                                   │
│  │     ├── service.py (AI orchestration)                      │
│  │     ├── deepseek_client.py (LLM API client)               │
│  │     ├── evidence_analysis_service.py (evidence analysis)  │
│  │     ├── prompt_builder.py (prompt construction)            │
│  │     ├── response_parser.py (JSON parsing)                  │
│  │     ├── evidence_reasoner.py (evidence reasoning)          │
│  │     ├── cache.py (response caching)                        │
│  │     ├── fallback.py (fallback strategies)                  │
│  │     └── schemas.py (AI response schemas)                   │
│  │                                                             │
│  ├── components/                                              │
│  │  ├── fraud_model.py (v1 fraud detection)                   │
│  │  ├── fraud_model_v2.py (v2 fraud detection - XGBoost)     │
│  │  ├── win_probability.py (win prediction model)             │
│  │  ├── confidence.py (confidence calculation)                │
│  │  ├── recommendation.py (recommendation engine)             │
│  │  ├── explanation.py (explainability module)                │
│  │  ├── evidence_validation.py (evidence validator)           │
│  │  ├── evidence_requirements.py (requirement checker)        │
│  │  ├── completeness.py (completeness scorer)                 │
│  │  ├── contradiction.py (contradiction detector)             │
│  │  ├── reason_classifier.py (dispute reason classifier)      │
│  │  ├── fraud_rules.py (business rules engine)                │
│  │  ├── evidence_retrieval.py (evidence fetcher)              │
│  │  └── __init__.py                                           │
│  │                                                             │
│  ├── pipeline/                                                │
│  │  ├── risk_engine.py (main risk orchestration)              │
│  │  ├── analysis_service.py (dispute analysis)                │
│  │  └── autopilot.py (AI autopilot mode)                      │
│  │                                                             │
│  ├── schemas/                                                 │
│  │  ├── api_schemas.py (request/response Pydantic models)    │
│  │  └── (other schema modules)                                │
│  │                                                             │
│  ├── evidence/                                                │
│  │  ├── engine.py (evidence orchestration)                    │
│  │  ├── file_processor.py (file extraction)                   │
│  │  └── schemas.py (evidence schemas)                         │
│  │                                                             │
│  ├── chargeback/                                              │
│  │  └── service.py (package generation service)               │
│  │                                                             │
│  ├── actions/ (deprecated)                                    │
│  ├── response/ (response builder)                             │
│  └── utils/                                                   │
│     ├── logger.py (logging configuration)                     │
│     ├── id_generator.py (UUID generation)                     │
│     ├── data_generator.py (demo data generation)              │
│     └── (other utilities)                                     │
│                                                                 │
├─ models/                                                       │
│  ├── fraud_model.pkl (original fraud model)                  │
│  ├── fraud_pipeline.joblib (original pipeline)               │
│  ├── fraud_v2_pipeline.joblib (XGBoost pipeline - V2)        │
│  ├── win_pipeline.joblib (win probability pipeline)           │
│  └── win_probability_model.pkl (win probability model)        │
│                                                                 │
├─ data/                                                        │
│  ├── synthetic/ (demo dispute scenarios)                      │
│  ├── metrics/ (evaluation results)                            │
│  └── datasets/ (training data)                                │
│                                                                 │
├─ tests/                                                        │
│  ├── test_fraud_model.py                                      │
│  ├── test_evidence_analysis.py                                │
│  ├── test_win_probability.py                                  │
│  ├── test_api_endpoints.py                                    │
│  └── (other test files)                                       │
│                                                                 │
└─ config/                                                       │
   ├── settings.py (configuration management)                   │
   └── constants.py (application constants)                     │
│                                                                 │
└──────────────────────────────────────────────────────────────────┘
```

## 4. DATA FLOW ARCHITECTURE

### Transaction → Dispute → Evidence → Decision Flow

```
┌─────────────┐
│ Transaction │ (amount, timestamp, card, merchant, device, geography, etc.)
└──────┬──────┘
       │
       ├─→ Fraud Model V2 (XGBoost) ──→ Fraud Probability (0-1)
       │                                 Risk Level (LOW/MEDIUM/HIGH)
       │
       └─→ Store in Database
           ├── customers table
           ├── transactions table
           ├── payments table
           └── orders table

┌──────────────┐
│   Dispute    │ (reason code, amount, respond_by, status)
│  Raised      │
└──────┬───────┘
       │
       ├─→ Fetch Transaction ──→ Get Fraud Probability
       │
       └─→ Create Dispute Record
           ├── disputes table
           └── dispute_events table (timeline)

┌──────────────────┐
│  Merchant Uploads│
│    Evidence      │ (receipt, invoice, tracking, screenshot, etc.)
└──────┬───────────┘
       │
       ├─→ EvidenceFileProcessor
       │   ├── File type validation (PDF, image, text)
       │   ├── File size check
       │   ├── MIME type verification
       │   └── Extract text (PyPDF for PDFs, OCR for images)
       │
       ├─→ Store Evidence Record
       │   └── evidence table
       │
       └─→ Trigger AI Analysis

┌──────────────────────────┐
│ DeepSeek LLM Analysis    │
└──────┬───────────────────┘
       │
       ├─→ PromptBuilder
       │   ├── System prompt (rules for evidence analysis)
       │   ├── Evidence context (extracted text)
       │   ├── Dispute context (reason, amount)
       │   └── Instructions (completeness, contradictions, validation)
       │
       ├─→ DeepSeekClient (chat_completion)
       │   ├── HTTP POST to api.deepseek.com
       │   ├── JSON mode enabled
       │   ├── Temperature: 0.2
       │   ├── Max tokens: 1500
       │   ├── Timeout: 30 seconds
       │   └── Fallback: graceful error if API unavailable
       │
       └─→ ResponseParser
           ├── Parse JSON response
           ├── Validate schema
           ├── Extract:
           │   ├── completeness_score (0-100)
           │   ├── missing_evidence (list)
           │   ├── contradictions (list)
           │   ├── key_entities (extracted facts)
           │   ├── claims_validation (verified/unverified)
           │   ├── risk_flags (concerning items)
           │   └── overall_assessment
           │
           └─→ Store Analysis Results
               └── evidence.ai_analysis_json

┌────────────────────────────┐
│ ML Assessment Calculation  │
└────────┬───────────────────┘
         │
         ├─→ Fetch All Evidence for Dispute
         │   └── Aggregate completeness scores
         │
         ├─→ Win Probability Model (XGBoost)
         │   ├── Input: fraud_score + evidence_quality + dispute_context
         │   └── Output: win_probability (0-1)
         │
         └─→ Confidence Calculation
             ├── Based on evidence quality
             ├── Based on AI agreement
             └── Confidence Level (LOW/MEDIUM/HIGH)

┌──────────────────────────┐
│ Store Dispute Assessment │
└────────┬─────────────────┘
         │
         └─→ dispute_assessments table
             ├── fraud_probability
             ├── win_probability
             ├── confidence
             ├── ml_recommendation (CONTEST/ACCEPT/INVESTIGATE)
             ├── ai_recommendation (CONTEST/ACCEPT/INVESTIGATE)
             ├── ml_results_json
             ├── deepseek_results_json
             ├── evidence_analysis_json
             └── conflict_detected (if ML ≠ AI)

┌──────────────────────────┐
│ Merchant Review Phase    │
└────────┬─────────────────┘
         │
         ├─→ Display Assessment to Merchant
         │   ├── Evidence completeness gaps
         │   ├── Detected contradictions
         │   ├── Win probability
         │   ├── AI recommendation
         │   └── Required next steps
         │
         └─→ Merchant Decision
             ├── Option 1: Upload more evidence (re-analyze)
             ├── Option 2: Mark complete (proceed to submission)
             └── Option 3: Accept (don't contest)

┌──────────────────────────┐
│ Submission & Packaging   │
└────────┬─────────────────┘
         │
         └─→ ChargebackPackageService
             ├── Validate readiness
             ├── Organize evidence by type
             ├── Generate response document
             ├── Create package record
             │   └── chargeback_packages table
             └── Mark dispute as SUBMITTED

┌──────────────────────────┐
│ Final State              │
└──────────────────────────┘
         
dispute.status = "SUBMITTED"
dispute.workflow_stage = "SUBMITTED"
chargeback_package.package_status = "READY_FOR_SUBMISSION"

Ready for Razorpay to review and process
```

## 5. ML/AI PROCESSING PIPELINE

```
┌─────────────────────────────────────────────────────────┐
│ Machine Learning Pipeline                               │
└──────────────────────────────────────────────────────────┘

FRAUD DETECTION:
  Input Features → Feature Engineering → XGBoost Model → Fraud Probability
  ├── amount
  ├── transaction_hour
  ├── account_age_days
  ├── previous_chargebacks
  ├── device_type
  ├── is_international
  ├── is_high_risk_merchant
  ├── transaction_velocity_1h
  ├── transaction_velocity_24h
  ├── avg_transaction_amount_30d
  └── merchant_category

  Model: fraud_v2_pipeline.joblib
  Output: fraud_probability (0.0 - 1.0)
  Risk Mapping:
    [0.0-0.3]   → LOW
    [0.3-0.7]   → MEDIUM
    [0.7-1.0]   → HIGH

WIN PROBABILITY:
  [Fraud Score] + [Evidence Quality] + [Dispute Context]
  ↓
  XGBoost Regressor
  ↓
  Output: win_probability (0.0 - 1.0)
  
  Model: win_pipeline.joblib
  Calibrated for probability output

AI EVIDENCE ANALYSIS:
  [Extracted Evidence Text]
  ↓
  PromptBuilder (construct LLM prompt)
  ↓
  DeepSeek API (deepseek-chat model)
  ├── Temperature: 0.2
  ├── Max Tokens: 1500
  ├── Response Format: JSON
  └── Timeout: 30 seconds
  ↓
  ResponseParser (validate + extract JSON)
  ↓
  Output: EvidenceAnalysisResult
  ├── completeness_score (0-100)
  ├── missing_evidence (list)
  ├── contradictions (list)
  ├── key_entities (extracted facts)
  ├── claims_validation
  ├── risk_flags
  └── overall_assessment
```

---

**Document Status:** Complete architectural overview
**Last Updated:** September 2, 2026

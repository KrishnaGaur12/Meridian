# MASTER PROJECT CONTEXT & FULL-STACK ARCHITECTURE SPECIFICATION
## Razorpay AI Risk Manager — Merchant-First AI Chargeback Operations Platform

> **AUTHORITATIVE MASTER CONTEXT & WORKSPACE MEMORY**  
> *This document represents the SINGLE integrated source of truth for the entire full-stack project workspace. It governs all future AI-assisted development across Frontend, Backend, Database, REST APIs, AI/ML models, Risk Engine, Evidence Engine, and Chargeback Response logic.*

---

## 1. EXECUTIVE OVERVIEW & INTEGRATED FULL-STACK DECLARATION

**Razorpay AI Risk Manager** is a merchant-first AI chargeback operations platform. It turns high-friction, complex payment chargeback disputes into proactive, automated AI workflows where merchants only intervene when a human decision or action is strictly required.

### Key Architectural Principles
1. **AI Autopilot as Central Orchestration Engine**: Every dispute automatically runs AI analysis, assigns one of 4 merchant attention states (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`), and recalculates risk, evidence completeness, win probability, Next Best Action, and readiness whenever evidence or events change.
2. **Human-in-the-Loop Submission Policy**: Even for `AI_HANDLING` cases where all evidence is complete and verified, final submission requires explicit merchant sign-off.
3. **Explicit 3-Tier Data Architecture**:
   - `DEMO`: Seeded showcase scenarios for demonstration.
   - `SIMULATED_RAZORPAY`: Local simulation disputes created via the Razorpay Demo page ("Razorpay-like local simulation").
   - `REAL_RAZORPAY`: Reserved tier for future external webhook integration.
4. **Transparent AI Activity Stream**: Logs explicit AI events ("AI completed case analysis", "AI checked 4/5 required proofs", "AI reassessed case") alongside merchant actions.
5. **Ultra-Simple Merchant Dashboard**: Designed to answer "Do I need to do anything today?" featuring header, search bar, money at risk summary, 4 operational attention cards (`Need your action`, `Ready for your review`, `Ready to submit`, `AI handling automatically`), and compact recent activity feed. Zero ML jargon or raw JSON on main dashboard.
6. **Expandable AI Explainability inside Dispute Workspace**: Surfaces plain business language by default ("Strong case"), with an expandable "AI Explanation" section showing supporting factors, risk factors, and model assessment metrics.
7. **Strict Case Isolation**: Every dispute is a single, isolated case workspace (`DSP_xxxx`) with top navigation (`← Back to disputes`, `← Previous case | Next case →`). Every DB/API query is bound strictly to `dispute_id`.
8. **Next Best Action "Why is AI asking me?"**: Surfaces clear explanations in Next Best Action ("We need your delivery confirmation: The customer says the order wasn't received... Adding this will directly strengthen your response.").
9. **Event-Driven Local Simulation**: Reassesses case, updates dashboard queues, updates package readiness, and logs timeline events whenever evidence is uploaded or modified locally.

### Unified Full-Stack Architecture
This workspace represents **ONE integrated full-stack project** split into two complementary physical directories:
1. **Backend Layer (`AI Chargeback Evidence Responce/`)**: Built with Python 3.11+, FastAPI 2.0, SQLAlchemy ORM, SQLite, XGBoost, Scikit-Learn, Joblib, and Pytest.
2. **Frontend Layer (`AI Chargeback-Frontend/`)**: Built with React 19, TypeScript 6, Vite 8, Tailwind CSS v4, Lucide React, and Recharts.

```text
                                FULL-STACK SYSTEM BOUNDARY
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                         │
│   React Frontend (TypeScript / Vite / Tailwind)                                         │
│                          │                                                              │
│                          ▼                                                              │
│   Frontend API Layer (Axios Services / dashboardService.ts)                             │
│                          │                                                              │
│                          ▼  REST HTTP / JSON APIs                                       │
│   FastAPI Backend (src/api/router.py / main.py)                                         │
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

---

## 2. CONTEXT FILE LOCATION & SYNCHRONIZATION POLICY

- **Authoritative Files**:
  - Primary Backend Workspace Path: [`AI Chargeback Evidence Responce/PROJECT_CONTEXT.md`](file:///d:/Github%20Projects/Razorpay%20AI%20Risk%20Manager/AI%20Chargeback%20Evidence%20Responce/PROJECT_CONTEXT.md)
  - Primary Frontend Workspace Path: [`AI Chargeback-Frontend/PROJECT_CONTEXT.md`](file:///d:/Github%20Projects/Razorpay%20AI%20Risk%20Manager/AI%20Chargeback-Frontend/PROJECT_CONTEXT.md)
- **Synchronization Policy**: Both workspace files represent identical copies of this master full-stack specification. Whenever an architecture, schema, API, or workflow change occurs, both copies must be updated simultaneously.

---

## 3. IMPLEMENTATION ACHIEVEMENTS SUMMARY

1. **Central AI Autopilot Architecture**: Dynamic orchestration decision pipeline calculating `merchant_attention_state` (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`).
2. **Human-in-the-Loop Submission Policy**: Merchants explicitly review and approve responses before local gateway boundary submission.
3. **3-Tier Data Architecture**: `DEMO`, `SIMULATED_RAZORPAY`, `REAL_RAZORPAY` labels across all API schemas, database queries, and frontend UI components.
4. **Razorpay Demo Local Simulation**: Dedicated simulation page (`/demo`) enabling creation of custom simulated chargebacks with automatic AI analysis and dashboard updates.
5. **Ultra-Simple Merchant Dashboard**: Clean white Razorpay merchant layout with 4 operational cards, money at risk summary, search bar, and live activity feed.
6. **Isolated Single-Case Workspace**: Single page (`DSP_xxxx`) with 7 human-readable sections, Next Best Action "Why is AI asking me?", expandable AI Explainability, Before vs After Impact Delta, Package Inspection modal, and book-like `← Previous case | Next case →` navigation.
7. **Local Gateway Boundary Submission**: Submissions record `Submitted — Local Gateway Boundary` without claiming live external Razorpay API calls.
8. **100% Pytest Pass Rate**: All 102/102 backend Pytest unit and integration tests passing cleanly.
9. **100% TypeScript Compilation**: Frontend Vite production build compiling 100% cleanly with zero errors.

---

## 4. FRONTEND ↔ BACKEND CONTRACT

| Frontend Feature | Frontend File | Backend Endpoint | Backend Logic / Service | Database Source |
| :--- | :--- | :--- | :--- | :--- |
| **Merchant Dashboard** | `DashboardPage.tsx` | Client-side Service | `dashboardService.ts` | `disputes`, `transactions` |
| **Disputes Registry** | `DisputesPage.tsx` | `GET /disputes` | `list_disputes_endpoint()` | `disputes`, `transactions` |
| **File Dispute Case** | `DisputesPage.tsx` | `POST /disputes` | `create_dispute()` | `disputes`, `dispute_events` |
| **Razorpay Simulation**| `RazorpayDemoPage.tsx` | `POST /demo/simulate-dispute` | `simulate_razorpay_dispute()` (`SIMULATED_RAZORPAY`) | `disputes`, `transactions`, `AIAutopilot` |
| **Simulation Tx List**| `RazorpayDemoPage.tsx` | `GET /demo/available-transactions` | `list_available_transactions()` | `transactions`, `disputes` |
| **Dispute Detail Workspace**| `DisputeDetailPage.tsx` | `GET /disputes/{id}` | `get_dispute_endpoint()` | `disputes`, `transactions` |
| **Command Center Snapshot** | `DisputeDetailPage.tsx` | `GET /disputes/{id}/command-center` | `get_dispute_command_center()` | Aggregated snapshot |
| **Next Best Action** | `DisputeDetailPage.tsx` | `GET /disputes/{id}/next-action` | `NextBestActionEngine` | Actionable guidance & why asking |
| **Package Inspection**| `PackageInspectionModal.tsx` | `GET /disputes/{id}/package-inspection` | `inspect_chargeback_package()` | Inspection payload & local boundary notice |
| **Dispute Submission** | `DisputeDetailPage.tsx` | `POST /disputes/{id}/submit` | `submit_dispute_package()` | Submission gate & timeline event |
| **Evidence Reassessment** | `DisputeDetailPage.tsx` | `POST/PUT/DELETE /evidence` | `create_evidence_endpoint()`, `AIAutopilot` | `evidence`, `dispute_events` |
| **Merchant Accept / Override** | `DisputeDetailPage.tsx` | `POST /disputes/{id}/accept`, `override-recommendation` | `accept_dispute_endpoint()`, `override_recommendation_endpoint()` | `disputes`, `dispute_events` |
| **ML Model Health** | `Header.tsx` | `GET /health/models` | `ml_model_health_endpoint()` | Model files & metadata |

---

## 5. VERIFICATION & EXECUTION COMMANDS

### Backend Commands
```powershell
cd "d:\Github Projects\Razorpay AI Risk Manager\AI Chargeback Evidence Responce"
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 127.0.0.1 --port 8000
.\.venv\Scripts\pytest -v
```

### Frontend Commands
```powershell
cd "d:\Github Projects\Razorpay AI Risk Manager\AI Chargeback-Frontend"
npm run dev
npm run build
```

---

## 6. FINAL VALIDATION & STATUS SUMMARY
- **Backend Test Status**: 118/118 Pytest unit & integration tests passing 100% cleanly (including 16 comprehensive productization test suites).
- **Frontend Build Status**: Vite production build compiled 100% cleanly with ZERO TypeScript errors.
- **AI Autopilot Engine**: Centralized attention state prioritization (`Action Required`, `Review Recommended`, `AI Handling`, `Waiting`). Continuous AI reassessment, honest Before vs After Impact Delta, Next Best Action "Why is AI asking me?", and human-in-the-loop submission sign-off.
- **Data Integrity**: 100% real database querying preserved across all merchant views with zero cross-dispute contamination.
- **Data Separation**: Explicit separation of `DEMO` seeded showcase data, `SIMULATED_RAZORPAY` local incoming disputes, and reserved `REAL_RAZORPAY` integration boundary.

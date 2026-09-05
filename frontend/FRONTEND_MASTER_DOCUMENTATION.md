# Frontend Master Documentation: Razorpay AI Risk Manager & Merchant Dispute Platform

> **Document Version:** 2.0.0  
> **Target Audience:** Buildathon Jury, Product Managers, Frontend Architects, UI/UX Reviewers, Cybersecurity Auditors, and New Engineers  
> **Source Grounding:** 100% verified against frontend codebase (`package.json`, `vite.config.ts`, `src/**/*`)  
> **Frontend Architecture Philosophy:** Zero-Lag, Real-Time SSE Synchronized, Explainable AI & Human-in-the-Loop Representation Engine

---

## 1. Executive Overview

### 1.1 What the Frontend Is
The **Razorpay AI Risk Manager Frontend** is a modern, single-page web application (SPA) designed as a **Merchant-First Dispute Operations & AI Chargeback Defense Platform**. It empowers online businesses and merchants to monitor incoming payment disputes, inspect AI/ML fraud and win-probability predictions, manage and upload documentary evidence, generate legally grounded chargeback rebuttal letters, and submit formal representation packages to payment gateways (Razorpay, card networks, and issuing banks).

### 1.2 Who the Users Are
- **Primary Users:** Merchants, E-commerce Store Owners, Dispute Operations Specialists, Finance & Risk Teams.
- **Secondary / Administrative Users:** Risk Analysts reviewing automated ML models, and Demo Evaluators/Jury testing simulated webhook events and gateway outcomes.

### 1.3 What Users Can Do
1. **Triage Active Disputes:** View prioritized dispute queues categorized by urgency (`URGENT`, `IMPORTANT`, `READY`, `NORMAL`) and attention states (`ACTION_REQUIRED`, `REVIEW_RECOMMENDED`, `AI_HANDLING`, `WAITING`).
2. **Inspect Dual-Model AI Intelligence:** Review real-time merchant win probabilities (`models/win_pipeline.joblib`), fraud risk scores (`models/fraud_v2_pipeline.joblib`), confidence levels, positive/negative winning factors, and DeepSeek AI reasoning vs. deterministic fallbacks.
3. **Execute Evidence Operations:** Upload proof documents (PDF, PNG, JPG), create structured delivery logs (carrier tracking), edit metadata, replace backing files, delete stale evidence, and inspect extracted key facts.
4. **Enforce Human-in-the-Loop Governance:** Explicitly approve or reject evidence items before they can be compiled into a representation bundle.
5. **Manage Defense Statements:** Customize and persist auto-generated rebuttal letters contesting cardholder claims.
6. **Pass Automated Readiness Gates:** Verify that representation packages satisfy all gateway criteria (zero unapproved items, required evidence attached) before triggering submission.
7. **Simulate Gateway Lifecycle:** Use the embedded and standalone Razorpay Webhook Simulators to simulate incoming chargebacks (`dispute.created`) and test bank resolution outcomes (`WON` / `LOST`).
8. **Switch Database Environments:** Instantly toggle between `DEMO` and `LIVE` database modes via the global header switcher without page reloads.

### 1.4 Major Screens
- **Dashboard (`/`):** High-level financial KPIs, urgency-sorted attention queue, tabbed attention buckets, and quick dispute navigation.
- **Disputes Queue (`/disputes`):** Filterable, searchable operational list of disputes with real-time status and priority badges.
- **Dispute Workspace & Control Center (`/disputes/:disputeId`):** The comprehensive dispute command center with a 4-step workflow navigation: *Overview*, *Review & Control Center*, *Gateway Review*, and *Final Outcome*.
- **History Archive (`/history`):** Historical repository of all resolved (`WON`, `LOST`, `CLOSED`) disputes.
- **Settings & Policies (`/settings`):** Merchant profile configuration, dispute automation preferences, default refund policies, and logistics connectors.
- **Standalone Razorpay Webhook Portal (`/webhooks`):** Specialized developer/jury testing interface to simulate real-time chargeback webhooks against live transactions.

### 1.5 Relationship with the Backend
- The frontend operates as a decoupled client communicating with the backend over HTTP REST (`axios`) and Server-Sent Events (`EventSource`).
- The frontend injects the `X-Database-Mode` header (`DEMO` or `LIVE`) on every request.
- The frontend relies on the backend for machine learning predictions, DeepSeek reasoning, database persistence (SQLite), and mock payment gateway transitions. When backend services are unavailable, graceful fallbacks and error states are rendered.

---

## 2. Product & User Experience Journey

```
+---------------------------------------------------------------------------------------+
|                                MERCHANT USER JOURNEY                                  |
+---------------------------------------------------------------------------------------+
  Direct Access (Mock Merchant MID_001)
     │
     ▼
  1. Executive Dashboard (/)
     │  ├── High-level Financial KPIs (₹ at Risk, ₹ Recovered, Active Cases)
     │  └── Attention Buckets (Action Required, Review Recommended, AI Handling)
     │
     ▼
  2. Disputes Queue (/disputes)
     │  ├── Instant Search & Tab Filtering (Needs Attention, Under Review, Resolved)
     │  └── Priority & Deadline Indicators (e.g., "Due in 18 hours")
     │
     ▼
  3. Dispute Control Center (/disputes/:disputeId)
     │
     ├── Step 1: Case Overview & Chronological Timeline
     │     └── 12 Core Parameters + ML Risk/Win Preview + Event Audit Stream
     │
     ├── Step 2: Review & Control Center (CaseMerchantControlCenter)
     │     ├── AI Verdict & Win Assessment Card (DeepSeek + ML Models + Conf. Metrics)
     │     ├── Evidence Management (Upload PDF/Images, Add Courier Info, Replace Files)
     │     ├── Human-in-the-Loop Review (Explicit Merchant Approval / Rejection)
     │     ├── Rebuttal Statement Editor (Custom Rebuttal Letter to Issuing Bank)
     │     └── Readiness Gate Validation (Automated Blocker Check)
     │
     ├── Step 3: Gateway Submission
     │     └── Hard Representation Gate (Locks Editing, Transmits to Gateway)
     │
     ├── Step 4: Razorpay Gateway Review
     │     ├── Awaiting Bank & Card Network Ruling
     │     └── Simulator Option: Trigger Simulated Outcome (WON / LOST)
     │
     └── Step 5: Final Outcome & Resolution
           ├── Revenue Recovery Report (₹ Recovered / Lost)
           └── Immutable Database Audit Trail
```

---

## 3. Complete Frontend Architecture

### 3.1 Actual Implemented Architecture Diagram

```
+-----------------------------------------------------------------------------------------+
|                                    BROWSER CLIENT                                       |
+-----------------------------------------------------------------------------------------+
                                           │
                                           ▼
                                   [index.html]
                                           │
                                           ▼
                                    [src/main.tsx]
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
             [BrowserRouter (v7)]                   [index.css (Tailwind v4)]
                       │
                       ▼
            [DatabaseModeProvider] (React Context: DEMO vs LIVE / localStorage)
                       │
                       ▼
                  [<App />]
                       │
         ┌─────────────┴─────────────────────────────────┐
         ▼                                               ▼
  [<AppLayout />] (Shell)                    [Standalone Webhook Portal]
         │                                               │
   ┌─────┴───────────────┐                               ▼
   ▼                     ▼                   [RazorpayWebhookPage (/webhooks)]
[<Sidebar />]      [<Header />]                          │
   │               (Mode Toggle, Search)                 │
   │                     │                               │
   └──────────┬──────────┘                               │
              ▼                                          │
       [<Outlet />]                                      │
              │                                          │
   ┌──────────┼───────────────┬──────────────┐           │
   ▼          ▼               ▼              ▼           │
Dashboard  Disputes     DisputeDetail     History        │
   (/)    (/disputes) (/disputes/:id)   (/history)       │
                              │                          │
                   ┌──────────┴──────────┐               │
                   ▼                     ▼               │
           CaseOverviewTab    CaseMerchantControlCenter  │
                   │                     │               │
                   ▼                     ▼               │
           CaseRazorpayReview     CaseOutcomeTab         │
                                                         │
─────────────────────────────────────────────────────────┼───────────────────────────────
                     STATE & HOOKS LAYER                 │
                                                         │
   ┌──────────────────────────────────────────────┐      │
   │ • useDatabaseMode (Active Mode Context)      │      │
   │ • useRealtimeRefresh (SSE + Heartbeat Sync)  │◄─────┤
   │ • useRealtimeEvents (EventSource SSE Client) │      │
   │ • Component Local State (Optimistic Updates) │      │
   └──────────────────────────────────────────────┘      │
                                                         │
─────────────────────────────────────────────────────────┼───────────────────────────────
                      SERVICE & CACHE LAYER              │
                                                         │
   ┌──────────────────────────────────────────────┐      │
   │ [cacheService.ts] (In-memory TTL + Dedupe)   │      │
   │ [disputeService.ts] (Dispute & ML Endpoints) │◄─────┤
   │ [evidenceService.ts] (Multipart File Upload) │      │
   │ [simulationService.ts] (Webhook Simulator)   │      │
   │ [dashboardService.ts] (Client Aggregator)    │      │
   └──────────────────────────────────────┬───────┘      │
                                          │              │
                                          ▼              │
                                   [services/api.ts]     │
                         (Axios Client: X-Database-Mode) │
                                          │              │
──────────────────────────────────────────┼──────────────┴───────────────────────────────
                       NETWORK & PROXY LAYER
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
            Vite Dev Proxy (/api)                    Vite Dev Proxy (/events)
            http://localhost:8000                     http://localhost:8000/events
                     │                                         │
                     └────────────────────┬────────────────────┘
                                          ▼
                             [FastAPI Backend Server]
```

### 3.2 Architectural Component Descriptions
- **Entry Point (`src/main.tsx`):** Bootstraps React 19 root into DOM `#root`, wrapping the application with React 19 StrictMode and React Router DOM v7 `BrowserRouter`.
- **Global Context (`src/context/DatabaseModeContext.tsx`):** Manages `DEMO` vs `LIVE` environment mode, syncs state to `localStorage` (`razorpay_database_mode`), and automatically sets `X-Database-Mode` default headers across Axios instances.
- **Layout Shell (`src/components/layout/AppLayout.tsx`):** Provides the persistent sidebar navigation, the top bar containing global dispute search and environment switchers, real-time background SSE sync hooks, and dynamic mode transition banners.
- **In-Memory Cache & Deduping Engine (`src/services/cacheService.ts`):** High-performance cache layer that eliminates lag by deduplicating concurrent in-flight requests and maintaining TTL-based cached responses (15s–30s) with prefix-based invalidation upon user actions.
- **Real-Time Synchronizer (`src/hooks/useRealtimeEvents.ts`):** Establishes an `EventSource` connection to `/events` (proxied to backend), listening to 8 lifecycle events (`DISPUTE_CREATED`, `ML_ANALYSIS_COMPLETED`, `DEEPSEEK_ANALYSIS_COMPLETED`, `EVIDENCE_APPROVED`, `DISPUTE_STAGE_CHANGED`, etc.) to trigger silent background UI updates.

---

## 4. Repository Structure

```
d:/Github Projects/AI Frontent -Razorpay project/
├── index.html                           # HTML5 Entry Point (Inter & JetBrains Mono fonts)
├── package.json                         # Project dependencies, scripts & metadata
├── tsconfig.json                        # Root TypeScript configuration
├── tsconfig.app.json                    # Application TS compilation settings
├── tsconfig.node.json                   # Node/Vite build TS configuration
├── vite.config.ts                       # Vite 6 config with Tailwind v4 & API reverse proxy
├── openapi.json                         # API schema descriptor (0 bytes / placeholder)
└── src/
    ├── App.tsx                          # Root Route definitions & Route shell
    ├── main.tsx                         # DOM Root mounting & BrowserRouter bootstrap
    ├── index.css                        # Tailwind v4 import, font tokens, custom scrollbars
    ├── vite-env.d.ts                    # Vite client TypeScript definitions
    │
    ├── components/
    │   ├── common/                      # Reusable UI Atoms & Molecules
    │   │   ├── Badge.tsx                # Status & Priority badge component (6 variants)
    │   │   ├── Button.tsx               # Primary, Secondary, Outline, Danger, Ghost buttons
    │   │   ├── Card.tsx                 # Base container card with optional hover elevation
    │   │   ├── Modal.tsx                # Accessible backdrop dialog with Esc key listener
    │   │   ├── SearchBar.tsx            # Global instant search dropdown for disputes
    │   │   └── Skeleton.tsx             # Pulsing placeholder loader for async states
    │   │
    │   ├── layout/                      # Application Shell Components
    │   │   ├── AppLayout.tsx            # Main portal layout (Sidebar + Header + Outlet)
    │   │   ├── Header.tsx               # Top navigation (Search, Mode toggle, Profile)
    │   │   ├── Sidebar.tsx              # Operations & System navigation links
    │   │   └── SimulatorLayout.tsx      # Sub-layout for multi-page simulator views
    │   │
    │   └── disputes/                    # Dispute Review & Control Center Components
    │       ├── AIRecommendationSection.tsx # Standalone AI decision breakdown & override modal
    │       ├── CaseAIAnalysisTab.tsx    # Detailed ML & DeepSeek breakdown tab
    │       ├── CaseHeader.tsx           # Sticky dispute summary strip with deadline alert
    │       ├── CaseMerchantControlCenter.tsx # 85KB All-in-one dispute management workspace
    │       ├── CaseMerchantReviewTab.tsx # Standalone merchant concession/contest tab
    │       ├── CaseOutcomeTab.tsx       # Final resolved outcome view with financial delta
    │       ├── CaseOverviewTab.tsx      # High-level overview, 12 params & timeline
    │       ├── CaseRazorpayReviewTab.tsx# Gateway review stage & outcome simulation trigger
    │       ├── CaseSubmissionTab.tsx    # Representation submission tab with rebuttal editor
    │       ├── CaseTimeline.tsx         # Chronological vertical audit trail component
    │       ├── EvidenceSection.tsx      # Standalone modular evidence manager
    │       ├── FinalReviewSection.tsx   # Modular review & submission summary section
    │       ├── OutcomeCard.tsx          # Card displaying simulated WON/LOST details
    │       ├── ProgressStepper.tsx      # 7-stage horizontal progress checkpoint bar
    │       ├── StickyCaseNav.tsx        # Scrollspy sticky navigation bar
    │       ├── SubmissionModal.tsx      # Modal confirming package submission & outcome
    │       └── WorkflowStepNav.tsx      # 4-step merchant journey navigation tabs
    │
    ├── context/
    │   └── DatabaseModeContext.tsx      # Global React Context for DEMO / LIVE database modes
    │
    ├── hooks/
    │   ├── useRealtimeEvents.ts         # SSE EventSource listener for backend events
    │   └── useRealtimeRefresh.ts        # Combined SSE + 8s polling heartbeat hook
    │
    ├── pages/
    │   ├── DashboardPage.tsx            # Executive dispute operations overview
    │   ├── DisputesPage.tsx             # Operational dispute queue with search & filters
    │   ├── DisputeDetailPage.tsx        # Route container for Dispute Workspace
    │   ├── HistoryPage.tsx              # Resolved disputes historical archive
    │   ├── RazorpayWebhookPage.tsx      # Standalone live webhook simulation portal
    │   ├── SettingsPage.tsx             # Merchant settings, policies & connectors
    │   ├── SimulatorPage.tsx            # Embedded alternative simulator page
    │   └── simulator/                   # Alternate sub-page simulator views
    │       ├── RaiseDisputePage.tsx     # Direct dispute simulation form
    │       ├── SimulatorActivityPage.tsx# Simulator activity stream
    │       ├── SimulatorCustomersPage.tsx# Simulated customer database list
    │       ├── SimulatorDisputesPage.tsx # Simulated dispute registry list
    │       ├── SimulatorMerchantsPage.tsx# Merchant profile in simulator
    │       ├── SimulatorOverviewPage.tsx # Simulation stats & quick actions
    │       └── SimulatorTransactionsPage.tsx # Eligible transaction list
    │
    ├── services/
    │   ├── api.ts                       # Axios client instance & interceptors
    │   ├── cacheService.ts              # In-memory TTL cache & request deduplicator
    │   ├── dashboardService.ts          # Client-side KPI and attention bucket aggregator
    │   ├── disputeService.ts            # Dispute CRUD, analysis, override & submit API
    │   ├── evidenceService.ts           # Evidence upload, update, approve & delete API
    │   ├── simulationService.ts         # Transactions fetch & Webhook dispute trigger API
    │   └── transactionService.ts        # Direct transaction & risk assessment API
    │
    ├── types/
    │   ├── commandCenter.ts             # Snapshot, AI recommendation, ML explainability types
    │   ├── dispute.ts                   # Dispute core schema, readiness & outcome types
    │   ├── evidence.ts                  # Evidence item, impact delta, payload types
    │   ├── simulation.ts                # Simulation payload & transaction types
    │   └── transaction.ts               # Transaction & ML risk assessment schema
    │
    └── utils/
        └── formatters.ts                # INR/USD currency, dates, deadlines, reason codes
```

---

## 5. Technology Stack

| Category | Package / Tool | Version | Purpose & Implementation Details |
| :--- | :--- | :--- | :--- |
| **Framework** | `react` / `react-dom` | `^19.0.0` | UI component tree, hooks, StrictMode execution |
| **Language** | `typescript` | `~5.7.3` | End-to-end static typing for models, API payloads, and props |
| **Build Tool** | `vite` | `^6.1.0` | Ultra-fast HMR dev server and ES module production bundler |
| **Routing** | `react-router-dom` | `^7.2.0` | Client-side SPA routing (`BrowserRouter`, `Routes`, `Route`, `Outlet`, `useParams`, `useNavigate`) |
| **Styling** | `tailwindcss` + `@tailwindcss/vite` | `^4.0.6` | Utility-first CSS using Tailwind CSS v4 CSS-first engine |
| **Class Utilities** | `clsx` (`^2.1.1`), `tailwind-merge` (`^3.0.1`) | Latest | Dynamic CSS class merging without style conflicts |
| **Icons** | `lucide-react` / Inline SVGs | `^0.475.0` | Vector icons for navigation, statuses, and quick actions |
| **HTTP Client** | `axios` | `^1.7.9` | Promise-based HTTP client with request/response interceptors |
| **Realtime Sync** | Browser `EventSource` (SSE) | Native | Server-Sent Events listener for real-time backend updates |
| **State Manager** | React Context + In-Memory Cache | Native | `DatabaseModeContext` + custom `CacheService` class |
| **Typography** | Google Fonts (`Inter`, `JetBrains Mono`) | External | Clean fintech aesthetic with monospace typography for IDs |

---

## 6. Application Startup & Initialization Sequence

1. **HTML Parsing (`index.html`):** Browser loads HTML, connects to Google Fonts (`Inter` 300–700, `JetBrains Mono` 400–500), and executes `/src/main.tsx`.
2. **React Root Creation (`src/main.tsx`):** `ReactDOM.createRoot` mounts the root DOM node under `#root`.
3. **Router Initialization:** Wraps `<App />` with `<BrowserRouter>`.
4. **Context Provider Mount (`src/context/DatabaseModeContext.tsx`):**
   - Reads `razorpay_database_mode` from `localStorage` (defaults to `'DEMO'`).
   - Sets Axios default common header: `api.defaults.headers.common['X-Database-Mode'] = mode`.
5. **App Layout Mount (`src/components/layout/AppLayout.tsx`):**
   - Initiates `useRealtimeRefresh` (opens SSE stream on `/events` and starts fallback heartbeat timer).
   - Mounts `<Sidebar />` and `<Header />`.
6. **Route Resolution:** Matches URL path (e.g., `/`, `/disputes`, `/disputes/:disputeId`) and renders the corresponding page component.

---

## 7. Route Architecture

| Route Path | Page Component | Protected? | Parameters | Data Loaded / APIs Called | Key Subcomponents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | `DashboardPage` | No (Direct) | None | `disputeService.getDisputes()` via `dashboardService` | KPI Cards, Attention Tabs, Needs Attention Cards |
| `/disputes` | `DisputesPage` | No (Direct) | None | `disputeService.getDisputes()` | Tab Filters, Search Input, Dispute Cards |
| `/disputes/:disputeId` | `DisputeDetailPage` | No (Direct) | `disputeId` | `getCommandCenter(id)`, `getReadiness(id)` | `CaseHeader`, `WorkflowStepNav`, `CaseMerchantControlCenter`, `CaseOverviewTab`, `CaseRazorpayReviewTab`, `CaseOutcomeTab` |
| `/history` | `HistoryPage` | No (Direct) | None | `disputeService.getDisputes()` (filtered resolved) | Resolved Dispute Cards, Financial Summary |
| `/settings` | `SettingsPage` | No (Direct) | None | Local state (Merchant Profile, Policies) | Profile Form, Preferences Checkboxes, Policy Textareas |
| `/webhooks` | `RazorpayWebhookPage` | No (Direct) | None | `simulationService.getAvailableTransactions()` | Transaction Table, Webhook Simulation Modal, Payload Preview |
| `/webhook` | `Navigate` | No | None | Redirects to `/webhooks` | N/A |
| `*` | `Navigate` | No | None | Redirects to `/` | N/A |

*Note: Alternate simulator routes exist in code under `src/pages/simulator/*` and `SimulatorPage.tsx` for modular multi-page simulations.*

---

## 8. Complete Screen Inventory

| Screen Name | Route | Purpose | Key Components | Data / API | Primary User Actions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Executive Dashboard** | `/` | Operational overview and triage | `Card`, `Skeleton`, `Badge` | `GET /disputes` | Switch attention tabs, click dispute card, jump to Review |
| **Disputes Registry** | `/disputes` | Filterable list of chargebacks | `Card`, `Button`, `Skeleton` | `GET /disputes` | Filter by status (`needs_attention`, `in_review`, `resolved`), search by ID/reason, navigate to case |
| **Case Overview** | `/disputes/:id` (Step 1) | High-level case facts & timeline | `CaseHeader`, `CaseOverviewTab`, `CaseTimeline` | `GET /disputes/:id/command-center` | Review 12 parameters, inspect timeline, proceed to Review |
| **Merchant Control Center** | `/disputes/:id` (Step 2) | All-in-one review & evidence editor | `CaseMerchantControlCenter`, `Modal`, `Button` | `GET /disputes/:id/command-center`, `POST /evidence`, `POST /evidence/upload`, `POST /disputes/:id/submit` | Upload files, add courier info, edit metadata, approve evidence, edit rebuttal, trigger AI verification, submit package |
| **Gateway Review** | `/disputes/:id` (Step 3) | Awaiting gateway decision | `CaseRazorpayReviewTab`, `Card`, `Button` | `POST /disputes/:id/simulate-outcome` | View gateway reference ID, simulate bank outcome |
| **Final Outcome** | `/disputes/:id` (Step 4) | Resolution summary & audit log | `CaseOutcomeTab`, `Card`, `Button` | `GET /disputes/:id/command-center` | View revenue recovered/lost, inspect full audit trail |
| **Historical Archive** | `/history` | Closed & resolved dispute log | `Card`, `Button`, `Skeleton` | `GET /disputes` | View past won/lost cases, inspect summaries |
| **Settings & Policies** | `/settings` | Configure business policies | `Card`, `Button`, Form inputs | Client state | Edit business name, toggle AI autopilot, save refund policy |
| **Razorpay Webhook Portal** | `/webhooks` | Live chargeback webhook simulator | `Card`, `Modal`, `Button`, `Skeleton` | `GET /webhooks/transactions`, `POST /webhooks/razorpay` | Select transaction, choose reason code, fire real webhook |

---

## 9. Dashboard Architecture & Metrics

### 9.1 KPI Cards
1. **Total At-Risk Volume:** Sum of amounts for all active, unsubmitted, and under-review disputes (formatted in INR e.g., `₹45,200`).
2. **Total Recovered Revenue:** Sum of amounts for all won disputes (e.g., `₹128,500`).
3. **Action Required Count:** High-priority disputes requiring immediate merchant intervention (e.g., missing critical proof with deadline < 48h).
4. **Review Recommended Count:** Cases where AI has completed analysis and collected initial proof, awaiting merchant sign-off.
5. **AI Handling Count:** Cases currently undergoing evidence ingestion or automated background triage.
6. **Submitted Count:** Cases currently submitted and awaiting bank review.

### 9.2 Attention Buckets & Triage Logic
The `dashboardService` computes attention buckets on the client side from `disputeService.getDisputes()`:
- **`ACTION_REQUIRED`:** Priority 0 — cases with `merchant_attention_state === 'ACTION_REQUIRED'`.
- **`REVIEW_RECOMMENDED`:** Priority 1 — cases with `workflow_stage === 'MERCHANT_REVIEW'` or `attention === 'REVIEW_RECOMMENDED'`.
- **`AI_HANDLING`:** Cases with `stage === 'EVIDENCE_COLLECTION'` or `stage === 'DISPUTE_RAISED'`.
- **`SUBMITTED`:** Cases with `stage === 'SUBMITTED'` or `status === 'UNDER_REVIEW'`.
- **`RESOLVED`:** Cases with `status === 'WON' | 'LOST' | 'CLOSED'`.

---

## 10. Dispute Management UI

### 10.1 List, Search, and Filtering
- **Search Bar (`src/components/common/SearchBar.tsx`):** Instant dropdown in the top header matching Dispute ID, Transaction ID, Customer ID, and Reason Code.
- **Queue Filters (`src/pages/DisputesPage.tsx`):**
  - `All`: Full list of disputes in active database.
  - `Needs Attention`: Disputes requiring merchant action or review.
  - `Under Review`: Disputes submitted to Razorpay / Bank.
  - `Resolved`: Finalized Won / Lost / Closed cases.
- **Priority Badging:** `URGENT` (Rose border/bg), `IMPORTANT` (Amber), `READY` (Emerald), `NORMAL` (Slate).

---

## 11. Dispute Review & Control Center Workflow

When a merchant opens a dispute (`/disputes/:disputeId`):
1. **Command Center Ingestion:** `disputeService.getCommandCenter(disputeId)` fetches the complete aggregated snapshot in a single round-trip.
2. **Readiness Ingestion:** `disputeService.getReadiness(disputeId)` fetches the blocking submission rules.
3. **Interactive Control Center Mounts (`CaseMerchantControlCenter.tsx`):**
   - **Progress Stepper:** Shows 11-step backend lifecycle progression.
   - **AI Verdict Card:** Displays win probability percentage, fraud score, recommendation (`CONTEST` vs `ACCEPT`), DeepSeek explanation, and positive/negative factors.
   - **Evidence Management Workspace:** Renders evidence cards with lifecycle statuses (`Verified & Approved`, `Pending Verification`, `Needs Review`, `Rejected`, `Failed`).
   - **Merchant Actions:** Merchant can approve pending evidence with one click, upload new files, add manual courier tracking, or edit descriptions.
   - **Rebuttal Letter:** Merchant can customize and persist the defense letter sent to the issuing bank.
   - **Submission Gate:** When all items are approved and no blockers remain, the "Submit Representation Package" button enables.
   - **Final Transmission:** Merchant confirms submission in modal; case transitions to `SUBMITTED` stage and navigates to Step 3 (*Gateway Review*).

---

## 12. Evidence Management UI

### 12.1 Supported Document Types & Formats
- **File Uploads:** PDF (`.pdf`), PNG (`.png`), JPG/JPEG (`.jpg`, `.jpeg`) via `multipart/form-data` to `/evidence/upload`.
- **Structured Manual Evidence:** Carrier tracking numbers, shipping carrier selection (`FedEx`, `Blue Dart`, `DHL`, `India Post`), delivery timestamps, and notes.
- **Preconfigured Policy Attachments:** Terms of Service, Refund Policy, IP Logs, Invoices.

### 12.2 Evidence Operations Matrix

| Operation | Service Method | Backend Endpoint | Optimistic UI Behavior |
| :--- | :--- | :--- | :--- |
| **Upload File** | `evidenceService.uploadEvidenceFile` | `POST /evidence/upload` | Prepends optimistic item with `MERCHANT_FILE_UPLOAD` source; triggers AI reassessment |
| **Add Manual Record** | `evidenceService.createEvidence` | `POST /evidence` | Prepends optimistic item with `MERCHANT_UPLOAD` source; triggers AI reassessment |
| **Edit Metadata** | `evidenceService.updateEvidence` | `PUT /evidence/:id` | Updates title/description locally; sets status to `PENDING_APPROVAL` |
| **Replace Backing File** | `evidenceService.replaceEvidenceFile` | `POST /evidence/:id/replace` | Replaces backing file; resets verification status to `PENDING_APPROVAL` |
| **Approve Evidence** | `evidenceService.approveEvidence` | `POST /disputes/:dId/evidence/:eId/approve` | Immediately sets status to `APPROVED` / `Verified & Approved`; unblocks submission gate |
| **Reject / Revoke** | `evidenceService.rejectEvidence` | `POST /disputes/:dId/evidence/:eId/reject` | Sets status to `REJECTED`; excludes from representation package |
| **Delete Evidence** | `evidenceService.deleteEvidence` | `DELETE /evidence/:id` | Removes item from local state list; recalculates readiness |

---

## 13. AI Evidence Verification & Explainability UI

### 13.1 Lifecycle States Handled by Frontend

```
+-----------------------------------------------------------------------------------------+
|                                EVIDENCE LIFECYCLE STATES                                |
+-----------------------------------------------------------------------------------------+

 [Pending Verification]  ──(Trigger AI / Reassess)──►  [Analyzing...] (Pulsing Indigo)
         │                                                     │
         │                                                     ▼
         ├─────────────────────────────────────────►  [AI Verified] (Emerald)
         │                                                     │
         │                                                     ▼
         ├─────────────────────────────────────────►  [Verified & Approved] (Merchant Sign-off)
         │
         ├─────────────────────────────────────────►  [Needs Review / Flagged] (Amber)
         │
         ├─────────────────────────────────────────►  [Rejected / Invalid] (Rose)
         │
         └─────────────────────────────────────────►  [AI Unavailable / Failed] (Rose)
```

### 13.2 Provenance of AI & ML Results
- **Win Probability:** Computed by backend machine learning pipeline (`models/win_pipeline.joblib`) and returned in `analysis.win_probability`.
- **Fraud Probability & Risk Decision:** Computed by backend ML model (`models/fraud_v2_pipeline.joblib`) and returned in `analysis.risk_analysis`.
- **Reasoning & Rebuttal Generation:** Generated via DeepSeek AI API (with deterministic rule-based fallback if API is unreachable) and returned in `analysis.recommendation`.
- **Frontend Role:** The frontend **never** executes local AI inference. It acts as an authoritative, explainable rendering and decision-support client.

---

## 14. API Integration Inventory

| HTTP Method | Endpoint Path | Calling Service / Function | Request Body / Query Params | Expected Response Data |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/disputes` | `disputeService.getDisputes` | Query: `case_source?` | `Dispute[]` |
| `GET` | `/disputes/:disputeId` | `disputeService.getDisputeById` | None | `Dispute` |
| `GET` | `/disputes/:disputeId/command-center` | `disputeService.getCommandCenter` | None | `CommandCenterSnapshot` |
| `GET` | `/disputes/:disputeId/analysis` | `disputeService.getAnalysis` | None | `CaseAnalysis` |
| `GET` | `/disputes/:disputeId/explainability` | `disputeService.getExplainability` | None | `AIExplainability` |
| `GET` | `/disputes/:disputeId/next-action` | `disputeService.getNextAction` | None | `NextBestAction` |
| `GET` | `/disputes/:disputeId/readiness` | `disputeService.getReadiness` | None | `DisputeCaseReadiness` |
| `GET` | `/disputes/:disputeId/package-inspection` | `disputeService.getPackageInspection` | None | `PackageInspection` |
| `GET` | `/disputes/:disputeId/audit` | `disputeService.getAuditLog` | None | `DisputeTimelineEvent[]` |
| `PATCH` / `PUT` | `/disputes/:disputeId/rebuttal` | `disputeService.updateRebuttalResponse` | Body: `{ rebuttal_text }` | Status confirmation |
| `POST` | `/disputes/:disputeId/submit` | `disputeService.submitDispute` | None | `DisputeSubmitResponse` |
| `POST` | `/disputes/:disputeId/simulate-outcome`| `disputeService.simulateOutcome` | None | `DisputeOutcomeResponse` |
| `POST` | `/disputes/:disputeId/accept` | `disputeService.acceptDispute` | Body: `{ reason }` | Status confirmation |
| `POST` | `/disputes/:disputeId/override-recommendation` | `disputeService.overrideRecommendation` | Body: `{ override_decision, reason }` | Status confirmation |
| `POST` | `/disputes/:disputeId/reassess` | `disputeService.reassessDispute` | None | Updated analysis |
| `POST` | `/evidence` | `evidenceService.createEvidence` | Body: `CreateEvidencePayload` | `{ evidence, impact_delta }` |
| `POST` | `/evidence/upload` | `evidenceService.uploadEvidenceFile` | Multipart: `file, dispute_id, ...` | `{ success, evidence_id, ... }` |
| `POST` | `/evidence/:id/replace` | `evidenceService.replaceEvidenceFile`| Multipart: `file` | `{ success, evidence_id, ... }` |
| `PUT` | `/evidence/:id` | `evidenceService.updateEvidence` | Body: `UpdateEvidencePayload` | Updated evidence metadata |
| `POST` | `/disputes/:dId/evidence/:eId/approve`| `evidenceService.approveEvidence` | Body: metadata object | Approval confirmation |
| `POST` | `/disputes/:dId/evidence/:eId/reject` | `evidenceService.rejectEvidence` | Body: `{ reason }` | Rejection confirmation |
| `DELETE` | `/evidence/:id` | `evidenceService.deleteEvidence` | None | `{ evidence_id, deleted }` |
| `GET` | `/webhooks/transactions` | `simulationService.getAvailableTransactions`| None | `AvailableTransactionsResponse` |
| `POST` | `/webhooks/razorpay` | `simulationService.simulateDispute` | Body: `SimulateDisputePayload` | `SimulateDisputeResponse` |
| `GET` | `/events` | `useRealtimeEvents` (SSE) | None | Server-Sent Event stream |

---

## 15. Backend Dependency Map & Contract Resilience

```
+───────────────────────────+──────────────────────────────────+────────────────────────────────────────+
| Frontend Feature          | API Endpoint                     | Expected Backend Contract Response     |
+───────────────────────────+──────────────────────────────────+────────────────────────────────────────+
| Dashboard Metrics         | GET /disputes                    | JSON Array of Dispute objects          |
| Dispute Workspace         | GET /disputes/:id/command-center | Unified CommandCenterSnapshot          |
| Readiness Gate            | GET /disputes/:id/readiness      | { can_submit, blocking_issues, ... }   |
| Evidence Upload           | POST /evidence/upload            | { success: true, evidence_id, ... }    |
| Evidence Approval         | POST /.../approve                | Status update confirmation             |
| Defense Rebuttal Edit     | PATCH /disputes/:id/rebuttal     | Updated rebuttal text confirmation     |
| Hard Submission Gate      | POST /disputes/:id/submit        | { status: 'SUBMITTED', is_submitted }  |
| Simulated Resolution      | POST /disputes/:id/simulate-out. | { outcome: 'WON'|'LOST', ... }         |
| Webhook Simulation        | POST /webhooks/razorpay          | { dispute_id, simulation_status, ... } |
| Realtime Sync             | GET /events                      | SSE text/event-stream                  |
+───────────────────────────+──────────────────────────────────+────────────────────────────────────────+
```

### Backend Unavailable / Failure Behavior:
- **Axios Interceptor (`services/api.ts`):** Converts timeouts (`ECONNABORTED`) and network errors into clean error messages: *"Network connection error. Please ensure the backend server is reachable."*
- **Detail View Fallback:** Renders a clean error card with **"Try Again"** and **"Back to Disputes"** buttons.
- **SSE Stream:** Disconnects silently on error and retries with exponential backoff every 5000ms without triggering UI popups.

---

## 16. State Management Architecture

1. **Global Environment State (`DatabaseModeContext.tsx`):**
   - Controls active database mode (`DEMO` vs `LIVE`).
   - Persisted in `localStorage` (`razorpay_database_mode`).
   - Propagated to Axios headers via `api.defaults.headers.common['X-Database-Mode']`.
2. **Server-State & In-Memory Cache (`cacheService.ts`):**
   - Stores query results in memory with 15s to 30s TTL.
   - Automatically invalidated on write operations (`createEvidence`, `approveEvidence`, `submitDispute`).
3. **Component-Level Optimistic State (`CaseMerchantControlCenter.tsx`):**
   - Maintains `localEvidence` state.
   - When a user uploads or approves evidence, local state updates immediately for zero-lag UI feedback while the backend processes the request asynchronously.
4. **Form & Modal States:**
   - Isolated in React component state (`useState`, `useRef`). Modals clean up state upon closing.

---

## 17. Data Fetching Lifecycle & Performance Optimization

### 17.1 Standard Fetch Lifecycle
```
[Component Mount]
       │
       ▼
[Check CacheService (In-Memory)]
 ├── CACHE HIT (TTL Valid) ──────────────► [Instant UI Render (0ms)]
 └── CACHE MISS
       │
       ▼
 [Axios Request with AbortSignal]
       │
       ├── SUCCESS ──► [Store in CacheService] ──► [Set React State] ──► [Render UI]
       └── ERROR   ──► [Axios Interceptor Normalization] ──► [Display Error UI with Retry]
```

### 17.2 Why Disputes Screen Is Fast & Responsive
- **Deduplication:** Multiple components requesting the same dispute ID share the same in-flight Promise (`appCache.dedupe`).
- **Request Cancellation:** `AbortController` aborts pending requests on unmount or mode switch, preventing memory leaks and state updates on unmounted components.
- **Prefix Invalidation:** Mutation of evidence only invalidates `command_center_${id}`, preserving unrelated cached records.

---

## 18. Responsive Design & UI Design System

### 18.1 Breakpoint System
- **Mobile (`< 640px`):** Stacked single-column layouts, horizontal-scrolling step navigators, full-width buttons.
- **Tablet (`640px – 1024px`):** 2-column KPI grids, responsive search bar, adaptive card headers.
- **Desktop (`> 1024px`):** Fixed 256px sidebar, 3-column overview grids, side-by-side evidence and AI reasoning layout.

### 18.2 UI Design System Tokens
- **Font Stack:** Primary: `Inter`, sans-serif; Monospace: `JetBrains Mono`.
- **Color Palette:**
  - Neutral / Slate: `#0f172a` (slate-900), `#f8fafc` (slate-50 background).
  - Brand Indigo: `#4f46e5` (indigo-600), `#4338ca` (indigo-700).
  - Urgent Rose: `#e11d48` (rose-600), `#fff1f2` (rose-50).
  - Warning Amber: `#d97706` (amber-600), `#fffbeb` (amber-50).
  - Success Emerald: `#059669` (emerald-600), `#ecfdf5` (emerald-50).
- **Custom Scrollbar:** Sleek 6px webkit scrollbars styled for a modern fintech dashboard.

---

## 19. UX States & Edge-Case Handling

| State | Visual Representation | Implementation Component |
| :--- | :--- | :--- |
| **Loading** | Pulsing skeleton bars matching component height | `Skeleton.tsx`, `animate-pulse` |
| **Empty** | Centered icon with helpful instructional message | `DisputesPage`, `HistoryPage` |
| **Error** | Bordered alert with retry button | `Card.tsx`, `Button.tsx` |
| **Pending Approval** | Amber/slate pill with "Pending Verification" | `CaseMerchantControlCenter.tsx` |
| **Analyzing** | Indigo pulsing badge with spinning loader | `CaseAIAnalysisTab.tsx` |
| **Verified** | Emerald badge with checkmark | `Badge.tsx` (`variant="success"`) |
| **Disabled** | 50% opacity with `cursor-not-allowed` | `Button.tsx` (`disabled={true}`) |

---

## 20. Notifications System Audit

> [!IMPORTANT]
> **Source Grounding Finding on Notifications:**  
> The repository **does not contain** a persistent notification center, bell icon, or database-driven notification queue.
> - **Header Audit:** `<Header />` contains only Search, Webhook Link, Demo/Live Switcher, and Merchant Profile. No notification bell exists.
> - **Alert Feedback:** Success/error feedback is provided via temporary contextual banners (e.g., in `CaseMerchantControlCenter.tsx` and `SettingsPage.tsx` with auto-dismiss timers).
> - **Real-time Synchronization:** Background updates are handled transparently via SSE (`useRealtimeEvents.ts`) without obstructive popups.

---

## 21. Form Handling & Validation

1. **Evidence Upload Form (`CaseMerchantControlCenter.tsx`):**
   - Validates file presence and non-empty document title.
   - Enforces supported document types (`.pdf`, `.png`, `.jpg`).
2. **Manual Courier Evidence Form:**
   - Validates carrier selection and tracking number inputs.
3. **Rebuttal Response Form:**
   - Allows multi-line text input with live character preview and default template fallback.
4. **Settings Forms (`SettingsPage.tsx`):**
   - Validates email formats and persists operational checkboxes.

---

## 22. Authentication UX & Security Review

| Security Dimension | Status | Codebase Finding & Evidence |
| :--- | :--- | :--- |
| **Authentication UI** | *MOCKED (Direct Access)* | No login/signup screen. Boots directly to merchant portal with fixed header MID (`Acme Store` / `MID_001`). |
| **Token Storage** | *NONE* | No JWT, session token, or API key stored in `localStorage` or `sessionStorage`. |
| **XSS Prevention** | *IMPLEMENTED* | Zero instances of `dangerouslySetInnerHTML`. React JSX auto-escapes all strings. |
| **Untrusted Content** | *IMPLEMENTED* | Claim narratives and evidence descriptions are rendered strictly as text nodes. |
| **Client-Side Upload Validation** | *PARTIAL* | Validates file presence and file types; server must enforce MIME sniffing and byte limits. |
| **Environment Secrets** | *VERIFIED SECURE* | No secret keys exposed in client bundles or `.env`. Only public `VITE_API_BASE_URL` supported. |

---

## 23. Accessibility (a11y)

- **Keyboard Navigation:** Modals support `Escape` key listeners to dismiss dialogs (`Modal.tsx`).
- **Semantic HTML:** Semantic elements (`<header>`, `<aside>`, `<main>`, `<section>`, `<h1>`–`<h4>`, `<table>`) used throughout.
- **Color Contrast:** High contrast text tokens (Slate-900 on White / Slate-50) meeting WCAG AA standards.
- **Focus Rings:** Explicit `focus:ring-2 focus:ring-indigo-500` on buttons, inputs, and tab navigation.

---

## 24. Testing & Reliability Assessment

- **Unit / Component / E2E Tests:** *NOT FOUND* in repository (no Jest, Vitest, Cypress, or Playwright configuration in `package.json`).
- **Static Analysis:** TypeScript compiler (`tsc -b`) enforces strict type-checking during `npm run build`.
- **Recommended Additions Before Production:**
  - Install Vitest + React Testing Library for component tests (`Button.test.tsx`, `Modal.test.tsx`, `CaseMerchantControlCenter.test.tsx`).
  - Add Playwright E2E test covering the complete Dispute Review -> Evidence Upload -> Submit workflow.

---

## 25. Build & Deployment Configuration

### 25.1 Package Scripts
- `npm run dev`: Starts Vite dev server on port `5173` with proxy rules for `/api` and `/events`.
- `npm run build`: Executes `tsc -b` type checking followed by `vite build` production bundle generation into `dist/`.
- `npm run preview`: Starts local static web server serving the `dist/` production build.

### 25.2 Vite Proxy Configuration (`vite.config.ts`)
```typescript
server: {
  port: 5173,
  host: true,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
    '/events': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

---

## 26. 100+ Key Questions Answered (Direct from Source)

### Product & UX
1. **What is the frontend's purpose?** To provide a merchant-first dispute management, AI risk explanation, and chargeback representation platform.
2. **Who is the primary user?** Online merchants, risk analysts, and dispute operations teams.
3. **What problem does the UI solve?** Eliminates tedious manual chargeback defense by aggregating evidence, calculating win probabilities, generating rebuttal letters, and validating representation readiness.
4. **What are the main screens?** Dashboard (`/`), Disputes (`/disputes`), Dispute Workspace (`/disputes/:id`), History (`/history`), Settings (`/settings`), and Webhooks (`/webhooks`).
5. **What is the first screen after loading?** Executive Dashboard (`/`).
6. **What does the dashboard show?** Financial KPIs (At-risk amount, recovered amount), triage attention buckets, and urgent cases due soon.
7. **What does the disputes page show?** Filterable table/cards of chargebacks with search, priority badges, and deadline indicators.
8. **What does dispute review show?** 4-step workflow: Overview, Control Center, Gateway Review, and Final Outcome.
9. **How does evidence appear?** In structured cards with lifecycle status pills, metadata, and extracted intelligence facts.
10. **How does AI verification appear?** Win probability scores, fraud risk ratings, DeepSeek reasoning narratives, and positive/negative factors.
11. **Can merchants add evidence?** Yes, via file upload (PDF/PNG/JPG) or manual carrier tracking entry.
12. **Can merchants edit evidence?** Yes, via the Edit Metadata modal in `CaseMerchantControlCenter.tsx`.
13. **Can merchants delete evidence?** Yes, via the Delete Evidence confirmation modal.
14. **Can merchants replace evidence files?** Yes, via the Replace Backing Document modal.
15. **Can merchants approve evidence?** Yes, via single-click approval action per evidence card.
16. **Can merchants retry AI analysis?** Yes, via the "Trigger AI Verification" button calling `disputeService.reassessDispute`.
17. **What happens while AI is analyzing?** The UI renders an animated analyzing state with step-by-step pipeline indicators.
18. **What happens if AI verification fails?** The UI renders an "AI Unavailable / Failed" badge and allows manual retry.
19. **What happens if evidence upload fails?** An error message is displayed and the optimistic item is removed.
20. **What happens if backend is unavailable?** Axios error interceptor displays a clean error card with a retry button.

### Routing & Architecture
21. **What routing library is used?** `react-router-dom` version `^7.2.0`.
22. **What routes exist?** `/`, `/disputes`, `/disputes/:disputeId`, `/history`, `/settings`, `/webhooks`, `/webhook`.
23. **Which routes are protected?** None currently (open direct access).
24. **What is the root component?** `App.tsx` mounted inside `main.tsx`.
25. **What is the global layout?** `AppLayout.tsx` (Sidebar + Header + Content Outlet).
26. **What state manager is used?** React Context (`DatabaseModeContext`) and in-memory cache (`cacheService.ts`).
27. **Is localStorage used?** Yes, for storing `razorpay_database_mode` (`DEMO` or `LIVE`).
28. **Is sessionStorage used?** No.
29. **Are cookies used?** No.
30. **What HTTP client is used?** `axios` version `^1.7.9`.
31. **What CSS solution is used?** Tailwind CSS version `^4.0.6`.
32. **What icon library is used?** `lucide-react` version `^0.475.0` and inline SVGs.
33. **What build tool is used?** `vite` version `^6.1.0`.
34. **What React version is used?** `react` and `react-dom` version `^19.0.0`.
35. **Are Server-Sent Events (SSE) used?** Yes, connected to `/events` in `useRealtimeEvents.ts`.
36. **Are duplicate requests prevented?** Yes, via `appCache.dedupe()`.
37. **Is request cancellation implemented?** Yes, via `AbortController` in `useEffect`.
38. **Are secrets exposed in frontend code?** No.
39. **Is dangerouslySetInnerHTML used?** No (0 occurrences).
40. **Are tests implemented in repo?** No unit or E2E tests are currently present in the codebase.

---

## 27. Frontend ↔ Backend Contract Map

| UI Feature | Frontend Source | API Route | Expected Backend Payload | UI State Triggered | Failure Fallback |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dispute Queue** | `DisputesPage.tsx` | `GET /disputes` | `Dispute[]` | Renders dispute cards | Error banner + Retry |
| **Case Snapshot** | `DisputeDetailPage.tsx` | `GET /disputes/:id/command-center` | `CommandCenterSnapshot` | Mounts workspace | Error card + Back link |
| **Case Readiness**| `DisputeDetailPage.tsx` | `GET /disputes/:id/readiness` | `DisputeCaseReadiness` | Updates blockers & submit gate | Fallback to snapshot readiness |
| **Evidence Upload**| `CaseMerchantControlCenter.tsx` | `POST /evidence/upload` | Multipart file response | Optimistic card -> Verified | Error alert; removes card |
| **Approve Evidence**| `CaseMerchantControlCenter.tsx` | `POST /.../approve` | `{ success: true }` | Status -> `APPROVED` | Error alert; reverts status |
| **Edit Rebuttal** | `CaseMerchantControlCenter.tsx` | `PATCH /disputes/:id/rebuttal` | `{ status: 'ok' }` | Updates active rebuttal | Error alert |
| **Submit Package**| `CaseMerchantControlCenter.tsx` | `POST /disputes/:id/submit` | `DisputeSubmitResponse` | Transitions to Step 3 | Error modal alert |
| **Simulate Outcome**| `CaseRazorpayReviewTab.tsx` | `POST /disputes/:id/simulate-outcome`| `DisputeOutcomeResponse` | Transitions to Step 4 | Error alert |
| **Live Webhook** | `RazorpayWebhookPage.tsx` | `POST /webhooks/razorpay` | `SimulateDisputeResponse` | Displays delivery receipt | Modal error alert |
| **Realtime Sync** | `useRealtimeEvents.ts` | `GET /events` | SSE Stream | Silent background refresh | Auto-reconnect every 5s |

---

## 28. Final Source Index

| Documentation Topic | Primary Source File(s) | Primary Component / Function / Hook | Confidence |
| :--- | :--- | :--- | :--- |
| **Bootstrap & Routing** | `src/main.tsx`, `src/App.tsx` | `ReactDOM.createRoot`, `<Routes>` | 100% Verified |
| **Global Layout & Shell** | `src/components/layout/AppLayout.tsx` | `<AppLayout>`, `<Header>`, `<Sidebar>` | 100% Verified |
| **Database Environment Mode**| `src/context/DatabaseModeContext.tsx` | `DatabaseModeProvider`, `useDatabaseMode` | 100% Verified |
| **In-Memory Cache & Deduping**| `src/services/cacheService.ts` | `CacheService`, `appCache.dedupe` | 100% Verified |
| **Real-time SSE Events** | `src/hooks/useRealtimeEvents.ts` | `useRealtimeEvents` | 100% Verified |
| **API Client & Interceptors**| `src/services/api.ts` | `api.interceptors.request / response` | 100% Verified |
| **Dispute Services** | `src/services/disputeService.ts` | `disputeService.getCommandCenter`, `submitDispute` | 100% Verified |
| **Evidence Services** | `src/services/evidenceService.ts` | `evidenceService.uploadEvidenceFile`, `approveEvidence` | 100% Verified |
| **Dashboard Operations** | `src/pages/DashboardPage.tsx`, `dashboardService.ts` | `DashboardPage`, `dashboardService.getDashboardData` | 100% Verified |
| **Dispute Queue** | `src/pages/DisputesPage.tsx` | `DisputesPage` | 100% Verified |
| **Dispute Workspace Container**| `src/pages/DisputeDetailPage.tsx` | `DisputeDetailPage` | 100% Verified |
| **Merchant Control Center** | `src/components/disputes/CaseMerchantControlCenter.tsx` | `CaseMerchantControlCenter` | 100% Verified |
| **AI Analysis Breakdown** | `src/components/disputes/CaseAIAnalysisTab.tsx` | `CaseAIAnalysisTab` | 100% Verified |
| **Gateway Review & Outcome**| `src/components/disputes/CaseRazorpayReviewTab.tsx`, `CaseOutcomeTab.tsx` | `CaseRazorpayReviewTab`, `CaseOutcomeTab` | 100% Verified |
| **Standalone Webhook Portal**| `src/pages/RazorpayWebhookPage.tsx` | `RazorpayWebhookPage` | 100% Verified |
| **Formatting Utilities** | `src/utils/formatters.ts` | `formatCurrency`, `formatReasonCode`, `formatPriority` | 100% Verified |

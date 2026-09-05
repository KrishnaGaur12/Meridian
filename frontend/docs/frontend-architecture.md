# Frontend Architecture Specification

## 1. System Overview
The **Razorpay AI Risk Manager Frontend** is a Single-Page Application (SPA) constructed using **React 19**, **TypeScript 5.7**, **Vite 6**, and **Tailwind CSS v4**. It interfaces with a Python FastAPI backend over RESTful HTTP endpoints and an asynchronous Server-Sent Events (SSE) stream.

---

## 2. Complete Architectural Diagram

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
[<Sidebar />]      [<Header />]
   │               (Mode Toggle, Search)
   │                     │
   └──────────┬──────────┘
              ▼
       [<Outlet />]
              │
   ┌──────────┼───────────────┬──────────────┐
   ▼          ▼               ▼              ▼
Dashboard  Disputes     DisputeDetail     History
   (/)    (/disputes) (/disputes/:id)   (/history)
                              │
                   ┌──────────┴──────────┐
                   ▼                     ▼
           CaseOverviewTab    CaseMerchantControlCenter
                   │                     │
                   ▼                     ▼
           CaseRazorpayReview     CaseOutcomeTab
```

---

## 3. Directory Layout & Module Responsibilities

```
src/
├── components/
│   ├── common/               # UI Atoms: Badge, Button, Card, Modal, SearchBar, Skeleton
│   ├── layout/               # Shell: AppLayout, Header, Sidebar, SimulatorLayout
│   └── disputes/             # Domain: CaseMerchantControlCenter, Tabs, Steppers
├── context/
│   └── DatabaseModeContext.tsx # Environment Context (DEMO / LIVE)
├── hooks/
│   ├── useRealtimeEvents.ts  # SSE EventSource Listener
│   └── useRealtimeRefresh.ts # Heartbeat & SSE Coordinator
├── pages/
│   ├── DashboardPage.tsx     # Executive Overview
│   ├── DisputesPage.tsx      # Disputes Queue
│   ├── DisputeDetailPage.tsx # Workspace Route Controller
│   ├── HistoryPage.tsx       # Resolved Archives
│   ├── SettingsPage.tsx      # Merchant Preferences
│   └── RazorpayWebhookPage.tsx # Standalone Webhook Simulator
├── services/
│   ├── api.ts                # Axios Client Instance
│   ├── cacheService.ts       # In-Memory Cache with TTL & Deduplication
│   ├── dashboardService.ts   # Metric Aggregator
│   ├── disputeService.ts     # Dispute APIs
│   ├── evidenceService.ts    # Evidence & File Upload APIs
│   └── simulationService.ts  # Simulator & Webhook APIs
├── types/                    # Static TypeScript Interfaces & Types
└── utils/
    └── formatters.ts         # Currency, Reason Code, Priority, Deadline Formatters
```

---

## 4. Key Architectural Patterns

### 4.1 Single-Trip Command Center Aggregation
Instead of executing 6 separate HTTP requests on the dispute detail page, the frontend calls `GET /disputes/:disputeId/command-center` which aggregates:
- Dispute core record
- Machine learning win-probability & fraud assessment
- Evidence intelligence & extracted parameters
- AI explainability & positive/negative factors
- Readiness gate requirements & blockers
- Chronological timeline audit trail

### 4.2 In-Memory TTL Caching & Deduplication (`cacheService.ts`)
- Eliminates unnecessary network traffic and perceived UI latency.
- Concurrent requests for the same dispute key share the exact same in-flight Promise.
- Mutation methods (`uploadEvidenceFile`, `approveEvidence`, `submitDispute`) execute targeted prefix invalidation.

### 4.3 Real-Time SSE Synchronization (`useRealtimeEvents.ts`)
- Automatically listens to backend events (`DISPUTE_CREATED`, `ML_ANALYSIS_COMPLETED`, `DEEPSEEK_ANALYSIS_COMPLETED`, `EVIDENCE_APPROVED`).
- Re-fetches current workspace silently without triggering loading spinners or blocking user interaction.

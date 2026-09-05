# Frontend API Integration Specification

## 1. HTTP Client & Base Configuration (`src/services/api.ts`)

- **Base URL:** `import.meta.env.VITE_API_BASE_URL || '/api'`
- **Timeout:** 20,000 ms
- **Default Headers:**
  - `Content-Type: application/json`
  - `Accept: application/json`
  - `X-Database-Mode: DEMO` (dynamically injected from `localStorage`)

### 1.1 Request Interceptor
```typescript
api.interceptors.request.use(
  (config) => {
    const savedMode = localStorage.getItem('razorpay_database_mode') || 'DEMO';
    config.headers['X-Database-Mode'] = savedMode;
    return config;
  },
  (error) => Promise.reject(error)
);
```

### 1.2 Response Interceptor
```typescript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      (error.code === 'ECONNABORTED'
        ? 'Request timed out. Please verify the backend is running.'
        : 'Network connection error. Please ensure the backend server is reachable.');

    const errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail);
    return Promise.reject(new Error(errorMessage));
  }
);
```

---

## 2. API Services & Endpoints Inventory

### 2.1 Dispute Service (`src/services/disputeService.ts`)
- `getDisputes(caseSource?, signal?, forceRefresh?)`: `GET /disputes` (Cached for 15s)
- `getDisputeById(disputeId, signal?, forceRefresh?)`: `GET /disputes/:disputeId` (Cached for 30s)
- `getCommandCenter(disputeId, signal?, forceRefresh?)`: `GET /disputes/:disputeId/command-center` (Cached for 30s)
- `getAnalysis(disputeId, signal?, forceRefresh?)`: `GET /disputes/:disputeId/analysis` (Cached for 30s)
- `getReadiness(disputeId, signal?, forceRefresh?)`: `GET /disputes/:disputeId/readiness` (Cached for 15s)
- `getPackageInspection(disputeId, signal?, forceRefresh?)`: `GET /disputes/:disputeId/package-inspection` (Cached for 20s)
- `getAuditLog(disputeId, signal?)`: `GET /disputes/:disputeId/audit`
- `updateRebuttalResponse(disputeId, rebuttalText)`: `PATCH /disputes/:disputeId/rebuttal`
- `submitDispute(disputeId)`: `POST /disputes/:disputeId/submit`
- `simulateOutcome(disputeId)`: `POST /disputes/:disputeId/simulate-outcome`
- `acceptDispute(disputeId, reason)`: `POST /disputes/:disputeId/accept`
- `overrideRecommendation(disputeId, overrideDecision, reason)`: `POST /disputes/:disputeId/override-recommendation`
- `reassessDispute(disputeId)`: `POST /disputes/:disputeId/reassess`

### 2.2 Evidence Service (`src/services/evidenceService.ts`)
- `createEvidence(payload)`: `POST /evidence`
- `uploadEvidenceFile(disputeId, file, evidenceType?, title?, description?)`: `POST /evidence/upload` (`multipart/form-data`)
- `replaceEvidenceFile(evidenceId, file, disputeId?)`: `POST /evidence/:evidenceId/replace` (`multipart/form-data`)
- `updateEvidence(evidenceId, payload, disputeId?)`: `PUT /evidence/:evidenceId`
- `approveEvidence(disputeId, evidenceId, extraData?)`: `POST /disputes/:disputeId/evidence/:evidenceId/approve`
- `rejectEvidence(disputeId, evidenceId, reason?)`: `POST /disputes/:disputeId/evidence/:evidenceId/reject`
- `deleteEvidence(evidenceId, disputeId?)`: `DELETE /evidence/:evidenceId`
- `generateEvidencePackage(disputeId)`: `POST /disputes/:disputeId/evidence`

### 2.3 Simulation Service (`src/services/simulationService.ts`)
- `getAvailableTransactions()`: `GET /webhooks/transactions` (fallback: `/demo/available-transactions`)
- `simulateDispute(payload)`: `POST /webhooks/razorpay` (fallback: `/demo/simulate-dispute`)

### 2.4 Server-Sent Events Hook (`src/hooks/useRealtimeEvents.ts`)
- **SSE Stream URL:** `${API_BASE_URL}/events`
- **Supported Event Types:**
  - `DISPUTE_CREATED`
  - `DISPUTE_ANALYSIS_STARTED`
  - `ML_ANALYSIS_COMPLETED`
  - `DEEPSEEK_ANALYSIS_COMPLETED`
  - `DISPUTE_ANALYSIS_COMPLETED`
  - `EVIDENCE_APPROVED`
  - `DISPUTE_STAGE_CHANGED`
  - `DASHBOARD_UPDATED`

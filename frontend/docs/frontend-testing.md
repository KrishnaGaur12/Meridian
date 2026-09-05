# Frontend Testing & Quality Assurance Strategy

## 1. Current Repository Test Status

> [!WARNING]
> **Source Inspection Finding:**  
> The repository currently does **not contain** automated unit tests, component tests, or end-to-end (E2E) suites. No test framework (`vitest`, `jest`, `playwright`, `cypress`) is declared in `package.json`.

---

## 2. Recommended Testing Architecture

### 2.1 Unit & Component Testing (Vitest + React Testing Library)
To ensure long-term stability and prevent regressions, the following test suites should be installed:

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

#### Proposed Test Specifications:
1. **`formatters.test.ts`:**
   - Verify `formatCurrency(1500, 'INR')` outputs `₹1,500`.
   - Verify `formatPriority` accurately classifies cases with `< 48h` deadline as `URGENT`.
   - Verify `formatDeadlineText` handles null, overdue, and upcoming dates.
2. **`cacheService.test.ts`:**
   - Verify in-flight deduplication returns the identical Promise instance.
   - Verify TTL expiration purges stale data after specified duration.
   - Verify `invalidate('command_center_')` deletes matching prefixed entries.
3. **`CaseMerchantControlCenter.test.tsx`:**
   - Verify optimistic rendering of uploaded evidence.
   - Verify that clicking "Approve" transitions verification status to `APPROVED` and unblocks the submission gate.

### 2.2 End-to-End Testing (Playwright)
```bash
npm install -D @playwright/test
```
#### Core E2E Test Workflow:
1. Navigate to `/webhooks` -> Select eligible transaction -> Trigger simulated chargeback.
2. Navigate to `/disputes` -> Verify new dispute appears in `Needs Attention`.
3. Open dispute -> Navigate to Control Center -> Approve evidence -> Edit rebuttal -> Click "Submit Representation Package".
4. Verify transition to Step 3 (*Gateway Review*) and verify simulated outcome resolution (*Won / Lost*).

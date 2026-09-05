# Backend Troubleshooting & Diagnostics Guide

## 1. Common Diagnostics & Solutions

### 1.1 DeepSeek AI Issues

#### Symptom: AI generations show `"is_fallback": true` or `"ai_source": "FALLBACK"`
- **Cause 1**: `DEEPSEEK_API_KEY` is not set or empty in environment.
  - **Resolution**: Add `DEEPSEEK_API_KEY=your_key` to `.env` or set in system environment variables.
- **Cause 2**: DeepSeek API request timed out (>=15s) or returned HTTP 429/500.
  - **Resolution**: Check external network connectivity. The backend automatically produces deterministic rule-based output without failing the API request.

#### Symptom: Evidence analysis returns `UNREADABLE` or `FAILED`
- **Cause**: Uploaded file is empty, password-protected, or in an unsupported format.
  - **Resolution**: Upload a standard PDF, PNG, JPG, or TXT file with extractable text or legible image headers.

---

### 1.2 Submission Gate Issues

#### Symptom: `POST /disputes/{id}/submit` returns HTTP 400 with `"Submission BLOCKED by gate"`
- **Cause**: One or more mandatory representment conditions are not met:
  1. Mandatory required evidence (e.g. `delivery_confirmation` for `product_not_received`) is missing or not approved.
  2. Evidence item was marked `REJECTED` by merchant.
  3. AI response statement has not yet been generated.
  4. Dispute deadline is `OVERDUE`.
- **Resolution**: Call `GET /disputes/{id}/readiness` to inspect the exact `blocking_issues` list and resolve each item before resubmitting.

---

### 1.3 Database Mode & Isolation Issues

#### Symptom: Newly created webhook disputes do not appear on demo dashboard
- **Cause**: Webhooks strictly operate in the `LIVE` database (`live_database.db`), while the demo UI may be pointing to `DEMO` mode (`demo_database.db`).
- **Resolution**:
  - Check active mode via `GET /mode`.
  - Pass HTTP header `X-Database-Mode: LIVE` or query param `?mode=LIVE` to view live webhook disputes.

#### Symptom: Resetting Live database during testing
- **Resolution**: Call `POST /system/reset-live` to clear all simulated disputes and restore the initial 15 clean live transactions.

---

### 1.4 Port & Server Conflicts

#### Symptom: `Address already in use` error when starting Uvicorn
- **Resolution**:
  ```bash
  # Check process occupying port 8000 (Windows PowerShell):
  Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
  # Or start on an alternate port:
  uvicorn main:app --reload --port 8001
  ```

# Frontend Troubleshooting & Operations Runbook

## 1. Common Issues & Resolution Steps

### 1.1 "Network connection error. Please ensure the backend server is reachable."
- **Root Cause:** Vite dev proxy cannot reach `http://localhost:8000`.
- **Resolution:**
  1. Verify the Python FastAPI backend is active and listening on port 8000.
  2. Check `curl http://localhost:8000/docs` in your terminal.
  3. Ensure no firewall or port collision is blocking port 8000.

### 1.2 "No active disputes in Live mode yet"
- **Root Cause:** When switched to **Live Mode**, the backend connects to `live_database.db`, which starts empty until webhook events are created.
- **Resolution:**
  1. Click **"Razorpay Webhook"** in the top navigation bar (or open `/webhooks`).
  2. Select an eligible captured transaction.
  3. Click **"+ Raise Simulated Dispute"** to fire a `dispute.created` webhook.
  4. Return to `/disputes` — the newly created chargeback will appear immediately.

### 1.3 Evidence Upload Returns Error / Doesn't Save
- **Root Cause:** Invalid payload format or missing backend upload directory.
- **Resolution:**
  1. Ensure the file is `< 10MB` and formatted as `.pdf`, `.png`, or `.jpg`.
  2. Verify the backend has write permissions for the evidence directory.
  3. Check developer console network tab for detailed backend JSON response.

### 1.4 Real-time SSE Disconnecting Repeatedly
- **Root Cause:** Backend SSE endpoint `/events` closed the connection or timed out.
- **Resolution:**
  - `useRealtimeEvents.ts` will automatically retry every 5 seconds.
  - Check that the backend FastAPI event stream generator yields keepalive ping comments (`: ping\n\n`) periodically.

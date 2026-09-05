# Backend Security Architecture & Vulnerability Review

## 1. Security Architecture Matrix

| Security Domain | Implementation Status | Implemented Controls & Repository Evidence |
|---|---|---|
| **SQL Injection Prevention** | **IMPLEMENTED** | Parameterized query execution via SQLAlchemy 2.0 ORM. All raw migration commands use parameterized `sqlalchemy.text()`. |
| **Error Sanitization** | **IMPLEMENTED** | Custom exception handlers in `main.py:71-121` intercept `SQLAlchemyError` and unhandled exceptions, returning sanitized error codes (`DATABASE_ERROR`, `INTERNAL_SERVER_ERROR`) without leaking table schemas, queries, or raw stack traces. |
| **File Upload Security** | **IMPLEMENTED** | Strict file extension allowlist (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.txt`, `.csv`, `.json`, `.doc`, `.docx`) and hard 15MB file size limit enforced in `src/evidence/file_processor.py:29-57`. |
| **Path Traversal Protection** | **IMPLEMENTED** | File storage in `src/services/storage.py` resolves relative paths, uses timestamped unique filenames, and isolates all uploads inside `data/uploads/`. |
| **Data Provenance & Hashing** | **IMPLEMENTED** | Immediate computation of SHA-256 document hash on raw upload bytes and SHA-256 content hash on extracted facts (`src/evidence/file_processor.py:40`). |
| **Prompt Injection Protection** | **PARTIAL** | `PromptBuilder.sanitize_context` strips internal database keys. `ClaimEvidenceValidator` rejects any generated claim that cannot be proven by database evidence facts. |
| **PII & Cardholder Data** | **IMPLEMENTED** | Full Primary Account Numbers (PAN) are never stored; only card network and `last4` digits are retained (`src/database/models.py:74`). |
| **CORS Configuration** | **IMPLEMENTED** | Restricted in `main.py:52-61` strictly to frontend development origins: `http://localhost:5173` and `http://127.0.0.1:5173`. |
| **Secret Management** | **IMPLEMENTED** | Secrets (`DEEPSEEK_API_KEY`) loaded from environment variables and `.env`; redacted from logs and API serialization. |
| **Audit Trail Immutability** | **IMPLEMENTED** | State mutations, AI reassessments, merchant approvals, and submissions write immutable event records to `dispute_events`. |
| **Authentication / JWT** | **MISSING** | Endpoints are currently open without token authentication (internal microservice / buildathon architecture). |
| **Rate Limiting** | **MISSING** | No rate-limiting middleware configured on API router. |

---

## 2. Evidence Processing Security Details

```
Merchant File Upload (Multipart Form)
        │
        ├──> Size Check: len(file_bytes) <= 15MB
        │
        ├──> Extension Check: ext in [.pdf, .png, .jpg, .jpeg, .webp, .txt, .csv, .json, .doc, .docx]
        │
        ├──> Cryptographic Integrity: SHA-256 digest computed
        │
        ├──> Isolated File Storage: Saved to data/uploads/ with unique timestamped filename
        │
        ├──> Safe Parsing: PyPDF and Pillow in-memory byte buffer parsing (no arbitrary shell invocation)
        │
        ├──> Context Sanitization: Strips internal DB metadata before formatting prompt
        │
        └──> Post-LLM Claim Verification: ClaimEvidenceValidator verifies every citation against DB evidence
```

---

## 3. Production Hardening Checklist

For enterprise production deployment outside the sandbox environment, the following controls should be implemented:

1. **Authentication & Authorization**: Add OAuth2 with JWT Bearer Token verification and multi-tenant merchant role access.
2. **Rate Limiting**: Integrate `slowapi` or Redis-backed rate-limiting on `/disputes/*/submit` and `/evidence/upload`.
3. **Webhook Verification**: Enforce Razorpay HMAC-SHA256 signature verification on `/webhooks/razorpay`.
4. **Antivirus Scanning**: Add ClamAV / AWS GuardDuty container scanning for uploaded binary attachments.
5. **Database Migration**: Deploy on managed PostgreSQL with encrypted storage at rest (AES-256) and TLS in transit.

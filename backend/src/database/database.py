"""
Database setup for Razorpay AI Risk Manager.
Provides Two-Database Architecture with absolute isolation:
- DEMO DATABASE: data/demo_database.db / data/app_database.db (contains demo scenarios & seeded sandbox cases)
- LIVE DATABASE: data/live_database.db (contains real/live transactions & clean dispute workspace)
"""

from pathlib import Path
from typing import Optional, Generator
import shutil
from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import BASE_DIR

# Database directories & files
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)

DEMO_DB_FILE = DB_DIR / "demo_database.db"
LEGACY_DEMO_DB_FILE = DB_DIR / "app_database.db"
LIVE_DB_FILE = DB_DIR / "live_database.db"

# If demo_database.db doesn't exist but legacy app_database.db does, sync or copy
if not DEMO_DB_FILE.exists() and LEGACY_DEMO_DB_FILE.exists():
    try:
        shutil.copyfile(LEGACY_DEMO_DB_FILE, DEMO_DB_FILE)
    except Exception:
        DEMO_DB_FILE = LEGACY_DEMO_DB_FILE
elif not DEMO_DB_FILE.exists() and not LEGACY_DEMO_DB_FILE.exists():
    DEMO_DB_FILE = DB_DIR / "demo_database.db"

DEMO_DATABASE_URL = f"sqlite:///{DEMO_DB_FILE}"
LIVE_DATABASE_URL = f"sqlite:///{LIVE_DB_FILE}"

# Engine with check_same_thread=False for SQLite in multi-threaded FastAPI env
demo_engine = create_engine(
    DEMO_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

live_engine = create_engine(
    LIVE_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Backward-compatibility alias
engine = demo_engine

DemoSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=demo_engine)
LiveSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=live_engine)

# Backward-compatibility alias
SessionLocal = DemoSessionLocal

Base = declarative_base()

# Active global mode context (DEMO or LIVE)
_ACTIVE_DATABASE_MODE = "DEMO"


def set_active_database_mode(mode: str) -> str:
    """Sets the backend global active database mode ('DEMO' or 'LIVE')."""
    global _ACTIVE_DATABASE_MODE
    normalized = mode.strip().upper()
    if normalized in ("LIVE", "DEMO"):
        _ACTIVE_DATABASE_MODE = normalized
    return _ACTIVE_DATABASE_MODE


def get_active_database_mode() -> str:
    """Gets the backend global active database mode ('DEMO' or 'LIVE')."""
    return _ACTIVE_DATABASE_MODE


def resolve_database_mode(request: Optional[Request] = None, explicit_mode: Optional[str] = None) -> str:
    """
    Deterministically determines the active database mode ('DEMO' or 'LIVE').
    Resolution precedence:
    1. Explicit parameter mode (if passed)
    2. HTTP Header 'X-Database-Mode' or 'x-database-mode'
    3. Query parameter 'mode' or 'db_mode'
    4. Active server mode (_ACTIVE_DATABASE_MODE, default: 'DEMO')
    """
    if explicit_mode:
        mode = explicit_mode.strip().upper()
        if mode in ("LIVE", "DEMO"):
            return mode

    if request:
        # Check HTTP headers
        header_mode = request.headers.get("X-Database-Mode") or request.headers.get("x-database-mode")
        if header_mode and header_mode.strip().upper() in ("LIVE", "DEMO"):
            return header_mode.strip().upper()

        # Check Query Parameters
        query_mode = request.query_params.get("mode") or request.query_params.get("db_mode")
        if query_mode and query_mode.strip().upper() in ("LIVE", "DEMO"):
            return query_mode.strip().upper()

    return get_active_database_mode()


def get_db_session(mode: str = "DEMO") -> Session:
    """Creates a new database session for the specified mode ('DEMO' or 'LIVE')."""
    normalized = mode.strip().upper()
    if normalized == "LIVE":
        return LiveSessionLocal()
    return DemoSessionLocal()


def get_db(request: Request = None) -> Generator[Session, None, None]:
    """
    FastAPI Dependency for database session injection.
    Automatically routes to Demo DB or Live DB based on request headers / query params / server mode.
    """
    mode = resolve_database_mode(request)
    session_factory = LiveSessionLocal if mode == "LIVE" else DemoSessionLocal
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def _run_migrations(target_engine):
    """Executes backward-compatible SQLite table & column additions for database files."""
    try:
        with target_engine.connect() as conn:
            # Disputes migrations
            res = conn.execute(text("PRAGMA table_info(disputes)")).fetchall()
            cols = {row[1] for row in res}
            if cols:
                if "phase" not in cols:
                    conn.execute(text("ALTER TABLE disputes ADD COLUMN phase VARCHAR DEFAULT 'chargeback'"))
                if "respond_by" not in cols:
                    conn.execute(text("ALTER TABLE disputes ADD COLUMN respond_by VARCHAR"))
                if "workflow_stage" not in cols:
                    conn.execute(text("ALTER TABLE disputes ADD COLUMN workflow_stage VARCHAR DEFAULT 'DISPUTE_RAISED'"))
                if "case_source" not in cols:
                    conn.execute(text("ALTER TABLE disputes ADD COLUMN case_source VARCHAR DEFAULT 'SIMULATED_RAZORPAY'"))
                if "merchant_attention_state" not in cols:
                    conn.execute(text("ALTER TABLE disputes ADD COLUMN merchant_attention_state VARCHAR DEFAULT 'ACTION_REQUIRED'"))
                if "ai_last_checked" not in cols:
                    conn.execute(text("ALTER TABLE disputes ADD COLUMN ai_last_checked VARCHAR"))

            # Dispute events migrations
            res_evt = conn.execute(text("PRAGMA table_info(dispute_events)")).fetchall()
            cols_evt = {row[1] for row in res_evt}
            if cols_evt:
                if "actor_type" not in cols_evt:
                    conn.execute(text("ALTER TABLE dispute_events ADD COLUMN actor_type VARCHAR DEFAULT 'SYSTEM'"))
                if "previous_stage" not in cols_evt:
                    conn.execute(text("ALTER TABLE dispute_events ADD COLUMN previous_stage VARCHAR"))
                if "new_stage" not in cols_evt:
                    conn.execute(text("ALTER TABLE dispute_events ADD COLUMN new_stage VARCHAR"))
                if "metadata_json" not in cols_evt:
                    conn.execute(text("ALTER TABLE dispute_events ADD COLUMN metadata_json TEXT DEFAULT '{}'"))

            # Evidence migrations
            res_evd = conn.execute(text("PRAGMA table_info(evidence)")).fetchall()
            cols_evd = {row[1] for row in res_evd}
            if cols_evd:
                if "approval_status" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN approval_status VARCHAR DEFAULT 'PENDING_APPROVAL'"))
                if "approved_at" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN approved_at VARCHAR"))
                if "approved_by" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN approved_by VARCHAR"))
                if "source_reference_id" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN source_reference_id VARCHAR"))
                if "file_path" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN file_path VARCHAR"))
                if "mime_type" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN mime_type VARCHAR"))
                if "file_size" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN file_size INTEGER DEFAULT 0"))
                if "document_hash" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN document_hash VARCHAR"))
                if "content_hash" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN content_hash VARCHAR"))
                if "raw_content" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN raw_content TEXT"))
                if "extracted_text" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN extracted_text TEXT"))
                if "content_json" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN content_json TEXT DEFAULT '{}'"))
                if "key_entities_json" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN key_entities_json TEXT DEFAULT '{}'"))
                if "verification_confidence" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN verification_confidence FLOAT DEFAULT 1.0"))
                if "verification_errors_json" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN verification_errors_json TEXT DEFAULT '[]'"))
                if "ai_analysis_json" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN ai_analysis_json TEXT DEFAULT '{}'"))
                if "ai_analysis_status" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN ai_analysis_status VARCHAR DEFAULT 'PENDING'"))
                if "ai_analyzed_at" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN ai_analyzed_at VARCHAR"))
                if "ai_error" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN ai_error TEXT"))
                if "updated_at" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN updated_at VARCHAR"))
                if "is_deleted" not in cols_evd:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN is_deleted INTEGER DEFAULT 0"))

            # Database performance indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_status ON disputes (status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_workflow_stage ON disputes (workflow_stage)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_case_source ON disputes (case_source)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_created_at ON disputes (created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_respond_by ON disputes (respond_by)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_merchant_attention_state ON disputes (merchant_attention_state)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_disputes_customer_id ON disputes (customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_dispute_id ON evidence (dispute_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_transaction_id ON evidence (transaction_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_verification_status ON evidence (verification_status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_approval_status ON evidence (approval_status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_is_deleted ON evidence (is_deleted)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_created_at ON evidence (created_at)"))

            # Webhook Events table creation if missing
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id VARCHAR PRIMARY KEY,
                    idempotency_key VARCHAR,
                    event_type VARCHAR NOT NULL DEFAULT 'payment.dispute.created',
                    payload_json TEXT DEFAULT '{}',
                    status VARCHAR DEFAULT 'RECEIVED',
                    dispute_id VARCHAR,
                    created_at VARCHAR,
                    processed_at VARCHAR
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_webhook_events_idempotency_key ON webhook_events (idempotency_key)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_webhook_events_event_id ON webhook_events (event_id)"))

            # Dispute Assessments table creation if missing
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dispute_assessments (
                    assessment_id VARCHAR PRIMARY KEY,
                    dispute_id VARCHAR NOT NULL,
                    analysis_version INTEGER DEFAULT 1,
                    trigger VARCHAR DEFAULT 'DISPUTE_CREATED',
                    risk_score FLOAT DEFAULT 0.0,
                    fraud_probability FLOAT DEFAULT 0.0,
                    win_probability FLOAT DEFAULT 0.5,
                    confidence FLOAT DEFAULT 0.5,
                    confidence_level VARCHAR DEFAULT 'MEDIUM',
                    ml_recommendation VARCHAR DEFAULT 'REVIEW',
                    ai_recommendation VARCHAR DEFAULT 'REVIEW',
                    conflict_detected INTEGER DEFAULT 0,
                    ml_results_json TEXT DEFAULT '{}',
                    deepseek_results_json TEXT DEFAULT '{}',
                    evidence_analysis_json TEXT DEFAULT '{}',
                    model_versions_json TEXT DEFAULT '{}',
                    generated_at VARCHAR,
                    FOREIGN KEY(dispute_id) REFERENCES disputes(dispute_id)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_dispute_assessments_dispute_id ON dispute_assessments (dispute_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_dispute_assessments_assessment_id ON dispute_assessments (assessment_id)"))

            conn.commit()
    except Exception:
        pass


def init_db(custom_engine=None, seed: bool = True):
    """
    Initializes both DEMO and LIVE database tables and populates baseline records.
    DEMO DB receives demo scenarios.
    LIVE DB receives clean live transactions with ZERO initial disputes.
    """
    if custom_engine is not None:
        Base.metadata.create_all(bind=custom_engine)
        _run_migrations(custom_engine)
        if seed:
            from src.database.seed import seed_database_if_empty
            session_factory = sessionmaker(bind=custom_engine)
            db = session_factory()
            try:
                seed_database_if_empty(db)
            finally:
                db.close()
        return

    # 1. Initialize DEMO Database
    Base.metadata.create_all(bind=demo_engine)
    _run_migrations(demo_engine)
    if seed:
        from src.database.seed import seed_database_if_empty
        db_demo = DemoSessionLocal()
        try:
            seed_database_if_empty(db_demo)
        finally:
            db_demo.close()

    # 2. Initialize LIVE Database
    Base.metadata.create_all(bind=live_engine)
    _run_migrations(live_engine)
    if seed:
        from src.database.live_seed import seed_live_database_if_empty
        db_live = LiveSessionLocal()
        try:
            seed_live_database_if_empty(db_live)
        finally:
            db_live.close()


def reset_live_database():
    """
    Developer-only helper: Resets Live DB to initial clean state.
    Clears all simulated disputes, evidence, events, and packages,
    and reseeds the 15 clean live transactions.
    Leaves DEMO DB 100% untouched.
    """
    from src.database.live_seed import reset_live_database_seed
    db = LiveSessionLocal()
    try:
        reset_live_database_seed(db)
    finally:
        db.close()

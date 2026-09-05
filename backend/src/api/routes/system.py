"""
System & Mode Management API Endpoints.
Provides database mode inspection and developer-only Live DB reset capabilities.
"""

from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.orm import Session
from src.database.database import get_db, resolve_database_mode, reset_live_database, DEMO_DB_FILE, LIVE_DB_FILE
from src.database.repository import get_all_transactions, get_all_disputes

router = APIRouter(prefix="/system", tags=["System & Mode"])


@router.get("/mode", status_code=status.HTTP_200_OK)
def get_system_mode_endpoint(request: Request, db: Session = Depends(get_db)):
    """
    Returns current active database mode and summary statistics.
    Mode is resolved from 'X-Database-Mode' header or 'mode' query param (defaults to DEMO).
    """
    mode = resolve_database_mode(request)
    total_txns = len(get_all_transactions(db))
    total_disputes = len(get_all_disputes(db))

    return {
        "active_mode": mode,
        "database_file": str(LIVE_DB_FILE.name if mode == "LIVE" else DEMO_DB_FILE.name),
        "total_transactions": total_txns,
        "total_disputes": total_disputes,
        "isolation_guarantee": "STRICT_ISOLATION",
        "description": f"Currently operating on {mode} SQLite database. Zero cross-database fallback."
    }


@router.post("/reset-live", status_code=status.HTTP_200_OK)
def reset_live_database_endpoint(request: Request):
    """
    Developer-Only Reset Mechanism:
    Clears all simulated disputes, evidence, events, and packages in Live DB,
    and restores the initial 15 clean Live transactions with 0 disputes.
    DEMO DB is preserved 100% untouched.
    """
    try:
        reset_live_database()
        return {
            "success": True,
            "message": "Live database successfully reset to 15 clean transactions with 0 disputes.",
            "demo_database_preserved": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset Live database: {str(e)}"
        )

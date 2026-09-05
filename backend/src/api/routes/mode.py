"""
Database Mode Management Router.
Provides GET /mode and POST /mode endpoints to inspect and switch the backend database context (DEMO / LIVE).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import (
    get_db, resolve_database_mode, set_active_database_mode, get_active_database_mode,
    get_db_session, DEMO_DB_FILE, LIVE_DB_FILE
)
from src.database.repository import get_all_transactions, get_all_disputes

router = APIRouter(prefix="", tags=["Database Mode"])


class SetModeRequest(BaseModel):
    mode: str = Field(..., description="Target database mode: 'DEMO' or 'LIVE'")


@router.get("/mode", status_code=status.HTTP_200_OK)
def get_mode_endpoint(request: Request, db: Session = Depends(get_db)):
    """
    Returns current active database mode and summary statistics.
    Mode resolution checks explicit param, X-Database-Mode header, query param, or server active mode.
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
        "description": f"Currently operating on {mode} SQLite database."
    }


@router.post("/mode", status_code=status.HTTP_200_OK)
def set_mode_endpoint(payload: SetModeRequest):
    """
    Changes the backend global active database mode ('DEMO' or 'LIVE').
    Subsequent API calls without explicit headers will operate against this database.
    """
    target = payload.mode.strip().upper()
    if target not in ("LIVE", "DEMO"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'DEMO' or 'LIVE'."
        )

    active = set_active_database_mode(target)
    db = get_db_session(active)
    try:
        total_txns = len(get_all_transactions(db))
        total_disputes = len(get_all_disputes(db))
    finally:
        db.close()

    return {
        "success": True,
        "active_mode": active,
        "database_file": str(LIVE_DB_FILE.name if active == "LIVE" else DEMO_DB_FILE.name),
        "total_transactions": total_txns,
        "total_disputes": total_disputes,
        "message": f"Backend database mode successfully switched to {active}."
    }

"""
Transaction API Endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.repository import (
    create_transaction, get_transaction, get_all_transactions,
    get_eligible_transactions, get_all_disputes
)
from src.schemas.api_schemas import TransactionCreateSchema, TransactionResponseSchema

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionResponseSchema], status_code=status.HTTP_200_OK)
def list_transactions_endpoint(db: Session = Depends(get_db)):
    """Retrieves all transaction records from the active database."""
    return get_all_transactions(db)

@router.get("/eligible", response_model=List[TransactionResponseSchema], status_code=status.HTTP_200_OK)
def list_eligible_transactions_endpoint(db: Session = Depends(get_db)):
    """Retrieves only dispute-eligible transactions (SUCCESS status with no active dispute)."""
    return get_eligible_transactions(db)

@router.get("/disputed", status_code=status.HTTP_200_OK)
def list_disputed_transactions_endpoint(db: Session = Depends(get_db)):
    """Retrieves transactions that currently have active or resolved disputes."""
    disputes = get_all_disputes(db)
    disputed_txn_map = {}
    for d in disputes:
        tx = d.transaction
        if tx:
            disputed_txn_map[tx.transaction_id] = {
                "transaction_id": tx.transaction_id,
                "amount": tx.amount,
                "currency": tx.currency,
                "customer_id": tx.customer_id,
                "dispute_id": d.dispute_id,
                "dispute_status": d.status,
                "workflow_stage": d.workflow_stage,
                "reason_code": d.reason_code,
                "created_at": d.created_at
            }
    return list(disputed_txn_map.values())

@router.post("", response_model=TransactionResponseSchema, status_code=status.HTTP_201_CREATED)
def create_transaction_endpoint(payload: TransactionCreateSchema, db: Session = Depends(get_db)):
    """Creates a new transaction record in the active database."""
    try:
        data_dict = payload.model_dump()
        tx = create_transaction(db, data_dict)
        return tx
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create transaction: {str(e)}"
        )

@router.get("/{transaction_id}", response_model=TransactionResponseSchema, status_code=status.HTTP_200_OK)
def get_transaction_endpoint(transaction_id: str, db: Session = Depends(get_db)):
    """Retrieves a transaction by ID from the active database."""
    tx = get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found."
        )
    return tx

"""
Transaction API Endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.repository import create_transaction, get_transaction, get_all_transactions
from src.schemas.api_schemas import TransactionCreateSchema, TransactionResponseSchema

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionResponseSchema], status_code=status.HTTP_200_OK)
def list_transactions_endpoint(db: Session = Depends(get_db)):
    """Retrieves all transaction records from database."""
    return get_all_transactions(db)

@router.post("", response_model=TransactionResponseSchema, status_code=status.HTTP_201_CREATED)
def create_transaction_endpoint(payload: TransactionCreateSchema, db: Session = Depends(get_db)):
    """Creates a new transaction record in the application database."""
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
    """Retrieves a transaction by ID."""
    tx = get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found."
        )
    return tx

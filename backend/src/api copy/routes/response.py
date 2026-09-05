"""
AI Response Generator API Endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.response.service import ResponseGeneratorService
from src.response.schemas import AIResponseSchema

router = APIRouter(prefix="/disputes", tags=["AI Response Generator"])

response_service = ResponseGeneratorService()

@router.post("/{dispute_id}/generate-response", response_model=AIResponseSchema, status_code=status.HTTP_200_OK)
def generate_ai_response_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Executes AI Response Generator for a dispute case.
    Uses verified evidence facts, enforces post-LLM claim validation, and returns structured response.
    """
    try:
        response = response_service.generate_response_for_dispute(db, dispute_id)
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI response: {str(e)}"
        )

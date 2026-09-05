"""
Chargeback Package Generator API Endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.chargeback.service import ChargebackPackageService
from src.chargeback.schemas import ChargebackPackageSchema

router = APIRouter(prefix="/disputes", tags=["Chargeback Package Generator"])

package_service = ChargebackPackageService()

@router.post("/{dispute_id}/generate-package", response_model=ChargebackPackageSchema, status_code=status.HTTP_200_OK)
def generate_chargeback_package_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Executes Chargeback Package Generator for a dispute case.
    Combines dispute info, risk assessment, verified evidence summary, AI response,
    and evidence traceability. Persists package to database and returns complete JSON.
    """
    try:
        package = package_service.generate_and_save_package(db, dispute_id)
        return package
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate chargeback package."
        )

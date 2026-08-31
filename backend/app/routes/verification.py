from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import VerifyRequest, VerifyResponse
from backend.app.services.participant_service import check_eligibility

router = APIRouter(prefix="/api", tags=["Verification"])


@router.post("/verify", response_model=VerifyResponse)
def verify_email_eligibility(payload: VerifyRequest, db: Session = Depends(get_db)):
    """
    Checks if an email is authorized.
    Does NOT leak internal participant data, names, IDs, or full list.
    """
    is_eligible, participant = check_eligibility(db, payload.email)
    
    if is_eligible and participant:
        return VerifyResponse(
            eligible=True,
            message="Email eligibility verified"
        )
    
    return VerifyResponse(
        eligible=False,
        message="This email address is not eligible for a certificate."
    )

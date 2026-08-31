import re
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.schemas import GenerateCertificateRequest
from backend.app.services.participant_service import claim_certificate_generation, release_certificate_claim
from backend.app.services.certificate_service import generate_certificate_pdf, CertificateGenerationError

router = APIRouter(prefix="/api/certificates", tags=["Certificates"])
settings = get_settings()


def safe_download_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")
    return cleaned or "participant"


@router.post("/generate")
def generate_certificate(
    payload: GenerateCertificateRequest,
    db: Session = Depends(get_db)
):
    """
    Atomically verifies participant eligibility and generates personalized certificate PDF.
    Guarantees that race conditions cannot generate duplicate certificates.
    """
    # 1. Atomic claim check
    is_claimed, participant, reason = claim_certificate_generation(
        db=db,
        email=payload.email,
        allow_regeneration=settings.ALLOW_CERTIFICATE_REGENERATION
    )

    if reason == "NOT_ELIGIBLE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This email address is not eligible for a certificate."
        )

    if reason == "ALREADY_GENERATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A certificate has already been generated for this email address."
        )

    # 2. Generate PDF
    try:
        pdf_bytes = generate_certificate_pdf(participant_name=payload.name)
    except CertificateGenerationError:
        # Revert claim if generation failed
        if participant:
            release_certificate_claim(db, participant)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong while generating your certificate. Please contact the workshop host."
        )
    except Exception:
        if participant:
            release_certificate_claim(db, participant)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong while generating your certificate. Please try again."
        )

    # 3. Return downloadable PDF
    filename = f"Certificate_{safe_download_filename(payload.name)}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

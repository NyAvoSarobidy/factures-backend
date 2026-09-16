"""
Router FastAPI — /extract

Endpoints :
  POST /extract — reçoit un term sheet PDF, retourne le JSON structuré
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

from app.services.pdf_extractor import extract_term_sheet

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/extract",
    tags=["extract"],
)


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Extrait les données d'un term sheet PDF",
)
async def extract_pdf(file: UploadFile = File(...)):
    """Reçoit un term sheet PDF et retourne un JSON structuré.

    Le JSON retourné contient :
    - Les champs extractibles : product_name, isin, issuer, currency, upfront_fee_rate
    - Les champs NOTIONNEL et COMMISSION sont TOUJOURS vides (à remplir à la main)
    - Un score de confiance et des warnings
    """
    return await _do_extract(file)


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Extrait les données d'un term sheet PDF",
    include_in_schema=False,
)
async def extract_pdf_no_slash(file: UploadFile = File(...)):
    """Route sans le slash final (redirection)."""
    return await _do_extract(file)


async def _do_extract(file: UploadFile):
    """Logique d'extraction commune."""
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers PDF sont acceptés",
        )

    content = await file.read()
    if len(content) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier PDF vide ou corrompu",
        )

    try:
        result = extract_term_sheet(content)
        return result
    except Exception as e:
        logger.error("Erreur extraction : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'extraction : {str(e)}",
        )

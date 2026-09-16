"""
Dependencies FastAPI — protection par clé API interne.
"""

from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_internal_api_key(x_api_key: str | None = Header(None)) -> None:
    """Vérifie la clé API interne pour accéder aux endpoints confidentiels.

    Cette protection est requise pour les endpoints qui renvoient des données
    internes confidentielles (total_fees, calculation_detail) :
    - GET /preconfirmation/{id}/detail
    - GET /preconfirmations/ (listing)
    - GET /preconfirmations/compare

    Les endpoints publics (/health, POST /commission/calculate, POST /generate, etc.)
    ne sont PAS concernés.
    """
    if settings.INTERNAL_API_KEY and x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API interne invalide ou manquante",
        )

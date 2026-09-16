"""
Router FastAPI — /commission

Endpoints :
  POST /commission/calculate — calcule et retourne les commissions (sans frais)
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.commission import DealInput
from app.schemas.api_response import DealPublic
from app.services.commission_service import calculate_commission_response

router = APIRouter(
    prefix="/commission",
    tags=["commission"],
)


@router.post(
    "/calculate",
    response_model=DealPublic,
    status_code=status.HTTP_200_OK,
    summary="Calcule les commissions d'un deal",
    description=(
        "Calcule les commissions pour un ou plusieurs produits. "
        "Le notionnel et les termes de commission sont toujours "
        "fournis manuellement (jamais depuis le term sheet)."
    ),
)
async def calculate_commission(deal: DealInput) -> DealPublic:
    """Endpoint principal du moteur de commission."""
    try:
        result = calculate_commission_response(deal)
        return result.public
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de calcul : {str(e)}",
        )

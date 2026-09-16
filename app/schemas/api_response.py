"""
Schemas de reponse API — lisses pour l'exposition.

Ces schemas volontairement n'incluent PAS :
  - total_fees (confidentiel)
  - calculation_detail (contient des montants intermediaires confidentiels)
  - ce que l'entreprise garde (confidentiel)

Ils ne contiennent que ce qui peut legitimement sortir vers
la contrepartie.
"""

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.commission import CommissionType


class CommissionTermPublic(BaseModel):
    """Resultat de commission expose vers la contrepartie."""

    introducer_id: str
    commission_type: CommissionType
    commission_value: Decimal
    commission_currency: str
    calculated_amount: Decimal
    # PAS de calculation_detail ici — il contient des montants intermediaires
    # confidentiels (ex: total des frais). Il reste dans le snapshot DB
    # pour l'audit interne uniquement.


class ProductPublic(BaseModel):
    """Produit expose — sans total_fees."""

    product_name: str
    notional: Decimal
    currency: str
    upfront_fee_rate: Decimal
    commissions: List[CommissionTermPublic]


class DealPublic(BaseModel):
    """Reponse API finale — rien de confidentiel."""

    deal_reference: Optional[str]
    products: List[ProductPublic]
    total_commissions: Decimal
    confidentiality_notice: str = Field(
        default=(
            "Ce document ne divulgue pas le montant total des frais "
            "percus par l'emetteur."
        )
    )

"""
Service de calcul de commission — point d'entree unique.

Il orchestre :
  1. La validation des donnees entrantes (schemas Pydantic)
  2. Le calcul (moteur pur)
  3. Le mapping vers la reponse publique (confidentialite)
  4. Le snapshot complet pour l'audit interne
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.schemas.commission import DealInput
from app.schemas.api_response import (
    CommissionTermPublic,
    DealPublic,
    ProductPublic,
)
from app.services.commission_engine import calculate_deal, calculate_product


@dataclass
class DealCalculationResult:
    """Resultat complet d'un calcul.

    public : reponse API — sans donnees confidentielles
    snapshot : donnees completes pour l'audit interne (contient
               calculation_detail, total_fees, etc.)
    """
    public: DealPublic
    snapshot: dict


def calculate_commission_response(deal_input: DealInput) -> DealCalculationResult:
    """Calcule les commissions et retourne un resultat sur pour l'API.

    Le moteur interne produit des resultats incluant total_fees
    et calculation_detail. Cette fonction mappe vers le schema
    public qui exclut les informations confidentielles, et
    conserve les donnees completes dans le snapshot.
    """
    result = calculate_deal(deal_input)

    products_public = []
    snapshot_products = []
    for p in result.products:
        commissions_public = []
        snapshot_commissions = []
        for c in p.commission_results:
            commissions_public.append(
                CommissionTermPublic(
                    introducer_id=c.introducer_id,
                    commission_type=c.commission_type,
                    commission_value=c.commission_value,
                    commission_currency=c.commission_currency,
                    calculated_amount=c.calculated_amount,
                    # PAS de calculation_detail ici — confidentiel
                )
            )
            snapshot_commissions.append({
                "introducer_id": c.introducer_id,
                "type": c.commission_type.value,
                "value": str(c.commission_value),
                "currency": c.commission_currency,
                "calculated": str(c.calculated_amount),
                "detail": c.calculation_detail,  # detail complet pour audit
            })
        products_public.append(
            ProductPublic(
                product_name=p.product_name,
                notional=p.notional,
                currency=p.currency,
                upfront_fee_rate=p.upfront_fee_rate,
                commissions=commissions_public,
            )
        )
        snapshot_products.append({
            "name": p.product_name,
            "notional": str(p.notional),
            "currency": p.currency,
            "upfront_fee_rate": str(p.upfront_fee_rate),
            "total_fees": str(p.total_fees),  # confidentiel, pour audit interne
            "commissions": snapshot_commissions,
        })

    public = DealPublic(
        deal_reference=result.deal_reference,
        products=products_public,
        total_commissions=result.total_commissions,
    )

    snapshot = {
        "deal_reference": result.deal_reference,
        "products": snapshot_products,
        "total_commissions": str(result.total_commissions),
        "total_fees_global": str(sum(
            p.total_fees for p in result.products
        )),  # confidentiel, audit uniquement
    }

    return DealCalculationResult(public=public, snapshot=snapshot)

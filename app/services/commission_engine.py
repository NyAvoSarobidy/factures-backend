"""
Moteur de calcul de commission.

Principes :
- Decimal uniquement (jamais de float) — precision comptable
- Arrondi bancaire (ROUND_HALF_EVEN) a 2 decimales — norme comptable
- Aucun effet de bord — le moteur ne fait que calculer
- Chaque calcul est tracable via calculation_detail

Regle d'arrondi (decision non specifiee par le brief) :
  ROUND_HALF_EVEN, 2 decimales. C'est le comportement par defaut de
  Decimal.quantize(), et c'est la norme comptable (IEEE 754 / IEEE 850).
  Exemple : 15000.005 -> 15000.00 (pas de biais systematique vers le haut)
"""

from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from typing import List

from app.schemas.commission import (
    CommissionResult,
    CommissionTermInput,
    CommissionType,
    ProductInput,
    ProductResult,
    DealInput,
    DealResult,
)

# Precision interne : 28 chiffres (defaut Decimal). Suffisant pour
# des montants jusqu'a 10^21 avec 2 decimales.
getcontext().prec = 28

# Constantes
TWO_PLACES = Decimal("0.01")
BASIS_POINT = Decimal("0.0001")  # 1 bp = 0.01% = 0.0001
PERCENT = Decimal("0.01")  # 1% = 0.01


def _round(value: Decimal) -> Decimal:
    """Arrondi bancaire a 2 decimales."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)


def calculate_flat(term: CommissionTermInput) -> CommissionResult:
    """Commission montant fixe — la valeur EST le montant."""
    amount = _round(term.commission_value)
    return CommissionResult(
        introducer_id=term.introducer_id,
        commission_type=term.commission_type,
        commission_value=term.commission_value,
        commission_currency=term.commission_currency,
        calculated_amount=amount,
        calculation_detail=f"flat: {term.commission_value} {term.commission_currency}",
    )


def calculate_fee_share(
    term: CommissionTermInput, total_fees: Decimal
) -> CommissionResult:
    """Commission = fraction des frais totaux du produit.

    Utilise la fraction exacte (fraction_numerateur/denominateur) si disponible,
    sinon la fraction décimale (commission_value).
    """
    fraction = term.get_fraction_value()
    raw = fraction * total_fees
    amount = _round(raw)
    percentage = fraction * Decimal("100")
    
    if term.fraction_numerateur is not None and term.fraction_denominateur is not None:
        fraction_str = f"{term.fraction_numerateur}/{term.fraction_denominateur}"
    else:
        fraction_str = f"{fraction}"
    
    return CommissionResult(
        introducer_id=term.introducer_id,
        commission_type=term.commission_type,
        commission_value=term.commission_value,
        commission_currency=term.commission_currency,
        calculated_amount=amount,
        calculation_detail=(
            f"fee_share: {fraction_str} ({percentage}%) de {total_fees} = {raw} -> {amount}"
        ),
    )


def calculate_bps_notional(
    term: CommissionTermInput, notional: Decimal
) -> CommissionResult:
    """Commission = points de base du notionnel.

    commission_value est en points de base (bps) :
      50 bps = 0.50% du notionnel
      120 bps = 1.20% du notionnel

    Formule : notional * bps * 0.0001
    """
    raw = notional * term.commission_value * BASIS_POINT
    amount = _round(raw)
    percentage = term.commission_value * BASIS_POINT * Decimal("100")
    return CommissionResult(
        introducer_id=term.introducer_id,
        commission_type=term.commission_type,
        commission_value=term.commission_value,
        commission_currency=term.commission_currency,
        calculated_amount=amount,
        calculation_detail=(
            f"bps_notional: {term.commission_value} bps ({percentage}%) "
            f"de {notional} = {raw} -> {amount}"
        ),
    )


# Dispatcher
CALCULATORS = {
    CommissionType.FLAT: calculate_flat,
    CommissionType.FEE_SHARE: calculate_fee_share,
    CommissionType.BPS_NOTIONAL: calculate_bps_notional,
}


def calculate_product(product: ProductInput) -> ProductResult:
    """Calcule les commissions d'un produit.

    Le total des frais est calcule mais n'est PAS expose dans le resultat
    API final (confidentialite). Il sert uniquement de base aux calculs
    internes (fee_share).
    """
    # Total des frais — confidentiel, ne sort jamais de l'API
    total_fees = _round(product.notional * product.upfront_fee_rate * PERCENT)

    commission_results: List[CommissionResult] = []
    for term in product.commission_terms:
        if term.commission_type == CommissionType.FLAT:
            result = calculate_flat(term)
        elif term.commission_type == CommissionType.FEE_SHARE:
            result = calculate_fee_share(term, total_fees)
        elif term.commission_type == CommissionType.BPS_NOTIONAL:
            result = calculate_bps_notional(term, product.notional)
        else:
            raise ValueError(f"Type de commission non supporte: {term.commission_type}")
        commission_results.append(result)

    return ProductResult(
        product_name=product.product_name,
        notional=product.notional,
        currency=product.currency,
        upfront_fee_rate=product.upfront_fee_rate,
        total_fees=total_fees,
        commission_results=commission_results,
    )


def calculate_deal(deal: DealInput) -> DealResult:
    """Calcule les commissions d'un deal complet (un ou plusieurs produits)."""
    product_results = [calculate_product(p) for p in deal.products]

    total = sum(
        (r.calculated_amount for p in product_results for r in p.commission_results),
        Decimal("0"),
    )

    return DealResult(
        deal_reference=deal.deal_reference,
        products=product_results,
        total_commissions=_round(total),
    )

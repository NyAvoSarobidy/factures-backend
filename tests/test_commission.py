"""
Les 5 cas de test du brief — reference absolue.

Aucune modification du moteur ne doit regresser dessus.
"""

from decimal import Decimal

import pytest

from app.schemas.commission import (
    CommissionTermInput,
    CommissionType,
    DealInput,
    ProductInput,
)
from app.services.commission_engine import calculate_deal, calculate_product


def make_product(
    name: str,
    notional: str,
    fee_rate: str,
    commission_type: CommissionType,
    commission_value: str = "0",
    currency: str = "EUR",
    introducer: str = "intro-1",
    fraction_numerateur: int = None,
    fraction_denominateur: int = None,
) -> ProductInput:
    return ProductInput(
        product_name=name,
        notional=Decimal(notional),
        upfront_fee_rate=Decimal(fee_rate),
        currency=currency,
        commission_terms=[
            CommissionTermInput(
                introducer_id=introducer,
                commission_type=commission_type,
                commission_value=Decimal(commission_value),
                commission_currency=currency,
                fraction_numerateur=fraction_numerateur,
                fraction_denominateur=fraction_denominateur,
            )
        ],
    )


# =============================================================
# Cas A : 1 000 000 EUR | 1.50% | 50 bps du notionnel
# Attendu : 1 000 000 * 50 * 0.0001 = 5 000 EUR
# =============================================================
def test_case_a_bps_notional():
    product = make_product("A", "1000000", "1.50", CommissionType.BPS_NOTIONAL, "50")
    result = calculate_product(product)
    assert len(result.commission_results) == 1
    r = result.commission_results[0]
    assert r.calculated_amount == Decimal("5000.00")
    assert r.commission_type == CommissionType.BPS_NOTIONAL


# =============================================================
# Cas B : 1 000 000 EUR | 1.50% | un tiers des frais totaux
# Attendu : frais = 1 000 000 * 1.50% = 15 000 ; 1/3 = 5 000 EUR
# =============================================================
def test_case_b_fee_share_exact():
    """Cas B avec fraction exacte 1/3 — doit donner 5000.00 exactement."""
    product = make_product(
        "B", "1000000", "1.50", CommissionType.FEE_SHARE,
        fraction_numerateur=1, fraction_denominateur=3
    )
    result = calculate_product(product)
    r = result.commission_results[0]
    assert r.calculated_amount == Decimal("5000.00")


def test_case_b_fee_share_decimal():
    """Cas B avec fraction decimale 0.3333 — donne 4999.50 (comportement attendu)."""
    product = make_product("B-dec", "1000000", "1.50", CommissionType.FEE_SHARE, "0.3333")
    result = calculate_product(product)
    r = result.commission_results[0]
    assert r.calculated_amount == Decimal("4999.50")


# =============================================================
# Cas C : 2 500 000 USD | 1.20% | flat 5 000 EUR
# Attendu : 5 000 EUR (montant fixe, independant du notionnel/frais)
# =============================================================
def test_case_c_flat():
    product = make_product("C", "2500000", "1.20", CommissionType.FLAT, "5000", currency="USD")
    result = calculate_product(product)
    r = result.commission_results[0]
    assert r.calculated_amount == Decimal("5000.00")
    assert r.commission_currency == "USD"


# =============================================================
# Cas D : 750 000 EUR | 0.85% | 40% des frais totaux
# Attendu : frais = 750 000 * 0.85% = 6 375 ; 40% = 2 550 EUR
# =============================================================
def test_case_d_fee_share():
    product = make_product("D", "750000", "0.85", CommissionType.FEE_SHARE, "0.40")
    result = calculate_product(product)
    r = result.commission_results[0]
    assert r.calculated_amount == Decimal("2550.00")


# =============================================================
# Cas E : 500 000 EUR | 0.60% | 120 bps du notionnel
# Attendu : 500 000 * 120 * 0.0001 = 6 000 EUR
# =============================================================
def test_case_e_bps_notional():
    product = make_product("E", "500000", "0.60", CommissionType.BPS_NOTIONAL, "120")
    result = calculate_product(product)
    r = result.commission_results[0]
    assert r.calculated_amount == Decimal("6000.00")


# =============================================================
# Test multi-produits : un deal avec les 5 produits (fractions exactes)
# =============================================================
def test_deal_multi_product():
    deal = DealInput(
        deal_reference="TEST-ALL-5",
        products=[
            make_product("A", "1000000", "1.50", CommissionType.BPS_NOTIONAL, "50"),
            make_product("B", "1000000", "1.50", CommissionType.FEE_SHARE, fraction_numerateur=1, fraction_denominateur=3),
            make_product("C", "2500000", "1.20", CommissionType.FLAT, "5000", currency="USD"),
            make_product("D", "750000", "0.85", CommissionType.FEE_SHARE, "0.40"),
            make_product("E", "500000", "0.60", CommissionType.BPS_NOTIONAL, "120"),
        ],
    )
    result = calculate_deal(deal)
    amounts = [r.calculated_amount for p in result.products for r in p.commission_results]
    assert amounts == [
        Decimal("5000.00"),   # A
        Decimal("5000.00"),   # B (1/3 exact)
        Decimal("5000.00"),   # C
        Decimal("2550.00"),   # D
        Decimal("6000.00"),   # E
    ]
    assert result.total_commissions == Decimal("23550.00")


# =============================================================
# Test multi-introducers sur un meme produit
# =============================================================
def test_multi_introducers_same_product():
    """Deux introducers sur un meme produit — chacun sa commission."""
    product = ProductInput(
        product_name="Multi-Intro",
        notional=Decimal("1000000"),
        upfront_fee_rate=Decimal("1.50"),
        currency="EUR",
        commission_terms=[
            CommissionTermInput(
                introducer_id="intro-1",
                commission_type=CommissionType.BPS_NOTIONAL,
                commission_value=Decimal("50"),
                commission_currency="EUR",
            ),
            CommissionTermInput(
                introducer_id="intro-2",
                commission_type=CommissionType.FEE_SHARE,
                commission_value=Decimal("0.25"),
                commission_currency="EUR",
            ),
        ],
    )
    result = calculate_product(product)
    assert len(result.commission_results) == 2
    
    r1 = result.commission_results[0]
    r2 = result.commission_results[1]
    
    # Intro 1 : 50 bps × 1M = 5000
    assert r1.introducer_id == "intro-1"
    assert r1.calculated_amount == Decimal("5000.00")
    
    # Intro 2 : 25% × 15000 = 3750
    assert r2.introducer_id == "intro-2"
    assert r2.calculated_amount == Decimal("3750.00")


# =============================================================
# Test tracabilite : chaque resultat contient la formule
# =============================================================
def test_calculation_detail_present():
    product = make_product("TRACE", "1000000", "1.50", CommissionType.BPS_NOTIONAL, "50")
    result = calculate_product(product)
    r = result.commission_results[0]
    assert "bps" in r.calculation_detail
    assert "50" in r.calculation_detail
    assert "1000000" in r.calculation_detail


# =============================================================
# Test confidentialite : le moteur ne fuit pas de donnees
# =============================================================
def test_no_sensitive_data_in_public_fields():
    """Verifie que les champs sensibles ne sont pas dans les schemas publics."""
    from app.schemas.api_response import DealPublic, ProductPublic, CommissionTermPublic
    
    # Ces schemas ne doivent pas avoir les champs sensibles
    public_fields = set(DealPublic.model_fields.keys())
    assert "total_fees" not in public_fields
    
    product_fields = set(ProductPublic.model_fields.keys())
    assert "total_fees" not in product_fields
    
    commission_fields = set(CommissionTermPublic.model_fields.keys())
    assert "calculation_detail" not in commission_fields

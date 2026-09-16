"""
Schemas Pydantic pour le moteur de commission.

On utilise Decimal pour toute valeur monetaire — jamais de float.
Raison : un float introduit des erreurs de representation binaire invisibles
(ex: 0.1 + 0.2 = 0.30000000000000004). Sur un document qui declenche
un paiement reel, c'est inacceptable.
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CommissionType(str, Enum):
    """Types de commission supportes.

    Le brief en liste 3 ('au minimum') :
      - flat         : montant fixe
      - fee_share    : pourcentage des frais totaux du produit
      - bps_notional : points de base du notionnel

    L'enum est ouvert — on pourra ajouter :
      - tiered_bps   : bareme de bps par tranches de notionnel
      - performance  : commission variable selon performance
    sans casser l'API.
    """

    FLAT = "flat"
    FEE_SHARE = "fee_share"
    BPS_NOTIONAL = "bps_notional"


class CommissionTermInput(BaseModel):
    """Un terme de commission s'applique a un produit pour un introducer.

    Deux champs ne viennent JAMAIS du term sheet :
      - notional (toujours saisi a la main)
      - ce terme de commission (toujours saisi a la main)
    """

    introducer_id: str = Field(
        ...,
        description="Identifiant de l'introducer (ex: 'introducer-uuid')",
    )
    commission_type: CommissionType = Field(
        ...,
        description="Type de commission : flat, fee_share, bps_notional",
    )
    commission_value: Decimal = Field(
        ...,
        description=(
            "Valeur du terme :\n"
            "- flat: montant (ex: 5000.00)\n"
            "- fee_share: fraction decimale (ex: 0.3333 pour un tiers)\n"
            "- bps_notional: nombre de points de base (ex: 50 pour 50 bps)"
        ),
    )
    commission_currency: str = Field(
        default="EUR",
        min_length=3,
        max_length=3,
        description="ISO 4217 — devise dans laquelle la commission est libellee",
    )

    @field_validator("commission_value")
    @classmethod
    def value_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("commission_value doit etre strictement positif")
        return v


class ProductInput(BaseModel):
    """Un produit d'un deal."""

    product_name: str = Field(..., description="Nom ou reference du produit")
    notional: Decimal = Field(
        ...,
        description="Notionnel — TOUJOURS saisi a la main (jamais depuis term sheet)",
    )
    upfront_fee_rate: Decimal = Field(
        ...,
        description="Frais upfront en pourcentage (ex: 1.50 pour 1.50%)",
    )
    currency: str = Field(
        default="EUR",
        min_length=3,
        max_length=3,
        description="Devise du notionnel et des frais",
    )
    commission_terms: List[CommissionTermInput] = Field(
        default_factory=list,
        description="Un ou plusieurs termes de commission (plusieurs introducers possibles)",
    )

    @field_validator("notional")
    @classmethod
    def notional_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Le notionnel doit etre strictement positif")
        return v

    @field_validator("upfront_fee_rate")
    @classmethod
    def rate_must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Le taux de frais doit etre positif ou nul")
        return v


class DealInput(BaseModel):
    """Un deal complet — peut contenir plusieurs produits."""

    deal_reference: Optional[str] = Field(
        None,
        description="Reference libre du deal (ex: 'BNP-2024-001')",
    )
    products: List[ProductInput] = Field(
        ...,
        min_length=1,
        description="Liste des produits (au moins un)",
    )


class CommissionResult(BaseModel):
    """Resultat du calcul pour un terme de commission."""

    introducer_id: str
    commission_type: CommissionType
    commission_value: Decimal
    commission_currency: str
    calculated_amount: Decimal = Field(
        ...,
        description="Montant final de la commission, arrethi a 2 decimales",
    )
    calculation_detail: str = Field(
        ...,
        description="Formule appliquee — pour l'audit et la tracabilite",
    )


class ProductResult(BaseModel):
    """Resultat du calcul pour un produit."""

    product_name: str
    notional: Decimal
    currency: str
    upfront_fee_rate: Decimal
    total_fees: Decimal = Field(
        ...,
        description="Montant total des frais sur le produit (confidentiel)",
    )
    commission_results: List[CommissionResult]


class DealResult(BaseModel):
    """Resultat complet pour un deal."""

    deal_reference: Optional[str]
    products: List[ProductResult]
    total_commissions: Decimal = Field(
        ...,
        description="Somme de toutes les commissions du deal",
    )

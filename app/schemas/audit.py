"""
Schemas pour l'audit / historique des documents.

Ces schemas exposent uniquement les métadonnées nécessaires à l'audit.
Les données confidentielles (total_fees, calculation_detail) restent
dans le snapshot JSONB interne et ne sont jamais exposées via l'API.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class AuditDocumentSummary(BaseModel):
    """Résumé d'un document pour le listing d'audit.

    Contient uniquement les métadonnées nécessaires :
    - Identification (id, deal_reference, version)
    - Statut et dates
    - Liens (pdf_url)
    - Montant total des commissions (pas les frais !)
    """

    id: str
    deal_reference: Optional[str] = None
    version: int
    status: str
    generated_at: datetime
    generated_by: Optional[str] = None
    pdf_url: Optional[str] = None
    total_commissions: Decimal
    product_count: int
    introducer_count: int


class AuditDocumentDetail(BaseModel):
    """Détail complet d'un document pour l'audit.

    Contient le snapshot complet (avec données confidentielles)
    car l'audit interne y a accès. Mais ce n'est exposé que
    via un endpoint protégé (pas dans le listing public).
    """

    id: str
    deal_reference: Optional[str] = None
    version: int
    status: str
    generated_at: datetime
    generated_by: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_path: str
    snapshot: dict


class AuditComparison(BaseModel):
    """Comparaison entre deux versions d'un document."""

    deal_reference: str
    version_a: int
    version_b: int
    changes: List[str]
    total_commissions_a: Decimal
    total_commissions_b: Decimal
    difference: Decimal

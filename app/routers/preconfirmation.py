"""
Router FastAPI — /preconfirmation et /preconfirmations

Endpoints :
  POST /preconfirmation/generate — calcule, génère le PDF, le stocke
  GET /preconfirmation/{id} — récupère un document (résumé audit, sans données confidentielles)
  GET /preconfirmation/{id}/detail — récupère le détail complet (avec snapshot confidentiel)
  GET /preconfirmations — liste les documents (audit / historique)
  GET /preconfirmations/compare?a={id}&b={id} — compare deux versions
"""

import json
import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

logger = logging.getLogger(__name__)

from app.schemas.commission import DealInput
from app.schemas.api_response import DealPublic
from app.services.commission_service import calculate_commission_response
from app.services.pdf_generator import generate_preconfirmation_pdf
from app.services.storage_service import (
    store_pdf,
    list_documents_summary,
    get_document_detail,
    compare_versions,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/preconfirmation",
    tags=["preconfirmation"],
)

audit_router = APIRouter(
    prefix="/preconfirmations",
    tags=["preconfirmation"],
)


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Génère une pré-confirmation de commission en PDF",
)
async def generate_preconfirmation(
    data: str = Form(...),
    logo: Optional[UploadFile] = File(None),
    counterparty_name: Optional[str] = Form(None),
    counterparty_address: Optional[str] = Form(None),
):
    """Calcule les commissions, génère le PDF et le stocke.

    Paramètres (multipart/form-data):
    - data : données du deal en JSON (string)
    - logo : fichier image optionnel (PNG/JPG)
    - counterparty_name : nom de la contrepartie (optionnel)
    - counterparty_address : adresse de la contrepartie (optionnel)
    """
    try:
        deal_data = json.loads(data)
        deal_input = DealInput(**deal_data)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Données invalides: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Données invalides. Vérifiez le format du deal.",
        )

    try:
        calc_result = calculate_commission_response(deal_input)
        deal_public: DealPublic = calc_result.public
    except Exception as e:
        logger.error("Erreur de calcul: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors du calcul. Vérifiez les données saisies.",
        )

    logo_path = None
    if logo and logo.filename:
        suffix = os.path.splitext(logo.filename)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await logo.read()
            tmp.write(content)
            logo_path = tmp.name
        logger.info("Logo reçu : %s", logo.filename)

    try:
        pdf_bytes = generate_preconfirmation_pdf(
            deal_public,
            logo_path=logo_path,
            counterparty_name=counterparty_name,
            counterparty_address=counterparty_address,
        )
    except Exception as e:
        logger.error("Erreur génération PDF : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération du PDF : {str(e)}",
        )
    finally:
        if logo_path:
            try:
                os.unlink(logo_path)
            except Exception:
                pass

    try:
        doc_record = store_pdf(pdf_bytes, deal_public, calc_result.snapshot)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du stockage : {str(e)}",
        )

    return {
        "status": "ok",
        "document_id": doc_record.get("id"),
        "version": doc_record.get("version"),
        "pdf_url": doc_record.get("pdf_url"),
        "deal_reference": deal_input.deal_reference,
        "total_commissions": str(deal_public.total_commissions),
        "generated_at": doc_record.get("generated_at"),
    }


@router.get(
    "/{doc_id}",
    summary="Récupère un document (résumé audit, sans données confidentielles)",
)
async def get_preconfirmation(doc_id: str):
    """Récupère les métadonnées d'un document — sans le snapshot confidentiel."""
    doc = get_document_detail(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )
    snapshot = doc.get("snapshot", {})
    return {
        "id": doc.get("id"),
        "deal_reference": snapshot.get("deal_reference"),
        "version": doc.get("version"),
        "status": doc.get("status"),
        "generated_at": doc.get("generated_at"),
        "generated_by": doc.get("generated_by"),
        "pdf_url": doc.get("pdf_url"),
        "total_commissions": snapshot.get("total_commissions", "0"),
        "product_count": len(snapshot.get("products", [])),
    }


@router.get(
    "/{doc_id}/detail",
    summary="Récupère le détail complet (avec snapshot confidentiel)",
)
async def get_preconfirmation_detail(doc_id: str):
    """Récupère le détail complet avec le snapshot (audit interne uniquement)."""
    doc = get_document_detail(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé",
        )
    return doc


@audit_router.get(
    "/",
    summary="Liste les documents générés (audit / historique)",
)
async def list_preconfirmations(deal_reference: Optional[str] = None, limit: int = 50):
    """Liste les documents avec un résumé audit (sans données confidentielles)."""
    return list_documents_summary(deal_reference=deal_reference, limit=limit)


@audit_router.get(
    "",
    summary="Liste les documents générés (audit / historique)",
    include_in_schema=False,
)
async def list_preconfirmations_no_slash(deal_reference: Optional[str] = None, limit: int = 50):
    """Liste les documents — variante sans slash."""
    return list_documents_summary(deal_reference=deal_reference, limit=limit)


@audit_router.get(
    "/compare",
    summary="Compare deux versions d'un document",
)
async def compare_preconfirmations(doc_id_a: str = Query(...), doc_id_b: str = Query(...)):
    """Compare deux versions et retourne les différences."""
    result = compare_versions(doc_id_a, doc_id_b)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Un ou deux documents non trouvés",
        )
    return result

"""
Service de stockage du PDF dans Supabase Storage et enregistrement en base.

Principes :
- Les PDFs ne sont jamais écrasés — chaque génération crée un nouvel enregistrement
- Un snapshot des chiffres est stocké à côté (pour l'audit)
- Les fichiers sont nommés de manière unique par deal + version
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import db
from app.schemas.api_response import DealPublic

logger = logging.getLogger(__name__)

BUCKET_NAME = "preconfirmations"


def _sanitize_filename(name: str) -> str:
    """Nettoie un nom pour un nom de fichier sûr."""
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
    return "".join(c for c in name if c in keep).rstrip()


def get_next_version(deal_reference: str) -> int:
    """Calcule la prochaine version pour un deal donné."""
    try:
        result = (
            db.client.table("preconfirmation_documents")
            .select("version")
            .contains("snapshot", {"deal_reference": deal_reference})
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0].get("version", 0) + 1
    except Exception:
        pass
    return 1


def store_pdf(
    pdf_bytes: bytes,
    deal: DealPublic,
    snapshot: dict,
    generated_by: Optional[str] = None,
) -> dict:
    """Stocke le PDF et retourne les informations de stockage."""
    ref = deal.deal_reference or "unknown"
    safe_ref = _sanitize_filename(ref)
    version = get_next_version(ref)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    file_path = f"deals/{safe_ref}/{timestamp}_v{version}.pdf"

    try:
        # fpdf2 peut retourner un bytearray — convertir en bytes pour Supabase
        pdf_bytes = bytes(pdf_bytes) if isinstance(pdf_bytes, bytearray) else pdf_bytes
        db.client.storage.from_(BUCKET_NAME).upload(
            file_path,
            pdf_bytes,
            file_options={
                "content-type": "application/pdf",
                "cache-control": "3600",
            },
        )
        logger.info("PDF uploadé : %s", file_path)
    except Exception as e:
        logger.error("Erreur upload PDF : %s", e)
        raise RuntimeError(f"Impossible d'uploader le PDF : {e}")

    try:
        public_url = db.client.storage.from_(BUCKET_NAME).get_public_url(file_path)
    except Exception:
        public_url = None
        logger.warning("Impossible de générer l'URL publique pour %s", file_path)

    record = {
        "version": version,
        "pdf_path": file_path,
        "pdf_url": public_url,
        "generated_by": generated_by,
        "snapshot": snapshot,
        "status": "active",
    }

    try:
        db_response = db.client.table("preconfirmation_documents").insert(record).execute()
        logger.info("Document enregistré en base : version %s pour %s", version, ref)
        if db_response.data:
            return db_response.data[0]
        return record
    except Exception as e:
        logger.error("Erreur enregistrement DB : %s", e)
        raise RuntimeError(f"Impossible d'enregistrer le document en base : {e}")


def get_document_by_id(doc_id: str) -> Optional[dict]:
    """Récupère un document par son ID."""
    try:
        result = (
            db.client.table("preconfirmation_documents")
            .select("*")
            .eq("id", doc_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error("Erreur récupération document : %s", e)
        return None


def list_documents_summary(deal_reference: Optional[str] = None, limit: int = 50) -> list:
    """Liste les documents avec un résumé audit (sans données confidentielles)."""
    try:
        query = db.client.table("preconfirmation_documents").select("*")
        if deal_reference:
            query = query.contains("snapshot", {"deal_reference": deal_reference})
        result = query.order("generated_at", desc=True).limit(limit).execute()
        
        summaries = []
        for doc in result.data or []:
            snapshot = doc.get("snapshot", {})
            products = snapshot.get("products", [])
            introducer_ids = set()
            for p in products:
                for c in p.get("commissions", []):
                    introducer_ids.add(c.get("introducer_id"))
            
            summaries.append({
                "id": doc.get("id"),
                "deal_reference": snapshot.get("deal_reference"),
                "version": doc.get("version"),
                "status": doc.get("status"),
                "generated_at": doc.get("generated_at"),
                "generated_by": doc.get("generated_by"),
                "pdf_url": doc.get("pdf_url"),
                "total_commissions": snapshot.get("total_commissions", "0"),
                "product_count": len(products),
                "introducer_count": len(introducer_ids),
            })
        return summaries
    except Exception as e:
        logger.error("Erreur listing documents : %s", e)
        return []


def get_document_detail(doc_id: str) -> Optional[dict]:
    """Récupère le détail complet d'un document (avec snapshot confidentiel)."""
    try:
        result = (
            db.client.table("preconfirmation_documents")
            .select("*")
            .eq("id", doc_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error("Erreur récupération document : %s", e)
        return None


def compare_versions(doc_id_a: str, doc_id_b: str) -> Optional[dict]:
    """Compare deux versions d'un document."""
    doc_a = get_document_by_id(doc_id_a)
    doc_b = get_document_by_id(doc_id_b)
    
    if not doc_a or not doc_b:
        return None
    
    snap_a = doc_a.get("snapshot", {})
    snap_b = doc_b.get("snapshot", {})
    
    changes = []
    
    # Comparaison des totaux
    total_a = snap_a.get("total_commissions", "0")
    total_b = snap_b.get("total_commissions", "0")
    if total_a != total_b:
        changes.append(f"Total commissions : {total_a} → {total_b}")
    
    # Comparaison du nombre de produits
    products_a = snap_a.get("products", [])
    products_b = snap_b.get("products", [])
    if len(products_a) != len(products_b):
        changes.append(f"Nombre de produits : {len(products_a)} → {len(products_b)}")
    
    # Comparaison des frais globaux
    fees_a = snap_a.get("total_fees_global", "0")
    fees_b = snap_b.get("total_fees_global", "0")
    if fees_a != fees_b:
        changes.append(f"Frais totaux : {fees_a} → {fees_b}")
    
    return {
        "deal_reference": snap_a.get("deal_reference"),
        "version_a": doc_a.get("version"),
        "version_b": doc_b.get("version"),
        "changes": changes,
        "total_commissions_a": total_a,
        "total_commissions_b": total_b,
    }

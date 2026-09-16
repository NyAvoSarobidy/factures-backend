"""
Service d'extraction des term sheets PDF.

Le brief est clair :
- L'extraction ne remplit PAS le notionnel (toujours saisi a la main)
- L'extraction ne remplit PAS la commission (toujours saisie a la main)
- Elle ne fait que prendre ce qu'elle peut : nom du produit, ISIN, emetteur, frais...

Le JSON retourne contient des champs `notional` et `commission` explicitement
vides pour rappeler a l'UI qu'il faut les remplir manuellement.
"""

import io
import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)


class TermSheetExtraction:
    """Resultat de l'extraction d'un term sheet."""

    def __init__(self):
        self.product_name: Optional[str] = None
        self.isin: Optional[str] = None
        self.issuer: Optional[str] = None
        self.currency: Optional[str] = None
        self.upfront_fee_rate: Optional[Decimal] = None
        self.notional: Optional[Decimal] = None  # TOUJOURS None — rempli a la main
        self.commission_terms: list = []  # TOUJOURS vide — rempli a la main
        self.raw_text: str = ""
        self.confidence: float = 0.0
        self.warnings: list = []

    def to_dict(self) -> dict:
        return {
            "product_name": self.product_name,
            "isin": self.isin,
            "issuer": self.issuer,
            "currency": self.currency,
            "upfront_fee_rate": str(self.upfront_fee_rate) if self.upfront_fee_rate else None,
            "notional": None,  # JAMAIS depuis le term sheet
            "commission_terms": [],  # JAMAIS depuis le term sheet
            "confidence": self.confidence,
            "warnings": self.warnings,
            "_meta": {
                "source": "term_sheet_extraction",
                "note": (
                    "Le notionnel et les termes de commission ne sont PAS "
                    "extraits du term sheet. Ils doivent etre saisis manuellement."
                ),
            },
        }


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte brut d'un PDF via PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        logger.error("Erreur lecture PDF : %s", e)
        raise RuntimeError(f"Impossible de lire le PDF : {e}")


def _extract_isin(text: str) -> Optional[str]:
    """Cherche un code ISIN (2 lettres + 9 alphanum + 1 chiffre)."""
    pattern = r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b'
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _extract_percentage(text: str, keywords: list) -> Optional[Decimal]:
    """Cherche un pourcentage pres d'un mot-cle."""
    for keyword in keywords:
        # Pattern: mot-cle suivi de nombre% (avec tolerance espaces)
        pattern = rf'{keyword}[:\s]+(\d+[.,]?\d*)\s*%'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = match.group(1).replace(',', '.')
                return Decimal(value)
            except InvalidOperation:
                pass
    return None


def _extract_currency(text: str) -> Optional[str]:
    """Cherche une devise (EUR, USD, GBP...)."""
    currencies = ['EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD']
    for cur in currencies:
        if cur in text.upper():
            return cur
    return None


def _extract_product_name(text: str) -> Optional[str]:
    """Heuristique : cherche 'Product', 'Note', 'Certificate' + nom."""
    patterns = [
        r'Product[:\s]+([A-Za-z\s\-]+?)(?:\n|$)',
        r'Name[:\s]+([A-Za-z\s\-]+?)(?:\n|$)',
        r'(?:Note|Certificate|Autocall|Snowball|Phoenix|Reverse)[:\s]*([A-Za-z\s\-]+?)(?:\n|$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if len(name) > 3 and len(name) < 100:
                return name
    return None


def _extract_issuer(text: str) -> Optional[str]:
    """Cherche l'emetteur."""
    patterns = [
        r'Issuer[:\s]+([A-Za-z\s\-\.]+?)(?:\n|$)',
        r'Emtteur[:\s]+([A-Za-z\s\-\.]+?)(?:\n|$)',
        r'(?:BNP|SG|JPM|GS|MS|CITI|DB|BARCLAYS|HSBC|UBS|CS)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.group(0).strip() and len(match.group(0).strip()) < 50:
                return match.group(0).strip()
    return None


def extract_term_sheet(pdf_bytes: bytes) -> dict:
    """Point d'entree principal de l'extraction.

    Retourne un JSON structure avec :
    - Les champs extractibles (nom, ISIN, emetteur, frais, devise)
    - Les champs NOTIONNEL et COMMISSION explicitement vides
    - Un score de confiance et des warnings
    """
    extraction = TermSheetExtraction()

    try:
        text = _extract_text_from_pdf(pdf_bytes)
        extraction.raw_text = text

        if not text.strip():
            extraction.warnings.append("PDF sans texte — peut-etre un scan")
            extraction.confidence = 0.0
            return extraction.to_dict()

        extraction.isin = _extract_isin(text)
        extraction.currency = _extract_currency(text)
        extraction.product_name = _extract_product_name(text)
        extraction.issuer = _extract_issuer(text)
        extraction.upfront_fee_rate = _extract_percentage(
            text, ['Fee', 'Frais', 'Commission', 'Upfront', 'Placement']
        )

        # Calcul de confiance
        fields = [extraction.isin, extraction.currency, extraction.product_name,
                  extraction.issuer, extraction.upfront_fee_rate]
        extraction.confidence = sum(1 for f in fields if f is not None) / len(fields)

        # Warnings
        if extraction.isin is None:
            extraction.warnings.append("ISIN non detecte")
        if extraction.upfront_fee_rate is None:
            extraction.warnings.append("Taux de frais non detecte")
        if extraction.currency is None:
            extraction.warnings.append("Devise non detecte")

    except Exception as e:
        logger.error("Erreur extraction : %s", e)
        extraction.warnings.append(f"Erreur : {str(e)}")

    return extraction.to_dict()

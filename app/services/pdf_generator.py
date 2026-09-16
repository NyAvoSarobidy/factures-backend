"""
Service de generation du PDF de pre-confirmation.

Le PDF est le document officiel envoye a la contrepartie.
Il ne contient JAMAIS :
  - le total des frais de l'emetteur
  - ce que l'entreprise garde

Il contient :
  - Logo (optionnel, uploade par l'utilisateur)
  - Reference du deal
  - Tableau multi-produits (notionnel, type de commission, montant d\u00fb)
  - Total des commissions
  - Bloc emetteur fixe
  - Notice de confidentialite
  - Mention de version / date de generation
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fpdf import FPDF

from app.schemas.api_response import DealPublic

logger = logging.getLogger(__name__)

# Police NotoSans — support complet Unicode + €
FONT_PATH = "fonts/NotoSans-Regular.ttf"
FONT_BOLD_PATH = "fonts/NotoSans-Bold.ttf"

# Constantes de mise en page
MARGIN_LEFT = 15
MARGIN_RIGHT = 15
PAGE_WIDTH = 210  # A4
PAGE_HEIGHT = 297
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

# Couleurs
DARK_BLUE = (26, 26, 46)  # #1a1a2e
LIGHT_GRAY = (245, 245, 245)
MEDIUM_GRAY = (150, 150, 150)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def _format_amount(amount: Decimal) -> str:
    """Formate un montant avec separateur de milliers et 2 decimales."""
    parts = f"{amount:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]
    if len(int_part) > 3:
        int_part = " ".join(
            [int_part[max(i - 3, 0):i] for i in range(len(int_part), 0, -3)][::-1]
        )
    return f"{int_part},{dec_part}"


class PreconfirmationPDF(FPDF):
    """PDF de pre-confirmation — stylise et professionnel."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(MARGIN_LEFT, 15, MARGIN_RIGHT)
        try:
            self.add_font("NotoSans", "", FONT_PATH, uni=False)
        except Exception:
            logger.warning("Police NotoSans introuvable — fallback Helvetica")
            self.add_font("NotoSans", "", "Helvetica", uni=False)
        try:
            self.add_font("NotoSans", "B", FONT_BOLD_PATH, uni=False)
        except Exception:
            pass

    def header(self):
        self.set_fill_color(*DARK_BLUE)
        self.rect(0, 0, PAGE_WIDTH, 8, style="F")

    def footer(self):
        self.set_y(-15)
        self.set_font("NotoSans", "", 8)
        self.set_text_color(*MEDIUM_GRAY)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")
        self.ln(4)
        self.cell(0, 10, "Document confidentiel — Ne pas diffuser sans autorisation.", align="C")

    def render_deal(
        self,
        deal: DealPublic,
        logo_path: Optional[str] = None,
        counterparty_name: Optional[str] = None,
        counterparty_address: Optional[str] = None,
    ):
        self.alias_nb_pages()
        self.add_page()

        y_start = 20

        if logo_path:
            try:
                self.image(logo_path, x=MARGIN_LEFT, y=y_start, w=40)
                y_start += 25
            except Exception as e:
                logger.warning("Logo illisible : %s", e)

        self.set_font("NotoSans", "B" if "B" in self.fonts else "", 18)
        self.set_text_color(*DARK_BLUE)
        self.set_xy(MARGIN_LEFT, y_start)
        self.cell(CONTENT_WIDTH, 12, "Pré-confirmation de commission", align="C")
        y_start += 16

        self.set_font("NotoSans", "", 10)
        self.set_text_color(*BLACK)
        ref = deal.deal_reference or "Non renseigné"
        self.set_xy(MARGIN_LEFT, y_start)
        self.cell(0, 6, f"Référence : {ref}")
        self.ln(6)
        date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        self.cell(0, 6, f"Date d'émission : {date_str}")
        self.ln(10)

        if counterparty_name:
            self.set_font("NotoSans", "B" if "B" in self.fonts else "", 11)
            self.cell(0, 8, "À l'attention de :")
            self.ln(7)
            self.set_font("NotoSans", "", 10)
            self.cell(0, 6, counterparty_name)
            self.ln(5)
            if counterparty_address:
                for line in counterparty_address.split("\n"):
                    self.cell(0, 5, line.strip())
                    self.ln(5)
            self.ln(5)

        self._render_table(deal)

        self.ln(8)
        total_formatted = _format_amount(deal.total_commissions)
        self.set_font("NotoSans", "B" if "B" in self.fonts else "", 13)
        self.set_text_color(*DARK_BLUE)
        self.cell(0, 10, f"Total des commissions : {total_formatted}")
        self.set_text_color(*BLACK)

        self._render_issuer_block()

    def _render_table(self, deal: DealPublic):
        col_widths = [55, 40, 50, 45]
        headers = ["Produit", "Notionnel", "Commission", "Montant dû"]

        self.set_fill_color(*DARK_BLUE)
        self.set_text_color(*WHITE)
        self.set_font("NotoSans", "B" if "B" in self.fonts else "", 9)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
        self.ln()

        self.set_text_color(*BLACK)
        self.set_font("NotoSans", "", 9)
        fill = False
        for product in deal.products:
            for comm in product.commissions:
                if fill:
                    self.set_fill_color(*LIGHT_GRAY)
                else:
                    self.set_fill_color(*WHITE)
                cells = [
                    product.product_name[:28],
                    f"{_format_amount(product.notional)} {product.currency}",
                    f"{comm.commission_type.value}",
                    f"{_format_amount(comm.calculated_amount)} {comm.commission_currency}",
                ]
                for i, txt in enumerate(cells):
                    self.cell(col_widths[i], 7, txt, border=1, align="C", fill=True)
                self.ln()
                fill = not fill

    def _render_issuer_block(self):
        self.ln(15)
        self.set_draw_color(*DARK_BLUE)
        self.line(MARGIN_LEFT, self.get_y(), PAGE_WIDTH - MARGIN_RIGHT, self.get_y())
        self.ln(5)
        self.set_font("NotoSans", "B" if "B" in self.fonts else "", 10)
        self.set_text_color(*DARK_BLUE)
        self.cell(0, 6, "Émis par :")
        self.ln(6)
        self.set_font("NotoSans", "", 9)
        self.set_text_color(*BLACK)
        for line in [
            "Conseil Structured Products SARL",
            "12 avenue des Champs-Élysées",
            "75008 Paris, France",
            "SIRET : 123 456 789 00012",
            "contact@structured-products.fr",
        ]:
            self.cell(0, 5, line)
            self.ln(5)


def generate_preconfirmation_pdf(
    deal: DealPublic,
    logo_path: Optional[str] = None,
    counterparty_name: Optional[str] = None,
    counterparty_address: Optional[str] = None,
) -> bytes:
    """Genere le PDF et retourne les bytes."""
    pdf = PreconfirmationPDF()
    pdf.render_deal(deal, logo_path, counterparty_name, counterparty_address)
    return pdf.output()

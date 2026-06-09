"""PDF exporter.

Engine selection (preferred → fallback):
  1. **WeasyPrint** — best HTML/CSS fidelity, but needs native system libraries
     (Pango/Cairo). Used automatically when it imports successfully.
  2. **reportlab** — pure-Python, always installable. Parses the sanitized HTML body
     with BeautifulSoup and renders headings, paragraphs, ordered/unordered lists,
     blockquotes and inline bold/italic/underline. This guarantees PDF export works
     on every platform (Section 4.8) and is the documented fallback.
"""
from __future__ import annotations

import io
from html import escape

from bs4 import BeautifulSoup, NavigableString, Tag

from app.exporters.base import DocumentExporter
from app.models.document import Document


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except Exception:
        return False
    return True


class PdfExporter(DocumentExporter):
    formats = ("pdf",)
    extension = ".pdf"
    media_type = "application/pdf"

    def _render(self, document: Document) -> bytes:
        if _weasyprint_available():
            try:
                return self._render_weasyprint(document)
            except Exception:
                # Any runtime issue (missing libs surfaced late) → reportlab.
                pass
        return self._render_reportlab(document)

    # ---- engine 1: WeasyPrint ------------------------------------------------

    def _render_weasyprint(self, document: Document) -> bytes:
        import weasyprint

        full_html = (
            "<html><head><meta charset='utf-8'><style>"
            "body{font-family:Helvetica,Arial,sans-serif;margin:2.5cm;line-height:1.5;}"
            "h1,h2,h3{font-family:Helvetica,Arial,sans-serif;}"
            "</style></head><body>"
            f"<h1>{escape(document.title)}</h1>"
            f"{document.content_html or ''}"
            "</body></html>"
        )
        return weasyprint.HTML(string=full_html).write_pdf()

    # ---- engine 2: reportlab -------------------------------------------------

    def _render_reportlab(self, document: Document) -> bytes:
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            "DocBody", parent=styles["BodyText"], fontSize=11, leading=16, alignment=TA_LEFT
        )
        quote_style = ParagraphStyle(
            "DocQuote", parent=body_style, leftIndent=18, textColor="#555555"
        )
        code_style = ParagraphStyle(
            "DocCode", parent=body_style, fontName="Courier", backColor="#f4f4f4"
        )
        heading_styles = {
            "h1": styles["Heading1"],
            "h2": styles["Heading2"],
            "h3": styles["Heading3"],
            "h4": styles["Heading4"],
            "h5": styles["Heading5"],
            "h6": styles["Heading6"],
        }

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2.2 * cm, rightMargin=2.2 * cm, title=document.title,
        )
        flow = [Paragraph(escape(document.title), styles["Title"]), Spacer(1, 10)]

        soup = BeautifulSoup(document.content_html or "", "html.parser")
        top_nodes = [n for n in soup.contents] or []
        for node in top_nodes:
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    flow.append(Paragraph(escape(text), body_style))
                continue
            if not isinstance(node, Tag):
                continue

            name = node.name.lower()
            if name in heading_styles:
                flow.append(Paragraph(self._inline(node), heading_styles[name]))
            elif name in ("ul", "ol"):
                flow.append(self._render_list(node, body_style, ListFlowable, ListItem, Paragraph))
            elif name == "blockquote":
                flow.append(Paragraph(self._inline(node), quote_style))
            elif name in ("pre", "code"):
                flow.append(Paragraph(self._inline(node), code_style))
            else:  # p, div, or anything else with text
                inline = self._inline(node)
                if inline.strip():
                    flow.append(Paragraph(inline, body_style))
            flow.append(Spacer(1, 4))

        if len(flow) <= 2:
            flow.append(Paragraph("(empty document)", body_style))

        doc.build(flow)
        return buf.getvalue()

    def _render_list(self, node, body_style, ListFlowable, ListItem, Paragraph):
        items = []
        for li in node.find_all("li", recursive=False):
            items.append(ListItem(Paragraph(self._inline(li), body_style)))
        bullet_type = "1" if node.name.lower() == "ol" else "bullet"
        return ListFlowable(items, bulletType=bullet_type, start="1", leftIndent=18)

    # ---- inline HTML -> reportlab mini-markup --------------------------------

    _INLINE_MAP = {
        "strong": "b", "b": "b",
        "em": "i", "i": "i",
        "u": "u",
        "s": "strike", "del": "strike",
        "sub": "sub", "sup": "super",
    }

    def _inline(self, node) -> str:
        out: list[str] = []
        for child in node.children:
            if isinstance(child, NavigableString):
                out.append(escape(str(child)))
            elif isinstance(child, Tag):
                name = child.name.lower()
                if name == "br":
                    out.append("<br/>")
                    continue
                inner = self._inline(child)
                tag = self._INLINE_MAP.get(name)
                if tag:
                    out.append(f"<{tag}>{inner}</{tag}>")
                elif name == "code":
                    out.append(f'<font face="Courier">{inner}</font>')
                else:  # a, span, mark, nested block — keep inner text
                    out.append(inner)
        return "".join(out).strip()

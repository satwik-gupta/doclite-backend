"""Markdown exporter: HTML body -> Markdown via markdownify."""
from __future__ import annotations

from markdownify import markdownify as md

from app.exporters.base import DocumentExporter
from app.models.document import Document


class MarkdownExporter(DocumentExporter):
    formats = ("md", "markdown")
    extension = ".md"
    media_type = "text/markdown; charset=utf-8"

    def _render(self, document: Document) -> bytes:
        body = md(document.content_html or "", heading_style="ATX")
        text = f"# {document.title}\n\n{body.strip()}\n"
        return text.encode("utf-8")

"""Markdown importer: converts Markdown to HTML, preserving headings/lists."""
from __future__ import annotations

import markdown as md

from app.importers.base import DocumentImporter


class MarkdownImporter(DocumentImporter):
    extensions = (".md", ".markdown")

    def _to_html(self, data: bytes) -> str:
        text = self._decode(data)
        html = md.markdown(
            text,
            extensions=["extra", "sane_lists", "nl2br"],
            output_format="html5",
        )
        return html or "<p></p>"

"""Plain-text importer: blank-line-separated blocks become paragraphs."""
from __future__ import annotations

from html import escape

from app.importers.base import DocumentImporter


class TxtImporter(DocumentImporter):
    extensions = (".txt",)

    def _to_html(self, data: bytes) -> str:
        text = self._decode(data).replace("\r\n", "\n").replace("\r", "\n")
        blocks = [b.strip() for b in text.split("\n\n")]
        paragraphs = []
        for block in blocks:
            if not block:
                continue
            # Preserve single newlines inside a block as <br>.
            inner = "<br>".join(escape(line) for line in block.split("\n"))
            paragraphs.append(f"<p>{inner}</p>")
        return "".join(paragraphs) or "<p></p>"

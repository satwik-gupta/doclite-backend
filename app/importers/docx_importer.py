"""DOCX importer: maps Word styles to HTML headings, lists and inline formatting.

Uses python-docx. Heading styles become ``<h1..h3>``; List Bullet / List Number
paragraphs are grouped into ``<ul>`` / ``<ol>``; run-level bold/italic/underline
become ``<strong>``/``<em>``/``<u>``. This preserves the structure the spec calls for
(headings + lists) without attempting a perfect fidelity conversion.
"""
from __future__ import annotations

import io
from html import escape

from docx import Document as DocxDocument

from app.core.exceptions import ValidationError
from app.importers.base import DocumentImporter


class DocxImporter(DocumentImporter):
    extensions = (".docx",)

    def _to_html(self, data: bytes) -> str:
        try:
            document = DocxDocument(io.BytesIO(data))
        except Exception as exc:  # corrupt / not a real docx
            raise ValidationError("Could not read the .docx file; it may be corrupt.") from exc

        html_parts: list[str] = []
        list_buffer: list[str] = []
        list_tag: str | None = None  # 'ul' or 'ol' while collecting list items

        def flush_list() -> None:
            nonlocal list_buffer, list_tag
            if list_buffer and list_tag:
                html_parts.append(f"<{list_tag}>" + "".join(list_buffer) + f"</{list_tag}>")
            list_buffer = []
            list_tag = None

        for para in document.paragraphs:
            style = (para.style.name if para.style else "") or ""
            inner = self._runs_to_html(para)
            if not inner.strip():
                flush_list()
                continue

            list_kind = self._list_kind(style)
            if list_kind:
                if list_tag and list_tag != list_kind:
                    flush_list()
                list_tag = list_kind
                list_buffer.append(f"<li>{inner}</li>")
                continue

            flush_list()
            tag = self._block_tag(style)
            html_parts.append(f"<{tag}>{inner}</{tag}>")

        flush_list()
        return "".join(html_parts) or "<p></p>"

    @staticmethod
    def _list_kind(style_name: str) -> str | None:
        """Any Word 'List …' style is a list item; numbered → ol, otherwise ul."""
        name = style_name.lower()
        if not name.startswith("list"):
            return None
        return "ol" if "number" in name else "ul"

    @staticmethod
    def _block_tag(style_name: str) -> str:
        name = style_name.lower()
        if name == "title":
            return "h1"
        if name.startswith("heading"):
            digits = "".join(ch for ch in name if ch.isdigit())
            level = int(digits) if digits else 1
            return f"h{min(max(level, 1), 4)}"
        return "p"

    @staticmethod
    def _runs_to_html(para) -> str:
        parts: list[str] = []
        for run in para.runs:
            text = escape(run.text or "")
            if not text:
                continue
            if run.bold:
                text = f"<strong>{text}</strong>"
            if run.italic:
                text = f"<em>{text}</em>"
            if run.underline:
                text = f"<u>{text}</u>"
            parts.append(text)
        if not parts:
            return escape(para.text or "")
        return "".join(parts)

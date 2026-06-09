"""ExporterFactory — selects the right exporter strategy for a format key."""
from __future__ import annotations

from typing import List

from app.core.exceptions import ValidationError
from app.exporters.base import DocumentExporter
from app.exporters.markdown_exporter import MarkdownExporter
from app.exporters.pdf_exporter import PdfExporter


class ExporterFactory:
    def __init__(self, exporters: List[DocumentExporter] | None = None) -> None:
        self._exporters: List[DocumentExporter] = exporters or [
            MarkdownExporter(),
            PdfExporter(),
        ]

    def register(self, exporter: DocumentExporter) -> None:
        self._exporters.append(exporter)

    def supported_formats(self) -> List[str]:
        formats: List[str] = []
        for exp in self._exporters:
            formats.extend(exp.formats)
        return formats

    def for_format(self, fmt: str) -> DocumentExporter:
        key = (fmt or "").lower().lstrip(".")
        for exporter in self._exporters:
            if key in exporter.formats:
                return exporter
        raise ValidationError(
            f"Unsupported export format '{fmt}'. Supported: {', '.join(self.supported_formats())}."
        )

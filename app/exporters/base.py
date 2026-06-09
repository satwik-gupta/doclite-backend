"""Abstract export strategy.

Each exporter renders a document's title + HTML body into a downloadable byte
stream with a media type and a file extension. Adding a new export format means
adding one subclass and registering it in the factory — existing exporters and
callers are untouched (Open/Closed).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.document import Document


@dataclass
class ExportResult:
    filename: str
    media_type: str
    content: bytes


class DocumentExporter(ABC):
    """Strategy interface for exporting a document."""

    #: short format keys this exporter answers to (e.g. ``("md", "markdown")``)
    formats: tuple[str, ...] = ()
    extension: str = ""
    media_type: str = "application/octet-stream"

    def export(self, document: Document) -> ExportResult:
        content = self._render(document)
        return ExportResult(
            filename=f"{self._safe_stem(document.title)}{self.extension}",
            media_type=self.media_type,
            content=content,
        )

    @abstractmethod
    def _render(self, document: Document) -> bytes:
        """Produce the raw bytes of the export. Implemented per format."""

    @staticmethod
    def _safe_stem(title: str) -> str:
        stem = re.sub(r"[^\w\- ]+", "", title or "document").strip().replace(" ", "_")
        return stem or "document"

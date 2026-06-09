"""Abstract import strategy.

Each concrete importer knows how to turn one family of uploaded bytes into the
canonical rich-text representation (sanitized HTML). The base class fixes the
contract (Liskov): every importer declares the extensions it handles and produces an
:class:`ImportResult`.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from app.core.html_sanitizer import sanitize_html


@dataclass
class ImportResult:
    title: str
    content_html: str


class DocumentImporter(ABC):
    """Strategy interface for converting uploaded bytes to a document."""

    #: file extensions (lowercase, with dot) this importer handles
    extensions: tuple[str, ...] = ()

    def can_handle(self, filename: str) -> bool:
        return self._ext(filename) in self.extensions

    def import_bytes(self, filename: str, data: bytes) -> ImportResult:
        """Template method: convert, then always sanitize before returning."""
        html = self._to_html(data)
        return ImportResult(
            title=self._title_from_filename(filename),
            content_html=sanitize_html(html),
        )

    @abstractmethod
    def _to_html(self, data: bytes) -> str:
        """Convert raw bytes to (unsanitized) HTML. Implemented per format."""

    # ---- helpers shared by subclasses ---------------------------------------

    @staticmethod
    def _ext(filename: str) -> str:
        return os.path.splitext(filename)[1].lower()

    @staticmethod
    def _title_from_filename(filename: str) -> str:
        stem = os.path.splitext(os.path.basename(filename))[0].strip()
        return stem or "Imported document"

    @staticmethod
    def _decode(data: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    @staticmethod
    def all_extensions(importers: Iterable["DocumentImporter"]) -> list[str]:
        result: list[str] = []
        for imp in importers:
            result.extend(imp.extensions)
        return result

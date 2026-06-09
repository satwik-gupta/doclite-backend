"""ImporterFactory — selects the right importer strategy for a filename.

Registration-based so adding a format is one line; callers never branch on type.
"""
from __future__ import annotations

import os
from typing import List

from app.core.exceptions import UnsupportedFileTypeError
from app.importers.base import DocumentImporter
from app.importers.docx_importer import DocxImporter
from app.importers.markdown_importer import MarkdownImporter
from app.importers.txt_importer import TxtImporter


class ImporterFactory:
    """Holds the registered importer strategies and resolves one per filename."""

    def __init__(self, importers: List[DocumentImporter] | None = None) -> None:
        self._importers: List[DocumentImporter] = importers or [
            TxtImporter(),
            MarkdownImporter(),
            DocxImporter(),
        ]

    def register(self, importer: DocumentImporter) -> None:
        self._importers.append(importer)

    def supported_extensions(self) -> List[str]:
        exts: List[str] = []
        for imp in self._importers:
            exts.extend(imp.extensions)
        return exts

    def for_filename(self, filename: str) -> DocumentImporter:
        for importer in self._importers:
            if importer.can_handle(filename):
                return importer
        ext = os.path.splitext(filename)[1].lower() or "(none)"
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. Supported: {', '.join(self.supported_extensions())}."
        )

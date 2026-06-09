"""ImportService — validate an upload, convert it, and create an editable document."""
from __future__ import annotations

import os
from typing import List

from app.core.config import Settings
from app.core.exceptions import UnsupportedFileTypeError, ValidationError
from app.importers.factory import ImporterFactory
from app.models.user import User
from app.services.document_service import DocumentService, DocumentWithRole


class ImportService:
    def __init__(
        self,
        document_service: DocumentService,
        settings: Settings,
        factory: ImporterFactory | None = None,
    ) -> None:
        self._documents = document_service
        self._settings = settings
        self._factory = factory or ImporterFactory()

    def supported_extensions(self) -> List[str]:
        return self._factory.supported_extensions()

    def import_upload(self, user: User, filename: str, data: bytes) -> DocumentWithRole:
        if not filename:
            raise ValidationError("A filename is required.")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in self._settings.allowed_upload_extensions:
            raise UnsupportedFileTypeError(
                f"Unsupported file type '{ext or '(none)'}'. "
                f"Allowed: {', '.join(self._settings.allowed_upload_extensions)}."
            )

        if not data:
            raise ValidationError("The uploaded file is empty.")
        if len(data) > self._settings.max_upload_bytes:
            limit_mb = self._settings.max_upload_bytes / (1024 * 1024)
            raise ValidationError(f"File too large. Maximum size is {limit_mb:.1f} MB.")

        importer = self._factory.for_filename(filename)
        result = importer.import_bytes(filename, data)
        return self._documents.create(user, result.title, result.content_html)

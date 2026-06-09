"""ExportService — access-controlled rendering of a document to a download."""
from __future__ import annotations

from typing import List

from app.domain.enums import Action
from app.exporters.base import ExportResult
from app.exporters.factory import ExporterFactory
from app.models.user import User
from app.services.access import AccessGuard


class ExportService:
    def __init__(self, access: AccessGuard, factory: ExporterFactory | None = None) -> None:
        self._access = access
        self._factory = factory or ExporterFactory()

    def supported_formats(self) -> List[str]:
        return self._factory.supported_formats()

    def export(self, user: User, document_id: int, fmt: str) -> ExportResult:
        # EXPORT is permitted for every role, but the user must still have access.
        document, _ = self._access.require(user, document_id, Action.EXPORT)
        exporter = self._factory.for_format(fmt)
        return exporter.export(document)

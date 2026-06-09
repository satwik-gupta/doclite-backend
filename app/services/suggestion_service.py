"""SuggestionService — propose changes without mutating the canonical body.

A suggestion stores the full proposed HTML separately from the document. The
document body is only ever changed when an owner/editor *accepts* a suggestion, at
which point the change is applied through :class:`DocumentService.save_body` (which
also records a version). Rejecting leaves the body untouched.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.core.exceptions import ConflictError, NotFoundError
from app.core.html_sanitizer import sanitize_html
from app.domain.enums import Action, SuggestionStatus
from app.models.suggestion import Suggestion
from app.models.user import User
from app.repositories.comment_repo import SuggestionRepository
from app.services.access import AccessGuard
from app.services.document_service import DocumentService, DocumentWithRole


class SuggestionService:
    def __init__(
        self,
        suggestion_repo: SuggestionRepository,
        document_service: DocumentService,
        access: AccessGuard,
    ) -> None:
        self._suggestions = suggestion_repo
        self._documents = document_service
        self._access = access

    def list_suggestions(self, user: User, document_id: int) -> List[Suggestion]:
        self._access.require(user, document_id, Action.VIEW)
        return self._suggestions.list_for_document(document_id)

    def create_suggestion(
        self, user: User, document_id: int, summary: str, proposed_html: str
    ) -> Suggestion:
        # SUGGEST capability => owner/editor/commenter; viewer is denied.
        document, _ = self._access.require(user, document_id, Action.SUGGEST)
        suggestion = Suggestion(
            document_id=document_id,
            author_id=user.id,
            summary=summary.strip() or "Proposed change",
            base_html=document.content_html,  # snapshot the body at proposal time
            proposed_html=sanitize_html(proposed_html),
            status=SuggestionStatus.PENDING,
        )
        return self._suggestions.add(suggestion)

    def accept_suggestion(
        self, user: User, document_id: int, suggestion_id: int
    ) -> DocumentWithRole:
        self._access.require(user, document_id, Action.RESOLVE_SUGGESTION)
        suggestion = self._require_pending(document_id, suggestion_id)
        # Apply the proposed body via the normal save path (records a version).
        item = self._documents.save_body(
            user,
            document_id,
            suggestion.proposed_html,
            create_version=True,
            label=f"accept suggestion #{suggestion.id}",
        )
        self._mark_resolved(suggestion, user, SuggestionStatus.ACCEPTED)
        return item

    def reject_suggestion(
        self, user: User, document_id: int, suggestion_id: int
    ) -> Suggestion:
        self._access.require(user, document_id, Action.RESOLVE_SUGGESTION)
        suggestion = self._require_pending(document_id, suggestion_id)
        self._mark_resolved(suggestion, user, SuggestionStatus.REJECTED)
        return suggestion

    # ---- helpers -------------------------------------------------------------

    def _require_pending(self, document_id: int, suggestion_id: int) -> Suggestion:
        suggestion = self._suggestions.get_for_document(document_id, suggestion_id)
        if suggestion is None:
            raise NotFoundError("Suggestion not found.")
        if suggestion.status != SuggestionStatus.PENDING:
            raise ConflictError(f"Suggestion already {suggestion.status.value}.")
        return suggestion

    @staticmethod
    def _mark_resolved(
        suggestion: Suggestion, user: User, status: SuggestionStatus
    ) -> None:
        suggestion.status = status
        suggestion.resolved_by_id = user.id
        suggestion.resolved_at = datetime.now(timezone.utc)

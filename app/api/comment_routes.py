"""Comment + reply + suggestion routes (thin controllers)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.api.deps import (
    CommentServiceDep,
    ConnectionManagerDep,
    CurrentUserDep,
    SharingServiceDep,
    SuggestionServiceDep,
)
from app.api.presenters import to_detail
from app.schemas.comment import CommentCreate, CommentOut, ReplyCreate
from app.schemas.common import MessageResponse
from app.schemas.document import DocumentDetail
from app.schemas.suggestion import SuggestionCreate, SuggestionOut

router = APIRouter(prefix="/api/documents", tags=["comments"])


# ---- comments ---------------------------------------------------------------


@router.get("/{document_id}/comments", response_model=List[CommentOut])
def list_comments(
    document_id: int, current_user: CurrentUserDep, comments: CommentServiceDep
) -> List[CommentOut]:
    return [
        CommentOut.model_validate(c)
        for c in comments.list_comments(current_user, document_id)
    ]


@router.post("/{document_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    document_id: int,
    payload: CommentCreate,
    current_user: CurrentUserDep,
    comments: CommentServiceDep,
) -> CommentOut:
    comment = comments.create_comment(
        current_user,
        document_id,
        payload.body,
        payload.anchor_start,
        payload.anchor_end,
        payload.quoted_text,
    )
    return CommentOut.model_validate(comment)


@router.post("/{document_id}/comments/{comment_id}/replies", response_model=CommentOut)
def reply_to_comment(
    document_id: int,
    comment_id: int,
    payload: ReplyCreate,
    current_user: CurrentUserDep,
    comments: CommentServiceDep,
) -> CommentOut:
    comments.reply(current_user, document_id, comment_id, payload.body)
    # Return the full comment (with the new reply) for easy UI refresh.
    comment = comments.get_comment(current_user, document_id, comment_id)
    return CommentOut.model_validate(comment)


@router.patch("/{document_id}/comments/{comment_id}/resolve", response_model=CommentOut)
def resolve_comment(
    document_id: int,
    comment_id: int,
    current_user: CurrentUserDep,
    comments: CommentServiceDep,
    resolved: bool = True,
) -> CommentOut:
    comment = comments.set_resolved(current_user, document_id, comment_id, resolved)
    return CommentOut.model_validate(comment)


@router.delete("/{document_id}/comments/{comment_id}", response_model=MessageResponse)
def delete_comment(
    document_id: int,
    comment_id: int,
    current_user: CurrentUserDep,
    comments: CommentServiceDep,
) -> MessageResponse:
    comments.delete_comment(current_user, document_id, comment_id)
    return MessageResponse(message="Comment deleted.")


# ---- suggestions ------------------------------------------------------------


@router.get("/{document_id}/suggestions", response_model=List[SuggestionOut])
def list_suggestions(
    document_id: int, current_user: CurrentUserDep, suggestions: SuggestionServiceDep
) -> List[SuggestionOut]:
    return [
        SuggestionOut.model_validate(s)
        for s in suggestions.list_suggestions(current_user, document_id)
    ]


@router.post("/{document_id}/suggestions", response_model=SuggestionOut, status_code=201)
def create_suggestion(
    document_id: int,
    payload: SuggestionCreate,
    current_user: CurrentUserDep,
    suggestions: SuggestionServiceDep,
) -> SuggestionOut:
    suggestion = suggestions.create_suggestion(
        current_user, document_id, payload.summary, payload.proposed_html
    )
    return SuggestionOut.model_validate(suggestion)


@router.post(
    "/{document_id}/suggestions/{suggestion_id}/accept", response_model=DocumentDetail
)
async def accept_suggestion(
    document_id: int,
    suggestion_id: int,
    current_user: CurrentUserDep,
    suggestions: SuggestionServiceDep,
    sharing: SharingServiceDep,
    connections: ConnectionManagerDep,
) -> DocumentDetail:
    item = suggestions.accept_suggestion(current_user, document_id, suggestion_id)
    collaborators = sharing.list_collaborators(current_user, document_id)
    await connections.notify_document_updated(
        document_id, current_user, label="suggestion accepted"
    )
    return to_detail(item, collaborators)


@router.post(
    "/{document_id}/suggestions/{suggestion_id}/reject", response_model=SuggestionOut
)
def reject_suggestion(
    document_id: int,
    suggestion_id: int,
    current_user: CurrentUserDep,
    suggestions: SuggestionServiceDep,
) -> SuggestionOut:
    suggestion = suggestions.reject_suggestion(current_user, document_id, suggestion_id)
    return SuggestionOut.model_validate(suggestion)

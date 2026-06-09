"""CommentService — range-anchored comments with replies and resolution."""
from __future__ import annotations

from typing import List

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.domain.enums import Action, Role
from app.models.comment import Comment, CommentReply
from app.models.user import User
from app.repositories.comment_repo import CommentRepository
from app.services.access import AccessGuard


class CommentService:
    def __init__(self, comment_repo: CommentRepository, access: AccessGuard) -> None:
        self._comments = comment_repo
        self._access = access

    def list_comments(self, user: User, document_id: int) -> List[Comment]:
        self._access.require(user, document_id, Action.VIEW)
        return self._comments.list_for_document(document_id)

    def get_comment(self, user: User, document_id: int, comment_id: int) -> Comment:
        self._access.require(user, document_id, Action.VIEW)
        return self._require_comment(document_id, comment_id)

    def create_comment(
        self,
        user: User,
        document_id: int,
        body: str,
        anchor_start: int,
        anchor_end: int,
        quoted_text: str,
    ) -> Comment:
        # COMMENT capability => owner/editor/commenter; viewer is denied here.
        self._access.require(user, document_id, Action.COMMENT)
        comment = Comment(
            document_id=document_id,
            author_id=user.id,
            body=body.strip(),
            anchor_start=anchor_start,
            anchor_end=anchor_end,
            quoted_text=(quoted_text or "")[:1000],
        )
        return self._comments.add(comment)

    def reply(self, user: User, document_id: int, comment_id: int, body: str) -> CommentReply:
        self._access.require(user, document_id, Action.COMMENT)
        comment = self._require_comment(document_id, comment_id)
        reply = CommentReply(comment_id=comment.id, author_id=user.id, body=body.strip())
        return self._comments.add_reply(reply)

    def set_resolved(
        self, user: User, document_id: int, comment_id: int, resolved: bool
    ) -> Comment:
        _, role = self._access.require(user, document_id, Action.COMMENT)
        comment = self._require_comment(document_id, comment_id)
        # Author, or anyone with edit rights (owner/editor), may toggle resolution.
        if comment.author_id != user.id and not role.at_least(Role.EDITOR):
            raise PermissionDeniedError("Only the comment author or an editor can resolve it.")
        comment.resolved = resolved
        return comment

    def delete_comment(self, user: User, document_id: int, comment_id: int) -> None:
        _, role = self._access.require(user, document_id, Action.VIEW)
        comment = self._require_comment(document_id, comment_id)
        if comment.author_id != user.id and role != Role.OWNER:
            raise PermissionDeniedError("Only the author or the owner can delete a comment.")
        self._comments.delete(comment)

    def _require_comment(self, document_id: int, comment_id: int) -> Comment:
        comment = self._comments.get_for_document(document_id, comment_id)
        if comment is None:
            raise NotFoundError("Comment not found.")
        return comment

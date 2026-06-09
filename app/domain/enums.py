"""Core domain enums: roles and actions.

These are first-class types (not loose strings) so the authorization policy and the
ORM share one vocabulary. ``Role`` is ordered by privilege to make comparisons easy.
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """A collaborator's role on a document, ordered most→least privileged."""

    OWNER = "owner"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"

    @property
    def rank(self) -> int:
        """Lower rank == more privilege. Useful for 'at least' comparisons."""
        return _ROLE_RANK[self]

    def at_least(self, other: "Role") -> bool:
        """True if this role is at least as privileged as ``other``."""
        return self.rank <= other.rank


_ROLE_RANK: dict[Role, int] = {
    Role.OWNER: 0,
    Role.EDITOR: 1,
    Role.COMMENTER: 2,
    Role.VIEWER: 3,
}


class Action(str, Enum):
    """Discrete actions a user may attempt against a document."""

    VIEW = "view"
    EDIT_BODY = "edit_body"
    COMMENT = "comment"
    SUGGEST = "suggest"
    RESOLVE_SUGGESTION = "resolve_suggestion"  # accept/reject suggestions
    CREATE_VERSION = "create_version"
    RESTORE_VERSION = "restore_version"
    EXPORT = "export"
    MANAGE_SHARING = "manage_sharing"  # add/change/revoke collaborators & roles
    RENAME = "rename"
    DELETE = "delete"


class SuggestionStatus(str, Enum):
    """Lifecycle of a proposed change."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

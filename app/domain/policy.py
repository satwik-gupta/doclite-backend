"""The single, central authorization policy.

Every service consults :class:`PermissionPolicy` to answer "can user U perform
action A on document D?". The role→capability mapping lives here and ONLY here —
there are no scattered, duplicated permission checks anywhere else in the codebase.

The policy is intentionally pure with respect to persistence: callers resolve a
user's *share role* (via the repository layer) and hand it in. The policy then
derives the effective role (owner is implied by ``Document.owner_id``) and applies
the capability matrix. This keeps the policy unit-testable in isolation.
"""
from __future__ import annotations

from typing import Optional

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.domain.enums import Action, Role
from app.models.document import Document
from app.models.user import User


class PermissionPolicy:
    """Encapsulates the role→capability matrix and access decisions."""

    # The complete capability matrix. Adding a role or action is a one-line change
    # here and nowhere else (Open/Closed).
    _MATRIX: dict[Role, frozenset[Action]] = {
        Role.OWNER: frozenset(Action),  # owner can do everything
        Role.EDITOR: frozenset(
            {
                Action.VIEW,
                Action.EDIT_BODY,
                Action.RENAME,
                Action.COMMENT,
                Action.SUGGEST,
                Action.RESOLVE_SUGGESTION,
                Action.CREATE_VERSION,
                Action.RESTORE_VERSION,
                Action.EXPORT,
            }
        ),
        Role.COMMENTER: frozenset(
            {
                Action.VIEW,
                Action.COMMENT,
                Action.SUGGEST,
                Action.EXPORT,
            }
        ),
        Role.VIEWER: frozenset(
            {
                Action.VIEW,
                Action.EXPORT,
            }
        ),
    }

    def capabilities(self, role: Role) -> frozenset[Action]:
        """Return the set of actions a role may perform."""
        return self._MATRIX.get(role, frozenset())

    def role_allows(self, role: Optional[Role], action: Action) -> bool:
        """Pure matrix check: does ``role`` permit ``action``? ``None`` => no access."""
        if role is None:
            return False
        return action in self._MATRIX.get(role, frozenset())

    def effective_role(
        self, user: User, document: Document, share_role: Optional[Role]
    ) -> Optional[Role]:
        """Resolve a user's effective role on a document.

        Ownership wins over any share; otherwise the share role (if any) applies;
        otherwise the user has no relationship to the document (``None``).
        """
        if document.owner_id == user.id:
            return Role.OWNER
        return share_role

    def can(
        self,
        user: User,
        action: Action,
        document: Document,
        share_role: Optional[Role] = None,
    ) -> bool:
        """Decision: may ``user`` perform ``action`` on ``document``?

        ``share_role`` is the user's stored collaborator role (``None`` if not shared);
        owners are detected automatically and need not pass a share role.
        """
        role = self.effective_role(user, document, share_role)
        return self.role_allows(role, action)

    def authorize(
        self,
        user: User,
        action: Action,
        document: Document,
        share_role: Optional[Role] = None,
    ) -> Role:
        """Enforce access, returning the effective role or raising.

        Raises :class:`NotFoundError` when the user has no relationship to the
        document at all (so existence is not leaked), and
        :class:`PermissionDeniedError` when the user has a role but lacks the
        specific capability.
        """
        role = self.effective_role(user, document, share_role)
        if role is None:
            # Hide existence from total strangers.
            raise NotFoundError("Document not found.")
        if not self.role_allows(role, action):
            raise PermissionDeniedError(
                f"Role '{role.value}' cannot perform '{action.value}'."
            )
        return role

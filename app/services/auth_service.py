"""AuthService — registration, authentication and token issuing."""
from __future__ import annotations

from typing import Optional

from app.core.exceptions import AuthenticationError, ValidationError
from app.core.security import SecurityManager
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, security: SecurityManager) -> None:
        self._users = user_repo
        self._security = security

    def register(
        self, email: str, username: str, display_name: str, password: str
    ) -> User:
        email = email.lower().strip()
        username = username.strip()
        if self._users.get_by_email(email):
            raise ValidationError("A user with that email already exists.")
        if self._users.get_by_username(username):
            raise ValidationError("That username is taken.")
        user = User(
            email=email,
            username=username,
            display_name=display_name.strip() or username,
            hashed_password=self._security.hash_password(password),
        )
        return self._users.add(user)

    def authenticate(self, identifier: str, password: str) -> User:
        user: Optional[User] = self._users.get_by_identifier(identifier)
        if user is None or not self._security.verify_password(password, user.hashed_password):
            # Same error for "no such user" and "bad password" — no account enumeration.
            raise AuthenticationError("Invalid username/email or password.")
        return user

    def issue_token(self, user: User) -> str:
        return self._security.create_access_token(subject=str(user.id))

    def user_from_token(self, token: str) -> User:
        subject = self._security.decode_subject(token)
        if subject is None:
            raise AuthenticationError("Invalid or expired token.")
        try:
            user_id = int(subject)
        except (TypeError, ValueError):
            raise AuthenticationError("Invalid token subject.")
        user = self._users.get(user_id)
        if user is None:
            raise AuthenticationError("User no longer exists.")
        return user

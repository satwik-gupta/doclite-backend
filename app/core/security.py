"""SecurityManager — password hashing and JWT issuing/verification.

A single class encapsulates all cryptographic concerns so services and routes never
touch passlib/jose directly (encapsulation + SRP).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings


class SecurityManager:
    """Hashes passwords and mints/validates JWT access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # ---- passwords ----------------------------------------------------------

    def hash_password(self, plain: str) -> str:
        return self._pwd.hash(plain)

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return self._pwd.verify(plain, hashed)
        except ValueError:
            return False

    # ---- tokens -------------------------------------------------------------

    def create_access_token(
        self, subject: str, expires_minutes: Optional[int] = None
    ) -> str:
        minutes = expires_minutes or self._settings.access_token_expire_minutes
        expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        payload = {"sub": str(subject), "exp": expire}
        return jwt.encode(
            payload, self._settings.secret_key, algorithm=self._settings.jwt_algorithm
        )

    def decode_subject(self, token: str) -> Optional[str]:
        """Return the ``sub`` claim if the token is valid, else ``None``."""
        try:
            payload = jwt.decode(
                token,
                self._settings.secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )
        except JWTError:
            return None
        return payload.get("sub")

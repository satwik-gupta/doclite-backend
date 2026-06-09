"""Idempotent database seeding.

Creates the schema and a small set of demo users (with documented credentials) plus
a sample shared document so reviewers can immediately exercise roles and sharing.
Safe to run repeatedly: existing users/documents are left untouched.
"""
from __future__ import annotations

from typing import List, Tuple

from app.core.config import Settings, get_settings
from app.core.database import Database, db as default_db
from app.core.security import SecurityManager
from app.domain.enums import Role
from app.models.document import Document
from app.models.share import DocumentShare
from app.models.version import DocumentVersion
from app.repositories.document_repo import DocumentRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

# (username, email, display_name, password)
SEED_USERS: List[Tuple[str, str, str, str]] = [
    ("alice", "alice@doclite.dev", "Alice Owner", "password123"),
    ("bob", "bob@doclite.dev", "Bob Editor", "password123"),
    ("carol", "carol@doclite.dev", "Carol Commenter", "password123"),
    ("dave", "dave@doclite.dev", "Dave Viewer", "password123"),
]

_SAMPLE_HTML = (
    "<h1>Welcome to DocLite</h1>"
    "<p>This is a <strong>sample</strong> document seeded for the demo. "
    "Try <em>editing</em>, <u>formatting</u>, commenting and sharing.</p>"
    "<h2>Things to try</h2>"
    "<ul><li>Format text with the toolbar</li><li>Share with a teammate</li>"
    "<li>Leave a comment on a selection</li></ul>"
    "<ol><li>Open the same doc as two users</li><li>Watch live presence</li></ol>"
)


def seed(settings: Settings | None = None, database: Database | None = None) -> None:
    settings = settings or get_settings()
    database = database or default_db
    database.create_all()

    security = SecurityManager(settings)
    session = database.session_factory()
    try:
        users_repo = UserRepository(session)
        docs_repo = DocumentRepository(session)
        auth = AuthService(users_repo, security)

        created = {}
        for username, email, display_name, password in SEED_USERS:
            existing = users_repo.get_by_username(username)
            if existing:
                created[username] = existing
                continue
            created[username] = auth.register(email, username, display_name, password)
        session.flush()

        # Sample document owned by alice, shared with the others by role — only once.
        alice = created["alice"]
        already = docs_repo.list_owned_by(alice.id)
        if not any(d.title == "Welcome to DocLite" for d in already):
            doc = Document(
                title="Welcome to DocLite",
                content_html=_SAMPLE_HTML,
                owner_id=alice.id,
            )
            docs_repo.add(doc)
            session.add(
                DocumentVersion(
                    document_id=doc.id,
                    version_number=1,
                    title=doc.title,
                    content_html=doc.content_html,
                    author_id=alice.id,
                    label="created",
                )
            )
            session.add_all(
                [
                    DocumentShare(document_id=doc.id, user_id=created["bob"].id, role=Role.EDITOR),
                    DocumentShare(document_id=doc.id, user_id=created["carol"].id, role=Role.COMMENTER),
                    DocumentShare(document_id=doc.id, user_id=created["dave"].id, role=Role.VIEWER),
                ]
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":  # pragma: no cover
    seed()
    print("Seed complete. Users:")
    for username, email, _, password in SEED_USERS:
        print(f"  {username} / {email}  (password: {password})")

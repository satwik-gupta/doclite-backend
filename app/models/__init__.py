"""SQLAlchemy ORM model classes.

Importing this package registers every mapper on ``Base.metadata`` so that
``Database.create_all()`` can build the schema.
"""
from app.models.user import User
from app.models.document import Document
from app.models.share import DocumentShare
from app.models.version import DocumentVersion
from app.models.comment import Comment, CommentReply
from app.models.suggestion import Suggestion

__all__ = [
    "User",
    "Document",
    "DocumentShare",
    "DocumentVersion",
    "Comment",
    "CommentReply",
    "Suggestion",
]

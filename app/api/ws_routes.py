"""WebSocket route for live per-document presence and update signaling.

Auth: the browser passes the JWT as a ``?token=`` query parameter (the WebSocket API
can't set Authorization headers). The handshake is authenticated AND authorized for
VIEW access before the socket joins the room. A short-lived DB session is used only
for that check so the long-lived socket doesn't pin a database connection.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.deps import get_connection_manager
from app.core.config import get_settings
from app.core.database import db
from app.core.exceptions import DocLiteError
from app.core.security import SecurityManager
from app.domain.enums import Action
from app.domain.policy import PermissionPolicy
from app.repositories.document_repo import DocumentRepository
from app.repositories.share_repo import ShareRepository
from app.repositories.user_repo import UserRepository
from app.services.access import AccessGuard
from app.services.auth_service import AuthService

router = APIRouter(tags=["realtime"])


def _authenticate_and_authorize(token: str, document_id: int):
    """Resolve the user and confirm VIEW access using a short-lived session."""
    session = db.session_factory()
    try:
        auth = AuthService(UserRepository(session), SecurityManager(get_settings()))
        user = auth.user_from_token(token)  # raises on invalid/expired token
        guard = AccessGuard(
            DocumentRepository(session), ShareRepository(session), PermissionPolicy()
        )
        guard.require(user, document_id, Action.VIEW)  # raises if no access
        return user
    finally:
        session.close()


@router.websocket("/ws/documents/{document_id}")
async def document_ws(
    websocket: WebSocket,
    document_id: int,
    token: str = Query(default=""),
) -> None:
    await websocket.accept()
    manager = get_connection_manager()

    if not token:
        await websocket.send_json({"type": "error", "message": "Missing token."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = _authenticate_and_authorize(token, document_id)
    except DocLiteError as exc:
        await websocket.send_json({"type": "error", "code": exc.code, "message": exc.message})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    connection = await manager.connect(document_id, websocket, user)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = (data or {}).get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "activity":
                state = (data or {}).get("state", "editing")
                await manager.relay_activity(document_id, connection, state)
            # other client message types are ignored (forward-compatible)
    except WebSocketDisconnect:
        pass
    except Exception:
        # Defensive: never let a socket error crash the worker.
        pass
    finally:
        await manager.disconnect(document_id, connection.connection_id)

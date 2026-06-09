"""ConnectionManager / PresenceManager — live per-document WebSocket presence.

Tracks the set of open WebSocket connections per document and broadcasts:
  * ``presence``         — the current list of distinct present users (sent on every
                           join/leave so clients can simply replace their list);
  * ``user_joined`` / ``user_left`` — transient notifications;
  * ``activity``         — a relayed "X is editing/viewing" signal;
  * ``document_updated`` — emitted when someone saves, so other present users learn a
                           newer version exists without refreshing.

One user may have several connections (multiple tabs); presence de-duplicates by user.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Set

from starlette.websockets import WebSocket


@dataclass
class PresenceConnection:
    connection_id: str
    websocket: WebSocket
    user_id: int
    username: str
    display_name: str


@dataclass
class _Room:
    connections: Dict[str, PresenceConnection] = field(default_factory=dict)


class ConnectionManager:
    """Owns all live document rooms and presence broadcasting."""

    def __init__(self) -> None:
        self._rooms: Dict[int, _Room] = {}
        self._lock = asyncio.Lock()

    # ---- lifecycle ----------------------------------------------------------

    async def connect(
        self, document_id: int, websocket: WebSocket, user
    ) -> PresenceConnection:
        """Register an already-accepted socket and announce the new presence."""
        connection = PresenceConnection(
            connection_id=uuid.uuid4().hex,
            websocket=websocket,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
        )
        async with self._lock:
            room = self._rooms.setdefault(document_id, _Room())
            room.connections[connection.connection_id] = connection

        # Send the current snapshot to the joiner, then tell everyone the new list.
        await self._send(connection, {"type": "presence", "users": self.presence(document_id)})
        await self.broadcast(
            document_id,
            {"type": "user_joined", "user": self._user_dict(connection)},
            exclude=connection.connection_id,
        )
        await self.broadcast(
            document_id, {"type": "presence", "users": self.presence(document_id)}
        )
        return connection

    async def disconnect(self, document_id: int, connection_id: str) -> None:
        async with self._lock:
            room = self._rooms.get(document_id)
            if not room:
                return
            connection = room.connections.pop(connection_id, None)
            if not room.connections:
                self._rooms.pop(document_id, None)
        if connection is None:
            return
        await self.broadcast(
            document_id, {"type": "user_left", "user": self._user_dict(connection)}
        )
        await self.broadcast(
            document_id, {"type": "presence", "users": self.presence(document_id)}
        )

    # ---- queries ------------------------------------------------------------

    def presence(self, document_id: int) -> List[dict]:
        """Distinct present users (deduped across multiple tabs)."""
        room = self._rooms.get(document_id)
        if not room:
            return []
        seen: Dict[int, dict] = {}
        for conn in room.connections.values():
            seen[conn.user_id] = {
                "id": conn.user_id,
                "username": conn.username,
                "display_name": conn.display_name,
            }
        return list(seen.values())

    # ---- broadcasting -------------------------------------------------------

    async def broadcast(self, document_id: int, message: dict, exclude: str | None = None) -> None:
        room = self._rooms.get(document_id)
        if not room:
            return
        dead: Set[str] = set()
        for conn_id, conn in list(room.connections.items()):
            if exclude and conn_id == exclude:
                continue
            try:
                await conn.websocket.send_json(message)
            except Exception:
                dead.add(conn_id)
        for conn_id in dead:
            room.connections.pop(conn_id, None)

    async def relay_activity(self, document_id: int, connection: PresenceConnection, state: str) -> None:
        await self.broadcast(
            document_id,
            {"type": "activity", "user": self._user_dict(connection), "state": state},
            exclude=connection.connection_id,
        )

    async def notify_document_updated(
        self, document_id: int, by_user, label: str = "save"
    ) -> None:
        """Tell present users a newer version exists (called after a save)."""
        await self.broadcast(
            document_id,
            {
                "type": "document_updated",
                "by": {
                    "id": by_user.id,
                    "username": by_user.username,
                    "display_name": by_user.display_name,
                },
                "label": label,
            },
        )

    # ---- helpers ------------------------------------------------------------

    @staticmethod
    async def _send(connection: PresenceConnection, message: dict) -> None:
        try:
            await connection.websocket.send_json(message)
        except Exception:
            pass

    @staticmethod
    def _user_dict(connection: PresenceConnection) -> dict:
        return {
            "id": connection.user_id,
            "username": connection.username,
            "display_name": connection.display_name,
        }

"""WebSocket connection manager.

Manages active WebSocket connections and provides broadcast/send primitives.
Actual event handling will be implemented in later phases.
"""

from fastapi import WebSocket


class ConnectionManager:
    """Tracks active WebSocket connections keyed by user ID.

    Design decisions:
    - One user can have multiple connections (e.g. multiple tabs).
    - Broadcasting iterates all connections; fine for SQLite-scale usage.
    - In a production system this would be backed by Redis pub/sub.
    """

    def __init__(self) -> None:
        # user_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection for a user."""
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)

    async def send_personal(self, user_id: str, message: dict) -> None:
        """Send a JSON message to all connections for a specific user."""
        # Copy the list to avoid modification during iteration
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id, ws)

    async def broadcast(self, message: dict, exclude: str | None = None) -> None:
        """Broadcast a JSON message to all connected users (optionally excluding one)."""
        for uid, connections in list(self._connections.items()):
            if uid == exclude:
                continue
            for ws in list(connections):
                try:
                    await ws.send_json(message)
                except Exception:
                    self.disconnect(uid, ws)

    def is_online(self, user_id: str) -> bool:
        """Check if a user has at least one active connection."""
        return bool(self._connections.get(user_id))

    def online_users(self) -> list[str]:
        """Return list of currently connected user IDs."""
        return list(self._connections.keys())


# Singleton instance used across the application
manager = ConnectionManager()

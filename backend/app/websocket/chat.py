"""WebSocket handler for real-time survey progress and chat."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.logging import get_logger
from app.core.security import decode_token
from app.services.cache_service import CacheService

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with survey-specific rooms."""

    def __init__(self):
        # Map: survey_id -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.cache = CacheService()

    async def connect(self, websocket: WebSocket, survey_id: str) -> bool:
        """Authenticate and accept a WebSocket connection."""
        # Extract token from query params
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return False

        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                await websocket.close(code=4001, reason="Invalid token type")
                return False
        except JWTError:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return False

        await websocket.accept()

        if survey_id not in self.active_connections:
            self.active_connections[survey_id] = set()
        self.active_connections[survey_id].add(websocket)

        logger.info("ws_connected", survey_id=survey_id, user_id=payload.get("sub"))
        return True

    def disconnect(self, websocket: WebSocket, survey_id: str) -> None:
        """Remove a WebSocket from the connection pool."""
        if survey_id in self.active_connections:
            self.active_connections[survey_id].discard(websocket)
            if not self.active_connections[survey_id]:
                del self.active_connections[survey_id]
        logger.info("ws_disconnected", survey_id=survey_id)

    async def broadcast_to_survey(self, survey_id: str, message: dict) -> None:
        """Send a message to all connections watching a survey."""
        if survey_id not in self.active_connections:
            return

        dead_connections = set()
        for ws in self.active_connections[survey_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.active_connections[survey_id].discard(ws)

    async def poll_progress(self, websocket: WebSocket, survey_id: str) -> None:
        """Poll Redis cache for progress updates and send to client."""
        try:
            while True:
                progress = await self.cache.get_survey_progress(survey_id)
                if progress:
                    await websocket.send_json(progress)
                    # If completed or failed, stop polling
                    status = progress.get("status", "")
                    if status in ("completed", "failed"):
                        break
                await asyncio.sleep(1)  # Poll every second
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("ws_poll_error", survey_id=survey_id, error=str(e))


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, survey_id: str):
    """WebSocket endpoint for survey progress updates.

    Connect to: ws://host/ws/surveys/{survey_id}?token=<jwt>
    """
    connected = await manager.connect(websocket, survey_id)
    if not connected:
        return

    try:
        # Start polling in background
        poll_task = asyncio.create_task(manager.poll_progress(websocket, survey_id))

        # Listen for client messages (e.g., chat)
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "chat":
                    # Chat messages could be handled here too
                    await websocket.send_json({
                        "type": "chat_ack",
                        "message": "Use the REST API for chat: POST /api/v1/surveys/{survey_id}/chat",
                    })
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        pass
    finally:
        poll_task.cancel()
        manager.disconnect(websocket, survey_id)

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from uuid import UUID
from datetime import datetime, timezone
import json

from app.core.database import async_session_factory
from app.core.deps import get_current_user_ws
from app.websocket.manager import manager
from app.repositories.conversation import ConversationRepository
from app.models.user import User

router = APIRouter(tags=["websocket"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
):
    if not token:
        await websocket.close(code=1008)
        return

    # Authenticate using short-lived session
    async with async_session_factory() as session:
        user = await get_current_user_ws(token, session)

    if not user:
        await websocket.close(code=1008)
        return

    user_id_str = str(user.id)
    await manager.connect(user_id_str, websocket)

    # Mark user online in DB and mark pending receipts as DELIVERED
    try:
        async with async_session_factory() as session:
            db_user = await session.get(User, user.id)
            if db_user:
                db_user.is_online = True
            
            conv_repo = ConversationRepository(session)
            delivered_list = await conv_repo.mark_messages_delivered(user.id)
            await session.commit()

        # If any pending messages were marked DELIVERED, broadcast to members
        for conv_id, msg_id in delivered_list:
            async with async_session_factory() as session:
                conv_repo = ConversationRepository(session)
                members = await conv_repo.get_members(conv_id)
                member_ids = [str(m.user_id) for m in members]

            for mem_id in member_ids:
                if mem_id != user_id_str and manager.is_online(mem_id):
                    await manager.send_personal(mem_id, {
                        "type": "message.delivered",
                        "payload": {
                            "conversation_id": str(conv_id),
                            "message_id": str(msg_id),
                            "user_id": user_id_str,
                        }
                    })

        # Broadcast online presence to others
        await manager.broadcast({
            "type": "presence.updated",
            "payload": {
                "user_id": user_id_str,
                "is_online": True,
            }
        }, exclude=user_id_str)

        while True:
            data = await websocket.receive_text()
            try:
                event = json.loads(data)
                event_type = event.get("type")
                payload = event.get("payload", {})
            except json.JSONDecodeError:
                continue

            # Heartbeat ping
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Typing events
            if event_type in ("typing.started", "typing.stopped"):
                conv_id_raw = payload.get("conversation_id")
                if not conv_id_raw:
                    continue
                try:
                    conv_id = UUID(conv_id_raw)
                except ValueError:
                    continue

                member_ids: list[str] = []
                async with async_session_factory() as session:
                    conv_repo = ConversationRepository(session)
                    if await conv_repo.is_member(conv_id, user.id):
                        members = await conv_repo.get_members(conv_id)
                        member_ids = [str(m.user_id) for m in members]

                for mem_id in member_ids:
                    if mem_id != user_id_str and manager.is_online(mem_id):
                        await manager.send_personal(mem_id, {
                            "type": event_type,
                            "payload": {
                                "conversation_id": str(conv_id),
                                "user_id": user_id_str,
                            }
                        })

            # Read receipts
            elif event_type == "message.read":
                conv_id_raw = payload.get("conversation_id")
                if not conv_id_raw:
                    continue
                try:
                    conv_id = UUID(conv_id_raw)
                    raw_msg_ids = payload.get("message_ids") or []
                    if isinstance(raw_msg_ids, str):
                        raw_msg_ids = [raw_msg_ids]
                    if not raw_msg_ids and payload.get("message_id"):
                        raw_msg_ids = [payload["message_id"]]
                    msg_ids = [UUID(mid) for mid in raw_msg_ids if mid]
                except ValueError:
                    continue

                updated_ids: list[UUID] = []
                member_ids = []
                async with async_session_factory() as session:
                    conv_repo = ConversationRepository(session)
                    if await conv_repo.is_member(conv_id, user.id):
                        updated_ids = await conv_repo.mark_messages_read(conv_id, user.id, msg_ids or None)
                        await session.commit()
                        members = await conv_repo.get_members(conv_id)
                        member_ids = [str(m.user_id) for m in members]

                if updated_ids:
                    for mem_id in member_ids:
                        if mem_id != user_id_str and manager.is_online(mem_id):
                            await manager.send_personal(mem_id, {
                                "type": "message.read",
                                "payload": {
                                    "conversation_id": str(conv_id),
                                    "message_ids": [str(uid) for uid in updated_ids],
                                    "user_id": user_id_str,
                                }
                            })

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        manager.disconnect(user_id_str, websocket)
        if not manager.is_online(user_id_str):
            now_utc = datetime.now(timezone.utc)
            try:
                async with async_session_factory() as session:
                    db_user = await session.get(User, user.id)
                    if db_user:
                        db_user.is_online = False
                        db_user.last_seen = now_utc
                        await session.commit()
            except Exception:
                pass

            await manager.broadcast({
                "type": "presence.updated",
                "payload": {
                    "user_id": user_id_str,
                    "is_online": False,
                    "last_seen": now_utc.isoformat(),
                }
            }, exclude=user_id_str)

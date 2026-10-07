"""Conversations router.

Endpoints:
  GET  /conversations                               - list user's conversations
  POST /conversations/direct                        - get or create a direct conversation
  GET  /conversations/{id}                          - get a conversation (member-only)
  GET  /conversations/{id}/messages                 - get paginated messages (member-only)
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationResponse,
    CreateDirectConversationRequest,
    CreateGroupConversationRequest,
    CreateMessageRequest,
    MessageResponse,
    LatestMessageResponse,
)
from app.services.conversation import ConversationService
from app.repositories.conversation import ConversationRepository
from app.websocket.manager import manager


router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conv_service(db: AsyncSession = Depends(get_db)) -> ConversationService:
    return ConversationService(db)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    """Return all conversations the current user is a member of."""
    conversations = await svc.get_user_conversations(current_user.id)

    # Attach latest_message to each conversation
    result = []
    for conv in conversations:
        latest = await svc.get_latest_message(conv.id)
        conv_dict = ConversationResponse.model_validate(conv)
        if latest:
            conv_dict.latest_message = LatestMessageResponse.model_validate(latest)
        result.append(conv_dict)
    return result


@router.post("/direct", response_model=ConversationResponse, status_code=status.HTTP_200_OK)
async def get_or_create_direct(
    payload: CreateDirectConversationRequest,
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    """Get an existing direct conversation with another user, or create one."""
    conv = await svc.get_or_create_direct(current_user.id, payload.other_user_id)
    # Reload with members for consistent response
    from app.repositories.conversation import ConversationRepository
    conv_repo = ConversationRepository(svc.session)
    conv = await conv_repo.get_by_id(conv.id)
    latest = await svc.get_latest_message(conv.id)
    result = ConversationResponse.model_validate(conv)
    if latest:
        result.latest_message = LatestMessageResponse.model_validate(latest)
    return result


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    """Get a conversation by ID. Caller must be a member."""
    conv = await svc.get_conversation(conversation_id, current_user.id)
    latest = await svc.get_latest_message(conv.id)
    result = ConversationResponse.model_validate(conv)
    if latest:
        result.latest_message = LatestMessageResponse.model_validate(latest)
    return result


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    """Get paginated messages for a conversation. Caller must be a member."""
    return await svc.get_messages(conversation_id, current_user.id, limit=limit, offset=offset)

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: UUID,
    payload: CreateMessageRequest,
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    msg = await svc.create_message(conversation_id, current_user.id, payload.content, payload.message_type)
    msg_resp = MessageResponse.model_validate(msg)
    
    # Broadcast to other members
    conv_repo = ConversationRepository(svc.session)
    members = await conv_repo.get_members(conversation_id)
    msg_dict = msg_resp.model_dump(mode='json')
    
    for member in members:
        if member.user_id != current_user.id and manager.is_online(str(member.user_id)):
            await manager.send_personal(str(member.user_id), {
                "type": "message.created",
                "payload": msg_dict
            })
            
    return msg_resp
@router.post("/{conversation_id}/read", status_code=status.HTTP_200_OK)
async def mark_conversation_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    """Mark unread messages in conversation as read for the current user."""
    updated_ids = await svc.mark_messages_read(conversation_id, current_user.id)
    if updated_ids:
        conv_repo = ConversationRepository(svc.session)
        members = await conv_repo.get_members(conversation_id)
        for member in members:
            if member.user_id != current_user.id and manager.is_online(str(member.user_id)):
                await manager.send_personal(str(member.user_id), {
                    "type": "message.read",
                    "payload": {
                        "conversation_id": str(conversation_id),
                        "message_ids": [str(mid) for mid in updated_ids],
                        "user_id": str(current_user.id),
                    }
                })
    return {"status": "ok", "read_count": len(updated_ids), "message_ids": [str(mid) for mid in updated_ids]}

@router.post("/group", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_group_conversation(
    payload: CreateGroupConversationRequest,
    current_user: User = Depends(get_current_user),
    svc: ConversationService = Depends(get_conv_service),
):
    conv = await svc.create_group(current_user.id, payload.name, payload.member_ids)
    
    conv_repo = ConversationRepository(svc.session)
    conv = await conv_repo.get_by_id(conv.id)
    
    return ConversationResponse.model_validate(conv)

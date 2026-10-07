"""Conversation service.

Business logic layer for conversation and message operations.
Enforces membership checks before returning data.
"""

from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation import ConversationRepository
from app.repositories.user import UserRepository
from app.models.conversation import Conversation
from app.models.message import Message


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conv_repo = ConversationRepository(session)
        self.user_repo = UserRepository(session)

    async def get_user_conversations(self, user_id: UUID) -> list[Conversation]:
        return await self.conv_repo.get_user_conversations(user_id)

    async def get_conversation(self, conversation_id: UUID, caller_id: UUID) -> Conversation:
        """Return a conversation, verifying the caller is a member."""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        is_member = await self.conv_repo.is_member(conversation_id, caller_id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return conv

    async def get_or_create_direct(self, caller_id: UUID, other_user_id: UUID) -> Conversation:
        """Return existing direct conversation or create a new one.

        Prevents self-conversations and validates the target user exists.
        """
        if caller_id == other_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start a conversation with yourself",
            )

        other_user = await self.user_repo.get_by_id(other_user_id)
        if not other_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        existing = await self.conv_repo.find_direct_conversation(caller_id, other_user_id)
        if existing:
            return existing

        return await self.conv_repo.create_direct_conversation(caller_id, other_user_id)

    async def get_messages(
        self,
        conversation_id: UUID,
        caller_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Return paginated messages after verifying membership."""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        is_member = await self.conv_repo.is_member(conversation_id, caller_id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return await self.conv_repo.get_messages(conversation_id, limit=limit, offset=offset)

    async def get_latest_message(self, conversation_id: UUID):
        return await self.conv_repo.get_latest_message(conversation_id)

    async def create_group(self, caller_id: UUID, name: str, member_ids: list[UUID]) -> Conversation:
        if caller_id not in member_ids:
            member_ids.append(caller_id)
            
        for mid in member_ids:
            user = await self.user_repo.get_by_id(mid)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {mid} not found")
                
        return await self.conv_repo.create_group_conversation(caller_id, name, member_ids)

    async def create_message(self, conversation_id: UUID, sender_id: UUID, content: str, message_type: str = "TEXT") -> Message:
        is_member = await self.conv_repo.is_member(conversation_id, sender_id)
        if not is_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            
        return await self.conv_repo.create_message(conversation_id, sender_id, content, message_type)

    async def mark_messages_read(
        self, conversation_id: UUID, user_id: UUID, message_ids: list[UUID] | None = None
    ) -> list[UUID]:
        is_member = await self.conv_repo.is_member(conversation_id, user_id)
        if not is_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return await self.conv_repo.mark_messages_read(conversation_id, user_id, message_ids)

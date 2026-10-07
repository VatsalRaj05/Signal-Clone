"""Conversation repository.

Handles all conversation/message-related DB operations.
"""

from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.user import User


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Conversation queries ──────────────────────────────────────────

    async def get_user_conversations(self, user_id: UUID) -> list[Conversation]:
        """Return all conversations the user is a member of.

        Eagerly loads members (with users) and the latest message so the
        sidebar can render previews without extra round-trips.
        """
        result = await self.session.execute(
            select(Conversation)
            .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
            .where(
                and_(
                    ConversationMember.user_id == user_id,
                    ConversationMember.left_at.is_(None),
                )
            )
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user),
            )
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().unique().all())

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user),
            )
        )
        return result.scalar_one_or_none()

    async def is_member(self, conversation_id: UUID, user_id: UUID) -> bool:
        """Check whether user_id is an active member of the conversation."""
        result = await self.session.execute(
            select(func.count(ConversationMember.id)).where(
                and_(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.user_id == user_id,
                    ConversationMember.left_at.is_(None),
                )
            )
        )
        return (result.scalar() or 0) > 0

    async def find_direct_conversation(self, user_id_a: UUID, user_id_b: UUID) -> Conversation | None:
        """Find an existing DIRECT conversation between exactly two users.

        Uses a subquery that counts how many of the two user IDs are members
        of a given direct conversation.  Only returns a conversation where
        both are members (count == 2).
        """
        # Subquery: conversation IDs where both users are active members
        member_counts = (
            select(
                ConversationMember.conversation_id,
                func.count(ConversationMember.user_id).label("cnt"),
            )
            .join(Conversation, Conversation.id == ConversationMember.conversation_id)
            .where(
                and_(
                    Conversation.type == ConversationType.DIRECT,
                    ConversationMember.user_id.in_([user_id_a, user_id_b]),
                    ConversationMember.left_at.is_(None),
                )
            )
            .group_by(ConversationMember.conversation_id)
            .having(func.count(ConversationMember.user_id) == 2)
        ).subquery()

        result = await self.session.execute(
            select(Conversation).join(member_counts, Conversation.id == member_counts.c.conversation_id)
        )
        return result.scalar_one_or_none()

    async def create_direct_conversation(self, user_id_a: UUID, user_id_b: UUID) -> Conversation:
        """Create a new DIRECT conversation and add both users as members."""
        conv = Conversation(type=ConversationType.DIRECT, created_by_id=user_id_a)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)

        m1 = ConversationMember(conversation_id=conv.id, user_id=user_id_a)
        m2 = ConversationMember(conversation_id=conv.id, user_id=user_id_b)
        self.session.add_all([m1, m2])
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def create_group_conversation(self, creator_id: UUID, name: str, member_ids: list[UUID]) -> Conversation:
        from app.models.conversation_member import MemberRole
        conv = Conversation(type=ConversationType.GROUP, name=name, created_by_id=creator_id)
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)

        m1 = ConversationMember(conversation_id=conv.id, user_id=creator_id, role=MemberRole.ADMIN)
        self.session.add(m1)
        for mid in member_ids:
            if mid != creator_id:
                self.session.add(ConversationMember(conversation_id=conv.id, user_id=mid, role=MemberRole.MEMBER))
        
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def get_members(self, conversation_id: UUID) -> list[ConversationMember]:
        result = await self.session.execute(
            select(ConversationMember).where(ConversationMember.conversation_id == conversation_id)
        )
        return list(result.scalars().all())

    # ── Message queries ───────────────────────────────────────────────

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Return paginated messages for a conversation, newest first.

        The caller should reverse the list for chronological display.
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(
                selectinload(Message.sender),
                selectinload(Message.receipts),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        messages = list(result.scalars().all())
        # Return in chronological order
        messages.reverse()
        return messages

    async def get_latest_message(self, conversation_id: UUID) -> Message | None:
        """Return the most recent message in a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.receipts))
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_message(
        self, conversation_id: UUID, sender_id: UUID, content: str, message_type: str = "TEXT"
    ) -> Message:
        from app.models.message import MessageType
        from app.models.message_receipt import MessageReceipt, ReceiptStatus
        from app.websocket.manager import manager

        mtype = getattr(MessageType, message_type.upper(), MessageType.TEXT)
        msg = Message(
            conversation_id=conversation_id, sender_id=sender_id, content=content, message_type=mtype
        )
        self.session.add(msg)
        
        # update conversation updated_at
        result = await self.session.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = result.scalar_one_or_none()
        if conv:
            conv.updated_at = func.now()
            
        await self.session.flush()
        await self.session.refresh(msg)

        # Create message receipts for other conversation members
        members = await self.get_members(conversation_id)
        for member in members:
            if member.user_id != sender_id:
                is_online = manager.is_online(str(member.user_id))
                receipt = MessageReceipt(
                    message_id=msg.id,
                    user_id=member.user_id,
                    status=ReceiptStatus.DELIVERED if is_online else ReceiptStatus.SENT,
                )
                self.session.add(receipt)

        await self.session.flush()
        
        # Load sender and receipts
        result = await self.session.execute(
            select(Message)
            .where(Message.id == msg.id)
            .options(
                selectinload(Message.sender),
                selectinload(Message.receipts),
            )
        )
        return result.scalar_one()

    async def mark_messages_read(
        self, conversation_id: UUID, user_id: UUID, message_ids: list[UUID] | None = None
    ) -> list[UUID]:
        """Mark receipts as READ for user_id in conversation_id."""
        from app.models.message_receipt import MessageReceipt, ReceiptStatus
        query = (
            select(MessageReceipt)
            .join(Message, Message.id == MessageReceipt.message_id)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    MessageReceipt.user_id == user_id,
                    MessageReceipt.status != ReceiptStatus.READ,
                )
            )
        )
        if message_ids:
            query = query.where(MessageReceipt.message_id.in_(message_ids))

        result = await self.session.execute(query)
        receipts = list(result.scalars().all())
        updated_ids: list[UUID] = []
        for r in receipts:
            r.status = ReceiptStatus.READ
            r.timestamp = func.now()
            updated_ids.append(r.message_id)
        if receipts:
            await self.session.flush()
        return updated_ids

    async def mark_messages_delivered(self, user_id: UUID) -> list[tuple[UUID, UUID]]:
        """Mark SENT receipts as DELIVERED for user_id. Returns [(conversation_id, message_id)]."""
        from app.models.message_receipt import MessageReceipt, ReceiptStatus
        query = (
            select(MessageReceipt, Message.conversation_id)
            .join(Message, Message.id == MessageReceipt.message_id)
            .where(
                and_(
                    MessageReceipt.user_id == user_id,
                    MessageReceipt.status == ReceiptStatus.SENT,
                )
            )
        )
        result = await self.session.execute(query)
        rows = result.all()
        updated: list[tuple[UUID, UUID]] = []
        for r, conv_id in rows:
            r.status = ReceiptStatus.DELIVERED
            r.timestamp = func.now()
            updated.append((conv_id, r.message_id))
        if rows:
            await self.session.flush()
        return updated


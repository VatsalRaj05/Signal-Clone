"""Pydantic schemas for conversations and messages."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.schemas.contact import ContactUserResponse


class MemberResponse(BaseModel):
    """A conversation member, with embedded user profile."""
    id: UUID
    conversation_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    user: ContactUserResponse

    model_config = ConfigDict(from_attributes=True)


class LatestMessageResponse(BaseModel):
    """Minimal message preview used in the conversation list."""
    id: UUID
    sender_id: UUID | None
    content: str
    status: str = "SENT"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Full conversation response including members.

    latest_message is computed by the service layer.
    """
    id: UUID
    type: str
    name: str | None = None
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime
    members: list[MemberResponse]
    latest_message: LatestMessageResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class CreateDirectConversationRequest(BaseModel):
    """Payload for POST /conversations/direct."""
    other_user_id: UUID


class MessageSenderResponse(BaseModel):
    """Minimal sender info embedded in a message."""
    id: UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageReceiptResponse(BaseModel):
    """Message receipt status for a recipient."""
    id: UUID
    message_id: UUID
    user_id: UUID
    status: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Full message response."""
    id: UUID
    conversation_id: UUID
    sender_id: UUID | None
    content: str
    message_type: str
    status: str = "SENT"
    created_at: datetime
    updated_at: datetime
    sender: MessageSenderResponse | None = None
    receipts: list[MessageReceiptResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CreateMessageRequest(BaseModel):
    content: str
    message_type: str = "TEXT"


class CreateGroupConversationRequest(BaseModel):
    name: str
    member_ids: list[UUID]


class AddGroupMemberRequest(BaseModel):
    user_id: UUID

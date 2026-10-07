"""Pydantic schemas for contacts and user search."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserResponse


class ContactUserResponse(BaseModel):
    """Public user profile returned inside a contact."""
    id: UUID
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    is_online: bool
    last_seen: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ContactResponse(BaseModel):
    """Contact edge with embedded contact_user profile."""
    id: UUID
    user_id: UUID
    contact_user_id: UUID
    contact_user: ContactUserResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddContactRequest(BaseModel):
    """Payload for POST /contacts."""
    contact_user_id: UUID

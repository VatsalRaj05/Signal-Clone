from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    phone: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None

class UserResponse(UserBase):
    id: UUID
    is_online: bool
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from datetime import datetime
import enum
from sqlalchemy import ForeignKey, DateTime, func, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base

class MessageType(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    SYSTEM = "SYSTEM"

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.TEXT)
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    sender: Mapped["User"] = relationship(
        "User", back_populates="sent_messages"
    )
    receipts: Mapped[list["MessageReceipt"]] = relationship(
        "MessageReceipt", back_populates="message", cascade="all, delete-orphan"
    )
    
    # Self-referencing relationships
    reply_to_message: Mapped["Message | None"] = relationship(
        "Message", remote_side=[id], back_populates="replies"
    )
    replies: Mapped[list["Message"]] = relationship(
        "Message", back_populates="reply_to_message"
    )

    @property
    def status(self) -> str:
        """Derive aggregate receipt status: READ > DELIVERED > SENT."""
        if not self.receipts:
            return "SENT"
        statuses = [r.status.value if hasattr(r.status, "value") else str(r.status) for r in self.receipts]
        if "READ" in statuses:
            return "READ"
        if "DELIVERED" in statuses:
            return "DELIVERED"
        return "SENT"

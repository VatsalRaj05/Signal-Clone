"""Contact repository.

Handles all contact-related DB operations.
"""

from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.user import User


class ContactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_contacts(self, user_id: UUID) -> list[Contact]:
        """Return all contacts for a user, with the contact_user loaded."""
        result = await self.session.execute(
            select(Contact)
            .where(Contact.user_id == user_id)
            .options(selectinload(Contact.contact_user))
            .order_by(Contact.created_at)
        )
        return list(result.scalars().all())

    async def get_contact(self, user_id: UUID, contact_user_id: UUID) -> Contact | None:
        """Return a specific contact edge, or None."""
        result = await self.session.execute(
            select(Contact).where(
                and_(Contact.user_id == user_id, Contact.contact_user_id == contact_user_id)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID, contact_user_id: UUID) -> Contact:
        """Insert a new contact row."""
        contact = Contact(user_id=user_id, contact_user_id=contact_user_id)
        self.session.add(contact)
        await self.session.flush()
        await self.session.refresh(contact)
        # Eagerly load the related user so callers don't hit lazy-load issues
        await self.session.refresh(contact, attribute_names=["contact_user"])
        return contact

    async def delete(self, user_id: UUID, contact_user_id: UUID) -> bool:
        """Delete a contact edge.  Returns True if it existed."""
        contact = await self.get_contact(user_id, contact_user_id)
        if not contact:
            return False
        await self.session.delete(contact)
        await self.session.flush()
        return True

    async def search_users(self, query: str, exclude_user_id: UUID, limit: int = 20) -> list[User]:
        """Full-text search users by username or display_name.

        Excludes the calling user from results.  Limited to ``limit`` rows.
        """
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(User)
            .where(
                and_(
                    User.id != exclude_user_id,
                    or_(
                        User.username.ilike(pattern),
                        User.display_name.ilike(pattern),
                    ),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

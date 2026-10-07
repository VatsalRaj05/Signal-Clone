"""Contact service.

Business logic layer between the contacts router and the contact repository.
"""

from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contact import ContactRepository
from app.repositories.user import UserRepository
from app.models.contact import Contact
from app.models.user import User


class ContactService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.contact_repo = ContactRepository(session)
        self.user_repo = UserRepository(session)

    async def get_contacts(self, user_id: UUID) -> list[Contact]:
        return await self.contact_repo.get_contacts(user_id)

    async def add_contact(self, user_id: UUID, contact_user_id: UUID) -> Contact:
        # Self-contact guard
        if user_id == contact_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot add yourself as a contact",
            )

        # Target user must exist
        target = await self.user_repo.get_by_id(contact_user_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Duplicate contact guard
        existing = await self.contact_repo.get_contact(user_id, contact_user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contact already exists",
            )

        return await self.contact_repo.create(user_id, contact_user_id)

    async def remove_contact(self, user_id: UUID, contact_user_id: UUID) -> None:
        deleted = await self.contact_repo.delete(user_id, contact_user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found",
            )

    async def search_users(self, query: str, caller_id: UUID) -> list[User]:
        if not query or len(query.strip()) < 1:
            return []
        return await self.contact_repo.search_users(query.strip(), exclude_user_id=caller_id)

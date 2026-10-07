"""Contacts router.

Endpoints:
  GET  /contacts          - list current user's contacts
  POST /contacts          - add a contact
  DELETE /contacts/{id}   - remove a contact
  GET  /users/search?q=   - search users by name/username
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.contact import ContactResponse, AddContactRequest
from app.schemas.user import UserResponse
from app.services.contact import ContactService

router = APIRouter(tags=["contacts"])


def get_contact_service(db: AsyncSession = Depends(get_db)) -> ContactService:
    return ContactService(db)


@router.get("/contacts", response_model=list[ContactResponse])
async def list_contacts(
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(get_contact_service),
):
    """List all contacts for the authenticated user."""
    return await svc.get_contacts(current_user.id)


@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def add_contact(
    payload: AddContactRequest,
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(get_contact_service),
):
    """Add a user to the current user's contact list."""
    return await svc.add_contact(current_user.id, payload.contact_user_id)


@router.delete("/contacts/{contact_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(
    contact_user_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ContactService = Depends(get_contact_service),
):
    """Remove a contact from the current user's contact list."""
    await svc.remove_contact(current_user.id, contact_user_id)

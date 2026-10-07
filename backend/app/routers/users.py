from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.contact import ContactUserResponse
from app.core.deps import get_current_user
from app.core.database import get_db
from app.repositories.user import UserRepository
from app.services.contact import ContactService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_me(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile (e.g. display_name, avatar_url).
    """
    user_repo = UserRepository(db)
    updated_user = await user_repo.update(current_user.id, profile_data.model_dump(exclude_unset=True))
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.get("/search", response_model=list[ContactUserResponse])
async def search_users(
    q: str = Query(..., min_length=1, description="Search query (username or display name)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for users by username or display name.
    Excludes the current user. Does not expose password hashes.
    """
    svc = ContactService(db)
    return await svc.search_users(q, caller_id=current_user.id)

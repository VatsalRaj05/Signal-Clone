from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, VerifyOTPRequest
from app.core.security import verify_password, hash_password, create_access_token

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, user_in: UserCreate) -> dict:
        # Check if username or phone already exists
        if await self.user_repo.get_by_username(user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        if user_in.phone and await self.user_repo.get_by_phone(user_in.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

        hashed_password = hash_password(user_in.password)
        db_user = User(
            username=user_in.username,
            phone=user_in.phone,
            display_name=user_in.display_name,
            avatar_url=user_in.avatar_url,
            password_hash=hashed_password
        )
        user = await self.user_repo.create(db_user)
        
        # MOCK OTP generation for phone registration
        # In a real app, send OTP via SMS here.
        mock_otp = "123456" 
        
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "mock_otp": mock_otp if user.phone else None
        }

    async def verify_otp(self, verify_data: VerifyOTPRequest) -> dict:
        # MOCK OTP Verification
        user = await self.user_repo.get_by_username(verify_data.identifier)
        if not user:
            user = await self.user_repo.get_by_phone(verify_data.identifier)
            
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        if verify_data.otp != "123456":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP"
            )
            
        # Optional: mark phone as verified in DB if we added a flag for it
        # For now, just generate token
        
        access_token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "phone": user.phone,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "is_online": user.is_online,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }
        }

    async def login(self, login_data: LoginRequest) -> dict:
        # Identify if identifier is username or phone
        # We can try username first, then phone
        user = await self.user_repo.get_by_username(login_data.identifier)
        if not user:
            user = await self.user_repo.get_by_phone(login_data.identifier)
            
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect identifier or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect identifier or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Update last_seen
        user = await self.user_repo.update(user.id, {"last_seen": datetime.now(timezone.utc)})
        
        access_token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "phone": user.phone,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "is_online": user.is_online,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            }
        }

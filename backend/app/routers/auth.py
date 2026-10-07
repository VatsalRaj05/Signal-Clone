from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, VerifyOTPRequest, Token, LoginResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user. Returns user_id and mock_otp for phone numbers.
    """
    return await auth_service.register(user_in)

@router.post("/verify", response_model=LoginResponse)
async def verify_otp(
    verify_data: VerifyOTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verify OTP for a user and return an access token.
    (MOCK: use '123456' as OTP)
    """
    return await auth_service.verify_otp(verify_data)

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login with username or phone number and password.
    Returns access token.
    """
    return await auth_service.login(login_data)

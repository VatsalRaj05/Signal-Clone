from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: str | None = None

class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username or phone number")
    password: str

class SendOTPRequest(BaseModel):
    identifier: str = Field(..., description="Username or phone number")

class VerifyOTPRequest(BaseModel):
    identifier: str = Field(..., description="Username or phone number")
    otp: str = Field(..., min_length=6, max_length=6)

class OTPResponse(BaseModel):
    message: str

class LoginResponse(Token):
    user: dict

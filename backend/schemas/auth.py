from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas (what frontend SENDS) ─────────────────────────────────────

class RegisterRequest(BaseModel):
    """Frontend sends this when user registers."""
    email: EmailStr                          # validates email format automatically
    password: str = Field(..., min_length=6) # minimum 6 characters


class LoginRequest(BaseModel):
    """Frontend sends this when user logs in."""
    email: EmailStr
    password: str


# ── Response Schemas (what API SENDS back) ────────────────────────────────────

class TokenResponse(BaseModel):
    """API returns this after successful login."""
    access_token: str
    token_type: str = "bearer"  # standard token type


class UserResponse(BaseModel):
    """API returns this after successful registration."""
    user_id: int
    email: str
    message: str = "Account created successfully"
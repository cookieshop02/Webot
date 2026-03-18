from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.auth.jwt import verify_access_token

# ── OAuth2 Scheme ──────────────────────────────────────────────────────────────
# This tells FastAPI where to look for the token
# "tokenUrl" is the login endpoint that gives out tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Get Current User ───────────────────────────────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    This function runs on every protected route.
    It extracts and verifies the JWT token from the request.
    Returns the user data if token is valid.
    Raises 401 error if token is invalid or missing.
    """
    # Verify the token
    payload = verify_access_token(token)

    # If token is invalid or expired
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user info from token
    user_id = payload.get("user_id")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    return {"user_id": user_id, "email": email}
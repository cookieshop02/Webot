import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# ── JWT Config ─────────────────────────────────────────────────────────────────
# Secret key used to sign tokens — keep this safe in .env
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise EnvironmentError("JWT_SECRET_KEY not found in environment variables.")

ALGORITHM = "HS256"           # hashing algorithm for JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # token expires in 24 hours


# ── Create Token ───────────────────────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    """
    Creates a JWT token with the given data.
    Called after successful login — token is sent to frontend.
    """
    to_encode = data.copy()

    # Add expiry time to token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # Sign and encode the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ── Verify Token ───────────────────────────────────────────────────────────────
def verify_access_token(token: str) -> dict | None:
    """
    Verifies a JWT token and returns the payload if valid.
    Returns None if token is invalid or expired.
    Called on every protected request to verify who the user is.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
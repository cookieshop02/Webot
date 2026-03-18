import logging
import psycopg
import os
from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext

from backend.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from backend.auth.jwt import create_access_token

# ── Logger ─────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ── Password Hashing ───────────────────────────────────────────────────────────
# bcrypt is the industry standard for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Convert plain password to hashed version."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if plain password matches hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

# ── Database Connection ────────────────────────────────────────────────────────
def get_db():
    """Get a fresh database connection."""
    return psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True)

# ── Router ─────────────────────────────────────────────────────────────────────
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# ── POST /auth/register ────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    """
    Creates a new user account.
    Hashes password before saving — never stores plain text password.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Check if email already exists
            cur.execute("SELECT id FROM users WHERE email = %s", (request.email,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered."
                )

            # Hash password before saving
            hashed = hash_password(request.password[:72])

            # Insert new user
            cur.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id",
                (request.email, hashed)
            )
            user_id = cur.fetchone()[0]

            logger.info(f"New user registered: {request.email}")
            return UserResponse(user_id=user_id, email=request.email)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed.")
    finally:
        conn.close()


# ── POST /auth/login ───────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """
    Logs in a user and returns a JWT token.
    Frontend saves this token and sends it with every request.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Find user by email
            cur.execute(
                "SELECT id, email, password FROM users WHERE email = %s",
                (request.email,)
            )
            user = cur.fetchone()

            # Check if user exists and password is correct
            if not user or not verify_password(request.password, user[2]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password."
                )

            # Create JWT token with user info
            token = create_access_token({
                "user_id": user[0],
                "email": user[1],
            })

            logger.info(f"User logged in: {user[1]}")
            return TokenResponse(access_token=token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed.")
    finally:
        conn.close()
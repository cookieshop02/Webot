import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.auth import router as auth_router
from backend.routes.chat import router as chat_router

# ── Load Environment ───────────────────────────────────────────────────────────
load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan (startup & shutdown events) ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Everything before yield runs at STARTUP
    logger.info("🚀 Webot API starting up...")

    # Validate required env vars early so app fails fast if misconfigured
    if not os.getenv("GROQ_API_KEY"):
        raise EnvironmentError("GROQ_API_KEY not found in environment variables.")

    logger.info("✅ Environment variables validated")
    logger.info("✅ Webot API is ready to accept requests")

    yield  # App runs here

    # Everything after yield runs at SHUTDOWN
    logger.info("🛑 Webot API shutting down...")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Webot API",
    description="Backend API for Webot — an AI chatbot powered by LangGraph and Groq",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS Middleware ────────────────────────────────────────────────────────────
# This allows your Streamlit frontend to talk to this FastAPI backend
# Without this, browsers block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",   # Streamlit default port
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],     # allow GET, POST, PUT, DELETE etc.
    allow_headers=["*"],     # allow all headers
)


# ── Register Routers ───────────────────────────────────────────────────────────
# This connects your routes/chat.py endpoints to the main app
app.include_router(auth_router)
app.include_router(chat_router)


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    """Simple health check — confirms API is running."""
    return {
        "status": "ok",
        "message": "Webot API is running 🤖",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check for monitoring."""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
    }
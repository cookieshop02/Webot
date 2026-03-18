import logging
import os
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from backend.auth.dependencies import get_current_user
from fastapi import APIRouter, HTTPException, Depends

from backend.schemas.chat import (
    SendMessageRequest,
    SendMessageResponse,
    NewThreadRequest,
    NewThreadResponse,
    GenerateTitleRequest,
    GenerateTitleResponse,
    HistoryResponse,
    ChatMessage,
)

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from Backend import chatbot

# ── Logger ─────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Router ─────────────────────────────────────────────────────────────────────
# APIRouter is like a mini FastAPI app — groups related endpoints together
router = APIRouter(
    prefix="/chat",       # all endpoints here will start with /chat
    tags=["Chat"],        # groups them nicely in Swagger UI docs
)


# ── POST /chat/new ─────────────────────────────────────────────────────────────
@router.post("/new", response_model=NewThreadResponse)
def create_new_thread(request: NewThreadRequest,current_user: dict = Depends(get_current_user)):
    """
    Called when user clicks 'New Chat'.
    Just acknowledges the new thread ID — no DB write needed,
    LangGraph creates the thread automatically on first message.
    """
    logger.info(f"New thread created: {request.thread_id}")
    return NewThreadResponse(thread_id=request.thread_id,)


# ── POST /chat/send ────────────────────────────────────────────────────────────
@router.post("/send", response_model=SendMessageResponse)
def send_message(request: SendMessageRequest,current_user: dict = Depends(get_current_user)):
    """
    Core endpoint — receives user message, runs LangGraph, returns AI response.
    """
    logger.info(f"Message received for thread: {request.thread_id}")

    # This is the same config you had in frontend.py before
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        # Collect full response from LangGraph stream
        ai_response = ""
        for chunk, metadata in chatbot.stream(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessage) and chunk.content:
                ai_response += chunk.content

        if not ai_response:
            raise HTTPException(status_code=500, detail="Empty response from LLM")

        logger.info(f"Response generated for thread: {request.thread_id}")
        return SendMessageResponse(
            thread_id=request.thread_id,
            response=ai_response,
        )

    except HTTPException:
        raise  # re-raise HTTP exceptions as-is

    except Exception as e:
        logger.error(f"Error processing message for thread {request.thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


# ── GET /chat/history/{thread_id} ──────────────────────────────────────────────
@router.get("/history/{thread_id}", response_model=HistoryResponse)
def get_history(thread_id: str,current_user: dict = Depends(get_current_user)):
    """
    Called when user switches to an existing conversation.
    Loads persisted messages from SQLite via LangGraph checkpointer.
    """
    logger.info(f"Loading history for thread: {thread_id}")

    try:
        state = chatbot.get_state(
            config={"configurable": {"thread_id": thread_id}}
        )
        messages = state.values.get("messages", [])

        result = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            result.append(ChatMessage(role=role, content=msg.content))

        return HistoryResponse(thread_id=thread_id, messages=result)

    except Exception as e:
        logger.error(f"Failed to load history for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not load history: {str(e)}")


# ── POST /chat/title ───────────────────────────────────────────────────────────
@router.post("/title", response_model=GenerateTitleResponse)
def generate_title(request: GenerateTitleRequest,current_user: dict = Depends(get_current_user)):
    """
    Called after the first message to auto-generate a chat title.
    Uses a lightweight LLM call — same logic you had in frontend.py before.
    """
    logger.info("Generating chat title")

    try:
        title_llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",
            max_tokens=16,
            temperature=0.3,
        )
        prompt = (
            f"Generate a short 3-5 word title for a chat that starts with: '{request.first_message}'. "
            "Reply with ONLY the title, no punctuation, no quotes, no explanation."
        )
        response = title_llm.invoke([HumanMessage(content=prompt)])
        title = response.content.strip().strip('"').strip("'")
        return GenerateTitleResponse(title=title if title else request.first_message[:30])

    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        # Not a critical failure — return truncated first message as fallback
        return GenerateTitleResponse(title=request.first_message[:30])
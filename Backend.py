import os
import logging
from typing import TypedDict, Annotated

import sqlite3

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── LLM Setup ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY not found in environment variables.")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=1024,
    max_retries=3,
)

# ── State Schema ──────────────────────────────────────────────────────────────
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ── Nodes ─────────────────────────────────────────────────────────────────────
def chat_node(state: ChatState) -> ChatState:
    """Core LLM node with system prompt, context trimming, and error handling."""
    try:
        system = SystemMessage(content="""
            You are a helpful, concise assistant.
            Always respond in the same language the user writes in.
            If you don't know something, say so clearly.
        """)

        # ✅ Trim to last 4000 tokens to prevent cost blowup on long chats
        trimmed = trim_messages(
            state["messages"],
            max_tokens=4000,
            strategy="last",
            token_counter=llm,
            include_system=True,
        )

        response = llm.invoke([system] + trimmed)

        usage = response.response_metadata.get("token_usage", {})
        logger.info(
            f"LLM response | "
            f"prompt_tokens: {usage.get('prompt_tokens', 'N/A')} | "
            f"completion_tokens: {usage.get('completion_tokens', 'N/A')}"
        )
        return {"messages": [response]}

    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        raise

# ── Checkpointer & Graph ──────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "./chatbot.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

# ✅ Compiled ONCE at startup — never per request
chatbot = graph.compile(checkpointer=checkpointer)

logger.info("✅ Chatbot graph compiled and ready.")
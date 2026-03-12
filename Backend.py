import os   #Lets you read environment variables (like API keys) from the system
import logging  #Built-in Python module for printing structured log messages (info, errors, warnings)
from typing import TypedDict, Annotated  #TypedDict lets you define a dictionary with specific key/value types and Annotated lets you attach extra metadata to a type hint

import psycopg  #Python library to connect to and interact with PostgreSQL databases

from dotenv import load_dotenv  #Loads variables from a .env file
from langchain_groq import ChatGroq  #lets you call Groq-hosted LLMs
from langchain_core.messages import BaseMessage, SystemMessage, trim_messages  #BaseMessage is the base class for all chat messages. SystemMessage is a special message that sets the AI's behavior. trim_messages cuts conversation history to fit within a token limit.
from langgraph.graph import StateGraph, START, END  #StateGraph lets you build a graph of nodes (processing steps). START and END are special built-in entry/exit points.
from langgraph.graph.message import add_messages  #A helper function used as a reducer — it tells LangGraph how to append new messages to the existing list rather than replacing them.
from langgraph.checkpoint.postgres import PostgresSaver  #A checkpointer that saves conversation state to PostgreSQL.

load_dotenv()  #Reads your .env file and loads all key-value pairs into environment variables.

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

# ── Nodes(these are the tasks in the workflow) ─────────────────────────────────────────────────────────────────────
def chat_node(state: ChatState) -> ChatState:
    """Core LLM node with system prompt, context trimming, and error handling."""
    try:
        system = SystemMessage(content="""
            You are a helpful, concise assistant.
            Always respond in the same language the user writes in.
            If you don't know something, say so clearly.
        """)

        # Trim to last 4000 tokens to prevent cost blowup on long chats
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
DB_PATH = os.getenv("DATABASE_URL", "./postgres.db")
conn = psycopg.connect(DB_PATH, autocommit=True)
checkpointer = PostgresSaver(conn)
checkpointer.setup()  

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

# Compiled ONCE at startup — never per request
chatbot = graph.compile(checkpointer=checkpointer)

logger.info("✅ Chatbot graph compiled and ready.")

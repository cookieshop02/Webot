import uuid
import logging
from datetime import datetime

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
import os

from Backend import chatbot

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Webot",
    page_icon="🤖",
    layout="wide",
)

# ── Utility Functions ─────────────────────────────────────────────────────────
def generate_thread_id() -> str:
    return str(uuid.uuid4())

def auto_generate_title(first_message: str) -> str:
    """Ask LLM to generate a short chat title from the first user message."""
    try:
        title_llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",
            max_tokens=16,
            temperature=0.3,
        )
        prompt = (
            f"Generate a short 3-5 word title for a chat that starts with: '{first_message}'. "
            "Reply with ONLY the title, no punctuation, no quotes, no explanation."
        )
        response = title_llm.invoke([HumanMessage(content=prompt)])
        title = response.content.strip().strip('"').strip("'")
        return title if title else first_message[:30]
    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        return first_message[:30]

def reset_chat():
    """Start a brand new conversation thread."""
    new_id = generate_thread_id()
    st.session_state["thread_id"] = new_id
    st.session_state["message_history"] = []
    st.session_state["chat_threads"].insert(0, {
        "id": new_id,
        "label": "New Chat",
        "titled": False,
        "created": datetime.now().strftime("%b %d, %H:%M"),
    })

def load_conversation(thread_id: str) -> list[dict]:
    """Load persisted conversation from checkpointer."""
    try:
        state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
        result = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            result.append({"role": role, "content": msg.content})
        return result
    except Exception as e:
        logger.error(f"Failed to load conversation {thread_id}: {e}")
        st.error("⚠️ Could not load conversation history.")
        return []

def switch_thread(thread: dict):
    """Switch to an existing conversation thread."""
    st.session_state["thread_id"] = thread["id"]
    st.session_state["message_history"] = load_conversation(thread["id"])
    st.session_state["renaming_thread_id"] = None

def rename_thread(thread_id: str, new_label: str):
    """Update the label of a thread by its ID."""
    new_label = new_label.strip()
    if not new_label:
        return
    for thread in st.session_state["chat_threads"]:
        if thread["id"] == thread_id:
            thread["label"] = new_label
            thread["titled"] = True
            break

def delete_thread(thread_id: str):
    """Remove a thread from the sidebar."""
    st.session_state["chat_threads"] = [
        t for t in st.session_state["chat_threads"] if t["id"] != thread_id
    ]
    if st.session_state["thread_id"] == thread_id:
        if st.session_state["chat_threads"]:
            switch_thread(st.session_state["chat_threads"][0])
        else:
            reset_chat()

def export_chat_as_txt(messages: list[dict]) -> str:
    lines = [f"{m['role'].upper()}: {m['content']}" for m in messages]
    return "\n\n".join(lines)

# ── Session State Init ────────────────────────────────────────────────────────
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []
if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = []
if "thread_id" not in st.session_state:
    reset_chat()
if "renaming_thread_id" not in st.session_state:
    st.session_state["renaming_thread_id"] = None
if "total_tokens" not in st.session_state:
    st.session_state["total_tokens"] = 0

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 Webot")
    st.divider()

    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        reset_chat()
        st.rerun()

    # ── Export Button ─────────────────────────────────────────────────────────
    if st.session_state["message_history"]:
        export_text = export_chat_as_txt(st.session_state["message_history"])
        st.download_button(
            label="⬇️ Export Chat",
            data=export_text,
            file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()
    st.subheader("Conversations")

    for thread in st.session_state["chat_threads"]:
        is_active = thread["id"] == st.session_state["thread_id"]
        is_renaming = st.session_state["renaming_thread_id"] == thread["id"]

        if is_renaming:
            new_name = st.text_input(
                "Rename",
                value=thread["label"],
                key=f"rename_input_{thread['id']}",
                label_visibility="collapsed",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅", key=f"confirm_{thread['id']}", use_container_width=True):
                    rename_thread(thread["id"], new_name)
                    st.session_state["renaming_thread_id"] = None
                    st.rerun()
            with col2:
                if st.button("❌", key=f"cancel_{thread['id']}", use_container_width=True):
                    st.session_state["renaming_thread_id"] = None
                    st.rerun()
        else:
            col_btn, col_rename, col_delete = st.columns([6, 1, 1])
            with col_btn:
                label = f"{'▶ ' if is_active else ''}{thread['label']}"
                if st.button(label, key=thread["id"], use_container_width=True):
                    switch_thread(thread)
                    st.rerun()
            with col_rename:
                if st.button("✏️", key=f"rename_{thread['id']}", help="Rename this chat"):
                    st.session_state["renaming_thread_id"] = thread["id"]
                    st.rerun()
            with col_delete:
                if st.button("🗑️", key=f"delete_{thread['id']}", help="Delete this chat"):
                    delete_thread(thread["id"])
                    st.rerun()

    st.divider()
    st.caption(f"🔢 Tokens this session: {st.session_state['total_tokens']:,}")
    st.caption(f"🧵 Thread: `{st.session_state['thread_id'][:8]}...`")

# ── Main Chat UI ──────────────────────────────────────────────────────────────
st.title("💬 Chat")

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Handle New Input ──────────────────────────────────────────────────────────
user_input = st.chat_input("Message the chatbot...")

if user_input:
    user_input = user_input.strip()
    if not user_input:
        st.stop()

    is_first_message = len(st.session_state["message_history"]) == 0

    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    config = {"configurable": {"thread_id": st.session_state["thread_id"]}}

    with st.chat_message("assistant"):
        try:
            ai_response = st.write_stream(
                chunk.content
                for chunk, metadata in chatbot.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                    stream_mode="messages",
                )
                if isinstance(chunk, AIMessage) and chunk.content
            )
            st.session_state["message_history"].append({
                "role": "assistant",
                "content": ai_response,
            })

            # ✅ Track token usage
            st.session_state["total_tokens"] += len(user_input.split()) + len(ai_response.split())

            # ✅ Auto-rename on first message
            if is_first_message:
                current_id = st.session_state["thread_id"]
                for thread in st.session_state["chat_threads"]:
                    if thread["id"] == current_id and not thread["titled"]:
                        thread["label"] = auto_generate_title(user_input)
                        thread["titled"] = True
                        break
                st.rerun()

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            st.error("⚠️ Something went wrong. Please try again.")
import uuid
import logging
from datetime import datetime

import requests
import streamlit as st

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── API Config ─────────────────────────────────────────────────────────────────
# All requests go to FastAPI now — frontend no longer imports Backend.py
API_BASE_URL = "http://localhost:8000"


# ── API Helper Functions ───────────────────────────────────────────────────────
def api_send_message(thread_id: str, message: str) -> str | None:
    """Send a message to FastAPI and get AI response."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/send",
            json={"thread_id": thread_id, "message": message},
            timeout=30,
        )
        response.raise_for_status()  # raises exception if status is 4xx or 5xx
        return response.json()["response"]
    except requests.exceptions.Timeout:
        st.error("⚠️ Request timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to API. Is the backend running?")
        return None
    except Exception as e:
        logger.error(f"API send message error: {e}")
        st.error("⚠️ Something went wrong. Please try again.")
        return None


def api_get_history(thread_id: str) -> list[dict]:
    """Load conversation history from FastAPI."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/chat/history/{thread_id}",
            timeout=10,
        )
        response.raise_for_status()
        messages = response.json()["messages"]
        return [{"role": m["role"], "content": m["content"]} for m in messages]
    except Exception as e:
        logger.error(f"API get history error: {e}")
        st.error("⚠️ Could not load conversation history.")
        return []


def api_generate_title(first_message: str) -> str:
    """Ask FastAPI to generate a chat title."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/title",
            json={"first_message": first_message},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["title"]
    except Exception as e:
        logger.warning(f"API title generation error: {e}")
        return first_message[:30]  # fallback


def api_new_thread(thread_id: str):
    """Notify FastAPI of a new thread creation."""
    try:
        requests.post(
            f"{API_BASE_URL}/chat/new",
            json={"thread_id": thread_id},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"API new thread error: {e}")


# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Webot",
    page_icon="🤖",
    layout="wide",
)


# ── Utility Functions ─────────────────────────────────────────────────────────
def generate_thread_id() -> str:
    return str(uuid.uuid4())


def reset_chat():
    """Start a brand new conversation thread."""
    new_id = generate_thread_id()
    st.session_state["thread_id"] = new_id
    st.session_state["message_history"] = []
    api_new_thread(new_id)  # notify API
    st.session_state["chat_threads"].insert(0, {
        "id": new_id,
        "label": "New Chat",
        "titled": False,
        "created": datetime.now().strftime("%b %d, %H:%M"),
    })


def switch_thread(thread: dict):
    """Switch to an existing conversation thread."""
    st.session_state["thread_id"] = thread["id"]
    st.session_state["message_history"] = api_get_history(thread["id"])  # calls API now
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

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Calls FastAPI instead of LangGraph directly
            ai_response = api_send_message(
                thread_id=st.session_state["thread_id"],
                message=user_input,
            )

        if ai_response:
            st.markdown(ai_response)
            st.session_state["message_history"].append({
                "role": "assistant",
                "content": ai_response,
            })

            # Track token usage
            st.session_state["total_tokens"] += len(user_input.split()) + len(ai_response.split())

            # Auto-rename on first message
            if is_first_message:
                current_id = st.session_state["thread_id"]
                for thread in st.session_state["chat_threads"]:
                    if thread["id"] == current_id and not thread["titled"]:
                        thread["label"] = api_generate_title(user_input)  # calls API now
                        thread["titled"] = True
                        break
                st.rerun()
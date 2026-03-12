# 🤖 Webot

> A **production-ready conversational AI chatbot** built with **LangGraph**, **Groq LLM**, and **Streamlit** — featuring persistent multi-thread memory, real-time streaming, auto-generated chat titles, and a clean ChatGPT-style interface.

![Status](https://img.shields.io/badge/Status-Work_In_Progress-yellow)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red?logo=streamlit)
![LangGraph](https://img.shields.io/badge/LangGraph-State_Machine-blueviolet)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![SQLite](https://img.shields.io/badge/SQLite-Persistence-lightblue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📌 Table of Contents

- [About the Project](#-about-the-project)
- [How It Works](#-how-it-works)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#️-architecture)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Usage](#-usage)
- [Roadmap](#️-roadmap)
- [Contributing](#-contributing)

---

## 📖 About the Project

**Webot** is a full-featured AI chatbot application that goes beyond a basic LLM wrapper. It manages **multiple independent conversation threads**, each with its own persistent memory stored in a local SQLite database — so your chats survive page refreshes and app restarts.

The backend is powered by **LangGraph**, a state machine framework that structures the conversation flow as a compiled graph. This makes the architecture scalable, inspectable, and easy to extend with new nodes (tools, RAG, agents, etc.).

On the frontend, **Streamlit** delivers a clean, responsive chat UI with sidebar thread management, real-time streaming responses, token tracking, and chat export — all in a single Python file.

---

## 🧠 How It Works

### Backend — LangGraph State Machine

```
User Message
     │
     ▼
┌──────────────────────────────────────────┐
│              LangGraph Graph             │
│                                          │
│   START ──► chat_node ──► END            │
│                                          │
│   chat_node:                             │
│   1. Attach system prompt                │
│   2. Trim messages to last 4000 tokens   │
│   3. Invoke Groq LLM                     │
│   4. Log token usage                     │
│   5. Return AI response                  │
└──────────────┬───────────────────────────┘
               │
               ▼
     SQLite Checkpointer
   (persists state per thread_id)
```

### Frontend — Streamlit Session Management

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit App                      │
│                                                      │
│  Sidebar                    Main Chat                │
│  ─────────                  ─────────                │
│  ➕ New Chat                 Chat messages rendered   │
│  ⬇️ Export Chat              st.chat_input box        │
│  Thread list                 st.write_stream()        │
│    ▶ Active thread           (real-time streaming)   │
│    ✏️ Rename                                          │
│    🗑️ Delete                                          │
│  Token counter                                       │
│  Thread ID display                                   │
└─────────────────────────────────────────────────────┘
```

Each conversation is identified by a **UUID thread ID**. LangGraph's `SqliteSaver` checkpointer stores the full message history per thread, so switching between conversations loads the exact prior context.

---

## ✨ Features

- 💬 **Multi-thread conversations** — create, switch, rename, and delete independent chat sessions
- 🧠 **Persistent memory** — chats are saved to SQLite and survive restarts
- ⚡ **Real-time streaming** — responses stream token-by-token like ChatGPT
- 🏷️ **Auto-generated titles** — first message automatically generates a smart thread title via LLM
- ✏️ **Rename & delete threads** — full conversation management from the sidebar
- ⬇️ **Export chat** — download any conversation as a `.txt` file
- ✂️ **Context trimming** — automatically trims to last 4,000 tokens to prevent cost blowup
- 🌐 **Multilingual** — responds in whatever language the user writes in
- 📊 **Token tracking** — live session token count displayed in sidebar
- 🔒 **Secure config** — API key loaded from `.env`, never hardcoded

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **LLM** | [Groq](https://groq.com) — `llama-3.1-8b-instant` | Ultra-fast chat inference |
| **Orchestration** | [LangGraph](https://langchain-ai.github.io/langgraph/) | State machine graph for conversation flow |
| **Memory** | [LangGraph SqliteSaver](https://langchain-ai.github.io/langgraph/) | Persistent per-thread checkpointing |
| **Database** | SQLite (`chatbot.db`) | Local storage for chat history |
| **Frontend** | [Streamlit](https://streamlit.io) | Full chat UI with sidebar |
| **LLM Client** | [LangChain Groq](https://python.langchain.com/docs/integrations/chat/groq/) | Groq API wrapper |
| **Language** | Python 3.10+ | Core language |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│                        app.py                                │
│                                                              │
│  Session State:                                              │
│  • message_history  — current thread messages                │
│  • chat_threads     — list of all thread metadata            │
│  • thread_id        — active UUID thread                     │
│  • total_tokens     — running token estimate                 │
└────────────────────────┬─────────────────────────────────────┘
                         │  chatbot.stream() / chatbot.get_state()
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph Backend                         │
│                      Backend.py                              │
│                                                              │
│   StateGraph(ChatState)                                      │
│   START ──► chat_node ──► END                                │
│                                                              │
│   chat_node:                                                 │
│   • System prompt injection                                  │
│   • trim_messages (last 4000 tokens)                         │
│   • llm.invoke()                                             │
│   • Token usage logging                                      │
└────────────────────────┬─────────────────────────────────────┘
                         │  read / write per thread_id
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  SQLite Checkpointer                         │
│                    chatbot.db                                │
│                                                              │
│   Stores full message state per thread_id                    │
│   Enables conversation persistence & resumption             │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      Groq API                                │
│               llama-3.1-8b-instant                           │
│          temp: 0.7 | max_tokens: 1024 | retries: 3           │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Webot/
│
├── Backend.py          # LangGraph graph, LLM setup, SQLite checkpointer
├── app.py              # Streamlit frontend — full chat UI
│
├── chatbot.db          # SQLite database (auto-created on first run)
│
├── .env                # API keys — never commit this
├── .env.example        # Safe template to share
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A free [Groq API key](https://console.groq.com)

---

### 1. Clone the repository

```bash
git clone https://github.com/cookieshop02/Webot.git
cd Webot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key.

### 5. Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` — and start chatting! 🎉

> The SQLite database (`chatbot.db`) is created automatically on first run. No setup needed.

---

## 🔐 Environment Variables

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional — defaults to ./chatbot.db
DB_PATH=./chatbot.db
```

Get your free Groq API key at [console.groq.com](https://console.groq.com).

> ⚠️ Never commit your `.env` file. It is already listed in `.gitignore`.

Commit this as `.env.example`:

```env
GROQ_API_KEY=
DB_PATH=./chatbot.db
```

---

## 💡 Usage

Once the app is running at `http://localhost:8501`:

| Action | How |
|---|---|
| Start a new chat | Click **➕ New Chat** in the sidebar |
| Ask a question | Type in the chat box and press Enter |
| Switch conversations | Click any thread in the sidebar |
| Rename a thread | Click **✏️** next to the thread name |
| Delete a thread | Click **🗑️** next to the thread name |
| Export a chat | Click **⬇️ Export Chat** in the sidebar |
| View token usage | Check the bottom of the sidebar |

Chats are **automatically saved** — close and reopen the app and your conversations will still be there.

---

## Changelog


### v3.0.0
v3 — Migrated to PostgreSQL

### v2.0.0
- Added FastAPI layer as backend API
- Frontend now communicates via REST API
- Separated concerns — frontend, routes, schemas

### v1.0.0
- Initial release
- Streamlit frontend directly connected to LangGraph

## 🤝 Contributing

Contributions are welcome!

```bash
# 1. Fork the repo
# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Commit your changes
git commit -m "Add: your feature description"

# 4. Push and open a Pull Request
git push origin feature/your-feature-name
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">Built with ❤️ by <a href="https://github.com/cookieshop02">cookieshop02</a></p>

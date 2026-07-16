# AURA — Autonomous University Response Assistant

> A free, self-hosted personal AI assistant for college students.
> Built with FastAPI, LangChain, ChromaDB, Ollama, and Next.js.

---

## Architecture

```
User / Telegram
     │
     ▼
Next.js Frontend  ←→  FastAPI Backend
                           │
              ┌────────────┼────────────┐
              │            │            │
         Auth/JWT    LangChain      RAG Engine
              │       Agent           │
              │       (LCEL)      ChromaDB
              │          │         + HuggingFace
              │     Model Router      Embeddings
              │    (llama3.1 / qwen3)
              │
          SQLite/PostgreSQL
          (Users, Tasks, Conversations, Memory)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| AI Orchestration | LangChain (LCEL chains) |
| Local LLM | Ollama — llama3.1 / qwen3 |
| Embeddings | HuggingFace `BAAI/bge-small-en-v1.5` |
| Vector DB | ChromaDB (local persistent) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT via python-jose |
| Notifications | Telegram Bot API |
| Frontend | Next.js + TypeScript + Tailwind CSS |

---

## Prerequisites

1. **Python 3.11+** installed
2. **Ollama** installed → https://ollama.com/download
3. Pull the AI models:
   ```bash
   ollama pull llama3.1
   ollama pull qwen3
   ```
4. **Node.js 18+** for the frontend (Phase 5)

---

## Quick Start (Backend)

```powershell
# 1. Navigate to backend
cd week_8\AURA\backend

# 2. Create virtual environment
py -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
Copy-Item .env.example .env
# Edit .env with your settings (SECRET_KEY, Telegram tokens, etc.)

# 5. Start Ollama (in a separate terminal)
ollama serve

# 6. Start the API server
uvicorn app.main:app --reload
```

API will be available at:
- **Swagger UI:** http://localhost:8000/docs
- **Ollama ping:** http://localhost:8000/chat/ping

---

## API Endpoints

### Authentication
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/token` | Login (get JWT) |
| GET | `/auth/me` | Current user profile |

### Chat (with Memory)
| Method | Path | Description |
|---|---|---|
| POST | `/chat/` | Send message (auto-routes model) |
| GET | `/chat/stream` | SSE streaming response |
| GET | `/chat/conversations` | List conversations |
| POST | `/chat/conversations` | New conversation |
| GET | `/chat/conversations/{id}/messages` | Chat history |
| GET | `/chat/ping` | Ollama health check |

### Documents & RAG
| Method | Path | Description |
|---|---|---|
| POST | `/docs/upload` | Upload PDF/TXT notes |
| GET | `/docs/search?q=...` | Semantic search |
| POST | `/docs/ask` | Ask from your notes |

### Tasks
| Method | Path | Description |
|---|---|---|
| GET | `/tasks/` | List pending tasks |
| POST | `/tasks/` | Create task |
| PATCH | `/tasks/{id}` | Update task |
| DELETE | `/tasks/{id}` | Delete task |
| GET | `/tasks/upcoming` | Due in next 7 days |

---

## Multi-Model Routing

Queries are automatically routed to the best model:

| Query Type | Model |
|---|---|
| General conversation, tasks | `llama3.1` (GENERAL) |
| Code, debugging, algorithms | `qwen3` (CODING) |
| Analysis, reasoning, explanation | `llama3.1` (REASONING) |

To change models, edit `.env`:
```env
GENERAL_MODEL=llama3.1
CODING_MODEL=qwen3
REASONING_MODEL=llama3.1
```

---

## RAG Usage

1. Upload your college notes:
   ```http
   POST /docs/upload
   Content-Type: multipart/form-data
   file=@dbms_notes.pdf
   subject=DBMS
   ```

2. Ask questions grounded in your notes:
   ```http
   POST /docs/ask
   {"question": "Explain normalization from my DBMS notes"}
   ```

---

## Development Phases

- [x] Phase 1: Backend setup, auth, SQLite, Ollama connection
- [x] Phase 2: LangChain LCEL agent, model routing, conversation memory
- [x] Phase 3: RAG pipeline (PDF ingestion → ChromaDB → grounded answers)
- [x] Phase 4: Task management API, Telegram notifications
- [ ] Phase 5: Next.js frontend dashboard
- [ ] Phase 6: Daily AI summaries, Docker deployment

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app + routers
│   ├── api/
│   │   ├── auth.py          # JWT auth endpoints
│   │   ├── chat.py          # Chat + conversation memory
│   │   ├── documents.py     # RAG upload + search + ask
│   │   └── tasks.py         # Task CRUD
│   ├── agents/
│   │   └── aura_agent.py    # LangChain LCEL chains
│   ├── rag/
│   │   └── rag_engine.py    # PDF ingestion + retrieval
│   ├── services/
│   │   ├── auth.py          # JWT + password utils
│   │   ├── conversation.py  # Short-term memory
│   │   └── model_router.py  # Multi-model routing
│   ├── models/
│   │   └── user.py          # SQLAlchemy models
│   ├── database/
│   │   ├── config.py        # Pydantic settings
│   │   └── db.py            # SQLAlchemy session
│   └── notifications/
│       └── telegram.py      # Telegram Bot integration
├── requirements.txt
└── .env.example
```

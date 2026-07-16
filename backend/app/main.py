"""
AURA FastAPI Application
--------------------------
Entry point for the backend server.
Run with: uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat
from app.api import documents, tasks
from app.services.scheduler import scheduler
from app.database.db import Base, engine, SessionLocal
from app.models import user  # noqa: F401 — ensures all models are registered before table creation
from app.models.user import Task
from app.notifications.telegram import send_daily_summary

# ── Logging Setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("aura")

# ── Daily Summary Job ─────────────────────────────────────────────────────────
def job_daily_summary():
    """Generates and sends a daily summary of pending tasks."""
    logger.info("Running daily summary job...")
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        upcoming = now + timedelta(days=1)
        pending_tasks = db.query(Task).filter(
            Task.is_completed == False,
            Task.due_date >= now,
            Task.due_date <= upcoming
        ).all()
        
        if pending_tasks:
            task_lines = [f"- {t.title} (Due: {t.due_date.strftime('%H:%M') if t.due_date else 'Soon'})" for t in pending_tasks]
            summary_text = "You have the following tasks due in the next 24 hours:\n" + "\n".join(task_lines)
        else:
            summary_text = "You have no immediate tasks due in the next 24 hours. Have a great day!"
            
        send_daily_summary(summary_text)
    except Exception as e:
        logger.error(f"Error in daily summary job: {e}")
    finally:
        db.close()

# ── Lifespan Setup ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.add_job(job_daily_summary, "cron", hour=8, minute=0)
    scheduler.start()
    logger.info("APScheduler started for daily summaries.")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("APScheduler shut down.")

# ── Create Database Tables ─────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AURA — Autonomous University Response Assistant",
    description=(
        "Backend API for AURA: a free, self-hosted personal AI assistant for college students. "
        "Powered by local Ollama models, LangChain, ChromaDB, and SQLite."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Allow Next.js dev server and any local origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://192.168.1.37:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/docs", tags=["Documents & RAG"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks & Calendar"])


# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "app": "AURA",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


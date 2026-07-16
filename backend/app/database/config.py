"""
AURA Application Settings
Loads from .env file, with sensible defaults for local development.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Database ───────────────────────────────────────────────────────────────
    # Uses SQLite by default; set to postgresql://... for production
    DATABASE_URL: str = "sqlite:///./aura.db"

    # ── Ollama ─────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Multi-model routing: each task type maps to a local Ollama model name.
    # Ensure the corresponding model is pulled via `ollama pull <name>`.
    GENERAL_MODEL: str = "llama3.1"    # General conversation & task assistance
    CODING_MODEL: str = "qwen3"        # Code generation / debugging
    REASONING_MODEL: str = "llama3.1"  # Logic / reasoning tasks (or deepseek-r1)

    # Convenience alias so existing code using PRIMARY_MODEL still works
    @property
    def PRIMARY_MODEL(self) -> str:
        return self.GENERAL_MODEL

    # ── RAG & Embeddings ───────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 4

    # ── Conversation Memory ────────────────────────────────────────────────────
    MAX_HISTORY_MESSAGES: int = 20   # Messages kept in short-term context

    # ── Telegram Notifications ────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


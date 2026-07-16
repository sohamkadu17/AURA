"""
AURA Documents API (RAG)
------------------------
POST /docs/upload          – Upload a PDF or .txt file; triggers ingestion pipeline
GET  /docs/search?q=...    – Semantic search over uploaded documents
POST /docs/ask             – Ask a question answered from uploaded notes (RAG)
GET  /docs/                – List uploaded documents for the current user
"""
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.conversation import ConversationService
from app.services.model_router import model_router
from app.rag.rag_engine import ingest_file, retrieve_context, get_rag_response
from app.database.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Upload directory (inside the backend dir)
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    filename: str
    chunks_added: int
    message: str

class SearchResult(BaseModel):
    content: str
    source: str
    page: Optional[int] = None

class RAGRequest(BaseModel):
    question: str
    conversation_id: Optional[int] = None

class RAGResponse(BaseModel):
    answer: str
    sources: list[str]
    conversation_id: int


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form(default="General"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF or .txt file and ingest it into ChromaDB.
    The `subject` form field helps organise documents (e.g. "DBMS", "OS").
    """
    # Validate file type
    allowed = {".pdf", ".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(allowed)}",
        )

    # Save to disk (user-scoped directory)
    user_dir = UPLOAD_DIR / str(current_user.id)
    user_dir.mkdir(exist_ok=True)
    save_path = user_dir / file.filename

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        await file.close()

    # Ingest into ChromaDB with metadata
    try:
        chunks = ingest_file(
            str(save_path),
            metadata={
                "user_id": str(current_user.id),
                "subject": subject,
                "filename": file.filename,
            },
        )
    except Exception as e:
        logger.error(f"[Docs] Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return UploadResponse(
        filename=file.filename,
        chunks_added=chunks,
        message=f"✅ '{file.filename}' ingested successfully into {chunks} chunks under subject '{subject}'.",
    )


@router.get("/search", response_model=list[SearchResult])
def search_documents(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search over uploaded documents for the current user.
    Returns the most relevant text chunks.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query 'q' cannot be empty.")

    try:
        docs = retrieve_context(q, user_filter={"user_id": str(current_user.id)})
    except Exception as e:
        logger.error(f"[Docs] Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return [
        SearchResult(
            content=doc.page_content,
            source=doc.metadata.get("filename", doc.metadata.get("source", "unknown")),
            page=doc.metadata.get("page"),
        )
        for doc in docs
    ]


@router.post("/ask", response_model=RAGResponse)
def ask_from_notes(
    request: RAGRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ask a question and get an answer grounded in your uploaded notes (RAG).
    The response cites which documents were used.
    """
    svc = ConversationService(db)
    conversation = svc.get_or_create_conversation(current_user.id, request.conversation_id)
    history = svc.get_history(conversation.id)

    # Route to appropriate model
    model_name, _ = model_router.route(request.question)

    # Persist user message
    svc.add_message(conversation.id, role="user", content=request.question)

    answer, sources = get_rag_response(
        question=request.question,
        history=history,
        model_name=model_name,
        user_filter={"user_id": str(current_user.id)},
    )

    # Persist assistant answer
    svc.add_message(
        conversation.id,
        role="assistant",
        content=answer,
        model_used=model_name,
        task_type="rag",
    )

    return RAGResponse(
        answer=answer,
        sources=sources,
        conversation_id=conversation.id,
    )

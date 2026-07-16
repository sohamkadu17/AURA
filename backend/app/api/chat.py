"""
AURA Chat API
-------------
POST /chat/                      - Send a message, get AI response (with memory)
GET  /chat/conversations          - List all conversations for the current user
POST /chat/conversations          - Create a new conversation
GET  /chat/conversations/{id}     - Get message history for a conversation
GET  /chat/ping                   - Check if Ollama is reachable
GET  /chat/stream                 - Server-Sent Events streaming endpoint (optional)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.conversation import ConversationService
from app.agents.aura_agent import get_response, stream_response
from app.database.config import settings
from app.services.scheduler import scheduler
from app.notifications.telegram import send_notification
import re
from datetime import datetime

import ollama as ollama_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None  # None = start new conversation

class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    model_used: str
    task_type: str

class ConversationOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True

class ConversationUpdate(BaseModel):
    title: str

class MessageOut(BaseModel):
    role: str
    content: str
    model_used: Optional[str]
    task_type: Optional[str]

    class Config:
        from_attributes = True


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Main chat endpoint.
    1. Gets or creates a conversation (short-term memory session).
    2. Loads the last N messages as context.
    3. Routes to the correct Ollama model via ModelRouter.
    4. Persists both the user message and AI reply.
    5. Returns the response with metadata.
    """
    svc = ConversationService(db)

    # Get or create a conversation (memory session)
    conversation = svc.get_or_create_conversation(
        user_id=current_user.id,
        conversation_id=request.conversation_id,
    )

    # Auto-title the conversation from the first message
    if conversation.title == "New conversation":
        short_title = request.message[:60] + ("…" if len(request.message) > 60 else "")
        conversation.title = short_title
        db.commit()

    # Load short-term memory (last N messages)
    history = svc.get_history(conversation.id)

    # Persist user message
    svc.add_message(conversation.id, role="user", content=request.message)

    # Call the LangChain agent
    response_text, model_name, task_type = get_response(request.message, history)

    # Post-process for alarms
    match = re.search(r"\[ALARM:\s*([^|]+)\|\s*(.+?)\]", response_text)
    if match:
        time_str = match.group(1).strip()
        msg = match.group(2).strip()
        try:
            # Handle YYYY-MM-DD HH:MM
            run_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            scheduler.add_job(send_notification, "date", run_date=run_time, args=[msg])
            logger.info(f"[Chat] Scheduled alarm for {run_time}: {msg}")
            # Replace the command block with a user-friendly confirmation
            response_text = re.sub(r"\[ALARM:.*?\]", f"⏰ *Alarm scheduled for {time_str}!*", response_text).strip()
        except Exception as e:
            logger.error(f"[Chat] Failed to schedule alarm: {e}")

    # Persist assistant reply with routing metadata
    svc.add_message(
        conversation.id,
        role="assistant",
        content=response_text,
        model_used=model_name,
        task_type=task_type,
    )

    logger.info(f"[Chat] user={current_user.username} conv={conversation.id} model={model_name}")

    return ChatResponse(
        response=response_text,
        conversation_id=conversation.id,
        model_used=model_name,
        task_type=task_type,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all conversations for the authenticated user."""
    return ConversationService(db).list_conversations(current_user.id)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Explicitly start a fresh conversation (clears short-term memory context)."""
    return ConversationService(db).create_conversation(current_user.id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation."""
    svc = ConversationService(db)
    success = svc.delete_conversation(conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def rename_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a conversation."""
    svc = ConversationService(db)
    conv = svc.update_conversation_title(conversation_id, current_user.id, update_data.title)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return full message history for a conversation."""
    svc = ConversationService(db)
    conv = svc.get_conversation(conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv.messages


@router.get("/stream")
def stream_chat(
    message: str,
    conversation_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events streaming endpoint.
    Usage: GET /chat/stream?message=hello&conversation_id=1
    The frontend can consume this with EventSource.
    """
    svc = ConversationService(db)
    conversation = svc.get_or_create_conversation(current_user.id, conversation_id)
    history = svc.get_history(conversation.id)
    svc.add_message(conversation.id, role="user", content=message)

    def event_generator():
        full_response = []
        for chunk in stream_response(message, history):
            full_response.append(chunk)
            yield f"data: {chunk}\n\n"
        full_text = "".join(full_response)
        
        # Post-process for alarms
        match = re.search(r"\[ALARM:\s*([^|]+)\|\s*(.+?)\]", full_text)
        if match:
            time_str = match.group(1).strip()
            msg = match.group(2).strip()
            try:
                run_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                scheduler.add_job(send_notification, "date", run_date=run_time, args=[msg])
                logger.info(f"[Chat Stream] Scheduled alarm for {run_time}: {msg}")
                # Replace the command block with a user-friendly confirmation in the database
                full_text = re.sub(r"\[ALARM:.*?\]", f"\n\n⏰ *Alarm scheduled for {time_str}!*", full_text).strip()
            except Exception as e:
                logger.error(f"[Chat Stream] Failed to schedule alarm: {e}")
                
        # Persist the full streamed response
        svc.add_message(conversation.id, role="assistant", content=full_text)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/ping")
def ping_ollama():
    """Health-check: verify Ollama is running and return available models."""
    try:
        client = ollama_client.Client(host=settings.OLLAMA_BASE_URL)
        models_resp = client.list()
        model_names = [m["model"] for m in models_resp.get("models", [])]
        return {"status": "ok", "ollama_url": settings.OLLAMA_BASE_URL, "models": model_names}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


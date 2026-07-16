"""
AURA Conversation Memory Service
---------------------------------
Manages short-term conversation memory stored in the SQL database.

Short-term memory = the rolling window of messages in the current conversation.
This is what gets injected as context into every LLM call.

Usage:
    svc = ConversationService(db)
    conv = svc.get_or_create_conversation(user_id, conversation_id)
    svc.add_message(conv.id, role="user", content="hello")
    history = svc.get_history(conv.id)  # list of {role, content} dicts
"""

from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import Conversation, Message
from app.database.config import settings


class ConversationService:
    """Handles conversation creation and message persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Conversations ──────────────────────────────────────────────────────────

    def create_conversation(self, user_id: int, title: str = "New conversation") -> Conversation:
        """Create and persist a new conversation for the user."""
        conv = Conversation(user_id=user_id, title=title)
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Fetch a conversation belonging to the given user."""
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def get_or_create_conversation(
        self, user_id: int, conversation_id: Optional[int] = None
    ) -> Conversation:
        """Return an existing conversation or create a new one."""
        if conversation_id:
            conv = self.get_conversation(conversation_id, user_id)
            if conv:
                return conv
        return self.create_conversation(user_id)

    def list_conversations(self, user_id: int) -> list[Conversation]:
        """List all conversations for a user, newest first."""
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .all()
        )

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """Delete a conversation and all its messages."""
        conv = self.get_conversation(conversation_id, user_id)
        if not conv:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True

    def update_conversation_title(self, conversation_id: int, user_id: int, new_title: str) -> Optional[Conversation]:
        """Rename a conversation."""
        conv = self.get_conversation(conversation_id, user_id)
        if not conv:
            return None
        conv.title = new_title
        self.db.commit()
        self.db.refresh(conv)
        return conv

    # ── Messages ───────────────────────────────────────────────────────────────

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Message:
        """Persist a message to the database."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            task_type=task_type,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_history(self, conversation_id: int) -> list[dict]:
        """
        Return the recent message history for LLM context injection.
        Capped at MAX_HISTORY_MESSAGES to avoid exceeding context windows.
        Returns list of dicts: [{"role": ..., "content": ...}, ...]
        """
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(settings.MAX_HISTORY_MESSAGES)
            .all()
        )
        # Reverse so oldest-first for the LLM
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

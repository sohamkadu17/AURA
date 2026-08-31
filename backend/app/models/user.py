"""
SQLAlchemy models for AURA database.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class User(Base):
    """Registered users of AURA."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete")
    tasks = relationship("Task", back_populates="user", cascade="all, delete")
    memories = relationship("LongTermMemory", back_populates="user", cascade="all, delete")


class Conversation(Base):
    """
    Conversation session — groups messages into a chat thread.
    Short-term memory lives inside each conversation's messages.
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="New conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete", order_by="Message.created_at")


class Message(Base):
    """
    A single chat message inside a conversation.
    role: 'user' | 'assistant' | 'system'
    model_used: which Ollama model answered (populated for assistant messages)
    task_type: which routing category was detected
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)         # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=True)   # e.g. "llama3.1", "qwen3"
    task_type = Column(String(50), nullable=True)     # e.g. "coding", "reasoning"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class Task(Base):
    """
    Assignment / reminder task created by the agent.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    priority = Column(String(20), default="medium")   # 'low' | 'medium' | 'high'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="tasks")


class LongTermMemory(Base):
    """
    Key facts the agent should remember about the user long-term.
    e.g. semester, subjects, preferences, important dates.
    These are stored as structured key-value facts.
    """
    __tablename__ = "long_term_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False)    # e.g. "preference", "schedule", "goal"
    key = Column(String(255), nullable=False)          # e.g. "preferred_language"
    value = Column(Text, nullable=False)              # e.g. "Python"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="memories")

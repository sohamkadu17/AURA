"""
AURA Tasks API — Phase 4
------------------------
CRUD endpoints for the Task Management Agent Tool.

GET    /tasks/           – list all tasks for current user
POST   /tasks/           – create a new task
PATCH  /tasks/{id}       – update a task (e.g. mark complete, change due date)
DELETE /tasks/{id}       – delete a task
GET    /tasks/upcoming   – tasks due in the next N days
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import Task, User
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"  # "low" | "medium" | "high"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    is_completed: Optional[bool] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: str
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_task_or_404(task_id: int, user_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[TaskOut])
def list_tasks(
    include_completed: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all tasks. Pass ?include_completed=true to include done tasks."""
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if not include_completed:
        query = query.filter(Task.is_completed == False)
    return query.order_by(Task.due_date.asc().nullslast()).all()


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new task/reminder."""
    new_task = Task(
        user_id=current_user.id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    logger.info(f"[Tasks] Created: '{task.title}' for user={current_user.username}")
    return new_task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    updates: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update any fields of a task. Also used to mark it complete."""
    task = _get_task_or_404(task_id, current_user.id, db)
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a task permanently."""
    task = _get_task_or_404(task_id, current_user.id, db)
    db.delete(task)
    db.commit()


@router.get("/upcoming", response_model=list[TaskOut])
def get_upcoming_tasks(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return tasks due within the next N days (default 7)."""
    now = datetime.utcnow()
    deadline = now + timedelta(days=days)
    return (
        db.query(Task)
        .filter(
            Task.user_id == current_user.id,
            Task.is_completed == False,
            Task.due_date >= now,
            Task.due_date <= deadline,
        )
        .order_by(Task.due_date.asc())
        .all()
    )

"""
AURA Authentication API
-----------------------
POST /auth/register   create a new AURA account
POST /auth/token      login and get a JWT access token (OAuth2 compatible)
GET  /auth/me         verify token and return current user info
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.db import get_db
from app.models.user import User
from app.services.auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter()


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new AURA user and return a JWT token immediately."""
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate with username/password and receive a JWT (OAuth2 compatible)."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


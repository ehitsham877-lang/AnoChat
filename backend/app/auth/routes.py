from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.auth.service import authenticate_user, get_current_user
from app.common import ensure_roles
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenOut, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    login = payload.login or payload.email
    exists = db.query(User).filter((User.login == login) | (User.email == payload.email)).first()
    if exists:
        raise HTTPException(status_code=409, detail="User already exists")
    roles = ensure_roles(db, payload.roles or ["customer"])
    user = User(
        name=payload.name,
        login=login,
        email=str(payload.email),
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        roles=roles,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.login, payload.password, request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password")
    user.messenger_status = "online"
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(str(user.id)), user=user)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.messenger_status = "offline"
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

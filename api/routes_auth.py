from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db, User
from .auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class SignupRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str = None
    location: str = "Lahore"


def set_auth_cookie(response: Response, jwt_token: str):
    """Set the JWT as an httpOnly cookie instead of returning it in the body.
    samesite='none' + secure=True is required because the frontend (Vercel)
    and backend (HF Spaces) are on different domains."""
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,  # 7 days, matches token expiry below
        path="/",
    )


@router.post("/signup")
def signup(request: SignupRequest, response: Response, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create user
    user = User(
        email=request.email,
        username=request.username,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        location=request.location
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token and set as cookie instead of returning it
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=7),
    )
    set_auth_cookie(response, token)

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }


@router.post("/login")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Accept email OR username
    user = db.query(User).filter(
        (User.email == form_data.username) |
        (User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password"
        )

    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(days=7),
    )
    set_auth_cookie(response, token)

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "location": current_user.location,
        "is_admin": bool(current_user.is_admin),
        "is_active": bool(current_user.is_active),
        "created_at": str(current_user.created_at) if current_user.created_at else None
    }


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    # Clear the cookie server-side — this is the actual "logout" now,
    # since there's no longer a client-stored token to delete.
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out successfully"}


class LoginJSONRequest(BaseModel):
    email: str
    password: str


@router.post("/login-json")
def login_json(request: LoginJSONRequest, response: Response, db: Session = Depends(get_db)):
    """Login with JSON body - clean email/password fields!"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(days=7),
    )
    set_auth_cookie(response, token)

    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": bool(user.is_admin)
    }
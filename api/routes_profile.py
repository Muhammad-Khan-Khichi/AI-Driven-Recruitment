from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database.db import get_db, User
from api.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ─────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    profile_picture: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class SetPasswordRequest(BaseModel):
    new_password: str


class ProfileResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    profile_picture: Optional[str]
    oauth_provider: Optional[str]
    is_active: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────
# GET /api/profile — Get current user's profile
# ─────────────────────────────────────────────────────────────
@router.get("/", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's profile."""
    return current_user


# ─────────────────────────────────────────────────────────────
# PUT /api/profile — Update profile
# ─────────────────────────────────────────────────────────────
@router.put("/", response_model=ProfileResponse)
def update_profile(
    updates: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile."""

    # Update full_name if provided
    if updates.full_name is not None:
        current_user.full_name = updates.full_name.strip()

    # Update username if provided (check uniqueness)
    if updates.username is not None:
        new_username = updates.username.strip()

        if len(new_username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters",
            )

        if not new_username.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username can only contain letters, numbers, underscores, and hyphens",
            )

        existing = (
            db.query(User)
            .filter(User.username == new_username, User.id != current_user.id)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        current_user.username = new_username

    # Update profile picture if provided (URL only, no file uploads)
    if updates.profile_picture is not None:
        url = updates.profile_picture.strip()
        if url == "":
            current_user.profile_picture = None
        elif url.startswith("http://") or url.startswith("https://"):
            current_user.profile_picture = url
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile picture must be a valid URL",
            )

    db.commit()
    db.refresh(current_user)

    return current_user


# ─────────────────────────────────────────────────────────────
# POST /api/profile/change-password — Change password
# ─────────────────────────────────────────────────────────────
@router.post("/change-password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password."""

    if current_user.oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You signed up with {current_user.oauth_provider}. Password change not available.",
        )

    if current_user.hashed_password == "oauth_user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth account detected. Please set a password first.",
        )

    from api.auth import verify_password

    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    from api.auth import get_password_hash

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


# ─────────────────────────────────────────────────────────────
# POST /api/profile/set-password — For OAuth users to set password
# ─────────────────────────────────────────────────────────────
@router.post("/set-password")
def set_password(
    data: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allow OAuth users to set a password for direct login."""

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    from api.auth import get_password_hash

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    return {
        "message": "Password set! You can now log in with email/password too."
    }


# ─────────────────────────────────────────────────────────────
# DELETE /api/profile — Delete account (danger zone)
# ─────────────────────────────────────────────────────────────
@router.delete("/")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the current user's account."""

    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted successfully"}
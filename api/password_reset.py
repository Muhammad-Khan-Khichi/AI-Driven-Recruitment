# api/password_reset.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import hashlib

from database import get_db
from database.db import User
from database.db import PasswordReset
from api.auth import get_password_hash, verify_password, get_current_user
from utils.email import send_reset_password_email
from api.config import RESET_TOKEN_EXPIRE_HOURS, FRONTEND_URL

# ✅ THIS IS THE ROUTER (must be named 'router')
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ==================== Pydantic Models ====================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class VerifyTokenRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str


# ==================== Endpoints ====================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Step 1: User requests password reset
    """

    # Find user
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success (prevents email enumeration)
    if not user:
        return MessageResponse(
            message="If the email exists, a reset link has been sent."
        )

    # Generate secure token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Delete old tokens
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.used == False
    ).delete()

    # Create new reset
    reset = PasswordReset(
        user_id=user.id,
        token=token_hash,
        expires_at=datetime.utcnow() + timedelta(
            hours=RESET_TOKEN_EXPIRE_HOURS  # ✅ FIXED: removed settings.
        ),
        used=False,
        created_at=datetime.utcnow()
    )
    db.add(reset)
    db.commit()

    # Build reset link
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"  # ✅ FIXED: removed settings.

    # Send email
    send_reset_password_email(user.email, reset_link)

    return MessageResponse(
        message="If the email exists, a reset link has been sent."
    )


@router.post("/verify-reset-token")
async def verify_reset_token(
    request: VerifyTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Step 1.5: Verify token is valid
    """

    token_hash = hashlib.sha256(request.token.encode()).hexdigest()

    reset = db.query(PasswordReset).filter(
        PasswordReset.token == token_hash,
        PasswordReset.used == False
    ).first()

    if not reset:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    if datetime.utcnow() > reset.expires_at:
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired"
        )

    user = db.query(User).filter(User.id == reset.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "valid": True,
        "email": user.email,
        "expires_at": reset.expires_at.isoformat()
    }


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2: User submits new password with token
    """

    token_hash = hashlib.sha256(request.token.encode()).hexdigest()

    reset = db.query(PasswordReset).filter(
        PasswordReset.token == token_hash,
        PasswordReset.used == False
    ).first()

    if not reset:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    if datetime.utcnow() > reset.expires_at:
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired"
        )

    user = db.query(User).filter(User.id == reset.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    reset.used = True

    db.commit()

    return MessageResponse(
        message="Password reset successful. You can now log in with your new password."
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password while logged in (requires current password)
    """

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    current_user.hashed_password = get_password_hash(new_password)
    db.commit()

    return MessageResponse(message="Password changed successfully")
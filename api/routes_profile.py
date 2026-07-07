from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from PIL import Image
from io import BytesIO
import os
import uuid

from database.db import get_db, User
from api.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])

# ─────────────────────────────────────────────────────────────
# Avatar Configuration
# ─────────────────────────────────────────────────────────────
ALLOWED_AVATAR_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_DIR = "uploads/avatars"
AVATAR_MAX_DIMENSION = 500
AVATAR_QUALITY = 85

os.makedirs(AVATAR_DIR, exist_ok=True)


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


class AvatarUploadResponse(BaseModel):
    message: str
    avatar_url: str
    user: dict


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
# Helper Functions
# ─────────────────────────────────────────────────────────────
def delete_old_avatar(profile_picture_url: str) -> None:
    """Remove old avatar file from disk if it exists."""
    if profile_picture_url and profile_picture_url.startswith("/uploads/avatars/"):
        filepath = profile_picture_url.lstrip("/")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass


def process_avatar_image(image_bytes: bytes, user_id: int) -> str:
    """Process and save an avatar image, return the URL path."""
    image = Image.open(BytesIO(image_bytes))

    # Convert RGBA → RGB
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        background.paste(
            image,
            mask=image.split()[-1] if image.mode == "RGBA" else None,
        )
        image = background

    # Resize keeping aspect ratio
    image.thumbnail(
        (AVATAR_MAX_DIMENSION, AVATAR_MAX_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    # Center crop to square
    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    image = image.crop((left, top, left + min_dim, top + min_dim))

    # Generate unique filename
    filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(AVATAR_DIR, filename)

    # Save as JPEG
    image.save(filepath, "JPEG", quality=AVATAR_QUALITY, optimize=True)

    return f"/uploads/avatars/{filename}"


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

    # Update profile picture if provided
    if updates.profile_picture is not None:
        url = updates.profile_picture.strip()
        if url == "":
            # Empty string = remove picture
            delete_old_avatar(current_user.profile_picture)
            current_user.profile_picture = None
        elif url.startswith("/uploads/avatars/"):
            # Already an uploaded file
            current_user.profile_picture = url
        elif url.startswith("http://") or url.startswith("https://"):
            current_user.profile_picture = url
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile picture must be a valid URL or uploaded file",
            )

    db.commit()
    db.refresh(current_user)

    return current_user


# ─────────────────────────────────────────────────────────────
# POST /api/profile/avatar/upload — Upload profile picture
# ─────────────────────────────────────────────────────────────
@router.post("/avatar/upload", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload and process profile picture."""
    
    # ─── Validate content type ───
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_AVATAR_TYPES))}",
        )

    # ─── Read file ───
    contents = await file.read()

    # ─── Validate size ───
    if len(contents) > MAX_AVATAR_SIZE:
        size_mb = MAX_AVATAR_SIZE / 1024 / 1024
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {size_mb}MB",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    try:
        # ─── Process and save image ───
        avatar_url = process_avatar_image(contents, current_user.id)

        # ─── Delete old avatar if it was an uploaded file ───
        delete_old_avatar(current_user.profile_picture)

        # ─── Update user record ───
        current_user.profile_picture = avatar_url
        db.commit()
        db.refresh(current_user)

        return {
            "message": "Avatar uploaded successfully",
            "avatar_url": avatar_url,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
                "full_name": current_user.full_name,
                "profile_picture": current_user.profile_picture,
                "oauth_provider": current_user.oauth_provider,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────
# DELETE /api/profile/avatar — Remove profile picture
# ─────────────────────────────────────────────────────────────
@router.delete("/avatar")
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove the user's profile picture."""
    
    delete_old_avatar(current_user.profile_picture)
    current_user.profile_picture = None
    db.commit()

    return {"message": "Avatar removed successfully"}


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
    """Delete the current user's account. Also cleans up avatar."""
    
    # Clean up avatar file
    delete_old_avatar(current_user.profile_picture)

    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted successfully"}
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from database.db import get_db, User
from api.auth import create_access_token
from api.config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET,
    FRONTEND_URL
)
from datetime import timedelta
import uuid

router = APIRouter(prefix="/api/auth", tags=["oauth"])

# Initialize OAuth
oauth = OAuth()

# Register Google
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Register LinkedIn
oauth.register(
    name='linkedin',
    client_id=LINKEDIN_CLIENT_ID,
    client_secret=LINKEDIN_CLIENT_SECRET,
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    userinfo_endpoint='https://api.linkedin.com/v2/userinfo',
    client_kwargs={'scope': 'openid email profile'}
)


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google's OAuth page."""
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    try:
        # Get access token from Google
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from Google
        user_info = token.get('userinfo')
        
        if not user_info:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_failed")
        
        email = user_info.get('email')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        google_id = user_info.get('sub')
        
        if not email:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user from Google data
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            
            # Ensure unique username
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                email=email,
                username=username,
                full_name=name,
                oauth_provider='google',
                oauth_id=google_id,
                profile_picture=picture,
                hashed_password='oauth_user',  # Placeholder for OAuth users
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update OAuth info if not set
            if not user.oauth_provider:
                user.oauth_provider = 'google'
                user.oauth_id = google_id
                user.profile_picture = picture
                db.commit()
        
        # Create JWT token (7 days)
        jwt_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=7)
        )
        
        # Redirect to frontend with token
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={jwt_token}")
    
    except Exception as e:
        print(f"❌ Google OAuth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_failed")


@router.get("/linkedin/login")
async def linkedin_login(request: Request):
    """Redirect to LinkedIn's OAuth page."""
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/linkedin/callback"
    return await oauth.linkedin.authorize_redirect(request, redirect_uri)


@router.get("/linkedin/callback")
async def linkedin_callback(request: Request, db: Session = Depends(get_db)):
    """Handle LinkedIn OAuth callback."""
    try:
        # Get access token from LinkedIn
        token = await oauth.linkedin.authorize_access_token(request)
        
        # Get user info from LinkedIn
        resp = await oauth.linkedin.get('userinfo', token=token)
        user_info = resp.json()
        
        if not user_info:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=linkedin_failed")
        
        email = user_info.get('email')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        linkedin_id = user_info.get('sub')
        
        if not email:
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user from LinkedIn data
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            
            # Ensure unique username
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                email=email,
                username=username,
                full_name=name,
                oauth_provider='linkedin',
                oauth_id=linkedin_id,
                profile_picture=picture,
                hashed_password='oauth_user',
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update OAuth info if not set
            if not user.oauth_provider:
                user.oauth_provider = 'linkedin'
                user.oauth_id = linkedin_id
                user.profile_picture = picture
                db.commit()
        
        # Create JWT token (7 days)
        jwt_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=7)
        )
        
        # Redirect to frontend with token
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={jwt_token}")
    
    except Exception as e:
        print(f"❌ LinkedIn OAuth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=linkedin_failed")
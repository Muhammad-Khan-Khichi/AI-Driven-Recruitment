import httpx
import os
import logging
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

router = APIRouter(prefix="/api/auth", tags=["oauth"])

# Initialize OAuth
oauth = OAuth()

# ✅ Register Google — uses OpenID Connect discovery (works perfectly)
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ✅ Register LinkedIn — uses OpenID Connect discovery (proper config)
oauth.register(
    name='linkedin',
    client_id=LINKEDIN_CLIENT_ID,
    client_secret=LINKEDIN_CLIENT_SECRET,
    server_metadata_url='https://www.linkedin.com/oauth/v2/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


def _get_redirect_uri(request: Request, provider: str) -> str:
    """Build accurate OAuth callback URL from the actual request."""
    return f"{request.url.scheme}://{request.url.netloc}/api/auth/{provider}/callback"


def _get_or_create_user(db: Session, email: str, name: str, picture: str, 
                        provider_id: str, provider: str) -> User:
    """Find existing user or create new one from OAuth data."""
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Generate unique username
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            email=email,
            username=username,
            full_name=name,
            oauth_provider=provider,
            oauth_id=provider_id,
            profile_picture=picture,
            hashed_password='oauth_user',
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update OAuth info if missing
        if not user.oauth_provider:
            user.oauth_provider = provider
            user.oauth_id = provider_id
            user.profile_picture = picture
            db.commit()

    return user


# ─────────────────────────────────────────────────────────────
# GOOGLE
# ─────────────────────────────────────────────────────────────
@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google's OAuth page."""
    redirect_uri = _get_redirect_uri(request, 'google')
    print(f"🔍 Google login initiated. Redirect URI: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    try:
        # ✅ DEBUG: Show what we received
        print(f"═══════════════════════════════════════════")
        print(f"🔍 GOOGLE CALLBACK")
        print(f"🔍 Cookies: {dict(request.cookies)}")
        if hasattr(request, 'session'):
            print(f"🔍 Session: {dict(request.session)}")
        print(f"🔍 Query: code={bool(request.query_params.get('code'))}, "
              f"state={bool(request.query_params.get('state'))}")
        print(f"═══════════════════════════════════════════")

        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            print(f"❌ No userinfo in token response")
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_failed")

        email     = user_info.get('email')
        name      = user_info.get('name', '')
        picture   = user_info.get('picture', '')
        google_id = user_info.get('sub')

        if not email:
            print(f"❌ No email in userinfo: {user_info}")
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")

        print(f"✅ Google user: {email}")

        user = _get_or_create_user(db, email, name, picture, google_id, 'google')

        jwt_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=7)
        )

        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={jwt_token}")

    except Exception as e:
        print(f"❌ Google OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=google_failed")


# ─────────────────────────────────────────────────────────────
# LINKEDIN — uses Authlib for both authorize AND token exchange
# ─────────────────────────────────────────────────────────────
@router.get("/linkedin/login")
async def linkedin_login(request: Request):
    """Redirect to LinkedIn's OAuth page."""
    redirect_uri = _get_redirect_uri(request, 'linkedin')
    print(f"🔍 LinkedIn login initiated. Redirect URI: {redirect_uri}")
    return await oauth.linkedin.authorize_redirect(request, redirect_uri)


@router.get("/linkedin/callback")
async def linkedin_callback(request: Request, db: Session = Depends(get_db)):
    """Handle LinkedIn OAuth callback."""
    try:
        # ✅ DEBUG: Show what we received
        print(f"═══════════════════════════════════════════")
        print(f"🔍 LINKEDIN CALLBACK")
        print(f"🔍 Cookies: {dict(request.cookies)}")
        if hasattr(request, 'session'):
            print(f"🔍 Session: {dict(request.session)}")
        print(f"🔍 Query: code={bool(request.query_params.get('code'))}")
        print(f"═══════════════════════════════════════════")

        # ✅ Use Authlib for token exchange (handles client_secret automatically)
        token = await oauth.linkedin.authorize_access_token(request)
        access_token = token.get('access_token')

        if not access_token:
            print(f"❌ No access_token in response: {token}")
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=linkedin_failed")

        # ✅ Fetch user info using the access token
        userinfo_response = httpx.get(
            'https://api.linkedin.com/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if userinfo_response.status_code != 200:
            print(f"❌ LinkedIn userinfo failed: {userinfo_response.text}")
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=linkedin_failed")

        user_info = userinfo_response.json()
        print(f"✅ LinkedIn user info: {user_info}")

        email       = user_info.get('email')
        name        = user_info.get('name', '')
        picture     = user_info.get('picture', '')
        linkedin_id = user_info.get('sub')

        if not email:
            print(f"❌ No email in userinfo")
            return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")

        user = _get_or_create_user(db, email, name, picture, linkedin_id, 'linkedin')

        jwt_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=7)
        )

        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={jwt_token}")

    except Exception as e:
        print(f"❌ LinkedIn OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=linkedin_failed")
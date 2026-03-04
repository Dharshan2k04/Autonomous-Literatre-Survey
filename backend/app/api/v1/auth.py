"""Auth API routes — registration, login, OAuth, token refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.oauth import oauth
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserWithToken,
)
from app.services.auth_service import AuthService

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=UserWithToken, status_code=201)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    service = AuthService(db)
    return await service.register(
        email=body.email, password=body.password, full_name=body.full_name
    )


@router.post("/login", response_model=UserWithToken)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    service = AuthService(db)
    return await service.login(email=body.email, password=body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    service = AuthService(db)
    return await service.refresh_tokens(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return UserResponse.model_validate(current_user)


# ---- Google OAuth ----

@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth login."""
    if not settings.has_google_oauth:
        return {"error": "Google OAuth not configured"}
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback."""
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo", {})

    service = AuthService(db)
    result = await service.oauth_login(
        provider="google",
        provider_id=user_info.get("sub", ""),
        email=user_info.get("email", ""),
        full_name=user_info.get("name", ""),
        avatar_url=user_info.get("picture"),
    )

    # Redirect to frontend with token
    frontend_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else "http://localhost:5173"
    return RedirectResponse(
        url=f"{frontend_url}/auth/callback?access_token={result.tokens.access_token}"
        f"&refresh_token={result.tokens.refresh_token}"
    )


# ---- GitHub OAuth ----

@router.get("/github/login")
async def github_login(request: Request):
    """Redirect to GitHub OAuth login."""
    if not settings.has_github_oauth:
        return {"error": "GitHub OAuth not configured"}
    redirect_uri = settings.GITHUB_REDIRECT_URI
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback")
async def github_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle GitHub OAuth callback."""
    token = await oauth.github.authorize_access_token(request)

    # Get user info from GitHub API
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        user_info = resp.json()

        # Get email (may need separate call if private)
        email = user_info.get("email")
        if not email:
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            emails = email_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            email = primary["email"] if primary else f"{user_info['login']}@github.noemail"

    service = AuthService(db)
    result = await service.oauth_login(
        provider="github",
        provider_id=str(user_info.get("id", "")),
        email=email,
        full_name=user_info.get("name") or user_info.get("login", ""),
        avatar_url=user_info.get("avatar_url"),
    )

    frontend_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else "http://localhost:5173"
    return RedirectResponse(
        url=f"{frontend_url}/auth/callback?access_token={result.tokens.access_token}"
        f"&refresh_token={result.tokens.refresh_token}"
    )

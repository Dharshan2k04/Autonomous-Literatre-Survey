"""Authentication service — user creation, login, OAuth handling."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse, UserWithToken

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """Handles user authentication and registration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, password: str, full_name: str) -> UserWithToken:
        """Register a new user with email/password."""
        existing = await self._get_user_by_email(email)
        if existing:
            raise ConflictError(f"User with email '{email}' already exists")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        logger.info("user_registered", user_id=str(user.id), email=email)
        return self._build_user_with_token(user)

    async def login(self, email: str, password: str) -> UserWithToken:
        """Authenticate user with email/password."""
        user = await self._get_user_by_email(email)
        if not user or not user.hashed_password:
            raise AuthenticationError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        logger.info("user_logged_in", user_id=str(user.id), method="password")
        return self._build_user_with_token(user)

    async def oauth_login(
        self,
        provider: str,
        provider_id: str,
        email: str,
        full_name: str,
        avatar_url: str | None = None,
    ) -> UserWithToken:
        """Handle OAuth login/registration."""
        user = await self._get_user_by_email(email)

        if user is None:
            # Auto-register OAuth user
            user = User(
                email=email,
                full_name=full_name,
                oauth_provider=provider,
                oauth_provider_id=provider_id,
                avatar_url=avatar_url,
            )
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            logger.info("oauth_user_registered", user_id=str(user.id), provider=provider)
        else:
            # Update OAuth info if needed
            if not user.oauth_provider:
                user.oauth_provider = provider
                user.oauth_provider_id = provider_id
            if avatar_url:
                user.avatar_url = avatar_url
            await self.db.flush()
            logger.info("oauth_user_logged_in", user_id=str(user.id), provider=provider)

        return self._build_user_with_token(user)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Issue new tokens using a valid refresh token."""
        payload = decode_token(refresh_token)
        if payload is None:
            raise AuthenticationError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        user = await self._get_user_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        return self._create_tokens(user.id)

    async def get_current_user(self, user_id: UUID) -> User:
        """Get user by ID (used in auth dependency)."""
        user = await self._get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return user

    # ---- Private helpers ----

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def _build_user_with_token(self, user: User) -> UserWithToken:
        return UserWithToken(
            user=UserResponse.model_validate(user),
            tokens=self._create_tokens(user.id),
        )

    def _create_tokens(self, user_id: UUID) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

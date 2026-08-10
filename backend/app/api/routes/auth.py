"""
Jan Vaani — Auth Routes
POST /auth/register  → Create account
POST /auth/login     → JSON login (returns token)
POST /auth/login/form → OAuth2 form login (for Swagger UI)
GET  /auth/me        → Get current user info
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.db_models import User
from app.models.schemas import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account.
    Returns a JWT access token so the user is immediately logged in after registration.
    """
    # Check email not already taken
    existing = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.user_id, "email": user.email})
    logger.info(f"New user registered: {user.email}")

    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """JSON login — returns JWT access token."""
    result = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    token = create_access_token({"sub": user.user_id, "email": user.email})
    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
    )


@router.post("/login/form", response_model=TokenResponse)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2-compatible form login (for Swagger UI /docs).
    Uses username field as the email.
    """
    result = await db.execute(select(User).where(User.email == form_data.username.lower().strip()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token({"sub": user.user_id, "email": user.email})
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user

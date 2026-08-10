"""
Jan Vaani — Auth Core
JWT token creation/validation and password hashing utilities.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 bearer token scheme (reads from Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/form")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare plain password against stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    
    Args:
        data: Payload dict — should include {'sub': user_id, 'email': email}
        expires_delta: Optional custom expiry. Defaults to settings value.
    
    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Raises:
        HTTPException 401 if token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency that validates the Bearer token and returns the current User ORM object.
    Inject into any route that requires authentication.
    """
    from app.models.db_models import User  # avoid circular import
    
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login/form", auto_error=False)),
    db: AsyncSession = Depends(get_db),
):
    """
    Like get_current_user but returns None if no/invalid token.
    Use for routes that work both authenticated and unauthenticated (e.g., demo mode).
    """
    if not token:
        return None
    try:
        from app.models.db_models import User  # avoid circular import
        payload = decode_token(token)
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user if (user and user.is_active) else None
    except HTTPException:
        return None
    except Exception:
        return None

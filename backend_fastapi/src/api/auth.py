"""
Authentication module for Travel Planner Pro.

Provides JWT token creation/verification, password hashing,
and FastAPI dependency for extracting the current user from
the Authorization header.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.api.database import get_db
from src.api.models import User

load_dotenv()

# JWT configuration from environment
# JWT_SECRET_KEY - Required. A secure random string for signing tokens.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "travel-planner-pro-default-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt-hashed password string.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# PUBLIC_INTERFACE
def create_access_token(user_id: str, role: str) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id: The user's UUID string.
        role: The user's role (user or admin).

    Returns:
        Encoded JWT token string.
    """
    expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# PUBLIC_INTERFACE
def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token string.

    Returns:
        Dictionary with 'sub' (user_id) and 'role' claims.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# PUBLIC_INTERFACE
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to extract the current authenticated user.

    Reads the JWT from the Authorization: Bearer header, decodes it,
    and fetches the corresponding User from the database.

    Args:
        credentials: The HTTP Bearer credentials.
        db: Database session.

    Returns:
        The authenticated User ORM object.

    Raises:
        HTTPException 401: If no token is provided or it is invalid.
        HTTPException 401: If the user is not found or is inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user


# PUBLIC_INTERFACE
def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency to optionally extract the current user.

    Returns None if no token is provided, otherwise behaves like
    get_current_user. Useful for endpoints that work both for
    authenticated and anonymous users.

    Args:
        credentials: The HTTP Bearer credentials (optional).
        db: Database session.

    Returns:
        The User ORM object or None if unauthenticated.
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_active:
            return user
        return None
    except HTTPException:
        return None


# PUBLIC_INTERFACE
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency that requires the current user to be an admin.

    Args:
        current_user: The authenticated user.

    Returns:
        The admin User ORM object.

    Raises:
        HTTPException 403: If the user is not an admin.
    """
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

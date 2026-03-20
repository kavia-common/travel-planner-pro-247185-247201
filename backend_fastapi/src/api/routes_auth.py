"""
Authentication routes for Travel Planner Pro.

Provides endpoints for user registration, login, and profile retrieval.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import User
from src.api.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
)
from src.api.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account and return a JWT access token.",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        payload: Registration data (email, password, name).
        db: Database session.

    Returns:
        TokenResponse with JWT token and user details.

    Raises:
        HTTPException 400: If the email is already registered.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.display_name,
            role=user.role.value,
            avatar_url=user.avatar_url,
            created_at=user.created_at.isoformat(),
        ),
    )


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
    description="Authenticate with email and password, receive a JWT token.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login a user.

    Args:
        payload: Login credentials (email, password).
        db: Database session.

    Returns:
        TokenResponse with JWT token and user details.

    Raises:
        HTTPException 401: If the credentials are invalid.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.display_name,
            role=user.role.value,
            avatar_url=user.avatar_url,
            created_at=user.created_at.isoformat(),
        ),
    )


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current user's profile.

    Args:
        current_user: The authenticated user.

    Returns:
        UserResponse with user details.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.display_name,
        role=current_user.role.value,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at.isoformat(),
    )

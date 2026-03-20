"""
Admin routes for Travel Planner Pro.

Provides endpoints for user management, dashboard statistics,
and admin moderation actions. All endpoints require admin role.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.api.database import get_db
from src.api.models import User, Trip, AdminLog, AdminAction, TripStatus
from src.api.schemas import UserResponse, UpdateUserRoleRequest, AdminStatsResponse
from src.api.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _user_to_response(user: User) -> UserResponse:
    """Convert a User ORM object to a UserResponse schema."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.display_name,
        role=user.role.value,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


# PUBLIC_INTERFACE
@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users",
    description="Returns all users. Admin only.",
)
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List all users (admin only).

    Args:
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        List of UserResponse objects.
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [_user_to_response(u) for u in users]


# PUBLIC_INTERFACE
@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user role",
    description="Update a user's role. Admin only.",
)
def update_user_role(
    user_id: str,
    payload: UpdateUserRoleRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's role.

    Args:
        user_id: The target user UUID.
        payload: New role data.
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        The updated UserResponse.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role.value
    user.updated_at = datetime.utcnow()

    # Log admin action
    log = AdminLog(
        admin_id=admin.id,
        action=AdminAction.update_role,
        target_user_id=user.id,
        details=f"Changed role to {payload.role.value}",
    )
    db.add(log)
    db.commit()
    db.refresh(user)
    return _user_to_response(user)


# PUBLIC_INTERFACE
@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user account. Admin only.",
)
def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a user account.

    Args:
        user_id: The target user UUID.
        admin: The authenticated admin user.
        db: Database session.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    # Log admin action
    log = AdminLog(
        admin_id=admin.id,
        action=AdminAction.delete_user,
        target_user_id=user.id,
        details=f"Deleted user {user.email}",
    )
    db.add(log)

    db.delete(user)
    db.commit()
    return None


# PUBLIC_INTERFACE
@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get admin statistics",
    description="Returns dashboard statistics. Admin only.",
)
def get_admin_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get admin dashboard statistics.

    Args:
        admin: The authenticated admin user.
        db: Database session.

    Returns:
        AdminStatsResponse with counts.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_trips = db.query(func.count(Trip.id)).scalar() or 0
    active_trips = db.query(func.count(Trip.id)).filter(
        Trip.status.in_([TripStatus.planning, TripStatus.active])
    ).scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        total_trips=total_trips,
        active_trips=active_trips,
    )

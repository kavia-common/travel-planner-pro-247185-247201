"""
Notification routes for Travel Planner Pro.

Provides endpoints for fetching, marking as read,
and batch-marking notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import Notification, User
from src.api.schemas import NotificationResponse
from src.api.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _notification_to_response(n: Notification) -> NotificationResponse:
    """Convert a Notification ORM object to a NotificationResponse schema."""
    # Map DB notification types to frontend types
    type_mapping = {
        "trip_reminder": "reminder",
        "share_invite": "info",
        "trip_update": "info",
        "budget_alert": "warning",
        "system": "info",
    }
    notification_type = type_mapping.get(n.type.value, "info") if n.type else "info"

    return NotificationResponse(
        id=str(n.id),
        user_id=str(n.user_id),
        title=n.title,
        message=n.message,
        type=notification_type,
        is_read=n.is_read,
        created_at=n.created_at.isoformat() if n.created_at else "",
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notifications",
    description="Returns all notifications for the current user, newest first.",
)
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List notifications for the current user.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of NotificationResponse objects.
    """
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()

    return [_notification_to_response(n) for n in notifications]


# PUBLIC_INTERFACE
@router.patch(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark notification as read",
    description="Mark a single notification as read.",
)
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark a notification as read.

    Args:
        notification_id: The notification UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    db.commit()
    return None


# PUBLIC_INTERFACE
@router.patch(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
    description="Mark all notifications for the current user as read.",
)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark all notifications as read for the current user.

    Args:
        current_user: The authenticated user.
        db: Database session.
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return None

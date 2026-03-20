"""
Trip sharing routes for Travel Planner Pro.

Provides endpoints for sharing trips with other users,
viewing share permissions, and revoking access.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import Trip, TripShare, User, Notification, NotificationType
from src.api.schemas import SharePayload, SharePermissionResponse
from src.api.auth import get_current_user

router = APIRouter(prefix="/api/trips/{trip_id}/share", tags=["Sharing"])


def _share_to_response(share: TripShare, db: Session) -> SharePermissionResponse:
    """Convert a TripShare ORM object to a SharePermissionResponse schema."""
    shared_user = db.query(User).filter(User.id == share.shared_with_id).first()
    return SharePermissionResponse(
        id=str(share.id),
        trip_id=str(share.trip_id),
        shared_with_email=shared_user.email if shared_user else "unknown",
        permission=share.permission.value if share.permission else "view",
        created_at=share.created_at.isoformat() if share.created_at else "",
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[SharePermissionResponse],
    summary="List share permissions",
    description="Returns all sharing permissions for a trip. Only the trip owner can view.",
)
def list_share_permissions(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all share permissions for a trip.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of SharePermissionResponse objects.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Only owner or admin can view share permissions
    if str(trip.owner_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can manage sharing")

    shares = db.query(TripShare).filter(TripShare.trip_id == trip_id).all()
    return [_share_to_response(s, db) for s in shares]


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=SharePermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Share trip",
    description="Share a trip with another user by email.",
)
def share_trip(
    trip_id: str,
    payload: SharePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Share a trip with another user.

    Args:
        trip_id: The trip UUID.
        payload: Share data (email, permission level).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created SharePermissionResponse.

    Raises:
        HTTPException 403: If the user is not the trip owner.
        HTTPException 404: If the target user is not found.
        HTTPException 400: If already shared or sharing with self.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if str(trip.owner_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can share this trip")

    # Find the target user by email
    target_user = db.query(User).filter(User.email == payload.shared_with_email).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found with that email")

    if str(target_user.id) == str(current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share a trip with yourself")

    # Check if already shared
    existing = db.query(TripShare).filter(
        TripShare.trip_id == trip_id,
        TripShare.shared_with_id == target_user.id,
    ).first()
    if existing:
        # Update permission
        existing.permission = payload.permission.value
        db.commit()
        db.refresh(existing)
        return _share_to_response(existing, db)

    share = TripShare(
        trip_id=trip_id,
        shared_with_id=target_user.id,
        permission=payload.permission.value,
    )
    db.add(share)

    # Create a notification for the target user
    notification = Notification(
        user_id=target_user.id,
        type=NotificationType.share_invite,
        title="Trip shared with you",
        message=f"{current_user.display_name} shared the trip '{trip.title}' with you ({payload.permission.value} access).",
        related_trip_id=trip_id,
    )
    db.add(notification)

    db.commit()
    db.refresh(share)
    return _share_to_response(share, db)


# PUBLIC_INTERFACE
@router.delete(
    "/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke share",
    description="Revoke a sharing permission for a trip.",
)
def revoke_share(
    trip_id: str,
    share_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke a sharing permission.

    Args:
        trip_id: The trip UUID.
        share_id: The share permission UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if str(trip.owner_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can revoke sharing")

    share = db.query(TripShare).filter(
        TripShare.id == share_id,
        TripShare.trip_id == trip_id,
    ).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share permission not found")

    db.delete(share)
    db.commit()
    return None

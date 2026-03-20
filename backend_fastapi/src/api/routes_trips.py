"""
Trip CRUD routes for Travel Planner Pro.

Provides endpoints for creating, reading, updating, and deleting trips.
Includes sharing-aware access: users can see trips they own or that are
shared with them.
"""

from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.api.database import get_db
from src.api.models import Trip, TripShare, User
from src.api.schemas import TripPayload, TripResponse
from src.api.auth import get_current_user

router = APIRouter(prefix="/api/trips", tags=["Trips"])


def _trip_to_response(trip: Trip) -> TripResponse:
    """Convert a Trip ORM object to a TripResponse schema."""
    return TripResponse(
        id=str(trip.id),
        user_id=str(trip.owner_id),
        title=trip.title,
        description=trip.description,
        destination=trip.destination,
        start_date=trip.start_date.isoformat() if trip.start_date else "",
        end_date=trip.end_date.isoformat() if trip.end_date else "",
        cover_image=trip.cover_image_url,
        status=trip.status.value if trip.status else "planning",
        created_at=trip.created_at.isoformat() if trip.created_at else "",
        updated_at=trip.updated_at.isoformat() if trip.updated_at else "",
    )


def _get_trip_with_access(trip_id: str, user: User, db: Session, require_edit: bool = False) -> Trip:
    """
    Fetch a trip and verify the user has access.
    
    For ownership or edit-shared access, require_edit=True.
    For view or edit shared access, require_edit=False.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Owner always has access
    if str(trip.owner_id) == str(user.id):
        return trip

    # Admin always has access
    if user.role.value == "admin":
        return trip

    # Check sharing permissions
    share = db.query(TripShare).filter(
        TripShare.trip_id == trip_id,
        TripShare.shared_with_id == user.id,
    ).first()

    if not share:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if require_edit and share.permission.value != "edit":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edit access required")

    return trip


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=list[TripResponse],
    summary="List all trips",
    description="Returns all trips owned by or shared with the current user.",
)
def list_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all trips for the current user.

    Includes trips owned by the user and trips shared with them.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of TripResponse objects.
    """
    # Get IDs of trips shared with this user
    shared_trip_ids = db.query(TripShare.trip_id).filter(
        TripShare.shared_with_id == current_user.id
    ).all()
    shared_ids = [str(s[0]) for s in shared_trip_ids]

    trips = db.query(Trip).filter(
        or_(
            Trip.owner_id == current_user.id,
            Trip.id.in_(shared_ids) if shared_ids else False,
        )
    ).order_by(Trip.updated_at.desc()).all()

    return [_trip_to_response(t) for t in trips]


# PUBLIC_INTERFACE
@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Get a trip",
    description="Returns a single trip by ID if the user has access.",
)
def get_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single trip by ID.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        TripResponse object.
    """
    trip = _get_trip_with_access(trip_id, current_user, db)
    return _trip_to_response(trip)


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trip",
    description="Create a new trip for the current user.",
)
def create_trip(
    payload: TripPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new trip.

    Args:
        payload: Trip creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created TripResponse object.
    """
    # Map frontend status values to DB enum values
    db_status = payload.status.value if payload.status else "planning"
    # Map 'ongoing' to 'active' for DB compatibility
    if db_status == "ongoing":
        db_status = "active"

    trip = Trip(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        destination=payload.destination,
        start_date=date.fromisoformat(payload.start_date),
        end_date=date.fromisoformat(payload.end_date),
        cover_image_url=payload.cover_image,
        status=db_status,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return _trip_to_response(trip)


# PUBLIC_INTERFACE
@router.put(
    "/{trip_id}",
    response_model=TripResponse,
    summary="Update a trip",
    description="Update an existing trip. Requires ownership or edit permission.",
)
def update_trip(
    trip_id: str,
    payload: TripPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a trip.

    Args:
        trip_id: The trip UUID.
        payload: Updated trip data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated TripResponse object.
    """
    trip = _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    if payload.title is not None:
        trip.title = payload.title
    if payload.description is not None:
        trip.description = payload.description
    if payload.destination is not None:
        trip.destination = payload.destination
    if payload.start_date is not None:
        trip.start_date = date.fromisoformat(payload.start_date)
    if payload.end_date is not None:
        trip.end_date = date.fromisoformat(payload.end_date)
    if payload.cover_image is not None:
        trip.cover_image_url = payload.cover_image
    if payload.status is not None:
        db_status = payload.status.value
        if db_status == "ongoing":
            db_status = "active"
        trip.status = db_status

    trip.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(trip)
    return _trip_to_response(trip)


# PUBLIC_INTERFACE
@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trip",
    description="Delete a trip. Only the owner or an admin can delete.",
)
def delete_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a trip.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if str(trip.owner_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete this trip")

    db.delete(trip)
    db.commit()
    return None

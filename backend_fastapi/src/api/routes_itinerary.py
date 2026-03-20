"""
Itinerary day and activity routes for Travel Planner Pro.

Provides CRUD endpoints for itinerary days within a trip and
activities within each itinerary day.
"""

from datetime import datetime, date, time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import ItineraryDay, Activity, User
from src.api.schemas import (
    ItineraryDayPayload, ItineraryDayResponse, ActivityPayload, ActivityResponse,
)
from src.api.auth import get_current_user
from src.api.routes_trips import _get_trip_with_access

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["Itinerary"])


def _activity_to_response(act: Activity) -> ActivityResponse:
    """Convert an Activity ORM object to an ActivityResponse schema."""
    return ActivityResponse(
        id=str(act.id),
        itinerary_day_id=str(act.itinerary_day_id),
        title=act.title,
        description=act.description,
        location=act.location,
        start_time=act.start_time.strftime("%H:%M") if act.start_time else None,
        end_time=act.end_time.strftime("%H:%M") if act.end_time else None,
        category=act.category.value if act.category else "other",
        cost=float(act.estimated_cost) if act.estimated_cost else None,
        notes=act.notes,
        order=act.sort_order,
    )


def _day_to_response(day: ItineraryDay) -> ItineraryDayResponse:
    """Convert an ItineraryDay ORM object to an ItineraryDayResponse schema."""
    return ItineraryDayResponse(
        id=str(day.id),
        trip_id=str(day.trip_id),
        day_number=day.day_number,
        date=day.date.isoformat() if day.date else "",
        title=day.title,
        notes=day.notes,
        activities=[_activity_to_response(a) for a in (day.activities or [])],
    )


# ─── Itinerary Day Endpoints ───

# PUBLIC_INTERFACE
@router.get(
    "/itinerary",
    response_model=list[ItineraryDayResponse],
    summary="List itinerary days",
    description="Returns all itinerary days for a trip, ordered by day number.",
)
def list_itinerary_days(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all itinerary days for a trip.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of ItineraryDayResponse objects with activities.
    """
    _get_trip_with_access(trip_id, current_user, db)
    days = db.query(ItineraryDay).filter(
        ItineraryDay.trip_id == trip_id
    ).order_by(ItineraryDay.day_number).all()
    return [_day_to_response(d) for d in days]


# PUBLIC_INTERFACE
@router.post(
    "/itinerary",
    response_model=ItineraryDayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create itinerary day",
    description="Add a new day to the trip itinerary.",
)
def create_itinerary_day(
    trip_id: str,
    payload: ItineraryDayPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new itinerary day.

    Args:
        trip_id: The trip UUID.
        payload: Day creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created ItineraryDayResponse object.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    # Check for duplicate day number
    existing = db.query(ItineraryDay).filter(
        ItineraryDay.trip_id == trip_id,
        ItineraryDay.day_number == payload.day_number,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Day number {payload.day_number} already exists for this trip"
        )

    day = ItineraryDay(
        trip_id=trip_id,
        day_number=payload.day_number,
        date=date.fromisoformat(payload.date),
        title=payload.title,
        notes=payload.notes,
    )
    db.add(day)
    db.commit()
    db.refresh(day)
    return _day_to_response(day)


# PUBLIC_INTERFACE
@router.delete(
    "/itinerary/{day_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete itinerary day",
    description="Remove an itinerary day and all its activities.",
)
def delete_itinerary_day(
    trip_id: str,
    day_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an itinerary day.

    Args:
        trip_id: The trip UUID.
        day_id: The itinerary day UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    day = db.query(ItineraryDay).filter(
        ItineraryDay.id == day_id,
        ItineraryDay.trip_id == trip_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    db.delete(day)
    db.commit()
    return None


# ─── Activity Endpoints ───

def _parse_time(time_str: str) -> time:
    """Parse a time string in HH:MM format."""
    if not time_str:
        return None
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


# PUBLIC_INTERFACE
@router.post(
    "/itinerary/{day_id}/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity",
    description="Add an activity to an itinerary day.",
)
def create_activity(
    trip_id: str,
    day_id: str,
    payload: ActivityPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new activity.

    Args:
        trip_id: The trip UUID.
        day_id: The itinerary day UUID.
        payload: Activity creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created ActivityResponse object.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    day = db.query(ItineraryDay).filter(
        ItineraryDay.id == day_id,
        ItineraryDay.trip_id == trip_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    # Determine sort order
    max_order = db.query(Activity).filter(
        Activity.itinerary_day_id == day_id
    ).count()
    sort_order = payload.order if payload.order is not None else max_order

    # Map category - handle potential mismatches
    cat_value = payload.category.value if payload.category else "other"

    activity = Activity(
        itinerary_day_id=day_id,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        start_time=_parse_time(payload.start_time) if payload.start_time else None,
        end_time=_parse_time(payload.end_time) if payload.end_time else None,
        category=cat_value,
        estimated_cost=payload.cost,
        notes=payload.notes,
        sort_order=sort_order,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return _activity_to_response(activity)


# PUBLIC_INTERFACE
@router.put(
    "/itinerary/{day_id}/activities/{activity_id}",
    response_model=ActivityResponse,
    summary="Update activity",
    description="Update an existing activity.",
)
def update_activity(
    trip_id: str,
    day_id: str,
    activity_id: str,
    payload: ActivityPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an activity.

    Args:
        trip_id: The trip UUID.
        day_id: The itinerary day UUID.
        activity_id: The activity UUID.
        payload: Updated activity data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated ActivityResponse object.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.itinerary_day_id == day_id,
    ).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    if payload.title is not None:
        activity.title = payload.title
    if payload.description is not None:
        activity.description = payload.description
    if payload.location is not None:
        activity.location = payload.location
    if payload.start_time is not None:
        activity.start_time = _parse_time(payload.start_time)
    if payload.end_time is not None:
        activity.end_time = _parse_time(payload.end_time)
    if payload.category is not None:
        activity.category = payload.category.value
    if payload.cost is not None:
        activity.estimated_cost = payload.cost
    if payload.notes is not None:
        activity.notes = payload.notes
    if payload.order is not None:
        activity.sort_order = payload.order

    activity.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(activity)
    return _activity_to_response(activity)


# PUBLIC_INTERFACE
@router.delete(
    "/itinerary/{day_id}/activities/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete activity",
    description="Remove an activity from an itinerary day.",
)
def delete_activity(
    trip_id: str,
    day_id: str,
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an activity.

    Args:
        trip_id: The trip UUID.
        day_id: The itinerary day UUID.
        activity_id: The activity UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.itinerary_day_id == day_id,
    ).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    db.delete(activity)
    db.commit()
    return None

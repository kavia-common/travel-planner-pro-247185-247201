"""
Packing list routes for Travel Planner Pro.

Provides endpoints for managing packing checklists per trip.
The frontend expects a PackingList wrapper with items inside.
Since the DB stores packing_items directly linked to trips,
we synthesize the PackingList response shape.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import PackingItem, User
from src.api.schemas import (
    PackingItemPayload, PackingItemResponse, PackingListResponse, TogglePackedRequest,
)
from src.api.auth import get_current_user
from src.api.routes_trips import _get_trip_with_access

router = APIRouter(prefix="/api/trips/{trip_id}/packing", tags=["Packing"])


def _item_to_response(item: PackingItem) -> PackingItemResponse:
    """Convert a PackingItem ORM object to a PackingItemResponse schema."""
    return PackingItemResponse(
        id=str(item.id),
        packing_list_id=str(item.trip_id),
        name=item.name,
        quantity=item.quantity,
        is_packed=item.is_packed,
        category=item.category or "general",
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=PackingListResponse,
    summary="Get packing list",
    description="Returns the packing checklist for a trip.",
)
def get_packing_list(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the packing list for a trip.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PackingListResponse with all items.
    """
    _get_trip_with_access(trip_id, current_user, db)

    items = db.query(PackingItem).filter(
        PackingItem.trip_id == trip_id
    ).order_by(PackingItem.created_at).all()

    return PackingListResponse(
        id=trip_id,
        trip_id=trip_id,
        items=[_item_to_response(i) for i in items],
    )


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=PackingItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add packing item",
    description="Add an item to the trip packing checklist.",
)
def create_packing_item(
    trip_id: str,
    payload: PackingItemPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new packing item.

    Args:
        trip_id: The trip UUID.
        payload: Packing item data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created PackingItemResponse object.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    item = PackingItem(
        trip_id=trip_id,
        name=payload.name,
        quantity=payload.quantity,
        is_packed=payload.is_packed or False,
        category=payload.category or "general",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_response(item)


# PUBLIC_INTERFACE
@router.patch(
    "/{item_id}",
    response_model=PackingItemResponse,
    summary="Toggle packing item",
    description="Toggle the packed status of a packing item.",
)
def toggle_packing_item(
    trip_id: str,
    item_id: str,
    payload: TogglePackedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle the packed status of a packing item.

    Args:
        trip_id: The trip UUID.
        item_id: The packing item UUID.
        payload: Toggle data with is_packed boolean.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated PackingItemResponse object.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    item = db.query(PackingItem).filter(
        PackingItem.id == item_id,
        PackingItem.trip_id == trip_id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packing item not found")

    item.is_packed = payload.is_packed
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return _item_to_response(item)


# PUBLIC_INTERFACE
@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete packing item",
    description="Remove an item from the packing checklist.",
)
def delete_packing_item(
    trip_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a packing item.

    Args:
        trip_id: The trip UUID.
        item_id: The packing item UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    item = db.query(PackingItem).filter(
        PackingItem.id == item_id,
        PackingItem.trip_id == trip_id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packing item not found")

    db.delete(item)
    db.commit()
    return None

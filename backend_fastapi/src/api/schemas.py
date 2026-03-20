"""
Pydantic schemas for Travel Planner Pro API.

Defines request and response models for all API endpoints,
matching the frontend TypeScript type definitions exactly.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from enum import Enum


# ─── Enums ───

class TripStatusEnum(str, Enum):
    """Trip status options."""
    planning = "planning"
    active = "active"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"


class ActivityCategoryEnum(str, Enum):
    """Activity category options."""
    transport = "transport"
    food = "food"
    sightseeing = "sightseeing"
    accommodation = "accommodation"
    shopping = "shopping"
    entertainment = "entertainment"
    nature = "nature"
    culture = "culture"
    other = "other"


class ExpenseCategoryEnum(str, Enum):
    """Expense category options."""
    flights = "flights"
    transport = "transport"
    food = "food"
    accommodation = "accommodation"
    activities = "activities"
    shopping = "shopping"
    insurance = "insurance"
    visa = "visa"
    other = "other"


class SharePermissionEnum(str, Enum):
    """Share permission options."""
    view = "view"
    edit = "edit"


class NotificationTypeEnum(str, Enum):
    """Notification type options."""
    info = "info"
    reminder = "reminder"
    warning = "warning"
    success = "success"
    trip_reminder = "trip_reminder"
    share_invite = "share_invite"
    trip_update = "trip_update"
    budget_alert = "budget_alert"
    system = "system"


class UserRoleEnum(str, Enum):
    """User role options."""
    user = "user"
    admin = "admin"


# ─── Auth Schemas ───

class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password, minimum 6 characters")
    name: str = Field(..., min_length=1, description="Display name")


class LoginRequest(BaseModel):
    """Request body for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT token response after successful authentication."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserResponse" = Field(..., description="Authenticated user details")


# ─── User Schemas ───

class UserResponse(BaseModel):
    """User data in API responses."""
    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="Display name")
    role: str = Field(..., description="User role (user or admin)")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    created_at: str = Field(..., description="ISO timestamp of creation")

    model_config = {"from_attributes": True}


class UpdateUserRoleRequest(BaseModel):
    """Request body for updating a user's role."""
    role: UserRoleEnum = Field(..., description="New role to assign")


# ─── Trip Schemas ───

class TripPayload(BaseModel):
    """Request body for creating or updating a trip."""
    title: str = Field(..., min_length=1, description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    destination: str = Field(..., min_length=1, description="Trip destination")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    status: Optional[TripStatusEnum] = Field(None, description="Trip status")


class TripResponse(BaseModel):
    """Trip data in API responses."""
    id: str = Field(..., description="Trip UUID")
    user_id: str = Field(..., description="Owner user UUID")
    title: str = Field(..., description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    destination: str = Field(..., description="Trip destination")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    status: str = Field(..., description="Trip status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


# ─── Itinerary Day Schemas ───

class ItineraryDayPayload(BaseModel):
    """Request body for creating an itinerary day."""
    day_number: int = Field(..., ge=1, description="Day number in trip")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    title: Optional[str] = Field(None, description="Day title")
    notes: Optional[str] = Field(None, description="Day notes")


class ActivityResponse(BaseModel):
    """Activity data in API responses."""
    id: str = Field(..., description="Activity UUID")
    itinerary_day_id: str = Field(..., description="Parent itinerary day UUID")
    title: str = Field(..., description="Activity title")
    description: Optional[str] = Field(None, description="Activity description")
    location: Optional[str] = Field(None, description="Activity location")
    start_time: Optional[str] = Field(None, description="Start time")
    end_time: Optional[str] = Field(None, description="End time")
    category: str = Field(..., description="Activity category")
    cost: Optional[float] = Field(None, description="Estimated cost")
    notes: Optional[str] = Field(None, description="Activity notes")
    order: int = Field(..., description="Sort order")

    model_config = {"from_attributes": True}


class ItineraryDayResponse(BaseModel):
    """Itinerary day data in API responses."""
    id: str = Field(..., description="Itinerary day UUID")
    trip_id: str = Field(..., description="Parent trip UUID")
    day_number: int = Field(..., description="Day number")
    date: str = Field(..., description="Date")
    title: Optional[str] = Field(None, description="Day title")
    notes: Optional[str] = Field(None, description="Day notes")
    activities: List[ActivityResponse] = Field(default_factory=list, description="Activities for this day")

    model_config = {"from_attributes": True}


# ─── Activity Schemas ───

class ActivityPayload(BaseModel):
    """Request body for creating or updating an activity."""
    title: str = Field(..., min_length=1, description="Activity title")
    description: Optional[str] = Field(None, description="Activity description")
    location: Optional[str] = Field(None, description="Activity location")
    start_time: Optional[str] = Field(None, description="Start time HH:MM")
    end_time: Optional[str] = Field(None, description="End time HH:MM")
    category: ActivityCategoryEnum = Field(default=ActivityCategoryEnum.other, description="Activity category")
    cost: Optional[float] = Field(None, description="Estimated cost")
    notes: Optional[str] = Field(None, description="Activity notes")
    order: Optional[int] = Field(None, description="Sort order")


# ─── Budget Schemas ───

class BudgetPayload(BaseModel):
    """Request body for creating or updating a budget."""
    total_budget: float = Field(..., ge=0, description="Total budget amount")
    currency: str = Field(default="USD", description="Currency code")


class ExpenseResponse(BaseModel):
    """Expense data in API responses."""
    id: str = Field(..., description="Expense UUID")
    budget_id: str = Field(..., description="Parent budget UUID")
    title: str = Field(..., description="Expense title")
    amount: float = Field(..., description="Expense amount")
    category: str = Field(..., description="Expense category")
    date: str = Field(..., description="Expense date")
    notes: Optional[str] = Field(None, description="Expense notes")

    model_config = {"from_attributes": True}


class BudgetResponse(BaseModel):
    """Budget data in API responses."""
    id: str = Field(..., description="Budget UUID")
    trip_id: str = Field(..., description="Parent trip UUID")
    total_budget: float = Field(..., description="Total budget amount")
    currency: str = Field(..., description="Currency code")
    expenses: List[ExpenseResponse] = Field(default_factory=list, description="Expenses in this budget")

    model_config = {"from_attributes": True}


class ExpensePayload(BaseModel):
    """Request body for creating an expense."""
    title: str = Field(..., min_length=1, description="Expense title")
    amount: float = Field(..., gt=0, description="Expense amount")
    category: ExpenseCategoryEnum = Field(default=ExpenseCategoryEnum.other, description="Expense category")
    date: str = Field(..., description="Expense date YYYY-MM-DD")
    notes: Optional[str] = Field(None, description="Expense notes")


# ─── Packing Schemas ───

class PackingItemPayload(BaseModel):
    """Request body for creating a packing item."""
    name: str = Field(..., min_length=1, description="Item name")
    quantity: int = Field(default=1, ge=1, description="Item quantity")
    is_packed: Optional[bool] = Field(False, description="Whether the item is packed")
    category: str = Field(default="general", description="Item category")


class PackingItemResponse(BaseModel):
    """Packing item data in API responses."""
    id: str = Field(..., description="Packing item UUID")
    packing_list_id: str = Field(..., description="Parent packing list (trip) UUID")
    name: str = Field(..., description="Item name")
    quantity: int = Field(..., description="Item quantity")
    is_packed: bool = Field(..., description="Whether the item is packed")
    category: str = Field(..., description="Item category")

    model_config = {"from_attributes": True}


class PackingListResponse(BaseModel):
    """Packing list data in API responses."""
    id: str = Field(..., description="Packing list (trip) UUID")
    trip_id: str = Field(..., description="Trip UUID")
    items: List[PackingItemResponse] = Field(default_factory=list, description="Items in the list")

    model_config = {"from_attributes": True}


class TogglePackedRequest(BaseModel):
    """Request body for toggling packing item status."""
    is_packed: bool = Field(..., description="New packed status")


# ─── Sharing Schemas ───

class SharePayload(BaseModel):
    """Request body for sharing a trip."""
    shared_with_email: str = Field(..., description="Email of user to share with")
    permission: SharePermissionEnum = Field(default=SharePermissionEnum.view, description="Permission level")


class SharePermissionResponse(BaseModel):
    """Share permission data in API responses."""
    id: str = Field(..., description="Share UUID")
    trip_id: str = Field(..., description="Trip UUID")
    shared_with_email: str = Field(..., description="Shared user's email")
    permission: str = Field(..., description="Permission level (view or edit)")
    created_at: str = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


# ─── Notification Schemas ───

class NotificationResponse(BaseModel):
    """Notification data in API responses."""
    id: str = Field(..., description="Notification UUID")
    user_id: str = Field(..., description="User UUID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    type: str = Field(..., description="Notification type")
    is_read: bool = Field(..., description="Whether notification has been read")
    created_at: str = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


# ─── Admin Schemas ───

class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""
    total_users: int = Field(..., description="Total number of users")
    total_trips: int = Field(..., description="Total number of trips")
    active_trips: int = Field(..., description="Number of active/planning trips")


# Update forward references
TokenResponse.model_rebuild()

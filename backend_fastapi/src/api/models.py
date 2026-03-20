"""
SQLAlchemy ORM models for Travel Planner Pro.

Maps to the existing PostgreSQL schema with tables: users, trips,
itinerary_days, activities, budgets, expenses, packing_items,
trip_shares, notifications, admin_logs.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, Numeric,
    Date, Time, DateTime, ForeignKey, UniqueConstraint, CheckConstraint,
    Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.api.database import Base

import enum


# ─── Python Enums matching PostgreSQL custom types ───

class UserRole(str, enum.Enum):
    """User role enumeration."""
    user = "user"
    admin = "admin"


class TripStatus(str, enum.Enum):
    """Trip status enumeration."""
    planning = "planning"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ActivityCategory(str, enum.Enum):
    """Activity category enumeration."""
    sightseeing = "sightseeing"
    food = "food"
    transport = "transport"
    accommodation = "accommodation"
    shopping = "shopping"
    entertainment = "entertainment"
    nature = "nature"
    culture = "culture"
    other = "other"


class ExpenseCategory(str, enum.Enum):
    """Expense category enumeration."""
    flights = "flights"
    accommodation = "accommodation"
    food = "food"
    transport = "transport"
    activities = "activities"
    shopping = "shopping"
    insurance = "insurance"
    visa = "visa"
    other = "other"


class SharePermission(str, enum.Enum):
    """Share permission enumeration."""
    view = "view"
    edit = "edit"


class NotificationType(str, enum.Enum):
    """Notification type enumeration."""
    trip_reminder = "trip_reminder"
    share_invite = "share_invite"
    trip_update = "trip_update"
    budget_alert = "budget_alert"
    system = "system"


class AdminAction(str, enum.Enum):
    """Admin action enumeration."""
    ban_user = "ban_user"
    unban_user = "unban_user"
    delete_trip = "delete_trip"
    delete_user = "delete_user"
    update_role = "update_role"
    system_config = "system_config"


# ─── ORM Models ───

class User(Base):
    """ORM model for the users table."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(SAEnum(UserRole, name="user_role", create_type=False), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trips = relationship("Trip", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    shared_trips = relationship("TripShare", back_populates="shared_with_user", foreign_keys="TripShare.shared_with_id")


class Trip(Base):
    """ORM model for the trips table."""
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    destination = Column(String, nullable=False)
    cover_image_url = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(SAEnum(TripStatus, name="trip_status", create_type=False), default=TripStatus.planning, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="check_dates"),
    )

    # Relationships
    owner = relationship("User", back_populates="trips")
    itinerary_days = relationship("ItineraryDay", back_populates="trip", cascade="all, delete-orphan")
    budget = relationship("Budget", back_populates="trip", uselist=False, cascade="all, delete-orphan")
    packing_items = relationship("PackingItem", back_populates="trip", cascade="all, delete-orphan")
    shares = relationship("TripShare", back_populates="trip", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="related_trip")


class ItineraryDay(Base):
    """ORM model for the itinerary_days table."""
    __tablename__ = "itinerary_days"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    day_number = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    title = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("trip_id", "day_number", name="uq_trip_day_number"),
    )

    # Relationships
    trip = relationship("Trip", back_populates="itinerary_days")
    activities = relationship("Activity", back_populates="itinerary_day", cascade="all, delete-orphan", order_by="Activity.sort_order")


class Activity(Base):
    """ORM model for the activities table."""
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    itinerary_day_id = Column(UUID(as_uuid=True), ForeignKey("itinerary_days.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    category = Column(SAEnum(ActivityCategory, name="activity_category", create_type=False), default=ActivityCategory.other, nullable=False)
    estimated_cost = Column(Numeric, nullable=True, default=0)
    currency = Column(String, nullable=True, default="USD")
    notes = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    itinerary_day = relationship("ItineraryDay", back_populates="activities")


class Budget(Base):
    """ORM model for the budgets table."""
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_budget = Column(Numeric, nullable=False, default=0)
    currency = Column(String, nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="budget")
    expenses = relationship("Expense", back_populates="budget", cascade="all, delete-orphan")


class Expense(Base):
    """ORM model for the expenses table."""
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    category = Column(SAEnum(ExpenseCategory, name="expense_category", create_type=False), default=ExpenseCategory.other, nullable=False)
    date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="expenses")


class PackingItem(Base):
    """ORM model for the packing_items table."""
    __tablename__ = "packing_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    is_packed = Column(Boolean, nullable=False, default=False)
    category = Column(String, nullable=True, default="general")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="packing_items")


class TripShare(Base):
    """ORM model for the trip_shares table."""
    __tablename__ = "trip_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    shared_with_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permission = Column(SAEnum(SharePermission, name="share_permission", create_type=False), default=SharePermission.view, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("trip_id", "shared_with_id", name="uq_trip_share"),
    )

    # Relationships
    trip = relationship("Trip", back_populates="shares")
    shared_with_user = relationship("User", back_populates="shared_trips", foreign_keys=[shared_with_id])


class Notification(Base):
    """ORM model for the notifications table."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(SAEnum(NotificationType, name="notification_type", create_type=False), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    related_trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")
    related_trip = relationship("Trip", back_populates="notifications")


class AdminLog(Base):
    """ORM model for the admin_logs table."""
    __tablename__ = "admin_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(SAEnum(AdminAction, name="admin_action", create_type=False), nullable=False)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
